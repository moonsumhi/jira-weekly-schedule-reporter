"""SR 담당자 배정 시 PM 이슈 자동 생성 브릿지."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.services.pm.issue_service import next_issue_number

_REQUEST_TYPE_LABEL: dict[str, str] = {
    "IMPROVEMENT": "기능 개선",
    "BUG_FIX": "오류 수정",
    "DATA_REQUEST": "데이터 요청",
    "PERMISSION": "권한 요청",
    "CONFIG_CHANGE": "설정 변경",
    "SERVER_INFRA": "서버/인프라",
    "SECURITY": "보안 조치",
    "ETC": "기타",
}

_PRIORITY_MAP: dict[str, str] = {
    "CRITICAL": "HIGHEST",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}


def _fmt_date(val) -> str:
    if not val:
        return "-"
    return str(val)[:10]


async def auto_create_pm_issue(
    sr: dict,
    assignee_id: str,
    actor_id: str,
) -> tuple[str, str] | None:
    """SR을 기반으로 기본 SR 프로젝트 백로그에 이슈를 자동 생성.

    Returns (issue_id, project_id), 기본 프로젝트 미설정 시 None.
    """
    projects_col = MongoClientManager.get_pm_projects_collection()
    default_project = await projects_col.find_one({"is_sr_default": True})
    if not default_project:
        return None

    project_id = default_project["_id"]
    number = await next_issue_number(project_id)

    sr_no = sr.get("sr_no", "")
    rt = _REQUEST_TYPE_LABEL.get(sr.get("request_type", ""), sr.get("request_type", ""))
    priority = _PRIORITY_MAP.get(sr.get("priority", "MEDIUM"), "MEDIUM")

    requester = sr.get("requester_name", "")
    department = sr.get("requester_department", "")
    requester_str = f"{requester} ({department})" if department else requester

    raw_desc = sr.get("description") or ""
    import re, html as _html
    plain_desc = _html.unescape(re.sub(r"<[^>]+>", "", raw_desc)).strip()

    description = (
        f"[ SR 자동 연동 이슈 ]\n"
        f"{'─' * 36}\n"
        f"  SR 번호     : {sr_no}\n"
        f"  요청 유형   : {rt}\n"
        f"  요청자      : {requester_str}\n"
        f"  관련 시스템 : {sr.get('related_system') or '-'}\n"
        f"  희망 완료일 : {_fmt_date(sr.get('desired_due_date'))}\n"
        f"{'─' * 36}\n\n"
        f"▸ 요청 내용\n\n"
        f"{plain_desc}"
    )

    now = datetime.now(timezone.utc)
    issues_col = MongoClientManager.get_pm_issues_collection()

    result = await issues_col.insert_one({
        "project_id": project_id,
        "number": number,
        "title": f"[{sr_no}] {sr.get('title', '')}",
        "description": description,
        "type": "TASK",
        "status": "BACKLOG",
        "priority": priority,
        "assignee_id": ObjectId(assignee_id) if assignee_id else None,
        "reporter_id": ObjectId(actor_id) if actor_id else None,
        "sprint_id": None,
        "epic_id": None,
        "parent_issue_id": None,
        "label_ids": [],
        "start_date": sr.get("planned_start_date"),
        "due_date": sr.get("planned_due_date") or sr.get("desired_due_date"),
        "story_points": None,
        "attachments": [],
        "order": float(number),
        "linked_sr_id": str(sr["_id"]),
        "created_at": now,
        "updated_at": now,
    })

    return str(result.inserted_id), str(project_id)


async def update_pm_issue_assignee(issue_id: str, assignee_id: str) -> None:
    """재배정 시 기존 PM 이슈 담당자만 업데이트."""
    issues_col = MongoClientManager.get_pm_issues_collection()
    await issues_col.update_one(
        {"_id": ObjectId(issue_id)},
        {"$set": {
            "assignee_id": ObjectId(assignee_id) if assignee_id else None,
            "updated_at": datetime.now(timezone.utc),
        }},
    )


async def prepare_issue_completion(sr: dict, user, requested: bool, status: str) -> list[dict]:
    """Resolve links on the server and authorize before changing the SR."""
    if not requested:
        return []
    from fastapi import HTTPException
    from app.services.pm.permission import require_pm_member
    from app.models.pm.issue import canonical_issue_status

    if status != 'COMPLETED':
        raise HTTPException(422, '연결 일감 완료는 SR 처리 완료 시에만 선택할 수 있습니다.')
    ids = [ObjectId(str(sr[field])) for field in ('converted_issue_id', 'related_issue_id')
           if sr.get(field) and ObjectId.is_valid(str(sr[field]))]
    query = {'$or': [{'_id': {'$in': ids}},
                     {'linked_sr_id': {'$in': [str(sr['_id']), sr['_id']]}}]}
    issues = await MongoClientManager.get_pm_issues_collection().find(query).to_list(None)
    pending = [issue for issue in issues if canonical_issue_status(issue.get('status')) != 'DONE']
    for project_id in {str(issue['project_id']) for issue in pending}:
        await require_pm_member(user, project_id)
    return pending


async def complete_linked_issues(issues: list[dict], user) -> None:
    # Use the standard issue update path, including history and inspection snapshots.
    from app.models.pm.issue import IssuePatch
    from app.routers.pm.issues import patch_issue

    for issue in issues:
        await patch_issue(str(issue['project_id']), str(issue['_id']), IssuePatch(status='DONE'), user)
