from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.db.mongo import MongoClientManager


async def create_notification(
    recipient_user_id: str,
    notification_type: str,
    title: str,
    message: str,
    sender_user_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_url: Optional[str] = None,
    deduplication_key: Optional[str] = None,
) -> Optional[str]:
    col = MongoClientManager.get_db()[MongoClientManager.NOTIFICATIONS]
    now = datetime.now(timezone.utc)

    if deduplication_key:
        existing = await col.find_one({
            "recipient_user_id": recipient_user_id,
            "deduplication_key": deduplication_key,
        })
        if existing:
            return str(existing["_id"])

    doc = {
        "recipient_user_id": recipient_user_id,
        "sender_user_id": sender_user_id,
        "sender_name": sender_name,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "target_type": target_type,
        "target_id": target_id,
        "target_url": target_url,
        "is_read": False,
        "read_at": None,
        "is_archived": False,
        "deduplication_key": deduplication_key,
        "created_at": now,
        "updated_at": now,
    }
    result = await col.insert_one(doc)
    return str(result.inserted_id)


async def notify_users(
    user_ids: List[str],
    notification_type: str,
    title: str,
    message: str,
    sender_user_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_url: Optional[str] = None,
    dedup_key_prefix: Optional[str] = None,
) -> None:
    for uid in set(user_ids):
        dedup = f"{dedup_key_prefix}:{uid}" if dedup_key_prefix else None
        await create_notification(
            recipient_user_id=uid,
            notification_type=notification_type,
            title=title,
            message=message,
            sender_user_id=sender_user_id,
            sender_name=sender_name,
            target_type=target_type,
            target_id=target_id,
            target_url=target_url,
            deduplication_key=dedup,
        )


async def get_sr_operator_ids() -> List[str]:
    """SR 처리자 이상 권한을 가진 사용자 ID 목록."""
    users_col = MongoClientManager.get_users_collection()
    docs = await users_col.find({
        "$or": [
            {"is_admin": True},
            {"permissions": {"$in": ["sr_operator", "sr_manager"]}},
        ]
    }, {"_id": 1}).to_list(None)
    return [str(d["_id"]) for d in docs]
