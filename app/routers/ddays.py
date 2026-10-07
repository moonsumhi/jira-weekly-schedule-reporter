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


def _audience_filter(current_user: UserPublic) -> dict:
    if current_user.is_admin:
        return {}

    unrestricted_audience = {
        "$and": [
            {"$or": [
                {"visible_user_ids": {"$exists": False}},
                {"visible_user_ids": None},
                {"visible_user_ids": []},
            ]},
            {"$or": [
                {"visible_teams": {"$exists": False}},
                {"visible_teams": None},
                {"visible_teams": []},
            ]},
        ]
    }
    audience_filters = [
        {"visible_user_ids": current_user.id},
        unrestricted_audience,
        {"created_by": current_user.id},
    ]
    if current_user.team:
        audience_filters.append({"visible_teams": current_user.team})
    return {"$or": audience_filters}


def _scoped_query(base_query: dict, current_user: UserPublic) -> dict:
    audience = _audience_filter(current_user)
    if not audience:
        return base_query
    return {"$and": [base_query, audience]}


def _to_out(doc: dict) -> DDayOut:
    return DDayOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        date=doc.get("date", ""),
        color=doc.get("color", "blue"),
        note=doc.get("note"),
        visible_user_ids=[str(user_id) for user_id in (doc.get("visible_user_ids") or [])],
        visible_teams=[str(team) for team in (doc.get("visible_teams") or [])],
        created_at=fmt_dt(doc.get("created_at")),
        created_by=doc.get("created_by"),
        completed=bool(doc.get("completed") or doc.get("completed_at")),
        completed_at=fmt_dt(doc.get("completed_at")),
    )


@router.get("", response_model=list[DDayOut])
async def list_ddays(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_ddays_collection()
    active_filter = {"completed_at": None, "completed": {"$ne": True}}
    query = _scoped_query(active_filter, current_user)
    docs = [doc async for doc in col.find(query)]
    docs.sort(key=lambda d: d.get("date", ""))
    return [_to_out(doc) for doc in docs]


@router.get("/history", response_model=list[DDayOut])
async def list_dday_history(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_ddays_collection()
    completed_filter = {
        "$or": [
            {"completed": True},
            {"completed_at": {"$exists": True, "$ne": None}},
        ]
    }
    query = _scoped_query(completed_filter, current_user)
    docs = [doc async for doc in col.find(query).sort("completed_at", -1)]
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=DDayOut, status_code=201)
async def create_dday(
    payload: DDayCreate,
    current_user: UserPublic = Depends(require_admin),
):
    col = MongoClientManager.get_ddays_collection()
    doc = {
        "title": payload.title,
        "date": payload.date,
        "color": payload.color,
        "note": payload.note,
        "visible_user_ids": payload.visible_user_ids,
        "visible_teams": payload.visible_teams,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.id,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.post("/{dday_id}/complete", response_model=DDayOut)
async def complete_dday(
    dday_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_ddays_collection()
    _oid = parse_oid(dday_id, "잘못된 D-Day ID입니다.")
    doc = await col.find_one({"_id": _oid})
    if not doc:
        raise HTTPException(status_code=404, detail="D-Day를 찾을 수 없습니다.")
    if doc.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="D-Day를 등록한 사람만 완료 처리할 수 있습니다.")
    if doc.get("completed") or doc.get("completed_at"):
        return _to_out(doc)
    completed_at = datetime.now(timezone.utc)
    await col.update_one(
        {"_id": _oid, "created_by": current_user.id, "completed_at": None},
        {"$set": {"completed": True, "completed_at": completed_at, "completed_by": current_user.id}},
    )
    updated = await col.find_one({"_id": _oid})
    if not updated:
        raise HTTPException(status_code=404, detail="D-Day를 찾을 수 없습니다.")
    return _to_out(updated)


@router.patch("/{dday_id}", response_model=DDayOut)
async def patch_dday(dday_id: str, payload: DDayPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_ddays_collection()
    _oid = parse_oid(dday_id, "잘못된 D-Day ID입니다.")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")
    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="D-Day를 찾을 수 없습니다.")
    return _to_out(doc)


@router.delete("/{dday_id}", status_code=204)
async def delete_dday(dday_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_ddays_collection()
    _oid = parse_oid(dday_id, "잘못된 D-Day ID입니다.")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="D-Day를 찾을 수 없습니다.")
