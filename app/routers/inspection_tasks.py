"""서버 점검 작업과 PM 이슈·등록 자산 연결 API."""
from typing import Annotated, Literal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services import inspection_service as svc
from app.services import inspection_work_plans as plans
from app.services import inspection_plan_tasks as plan_tasks
from app.services.work_document_assets import require_job
from app.utils.mongo import oid

Month = Annotated[str, Field(pattern=r'^(20\d{2})-(0[1-9]|1[0-2])$')]


async def require_inspection(user: UserPublic = Depends(get_current_user)):
    if not user.is_admin and 'server_check' not in user.permissions:
        raise HTTPException(403, '서버 점검 메뉴 권한이 필요합니다.')
    return user


class Targets(BaseModel):
    asset_ids: list[str] = Field(default_factory=list, max_length=100)
    common: bool = False

    @model_validator(mode='after')
    def valid_targets(self):
        if self.common == bool(self.asset_ids):
            raise ValueError('대상 서버를 선택하거나 공통 작업으로 지정해 주세요.')
        if len(self.asset_ids) != len(set(self.asset_ids)):
            raise ValueError('중복된 서버가 있습니다.')
        for value in self.asset_ids:
            oid(value)
        return self


class PlanSelection(BaseModel):
    work_plan_ids: list[str] | None = Field(default=None, max_length=20)

    @field_validator('work_plan_ids')
    @classmethod
    def canonical_plans(cls, values):
        if values is None:
            return values
        result = [str(oid(value)) for value in values]
        if len(result) != len(set(result)):
            raise ValueError('같은 작업계획서를 중복 연결할 수 없습니다.')
        return result


class Registration(Targets, PlanSelection):
    month: Month
    issue_id: str


class PlanRegistration(Targets):
    month: Month
    work_plan_id: str
    assignee_id: str | None = None
    planned_on: date


class PlanTaskChange(BaseModel):
    version: int = Field(ge=1)
    status: Literal['BACKLOG', 'TODO', 'IN_PROGRESS', 'IMPLEMENTED', 'DONE'] | None = None
    assignee_id: str | None = None
    planned_on: date | None = None
    asset_ids: list[str] | None = Field(default=None, max_length=100)
    common: bool | None = None

    @model_validator(mode='after')
    def validate_changes(self):
        fields = self.model_fields_set
        if not (fields - {'version'}):
            raise ValueError('변경할 내용을 입력해 주세요.')
        for key in ('status', 'planned_on'):
            if key in fields and getattr(self, key) is None:
                raise ValueError('상태와 예정일은 비워 둘 수 없습니다.')
        if {'asset_ids', 'common'} & fields:
            if self.asset_ids is None or self.common is None:
                raise ValueError('대상 서버와 공통 작업 여부를 함께 입력해 주세요.')
            Targets(asset_ids=self.asset_ids, common=self.common)
        return self


class Change(Targets):
    action: Literal['rollover', 'exclude', 'targets']
    reason: str = Field(default='', max_length=1000)
    common: bool = True

    @model_validator(mode='after')
    def require_reason(self):
        self.reason = self.reason.strip()
        if self.action in ('rollover', 'exclude') and not self.reason:
            raise ValueError('이월 또는 제외 사유를 입력해 주세요.')
        return self


router = APIRouter()


@router.post('/from-work-plan', status_code=201)
async def register_plan(body: PlanRegistration, user: UserPublic = Depends(require_inspection)):
    return await plan_tasks.register(body, user)


@router.patch('/{task_id}/{month}/plan')
async def update_plan_task(task_id: str, month: Month, body: PlanTaskChange,
                           user: UserPublic = Depends(require_inspection)):
    return await plan_tasks.change(task_id, month, body, user)


class PlanLinks(PlanSelection):
    version: int = Field(ge=0)
    work_plan_ids: list[str] = Field(max_length=20)


