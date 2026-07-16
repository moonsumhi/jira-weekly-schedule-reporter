"""PM 보고서 자동 집계 - 이슈 데이터에서 프로젝트별/개인별 현황을 자동 생성."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.models.pm.reports import (
    PersonBreakdown, ProjectBreakdown, ReportStats, WorkItem,
)


def _calc_stats(completed, in_progress, delayed=None) -> ReportStats:
    # delayed 는 in_progress 의 부분집합이므로 total 에 중복 집계하지 않음
    total = len(completed) + len(in_progress)
    c = len(completed)
    rate = int(c / total * 100) if total > 0 else 0
    return ReportStats(
        total=total, completed=c,
        in_progress=len(in_progress),
        delayed=len(delayed) if delayed else 0,
        completion_rate=rate,
    )


async def aggregate_period(
    start_dt: datetime,
    end_dt: datetime,
    next_start_dt: Optional[datetime] = None,
    next_end_dt: Optional[datetime] = None,
) -> tuple[
    list[WorkItem],          # all_items (현재 기간)
    list[WorkItem],          # upcoming_items (차주/차월)
    list[ProjectBreakdown],  # by_project
    list[PersonBreakdown],   # by_person
    ReportStats,             # overall stats
]:
    now = datetime.now(timezone.utc)

    issues_col   = MongoClientManager.get_pm_issues_collection()
    projects_col = MongoClientManager.get_pm_projects_collection()
    orgs_col     = MongoClientManager.get_pm_organizations_collection()
    users_col    = MongoClientManager.get_users_collection()
    sprints_col  = MongoClientManager.get_pm_sprints_collection()

    # ── 캐시 ─────────────────────────────────────────────────────────
    _proj_cache:   dict = {}
    _org_cache:    dict = {}
    _user_cache:   dict = {}
    _sprint_cache: dict = {}
    _epic_cache:   dict = {}

    async def get_proj(pid):
        k = str(pid)
        if k not in _proj_cache:
            _proj_cache[k] = await projects_col.find_one({"_id": pid})
        return _proj_cache[k]

    async def get_org(oid):
        k = str(oid)
        if k not in _org_cache:
            _org_cache[k] = await orgs_col.find_one({"_id": oid})
        return _org_cache[k]

    async def get_user(uid):
        if not uid:
            return None
        k = str(uid)
        if k not in _user_cache:
            _user_cache[k] = await users_col.find_one({"_id": uid}, {"full_name": 1, "email": 1})
        return _user_cache[k]

    async def get_sprint(sid):
        if not sid:
            return None
        k = str(sid)
        if k not in _sprint_cache:
            _sprint_cache[k] = await sprints_col.find_one({"_id": sid})
        return _sprint_cache[k]

    async def get_epic(eid):
        if not eid:
            return None
        k = str(eid)
        if k not in _epic_cache:
            _epic_cache[k] = await issues_col.find_one({"_id": eid}, {"title": 1})
        return _epic_cache[k]

    async def doc_to_item(doc) -> Optional[WorkItem]:
        proj = await get_proj(doc["project_id"])
        if not proj:
            return None
        org = await get_org(proj["org_id"]) if proj.get("org_id") else None
        user = await get_user(doc.get("assignee_id"))
        sprint = await get_sprint(doc.get("sprint_id"))
        epic = await get_epic(doc.get("epic_id"))

        due_date = doc.get("due_date")
        status = doc.get("status", "BACKLOG")
        is_delayed = bool(due_date and due_date.replace(tzinfo=timezone.utc) < now and status != "DONE")

        return WorkItem(
            issue_id=str(doc["_id"]),
            issue_number=doc["number"],
            title=doc["title"],
            type=doc["type"],
            project_id=str(proj["_id"]),
            project_name=proj["name"],
            org_name=org["name"] if org else None,
            assignee_id=str(doc["assignee_id"]) if doc.get("assignee_id") else None,
            assignee_name=(user.get("full_name") or user.get("email")) if user else None,
            status=status,
            priority=doc.get("priority", "MEDIUM"),
            epic_title=epic["title"] if epic else None,
            sprint_name=sprint["name"] if sprint else None,
            start_date=doc.get("start_date"),
            due_date=due_date,
            is_delayed=is_delayed,
            story_points=doc.get("story_points"),
        )

    # end_dt 를 해당일 23:59:59 로 확장 (날짜만 받아온 경우 당일 이슈 누락 방지)
    if end_dt.hour == 0 and end_dt.minute == 0 and end_dt.second == 0:
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
    if next_end_dt and next_end_dt.hour == 0 and next_end_dt.minute == 0 and next_end_dt.second == 0:
        next_end_dt = next_end_dt.replace(hour=23, minute=59, second=59)

    # ── 현재 기간 이슈 쿼리 ──────────────────────────────────────────
    # start_date/due_date 가 기간 내이거나, 진행 중이거나, 기간 내 완료된 것
    # 업무현황과 동일한 기준: TASK/SUB_TASK 타입만 집계
    query = {
        "type": {"$in": ["TASK", "SUB_TASK"]},
        "$or": [
            {"start_date": {"$gte": start_dt, "$lte": end_dt}},
            {"due_date":   {"$gte": start_dt, "$lte": end_dt}},
            {"status": {"$in": ["IN_PROGRESS", "IN_REVIEW"]}},  # 날짜 미설정 진행 중 이슈도 포함
            {"status": "DONE",
             "updated_at": {"$gte": start_dt, "$lte": end_dt}},
        ],
    }
    docs = await issues_col.find(query).sort("number", 1).to_list(None)

    all_items: list[WorkItem] = []
    for doc in docs:
        item = await doc_to_item(doc)
        if item:
            all_items.append(item)

    # ── 차주/차월 이슈 쿼리 ──────────────────────────────────────────
    upcoming_items: list[WorkItem] = []
    if next_start_dt and next_end_dt:
        existing_ids = {i.issue_id for i in all_items}
        uq = {
            "type": "TASK",
            "status": {"$in": ["TODO", "BACKLOG"]},
            "$or": [
                {"start_date": {"$gte": next_start_dt, "$lte": next_end_dt}},
                {"due_date":   {"$gte": next_start_dt, "$lte": next_end_dt}},
            ],
        }
        udocs = await issues_col.find(uq).sort("number", 1).to_list(None)
        for doc in udocs:
            if str(doc["_id"]) in existing_ids:
                continue
            item = await doc_to_item(doc)
            if item:
                upcoming_items.append(item)

    # ── 프로젝트별 / 개인별 분류 ─────────────────────────────────────
    by_project: dict[str, ProjectBreakdown] = {}
    by_person:  dict[str, PersonBreakdown]  = {}

    def classify(item: WorkItem) -> str:
        if item.status == "DONE":
            return "completed"
        return "in_progress"

    def ensure_proj(item: WorkItem):
        pid = item.project_id
        if pid not in by_project:
            by_project[pid] = ProjectBreakdown(
                project_id=pid,
                project_name=item.project_name,
                org_name=item.org_name,
            )
        return by_project[pid]

    def ensure_person(item: WorkItem):
        uid = item.assignee_id or "__unassigned__"
        uname = item.assignee_name or "미지정"
        if uid not in by_person:
            by_person[uid] = PersonBreakdown(user_id=uid, user_name=uname)
        return by_person[uid]

    for item in all_items:
        cat = classify(item)
        getattr(ensure_proj(item), cat).append(item)
        getattr(ensure_person(item), cat).append(item)
        # 진행중이면서 마감일 초과 → delayed 에도 추가 (부분집합, 강조 표시용)
        if cat == "in_progress" and item.is_delayed:
            ensure_proj(item).delayed.append(item)
            ensure_person(item).delayed.append(item)

    for item in upcoming_items:
        ensure_proj(item).upcoming.append(item)
        ensure_person(item).upcoming.append(item)

    # ── 프로젝트 멤버 전체 포함 (이슈 없는 멤버도 표시) ─────────────────
    project_ids = list(by_project.keys())
    if project_ids:
        members_col = MongoClientManager.get_pm_project_members_collection()
        obj_ids = [ObjectId(pid) for pid in project_ids]
        member_docs = await members_col.find(
            {"project_id": {"$in": obj_ids}}
        ).to_list(None)
        for m in member_docs:
            uid = str(m["user_id"])
            if uid not in by_person:
                uname = m.get("user_name") or m.get("user_email") or uid
                by_person[uid] = PersonBreakdown(user_id=uid, user_name=uname)

    # ── 통계 계산 ─────────────────────────────────────────────────────
    for pb in by_project.values():
        pb.stats = _calc_stats(pb.completed, pb.in_progress, pb.delayed)

    for pb in by_person.values():
        pb.stats = _calc_stats(pb.completed, pb.in_progress, pb.delayed)

    total = len(all_items)
    c   = sum(1 for i in all_items if i.status == "DONE")
    ip  = total - c
    dl  = sum(1 for i in all_items if i.is_delayed and i.status != "DONE")
    rate = int(c / total * 100) if total > 0 else 0
    stats = ReportStats(
        total=total, completed=c, in_progress=ip,
        delayed=dl, completion_rate=rate,
    )

    return (
        all_items,
        upcoming_items,
        list(by_project.values()),
        list(by_person.values()),
        stats,
    )
