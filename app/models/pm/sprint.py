from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


SprintStatus = Literal["PLANNED", "ACTIVE", "COMPLETED"]


class SprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    goal: Optional[str] = Field(None, max_length=500)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SprintPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    goal: Optional[str] = Field(None, max_length=500)
    status: Optional[SprintStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SprintOut(BaseModel):
    id: str
    project_id: str
    name: str
    goal: Optional[str]
    status: SprintStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    issue_count: int = 0
    created_at: datetime
    updated_at: datetime
