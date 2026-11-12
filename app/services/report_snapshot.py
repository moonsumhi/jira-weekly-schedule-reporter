"""Refresh derived report fields without changing authored content or edit versions."""
from datetime import datetime, timezone

from fastapi import HTTPException


def is_live_report(doc: dict) -> bool:
    return doc.get("status", "DRAFT") in {"DRAFT", "REVIEWING"}


def snapshot_filter(doc: dict) -> dict:
    # A slower read must not overwrite a newer snapshot, a changed reporting
    # period/department, a concurrent confirmation, or a deleted report.
    return {
        "_id": doc["_id"], "deleted_at": None,
        "status": doc.get("status"), "updated_at": doc.get("updated_at"),
        "aggregated_at": doc.get("aggregated_at"),
    }


async def sync_report_snapshot(col, doc: dict, collect, *, aggregated_by=None) -> dict:
    for _ in range(2):
        if not is_live_report(doc):
            return doc
        snapshot = await collect(doc)
        if all(doc.get(key) == value for key, value in snapshot.items()):
            return doc
        snapshot["aggregated_at"] = datetime.now(timezone.utc)
        if aggregated_by is not None:
            snapshot["aggregated_by"] = aggregated_by
        updated = await col.find_one_and_update(
            snapshot_filter(doc), {"$set": snapshot}, return_document=True,
        )
        if updated:
            return updated
        doc = await col.find_one({"_id": doc["_id"], "deleted_at": None})
        if not doc:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")
    return doc
