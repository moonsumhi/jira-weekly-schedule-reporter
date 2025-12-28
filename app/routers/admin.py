# app/routers/admin.py
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user  # auth의 current_user 재사용

router = APIRouter(prefix="/admin", tags=["admin"])


def _is_admin_email(email: str) -> bool:
    admin_emails = getattr(settings, "ADMIN_EMAILS", None)
    if not admin_emails:
        return False
    return email in set(admin_emails)


async def require_admin(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user


class PendingUserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    status: Literal["PENDING", "APPROVED", "REJECTED"]


class RejectRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/users/pending", response_model=list[PendingUserPublic])
async def list_pending(admin: UserPublic = Depends(require_admin)):
    pending = MongoClientManager.get_pending_users_collection()
    cursor = pending.find({"status": "PENDING"}).sort("requested_at", 1)

    items: list[PendingUserPublic] = []
    async for doc in cursor:
        items.append(
            PendingUserPublic(
                id=str(doc["_id"]),
                email=doc["email"],
                full_name=doc.get("full_name"),
                status=doc.get("status", "PENDING"),
            )
        )
    return items


@router.post("/users/pending/{request_id}/approve", response_model=UserPublic)
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

    # users 생성
    user_doc = {
        "email": p["email"],
        "full_name": p.get("full_name"),
        "hashed_password": p["hashed_password"],
        "created_at": datetime.now(timezone.utc),
        "created_from_request_id": str(p["_id"]),
        "approved_by": admin.email,
        "approved_at": datetime.now(timezone.utc),
    }
    result = await users.insert_one(user_doc)

    # move 방식: pending 삭제 (승인 기록 유지가 필요하면 delete 대신 status update로 바꾸면 됨)
    await pending.delete_one({"_id": _id})

    return UserPublic(
        id=str(result.inserted_id),
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
    )


@router.post(
    "/users/pending/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT
)
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
