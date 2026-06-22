"""D-Day 일정 CRUD."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import MongoClientManager
from app.models.dday import DDayCreate, DDayOut, DDayPatch
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.admin import require_admin
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


def _to_out(doc: dict) -> DDayOut:
    return DDayOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        date=doc.get("date", ""),
        color=doc.get("color", "blue"),
        note=doc.get("note"),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[DDayOut])
async def list_ddays(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_ddays_collection()
    docs = [doc async for doc in col.find({})]
    docs.sort(key=lambda d: d.get("date", ""))
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=DDayOut, status_code=201)
async def create_dday(payload: DDayCreate, _=Depends(require_admin)):
    col = MongoClientManager.get_ddays_collection()
    doc = {
        "title": payload.title,
        "date": payload.date,
        "color": payload.color,
        "note": payload.note,
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{dday_id}", response_model=DDayOut)
async def patch_dday(dday_id: str, payload: DDayPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_ddays_collection()
    _oid = parse_oid(dday_id, "Invalid dday id")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="D-Day not found")
    return _to_out(doc)


@router.delete("/{dday_id}", status_code=204)
async def delete_dday(dday_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_ddays_collection()
    _oid = parse_oid(dday_id, "Invalid dday id")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="D-Day not found")
