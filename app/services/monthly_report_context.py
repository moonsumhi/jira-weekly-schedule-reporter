"""Capture comparable, bounded context when a monthly report is aggregated."""
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager as M

AGGREGATION_VERSION = "monthly-actuals-v1"
OPEN_SR = {"SUBMITTED", "REVIEWING", "PENDING_INFO", "APPROVED", "ASSIGNED", "IN_PROGRESS", "CONFIRMING", "ON_HOLD"}


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


async def capture_context(report_year, report_month, department, start, end):
    previous_year, previous_month = (report_year - 1, 12) if report_month == 1 else (report_year, report_month - 1)
    previous = await M.get_pm_monthly_reports_collection().find_one(
        {"report_year": previous_year, "report_month": previous_month, "department": department if department else {"$in": [None, ""]},
         "status": "CONFIRMED", "deleted_at": None, "aggregation_version": AGGREGATION_VERSION},
        sort=[("confirmed_at", -1), ("_id", -1)],
    )
    comparison = None if not previous else {
        "report_id": str(previous["_id"]), "title": previous.get("title", ""),
        "year": previous_year, "month": previous_month, "stats": previous.get("stats", {}),
    }

    cutoff = min(datetime.now(timezone.utc), end)
    db = M.get_db()
    sr_docs = await db[M.SERVICE_REQUESTS].find({"created_at": {"$lte": cutoff}, "deleted_at": None}).to_list(None)
    sr_ids = [str(doc["_id"]) for doc in sr_docs]
    histories = await db[M.SR_STATUS_HISTORIES].find({"sr_id": {"$in": sr_ids}}).sort([("changed_at", 1), ("_id", 1)]).to_list(None)
    by_sr = {}
    for event in histories:
        by_sr.setdefault(event["sr_id"], []).append(event)
    received = completed = open_count = 0
    for doc in sr_docs:
        entries = by_sr.get(str(doc["_id"]), [])
        before = [e for e in entries if _utc(e["changed_at"]) <= cutoff]
        after = [e for e in entries if _utc(e["changed_at"]) > cutoff]
        status = (after[0].get("previous_status") if after else before[-1].get("new_status") if before else doc.get("status")) or doc.get("status")
        submitted = next((_utc(e["changed_at"]) for e in entries if e.get("new_status") == "SUBMITTED" and e.get("previous_status") in ("", None, "DRAFT")), None)
        if submitted is None and not entries and doc.get("status") != "DRAFT":
            submitted = _utc(doc.get("created_at"))
        if submitted and start <= submitted <= cutoff:
            received += 1
        completion = _utc(doc.get("actual_completed_at"))
        if completion and start <= completion <= cutoff:
            completed += 1
        if status in OPEN_SR:
            open_count += 1

    # Separate finalized result reports are shown individually because their scopes may overlap.
    inspections = await db["monthly_inspection_reports"].find({
        "month": f"{report_year:04d}-{report_month:02d}", "kind": {"$in": ["RESULT", None]}, "state": "FINAL",
        "finalized_at": {"$lte": datetime.now(timezone.utc)},
    }).sort([("revision", -1), ("_id", -1)]).to_list(None)
    seen, inspection_reports = set(), []
    for doc in inspections:
        scope = doc.get("scope_key", str(doc["_id"]))
        if scope in seen:
            continue
        seen.add(scope)
        stats = doc.get("snapshot", {}).get("stats", {})
        inspection_reports.append({"id": str(doc["_id"]), "title": doc.get("title", "점검 결과서"),
                                   "planned": stats.get("planned", 0), "done": stats.get("done", 0),
                                   "pending": stats.get("pending", 0), "rolled": stats.get("rolled", 0),
                                   "danger": stats.get("danger", 0), "warning": stats.get("warning", 0)})
    return comparison, {"as_of": cutoff, "captured_at": datetime.now(timezone.utc),
                        "sr": {"received": received, "completed": completed, "open": open_count},
                        "inspection_reports": inspection_reports}
