"""Versioned monthly reports. Source data is copied, never dereferenced for final reports."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import ipaddress
import math
import re

from bson import BSON, ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager as M
from app.services import inspection_service as tasks
from app.utils.mongo import oid

REPORTS = 'monthly_inspection_reports'
PREVIEWS = 'monthly_inspection_report_previews'
MAPPINGS = 'inspection_asset_mappings'  # Legacy records are retained but no longer used.
PARTICIPANT_ROLES = {
    'LEAD': '점검 총괄',
    'RESOURCE_CHECK': '서버·자원 점검',
    'WORK_EXECUTION': '작업 수행',
    'SERVICE_CHECK': '서비스 확인',
    'REVIEW': '결과 검토',
    'OTHER': '기타',
}


async def participant_options(search):
    query = {'is_blocked': {'$ne': True}, 'is_deleted': {'$ne': True}}
    if search.strip():
        pattern = {'$regex': re.escape(search.strip()), '$options': 'i'}
        query['$or'] = [{field: pattern} for field in ('full_name', 'email', 'team')]
    docs = await M.get_users_collection().find(query, {'full_name': 1, 'email': 1, 'team': 1}).sort([('full_name', 1), ('_id', 1)]).limit(50).to_list(50)
    return {'users': [{'id': str(d['_id']), 'name': d.get('full_name') or d.get('email') or '이름 없음',
                       'email': d.get('email') or '', 'team': d.get('team') or ''} for d in docs],
            'roles': [{'value': value, 'label': label} for value, label in PARTICIPANT_ROLES.items()]}


def assigned_participant_tasks(doc, user_id):
    """Use this report's captured assignments, never live issues or display names."""
    linked = {}
    for task in doc['snapshot']['tasks']:
        issue = task['issue']
        if (task['month'] == doc['month'] and task['state'] == 'ACTIVE'
                and issue.get('assignee_id') == user_id):
            linked[task['issue_id']] = {
                'issue_id': task['issue_id'], 'month': task['month'],
                'key': issue['key'], 'title': issue['title'],
            }
    return list(linked.values())


def sync_participant_assignments(doc):
    # Manual links and prose are independent, including links retained from older snapshots.
    return [{**person, 'assigned_tasks': assigned_participant_tasks(doc, person['user_id'])}
            for person in doc.get('participants', [])]


async def resolve_participants(doc, values):
    """Keep historical identities; validate every new person and task against canonical data."""
    previous = {p['user_id']: p for p in doc.get('participants', [])}
    ids = [oid(p.user_id) for p in values if p.user_id not in previous]
    users = await M.get_users_collection().find({'_id': {'$in': ids}, 'is_blocked': {'$ne': True}, 'is_deleted': {'$ne': True}},
                                               {'full_name': 1, 'email': 1, 'team': 1}).to_list(None)
    users_by_id = {str(u['_id']): u for u in users}
    available_tasks = {t['issue_id']: t for t in doc['snapshot']['tasks']}
    result = []
    for value in values:
        old = previous.get(value.user_id)
        user = users_by_id.get(value.user_id)
        if not old and not user:
            raise HTTPException(422, '선택한 참여자가 삭제되었거나 이용이 제한된 사용자입니다. 참여자를 다시 선택해 주세요.')
        # Allow retaining a previously recorded link if a later refresh removed the source task.
        old_tasks = {t['issue_id']: t for t in (old or {}).get('tasks', [])}
        linked = []
        for issue_id in value.issue_ids:
            task = available_tasks.get(issue_id)
            if task:
                linked.append({'issue_id': issue_id, 'month': task['month'], 'key': task['issue']['key'], 'title': task['issue']['title']})
            elif issue_id in old_tasks:
                linked.append(deepcopy(old_tasks[issue_id]))
            else:
                raise HTTPException(422, '보고서에 포함된 월간 작업만 연결할 수 있습니다. 작업 목록을 확인해 주세요.')
        result.append({'user_id': value.user_id,
                       'name': old['name'] if old else user.get('full_name') or user.get('email') or '이름 없음',
                       'team': old.get('team', '') if old else user.get('team') or '',
                       'roles': [{'value': r, 'label': PARTICIPANT_ROLES[r]} for r in value.roles],
                       'work_summary': value.work_summary.strip(), 'tasks': linked,
                       'assigned_tasks': assigned_participant_tasks(doc, value.user_id)})
    return result


def now():
    return datetime.now(timezone.utc)


