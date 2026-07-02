from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ProjectRole = Literal["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "VIEWER"]

# 쓰기 가능한 역할 (Viewer 제외)
WRITABLE_ROLES: list[ProjectRole] = ["ADMIN", "PROJECT_MANAGER", "DEVELOPER"]


class ProjectCreate(BaseModel):
    org_id: str
    name: str = Field(..., min_length=1, max_length=100)
    key: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Z][A-Z0-9]*$")
    description: Optional[str] = Field(None, max_length=500)


class ProjectPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ProjectOut(BaseModel):
    id: str
    org_id: str
    name: str
    key: str
    description: Optional[str]
    is_sr_default: bool = False
    created_at: datetime
    updated_at: datetime


class ProjectMemberOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    user_email: str
    user_name: str
    role: ProjectRole
    joined_at: datetime


class ProjectMemberAdd(BaseModel):
    user_id: str
    role: ProjectRole = "DEVELOPER"


class ProjectMemberRolePatch(BaseModel):
    role: ProjectRole
