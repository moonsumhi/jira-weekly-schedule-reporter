# app/routers/assets.py
from __future__ import annotations

import io
import logging
import urllib.parse
from typing import Dict, List, Optional

import msoffcrypto
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, UploadFile, status
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.db.mongo import MongoClientManager

from app.models.assets import (
    AssetHistoryOut,
    McpAssetCreate,
    ServerAssetCreate,
    ServerAssetDelete,
    ServerAssetOut,
    ServerAssetPatch,
    ServerAssetReplace,
)
from app.models.user import UserPublic
from app.routers.admin import require_admin
from app.routers.auth import get_current_user
from app.routers.permissions import require_asset_access
from app.services.assets_service import AssetsService, list_all_assets
from app.services import asset_import_batches
from app.services.asset_registration import evaluate_lifecycle, prepare_mcp_asset
from app.services.eos_service import EosService
from app.lifecycle_audit import asset_eos
from app.utils.mongo import oid

VALID_CATEGORIES = set(MongoClientManager.CATEGORY_COLLECTIONS)

logger = logging.getLogger(__name__)

router = APIRouter()


def _svc(category: Optional[str]) -> AssetsService:
    cat = category or "서버"
    if cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 카테고리입니다. 허용값: {', '.join(sorted(VALID_CATEGORIES))}",
        )
    return AssetsService(cat)


@router.get("/eos-map", response_model=Dict[str, str])
async def get_eos_map(current_user: UserPublic = Depends(get_current_user)):
    return await EosService.get_eos_map()


@router.get("/eos-summary")
async def get_eos_summary(current_user: UserPublic = Depends(get_current_user)):
    from datetime import date, timedelta
    from app.services.assets_service import list_all_assets

    assets = await list_all_assets(include_deleted=False)
    today = date.today()
    one_year_later = today + timedelta(days=365)

    eos_list = []
    soon_list = []

    for a in assets:
        fields = dict(a.get("fields") or {})
        fields.update(asset_eos(fields, fields.get("자산유형", "서버")) or {})
        if str(fields.get("상태") or "").strip() == "폐기":
            continue  # 폐기된 자산은 EoS 카운트에서 제외
        status_val = str(fields.get("eos_action_status") or "").strip()
        eos_date_str = str(fields.get("eos_date") or "").strip()

        item = {
            "id": str(a.get("_id", "")),
            "name": a.get("name", ""),
            "ip": a.get("ip", ""),
            "category": fields.get("자산유형", "서버"),
            "os": fields.get("운영체제", ""),
            "version": fields.get("version", ""),
            "eos_date": eos_date_str,
        }

        if status_val == "EOS":
            eos_list.append(item)
        elif eos_date_str:
            try:
                # eos_date: YYYY-MM or YYYY-MM-DD
                parts = eos_date_str.split("-")
                if len(parts) == 2:
                    eos_date = date(int(parts[0]), int(parts[1]), 1)
                else:
                    eos_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                if today <= eos_date <= one_year_later:
                    soon_list.append(item)
            except (ValueError, IndexError):
                pass

    return {
        "eos_count": len(eos_list),
        "soon_count": len(soon_list),
        "eos_assets": eos_list,
        "soon_assets": soon_list,
    }
@router.post('/imports')
async def start_asset_import(filename: str = Body(..., embed=True), current_user: UserPublic = Depends(require_asset_access)):
    return await asset_import_batches.start_batch(filename, current_user.email)


@router.get('/mcp-schema')
async def mcp_asset_schema(current_user: UserPublic = Depends(require_asset_access)):
    """MCP가 고정 스키마와 유형별 규칙을 백엔드에서 함께 조회한다."""
    return {
        'schema': McpAssetCreate.model_json_schema(),
        'required_fields': ['구분', '서버명', '설명', '운영체제'],
        'category_rules': {
            '서버': '운영체제/배포판 필수, system_info 선택',
            'VMware': '운영체제/배포판 필수',
            '네트워크': '운영체제에 장비 기종 입력',
            '스토리지': '운영체제에 스토리지 기종 입력, version에 펌웨어 버전 입력 가능',
            '소프트웨어': '운영체제에 제품명, version에 버전 입력 가능. IP는 선택',
            '정보보호시스템': '운영체제에 장비 기종, 제조사 필수',
            'DBMS': '운영체제에 DB 종류, version 또는 db_series 필수',
        },
        'note': '자산번호는 asset_no, 자산명은 fields.서버명, 호스트명은 name에 입력합니다. 랙 배치는 지원하지 않습니다.',
    }


