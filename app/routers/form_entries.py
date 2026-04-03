"""Form entry CRUD endpoints — stores submitted data for a form template."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()


class FormEntryCreate(BaseModel):
    template_id: str
    data: dict[str, Any]  # {sectionTitle: {fieldLabel: value}}


class FormEntryPatch(BaseModel):
    data: dict[str, Any]
    version: int


class FormEntryOut(BaseModel):
    id: str
    template_id: str
    data: dict[str, Any]
    version: int
    is_deleted: bool
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_out(doc: dict) -> FormEntryOut:
    def _fmt(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return FormEntryOut(
        id=str(doc["_id"]),
        template_id=doc.get("template_id", ""),
        data=doc.get("data", {}),
        version=doc.get("version", 1),
        is_deleted=doc.get("is_deleted", False),
        created_at=_fmt(doc.get("created_at")),
        created_by=doc.get("created_by"),
        updated_at=_fmt(doc.get("updated_at")),
        updated_by=doc.get("updated_by"),
    )


@router.get("", response_model=list[FormEntryOut])
async def list_entries(
    template_id: str = Query(...),
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    query: dict = {"template_id": template_id}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    cursor = col.find(query).sort("created_at", -1)
    return [_to_out(doc) async for doc in cursor]


@router.post("", response_model=FormEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: FormEntryCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    now = _now()
    doc = {
        "template_id": payload.template_id,
        "data": payload.data,
        "version": 1,
        "is_deleted": False,
        "created_at": now,
        "created_by": current_user.email,
        "updated_at": now,
        "updated_by": current_user.email,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{entry_id}", response_model=FormEntryOut)
async def patch_entry(
    entry_id: str,
    payload: FormEntryPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry id")

    now = _now()
    result = await col.find_one_and_update(
        {"_id": oid, "version": payload.version, "is_deleted": {"$ne": True}},
        {"$set": {"data": payload.data, "updated_at": now, "updated_by": current_user.email},
         "$inc": {"version": 1}},
        return_document=True,
    )
    if result is None:
        doc = await col.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        raise HTTPException(status_code=409, detail="Version conflict")
    return _to_out(result)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry id")

    result = await col.update_one(
        {"_id": oid, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "updated_at": _now(), "updated_by": current_user.email}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
