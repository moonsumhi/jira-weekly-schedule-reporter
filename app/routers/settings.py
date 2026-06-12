"""앱 전역 설정 — key/value 저장소"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.admin import require_admin

router = APIRouter()


class SettingOut(BaseModel):
    key: str
    value: Optional[str] = None


class SettingPut(BaseModel):
    value: str


class MyIpOut(BaseModel):
    client_ip: str
    is_internal: bool


@router.get("/my-ip", response_model=MyIpOut)
async def get_my_ip(request: Request):
    """현재 접속 IP 및 내부 여부 반환 (인증 불필요, IP 디버깅용)"""
    from app.utils.ip import _get_client_ip, is_internal_ip
    client_ip = _get_client_ip(request)
    internal = await is_internal_ip(request)
    return MyIpOut(client_ip=client_ip, is_internal=internal)


@router.get("/{key}", response_model=SettingOut)
async def get_setting(key: str, _: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
    doc = await col.find_one({"key": key})
    return SettingOut(key=key, value=doc.get("value") if doc else None)


@router.put("/{key}", response_model=SettingOut)
async def put_setting(key: str, payload: SettingPut, _=Depends(require_admin)):
    from app.utils.ip import invalidate_cache
    col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
    await col.update_one({"key": key}, {"$set": {"value": payload.value}}, upsert=True)
    if key == "internal_ips":
        invalidate_cache()
    return SettingOut(key=key, value=payload.value)
