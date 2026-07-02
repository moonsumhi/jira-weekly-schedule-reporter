from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import MongoClientManager


async def next_issue_number(project_id: ObjectId) -> int:
    """프로젝트 내 이슈 번호 자동 증가 (동시성 안전: find_one_and_update)."""
    col = MongoClientManager.get_pm_issues_collection()
    last = await col.find_one(
        {"project_id": project_id},
        sort=[("number", -1)],
        projection={"number": 1},
    )
    return (last["number"] + 1) if last else 1


async def record_history(
    issue_id: ObjectId,
    user_id: ObjectId,
    field: str,
    old_value: Any,
    new_value: Any,
) -> None:
    """이슈 필드 변경 이력을 저장."""
    if old_value == new_value:
        return
    col = MongoClientManager.get_pm_issue_history_collection()
    await col.insert_one({
        "issue_id": issue_id,
        "user_id": user_id,
        "field": field,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": str(new_value) if new_value is not None else None,
        "created_at": datetime.now(timezone.utc),
    })


async def enrich_issue(doc: dict) -> dict:
    """이슈 doc에 담당자/보고자 이름을 JOIN하여 반환."""
    users = MongoClientManager.get_users_collection()
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d["project_id"] = str(d["project_id"])
    d["reporter_id"] = str(d["reporter_id"])

    # 프로젝트 키 / 이름
    projects_col = MongoClientManager.get_pm_projects_collection()
    project = await projects_col.find_one({"_id": ObjectId(d["project_id"])}, {"key": 1, "name": 1})
    d["project_key"] = project.get("key") if project else None
    d["project_name"] = project.get("name") if project else None
    d["sprint_id"] = str(d["sprint_id"]) if d.get("sprint_id") else None
    d["epic_id"] = str(d["epic_id"]) if d.get("epic_id") else None
    d["parent_issue_id"] = str(d["parent_issue_id"]) if d.get("parent_issue_id") else None
    d["label_ids"] = [str(x) for x in d.get("label_ids", [])]

    # 담당자
    if d.get("assignee_id"):
        d["assignee_id"] = str(d["assignee_id"])
        user = await users.find_one({"_id": ObjectId(d["assignee_id"])}, {"full_name": 1, "email": 1})
        d["assignee_name"] = user.get("full_name") or user.get("email", "") if user else ""
    else:
        d["assignee_id"] = None
        d["assignee_name"] = None

    # 보고자
    reporter = await users.find_one({"_id": ObjectId(d["reporter_id"])}, {"full_name": 1, "email": 1})
    d["reporter_name"] = reporter.get("full_name") or reporter.get("email", "") if reporter else ""

    # 상위 Epic 제목
    if d.get("epic_id"):
        issues_col = MongoClientManager.get_pm_issues_collection()
        epic = await issues_col.find_one({"_id": ObjectId(d["epic_id"])}, {"title": 1})
        d["epic_title"] = epic.get("title") if epic else None
    else:
        d["epic_title"] = None

    # story_points 기본값
    if "story_points" not in d:
        d["story_points"] = None

    # attachments 기본값
    if "attachments" not in d:
        d["attachments"] = []

    # linked_sr_id (SR 연동 이슈인 경우)
    d["linked_sr_id"] = d.get("linked_sr_id") or None

    return d
