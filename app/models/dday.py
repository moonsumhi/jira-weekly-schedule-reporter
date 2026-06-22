from pydantic import BaseModel


class DDayCreate(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    color: str = "blue"
    note: str | None = None


class DDayPatch(BaseModel):
    title: str | None = None
    date: str | None = None
    color: str | None = None
    note: str | None = None


class DDayOut(BaseModel):
    id: str
    title: str
    date: str
    color: str
    note: str | None = None
    created_at: str | None = None
