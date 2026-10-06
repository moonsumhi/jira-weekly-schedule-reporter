from pydantic import BaseModel, Field


class SubMenuItem(BaseModel):
    title: str
    icon: str
    link: str
    require_admin: bool = False


class MenuCreate(BaseModel):
    title: str
    icon: str = "fa-solid fa-folder"
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = None
    is_visible: bool = True
    link: str | None = None


class MenuPatch(BaseModel):
    title: str | None = None
    icon: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = None
    is_visible: bool | None = None
    is_external_visible: bool | None = None
    is_internal_visible: bool | None = None
    sub_icons: dict[str, str] | None = None
    sub_colors: dict[str, str] | None = None
    sub_order: list[str] | None = None
    link: str | None = None


class MenuOut(BaseModel):
    id: str
    title: str
    icon: str
    color: str | None = None
    sort_order: int | None = None
    is_visible: bool
    is_external_visible: bool = False
    is_internal_visible: bool = True
    is_system: bool = False
    slug: str | None = None
    sub_icons: dict[str, str] | None = None
    sub_colors: dict[str, str] | None = None
    sub_order: list[str] | None = None
    link: str | None = None
    submenus: list[SubMenuItem] = []
    created_at: str | None = None
