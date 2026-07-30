from pydantic import BaseModel


class NoticeCreate(BaseModel):
    title: str
    content: str
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    is_active: bool = True


class NoticePatch(BaseModel):
    title: str | None = None
    content: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_active: bool | None = None


class NoticeOut(BaseModel):
    id: str
    title: str
    content: str
    start_date: str
    end_date: str
    is_active: bool
    created_by: str
    created_at: str | None = None
