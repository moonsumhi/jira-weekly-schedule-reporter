from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.pm.issue import IssueStatus, IssueType


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
    is_favorite: bool = False
    favorite_order: Optional[float] = None
    has_access: bool = True
    access_request_status: Optional[Literal["PENDING", "REJECTED"]] = None
    pending_access_request_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectIssueSearchItem(BaseModel):
    id: str
    key: str
    number: int
    title: str
    type: IssueType
    status: IssueStatus
    project_id: str = Field(serialization_alias="projectId")
    project_key: str = Field(serialization_alias="projectKey")
    project_name: str = Field(serialization_alias="projectName")


class ProjectIssueSearchOut(BaseModel):
    items: list[ProjectIssueSearchItem]
    has_more: bool = Field(serialization_alias="hasMore")


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


class ProjectAccessRequestCreate(BaseModel):
    reason: str = Field(..., max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValueError("신청 사유를 입력해 주세요.")
        return reason


class ProjectAccessRequestOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    user_name: str
    user_email: str
    status: Literal["PENDING", "REJECTED", "APPROVED"]
    reason: Optional[str] = None
    created_at: datetime


class FavoriteOrderPatch(BaseModel):
    project_ids: list[str] = Field(..., description="드래그로 정해진 즐겨찾기 프로젝트 순서 (앞이 먼저)")
