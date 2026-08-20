from pydantic import BaseModel


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


class PostHistoryDiff(BaseModel):
    field: str
    before: str | None = None
    after: str | None = None


class PostHistoryOut(BaseModel):
    id: str
    post_id: str
    diff: list[PostHistoryDiff] = []
    changed_by: str
    changed_at: str | None = None
