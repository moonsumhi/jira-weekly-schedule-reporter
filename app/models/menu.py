from pydantic import BaseModel


class MenuCreate(BaseModel):
    title: str
    icon: str = "fa-solid fa-folder"
    sort_order: int | None = None
    is_visible: bool = True


class MenuPatch(BaseModel):
    title: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    is_visible: bool | None = None
    is_external_visible: bool | None = None
    is_internal_visible: bool | None = None
    sub_icons: dict[str, str] | None = None
    sub_order: list[str] | None = None


class MenuOut(BaseModel):
    id: str
    title: str
    icon: str
    sort_order: int | None = None
    is_visible: bool
    is_external_visible: bool = False
    is_internal_visible: bool = True
    is_system: bool = False
    slug: str | None = None
    sub_icons: dict[str, str] | None = None
    sub_order: list[str] | None = None
    created_at: str | None = None
