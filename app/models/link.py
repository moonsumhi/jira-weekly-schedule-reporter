from pydantic import BaseModel


class LinkCreate(BaseModel):
    title: str
    url: str
    type: str = ""
    color: str = "grey"
    note: str | None = None
    tags: list[str] = []
    rank: int | None = None
    is_visible: bool = True


class LinkPatch(BaseModel):
    title: str | None = None
    url: str | None = None
    type: str | None = None
    color: str | None = None
    note: str | None = None
    tags: list[str] | None = None
    rank: int | None = None
    is_visible: bool | None = None


class LinkOut(BaseModel):
    id: str
    title: str
    url: str
    type: str
    color: str
    note: str | None = None
    tags: list[str]
    rank: int | None = None
    is_visible: bool
    created_at: str | None = None
