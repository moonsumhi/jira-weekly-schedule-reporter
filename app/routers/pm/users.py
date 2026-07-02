from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("", response_model=List[dict])
async def list_users_for_pm(
    current_user: UserPublic = Depends(get_current_user),
    team: Optional[str] = Query(None),
):
    """멤버 초대용 전체 유저 목록 (차단된 유저 제외). team 파라미터로 팀 필터 가능."""
    col = MongoClientManager.get_users_collection()
    query: dict = {"is_blocked": {"$ne": True}}
    if team:
        query["team"] = team
    docs = await col.find(
        query,
        {"_id": 1, "email": 1, "full_name": 1, "team": 1},
    ).sort("full_name", 1).to_list(None)
    return [
        {"id": str(d["_id"]), "email": d["email"], "name": d.get("full_name") or "", "team": d.get("team") or ""}
        for d in docs
    ]
