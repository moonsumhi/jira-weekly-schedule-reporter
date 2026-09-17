from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.services import asset_links


async def attach_linked_sr_info(docs: list[dict]) -> None:
    """이슈 목록에 연결된 SR ID/번호를 한 번의 조회로 보강한다."""
    if not docs:
        return

    issue_ids = [doc["_id"] for doc in docs]
    linked_sr_ids = [
        ObjectId(str(doc["linked_sr_id"]))
        for doc in docs
        if doc.get("linked_sr_id") and ObjectId.is_valid(str(doc["linked_sr_id"]))
    ]
    conditions: list[dict] = [
        {"related_issue_id": {"$in": issue_ids}},
        {"converted_issue_id": {"$in": [*issue_ids, *map(str, issue_ids)]}},
    ]
    if linked_sr_ids:
        conditions.append({"_id": {"$in": linked_sr_ids}})

    sr_by_id: dict[str, dict] = {}
    sr_by_issue_id: dict[str, dict] = {}
    sr_col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    async for sr in sr_col.find({"$or": conditions}, {"sr_no": 1, "related_issue_id": 1, "converted_issue_id": 1}):
        sr_by_id[str(sr["_id"])] = sr
        for field in ("related_issue_id", "converted_issue_id"):
            if sr.get(field):
                sr_by_issue_id[str(sr[field])] = sr

    for doc in docs:
        linked_sr_id = doc.get("linked_sr_id")
        sr = sr_by_id.get(str(linked_sr_id)) if linked_sr_id else None
        sr = sr or sr_by_issue_id.get(str(doc["_id"]))
        doc["linked_sr_no"] = sr.get("sr_no") if sr else None
        if sr and not linked_sr_id:
            doc["linked_sr_id"] = str(sr["_id"])


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
    await asset_links.hydrate([d])
    issue_object_id = d.pop("_id")
    d["id"] = str(issue_object_id)
    d["project_id"] = str(d["project_id"])

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

    # 보고자 (자동 생성 이슈는 보고자가 없을 수 있음)
    if d.get("reporter_id"):
        d["reporter_id"] = str(d["reporter_id"])
        reporter = await users.find_one({"_id": ObjectId(d["reporter_id"])}, {"full_name": 1, "email": 1})
        d["reporter_name"] = reporter.get("full_name") or reporter.get("email", "") if reporter else ""
    else:
        d["reporter_id"] = None
        d["reporter_name"] = None

    # 상위 이슈 요약 (대시보드 등 목록에서 하위 관계 표시에 사용)
    issues_col = MongoClientManager.get_pm_issues_collection()
    parent = None
    if d.get("parent_issue_id"):
        parent = await issues_col.find_one(
            {"_id": ObjectId(d["parent_issue_id"])},
            {"number": 1, "title": 1, "epic_id": 1},
        )
        d["parent_issue_number"] = parent.get("number") if parent else None
        d["parent_issue_title"] = parent.get("title") if parent else None
    else:
        d["parent_issue_number"] = None
        d["parent_issue_title"] = None

    # 서브 이슈는 부모가 속한 Epic까지 계층 문맥으로 사용한다.
    effective_epic_id = d.get("epic_id") or (
        str(parent["epic_id"]) if parent and parent.get("epic_id") else None
    )
    d["effective_epic_id"] = effective_epic_id
    if effective_epic_id:
        epic = await issues_col.find_one(
            {"_id": ObjectId(effective_epic_id)},
            {"number": 1, "title": 1},
        )
        d["epic_number"] = epic.get("number") if epic else None
        d["epic_title"] = epic.get("title") if epic else None
    else:
        d["epic_number"] = None
        d["epic_title"] = None

    # story_points 기본값
    if "story_points" not in d:
        d["story_points"] = None

    # attachments 기본값
    if "attachments" not in d:
        d["attachments"] = []

    # 연결된 SR 정보는 목록 조회 시 batch로 보강된다.
    linked_sr_id = d.get("linked_sr_id") or None
    d["linked_sr_id"] = str(linked_sr_id) if linked_sr_id else None
    d["linked_sr_no"] = d.get("linked_sr_no") or None

    # 남은 ObjectId 정리 — 반복업무 이슈의 recurring_template_id 등 메타 필드가
    # response_model 없는 엔드포인트(대시보드)에서 그대로 인코딩돼 500 나는 것 방지
    for _k, _v in list(d.items()):
        if isinstance(_v, ObjectId):
            d[_k] = str(_v)

    return d
