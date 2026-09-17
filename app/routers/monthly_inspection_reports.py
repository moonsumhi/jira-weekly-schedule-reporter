"""Monthly inspection report authoring API."""
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.user import UserPublic
from app.routers.inspection_tasks import Month, TaskResult, require_inspection
from app.services import monthly_inspection_reports as svc

router = APIRouter()
User = Annotated[UserPublic, Depends(require_inspection)]


class Mapping(BaseModel):
    row_key: str = Field(min_length=1, max_length=80)
    asset_id: str | None = None

    @field_validator('asset_id')
    @classmethod
    def canonical_asset(cls, value):
        return str(svc.oid(value)) if value is not None else None


class Preview(BaseModel):
    month: Month
    kind: Literal['PLAN', 'RESULT'] = 'RESULT'
    project_ids: list[str] | None = Field(default=None, max_length=500)
    source_id: str | None = None
    comparison_id: str | None = None
    mappings: list[Mapping] = Field(default_factory=list, max_length=5000)
    include_images: bool = True
    report_id: str | None = None
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def mapping_source_required(self):
        if self.mappings and not self.source_id:
            raise ValueError('자산을 연결할 점검 데이터를 선택해 주세요.')
        return self


class Create(BaseModel):
    preview_id: str
    client_id: str = Field(min_length=8, max_length=100)


class Version(BaseModel):
    version: int = Field(ge=1)


class Participant(BaseModel):
    user_id: str
    roles: list[Literal['LEAD', 'RESOURCE_CHECK', 'WORK_EXECUTION', 'SERVICE_CHECK', 'REVIEW', 'OTHER']] = Field(min_length=1, max_length=6)
    work_summary: str = Field(default='', max_length=5000)
    issue_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator('user_id')
    @classmethod
    def canonical_user_id(cls, value):
        return str(svc.oid(value))

    @field_validator('issue_ids')
    @classmethod
    def canonical_issue_ids(cls, values):
        result = [str(svc.oid(value)) for value in values]
        if len(result) != len(set(result)):
            raise ValueError('같은 작업을 중복 연결할 수 없습니다.')
        return result

    @field_validator('roles')
    @classmethod
    def unique_roles(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('같은 역할을 중복 선택할 수 없습니다.')
        return values


class Participants(Version):
    participants: list[Participant] = Field(max_length=100)

    @model_validator(mode='after')
    def unique_users(self):
        ids = [p.user_id for p in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError('같은 참여자를 중복 등록할 수 없습니다.')
        return self


class Edit(Version):
    title: str = Field(min_length=1, max_length=200)
    inspection_date: date
    purpose: str = Field(default='', max_length=3000)
    overview: str = Field(default='', max_length=10000)
    limitations: str = Field(default='', max_length=5000)
    include_appendix: bool = False
    planned_time: str = Field(default='', max_length=100)
    resource_checks: str = Field(default='', max_length=3000)


class ReportNote(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    content: str = Field(min_length=1, max_length=5000)

    @field_validator('content', mode='before')
    @classmethod
    def trim_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class ReportNotes(Version):
    notes: list[ReportNote] = Field(max_length=100)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({note.id for note in self.notes}) != len(self.notes):
            raise ValueError('같은 추가 확인 사항이 중복되어 있습니다.')
        return self


class Refresh(Version):
    preview_id: str


class ReportActionEdit(Version):
    row_key: str | None = Field(default=None, max_length=80)
    action_id: str | None = None
    action_token: str | None = Field(default=None, max_length=64)
    memo: str = Field(default='', max_length=10000)
    images: list[str] = Field(default_factory=list)
    is_resolved: bool = False


@router.get('/options')
async def options(month: Month, user: User):
    projects = await svc.report_projects()
    # Return only metadata. Full sources are read within permission-checked previews.
    docs = await svc.M.get_db()[svc.M.HEALTH_REPORTS].find(
        {'report_date': {'$lt': svc.tasks.next_month(month) + '-01'}},
        {'report_date': 1, 'report_title': 1, 'uploaded_at': 1, 'uploaded_by': 1}
    ).sort([('report_date', -1), ('uploaded_at', -1)]).to_list(None)
    return {'projects': projects, 'sources': [svc.source_info(d) for d in docs],
            'inspection_date': (await svc.tasks.inspection_date(month)).isoformat()}


@router.get('/participant-options')
async def participant_options(user: User, q: str = Query('', max_length=100)):
    return await svc.participant_options(q)


@router.get('')
async def list_reports(month: Month, user: User, kind: Literal['PLAN', 'RESULT'] = 'RESULT'):
    query = {'month': month, 'kind': 'PLAN' if kind == 'PLAN' else {'$ne': 'PLAN'}}
    docs = await svc.M.get_db()[svc.REPORTS].find(query, {'snapshot': 0}).sort([('revision', -1), ('created_at', -1)]).to_list(None)
    return svc.clean(docs)


@router.post('/preview')
async def preview(body: Preview, user: User):
    return await svc.preview(user, body)


@router.post('', status_code=201)
async def create(body: Create, user: User):
    return svc.clean(await svc.create_report(user, body.preview_id, body.client_id))


@router.get('/{report_id}')
async def get(report_id: str, user: User):
    return svc.clean(await svc.get_report(report_id, user))


@router.patch('/{report_id}')
async def edit(report_id: str, body: Edit, user: User):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, body.version)
    if not body.title.strip():
        raise HTTPException(422, '보고서 제목을 입력해 주세요.')
    values = body.model_dump(exclude={'version', 'limitations', 'planned_time', 'resource_checks'})
    if doc.get('kind') == 'PLAN':
        values.update({key: getattr(body, key) for key in ('planned_time', 'resource_checks')
                       if key in body.model_fields_set})
        values['include_appendix'] = False
    # Older clients can still edit legacy prose, but cannot flatten an item list.
    if 'limitations' in body.model_fields_set:
        notes = svc.report_notes(doc)
        if any(note['id'] != 'legacy' for note in notes):
            if body.limitations != doc.get('limitations', ''):
                raise HTTPException(409, '추가 확인 사항은 항목별로 수정해 주세요. 화면을 새로고침한 뒤 다시 시도해 주세요.')
        else:
            values.update(limitations=body.limitations,
                          additional_notes=svc.report_notes({'limitations': body.limitations}))
    values['title'] = body.title.strip()
    values['inspection_date'] = body.inspection_date.isoformat()
    if not values['inspection_date'].startswith(doc['month'] + '-'):
        raise HTTPException(422, '보고서 월에 해당하는 점검일을 선택해 주세요.')
    return svc.clean(await svc.change_report(doc, user, values))


@router.put('/{report_id}/notes')
async def save_notes(report_id: str, body: ReportNotes, user: User):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, body.version)
    return svc.clean(await svc.change_report(doc, user, {
        'additional_notes': [note.model_dump() for note in body.notes], 'limitations': ''}))


@router.get('/{report_id}/tasks/{issue_id}/{month}')
async def task_result(report_id: str, issue_id: str, month: Month, user: User):
    report = await svc.get_report(report_id, user)
    task = await svc.report_task(report, issue_id, month)
    rows = await svc.tasks.hydrate_tasks([task], month, include_overdue=False)
    return svc.clean(rows[0])


@router.put('/{report_id}/tasks/{issue_id}/{month}/result')
async def save_task_result(report_id: str, issue_id: str, month: Month, body: TaskResult, user: User):
    report = await svc.get_report(report_id, user)
    svc.draft_version(report, report['version'])
    task = await svc.report_task(report, issue_id, month)
    return svc.clean(await svc.tasks.save_result(task, month, body.model_dump(mode='json'), user))


@router.put('/{report_id}/participants')
async def participants(report_id: str, body: Participants, user: User):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, body.version)
    values = await svc.resolve_participants(doc, body.participants)
    return svc.clean(await svc.change_report(doc, user, {'participants': values}))