def clean(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
    if isinstance(value, dict):
        return {('id' if k == '_id' else k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


async def indexes():
    col = M.get_db()[REPORTS]
    await col.create_index([('month', 1), ('scope_key', 1), ('revision', 1)], unique=True)
    await col.create_index('create_key', unique=True, sparse=True)
    await col.create_index('parent_id', unique=True, partialFilterExpression={'parent_id': {'$type': 'string'}})
    await M.get_db()[PREVIEWS].create_index('expires_at', expireAfterSeconds=0)


async def report_projects(ids=None):
    """Project IDs describe report contents, not who may access the report."""
    docs = await M.get_pm_projects_collection().find({}).sort('name', 1).to_list(None)
    available = {str(d['_id']): d for d in docs}
    selected = list(available) if ids is None else sorted(set(ids))
    if any(i not in available for i in selected):
        raise HTTPException(422, '존재하지 않는 프로젝트가 포함되어 있습니다.')
    return [{'id': i, 'key': available[i].get('key', ''), 'name': available[i].get('name', '')} for i in selected]


def report_notes(doc):
    """Expose legacy prose as one editable item without rewriting stored reports."""
    if doc.get('additional_notes'):
        return deepcopy(doc['additional_notes'])
    content = doc.get('limitations') or ''
    return [{'id': 'legacy', 'content': content}] if content.strip() else []


async def get_report(report_id, user):
    if not user.is_admin and 'server_check' not in user.permissions:
        raise HTTPException(403, '서버 점검 메뉴 권한이 필요합니다.')
    doc = await M.get_db()[REPORTS].find_one({'_id': oid(report_id)})
    if not doc:
        raise HTTPException(404, '점검 보고서를 찾을 수 없습니다.')
    if doc['state'] == 'DRAFT':
        doc['participants'] = sync_participant_assignments(doc)
    doc.setdefault('kind', 'RESULT')
    doc['additional_notes'] = report_notes(doc)
    return doc


def require_result(doc):
    if doc.get('kind') == 'PLAN':
        raise HTTPException(422, '작업 결과와 조치 내역은 점검 결과서에서 작성해 주세요.')


async def report_task(report, issue_id, month):
    require_result(report)
    canonical_id = str(oid(issue_id))
    included = report['snapshot']['tasks'] + report['snapshot']['carryover']
    if not any(t['issue_id'] == canonical_id and t['month'] == month for t in included):
        raise HTTPException(404, '보고서에 포함된 점검 작업이 아닙니다.')
    doc = await tasks.collection().find_one({'_id': oid(canonical_id)})
    if not doc or not any(o['month'] == month for o in doc['occurrences']):
        raise HTTPException(404, '해당 월의 점검 작업을 찾을 수 없습니다.')
    return doc


def draft_version(doc, version):
    if doc['state'] != 'DRAFT':
        raise HTTPException(409, '확정된 보고서는 수정할 수 없습니다. 수정본을 작성해 주세요.')
    if doc['version'] != version:
        raise HTTPException(409, '다른 사용자가 보고서를 변경했습니다. 작성 내용은 유지됩니다. 최신 보고서를 확인해 주세요.')


def size_guard(value):
    if len(BSON.encode(value)) > 12 * 1024 * 1024:
        raise HTTPException(422, '보고서에 포함된 데이터가 너무 큽니다. 첨부 이미지의 크기나 개수를 줄인 뒤 다시 불러와 주세요.')


def pct(value):
    """Preserve zero and missing; source Excel stores ratios as well as percent strings."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(',', '')
    if not text or text.lower() in ('-', 'n/a', 'na', 'none', 'null'):
        return None
    try:
        number = float(text.rstrip('%').strip())
    except ValueError:
        return None
    if '%' not in text and 0 < number <= 1:
        number *= 100
    return round(number, 2) if math.isfinite(number) and 0 <= number <= 100 else None


def metric(detail, fallback):
    # Legacy Excel field names are retained by the importer. They represent the
    # source of a single monthly reading here, not a before/after comparison.
    before = pct((detail or {}).get('before_pct'))
    after = pct((detail or {}).get('after_pct'))
    value, basis = (after if after is not None else before), '측정값'
    if value is None:
        value, basis = pct(fallback), '요약 수치'
    return {'value': value, 'basis': basis, 'delta': None}


def disk_metric(detail, summary):
    disks = [(str(d.get('filesystem') or '').strip(), pct(d.get('pct'))) for d in detail.get('disks', [])]
    actual = [(p, v) for p, v in disks if p and p.lower() != 'total' and v is not None]
    if actual:
        path, value = max(actual, key=lambda pair: pair[1])
        basis = '파일시스템 최대'
    elif pct(summary.get('disk_max')) is not None:
        path, value, basis = '', pct(summary.get('disk_max')), '요약 수치'
    else:
        path, value = next(((p, v) for p, v in disks if p.lower() == 'total' and v is not None), ('', None))
        basis = 'Total' if value is not None else '자료 없음'
    return {'value': value, 'path': path, 'basis': basis, 'delta': None}


def host(value):
    return str(value or '').strip().lower().rstrip('.')


def ips(value):
    result = set()
    for part in re.split(r'[,;\s/]+', str(value or '')):
        try:
            result.add(str(ipaddress.ip_address(part)))
        except ValueError:
            pass
    return tuple(sorted(result))


def identity(row):
    return host(row.get('host_name')), ips(row.get('ip'))


def connect_resource_assets(rows, assets):
    """The asset hostname is canonical. IPs only suggest where to correct a mismatch."""
    by_host = {}
    for asset in assets:
        name = host(asset.get('name'))
        if name:
            by_host.setdefault(name, []).append(asset)
    counts = Counter(host(row['host_name']) for row in rows if not row['hostname_missing'])
    for row in rows:
        name = host(row['host_name'])
        matches = by_host.get(name, []) if not row['hostname_missing'] else []
        row.update(asset=None, candidate=None, mapping_state='unmatched', mapping_issue=None)
        if not row['hostname_missing'] and (len(matches) > 1 or counts[name] > 1):
            row.update(mapping_state='ambiguous', mapping_issue='ambiguous_hostname')
        elif len(matches) == 1:
            row.update(asset=tasks.asset_snapshot(matches[0]), mapping_state='automatic')
        else:
            row_ips = set(ips(row['ip']))
            same_ip = [a for a in assets if row_ips.intersection(ips(a.get('ip')))] if row_ips else []
            if len(same_ip) == 1:
                row['candidate'] = tasks.asset_snapshot(same_ip[0])
            row['mapping_issue'] = ('missing_hostname' if row['hostname_missing'] else
                                    'hostname_mismatch' if row['candidate'] else 'asset_not_found')


def no_finding(value):
    return str(value or '').strip().lower() in ('', '-', '없음', '정상', '양호', 'ok', 'n/a', 'na', 'none', '0', '이상없음', '이상 없음', 'false')


def checked(value):
    return str(value or '').strip().lower() not in ('', '-', 'false', '0', 'no', 'none', 'n/a', 'na', '☐', '□')


def resource_rows(source):
    if not source:
        return []
    summaries = source.get('summary') or []
    details = source.get('servers') or []
    used, paired = set(), []
    for summary in summaries:
        exact = [i for i, d in enumerate(details) if i not in used and identity(d) == identity(summary)]
        candidates = exact or [i for i, d in enumerate(details) if i not in used
                              and host(d.get('host_name')) == host(summary.get('host_name'))
                              and (not ips(d.get('ip')) or not ips(summary.get('ip')))]
        # A repeated hostname cannot safely merge two records by name alone.
        unique_summary = sum(host(s.get('host_name')) == host(summary.get('host_name')) for s in summaries) == 1
        chosen = candidates[0] if len(candidates) == 1 and (exact or unique_summary) else None
        if chosen is not None:
            used.add(chosen)
        paired.append((summary, details[chosen] if chosen is not None else {}))
    paired.extend(({}, detail) for i, detail in enumerate(details) if i not in used)
    rows, keys = [], Counter()
    for summary, detail in paired:
        name = detail.get('host_name') or summary.get('host_name') or '이름 없음'
        ip = detail.get('ip') or summary.get('ip') or ''
        signature = hashlib.sha256(repr((host(name), ips(ip))).encode()).hexdigest()[:24]
        keys[signature] += 1
        cpu, ram, disk = metric(detail.get('cpu'), summary.get('cpu')), metric(detail.get('ram'), summary.get('ram')), disk_metric(detail, summary)
        findings = []
        for label, m in (('CPU', cpu), ('RAM', ram), ('디스크', disk)):
            if m['value'] is not None and m['value'] >= 80:
                findings.append({'label': f"{label} {m['value']:g}%", 'level': 'danger' if m['value'] >= 90 else 'warning'})
        for check in detail.get('hw_checks', []):
            if checked(check.get('ng')):
                findings.append({'label': f"H/W · {check.get('item', '')}", 'level': 'danger'})
        for check in detail.get('security_checks', []):
            value = str(check.get('result') or '')
            if any(term in value.lower() for term in ('ng', 'fail', '불량', '오류', '미확인', '취약', '비정상')):
                findings.append({'label': f"보안 · {check.get('item', '')}: {value}", 'level': 'warning'})
        for service in detail.get('services', []):
            if any(term in str(service).lower() for term in ('fail', '오류', '미확인', '비정상', '중지', '중단', 'inactive', 'down')):
                findings.append({'label': f'서비스 · {service}', 'level': 'warning'})
        if not no_finding(summary.get('log_errors')):
            findings.append({'label': '로그 · ' + str(summary['log_errors']), 'level': 'warning'})
        rows.append({'key': f'{signature}-{keys[signature]}', 'identity_key': signature,
                     'host_name': name, 'hostname_missing': not host(detail.get('host_name') or summary.get('host_name')),
                     'server_name': detail.get('server_name') or '', 'ip': ip,
                     'cpu': cpu, 'ram': ram, 'disk': disk, 'findings': findings,
                     'level': 'danger' if any(f['level'] == 'danger' for f in findings) else 'warning' if findings else 'none',
                     'log_errors': summary.get('log_errors') or '', 'action_items': summary.get('action_items') or '',
                     'detail': detail, 'asset': None, 'candidate': None, 'mapping_state': 'unconfirmed', 'action': None})
    return rows


def source_info(source):
    if not source:
        return None
    return {'id': str(source['_id']), 'report_date': source.get('report_date', ''),
            'title': source.get('report_title') or '자원 점검 데이터',
            'uploaded_at': clean(source.get('uploaded_at')), 'uploaded_by': source.get('uploaded_by', '')}


async def source_doc(source_id, month=None, before=None):
    if not source_id:
        return None
    doc = await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': oid(source_id)})
    if not doc:
        raise HTTPException(422, '점검 데이터가 삭제되었습니다. 다시 불러와 주세요.')
    source_date = str(doc.get('report_date') or '')
    try:
        date.fromisoformat(source_date)
    except ValueError:
        raise HTTPException(422, '점검일 형식이 올바르지 않습니다. 업로드한 Excel 파일을 확인해 주세요.')
    if month and not source_date.startswith(month + '-'):
        raise HTTPException(422, '보고서와 같은 월의 점검 데이터만 선택할 수 있습니다.')
    if before and source_date >= before:
        raise HTTPException(422, '비교할 데이터의 점검일은 보고서에 사용할 데이터보다 앞서야 합니다.')
    return doc


async def latest_source(month):
    """Choose by inspection date, then upload time; never fall back to another month."""
    doc = await M.get_db()[M.HEALTH_REPORTS].find_one(
        {'report_date': {'$gte': month + '-01', '$lt': tasks.next_month(month) + '-01'}},
        {'_id': 1}, sort=[('report_date', -1), ('uploaded_at', -1), ('_id', -1)])
    return await source_doc(str(doc['_id']), month) if doc else None


def has_task_result(task):
    result = task.get('result') or {}
    return bool(result.get('content', '').strip() or any(
        not ref.get('unavailable') and not ref.get('is_deleted') for ref in result.get('work_results', [])))


def update_stats(snapshot):
    ts, servers = snapshot['tasks'], snapshot['servers']
    counts = Counter('rolled' if t['state'] == 'ROLLED' else 'excluded' if t['state'] == 'EXCLUDED' else
                     'done' if t['issue']['status'] == 'DONE' else 'pending' for t in ts)
    denominator = len(ts) - counts['excluded']
    snapshot['stats'] = {'planned': len(ts), **{key: counts[key] for key in ('done', 'pending', 'rolled', 'excluded')},
                         'completion_rate': round(counts['done'] / denominator * 100) if denominator else None,
                         'servers': len(servers), 'warning': sum(s['level'] == 'warning' for s in servers),
                         'danger': sum(s['level'] == 'danger' for s in servers),
                         'missing_resources': len(snapshot['missing_asset_resources'])}
    warning_counts = [
        ('no_source', '선택한 월의 점검 데이터 없음', int(snapshot['source'] is None)),
        ('unmapped', '자산 연결 확인 필요', sum(s['asset'] is None for s in servers)),
        ('missing_metrics', '측정값이 없는 서버', sum(any(s[k]['value'] is None for k in ('cpu', 'ram', 'disk')) for s in servers)),
        ('missing_resources', '점검 데이터가 없는 작업 대상 서버', len(snapshot['missing_asset_resources'])),
        ('missing_result', '완료했으나 결과를 작성하지 않은 작업', sum(t['state'] == 'ACTIVE' and t['issue']['status'] == 'DONE' and not has_task_result(t) for t in ts)),
        ('pending', '미완료 또는 이월한 작업', counts['pending'] + counts['rolled']),
        ('ambiguous_actions', '대상 서버를 확인할 수 없는 조치 내역', len(snapshot.get('unmatched_actions', []))),
    ]
    snapshot['warnings'] = [{'code': k, 'label': label, 'count': count} for k, label, count in warning_counts if count]


async def resource_snapshot(source, comparison=None, include_images=True, mappings_input=(), fallback_snapshot=None):
    rows, previous = resource_rows(source), resource_rows(comparison)
    prev_counts = Counter(s['identity_key'] for s in previous)
    counts = Counter(s['identity_key'] for s in rows)
    prev_by = {s['identity_key']: s for s in previous if prev_counts[s['identity_key']] == 1}
    assets = await M.get_assets_servers_collection().find({'is_deleted': {'$ne': True}}).to_list(None)
    connect_resource_assets(rows, assets)
    # Exceptions belong only to this request or this report's existing source snapshot.
    # Never read or write reusable aliases, and never transfer an exception to another source.
    asset_by = {str(a['_id']): tasks.asset_snapshot(a) for a in assets}
    if fallback_snapshot and (fallback_snapshot.get('source') or {}).get('id') == str((source or {}).get('_id')):
        saved = {r['key']: r['asset']['id'] for r in fallback_snapshot.get('servers', [])
                 if r.get('mapping_state') == 'manual' and r.get('asset') and r['asset']['id'] in asset_by}
    else:
        saved = {}
    keys = {row['key'] for row in rows}
    explicit = {m.row_key: m.asset_id for m in mappings_input}
    if len(explicit) != len(mappings_input):
        raise HTTPException(422, '같은 점검 항목을 중복 연결할 수 없습니다.')
    if explicit.keys() - keys:
        raise HTTPException(422, '점검 데이터가 변경되었습니다. 다시 불러와 주세요.')
    for row in rows:
        if row['mapping_state'] == 'automatic':
            continue
        chosen = explicit.get(row['key'], saved.get(row['key']))
        if chosen is not None:
            if chosen not in asset_by:
                raise HTTPException(422, '삭제되었거나 존재하지 않는 자산입니다. 연결 자산을 다시 선택해 주세요.')
            row.update(asset=asset_by[chosen], mapping_state='manual')
    actions = await M.get_db()[M.HEALTH_ACTIONS].find({'report_id': str(source['_id'])}).to_list(None) if source else []
    action_by = {host(a['host_name']): a for a in actions}
    host_counts = Counter(host(r['host_name']) for r in rows)
    matched_action_hosts = set()
    for row in rows:
        old = prev_by.get(row['identity_key']) if counts[row['identity_key']] == 1 and ips(row['ip']) else None
        if old:
            for kind in ('cpu', 'ram', 'disk'):
                a, b = row[kind], old[kind]
                if a['value'] is not None and b['value'] is not None and a['basis'] == b['basis'] and a.get('path') == b.get('path'):
                    a['delta'] = round(a['value'] - b['value'], 2)
        action = action_by.get(host(row['host_name']))
        if action and host_counts[host(row['host_name'])] == 1:
            row['action'] = clean(action)
            row['action']['images'] = [s for s in action.get('images', []) if include_images and re.match(r'^data:image/(png|jpeg|jpg|gif|webp);base64,', s)]
            matched_action_hosts.add(host(row['host_name']))
    unmatched_actions = [clean(a) for a in actions if host(a['host_name']) not in matched_action_hosts]
    for action in unmatched_actions:
        action['images'] = [s for s in action.get('images', []) if include_images and re.match(r'^data:image/(png|jpeg|jpg|gif|webp);base64,', s)]
    return rows, unmatched_actions


async def task_snapshot(month, ids):
    task_docs = await tasks.collection().find(tasks.project_scope([oid(i) for i in ids])).to_list(None)
    all_tasks = sorted(await tasks.hydrate_tasks(task_docs, month),
                       key=lambda t: (not t['overdue'], t['month'], t['issue']['title']))
    live = {str(i['_id']): i for i in await M.get_pm_issues_collection().find({'_id': {'$in': [oid(t['issue_id']) for t in all_tasks]}}).to_list(None)}
    for t in all_tasks:
        issue = live.get(t['issue_id'], {})
        t['planned_start'] = t.get('planned_on') if tasks.is_plan_task(t) else clean(issue.get('start_date'))
        t['planned_end'] = t.get('planned_on') if tasks.is_plan_task(t) else clean(issue.get('due_date'))
        # Hydration includes current asset data; copy the selected period's visible identity.
        t['assets'] = [deepcopy(a if month < tasks.current_month() or t['state'] != 'ACTIVE' else a.get('current') or a) for a in t['assets']]
        for a in t['assets']:
            a.pop('current', None)
        t['work_plans'] = [deepcopy(p if month < tasks.current_month() or t['state'] != 'ACTIVE' else p.get('current') or p)
                           for p in t.get('work_plans', [])]
        for plan in t['work_plans']:
            plan.pop('current', None)
        if t.get('work_plan'):
            plan = t['work_plan']
            historical = t['state'] != 'ACTIVE' or (t['month'] < tasks.current_month() and t.get('completed_snapshot'))
            t['work_plan'] = deepcopy(plan if historical else plan.get('current') or plan)
            t['work_plan'].pop('current', None)
        t.pop('history', None)
    from app.services.inspection_work_plans import freeze_results
    freeze_results(all_tasks)
    return all_tasks


async def snapshot(body, projects=None, previous_snapshot=None):
    projects = await report_projects(body.project_ids) if projects is None else projects
    ids = [p['id'] for p in projects]
    source = (await source_doc(body.source_id, body.month) if 'source_id' in body.model_fields_set
              else await latest_source(body.month))
    if body.comparison_id and not source:
        raise HTTPException(422, '보고서에 사용할 점검 데이터를 먼저 선택해 주세요.')
    comparison = None
    if source:
        if 'comparison_id' in body.model_fields_set:
            comparison = await source_doc(body.comparison_id, before=str(source['report_date']))
        else:
            previous_month = (date.fromisoformat(body.month + '-01') - timedelta(days=1)).strftime('%Y-%m')
            comparison = await latest_source(previous_month)
    rows, unmatched_actions = await resource_snapshot(source, comparison, include_images=body.include_images,
        mappings_input=body.mappings, fallback_snapshot=previous_snapshot if 'mappings' not in body.model_fields_set else None)
    # Reports are shared under server_check permission; PM membership must not drop rows on refresh.
    all_tasks = await task_snapshot(body.month, ids)
    current = [t for t in all_tasks if t['month'] == body.month]
    target_assets = {a['id']: a for t in current if t['state'] != 'EXCLUDED' for a in t['assets']
                     if a.get('category', '서버') == '서버'}
    mapped_ids = {r['asset']['id'] for r in rows if r['asset']}
    result = clean({'source': source_info(source), 'comparison': source_info(comparison), 'captured_at': now(),
                    'historical_reconstruction': body.month < tasks.current_month(),
                    'thresholds': {'warning': 80, 'danger': 90, 'version': 1},
                    'servers': rows, 'tasks': current, 'carryover': [t for t in all_tasks if t['month'] < body.month],
                    'missing_asset_resources': [a for i, a in target_assets.items() if i not in mapped_ids],
                    'unmatched_actions': unmatched_actions})
    from app.services.inspection_plan_reports import linked_plan
    result['plan'] = await linked_plan(body.month, previous_snapshot)
    update_stats(result)
    size_guard(result)
    return projects, result


async def preview(user, body):
    projects = None
    previous_snapshot = None
    if body.report_id:
        report = await get_report(body.report_id, user)
        draft_version(report, body.version)
        if body.kind != report.get('kind', 'RESULT'):
            raise HTTPException(422, '계획서와 결과서의 종류는 변경할 수 없습니다.')
        if body.month != report['month'] or sorted(body.project_ids or []) != sorted(report['project_ids']):
            raise HTTPException(422, '기존 보고서의 월과 포함 프로젝트는 변경할 수 없습니다.')
        projects = report['projects']
        previous_snapshot = report['snapshot']
    if body.kind == 'PLAN':
        from app.services.inspection_plan_reports import planning_snapshot
        projects, data = await planning_snapshot(body, projects)
    else:
        projects, data = await snapshot(body, projects, previous_snapshot)
    doc = {'_id': ObjectId(), 'owner': user.id, 'month': body.month, 'kind': body.kind, 'projects': projects,
           'report_id': body.report_id, 'report_version': body.version, 'snapshot': data,
           'include_images': body.include_images, 'expires_at': now() + timedelta(minutes=30)}
    await M.get_db()[PREVIEWS].insert_one(doc)
    return clean(doc)


async def read_preview(preview_id, user):
    doc = await M.get_db()[PREVIEWS].find_one({'_id': oid(preview_id), 'owner': user.id, 'expires_at': {'$gt': now()}})
    if not doc:
        raise HTTPException(409, '미리보기가 만료되었습니다. 점검 데이터를 다시 불러와 주세요.')
    return doc


async def create_report(user, preview_id, client_id):
    key = f'{user.id}:{client_id}'
    existing = await M.get_db()[REPORTS].find_one({'create_key': key})
    if existing:
        if existing.get('creation_preview_id') != preview_id:
            raise HTTPException(409, '이미 작성된 보고서가 있습니다. 보고서 목록을 확인해 주세요.')
        return await get_report(str(existing['_id']), user)
    p = await read_preview(preview_id, user)
    if p['report_id']:
        raise HTTPException(422, '기존 보고서를 불러온 상태에서는 새 보고서를 만들 수 없습니다.')
    project_ids = sorted(x['id'] for x in p['projects'])
    kind = p.get('kind', 'RESULT')
    scope_key = ('plan:' if kind == 'PLAN' else '') + hashlib.sha256(','.join(project_ids).encode()).hexdigest()
    doc = {'month': p['month'], 'kind': kind, 'project_ids': project_ids, 'projects': p['projects'], 'scope_key': scope_key,
           'revision': 1, 'state': 'DRAFT', 'version': 1, 'title': f"{p['month'][:4]}년 {int(p['month'][5:])}월 서버 점검 {'계획서' if kind == 'PLAN' else '결과서'}",
           'inspection_date': (p['snapshot']['source'] or {}).get('report_date') or (await tasks.inspection_date(p['month'])).isoformat(),
           'purpose': '서버 자원 사용량과 운영 상태를 확인하고, 월간 작업 결과와 추가 조치 계획을 기록합니다.',
           'overview': '', 'limitations': '', 'additional_notes': [], 'participants': [], 'include_appendix': False, 'include_images': p['include_images'],
           'snapshot': p['snapshot'], 'create_key': key, 'used_preview_id': str(p['_id']), 'creation_preview_id': str(p['_id']),
           'created_by': user.full_name or user.email, 'created_by_id': user.id, 'created_at': now(), 'updated_at': now()}
    if kind == 'PLAN':
        from app.services.inspection_plan_reports import initial_participants, DEFAULT_CHECKS
        doc.update(purpose='서버 운영 상태를 점검하고, 예정된 월간 작업을 수행합니다.',
                   planned_time='', resource_checks=DEFAULT_CHECKS,
                   participants=await initial_participants(doc))
    elif p['snapshot'].get('plan'):
        doc['participants'] = [{**deepcopy(person), 'work_summary': ''}
                               for person in p['snapshot']['plan'].get('participants', [])]
        doc['participants'] = sync_participant_assignments(doc)
    size_guard(doc)
    try:
        await M.get_db()[REPORTS].insert_one(doc)
    except DuplicateKeyError:
        doc = await M.get_db()[REPORTS].find_one({'create_key': key})
        if doc and doc.get('creation_preview_id') != preview_id:
            raise HTTPException(409, '이미 작성된 보고서가 있습니다. 보고서 목록을 확인해 주세요.')
        if not doc:
            doc = await M.get_db()[REPORTS].find_one({'month': p['month'], 'scope_key': scope_key}, sort=[('revision', -1)])
        return await get_report(str(doc['_id']), user)
    return doc


async def change_report(doc, user, values):
    values = {**values, 'participants': sync_participant_assignments({**doc, **values})}
    size_guard({**doc, **values})
    result = await M.get_db()[REPORTS].update_one({'_id': doc['_id'], 'version': doc['version'], 'state': 'DRAFT'},
        {'$set': {**values, 'updated_at': now(), 'updated_by': user.full_name or user.email}, '$inc': {'version': 1}})
    if not result.matched_count:
        raise HTTPException(409, '다른 사용자가 보고서를 변경했습니다. 작성 내용을 보관한 뒤 최신 보고서를 확인해 주세요.')
    return await get_report(str(doc['_id']), user)


async def refresh_report(doc, user, preview_id):
    if doc.get('used_preview_id') == preview_id:
        return doc
    p = await read_preview(preview_id, user)
    if p['report_id'] != str(doc['_id']) or p['report_version'] != doc['version']:
        raise HTTPException(409, '보고서가 변경되었습니다. 최신 내용을 다시 불러와 주세요.')
    updated = await change_report(doc, user, {'snapshot': p['snapshot'], 'include_images': p['include_images'], 'used_preview_id': preview_id})
    return updated


async def sync_results(doc, user):
    require_result(doc)
    data = deepcopy(doc['snapshot'])
    for t in data['tasks'] + data['carryover']:
        source = await tasks.collection().find_one({'_id': oid(t['issue_id'])})
        occurrence = next((o for o in (source or {}).get('occurrences', []) if o['month'] == t['month']), None)
        if occurrence and occurrence.get('result'):
            t['result'] = clean(occurrence['result'])
    from app.services.inspection_work_plans import hydrate_results, freeze_results
    await hydrate_results(data['tasks'] + data['carryover'])
    freeze_results(data['tasks'] + data['carryover'])
    data = clean(data)
    update_stats(data)
    return await change_report(doc, user, {'snapshot': data})


async def report_action(doc, row_key=None, action_id=None):
    """Resolve the target from the report, never from a caller-supplied source/hostname."""
    require_result(doc)
    source = doc['snapshot'].get('source')
    if not source:
        raise HTTPException(422, '보고서에 점검 데이터가 없습니다.')
    raw = await source_doc(source['id'], doc['month'])
    if bool(row_key) == bool(action_id):
        raise HTTPException(422, '수정할 조치 항목을 하나 선택해 주세요.')
    col = M.get_db()[M.HEALTH_ACTIONS]
    if action_id:
        if not any(a['id'] == action_id for a in doc['snapshot'].get('unmatched_actions', [])):
            raise HTTPException(404, '보고서에 포함된 조치가 아닙니다.')
        action = await col.find_one({'_id': oid(action_id), 'report_id': source['id']})
        if not action:
            raise HTTPException(409, '조치 내역이 삭제되었습니다. 최신 내용을 불러와 주세요.')
        return action['host_name'], action
    row = next((r for r in doc['snapshot']['servers'] if r['key'] == row_key), None)
    if not row:
        raise HTTPException(404, '보고서에 포함된 서버가 아닙니다.')
    normalized = host(row['host_name'])
    # Actions in the resource screen are keyed by hostname; duplicate hosts cannot be
    # edited as if they were separate servers, even if their IP addresses differ.
    for rows in (doc['snapshot']['servers'], resource_rows(raw)):
        matches = [r for r in rows if host(r['host_name']) == normalized]
        if len(matches) != 1 or matches[0].get('hostname_missing'):
            raise HTTPException(409, '호스트명으로 대상 서버를 구분할 수 없습니다. 점검 데이터의 호스트명을 확인해 주세요.')
    if not any(r['key'] == row_key for r in resource_rows(raw)):
        raise HTTPException(409, '서버 점검 데이터가 변경되었습니다. 최신 내용을 불러와 주세요.')
    actions = await col.find({'report_id': source['id']}).to_list(None)
    matches = [a for a in actions if host(a['host_name']) == normalized]
    if len(matches) > 1:
        raise HTTPException(409, '같은 호스트명에 조치가 여러 건 등록되어 있습니다. 자원 점검에서 확인해 주세요.')
    return row['host_name'], matches[0] if matches else None


def action_token(action):
    return hashlib.sha256(BSON.encode(action)).hexdigest() if action else None


def snapshot_with_action(doc, action, row_key, action_id):
    data = deepcopy(doc['snapshot'])
    captured = clean(action)
    captured['images'] = [s for s in action.get('images', []) if doc['include_images']
                          and re.match(r'^data:image/(png|jpeg|jpg|gif|webp);base64,', s)]
    if row_key:
        row = next((r for r in data['servers'] if r['key'] == row_key), None)
        if not row:
            raise HTTPException(409, '보고서의 대상 서버가 변경되었습니다.')
        row['action'] = captured
    else:
        index = next((i for i, a in enumerate(data['unmatched_actions']) if a['id'] == action_id), None)
        if index is None:
            raise HTTPException(409, '보고서의 조치 항목이 변경되었습니다.')
        data['unmatched_actions'][index] = captured
    update_stats(data)
    size_guard({**doc, 'snapshot': data})
    return data


async def save_report_action(doc, user, body):
    hostname, previous = await report_action(doc, body.row_key, body.action_id)
    if action_token(previous) != body.action_token:
        raise HTTPException(409, '다른 사용자가 조치 내역을 변경했습니다. 작성 내용을 보관한 뒤 최신 조치를 확인해 주세요.')
    source_id = doc['snapshot']['source']['id']
    values = {'memo': body.memo.strip(), 'images': body.images, 'is_resolved': body.is_resolved,
              'actor': user.full_name or user.email, 'actor_email': user.email, 'updated_at': now()}
    # A stable ID prevents simultaneous registrations through reports from making duplicates.
    action = {**(previous or {'_id': ObjectId(hashlib.sha256(f'{source_id}:{host(hostname)}'.encode()).hexdigest()[:24]),
                             'report_id': source_id, 'host_name': hostname, 'created_at': now()}), **values}
    data = snapshot_with_action(doc, action, body.row_key, body.action_id)
    size_guard(action)
    col = M.get_db()[M.HEALTH_ACTIONS]
    if previous:
        result = await col.update_one({k: previous.get(k) for k in ('_id', 'updated_at', 'memo', 'images', 'is_resolved')},
                                      {'$set': values})
        if not result.matched_count:
            raise HTTPException(409, '다른 사용자가 조치 내역을 변경했습니다. 작성 내용은 유지됩니다.')
    else:
        try:
            await col.insert_one(action)
        except DuplicateKeyError:
            raise HTTPException(409, '다른 사용자가 조치를 등록했습니다. 최신 조치를 확인해 주세요.')
    # Source actions and report snapshots are separate records. Merge only this action
    # after an unrelated concurrent report edit; never overwrite a finalized snapshot.
    for _ in range(3):
        try:
            updated = await change_report(doc, user, {'snapshot': data})
            return {'report': updated, 'warning': ''}
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            latest = await get_report(str(doc['_id']), user)
            if latest['state'] != 'DRAFT' or latest['snapshot'].get('source') != doc['snapshot'].get('source'):
                break
            try:
                _, current = await report_action(latest, body.row_key, body.action_id)
                if not current:
                    break
                data = snapshot_with_action(latest, current, body.row_key, body.action_id)
            except HTTPException:
                break
            doc = latest
    return {'report': await get_report(str(doc['_id']), user),
            'warning': '조치 내역은 저장됐지만 보고서가 변경되어 반영하지 못했습니다. 초안에서 최신 내용을 불러와 주세요.'}


async def revision(doc, user):
    if doc['state'] != 'FINAL':
        raise HTTPException(409, '확정된 보고서에서만 수정본을 만들 수 있습니다.')
    existing = await M.get_db()[REPORTS].find_one({'parent_id': str(doc['_id'])})
    if existing:
        return await get_report(str(existing['_id']), user)
    new = {k: deepcopy(v) for k, v in doc.items() if k not in ('_id', 'create_key', 'finalized_at', 'finalized_by')}
    new.update(parent_id=str(doc['_id']), revision=doc['revision'] + 1, state='DRAFT', version=1,
               created_at=now(), updated_at=now(), created_by=user.full_name or user.email, created_by_id=user.id)
    new['participants'] = sync_participant_assignments(new)
    size_guard(new)
    try:
        await M.get_db()[REPORTS].insert_one(new)
    except DuplicateKeyError:
        new = await M.get_db()[REPORTS].find_one({'parent_id': str(doc['_id'])})
    return new
