"""References to work management documents used by monthly inspections."""
from copy import deepcopy
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.services import work_document_assets
from app.utils.mongo import oid


def is_work_plan(template):
    if not template or not work_document_assets.is_work_document(template):
        return False
    key = str(template.get('jira_issue_key') or '').upper()
    return key in ('JOB-PLAN-SERVICE', 'JOB-PLAN-NONSERVICE') or (
        not key.startswith('JOB-') and
        ''.join(str(template.get('title') or '').split()).startswith('작업계획서'))


def is_work_result(template):
    if not template or not work_document_assets.is_work_document(template):
        return False
    key = str(template.get('jira_issue_key') or '').upper()
    return key == 'JOB-RESULT' or (not key.startswith('JOB-') and
        ''.join(str(template.get('title') or '').split()).startswith('작업결과서'))


def plan_summary(doc, template):
    return {**work_document_assets.summary(doc, template),
            'version': doc.get('version', 1),
            'linked_assets': deepcopy(doc.get('linked_assets', [])),
            'is_deleted': bool(doc.get('is_deleted')), 'unavailable': False}


async def search_plans(search='', asset_ids=(), limit=30):
    return await search_documents(search, asset_ids, limit)


async def search_documents(search='', asset_ids=(), limit=30, *, kind='PLAN'):
    matches = is_work_result if kind == 'RESULT' else is_work_plan
    templates = await M.get_form_templates_collection().find({'is_deleted': {'$ne': True}}).to_list(None)
    templates = {str(t['_id']): t for t in templates if matches(t)}
    query = {'template_id': {'$in': list(templates)}, 'is_deleted': {'$ne': True}}
    if asset_ids:
        query['asset_ids'] = {'$in': list(asset_ids)}
    # Search before limiting results, including older documents. Body/image content is not searched.
    cursor = M.get_form_entries_collection().find(query, {'data.문서 본문.내용': 0}).sort([('created_at', -1), ('_id', -1)])
    query_text = ''.join(search.casefold().split())
    selected, has_more = [], False
    async for doc in cursor:
        summary = plan_summary(doc, templates[doc['template_id']])
        searchable = ''.join(' '.join(str(summary.get(k) or '') for k in ('title', 'template_title', 'work_date')).casefold().split())
        if query_text and query_text not in searchable:
            continue
        if len(selected) == limit:
            has_more = True
            break
        selected.append(summary)
    await work_document_assets.hydrate(selected)
    return {'items': selected, 'has_more': has_more}


async def plan_map(ids):
    return await document_map(ids)


async def document_map(ids, *, kind='PLAN'):
    if not ids:
        return {}
    matches = is_work_result if kind == 'RESULT' else is_work_plan
    docs = await M.get_form_entries_collection().find({'_id': {'$in': [oid(i) for i in ids]}}, {'data.문서 본문.내용': 0}).to_list(None)
    template_ids = {str(d.get('template_id')) for d in docs}
    templates = {str(t['_id']): t for t in await M.get_form_templates_collection().find(
        {'_id': {'$in': [oid(i) for i in template_ids if ObjectId.is_valid(i)]}}).to_list(None)}
    await work_document_assets.hydrate(docs)
    return {str(d['_id']): plan_summary(d, templates[d['template_id']]) for d in docs
            if not d.get('is_deleted') and matches(templates.get(d.get('template_id')))
            and not templates[d['template_id']].get('is_deleted')}


async def selected_plans(ids, previous=()):
    return await selected_documents(ids, previous)


async def selected_documents(ids, previous=(), *, kind='PLAN'):
    current = await document_map(ids, kind=kind)
    previous = {p['id']: p for p in previous}
    result = []
    for entry_id in ids:
        if entry_id in current:
            result.append(current[entry_id])
        elif entry_id in previous:
            saved = deepcopy(previous[entry_id])
            saved.pop('current', None)
            saved['unavailable'] = True
            result.append(saved)
        else:
            label = '작업결과서' if kind == 'RESULT' else '작업계획서'
            raise HTTPException(422, f'삭제되었거나 연결할 수 없는 {label}가 있습니다. 다시 선택해 주세요.')
    return result


async def hydrate_plans(rows):
    ids = {p['id'] for row in rows for p in row.get('work_plans', [])}
    current = await plan_map(ids)
    for row in rows:
        row.setdefault('work_plans', [])
        row.setdefault('work_plans_version', 0)
        for plan in row['work_plans']:
            plan['current'] = deepcopy(current.get(plan['id']))
            plan['unavailable'] = plan['current'] is None


async def hydrate_results(rows):
    references = [ref for row in rows for ref in (row.get('result') or {}).get('work_results', [])]
    current = await document_map({ref['id'] for ref in references}, kind='RESULT')
    for ref in references:
        ref['current'] = deepcopy(current.get(ref['id']))
        ref['unavailable'] = ref['current'] is None


def freeze_results(rows):
    """Capture reference metadata without embedding the original document body."""
    for row in rows:
        result = row.get('result')
        if result is None:
            continue
        result['work_results'] = [deepcopy(ref.get('current') or ref) for ref in result.get('work_results', [])]
        for ref in result['work_results']:
            ref.pop('current', None)


async def save_links(issue_id, month, entry_ids, version, user):
    from app.services import inspection_service as tasks
    work_document_assets.require_job(user)
    doc = await tasks.collection().find_one({'_id': oid(issue_id)})
    if not doc:
        raise HTTPException(404, '점검 작업을 찾을 수 없습니다.')
    if tasks.is_plan_task(doc):
        raise HTTPException(409, '작업계획서에서 가져온 작업의 원본은 변경할 수 없습니다.')
    await tasks.require_pm_member(user, str(doc['project_id']))
    occurrence = next((o for o in doc['occurrences'] if o['month'] == month), None)
    if not occurrence:
        raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
    issue = await M.get_pm_issues_collection().find_one({'_id': doc['_id']})
    if not issue:
        raise HTTPException(409, '삭제된 이슈에는 작업계획서를 연결할 수 없습니다.')
    live = await tasks.issue_snapshot(issue)
    plans = await selected_plans(entry_ids, occurrence.get('work_plans', []))

    def change(items):
        item = next((o for o in items if o['month'] == month), None)
        if not item:
            raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
        if item['state'] != 'ACTIVE' or (month < tasks.current_month() and tasks.effective_issue(item, live)['status'] == 'DONE'):
            raise HTTPException(409, '지난 점검 기록의 작업계획서 연결은 변경할 수 없습니다.')
        if item.get('work_plans_version', 0) != version:
            raise HTTPException(409, '다른 사용자가 연결을 변경했습니다. 목록을 새로고침한 뒤 다시 선택해 주세요.')
        item['work_plans'] = deepcopy(plans)
        item['work_plans_version'] = version + 1
        item.setdefault('history', []).append({'action': 'work_plans', 'actor': user.id,
                                               'at': datetime.now(timezone.utc)})
    await tasks.mutate(issue_id, str(doc['project_id']), change)
    return {'work_plans': plans, 'work_plans_version': version + 1}
