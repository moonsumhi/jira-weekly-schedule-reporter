"""Work-plan sourced inspection tasks. No PM issue or copied document is created."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib

from bson import ObjectId
from fastapi import HTTPException

from app.services import inspection_service as tasks, inspection_work_plans as plans
from app.services.work_document_assets import require_job
from app.utils.mongo import oid


def task_id(entry_id):
    return ObjectId(hashlib.sha256(f'inspection-work-plan:{oid(entry_id)}'.encode()).hexdigest()[:24])


async def assignee_snapshot(user_id):
    if not user_id:
        return {'assignee_id': None, 'assignee_name': '미배정'}
    user = await tasks.M.get_users_collection().find_one({
        '_id': oid(user_id), 'is_deleted': {'$ne': True}, 'is_blocked': {'$ne': True}})
    if not user:
        raise HTTPException(422, '담당자를 다시 선택해 주세요.')
    return {'assignee_id': str(user['_id']), 'assignee_name': user.get('full_name') or user.get('email') or '이름 없음'}


def display_snapshot(occurrence, plan, users):
    info = deepcopy(occurrence['issue_snapshot'])
    if plan:
        info['title'] = plan['title']
    person = users.get(info.get('assignee_id'))
    if person:
        info['assignee_name'] = person.get('full_name') or person.get('email') or info['assignee_name']
    return info


async def register(body, user):
    require_job(user)
    entry_id = str(oid(body.work_plan_id))
    plan = (await plans.plan_map([entry_id])).get(entry_id)
    if not plan:
        raise HTTPException(422, '삭제되었거나 가져올 수 없는 작업계획서입니다.')
    assets = await tasks.resolve_assets(body.asset_ids)
    person = await assignee_snapshot(body.assignee_id)
    identifier = task_id(entry_id)
    info = {'id': str(identifier), 'project_id': '', 'key': '작업계획서',
            'title': plan['title'], 'status': 'TODO', **person}
    def change(items):
        previous = next((o for o in items if o['month'] == body.month), None)
        if previous and previous['state'] != 'EXCLUDED':
            raise HTTPException(409, '해당 월에 이미 추가된 작업계획서입니다.')
        item = {'month': body.month, 'assets': assets, 'common': body.common, 'state': 'ACTIVE',
                'issue_snapshot': info, 'work_plan_snapshot': deepcopy(plan), 'planned_on': body.planned_on.isoformat(),
                'reason': '', 'created_by': user.id, 'created_at': datetime.now(timezone.utc), 'history': []}
        if previous:
            if previous.get('result'):
                item['result'] = deepcopy(previous['result'])
            item['history'] = previous.get('history', []) + [{'action': 'reconnect', 'actor': user.id, 'at': datetime.now(timezone.utc)}]
            items.remove(previous)
        items.append(item)
    await tasks.mutate(str(identifier), None, change, source={'source_type': 'WORK_PLAN', 'work_plan_id': entry_id})
    return {'issue_id': str(identifier), 'month': body.month}


async def change(task_id, month, body, user):
    doc = await tasks.collection().find_one({'_id': oid(task_id)})
    if not doc or not tasks.is_plan_task(doc):
        raise HTTPException(404, '작업계획서에서 추가한 점검 작업을 찾을 수 없습니다.')
    await tasks.require_task_access(doc, user)
    plan = (await plans.plan_map([doc['work_plan_id']])).get(doc['work_plan_id'])
    if not plan:
        raise HTTPException(409, '원본 작업계획서가 삭제되었습니다.')
    values = body.model_dump(exclude_unset=True)
    person = await assignee_snapshot(body.assignee_id) if 'assignee_id' in values else None
    assets = await tasks.resolve_assets(body.asset_ids or []) if 'asset_ids' in values else None
    def update(items):
        item = next((o for o in items if o['month'] == month), None)
        if not item:
            raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
        if item['state'] != 'ACTIVE' or (month < tasks.current_month() and item['issue_snapshot']['status'] == 'DONE'):
            raise HTTPException(409, '지난 점검 기록은 변경할 수 없습니다.')
        info = item['issue_snapshot']
        info['title'] = plan['title']
        if person:
            info.update(person)
        if 'status' in values:
            info['status'] = body.status
        if info['status'] == 'DONE':
            item['completed_snapshot'] = deepcopy(info)
            item['work_plan_snapshot'] = deepcopy(plan)
        else:
            item.pop('completed_snapshot', None)
        if assets is not None:
            item.update(assets=assets, common=body.common)
        if 'planned_on' in values:
            item['planned_on'] = body.planned_on.isoformat()
        item.setdefault('history', []).append({'action': 'plan_task', 'actor': user.id, 'at': datetime.now(timezone.utc)})
    await tasks.mutate(task_id, None, update, expected_version=body.version)
    return {'version': body.version + 1}
