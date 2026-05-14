from pydantic import BaseModel


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
    content: str


class PostOut(BaseModel):
    id: str
    board_id: str
    title: str
    content: str
    author_id: str
    author_name: str
    created_at: str | None = None
