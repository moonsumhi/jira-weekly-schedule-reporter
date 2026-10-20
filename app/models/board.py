from datetime import datetime

from pydantic import BaseModel, Field

from app.models.comment_reaction import CommentReactionOut
from app.models.mention import MentionedUser


class BoardAttachment(BaseModel):
    file_id: str
    original_name: str
    url: str
    size: int
    content_type: str


class BoardCreate(BaseModel):
    title: str
    description: str = ""
    menu_id: str
    icon: str | None = None
    link: str | None = None
    sort_order: int | None = None


class BoardPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    icon: str | None = None
    link: str | None = None
    sort_order: int | None = None


class BoardOut(BaseModel):
    id: str
    title: str
    description: str
    menu_id: str
    icon: str | None = None
    post_count: int = 0
    link: str | None = None
    sort_order: int | None = None
    created_at: str | None = None


class PostCreate(BaseModel):
    title: str
    part: str = ""
    category: str = ""
    content: str
    attachments: list[BoardAttachment] = []
    parent_id: str | None = None
    expected_version: int | None = None
    editor_ids: list[str] = []
    owner_id: str | None = None
    mentioned_user_ids: list[str] = Field(default_factory=list)


class PostOut(BaseModel):
    id: str
    board_id: str
    title: str
    part: str = ""
    category: str = ""
    content: str
    author_id: str
    author_name: str
    attachments: list[BoardAttachment] = []
    created_at: str | None = None
    parent_id: str | None = None
    version: int = 1
    updated_at: str | None = None
    editor_ids: list[str] = []
    owner_id: str = ""
    owner_name: str = ""
    adopted_by: str | None = None
    adopted_name: str | None = None
    adopted_at: str | None = None
    adopted_version: int | None = None
    follower_count: int = 0
    mentioned_users: list[MentionedUser] = Field(default_factory=list)


class BoardCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    mentioned_user_ids: list[str] = Field(default_factory=list)


class BoardCommentOut(BaseModel):
    id: str
    board_id: str
    post_id: str
    author_id: str
    author_name: str
    content: str
    mentioned_users: list[MentionedUser] = Field(default_factory=list)
    reactions: list[CommentReactionOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PostHistoryDiff(BaseModel):
    key: str | None = None
    field: str
    before: str | None = None
    after: str | None = None


class PostVersionSnapshot(BaseModel):
    title: str = ""
    part: str = ""
    category: str = ""
    content: str = ""
    attachments: list[BoardAttachment] = Field(default_factory=list)
    parent_id: str | None = None


class AdoptPostVersion(BaseModel):
    version: int = Field(..., ge=1)


class PostHistoryOut(BaseModel):
    id: str
    post_id: str
    diff: list[PostHistoryDiff] = []
    changed_by: str
    changed_at: str | None = None
    version: int | None = None
    snapshot: PostVersionSnapshot | None = None
