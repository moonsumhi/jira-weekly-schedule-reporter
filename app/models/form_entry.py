from typing import Any
from pydantic import BaseModel


class FormEntryCreate(BaseModel):
    template_id: str
    data: dict[str, Any]


class FormEntryPatch(BaseModel):
    data: dict[str, Any]
    version: int


class FormEntryOut(BaseModel):
    id: str
    template_id: str
    data: dict[str, Any]
    version: int
    is_deleted: bool
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None
