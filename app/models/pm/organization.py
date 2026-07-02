from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


OrgRole = Literal["ADMIN", "MEMBER"]


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")


class OrganizationPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class OrgMemberOut(BaseModel):
    id: str
    org_id: str
    user_id: str
    user_email: str
    user_name: str
    role: OrgRole
    joined_at: datetime


class OrgMemberAdd(BaseModel):
    user_id: str
    role: OrgRole = "MEMBER"


class OrgMemberRolePatch(BaseModel):
    role: OrgRole
