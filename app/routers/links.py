"""URL 링크 북마크 CRUD."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import MongoClientManager
from app.models.link import LinkCreate, LinkOut, LinkPatch
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.admin import require_admin
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


def _to_out(doc: dict) -> LinkOut:
    return LinkOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        url=doc.get("url", ""),
        type=doc.get("type", ""),
        color=doc.get("color", "grey"),
        note=doc.get("note"),
        tags=doc.get("tags", []),
        rank=doc.get("rank"),
        is_visible=bool(doc.get("is_visible", True)),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[LinkOut])
async def list_links(
    visible_only: bool = True,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_links_collection()
    query = {"is_visible": True} if visible_only else {}
    docs = [doc async for doc in col.find(query)]
    docs.sort(key=lambda d: (d.get("rank") is None, d.get("rank") or 0))
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=LinkOut, status_code=201)
async def create_link(payload: LinkCreate, _=Depends(require_admin)):
    col = MongoClientManager.get_links_collection()
    doc = {
        "title": payload.title,
        "url": payload.url,
        "type": payload.type,
        "color": payload.color,
        "note": payload.note,
        "tags": payload.tags,
        "rank": payload.rank,
        "is_visible": payload.is_visible,
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{link_id}", response_model=LinkOut)
async def patch_link(link_id: str, payload: LinkPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_links_collection()
    _oid = parse_oid(link_id, "Invalid link id")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Link not found")
    return _to_out(doc)


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_links_collection()
    _oid = parse_oid(link_id, "Invalid link id")
    result = await col.delete_one({"_id": _oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Link not found")
