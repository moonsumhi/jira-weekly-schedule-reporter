"""로그인 전에도 필요한 앱 브랜딩(이름/테마 색상) — 인증 불필요, 조회만 제공"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.mongo import MongoClientManager

router = APIRouter()

DEFAULT_APP_NAME = "OPTOOL"
DEFAULT_THEME_COLOR = "blue"


class BrandingOut(BaseModel):
    app_name: str
    theme_color: str


@router.get("", response_model=BrandingOut)
async def get_branding():
    col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
    name_doc = await col.find_one({"key": "app_name"})
    color_doc = await col.find_one({"key": "app_theme_color"})
    return BrandingOut(
        app_name=(name_doc.get("value") if name_doc else None) or DEFAULT_APP_NAME,
        theme_color=(color_doc.get("value") if color_doc else None) or DEFAULT_THEME_COLOR,
    )
