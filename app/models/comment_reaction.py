"""이슈/SR 댓글 공통 이모티콘 반응 모델."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class CommentReactionUser(BaseModel):
    user_id: str
    display_name: str


class CommentReactionOut(BaseModel):
    emoji: str
    users: List[CommentReactionUser] = []


class CommentReactionToggle(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=8)
