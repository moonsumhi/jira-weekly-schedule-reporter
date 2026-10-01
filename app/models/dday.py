from pydantic import BaseModel, Field


class DDayCreate(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    color: str = "blue"
    note: str | None = None
    visible_user_ids: list[str] = Field(default_factory=list)


class DDayPatch(BaseModel):
    title: str | None = None
    date: str | None = None
    color: str | None = None
    note: str | None = None
    visible_user_ids: list[str] | None = None


class DDayOut(BaseModel):
    id: str
    title: str
    date: str
    color: str
    note: str | None = None
    visible_user_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
