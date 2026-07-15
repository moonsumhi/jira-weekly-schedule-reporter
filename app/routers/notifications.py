from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.notification import NotificationOut, NotificationListPage, NoticeCreate
from app.routers.auth import get_current_user
from app.services.notification_service import notify_users

router = APIRouter()


def _to_out(doc: dict) -> NotificationOut:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return NotificationOut(**d)


@router.get("", response_model=NotificationListPage)
async def list_notifications(
    is_read: Optional[bool] = Query(None),
    is_archived: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    uid = str(current_user.id)

    q: dict = {"recipient_user_id": uid, "is_archived": is_archived}
    if is_read is not None:
        q["is_read"] = is_read

    total = await col.count_documents(q)
    unread_count = await col.count_documents({"recipient_user_id": uid, "is_read": False, "is_archived": False})

    docs = await col.find(q).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
    return NotificationListPage(
        items=[_to_out(d) for d in docs],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    count = await col.count_documents({
        "recipient_user_id": str(current_user.id),
        "is_read": False,
        "is_archived": False,
    })
    return {"count": count}


@router.post("/read-all", status_code=204)
async def mark_all_read(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    now = datetime.now(timezone.utc)
    await col.update_many(
        {"recipient_user_id": str(current_user.id), "is_read": False},
        {"$set": {"is_read": True, "read_at": now, "updated_at": now}},
    )


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    now = datetime.now(timezone.utc)
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 알림 ID입니다.")
    result = await col.update_one(
        {"_id": oid, "recipient_user_id": str(current_user.id)},
        {"$set": {"is_read": True, "read_at": now, "updated_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")


@router.post("/{notification_id}/archive", status_code=204)
async def archive_notification(
    notification_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    now = datetime.now(timezone.utc)
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 알림 ID입니다.")
    result = await col.update_one(
        {"_id": oid, "recipient_user_id": str(current_user.id)},
        {"$set": {"is_archived": True, "updated_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")


@router.post("/notice", status_code=201)
async def create_notice(
    body: NoticeCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    """관리자용 전체 공지 알림 발송."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    users_col = MongoClientManager.get_users_collection()
    users = await users_col.find({}, {"_id": 1}).to_list(None)
    user_ids = [str(u["_id"]) for u in users]

    await notify_users(
        user_ids=user_ids,
        notification_type="NOTICE",
        title=body.title,
        message=body.message,
        sender_user_id=str(current_user.id),
        sender_name=current_user.full_name or current_user.email,
        target_type="SYSTEM",
        target_url=body.target_url,
    )
    return {"recipients": len(user_ids)}
