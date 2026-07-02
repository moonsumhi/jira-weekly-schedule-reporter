from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.reports import (
    WeeklyReportCreate, WeeklyReportPatch, WeeklyReportOut,
    ProjectBreakdown, PersonBreakdown, WorkItem, ReportStats,
)
from app.routers.auth import get_current_user
from app.routers.pm.report_agg import aggregate_period

router = APIRouter()

STATUS_KO       = {"DRAFT": "초안", "PUBLISHED": "게시됨", "ARCHIVED": "보관됨"}
PRIORITY_KO     = {"LOWEST": "최하", "LOW": "낮음", "MEDIUM": "중간", "HIGH": "높음", "HIGHEST": "최고"}
STATUS_ISSUE_KO = {
    "BACKLOG": "백로그", "TODO": "할 일",
    "IN_PROGRESS": "진행 중", "IN_REVIEW": "검토 중", "DONE": "완료",
}


def _require_admin(user: UserPublic):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")


async def _user_name(uid) -> Optional[str]:
    if not uid:
        return None
    u = await MongoClientManager.get_users_collection().find_one(
        {"_id": ObjectId(str(uid))}, {"full_name": 1, "email": 1}
    )
    return (u.get("full_name") or u.get("email")) if u else None


def _parse_items(raw: list) -> list[WorkItem]:
    return [WorkItem(**i) for i in raw]


def _parse_breakdown(raw: list, cls):
    result = []
    for d in raw:
        for key in ("completed", "in_progress", "delayed", "upcoming"):
            if key in d:
                d[key] = [WorkItem(**i) for i in d[key]]
        if "stats" in d and isinstance(d["stats"], dict):
            d["stats"] = ReportStats(**d["stats"])
        result.append(cls(**d))
    return result


def _doc_to_out(doc: dict) -> WeeklyReportOut:
    return WeeklyReportOut(
        id=str(doc["_id"]),
        report_year=doc["report_year"],
        report_week=doc["report_week"],
        start_date=doc["start_date"],
        end_date=doc["end_date"],
        title=doc["title"],
        department=doc.get("department"),
        by_project=_parse_breakdown(doc.get("by_project", []), ProjectBreakdown),
        by_person=_parse_breakdown(doc.get("by_person", []), PersonBreakdown),
        all_items=_parse_items(doc.get("all_items", [])),
        upcoming_items=_parse_items(doc.get("upcoming_items", [])),
        stats=ReportStats(**doc["stats"]) if doc.get("stats") else ReportStats(),
        admin_comment=doc.get("admin_comment"),
        created_by=str(doc["created_by"]),
        created_by_name=None,
        created_at=doc["created_at"],
        updated_by=str(doc["updated_by"]) if doc.get("updated_by") else None,
        updated_by_name=None,
        updated_at=doc["updated_at"],
    )


async def _enrich(out: WeeklyReportOut, doc: dict) -> WeeklyReportOut:
    out.created_by_name = await _user_name(doc.get("created_by"))
    out.updated_by_name = await _user_name(doc.get("updated_by"))
    return out


def _next_week(start_dt: datetime, end_dt: datetime):
    delta = end_dt - start_dt + timedelta(seconds=1)
    ns = end_dt + timedelta(seconds=1)
    return ns, ns + delta - timedelta(seconds=1)


def _excel_response(wb, filename: str) -> StreamingResponse:
    import io
    from urllib.parse import quote
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _write_items_table(ws, items: list, start_row: int, hf, hfont, alt):
    import openpyxl
    from openpyxl.styles import Alignment
    headers = ["번호", "업무명", "에픽", "스프린트", "담당자", "우선순위", "상태", "시작일", "마감일", "SP", "지연"]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=start_row, column=ci, value=h)
        c.fill = hf; c.font = hfont
        c.alignment = Alignment(horizontal="center")
    for ri, item in enumerate(items, start_row + 1):
        vals = [
            f"{item['project_name']}-{item['issue_number']}" if isinstance(item, dict) else f"{item.project_name}-{item.issue_number}",
            item['title'] if isinstance(item, dict) else item.title,
            (item.get('epic_title') or "") if isinstance(item, dict) else (item.epic_title or ""),
            (item.get('sprint_name') or "") if isinstance(item, dict) else (item.sprint_name or ""),
            (item.get('assignee_name') or "미지정") if isinstance(item, dict) else (item.assignee_name or "미지정"),
            PRIORITY_KO.get(item['priority'] if isinstance(item, dict) else item.priority, ""),
            STATUS_ISSUE_KO.get(item['status'] if isinstance(item, dict) else item.status, ""),
            "",  # start_date handled below
            "",  # due_date handled below
            (item.get('story_points') or "") if isinstance(item, dict) else (item.story_points or ""),
            "지연" if (item.get('is_delayed') if isinstance(item, dict) else item.is_delayed) else "",
        ]
        sd = item.get('start_date') if isinstance(item, dict) else item.start_date
        dd = item.get('due_date')   if isinstance(item, dict) else item.due_date
        vals[7] = sd.strftime("%Y-%m-%d") if sd else ""
        vals[8] = dd.strftime("%Y-%m-%d") if dd else ""
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=ri, column=ci, value=v)
            if ri % 2 == 0:
                c.fill = alt
    return start_row + 1 + len(items)


