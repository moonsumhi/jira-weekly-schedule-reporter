from pydantic import BaseModel


class EnvItem(BaseModel):
    id: str
    label: str
    sort_order: int = 0
    is_active: bool = True


class EnvItemCreate(BaseModel):
    label: str


class EnvItemPatch(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class EnvCategoryCreate(BaseModel):
    key: str
    label: str


class EnvCategoryPatch(BaseModel):
    label: str | None = None


class EnvCategoryOut(BaseModel):
    id: str
    key: str
    label: str
    is_system: bool = False
    items: list[EnvItem] = []
