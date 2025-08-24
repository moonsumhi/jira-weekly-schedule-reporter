from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Issue(BaseModel):
    key: str
    summary: str
    status: str
    assignee: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    duedate: Optional[datetime] = None
    start: Optional[datetime] = None
    url: str


class AssigneeGroup(BaseModel):
    assignee: str
    count: int
    issues: List[Issue]


class GroupedResponse(BaseModel):
    date_field: str = Field(..., description="필터링시 사용되는 날짜 필드")
    start: datetime
    end: datetime
    timezone: str
    total: int
    groups: List[AssigneeGroup]