# ════════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[WeeklyReportOut])
async def list_weekly_reports(
    year: Optional[int] = Query(None),
    week: Optional[int] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    col = MongoClientManager.get_pm_weekly_reports_collection()
    q: dict = {"deleted_at": None}
    if year: q["report_year"] = year
    if week: q["report_week"] = week
    docs = await col.find(q).sort([("report_year", -1), ("report_week", -1)]).to_list(None)
    result = []
    for doc in docs:
        out = _doc_to_out(doc)
        out.created_by_name = await _user_name(doc.get("created_by"))
        result.append(out)
    return result


# NOTE: /export/list must be defined BEFORE /{report_id} to avoid FastAPI route conflict
@router.get("/export/list")
async def export_weekly_list(
    year: Optional[int] = Query(None),
    week: Optional[int] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    col = MongoClientManager.get_pm_weekly_reports_collection()
    q: dict = {"deleted_at": None}
    if year: q["report_year"] = year
    if week: q["report_week"] = week
    docs = await col.find(q).sort([("report_year", -1), ("report_week", -1)]).to_list(None)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "주간보고 목록"
    hf    = PatternFill("solid", fgColor="2F75B6")
    hfont = Font(color="FFFFFF", bold=True)

    headers = ["연도", "주차", "보고 기간", "부서", "제목", "총", "완료", "진행", "지연", "완료율"]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(1, ci, h); c.fill = hf; c.font = hfont
        c.alignment = Alignment(horizontal="center")

    for ri, doc in enumerate(docs, 2):
        s = doc.get("stats", {})
        ws.cell(ri, 1, doc["report_year"])
        ws.cell(ri, 2, f"{doc['report_week']}주")
        ws.cell(ri, 3, f"{doc['start_date'].strftime('%m/%d')}~{doc['end_date'].strftime('%m/%d')}")
        ws.cell(ri, 4, doc.get("department") or "")
        ws.cell(ri, 5, doc["title"])
        ws.cell(ri, 6, s.get("total", 0))
        ws.cell(ri, 7, s.get("completed", 0))
        ws.cell(ri, 8, s.get("in_progress", 0))
        ws.cell(ri, 9, s.get("delayed", 0))
        ws.cell(ri, 10, f"{s.get('completion_rate', 0)}%")

    for ci in range(1, 11):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = 16
    ws.column_dimensions["E"].width = 40

    return _excel_response(wb, f"주간보고목록_{year or '전체'}년.xlsx")


@router.get("/{report_id}", response_model=WeeklyReportOut)
async def get_weekly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    doc = await MongoClientManager.get_pm_weekly_reports_collection().find_one(
        {"_id": ObjectId(report_id), "deleted_at": None}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
    return await _enrich(_doc_to_out(doc), doc)


@router.post("", response_model=WeeklyReportOut, status_code=201)
async def create_weekly_report(
    body: WeeklyReportCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    col = MongoClientManager.get_pm_weekly_reports_collection()
    now = datetime.now(timezone.utc)

    ns, ne = _next_week(body.start_date, body.end_date)
    all_items, upcoming_items, by_project, by_person, stats = await aggregate_period(
        body.start_date, body.end_date, ns, ne
    )

    result = await col.insert_one({
        "report_year":    body.report_year,
        "report_week":    body.report_week,
        "start_date":     body.start_date,
        "end_date":       body.end_date,
        "title":          body.title,
        "department":     body.department,
        "by_project":     [p.model_dump() for p in by_project],
        "by_person":      [p.model_dump() for p in by_person],
        "all_items":      [i.model_dump() for i in all_items],
        "upcoming_items": [i.model_dump() for i in upcoming_items],
        "stats":          stats.model_dump(),
        "admin_comment":  body.admin_comment,
        "created_by":     ObjectId(current_user.id),
        "updated_by":     None,
        "created_at":     now,
        "updated_at":     now,
        "deleted_at":     None,
    })
    doc = await col.find_one({"_id": result.inserted_id})
    return await _enrich(_doc_to_out(doc), doc)


@router.patch("/{report_id}", response_model=WeeklyReportOut)
async def patch_weekly_report(
    report_id: str,
    body: WeeklyReportPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    col = MongoClientManager.get_pm_weekly_reports_collection()
    doc = await col.find_one({"_id": ObjectId(report_id), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    patch = body.model_dump(exclude_unset=True)
    patch["updated_by"] = ObjectId(current_user.id)
    patch["updated_at"] = datetime.now(timezone.utc)

    updated = await col.find_one_and_update(
        {"_id": ObjectId(report_id)}, {"$set": patch}, return_document=True
    )
    return await _enrich(_doc_to_out(updated), updated)


@router.post("/{report_id}/refresh", response_model=WeeklyReportOut)
async def refresh_weekly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """이슈 데이터를 다시 집계하여 보고서 내용을 최신화합니다."""
    _require_admin(current_user)
    col = MongoClientManager.get_pm_weekly_reports_collection()
    doc = await col.find_one({"_id": ObjectId(report_id), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    ns, ne = _next_week(doc["start_date"], doc["end_date"])
    all_items, upcoming_items, by_project, by_person, stats = await aggregate_period(
        doc["start_date"], doc["end_date"], ns, ne
    )
    updated = await col.find_one_and_update(
        {"_id": ObjectId(report_id)},
        {"$set": {
            "by_project":     [p.model_dump() for p in by_project],
            "by_person":      [p.model_dump() for p in by_person],
            "all_items":      [i.model_dump() for i in all_items],
            "upcoming_items": [i.model_dump() for i in upcoming_items],
            "stats":          stats.model_dump(),
            "updated_by":     ObjectId(current_user.id),
            "updated_at":     datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return await _enrich(_doc_to_out(updated), updated)


@router.delete("/{report_id}", status_code=204)
async def delete_weekly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await MongoClientManager.get_pm_weekly_reports_collection().update_one(
        {"_id": ObjectId(report_id), "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")


@router.get("/{report_id}/export")
async def export_weekly_detail(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_admin(current_user)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    doc = await MongoClientManager.get_pm_weekly_reports_collection().find_one(
        {"_id": ObjectId(report_id), "deleted_at": None}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    r = _doc_to_out(doc)
    r.created_by_name = await _user_name(doc.get("created_by"))

    hf    = PatternFill("solid", fgColor="2F75B6")
    hfont = Font(color="FFFFFF", bold=True)
    alt   = PatternFill("solid", fgColor="DCE6F1")
    bold  = Font(bold=True)

    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "개요"
    ws1["A1"] = r.title; ws1["A1"].font = Font(bold=True, size=14)
    ws1.merge_cells("A1:F1")
    for i, (lbl, val) in enumerate([
        ("보고 기간", f"{r.report_year}년 {r.report_week}주차 ({r.start_date.strftime('%m/%d')}~{r.end_date.strftime('%m/%d')})"),
        ("부서", r.department or ""), ("작성자", r.created_by_name or ""),
    ], 3):
        ws1.cell(i, 1, lbl).font = bold; ws1.cell(i, 2, val)

    row = 8
    ws1.cell(row, 1, "업무 통계").font = Font(bold=True, size=12); row += 1
    for lbl, val in [("총 업무", r.stats.total), ("완료", r.stats.completed),
                     ("진행 중", r.stats.in_progress), ("지연", r.stats.delayed),
                     ("완료율", f"{r.stats.completion_rate}%")]:
        ws1.cell(row, 1, lbl).font = bold; ws1.cell(row, 2, val); row += 1

    if r.admin_comment:
        row += 1
        ws1.cell(row, 1, "관리자 코멘트").font = Font(bold=True, size=12); row += 1
        ws1.cell(row, 1, r.admin_comment)

    # 프로젝트별
    ws2 = wb.create_sheet("프로젝트별"); row2 = 1
    for pb in r.by_project:
        ws2.cell(row2, 1, f"▶ {pb.project_name}").font = Font(bold=True, size=12)
        ws2.merge_cells(f"A{row2}:K{row2}"); row2 += 1
        ws2.cell(row2, 1, f"완료 {pb.stats.completed} / 진행 {pb.stats.in_progress} / 지연 {pb.stats.delayed} / 완료율 {pb.stats.completion_rate}%")
        row2 += 2
        for sec, items in [("완료", pb.completed), ("진행 중", pb.in_progress), ("지연", pb.delayed), ("차주 계획", pb.upcoming)]:
            if not items: continue
            ws2.cell(row2, 1, sec).font = bold; row2 += 1
            row2 = _write_items_table(ws2, items, row2, hf, hfont, alt); row2 += 1
        row2 += 1

    # 개인별
    ws3 = wb.create_sheet("개인별"); row3 = 1
    for pb in r.by_person:
        ws3.cell(row3, 1, f"▶ {pb.user_name}").font = Font(bold=True, size=12)
        ws3.merge_cells(f"A{row3}:K{row3}"); row3 += 1
        ws3.cell(row3, 1, f"완료 {pb.stats.completed} / 진행 {pb.stats.in_progress} / 지연 {pb.stats.delayed} / 완료율 {pb.stats.completion_rate}%")
        row3 += 2
        for sec, items in [("완료", pb.completed), ("진행 중", pb.in_progress), ("지연", pb.delayed), ("차주 계획", pb.upcoming)]:
            if not items: continue
            ws3.cell(row3, 1, sec).font = bold; row3 += 1
            row3 = _write_items_table(ws3, items, row3, hf, hfont, alt); row3 += 1
        row3 += 1

    ws4 = wb.create_sheet("전체 업무")
    _write_items_table(ws4, r.all_items, 1, hf, hfont, alt)

    if r.upcoming_items:
        ws5 = wb.create_sheet("차주 계획")
        _write_items_table(ws5, r.upcoming_items, 1, hf, hfont, alt)

    for ws in wb.worksheets:
        for ci in range(1, 12):
            ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = 18
        ws.column_dimensions["B"].width = 40

    return _excel_response(wb, f"{r.title}.xlsx")