@router.post('/mcp-create', status_code=status.HTTP_201_CREATED)
async def create_mcp_asset(body: McpAssetCreate, current_user: UserPublic = Depends(require_asset_access)):
    """Validate once, then create the asset and its rollback snapshot in one write."""
    fields, lifecycle = prepare_mcp_asset(body)
    service = _svc(body.category)
    col = service._col()
    asset_id = body.asset_id.strip() if body.asset_id else None
    if asset_id:
        duplicate_id = await col.find_one({'asset_id': asset_id}, {'_id': 1, 'is_deleted': 1})
        if duplicate_id:
            raise HTTPException(409, detail={'code': 'DUPLICATE_ASSET_ID', 'message': '같은 자산 ID가 이미 있습니다.', 'asset_id': str(duplicate_id['_id']), 'is_deleted': duplicate_id.get('is_deleted', False)})
    candidates = await col.find({'ip': body.ip.strip(), 'is_deleted': {'$ne': True}},
                                {'_id': 1, 'name': 1, 'ip': 1, 'asset_id': 1}).limit(10).to_list(None)
    if body.ip.strip() and candidates and not body.confirm_duplicate_ip:
        raise HTTPException(409, detail={
            'code': 'DUPLICATE_IP', 'message': '같은 유형에 동일 IP가 있습니다. 사용자에게 확인받은 후 다시 요청하세요.',
            'candidates': [{'id': str(d['_id']), 'name': d.get('name', ''), 'ip': d.get('ip', ''), 'asset_id': d.get('asset_id')} for d in candidates],
        })
    batch = await asset_import_batches.start_batch(f'MCP 등록 · {body.name.strip()}', current_user.email, source='mcp')
    batch_id = batch['id']
    try:
        async with asset_import_batches.reserve(batch_id, current_user.email):
            asset = await service.create(
                ip=body.ip.strip(), name=body.name.strip(), asset_id=asset_id,
                asset_no=body.asset_no.strip(), fields=fields, system_info=body.system_info,
                actor_email=current_user.email, source='mcp', import_batch_id=batch_id,
            )
            await asset_import_batches.collection().update_one({'_id': oid(batch_id)}, {'$inc': {'write_count': 1}})
        return {'asset': ServerAssetOut(**asset), 'batch_id': batch_id, 'lifecycle': lifecycle}
    except DuplicateKeyError as exc:
        raise HTTPException(409, detail={'code': 'DUPLICATE_ASSET_ID', 'message': '같은 자산 ID가 이미 있습니다.', 'batch_id': batch_id}) from exc
    except ValueError as exc:
        raise HTTPException(409, detail={'message': str(exc), 'batch_id': batch_id}) from exc
    finally:
        await asset_import_batches.finish_batch(batch_id, current_user.email)


@router.get('/imports')
async def list_asset_imports(skip: int = Query(0, ge=0), limit: int = Query(51, ge=1, le=100),
                             current_user: UserPublic = Depends(require_admin)):
    return await asset_import_batches.list_batches(skip, limit)


@router.post('/imports/{batch_id}/finish', status_code=204)
async def finish_asset_import(batch_id: str, current_user: UserPublic = Depends(require_asset_access)):
    await asset_import_batches.finish_batch(batch_id, current_user.email)


@router.post('/imports/{batch_id}/rollback')
async def rollback_asset_import(batch_id: str, current_user: UserPublic = Depends(require_admin)):
    return await asset_import_batches.rollback_batch(batch_id, current_user.email)


