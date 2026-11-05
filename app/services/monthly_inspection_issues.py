"""Summarize the findings saved in a finalized server inspection snapshot."""
import re

from app.models.pm.issue import canonical_issue_status


def _action_note(value):
    text = str(value or '').strip()
    normalized = re.sub(r'\s+', '', text).lower()
    if not normalized or re.fullmatch(r'[-–—]+', normalized) or normalized in {
        '없음', '정상', '양호', 'ok', 'n/a', 'na', 'none', 'null', '0',
        '이상없음', '해당없음', '특이사항없음',
    }:
        return ''
    return text


def summarize_inspection(doc):
    snapshot = doc.get('snapshot') or {}
    thresholds = snapshot.get('thresholds') or {}
    warning = thresholds.get('warning', 80)
    danger = thresholds.get('danger', 90)
    if not isinstance(warning, (int, float)) or not isinstance(danger, (int, float)):
        warning, danger = 80, 90
    issues = []
    for index, server in enumerate(snapshot.get('servers') or []):
        findings = []
        for key, label in [('cpu', 'CPU'), ('ram', 'RAM'), ('disk', '디스크')]:
            metric = server.get(key) or {}
            value = metric.get('value')
            if value is None:
                findings.append({'label': f'{label} 측정값 없음', 'level': 'missing'})
            elif isinstance(value, (int, float)) and not isinstance(value, bool) and value >= warning:
                path = f" · {metric['path']}" if key == 'disk' and metric.get('path') else ''
                findings.append({'label': f'{label} {value:g}%{path}', 'level': 'danger' if value >= danger else 'warning'})
        for finding in server.get('findings') or []:
            label = str(finding.get('label') or '').strip()
            if label and not re.fullmatch(r'(CPU|RAM|디스크)\s+[\d.]+%', label):
                findings.append({'label': label, 'level': 'danger' if finding.get('level') == 'danger' else 'warning'})
        action = server.get('action') or None
        source_note = _action_note(server.get('action_items'))
        pending = bool((action and action.get('is_resolved') is False) or (not action and source_note))
        if not findings and not pending:
            continue
        severity = ('danger' if any(item['level'] == 'danger' for item in findings) else
                    'warning' if any(item['level'] == 'warning' for item in findings) else
                    'missing' if findings else 'action')
        issues.append({
            'key': str(server.get('key') or f'server-{index}'),
            'host_name': (server.get('asset') or {}).get('name') or server.get('host_name') or '이름 없음',
            'ip': server.get('ip') or '', 'severity': severity, 'findings': findings,
            'action_status': 'resolved' if action and action.get('is_resolved') is True else 'pending' if action else 'unregistered',
            'source_note': source_note, 'action_memo': str((action or {}).get('memo') or '').strip(),
        })
    for index, asset in enumerate(snapshot.get('missing_asset_resources') or []):
        issues.append({'key': f"missing-asset-{asset.get('id') or index}", 'host_name': asset.get('name') or '이름 없음',
                       'ip': asset.get('ip') or '', 'severity': 'missing',
                       'findings': [{'label': '점검 데이터가 없는 작업 대상 서버', 'level': 'missing'}],
                       'action_status': 'unregistered', 'source_note': '', 'action_memo': ''})
    for index, action in enumerate(snapshot.get('unmatched_actions') or []):
        if action.get('is_resolved') is not False:
            continue
        issues.append({'key': f"unmatched-{action.get('id') or index}", 'host_name': action.get('host_name') or '이름 없음',
                       'ip': '', 'severity': 'action', 'findings': [{'label': '대상 서버 확인 필요', 'level': 'warning'}],
                       'action_status': 'pending', 'source_note': '', 'action_memo': str(action.get('memo') or '').strip()})
    ranks = {'danger': 0, 'warning': 1, 'missing': 2, 'action': 3}
    issues.sort(key=lambda item: ranks[item['severity']])

    incomplete_issues = []
    seen = set()
    for index, task in enumerate(snapshot.get('tasks') or []):
        if task.get('state') == 'EXCLUDED' or task.get('source_type') not in (None, 'ISSUE'):
            continue
        issue = task.get('issue') or {}
        state = task.get('state')
        status = canonical_issue_status(issue.get('status') or '')
        if state != 'ROLLED' and status == 'DONE':
            continue
        key = (str(task.get('issue_id') or f'task-{index}'), str(task.get('month') or ''))
        if key in seen:
            continue
        seen.add(key)
        result = task.get('result') or {}
        status_label = {'BACKLOG': '백로그', 'TODO': '할 일', 'IN_PROGRESS': '진행 중'}.get(status, '상태 확인')
        incomplete_issues.append({'key': ':'.join(key), 'title': issue.get('title') or '제목 없음',
                                  'issue_key': issue.get('key') or '', 'assignee': issue.get('assignee_name') or '',
                                  'status': '이월' if state == 'ROLLED' else '지연' if task.get('overdue') else status_label,
                                  'result': str(result.get('content') or '').strip(),
                                  'detail': str(result.get('follow_up') or '').strip(),
                                  'reason': str(task.get('reason') or '').strip(),
                                  'due_date': str(task.get('planned_end') or '')})

    limitations = str(doc.get('limitations') or '').strip()
    notes = doc.get('additional_notes') or ([{'content': limitations}] if limitations else [])
    return {'issues': issues, 'incomplete_issues': incomplete_issues,
            'task_data_available': isinstance(snapshot.get('tasks'), list),
            'notes': [str(item.get('content') or '').strip() for item in notes if str(item.get('content') or '').strip()],
            'source_available': bool(snapshot.get('source') and snapshot.get('servers'))}