@router.get('/{report_id}/action')
async def action(report_id: str, user: User, row_key: str | None = None, action_id: str | None = None):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, doc['version'])
    hostname, current = await svc.report_action(doc, row_key, action_id)
    return svc.clean({'host_name': hostname, 'action': current, 'action_token': svc.action_token(current),
                      'version': doc['version']})


@router.put('/{report_id}/action')
async def save_action(report_id: str, body: ReportActionEdit, user: User):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, body.version)
    return svc.clean(await svc.save_report_action(doc, user, body))


@router.post('/{report_id}/refresh')
async def refresh(report_id: str, body: Refresh, user: User):
    doc = await svc.get_report(report_id, user)
    if doc['state'] == 'DRAFT' and doc.get('used_preview_id') == body.preview_id:
        return svc.clean(doc)
    svc.draft_version(doc, body.version)
    return svc.clean(await svc.refresh_report(doc, user, body.preview_id))


@router.post('/{report_id}/sync-results')
async def sync_results(report_id: str, body: Version, user: User):
    doc = await svc.get_report(report_id, user)
    svc.draft_version(doc, body.version)
    return svc.clean(await svc.sync_results(doc, user))


@router.post('/{report_id}/finalize')
async def finalize(report_id: str, body: Version, user: User):
    doc = await svc.get_report(report_id, user)
    if doc['state'] == 'FINAL' and doc['version'] == body.version + 1:
        return svc.clean(doc)
    svc.draft_version(doc, body.version)
    return svc.clean(await svc.change_report(doc, user, {
        'state': 'FINAL', 'finalized_at': svc.now(), 'finalized_by': user.full_name or user.email}))


@router.post('/{report_id}/revisions', status_code=201)
async def revision(report_id: str, user: User):
    return svc.clean(await svc.revision(await svc.get_report(report_id, user), user))
