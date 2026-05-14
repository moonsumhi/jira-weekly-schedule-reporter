# app/routers/assets.py
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.models.assets import (
    AssetHistoryOut,
    ServerAssetCreate,
    ServerAssetDelete,
    ServerAssetOut,
    ServerAssetPatch,
    ServerAssetReplace,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.assets_service import AssetsService, list_all_assets
from app.services.eos_service import EosService
from app.utils.mongo import oid

VALID_CATEGORIES = {"서버", "네트워크", "정보보호시스템", "DBMS", "VMware"}

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


@router.post("", response_model=ServerAssetOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerAssetCreate,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    cat = category or (body.fields or {}).get("자산유형", "서버")
    try:
        out = await _svc(cat).create(
            ip=body.ip,
            name=body.name,
            asset_id=body.asset_id,
            asset_no=body.asset_no,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except ValueError as e:
        logger.warning("409 create_server: cat=%s ip=%s name=%s asset_id=%s err=%s", cat, body.ip, body.name, body.asset_id, e)
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.put("/{server_id}", response_model=ServerAssetOut)
async def replace_server(
    server_id: str,
    body: ServerAssetReplace,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
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
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await _svc(category).patch(
            _id=oid(server_id),
            patch=body.model_dump(exclude_unset=True),
            expected_version=body.version,
            actor_email=current_user.email,
        )
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
    current_user: UserPublic = Depends(get_current_user),
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
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await _svc(category).restore(_id=oid(server_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ServerAssetOut(**out)


@router.get("/{server_id}/history", response_model=List[AssetHistoryOut])
async def get_history(
    server_id: str,
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await _svc(category).get_history(server_id=server_id)
    return [AssetHistoryOut(**x) for x in items]
