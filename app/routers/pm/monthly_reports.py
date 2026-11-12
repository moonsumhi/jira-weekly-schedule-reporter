from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.reports import (
    MonthlyReportCreate, MonthlyReportPatch, MonthlyReportOut, WeeklyReportStatusPatch,
    ProjectBreakdown, PersonBreakdown, WorkItem, ReportStats, EditHistoryEntry,
)
from app.routers.auth import get_current_user
from app.routers.pm.report_agg import aggregate_period
from app.services.report_snapshot import is_live_report, snapshot_filter, sync_report_snapshot
from app.services.monthly_report_context import capture_context, AGGREGATION_VERSION
from app.services.monthly_report_scheduler import SYSTEM_USER, TEAM
from app.routers.pm.weekly_reports import (
    _require_pm, _history_entry, _user_name, _excel_response, _write_items_table,
    STATUS_KO, PRIORITY_KO, STATUS_ISSUE_KO,
)

router = APIRouter()


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


def _doc_to_out(doc: dict) -> MonthlyReportOut:
    return MonthlyReportOut(
        id=str(doc["_id"]),
        report_year=doc["report_year"],
        report_month=doc["report_month"],
        title=doc["title"],
        department=doc.get("department"),
        status=doc.get("status", "DRAFT"),
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
        confirmed_by=str(doc["confirmed_by"]) if doc.get("confirmed_by") else None,
        confirmed_at=doc.get("confirmed_at"),
        aggregated_at=doc.get("aggregated_at"),
        highlights=doc.get("highlights") or {},
        insights=doc.get("insights") or [],
        comparison=doc.get("comparison"),
        operational_summary=doc.get("operational_summary"),
        edit_history=[
            EditHistoryEntry(
                editor_id=str(e["editor_id"]),
                editor_name=e.get("editor_name"),
                action=e.get("action", "수정"),
                edited_at=e["edited_at"],
            )
            for e in doc.get("edit_history", [])
        ],
    )


def _mask_operational(out: MonthlyReportOut, user: UserPublic) -> None:
    if not out.operational_summary or user.is_admin:
        return
    summary = dict(out.operational_summary)
    if "sr" not in (user.permissions or []):
        summary["sr"] = None
    if "server_check" not in (user.permissions or []):
        summary["inspection_reports"] = None
    out.operational_summary = summary


async def _hide_feedback_memos(out: MonthlyReportOut) -> None:
    # Older accepted items embedded the private note before the report text.
    # Strip only the exact stored note, leaving the saved data and other edits intact.
    ids = [item.id.removeprefix('feedback-') for item in out.insights
           if item.id.startswith('feedback-') and ObjectId.is_valid(item.id.removeprefix('feedback-'))]
    if not ids:
        return
    docs = await MongoClientManager.get_db()['pm_monthly_feedback'].find(
        {'_id': {'$in': [ObjectId(value) for value in ids]}}, {'comment': 1}
    ).to_list(None)
    notes = {str(doc['_id']): doc.get('comment', '') for doc in docs}
    for item in out.insights:
        key = item.id.removeprefix('feedback-')
        if item.id.startswith('feedback-') and key in notes:
            prefix = f"팀장님 코멘트: {notes[key]}\n\n"
            if item.content.startswith(prefix):
                item.content = item.content[len(prefix):]


async def _enrich(out: MonthlyReportOut, doc: dict, user: UserPublic) -> MonthlyReportOut:
    out.created_by_name = "시스템" if doc.get("created_by") == SYSTEM_USER else await _user_name(doc.get("created_by"))
    out.updated_by_name = await _user_name(doc.get("updated_by"))
    out.aggregated_by_name = "시스템" if doc.get("aggregated_by") == SYSTEM_USER else await _user_name(doc.get("aggregated_by"))
    _mask_operational(out, user)
    await _hide_feedback_memos(out)
    return out


def _month_range(year: int, month: int):
    last = monthrange(year, month)[1]
    kst = timezone(timedelta(hours=9))
    start = datetime(year, month, 1, tzinfo=kst).astimezone(timezone.utc)
    end = (datetime(year, month, last, tzinfo=kst) + timedelta(days=1) - timedelta(microseconds=1)).astimezone(timezone.utc)
    return start, end


