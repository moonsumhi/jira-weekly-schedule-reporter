# app/models/watch.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


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
    start: datetime
    end: datetime
    fields: Dict[str, Any] = {}

    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int
    is_deleted: bool
