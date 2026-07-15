from __future__ import annotations

from pydantic import BaseModel


class MentionedUser(BaseModel):
    user_id: str
    display_name: str
