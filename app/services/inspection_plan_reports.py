"""Planning documents use registered targets and tasks, never measured results."""
from copy import deepcopy

from app.services import monthly_inspection_reports as reports
from app.services import inspection_service as tasks
from app.db.mongo import MongoClientManager as M
from app.utils.mongo import oid

DEFAULT_CHECKS = 'CPU·메모리·디스크 사용량 확인\n서비스 동작 상태 확인\n로그 및 운영 중 이상 유무 확인'


async def planning_snapshot(body, projects=None):
    projects = await reports.report_projects(body.project_ids) if projects is None else projects
    rows = await reports.task_snapshot(body.month, [p['id'] for p in projects])
    current = [t for t in rows if t['month'] == body.month and t['state'] == 'ACTIVE']
    for task in current:
        task.pop('result', None)
        task.pop('completed_snapshot', None)
    config = await M.get_db()[M.APP_SETTINGS].find_one({'_id': 'inspection_resource_targets'}) or {}
    ids = config.get('asset_ids', [])
    assets = await M.get_assets_servers_collection().find({'_id': {'$in': [oid(i) for i in ids]}}).to_list(None)
    by_id = {str(a['_id']): tasks.asset_snapshot(a) for a in assets}
    targets = [by_id.get(i) or {'id': i, 'name': '삭제된 자산', 'ip': '', 'asset_name': '',
                              'status': '', 'is_deleted': True} for i in ids]
    warnings = [
        ('unassigned', '담당자가 정해지지 않은 작업', sum(not t['issue'].get('assignee_id') for t in current)),
        ('deleted_targets', '삭제된 정기 점검 대상 서버', sum(bool(a.get('is_deleted')) for a in targets)),
    ]
    data = reports.clean({
        'source': None, 'comparison': None, 'captured_at': reports.now(),
        'historical_reconstruction': body.month < tasks.current_month(),
        'thresholds': {'warning': 80, 'danger': 90, 'version': 1},
        'servers': [], 'resource_targets': targets, 'tasks': current, 'carryover': [],
        'missing_asset_resources': [], 'unmatched_actions': [],
        'warnings': [{'code': code, 'label': label, 'count': count} for code, label, count in warnings if count],
        'stats': {'planned': len(current), 'servers': len(targets), 'done': 0, 'pending': 0,
                  'rolled': 0, 'excluded': 0, 'warning': 0, 'danger': 0,
                  'missing_resources': 0, 'completion_rate': None},
    })
    reports.size_guard(data)
    return projects, data


async def initial_participants(doc):
    ids = sorted({t['issue']['assignee_id'] for t in doc['snapshot']['tasks'] if t['issue'].get('assignee_id')})
    users = await M.get_users_collection().find({
        '_id': {'$in': [oid(i) for i in ids]}, 'is_blocked': {'$ne': True}, 'is_deleted': {'$ne': True},
    }).sort([('full_name', 1), ('_id', 1)]).limit(100).to_list(100)
    return [{
        'user_id': str(user['_id']), 'name': user.get('full_name') or user.get('email') or '이름 없음',
        'team': user.get('team') or '', 'roles': [{'value': 'WORK_EXECUTION', 'label': '작업 수행'}],
        'work_summary': '', 'tasks': [], 'assigned_tasks': reports.assigned_participant_tasks(doc, str(user['_id'])),
    } for user in users]


async def linked_plan(month, previous_snapshot):
    # Once selected, keep the exact submitted revision even when a newer plan appears.
    if previous_snapshot and previous_snapshot.get('plan'):
        return deepcopy(previous_snapshot['plan'])
    plan = await M.get_db()[reports.REPORTS].find_one(
        {'month': month, 'kind': 'PLAN', 'state': 'FINAL'},
        sort=[('finalized_at', -1), ('revision', -1), ('_id', -1)],
    )
    if not plan:
        return None
    return reports.clean({
        'id': str(plan['_id']), 'title': plan['title'], 'month': month, 'revision': plan['revision'],
        'inspection_date': plan['inspection_date'], 'planned_time': plan.get('planned_time', ''),
        'finalized_at': plan['finalized_at'], 'purpose': plan['purpose'],
        'participants': deepcopy(plan.get('participants', [])),
        'resource_targets': deepcopy(plan['snapshot'].get('resource_targets', [])),
        'resource_checks': plan.get('resource_checks', ''), 'tasks': deepcopy(plan['snapshot']['tasks']),
    })
