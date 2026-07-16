from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.mention import MentionedUser


class Attachment(BaseModel):
    file_id: str
    original_name: str
    url: str
    size: int
    content_type: str


IssueType = Literal["EPIC", "STORY", "TASK", "BUG", "SUB_TASK"]
IssueStatus = Literal["BACKLOG", "TODO", "IN_PROGRESS", "IN_REVIEW", "DONE"]
IssuePriority = Literal["LOWEST", "LOW", "MEDIUM", "HIGH", "HIGHEST"]

ISSUE_STATUS_ORDER = ["BACKLOG", "TODO", "IN_PROGRESS", "IN_REVIEW", "DONE"]


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: IssueType = "TASK"
    status: IssueStatus = "BACKLOG"
    priority: IssuePriority = "MEDIUM"
    assignee_id: Optional[str] = None
    sprint_id: Optional[str] = None
    epic_id: Optional[str] = None
    parent_issue_id: Optional[str] = None
    label_ids: List[str] = []
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    story_points: Optional[int] = Field(None, ge=0, le=999)
    attachments: List[Attachment] = []


class IssuePatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[IssueType] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    assignee_id: Optional[str] = None
    sprint_id: Optional[str] = None
    epic_id: Optional[str] = None
    parent_issue_id: Optional[str] = None
    label_ids: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    story_points: Optional[int] = Field(None, ge=0, le=999)
    attachments: Optional[List[Attachment]] = None
    order: Optional[float] = None


class SubtaskSummary(BaseModel):
    id: str
    number: int
    title: str
    status: IssueStatus
    priority: IssuePriority
    assignee_name: Optional[str] = None


class IssueOut(BaseModel):
    id: str
    project_id: str
    project_key: Optional[str] = None
    project_name: Optional[str] = None
    number: int
    title: str
    description: Optional[str]
    type: IssueType
    status: IssueStatus
    priority: IssuePriority
    assignee_id: Optional[str]
    assignee_name: Optional[str]
    reporter_id: str
    reporter_name: str
    sprint_id: Optional[str]
    epic_id: Optional[str]
    epic_title: Optional[str] = None
    parent_issue_id: Optional[str] = None
    label_ids: List[str]
    start_date: Optional[datetime] = None
    due_date: Optional[datetime]
    story_points: Optional[int] = None
    attachments: List[Attachment] = []
    order: float
    linked_sr_id: Optional[str] = None
    subtasks: List[SubtaskSummary] = []
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class IssueCommentCreate(BaseModel):
    content: str = Field('', min_length=0)
    parent_id: Optional[str] = None
    attachments: List[Attachment] = []
    mentioned_user_ids: List[str] = []


class IssueCommentPatch(BaseModel):
    content: str = Field(..., min_length=1)
    mentioned_user_ids: List[str] = []


class IssueCommentOut(BaseModel):
    id: str
    issue_id: str
    parent_id: Optional[str] = None
    author_id: str
    author_name: str
    content: str
    attachments: List[Attachment] = []
    mentioned_users: List[MentionedUser] = []
    created_at: datetime
    updated_at: datetime


class IssueHistoryOut(BaseModel):
    id: str
    issue_id: str
    user_id: str
    user_name: str
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    created_at: datetime


class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field("#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")


class LabelOut(BaseModel):
    id: str
    project_id: str
    name: str
    color: str
