"""멘션 검증 및 알림 발송 서비스."""
from __future__ import annotations

from typing import List, Optional, Set

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.models.mention import MentionedUser
from app.services.notification_service import create_notification

MAX_MENTIONS = 20


async def resolve_mentions(
    mentioned_user_ids: List[str],
    actor_id: str,
    allowed_user_ids: Optional[Set[str]] = None,
) -> List[MentionedUser]:
    """멘션 대상 검증 후 MentionedUser 목록 반환.

    - 중복 제거, 자기 자신 제외, 차단/삭제 사용자 제외
    - allowed_user_ids 가 주어지면 그 범위 내에서만 허용
    - 최대 MAX_MENTIONS 명 제한
    """
    if not mentioned_user_ids:
        return []

    unique_ids = list(dict.fromkeys(
        uid for uid in mentioned_user_ids if uid != actor_id
    ))[:MAX_MENTIONS]

    if not unique_ids:
        return []

    users_col = MongoClientManager.get_users_collection()
    result: List[MentionedUser] = []
    for uid in unique_ids:
        try:
            oid = ObjectId(uid)
        except Exception:
            continue
        user = await users_col.find_one(
            {"_id": oid, "is_blocked": {"$ne": True}},
            {"full_name": 1, "email": 1},
        )
        if not user:
            continue
        if allowed_user_ids is not None and uid not in allowed_user_ids:
            continue
        display_name = user.get("full_name") or user.get("email", "")
        result.append(MentionedUser(user_id=uid, display_name=display_name))

    return result


async def notify_mentions(
    mentioned_users: List[MentionedUser],
    comment_id: str,
    target_type: str,
    target_id: str,
    target_title: str,
    actor_id: str,
    actor_name: str,
    target_url: str,
) -> None:
    """멘션된 사용자에게 MENTION 알림 생성."""
    for mu in mentioned_users:
        if mu.user_id == actor_id:
            continue
        await create_notification(
            recipient_user_id=mu.user_id,
            notification_type="MENTION",
            title="댓글에서 회원님을 언급했습니다.",
            message=f"{actor_name}님이 '{target_title}' 댓글에서 회원님을 언급했습니다.",
            sender_user_id=actor_id,
            sender_name=actor_name,
            target_type=target_type,
            target_id=target_id,
            target_url=target_url,
            deduplication_key=f"MENTION:{comment_id}:{mu.user_id}",
        )
