"""Regular resource inspections reference canonical server assets; measurements remain historical."""
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from pymongo.errors import DuplicateKeyError

from app.models.user import UserPublic
from app.routers.admin import require_admin
from app.routers.inspection_tasks import Month, require_inspection
from app.routers.monthly_inspection_reports import Mapping
from app.services import monthly_inspection_reports as reports
from app.services import inspection_service as tasks
from app.services import inspection_hostnames
from app.db.mongo import MongoClientManager as M
from app.utils.mongo import oid

router = APIRouter()
User = Annotated[UserPublic, Depends(require_inspection)]
SETTING = 'inspection_resource_targets'


class Targets(BaseModel):
    version: int = Field(ge=0)
    asset_ids: list[str] = Field(max_length=500)

    @field_validator('asset_ids')
    @classmethod
    def unique_assets(cls, values):
        values = [str(oid(value)) for value in values]
        if len(set(values)) != len(values):
            raise ValueError('같은 자산을 중복 선택할 수 없습니다.')
        return values


class ResourcePreview(BaseModel):
    month: Month
    source_id: str = Field(min_length=24, max_length=24)
    mappings: list[Mapping] = Field(default_factory=list, max_length=5000)


async def hostname_admin(user: Annotated[UserPublic, Depends(require_admin)]):
    if not user.is_internal:
        raise HTTPException(403, '자산 호스트명 변경은 내부 접속에서만 사용할 수 있습니다.')
    return user


HostnameAdmin = Annotated[UserPublic, Depends(hostname_admin)]


class HostnameChanges(BaseModel):
    revision: str = Field(pattern=r'^[0-9a-f]{64}$')
    asset_ids: list[str] = Field(min_length=1, max_length=5000)

    @field_validator('asset_ids')
    @classmethod
    def unique_assets(cls, values):
        return Targets.unique_assets(values)


@router.get('/{source_id}/hostnames/preview')
async def preview_hostnames(source_id: str, user: HostnameAdmin):
    data, _ = await inspection_hostnames.preview(source_id)
    return reports.clean(data)


@router.post('/{source_id}/hostnames/apply')
async def apply_hostnames(source_id: str, body: HostnameChanges, user: HostnameAdmin):
    return await inspection_hostnames.apply(source_id, body.revision, body.asset_ids, user)


async def target_state():
    config = await M.get_db()[M.APP_SETTINGS].find_one({'_id': SETTING}) or {'version': 0, 'asset_ids': []}
    assets = await M.get_assets_servers_collection().find({'_id': {'$in': [oid(i) for i in config['asset_ids']]}}).to_list(None)
    by_id = {str(a['_id']): tasks.asset_snapshot(a) for a in assets}
    return config, [by_id.get(i) or {'id': i, 'name': '삭제된 자산', 'ip': '', 'asset_name': '', 'status': '', 'is_deleted': True} for i in config['asset_ids']]


@router.get('/targets')
async def get_targets(user: User):
    config, assets = await target_state()
    return {'version': config['version'], 'assets': assets}


@router.put('/targets')
async def save_targets(body: Targets, user: User):
    assets = await tasks.resolve_assets(body.asset_ids, category='서버')
    values = {'asset_ids': body.asset_ids, 'version': body.version + 1,
              'updated_at': reports.now(), 'updated_by': user.id}
    col = M.get_db()[M.APP_SETTINGS]
    if body.version == 0:
        try:
            await col.insert_one({'_id': SETTING, **values})
        except DuplicateKeyError:
            raise HTTPException(409, '다른 사용자가 점검 대상을 변경했습니다. 새로고침 후 다시 선택해 주세요.')
    else:
        result = await col.update_one({'_id': SETTING, 'version': body.version}, {'$set': values})
        if not result.matched_count:
            raise HTTPException(409, '다른 사용자가 점검 대상을 변경했습니다. 새로고침 후 다시 선택해 주세요.')
    return {'version': values['version'], 'assets': assets}


@router.get('')
async def list_resources(month: Month, user: User, source_id: str | None = None):
    return await resource_view(month, source_id)


@router.post('/preview')
async def preview_resources(body: ResourcePreview, user: User):
    return await resource_view(body.month, body.source_id, body.mappings)


async def resource_view(month, source_id=None, mappings=()):
    config, targets = await target_state()
    source = await reports.source_doc(source_id, month) if source_id else await reports.latest_source(month)
    sources = await M.get_db()[M.HEALTH_REPORTS].find(
        {'report_date': {'$gte': month + '-01', '$lt': tasks.next_month(month) + '-01'}},
        {'report_date': 1, 'report_title': 1, 'uploaded_at': 1, 'uploaded_by': 1},
    ).sort([('report_date', -1), ('uploaded_at', -1), ('_id', -1)]).to_list(None)
    previous_month = (date.fromisoformat(month + '-01') - timedelta(days=1)).strftime('%Y-%m')
    comparison = await reports.latest_source(previous_month) if source else None
    # Evidence is loaded by the detail panel; do not duplicate base64 images in list rows.
    rows, _ = await reports.resource_snapshot(source, comparison, include_images=False, mappings_input=mappings)
    target_ids = {a['id'] for a in targets}
    items = [{'asset': asset, 'records': [r for r in rows if (r.get('asset') or {}).get('id') == asset['id']]} for asset in targets]
    other = [r for r in rows if (r.get('asset') or {}).get('id') not in target_ids]
    return reports.clean({'month': month, 'version': config['version'], 'items': items,
                          'sources': [reports.source_info(s) for s in sources],
                          'source': reports.source_info(source), 'comparison': reports.source_info(comparison),
                          'other_records': other, 'records': rows})


@router.put('/{source_id}/mappings', deprecated=True)
async def save_connections(source_id: str, user: User):
    raise HTTPException(410, '자산 연결은 점검 데이터별로 지정합니다. 자원 점검에서 연결할 자산을 선택해 주세요.')