@router.get('/work-plans')
async def work_plan_options(search: str = Query('', max_length=200), asset_ids: str = '',
                            user: UserPublic = Depends(require_inspection)):
    require_job(user)
    values = asset_ids.split(',') if asset_ids else []
    if len(values) > 100:
        raise HTTPException(422, '대상 서버는 최대 100대까지 선택할 수 있습니다.')
    return await plans.search_plans(search, [str(oid(value)) for value in values])


@router.put('/{issue_id}/{month}/work-plans')
async def link_work_plans(issue_id: str, month: Month, body: PlanLinks,
                          user: UserPublic = Depends(require_inspection)):
    return await plans.save_links(issue_id, month, body.work_plan_ids, body.version, user)


class TaskResult(BaseModel):
    version: int = Field(ge=0)
    content: str = Field(default='', max_length=10000)
    performed_on: date | None = None
    follow_up: str = Field(default='', max_length=3000)


@router.put('/{issue_id}/{month}/result')
async def save_result(issue_id: str, month: Month, body: TaskResult,
                      user: UserPublic = Depends(require_inspection)):
    doc = await svc.collection().find_one({'_id': oid(issue_id)})
    if not doc:
        raise HTTPException(404, '점검 작업을 찾을 수 없습니다.')
    await svc.require_task_access(doc, user)
    return await svc.save_result(doc, month, body.model_dump(mode='json'), user)


@router.get('')
async def list_tasks(month: Month, include_overdue: bool = True, issue_id: str | None = None,
                     asset_id: str | None = None, all_months: bool = False,
                     work_plan_id: str | None = None,
                     user: UserPublic = Depends(require_inspection)):
    if asset_id:
        oid(asset_id)
    if work_plan_id:
        require_job(user)
        work_plan_id = str(oid(work_plan_id))
    return {'inspection_date': (await svc.inspection_date(month)).isoformat(),
            'items': await svc.list_tasks(user, month, include_overdue, issue_id, asset_id, all_months, work_plan_id)}


@router.get('/schedule')
async def schedule(month: Month, user: UserPublic = Depends(require_inspection)):
    return {'inspection_date': (await svc.inspection_date(month)).isoformat()}


@router.get('/assets')
async def search_assets(search: str = Query('', max_length=200), ids: str = '',
                        user: UserPublic = Depends(require_inspection)):
    import re
    query = {'is_deleted': {'$ne': True}}
    if ids:
        values = ids.split(',')
        if len(values) > 100:
            raise HTTPException(422, '서버는 최대 100대까지 선택할 수 있습니다.')
        query['_id'] = {'$in': [oid(i) for i in values]}
    elif search.strip():
        pattern = {'$regex': re.escape(search.strip()), '$options': 'i'}
        query['$or'] = [{field: pattern} for field in ('name', 'ip', 'asset_no', 'fields.서버명')]
    docs = await svc.M.get_assets_servers_collection().find(query).sort('name', 1).limit(100).to_list(100)
    return [svc.asset_snapshot(d) for d in docs]


@router.post('', status_code=201)
async def register(body: Registration, user: UserPublic = Depends(require_inspection)):
    issue = await svc.issue_for_user(body.issue_id, user)
    assets = await svc.resolve_assets(body.asset_ids)
    linked_plans = None
    if body.work_plan_ids is not None:
        require_job(user)
        previous = await svc.collection().find_one({'_id': oid(body.issue_id)})
        occurrence = next((o for o in (previous or {}).get('occurrences', []) if o['month'] == body.month), {})
        linked_plans = await plans.selected_plans(body.work_plan_ids, occurrence.get('work_plans', []))
    await svc.register(issue, body.month, assets, body.common, user, linked_plans)
    return {'issue_id': body.issue_id, 'month': body.month}


@router.patch('/{issue_id}/{month}')
async def change(issue_id: str, month: Month, body: Change, user: UserPublic = Depends(require_inspection)):
    assets = await svc.resolve_assets(body.asset_ids) if body.action == 'targets' else None
    await svc.change_occurrence(issue_id, month, body.action, body.reason, user, assets, body.common)
    return {'ok': True}
