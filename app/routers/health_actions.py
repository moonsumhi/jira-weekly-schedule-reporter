"""서버 점검 조치 내역 — 조치 등록/수정/삭제"""
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()


class ActionCreate(BaseModel):
    memo: str = ""
    images: list[str] = []   # base64 data-URL strings
    is_resolved: bool = True


class ActionOut(BaseModel):
    id: str
    report_id: str
    host_name: str
    memo: str
    images: list[str]
    actor: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_resolved: bool


def _fmt(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def _to_out(doc: dict) -> ActionOut:
    return ActionOut(
        id=str(doc["_id"]),
        report_id=doc.get("report_id", ""),
        host_name=doc.get("host_name", ""),
        memo=doc.get("memo", ""),
        images=doc.get("images", []),
        actor=doc.get("actor", ""),
        created_at=_fmt(doc.get("created_at")),
        updated_at=_fmt(doc.get("updated_at")),
        is_resolved=doc.get("is_resolved", True),
    )


@router.get("/{report_id}/actions", response_model=list[ActionOut])
async def list_actions(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_db()[MongoClientManager.HEALTH_ACTIONS]
    docs = [doc async for doc in col.find({"report_id": report_id})]
    return [_to_out(d) for d in docs]


@router.post(
    "/{report_id}/actions/{host_name:path}",
    response_model=ActionOut,
    status_code=status.HTTP_200_OK,
)
async def upsert_action(
    report_id: str,
    host_name: str,
    payload: ActionCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    host_name = unquote(host_name)
    col = MongoClientManager.get_db()[MongoClientManager.HEALTH_ACTIONS]
    actor = current_user.full_name or current_user.email
    now = datetime.now(timezone.utc)

    existing = await col.find_one({"report_id": report_id, "host_name": host_name})
    if existing:
        await col.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "memo": payload.memo,
                "images": payload.images,
                "is_resolved": payload.is_resolved,
                "actor": actor,
                "actor_email": current_user.email,
                "updated_at": now,
            }},
        )
        doc = await col.find_one({"_id": existing["_id"]})
    else:
        doc = {
            "report_id": report_id,
            "host_name": host_name,
            "memo": payload.memo,
            "images": payload.images,
            "is_resolved": payload.is_resolved,
            "actor": actor,
            "actor_email": current_user.email,
            "created_at": now,
            "updated_at": now,
        }
        result = await col.insert_one(doc)
        doc["_id"] = result.inserted_id

    return _to_out(doc)


@router.delete("/{report_id}/actions/{host_name:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    report_id: str,
    host_name: str,
    current_user: UserPublic = Depends(get_current_user),
):
    host_name = unquote(host_name)
    col = MongoClientManager.get_db()[MongoClientManager.HEALTH_ACTIONS]
    result = await col.delete_one({"report_id": report_id, "host_name": host_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="조치 내역이 없습니다.")
