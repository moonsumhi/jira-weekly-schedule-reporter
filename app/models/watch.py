# app/models/watch.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, Field, PlainSerializer


# MongoDB returns naive datetime (no tzinfo). Serialize as UTC ISO with 'Z' suffix.
def serialize_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[datetime, PlainSerializer(serialize_utc)]


class WatchAssignmentBase(BaseModel):
    assignee: str = Field(min_length=1, max_length=100)
    start: datetime
    end: datetime
    fields: Optional[Dict[str, Any]] = None


class WatchAssignmentCreate(WatchAssignmentBase):
    pass


class WatchAssignmentReplace(WatchAssignmentBase):
    pass


class WatchAssignmentPatch(BaseModel):
    assignee: Optional[str] = Field(default=None, min_length=1, max_length=100)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    fields: Optional[Dict[str, Any]] = None
    version: Optional[int] = None  # optimistic lock


class WatchAssignmentOut(BaseModel):
    id: str
    assignee: str
    start: UtcDatetime
    end: UtcDatetime
    fields: Dict[str, Any] = Field(default_factory=dict)

    created_at: UtcDatetime
    created_by: str
    updated_at: UtcDatetime
    updated_by: str
    version: int
    is_deleted: bool