def _next_month_range(year: int, month: int):
    nm = month + 1
    ny = year
    if nm > 12:
        nm = 1; ny += 1
    return _month_range(ny, nm)


# ════════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[MonthlyReportOut])
async def list_monthly_reports(
    year:  Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    col = MongoClientManager.get_pm_monthly_reports_collection()
    q: dict = {"deleted_at": None}
    if year:  q["report_year"]  = year
    if month: q["report_month"] = month
    docs = await col.find(q).sort([("report_year", -1), ("report_month", -1)]).to_list(None)
    result = []
    for doc in docs:
        result.append(await _enrich(_doc_to_out(doc), doc, current_user))
    return result


# NOTE: /export/list must be defined BEFORE /{report_id} to avoid FastAPI route conflict
@router.get("/export/list")
async def export_monthly_list(
    year:  Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    col = MongoClientManager.get_pm_monthly_reports_collection()
    q: dict = {"deleted_at": None}
    if year:  q["report_year"]  = year
    if month: q["report_month"] = month
    docs = await col.find(q).sort([("report_year", -1), ("report_month", -1)]).to_list(None)

    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "월간보고 목록"
    hf    = PatternFill("solid", fgColor="2F75B6")
    hfont = Font(color="FFFFFF", bold=True)

    headers = ["연도", "월", "부서", "제목", "총", "완료", "진행", "지연", "완료율", "작성자", "작성일", "상태"]
    for ci, h in enumerate(headers, 1):
        c = ws.cell(1, ci, h); c.fill = hf; c.font = hfont
        c.alignment = Alignment(horizontal="center")

    for ri, doc in enumerate(docs, 2):
        s = doc.get("stats", {})
        ws.cell(ri, 1, doc["report_year"])
        ws.cell(ri, 2, f"{doc['report_month']}월")
        ws.cell(ri, 3, doc.get("department") or "")
        ws.cell(ri, 4, doc["title"])
        ws.cell(ri, 5, s.get("total", 0))
        ws.cell(ri, 6, s.get("completed", 0))
        ws.cell(ri, 7, s.get("in_progress", 0))
        ws.cell(ri, 8, s.get("delayed", 0))
        ws.cell(ri, 9, f"{s.get('completion_rate', 0)}%")
        ws.cell(ri, 10, await _user_name(doc.get("created_by")) or "")
        ws.cell(ri, 11, doc["created_at"].strftime("%Y-%m-%d"))
        ws.cell(ri, 12, STATUS_KO.get(doc.get("status", "DRAFT"), doc.get("status", "DRAFT")))

    for ci in range(1, 13):
        ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = 16
    ws.column_dimensions["D"].width = 40

    return _excel_response(wb, f"월간보고목록_{year or '전체'}년.xlsx")


async def _collect_snapshot(doc: dict) -> dict:
    start_dt, end_dt = _month_range(doc["report_year"], doc["report_month"])
    ns, ne = _next_month_range(doc["report_year"], doc["report_month"])
    all_items, upcoming_items, by_project, by_person, stats = await aggregate_period(
        start_dt, end_dt, ns, ne, monthly_actuals=True
    )
    comparison, operational_summary = await capture_context(
        doc["report_year"], doc["report_month"], doc.get("department"), start_dt, end_dt,
    )
    return {
        "by_project": [p.model_dump() for p in by_project],
        "by_person": [p.model_dump() for p in by_person],
        "all_items": [i.model_dump() for i in all_items],
        "upcoming_items": [i.model_dump() for i in upcoming_items],
        "stats": stats.model_dump(), "aggregation_version": AGGREGATION_VERSION,
        "comparison": comparison, "operational_summary": operational_summary,
    }


async def _sync_snapshot(doc: dict) -> dict:
    return await sync_report_snapshot(
        MongoClientManager.get_pm_monthly_reports_collection(), doc, _collect_snapshot,
        aggregated_by=SYSTEM_USER,
    )


@router.get("/{report_id}", response_model=MonthlyReportOut)
async def get_monthly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    doc = await MongoClientManager.get_pm_monthly_reports_collection().find_one(
        {"_id": ObjectId(report_id), "deleted_at": None}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
    doc = await _sync_snapshot(doc)
    return await _enrich(_doc_to_out(doc), doc, current_user)


@router.post("", response_model=MonthlyReportOut, status_code=201)
async def create_monthly_report(
    body: MonthlyReportCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    col = MongoClientManager.get_pm_monthly_reports_collection()
    now = datetime.now(timezone.utc)

    if (body.department or '').strip() in ('', TEAM):
        existing = await col.find_one({
            'report_year': body.report_year, 'report_month': body.report_month,
            'department': {'$in': [None, '', TEAM]}, 'deleted_at': None,
        }, {'_id': 1})
        if existing:
            raise HTTPException(status_code=409, detail='해당 월의 데이터운영팀 보고서가 이미 있습니다.')

    start_dt, end_dt = _month_range(body.report_year, body.report_month)
    ns, ne = _next_month_range(body.report_year, body.report_month)
    all_items, upcoming_items, by_project, by_person, stats = await aggregate_period(
        start_dt, end_dt, ns, ne, monthly_actuals=True
    )
    comparison, operational_summary = await capture_context(body.report_year, body.report_month, body.department, start_dt, end_dt)

    result = await col.insert_one({
        "report_year":    body.report_year,
        "report_month":   body.report_month,
        "title":          body.title,
        "department":     body.department,
        "status":         "DRAFT",
        "by_project":     [p.model_dump() for p in by_project],
        "by_person":      [p.model_dump() for p in by_person],
        "all_items":      [i.model_dump() for i in all_items],
        "upcoming_items": [i.model_dump() for i in upcoming_items],
        "stats":          stats.model_dump(),
        "aggregation_version": AGGREGATION_VERSION,
        "comparison": comparison,
        "operational_summary": operational_summary,
        "admin_comment":  body.admin_comment,
        "created_by":     ObjectId(current_user.id),
        "updated_by":     None,
        "created_at":     now,
        "updated_at":     now,
        "confirmed_by":   None,
        "confirmed_at":   None,
        "aggregated_at":  now,
        "aggregated_by":  ObjectId(current_user.id),
        "deleted_at":     None,
        "edit_history":   [_history_entry(current_user, "생성")],
    })
    doc = await col.find_one({"_id": result.inserted_id})
    return await _enrich(_doc_to_out(doc), doc, current_user)


@router.patch("/{report_id}", response_model=MonthlyReportOut)
async def patch_monthly_report(
    report_id: str,
    body: MonthlyReportPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    col = MongoClientManager.get_pm_monthly_reports_collection()
    doc = await col.find_one({"_id": ObjectId(report_id), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    if doc.get("status", "DRAFT") == "CONFIRMED":
        raise HTTPException(status_code=409, detail="확정된 보고서는 수정할 수 없습니다.")
    patch = body.model_dump(exclude_unset=True)
    expected_updated_at = patch.pop("expected_updated_at", None)
    if "department" in patch and (patch["department"] or "") != (doc.get("department") or ""):
        patch["comparison"] = None
    patch["updated_by"] = ObjectId(current_user.id)
    patch["updated_at"] = datetime.now(timezone.utc)

    update_filter = {"_id": ObjectId(report_id), "deleted_at": None, "status": {"$ne": "CONFIRMED"}}
    if expected_updated_at is not None:
        update_filter["updated_at"] = expected_updated_at
    updated = await col.find_one_and_update(
        update_filter,
        {"$set": patch, "$push": {"edit_history": _history_entry(current_user, "수정")}},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="보고서가 변경되어 저장할 수 없습니다. 내용을 보관한 뒤 최신 보고서를 다시 불러와 주세요.")
    return await _enrich(_doc_to_out(updated), updated, current_user)


@router.post("/{report_id}/refresh", response_model=MonthlyReportOut)
async def refresh_monthly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """이슈 데이터를 다시 집계하여 보고서 내용을 최신화합니다."""
    _require_pm(current_user)
    col = MongoClientManager.get_pm_monthly_reports_collection()
    doc = await col.find_one({"_id": ObjectId(report_id), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    if doc.get("status", "DRAFT") not in {"DRAFT", "REVIEWING"}:
        raise HTTPException(status_code=409, detail="확정 전 보고서만 재집계할 수 있습니다.")
    snapshot = await _collect_snapshot(doc)
    updated = await col.find_one_and_update(
        {"_id": ObjectId(report_id), "deleted_at": None, "department": doc.get("department"), "$or": [{"status": {"$in": ["DRAFT", "REVIEWING"]}}, {"status": {"$exists": False}}]},
        {
            "$set": {
                **snapshot,
                "aggregated_at":  datetime.now(timezone.utc),
                "aggregated_by":  ObjectId(current_user.id),
                "updated_by":     ObjectId(current_user.id),
                "updated_at":     datetime.now(timezone.utc),
            },
            "$push": {"edit_history": _history_entry(current_user, "데이터 새로고침")},
        },
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="보고서 상태가 변경되어 재집계할 수 없습니다.")
    return await _enrich(_doc_to_out(updated), updated, current_user)


@router.patch("/{report_id}/status", response_model=MonthlyReportOut)
async def change_monthly_report_status(report_id: str, body: WeeklyReportStatusPatch, current_user: UserPublic = Depends(get_current_user)):
    _require_pm(current_user)
    if body.status not in {"DRAFT", "REVIEWING", "CONFIRMED"}:
        raise HTTPException(status_code=400, detail="유효하지 않은 상태값입니다.")
    col = MongoClientManager.get_pm_monthly_reports_collection()
    doc = await col.find_one({"_id": ObjectId(report_id), "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
    now = datetime.now(timezone.utc)
    update = {"status": body.status, "updated_by": ObjectId(current_user.id), "updated_at": now,
              "confirmed_by": ObjectId(current_user.id) if body.status == "CONFIRMED" else None,
              "confirmed_at": now if body.status == "CONFIRMED" else None}
    if body.status == "CONFIRMED" and is_live_report(doc):
        update.update(await _collect_snapshot(doc))
        update.update(aggregated_at=now, aggregated_by=ObjectId(current_user.id))
    updated = await col.find_one_and_update(
        snapshot_filter(doc),
        {"$set": update,
         "$push": {"edit_history": _history_entry(current_user, f"상태 변경: {STATUS_KO[body.status]}")}},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="보고서가 변경되었습니다. 새로고침 후 다시 확인해 주세요.")
    updated = await _sync_snapshot(updated)
    return await _enrich(_doc_to_out(updated), updated, current_user)


@router.delete("/{report_id}", status_code=204)
async def delete_monthly_report(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    linked_feedback = await MongoClientManager.get_db()['pm_monthly_feedback'].find_one({
        '$or': [{'source_report_id': report_id}, {'target_report_id': report_id}],
        'status': {'$ne': 'CANCELLED'},
    }, {'_id': 1})
    if linked_feedback:
        raise HTTPException(status_code=409, detail='피드백 요청과 연결된 보고서는 삭제할 수 없습니다.')
    col = MongoClientManager.get_pm_monthly_reports_collection()
    result = await col.update_one(
        {"_id": ObjectId(report_id), "deleted_at": None, "status": {"$ne": "CONFIRMED"}},
        {"$set": {"deleted_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        if await col.find_one({"_id": ObjectId(report_id), "deleted_at": None}):
            raise HTTPException(status_code=409, detail="확정된 보고서는 삭제할 수 없습니다.")
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")


@router.get("/{report_id}/export")
async def export_monthly_detail(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    _require_pm(current_user)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    doc = await MongoClientManager.get_pm_monthly_reports_collection().find_one(
        {"_id": ObjectId(report_id), "deleted_at": None}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
    doc = await _sync_snapshot(doc)

    r = _doc_to_out(doc)
    _mask_operational(r, current_user)
    await _hide_feedback_memos(r)
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
        ("보고 기간", f"{r.report_year}년 {r.report_month}월"),
        ("부서", r.department or ""), ("작성자", r.created_by_name or ""),
        ("상태", STATUS_KO.get(r.status, r.status)),
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

    summary = wb.create_sheet("월간 요약")
    def text_cell(ws, row, column, value):
        cell = ws.cell(row, column, value)
        if isinstance(value, str):
            cell.data_type = "s"
        return cell
    summary.column_dimensions["A"].width = 22
    summary.column_dimensions["B"].width = 85
    row = 1
    for label, value in [("주요 성과", r.highlights.accomplishments), ("주의 사항", r.highlights.concerns),
                         ("차월 핵심 계획", r.highlights.next_plans)]:
        summary.cell(row, 1, label).font = bold
        text_cell(summary, row, 2, value).alignment = Alignment(wrap_text=True, vertical="top")
        row += 1
    if r.comparison:
        summary.cell(row, 1, "전월 비교 기준").font = bold
        text_cell(summary, row, 2, r.comparison.get("title", ""))
        row += 1
        previous = r.comparison.get("stats", {})
        for label, key, current in [("완료", "completed", r.stats.completed), ("진행 중", "in_progress", r.stats.in_progress), ("지연", "delayed", r.stats.delayed)]:
            summary.cell(row, 1, label)
            summary.cell(row, 2, f"전월 {previous.get(key, 0)} · 이번 달 {current}")
            row += 1
    delayed_items = sorted((item for item in r.all_items if item.is_delayed and item.due_date),
                           key=lambda item: item.due_date.isoformat())[:5]
    for item in delayed_items:
        summary.cell(row, 1, "오래 지연된 업무")
        due = item.due_date if item.due_date.tzinfo else item.due_date.replace(tzinfo=timezone.utc)
        due_kst = due.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
        text_cell(summary, row, 2, f"{item.project_name}-{item.issue_number} · {item.title} · 마감일 {due_kst}")
        row += 1
    if r.operational_summary:
        summary.cell(row, 1, "운영 현황 범위").font = bold
        text_cell(summary, row, 2, "전체 SR과 서버 점검 결과서 기준 (부서별 필터 없음)")
        row += 1
        sr = r.operational_summary.get("sr")
        if sr is not None:
            summary.cell(row, 1, "SR 현황").font = bold
            summary.cell(row, 2, f"접수 {sr.get('received', 0)} · 완료 {sr.get('completed', 0)} · 기준일 처리 중 {sr.get('open', 0)}")
            row += 1
            summary.cell(row, 1, "SR 집계 기준일")
            as_of = r.operational_summary.get("as_of")
            text_cell(summary, row, 2, str(as_of) if as_of else "")
            row += 1
        inspection_month = r.operational_summary.get("inspection_month")
        for inspection in r.operational_summary.get("inspection_reports") or []:
            summary.cell(row, 1, f"서버 점검 ({inspection_month or '기준 변경 전'})")
            text_cell(summary, row, 2, inspection.get('title', ''))
            row += 1
            if (r.operational_summary.get('inspection_detail_version') or 0) < 1:
                text_cell(summary, row, 2, '서버 점검 이슈 상세가 집계되지 않았습니다.')
                row += 1
                continue
            if not inspection.get('source_available'):
                text_cell(summary, row, 2, '점검 측정 데이터가 없어 서버별 이슈를 확인할 수 없습니다.')
                row += 1
            for issue in inspection.get('issues') or []:
                summary.cell(row, 1, '서버 점검 이슈')
                findings = ' · '.join(f.get('label', '') for f in issue.get('findings') or []) or '조치 내용 확인 필요'
                action_status = {'resolved': '조치 완료', 'pending': '조치 중', 'unregistered': '조치 미등록'}.get(issue.get('action_status'), '')
                details = [issue.get('host_name', ''), issue.get('ip', ''), findings, action_status,
                           issue.get('source_note', ''), issue.get('action_memo', '')]
                text_cell(summary, row, 2, ' · '.join(str(value) for value in details if value)).alignment = Alignment(wrap_text=True, vertical='top')
                row += 1
            if r.operational_summary.get('inspection_detail_version') == 1:
                summary.cell(row, 1, '미완료 점검 이슈')
                text_cell(summary, row, 2, '새 기준으로 재집계하면 미완료 이슈가 표시됩니다.')
                row += 1
            elif not inspection.get('task_data_available'):
                summary.cell(row, 1, '미완료 점검 이슈')
                text_cell(summary, row, 2, '점검 이슈 데이터가 없습니다.')
                row += 1
            elif not inspection.get('incomplete_issues'):
                summary.cell(row, 1, '미완료 점검 이슈')
                text_cell(summary, row, 2, '완료되지 않은 점검 이슈가 없습니다.')
                row += 1
            for item in inspection.get('incomplete_issues') or []:
                summary.cell(row, 1, '미완료 점검 이슈')
                text_cell(summary, row, 2, ' · '.join(str(value) for value in
                    (item.get('status'), item.get('issue_key'), item.get('title'), item.get('result'), item.get('reason'), item.get('detail'), item.get('assignee'), item.get('due_date')) if value)).alignment = Alignment(wrap_text=True, vertical='top')
                row += 1
            for note in inspection.get('notes') or []:
                summary.cell(row, 1, '점검 추가 기재사항')
                text_cell(summary, row, 2, note).alignment = Alignment(wrap_text=True, vertical='top')
                row += 1

    if r.insights:
        ws_insights = wb.create_sheet("주요 항목")
        headings = ["구분", "제목", "내용", "영향", "대응 / 요청", "담당자", "기한", "계획일", "예상일", "상태 / 변경 사유", "출처"]
        for ci, heading in enumerate(headings, 1):
            cell = ws_insights.cell(1, ci, heading); cell.fill = hf; cell.font = hfont
        kind_labels = {"MAIN_AGENDA": "주요 안건", "ISSUE_RISK": "이슈·리스크", "DECISION_REQUIRED": "결정 요청", "MILESTONE": "주요 일정"}
        for ri, item in enumerate(r.insights, 2):
            for ci, value in enumerate([kind_labels.get(item.kind, item.kind), item.title, item.content, item.impact,
                                         item.action_plan, item.owner, item.due_date, item.planned_date,
                                         item.expected_date, item.status, item.source_label or ""], 1):
                text_cell(ws_insights, ri, ci, value).alignment = Alignment(wrap_text=True, vertical="top")

    for ws_title, breakdowns, next_label in [
        ("프로젝트별", r.by_project, "차월 계획"),
        ("개인별", r.by_person, "차월 계획"),
    ]:
        wsn = wb.create_sheet(ws_title); rown = 1
        for pb in breakdowns:
            name = pb.project_name if hasattr(pb, "project_name") else pb.user_name
            wsn.cell(rown, 1, f"▶ {name}").font = Font(bold=True, size=12)
            wsn.merge_cells(f"A{rown}:K{rown}"); rown += 1
            wsn.cell(rown, 1, f"완료 {pb.stats.completed} / 진행 {pb.stats.in_progress} / 지연 {pb.stats.delayed} / 완료율 {pb.stats.completion_rate}%")
            rown += 2
            for sec, items in [("완료", pb.completed), ("진행 중", pb.in_progress), ("지연", pb.delayed), (next_label, pb.upcoming)]:
                if not items: continue
                wsn.cell(rown, 1, sec).font = bold; rown += 1
                rown = _write_items_table(wsn, items, rown, hf, hfont, alt); rown += 1
            rown += 1

    ws4 = wb.create_sheet("전체 업무")
    _write_items_table(ws4, r.all_items, 1, hf, hfont, alt)

    if r.upcoming_items:
        ws5 = wb.create_sheet("차월 계획")
        _write_items_table(ws5, r.upcoming_items, 1, hf, hfont, alt)

    for ws in wb.worksheets:
        for ci in range(1, 12):
            ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = 18
        ws.column_dimensions["B"].width = 40
    summary.column_dimensions["B"].width = 85

    return _excel_response(wb, f"월간보고_{r.report_year}년_{r.report_month:02d}월.xlsx")
