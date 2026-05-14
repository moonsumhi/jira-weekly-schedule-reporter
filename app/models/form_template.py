from typing import Any
from pydantic import BaseModel


class FormTemplateCreate(BaseModel):
    title: str
    jira_issue_key: str
    sections: list[Any]
    menu: str | None = None
    sort_order: int | None = None


class FormTemplatePatch(BaseModel):
    sort_order: int | None = None


class FormTemplateOut(BaseModel):
    id: str
    title: str
    jira_issue_key: str
    sections: list[Any]
    menu: str | None = None
    sort_order: int | None = None
    is_deleted: bool = False
    created_at: str | None = None
