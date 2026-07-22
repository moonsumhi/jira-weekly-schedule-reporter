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
    tab_title: str


@router.get("", response_model=BrandingOut)
async def get_branding():
    col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
    name_doc = await col.find_one({"key": "app_name"})
    color_doc = await col.find_one({"key": "app_theme_color"})
    tab_title_doc = await col.find_one({"key": "tab_title"})
    app_name = (name_doc.get("value") if name_doc else None) or DEFAULT_APP_NAME
    return BrandingOut(
        app_name=app_name,
        theme_color=(color_doc.get("value") if color_doc else None) or DEFAULT_THEME_COLOR,
        # 탭 제목을 별도로 설정한 적이 없으면 기존 동작대로 앱 이름을 그대로 사용
        tab_title=(tab_title_doc.get("value") if tab_title_doc else None) or app_name,
    )
