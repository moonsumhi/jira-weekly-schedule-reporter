# app/services/pm/recurring_issue_service.py
"""반복 이슈 템플릿 CRUD + 회차 계산/생성 로직.

- 회차 라벨("8월 2차")은 회차일 순번에서 자동 파생 → 작업 종류와 무관(범용).
- 생성된 이슈는 (recurring_template_id, occurrence_date) 로 중복 방지(idempotent).
- 자동 스케줄러와 즉시 생성 버튼이 같은 생성 로직을 공유한다.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.services.pm.issue_service import next_issue_number
from app.utils.time import KST


def _col():
    return MongoClientManager.get_recurring_issue_templates_collection()


def _issues_col():
    return MongoClientManager.get_pm_issues_collection()


def to_out(doc: dict) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d["project_id"] = str(d["project_id"]) if isinstance(d.get("project_id"), ObjectId) else d.get("project_id")
    return d


# ── 회차 계산 ────────────────────────────────────────────────────────────────

def _nth_weekday_day(year: int, month: int, weekday: int, week: int) -> Optional[int]:
    """해당 월의 'N째주 X요일' 일(day)을 반환. 없으면 None. (weekday 0=월 … 6=일)"""
    weeks = calendar.monthcalendar(year, month)  # 주 목록, 각 주는 [월..일], 없는 날은 0
    if week == -1:  # 마지막 주
        for w in reversed(weeks):
            if w[weekday] != 0:
                return w[weekday]
        return None
    count = 0
    for w in weeks:
        if w[weekday] != 0:
            count += 1
            if count == week:
                return w[weekday]
    return None  # 예: 그 달에 다섯째 월요일이 없음


def _rule_days(rule: dict, year: int, month: int) -> List[int]:
    """규칙(mode)에 따라 해당 월의 회차일(day) 목록을 정렬해 반환한다."""
    last_day = calendar.monthrange(year, month)[1]
    if rule.get("mode") == "weekday":
        days: set[int] = set()
        for wo in rule.get("weekdays", []):
            d = _nth_weekday_day(year, month, int(wo["weekday"]), int(wo["week"]))
            if d:
                days.add(d)
        return sorted(days)
    # 기본: 특정일 지정
    return sorted({d for d in rule.get("days_of_month", []) if 1 <= d <= last_day})


def compute_occurrences(template: dict, year: int, month: int) -> List[Dict[str, Any]]:
    """해당 연·월의 회차 목록을 계산한다. (생성은 안 함)

    반환 항목: { day, occurrence_date, round_label, title, occurrence_dt(aware UTC) }
    회차 라벨은 날짜순 순번에서 파생하므로 지정 방식(날짜/요일)과 무관하게 동일하다.
    """
    rule = template.get("rule", {})
    time_str = rule.get("time", "09:00")
    hh, mm = (int(x) for x in time_str.split(":"))
    base_title = template.get("blueprint", {}).get("title", "").strip() or template.get("name", "반복 업무")

    days = _rule_days(rule, year, month)
    out: List[Dict[str, Any]] = []
    for idx, day in enumerate(days):
        round_label = f"{month}월 {idx + 1}차"
        occ_dt_kst = KST.localize(datetime(year, month, day, hh, mm))
        out.append({
            "day": day,
            "occurrence_date": f"{year:04d}-{month:02d}-{day:02d}",
            "round_label": round_label,
            "title": f"{base_title} - {round_label}",
            "occurrence_dt": occ_dt_kst.astimezone(timezone.utc),
        })
    return out


# ── 이슈 생성 ────────────────────────────────────────────────────────────────

async def _existing_issue(template_id: ObjectId, occurrence_date: str) -> Optional[dict]:
    return await _issues_col().find_one({
        "recurring_template_id": template_id,
        "occurrence_date": occurrence_date,
    })


async def _create_issue_from_occurrence(
    template: dict, occ: Dict[str, Any], actor_id: Optional[str],
) -> dict:
    """회차 하나를 실제 이슈로 생성한다."""
    bp = template.get("blueprint", {})
    project_id = template["project_id"]
    pid = project_id if isinstance(project_id, ObjectId) else ObjectId(project_id)
    number = await next_issue_number(pid)
    now = datetime.now(timezone.utc)

    assignee_id = bp.get("assignee_id")
    doc = {
        "project_id": pid,
        "number": number,
        "title": occ["title"],
        "description": bp.get("description"),
        "type": bp.get("type", "TASK"),
        "status": "BACKLOG",
        "priority": bp.get("priority", "MEDIUM"),
        "assignee_id": ObjectId(assignee_id) if assignee_id else None,
        "reporter_id": ObjectId(actor_id) if actor_id else None,
        "sprint_id": None,
        "epic_id": None,
        "parent_issue_id": None,
        "label_ids": [ObjectId(x) for x in bp.get("label_ids", [])],
        "start_date": occ["occurrence_dt"],
        "due_date": occ["occurrence_dt"],
        "story_points": bp.get("story_points"),
        "effort_md": bp.get("effort_md"),
        "attachments": [],
        "show_on_dashboard": bp.get("show_on_dashboard", False),
        "order": float(number),
        # 반복 메타 (중복 방지 + 시리즈 묶음)
        "recurring_template_id": template["_id"],
        "occurrence_date": occ["occurrence_date"],
        "round_label": occ["round_label"],
        "created_at": now,
        "updated_at": now,
    }
    res = await _issues_col().insert_one(doc)
    return await _issues_col().find_one({"_id": res.inserted_id})


async def generate_month(
    template: dict, year: int, month: int, actor_id: Optional[str],
) -> Dict[str, List[dict]]:
    """해당 월의 모든 회차를 생성한다. 이미 있으면 건너뜀. (수동 버튼용)"""
    created: List[dict] = []
    skipped: List[dict] = []
    for occ in compute_occurrences(template, year, month):
        existing = await _existing_issue(template["_id"], occ["occurrence_date"])
        if existing:
            skipped.append({**_occ_summary(occ), "issue_id": str(existing["_id"]), "already_exists": True})
            continue
        issue = await _create_issue_from_occurrence(template, occ, actor_id)
        created.append({**_occ_summary(occ), "issue_id": str(issue["_id"])})
    return {"created": created, "skipped": skipped}


async def generate_due(template: dict, today: datetime) -> List[dict]:
    """오늘 기준 lead 창(회차일-lead_days ~ 회차일)에 든 회차를 생성한다. (스케줄러용)

    이달·다음달 회차만 검사해 과거를 소급 생성하지 않는다.
    """
    lead = int(template.get("lead_days", 0) or 0)
    today_d = today.date()
    created: List[dict] = []

    months: List[Tuple[int, int]] = [(today.year, today.month)]
    nm_year, nm_month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    months.append((nm_year, nm_month))

    from datetime import timedelta
    for (y, m) in months:
        for occ in compute_occurrences(template, y, m):
            occ_d = occ["occurrence_dt"].astimezone(KST).date()
            create_from = occ_d - timedelta(days=lead)
            if create_from <= today_d <= occ_d:  # lead 창 안
                if await _existing_issue(template["_id"], occ["occurrence_date"]):
                    continue
                issue = await _create_issue_from_occurrence(template, occ, actor_id=None)
                created.append({**_occ_summary(occ), "issue_id": str(issue["_id"])})
    return created


def _occ_summary(occ: Dict[str, Any]) -> dict:
    return {
        "occurrence_date": occ["occurrence_date"],
        "round_label": occ["round_label"],
        "title": occ["title"],
    }


# ── 템플릿 CRUD ──────────────────────────────────────────────────────────────

async def list_templates(project_id: Optional[str] = None) -> List[dict]:
    q: dict = {}
    if project_id:
        q["project_id"] = ObjectId(project_id)
    docs = await _col().find(q).sort("created_at", -1).to_list(None)
    return [to_out(d) for d in docs]


async def get_template(template_id: str) -> Optional[dict]:
    doc = await _col().find_one({"_id": ObjectId(template_id)})
    return doc


async def create_template(data: dict, actor_email: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "project_id": ObjectId(data["project_id"]),
        "created_at": now,
        "created_by": actor_email,
        "updated_at": now,
        "updated_by": actor_email,
    }
    res = await _col().insert_one(doc)
    doc["_id"] = res.inserted_id
    return to_out(doc)


async def patch_template(template_id: str, patch: dict, actor_email: str) -> Optional[dict]:
    clean = {k: v for k, v in patch.items() if v is not None}
    if not clean:
        doc = await _col().find_one({"_id": ObjectId(template_id)})
        return to_out(doc) if doc else None
    clean["updated_at"] = datetime.now(timezone.utc)
    clean["updated_by"] = actor_email
    doc = await _col().find_one_and_update(
        {"_id": ObjectId(template_id)},
        {"$set": clean},
        return_document=True,
    )
    return to_out(doc) if doc else None


async def delete_template(template_id: str) -> bool:
    res = await _col().delete_one({"_id": ObjectId(template_id)})
    return res.deleted_count > 0