@router.get("", response_model=List[ServerAssetOut])
async def list_servers(
    category: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    if category:
        items = await _svc(category).list(include_deleted=include_deleted)
    else:
        items = await list_all_assets(include_deleted=include_deleted)
    return [ServerAssetOut(**x) for x in items]


@router.get("/{server_id}", response_model=ServerAssetOut)
async def get_server(
    server_id: str,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await _svc(category).get(_id=oid(server_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ServerAssetOut(**out)


@router.post("", response_model=ServerAssetOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerAssetCreate,
    category: Optional[str] = Query(None),
    source: str = Query(default="manual"),
    import_batch_id: Optional[str] = Query(None),
    auto_lifecycle: bool = Query(False),
    lifecycle_series: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_asset_access),
):
    cat = category or (body.fields or {}).get("자산유형", "서버")
    try:
        async with asset_import_batches.reserve(import_batch_id, current_user.email) as batch_id:
            fields = dict(body.fields or {})
            if auto_lifecycle:
                computed, _ = evaluate_lifecycle(fields, cat, lifecycle_series)
                fields.update(computed)
            out = await _svc(cat).create(
                ip=body.ip, name=body.name, asset_id=body.asset_id, asset_no=body.asset_no,
                fields=fields, actor_email=current_user.email,
                source='import' if batch_id else source, import_batch_id=batch_id, system_info=body.system_info,
            )
            if import_batch_id:
                await asset_import_batches.collection().update_one({'_id': oid(import_batch_id)}, {'$inc': {'write_count': 1}})
    except ValueError as e:
        logger.warning("409 create_server: cat=%s ip=%s name=%s asset_id=%s err=%s", cat, body.ip, body.name, body.asset_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.put("/{server_id}", response_model=ServerAssetOut)
async def replace_server(
    server_id: str,
    body: ServerAssetReplace,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_asset_access),
):
    cat = category or (body.fields or {}).get("자산유형", "서버")
    try:
        out = await _svc(cat).replace(
            _id=oid(server_id),
            ip=body.ip,
            name=body.name,
            asset_id=body.asset_id,
            asset_no=body.asset_no,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.patch("/{server_id}", response_model=ServerAssetOut)
async def patch_server(
    server_id: str,
    body: ServerAssetPatch,
    category: Optional[str] = Query(None),
    import_batch_id: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_asset_access),
):
    try:
        async with asset_import_batches.reserve(import_batch_id, current_user.email) as batch_id:
            out = await _svc(category).patch(
                _id=oid(server_id), patch=body.model_dump(exclude_unset=True),
                expected_version=body.version, actor_email=current_user.email, import_batch_id=batch_id,
            )
            if import_batch_id:
                await asset_import_batches.collection().update_one({'_id': oid(import_batch_id)}, {'$inc': {'write_count': 1}})
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.delete("/{server_id}", response_model=ServerAssetOut)
async def delete_server(
    server_id: str,
    body: ServerAssetDelete = Body(default_factory=ServerAssetDelete),
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_asset_access),
):
    try:
        out = await _svc(category).delete(_id=oid(server_id), actor_email=current_user.email, reason=body.reason)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ServerAssetOut(**out)


@router.post("/{server_id}/restore", response_model=ServerAssetOut)
async def restore_server(
    server_id: str,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_asset_access),
):
    try:
        out = await _svc(category).restore(_id=oid(server_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.delete("/{server_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_server(
    server_id: str,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_admin),
):
    try:
        await _svc(category).purge(_id=oid(server_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{server_id}/history", response_model=List[AssetHistoryOut])
async def get_history(
    server_id: str,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await _svc(category).get_history(server_id=server_id)
    return [AssetHistoryOut(**x) for x in items]


@router.post("/decrypt-xlsx")
async def decrypt_xlsx(
    file: UploadFile,
    password: str = Query(...),
    current_user: UserPublic = Depends(get_current_user),
):
    content = await file.read()
    try:
        office_file = msoffcrypto.OfficeFile(io.BytesIO(content))
        office_file.load_key(password=password)
        out = io.BytesIO()
        office_file.decrypt(out)
        out.seek(0)
    except Exception as e:
        msg = str(e).lower()
        if "password" in msg or "invalid" in msg or "incorrect" in msg:
            raise HTTPException(status_code=400, detail="비밀번호가 올바르지 않습니다.")
        raise HTTPException(status_code=400, detail=f"복호화 실패: {e}")
    return Response(
        content=out.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/encrypt-xlsx")
async def encrypt_xlsx(
    file: UploadFile,
    filename: str = Query(default="export.xlsx"),
    current_user: UserPublic = Depends(get_current_user),
):
    if not settings.ASSET_EXPORT_PASSWORD:
        raise HTTPException(status_code=503, detail="ASSET_EXPORT_PASSWORD가 설정되지 않았습니다.")
    content = await file.read()
    out = io.BytesIO()
    msoffcrypto.OfficeFile(io.BytesIO(content)).encrypt(settings.ASSET_EXPORT_PASSWORD, out)
    out.seek(0)
    return Response(
        content=out.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"},
    )
