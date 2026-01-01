# app/routers/admin.py
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()


async def require_admin(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    # ✅ 네 코드에 is_admin이 이미 있다고 가정
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


PendingStatus = Literal["PENDING", "APPROVED", "REJECTED"]


class PendingUserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    status: PendingStatus
    requested_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reject_reason: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/users/pending", response_model=list[PendingUserPublic])
async def list_pending(
    status_filter: Optional[Literal["PENDING", "APPROVED", "REJECTED"]] = Query(
        None, alias="status"
    ),
    admin: UserPublic = Depends(require_admin),
):
    pending = MongoClientManager.get_pending_users_collection()

    query = {} if status_filter is None else {"status": status_filter}

    cursor = pending.find(query).sort("requested_at", 1)

    items: list[PendingUserPublic] = []
    async for doc in cursor:
        items.append(
            PendingUserPublic(
                id=str(doc["_id"]),
                email=doc["email"],
                full_name=doc.get("full_name"),
                status=doc.get("status", "PENDING"),
                requested_at=doc.get("requested_at"),
                reviewed_at=doc.get("reviewed_at"),
                reviewed_by=doc.get("reviewed_by"),
                reject_reason=doc.get("reject_reason"),
            )
        )
    return items


@router.post("/users/{request_id}/approve", response_model=UserPublic)
async def approve_pending_user(
    request_id: str,
    admin: UserPublic = Depends(require_admin),
):
    users = MongoClientManager.get_users_collection()
    pending = MongoClientManager.get_pending_users_collection()

    try:
        _id = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request id")

    p = await pending.find_one({"_id": _id})
    if not p:
        raise HTTPException(status_code=404, detail="Pending request not found")

    if p.get("status") != "PENDING":
        raise HTTPException(
            status_code=409, detail=f"Request is not pending (status={p.get('status')})"
        )

    # 중복 방지
    existing = await users.find_one({"email": p["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc)

    # users 생성
    user_doc = {
        "email": p["email"],
        "full_name": p.get("full_name"),
        "hashed_password": p["hashed_password"],
        "created_at": now,
        "created_from_request_id": str(p["_id"]),
        "approved_by": admin.email,
        "approved_at": now,
        "is_admin": False,
    }
    result = await users.insert_one(user_doc)

    # ✅ pending 이력 유지: status 업데이트
    await pending.update_one(
        {"_id": _id},
        {
            "$set": {
                "status": "APPROVED",
                "reviewed_at": now,
                "reviewed_by": admin.email,
            }
        },
    )

    return UserPublic(
        id=str(result.inserted_id),
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
    )


@router.post("/users/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_pending_user(
    request_id: str,
    body: RejectRequest,
    admin: UserPublic = Depends(require_admin),
):
    pending = MongoClientManager.get_pending_users_collection()

    try:
        _id = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request id")

    p = await pending.find_one({"_id": _id})
    if not p:
        raise HTTPException(status_code=404, detail="Pending request not found")

    if p.get("status") != "PENDING":
        raise HTTPException(
            status_code=409, detail=f"Request is not pending (status={p.get('status')})"
        )

    await pending.update_one(
        {"_id": _id},
        {
            "$set": {
                "status": "REJECTED",
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by": admin.email,
                "reject_reason": body.reason,
            }
        },
    )
    return
