"""월별 서버 점검. 이슈별 한 문서에 회차를 저장해 이월을 원자적으로 처리한다."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager as M
from app.services.pm.permission import require_pm_member
from app.services.asset_catalog import asset_map, asset_snapshot
from app.utils.mongo import oid

KST = ZoneInfo('Asia/Seoul')
COLLECTION = 'inspection_tasks'


def current_month():
    return datetime.now(KST).strftime('%Y-%m')


def next_month(month):
    d = date.fromisoformat(month + '-01')
    return (d.replace(day=28) + timedelta(days=4)).strftime('%Y-%m')


async def inspection_date(month):
    override = await M.get_ddays_collection().find_one({'title': f'서버 점검일 {month}'}, sort=[('created_at', -1)])
    if override:
        try:
            return date.fromisoformat(override['date'])
        except (ValueError, KeyError):
            pass
    first = date.fromisoformat(month + '-01')
    return first + timedelta(days=(3 - first.weekday()) % 7 + 14)


def collection():
    return M.get_db()[COLLECTION]


def is_plan_task(doc):
    return doc.get('source_type') == 'WORK_PLAN'


def project_scope(projects):
    return {} if projects is None else {'$or': [
        {'project_id': {'$in': projects}}, {'source_type': 'WORK_PLAN'}]}


async def require_task_access(doc, user):
    if is_plan_task(doc):
        if not user.is_admin and 'server_check' not in user.permissions:
            raise HTTPException(403, '서버 점검 메뉴 권한이 필요합니다.')
    else:
        await require_pm_member(user, str(doc['project_id']))


async def accessible_projects(user):
    if user.is_admin:
        return None
    docs = await M.get_pm_project_members_collection().find({'user_id': oid(user.id)}).to_list(None)
    return [d['project_id'] for d in docs]


async def issue_for_user(issue_id, user):
    issue = await M.get_pm_issues_collection().find_one({'_id': oid(issue_id)})
    if not issue:
        raise HTTPException(404, '이슈를 찾을 수 없습니다.')
    await require_pm_member(user, str(issue['project_id']))
    return issue


async def resolve_assets(ids, *, category=None):
    by_id = await asset_map(ids, include_deleted=False, category=category)
    if len(by_id) != len(ids):
        raise HTTPException(422, '삭제되었거나 선택할 수 없는 자산이 포함되어 있습니다.')
    return [by_id[i] for i in ids]


async def issue_snapshot(issue):
    project = await M.get_pm_projects_collection().find_one({'_id': issue['project_id']})
    assignee = await M.get_users_collection().find_one({'_id': issue['assignee_id']}) if issue.get('assignee_id') else None
    return {'id': str(issue['_id']), 'project_id': str(issue['project_id']),
            'key': f"{(project or {}).get('key', '')}-{issue['number']}",
            'title': issue['title'], 'status': issue['status'],
            'assignee_id': str(issue['assignee_id']) if issue.get('assignee_id') else None,
            'assignee_name': (assignee or {}).get('full_name') or (assignee or {}).get('email') or '미배정'}


def effective_issue(occurrence, live):
    if occurrence['state'] != 'ACTIVE':
        return occurrence.get('issue_snapshot') or live
    if occurrence['month'] < current_month() and occurrence.get('completed_snapshot'):
        return occurrence['completed_snapshot']
    return live


async def mutate(issue_id, project_id, transform, *, source=None, expected_version=None):
    """회차 변경 전체를 CAS 저장. 중복 등록과 동시 이월에도 문서를 쪼개지 않는다."""
    col = collection()
    for _ in range(5):
        doc = await col.find_one({'_id': oid(issue_id)})
        if doc and source and any(doc.get(k) != v for k, v in source.items()):
            raise HTTPException(409, '작업 등록 정보가 일치하지 않습니다.')
        if expected_version is not None and (not doc or doc['version'] != expected_version):
            raise HTTPException(409, '다른 사용자가 점검 작업을 변경했습니다. 다시 열어 확인해 주세요.')
        items = deepcopy(doc['occurrences']) if doc else []
        transform(items)
        now = datetime.now(timezone.utc)
        if doc:
            result = await col.update_one({'_id': doc['_id'], 'version': doc['version']},
                {'$set': {'occurrences': items, 'updated_at': now}, '$inc': {'version': 1}})
            if result.matched_count:
                return
        else:
            try:
                await col.insert_one({'_id': oid(issue_id), 'project_id': oid(project_id) if project_id else None,
                                     'occurrences': items, 'version': 1, 'updated_at': now, **(source or {})})
                return
            except DuplicateKeyError:
                continue
    raise HTTPException(409, '다른 사용자가 변경했습니다. 새로고침 후 다시 시도해 주세요.')


async def save_result(doc, month, values, user):
    """Save a shared occurrence result after the caller checks its access boundary."""
    links = None
    if values.get('work_result_ids') is not None:
        from app.services.work_document_assets import require_job
        from app.services.inspection_work_plans import selected_documents
        require_job(user)
        occurrence = next((o for o in doc['occurrences'] if o['month'] == month), {})
        links = await selected_documents(values['work_result_ids'],
            (occurrence.get('result') or {}).get('work_results', []), kind='RESULT')
    result = {'content': values['content'].strip(), 'follow_up': values['follow_up'].strip(),
              'performed_on': values['performed_on'], 'version': values['version'] + 1,
              'updated_at': datetime.now(timezone.utc),
              'updated_by': user.full_name or user.email, 'updated_by_id': user.id}

    def change(items):
        item = next((o for o in items if o['month'] == month), None)
        if not item:
            raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
        if (item.get('result') or {}).get('version', 0) != values['version']:
            raise HTTPException(409, '다른 사용자가 결과를 변경했습니다. 작성 내용을 복사한 뒤 최신 결과를 확인해 주세요.')
        result['work_results'] = deepcopy(links if links is not None else (item.get('result') or {}).get('work_results', []))
        item['result'] = result

    await mutate(str(doc['_id']), doc.get('project_id'), change)
    return result


async def register(issue, month, assets, common, user, work_plans=None):
    snapshot = await issue_snapshot(issue)
    def change(items):
        previous = next((o for o in items if o['month'] == month), None)
        if previous and previous['state'] != 'EXCLUDED':
            raise HTTPException(409, '해당 월에 이미 연결된 이슈입니다. 기존 작업을 확인해 주세요.')
        item = {'month': month, 'assets': assets, 'common': common, 'state': 'ACTIVE',
                'issue_snapshot': snapshot, 'reason': '', 'created_by': user.id,
                'created_at': datetime.now(timezone.utc), 'history': []}
        if issue['status'] == 'DONE':
            item['completed_snapshot'] = snapshot
        if previous:
            if previous.get('result'):
                item['result'] = deepcopy(previous['result'])
            item['work_plans'] = deepcopy(previous.get('work_plans', []))
            item['work_plans_version'] = previous.get('work_plans_version', 0)
            item['history'] = previous.get('history', []) + [
                {'action': 'reconnect', 'actor': user.id, 'at': datetime.now(timezone.utc)}]
            items.remove(previous)
        if work_plans is not None:
            item['work_plans'] = deepcopy(work_plans)
            item['work_plans_version'] = item.get('work_plans_version', 0) + 1
        items.append(item)
    await mutate(str(issue['_id']), str(issue['project_id']), change)


async def list_tasks(user, month, include_overdue=True, issue_id=None, asset_id=None, all_months=False, work_plan_id=None, work_result_id=None):
    projects = await accessible_projects(user)
    query = project_scope(projects)
    if issue_id:
        query['_id'] = oid(issue_id)
    if asset_id:
        query['occurrences.assets.id'] = asset_id
    if work_plan_id:
        query['$and'] = [{'$or': [{'work_plan_id': work_plan_id}, {'occurrences.work_plans.id': work_plan_id}]}]
    if work_result_id:
        query['occurrences.result.work_results.id'] = work_result_id
    docs = await collection().find(query).to_list(None)
    result = await hydrate_tasks(docs, month, include_overdue, asset_id, all_months, work_plan_id, work_result_id)
    return sorted(result, key=lambda x: (not x['overdue'], x['month'], x['issue']['title']))


async def hydrate_tasks(docs, month, include_overdue=True, asset_id=None, all_months=False, work_plan_id=None, work_result_id=None):
    """Resolve a batch of occurrences consistently for monthly tasks and asset history."""
    if not docs:
        return []
    issues = await M.get_pm_issues_collection().find({'_id': {'$in': [d['_id'] for d in docs if not is_plan_task(d)]}}).to_list(None)
    live_issues = {d['_id']: d for d in issues}
    snapshots = {issue_id: await issue_snapshot(issue) for issue_id, issue in live_issues.items()}
    asset_ids = {a['id'] for d in docs for o in d['occurrences'] for a in o['assets']}
    current_assets = await asset_map(asset_ids)
    from app.services.inspection_work_plans import plan_map
    from app.services.inspection_plan_tasks import display_snapshot
    plans = await plan_map({d['work_plan_id'] for d in docs if is_plan_task(d)})
    assignee_ids = {o['issue_snapshot'].get('assignee_id') for d in docs if is_plan_task(d) for o in d['occurrences']}
    users = {str(u['_id']): u for u in await M.get_users_collection().find(
        {'_id': {'$in': [oid(i) for i in assignee_ids if i]}}).to_list(None)}
    result = []
    for doc in docs:
        live = live_issues.get(doc['_id'])
        snapshot = snapshots.get(doc['_id'])
        for occurrence in doc['occurrences']:
            o = deepcopy(occurrence)
            plan = plans.get(doc.get('work_plan_id')) if is_plan_task(doc) else None
            current = display_snapshot(o, plan, users) if is_plan_task(doc) else snapshot
            info = effective_issue(o, current or o.get('completed_snapshot') or o['issue_snapshot'])
            overdue = o['month'] < month and o['state'] == 'ACTIVE' and info['status'] != 'DONE'
            if not all_months and o['month'] != month and not (include_overdue and overdue):
                continue
            if asset_id and not any(a['id'] == asset_id for a in o['assets']):
                continue
            if work_plan_id and doc.get('work_plan_id') != work_plan_id and not any(p['id'] == work_plan_id for p in o.get('work_plans', [])):
                continue
            if work_result_id and not any(ref['id'] == work_result_id for ref in (o.get('result') or {}).get('work_results', [])):
                continue
            for a in o['assets']:
                current = current_assets.get(a['id'])
                a['current'] = current
                a['is_deleted'] = not current or current['is_deleted']
            row = {**o, 'issue': info, 'issue_id': str(doc['_id']), 'task_version': doc['version'],
                   'source_type': 'WORK_PLAN' if is_plan_task(doc) else 'ISSUE',
                   'issue_deleted': plan is None if is_plan_task(doc) else live is None, 'overdue': overdue}
            if is_plan_task(doc):
                row['work_plan'] = {**deepcopy(o['work_plan_snapshot']), 'current': deepcopy(plan), 'unavailable': plan is None}
            result.append(row)
    from app.services.inspection_work_plans import hydrate_plans, hydrate_results
    await hydrate_plans(result)
    await hydrate_results(result)
    return result


async def change_occurrence(issue_id, month, action, reason, user, assets=None, common=False):
    doc = await collection().find_one({'_id': oid(issue_id)})
    if not doc:
        raise HTTPException(404, '점검 작업을 찾을 수 없습니다.')
    await require_task_access(doc, user)
    if is_plan_task(doc):
        from app.services.inspection_work_plans import plan_map
        live = (await plan_map([doc['work_plan_id']])).get(doc['work_plan_id'])
        snapshot = None
    else:
        live = await M.get_pm_issues_collection().find_one({'_id': doc['_id']})
        snapshot = await issue_snapshot(live) if live else None
    target = max(next_month(month), current_month())
    target_date = (await inspection_date(target)).isoformat() if action == 'rollover' and is_plan_task(doc) else None
    def change(items):
        item = next((o for o in items if o['month'] == month), None)
        if not item:
            raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
        if item['state'] != 'ACTIVE':
            raise HTTPException(409, '이미 이월 또는 제외된 작업입니다.')
        current = {**item['issue_snapshot'], 'title': live['title']} if is_plan_task(doc) and live else snapshot
        info = effective_issue(item, current or item['issue_snapshot'])
        if action == 'rollover':
            if not live:
                raise HTTPException(409, '원본이 삭제된 작업은 이월할 수 없습니다.')
            if info['status'] == 'DONE':
                raise HTTPException(409, '완료된 작업은 이월할 수 없습니다.')
            if any(o['month'] == target for o in items):
                raise HTTPException(409, '이월할 월에 이미 같은 작업이 등록되어 있습니다.')
            items.append({'month': target, 'assets': deepcopy(item['assets']), 'common': item['common'],
                          'work_plans': deepcopy(item.get('work_plans', [])), 'work_plans_version': 0,
                          'state': 'ACTIVE', 'issue_snapshot': info if is_plan_task(doc) else snapshot, 'from_month': month,
                          'reason': reason, 'created_by': user.id, 'created_at': datetime.now(timezone.utc), 'history': []})
            if is_plan_task(doc):
                items[-1].update(work_plan_snapshot=deepcopy(live), planned_on=target_date)
            item.update(state='ROLLED', to_month=target, issue_snapshot=info, reason=reason)
        elif action == 'exclude':
            item.update(state='EXCLUDED', issue_snapshot=info, reason=reason)
        elif action == 'targets':
            if month < current_month() and info['status'] == 'DONE':
                raise HTTPException(409, '지난달 완료 작업의 대상은 변경할 수 없습니다.')
            item.update(assets=assets, common=common)
        if is_plan_task(doc) and live and action in ('rollover', 'exclude'):
            item['work_plan_snapshot'] = deepcopy(live)
        item.setdefault('history', []).append({'action': action, 'reason': reason, 'actor': user.id,
                                               'at': datetime.now(timezone.utc)})
    await mutate(issue_id, doc.get('project_id'), change)


async def capture_completion(issue):
    """이슈가 다시 열려도 지난달 완료 기록을 보존한다."""
    doc = await collection().find_one({'_id': issue['_id']})
    if not doc:
        return
    snapshot = await issue_snapshot(issue)
    def change(items):
        for o in items:
            if o['state'] != 'ACTIVE':
                continue
            if issue['status'] == 'DONE' and not o.get('completed_snapshot'):
                o['completed_snapshot'] = snapshot
            elif issue['status'] != 'DONE' and o['month'] >= current_month():
                o.pop('completed_snapshot', None)
    await mutate(str(issue['_id']), str(issue['project_id']), change)
