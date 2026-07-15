from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

NotificationType = Literal[
    "MENTION",
    "ASSIGNED",
    "COMMENT_CREATED",
    "STATUS_CHANGED",
    "REVIEW_REQUESTED",
    "APPROVAL_REQUESTED",
    "DUE_DATE_APPROACHING",
    "DUE_DATE_OVERDUE",
    "NOTICE",
    "SYSTEM",
]

TargetType = Literal["SR", "PM_ISSUE", "SYSTEM"]


class NotificationOut(BaseModel):
    id: str
    recipient_user_id: str
    sender_user_id: Optional[str] = None
    sender_name: Optional[str] = None
    notification_type: NotificationType
    title: str
    message: str
    target_type: Optional[TargetType] = None
    target_id: Optional[str] = None
    target_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class NotificationListPage(BaseModel):
    items: List[NotificationOut]
    total: int
    unread_count: int


class NoticeCreate(BaseModel):
    title: str
    message: str
    target_url: Optional[str] = None
