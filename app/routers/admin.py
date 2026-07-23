# app/routers/admin.py
from datetime import datetime, timezone
from typing import Any, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.utils.mongo import oid as parse_oid

router = APIRouter()


async def require_admin(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    return current_user


async def require_internal(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    if not current_user.is_internal:
        raise HTTPException(status_code=403, detail="내부 접속에서만 사용할 수 있습니다.")
    return current_user


PendingStatus = Literal["PENDING", "APPROVED", "REJECTED"]


class PendingUserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    team: Optional[str] = None
    status: PendingStatus
    requested_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reject_reason: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class UserListItem(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    team: Optional[str] = None
    is_admin: bool = False
    is_blocked: bool = False
    permissions: list[str] = []
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    team: Optional[str] = None
    is_admin: Optional[bool] = None
    permissions: Optional[list[str]] = None


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    admin: UserPublic = Depends(require_admin),
):
    users = MongoClientManager.get_users_collection()
    items: list[UserListItem] = []
    async for doc in users.find().sort("created_at", 1):
        items.append(
            UserListItem(
                id=str(doc["_id"]),
                email=doc["email"],
                full_name=doc.get("full_name"),
                team=doc.get("team"),
                is_admin=bool(doc.get("is_admin", False)),
                is_blocked=bool(doc.get("is_blocked", False)),
                permissions=doc.get("permissions", []),
                created_at=doc.get("created_at"),
                last_login_at=doc.get("last_login_at"),
            )
        )
    return items


@router.patch("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    admin: UserPublic = Depends(require_admin),
):
    users = MongoClientManager.get_users_collection()
    _id = parse_oid(user_id, "잘못된 사용자 ID입니다.")

    doc = await users.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    update: dict = {}
    if body.full_name is not None:
        update["full_name"] = body.full_name
    if body.team is not None:
        update["team"] = body.team
    if body.is_admin is not None:
        update["is_admin"] = body.is_admin
    if body.permissions is not None:
        update["permissions"] = body.permissions

    if update:
        await users.update_one({"_id": _id}, {"$set": update})
        doc = await users.find_one({"_id": _id})

    return UserListItem(
        id=str(doc["_id"]),
        email=doc["email"],
        full_name=doc.get("full_name"),
        team=doc.get("team"),
        is_admin=bool(doc.get("is_admin", False)),
        is_blocked=bool(doc.get("is_blocked", False)),
        permissions=doc.get("permissions", []),
        created_at=doc.get("created_at"),
        last_login_at=doc.get("last_login_at"),
    )


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
                team=doc.get("team"),
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
    _id = parse_oid(request_id, "잘못된 요청 ID입니다.")

    p = await pending.find_one({"_id": _id})
    if not p:
        raise HTTPException(status_code=404, detail="가입 신청을 찾을 수 없습니다.")

    if p.get("status") != "PENDING":
        raise HTTPException(
            status_code=409, detail=f"대기 중인 신청이 아닙니다 (상태={p.get('status')})"
        )

    # 중복 방지
    existing = await users.find_one({"email": p["email"]})
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")

    now = datetime.now(timezone.utc)

    # users 생성 (권한은 빈 상태로, 관리자가 직접 부여)
    user_doc = {
        "email": p["email"],
        "full_name": p.get("full_name"),
        "team": p.get("team"),
        "hashed_password": p["hashed_password"],
        "created_at": now,
        "created_from_request_id": str(p["_id"]),
        "approved_by": admin.email,
        "approved_at": now,
        "is_admin": False,
        "permissions": [],
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


@router.post("/users/{user_id}/block", response_model=UserListItem)
async def block_user(user_id: str, admin: UserPublic = Depends(require_admin)):
    users = MongoClientManager.get_users_collection()
    _id = parse_oid(user_id, "잘못된 사용자 ID입니다.")
    doc = await users.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if bool(doc.get("is_admin", False)):
        raise HTTPException(status_code=400, detail="관리자 계정은 차단할 수 없습니다.")
    await users.update_one({"_id": _id}, {"$set": {"is_blocked": True}})
    doc = await users.find_one({"_id": _id})
    return UserListItem(
        id=str(doc["_id"]), email=doc["email"], full_name=doc.get("full_name"),
        team=doc.get("team"),
        is_admin=bool(doc.get("is_admin", False)), is_blocked=True,
        permissions=doc.get("permissions", []),
        created_at=doc.get("created_at"), last_login_at=doc.get("last_login_at"),
    )


@router.post("/users/{user_id}/unblock", response_model=UserListItem)
async def unblock_user(user_id: str, admin: UserPublic = Depends(require_admin)):
    users = MongoClientManager.get_users_collection()
    _id = parse_oid(user_id, "잘못된 사용자 ID입니다.")
    doc = await users.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    await users.update_one({"_id": _id}, {"$set": {"is_blocked": False}})
    doc = await users.find_one({"_id": _id})
    return UserListItem(
        id=str(doc["_id"]), email=doc["email"], full_name=doc.get("full_name"),
        team=doc.get("team"),
        is_admin=bool(doc.get("is_admin", False)), is_blocked=False,
        permissions=doc.get("permissions", []),
        created_at=doc.get("created_at"), last_login_at=doc.get("last_login_at"),
    )


class AuditLogItem(BaseModel):
    id: str
    category: str
    asset_id: str
    action: str
    source: Optional[str] = None
    changed_at: datetime
    changed_by: str
    diff: Optional[list[Any]] = None


class AuditLogResponse(BaseModel):
    total: int
    items: list[AuditLogItem]


class ActorOption(BaseModel):
    email: str
    name: str


@router.get("/audit-log/actors", response_model=list[ActorOption])
async def get_audit_log_actors(admin: UserPublic = Depends(require_admin)):
    users = MongoClientManager.get_users_collection()
    options = [
        ActorOption(email=doc["email"], name=doc.get("full_name") or doc["email"])
        async for doc in users.find({}, {"email": 1, "full_name": 1})
    ]
    return sorted(options, key=lambda o: o.name)


_INTERNAL_KEYS = {
    "id", "asset_id", "plan_id", "result_id", "checklist_id",
    "is_deleted", "created_at", "updated_at", "changed_at", "changed_by",
    "action", "source", "diff", "before", "after", "patch",
    "created_from_request_id", "approved_by", "approved_at",
}


def _diff_from_after(after: dict) -> list[dict]:
    """CREATE 액션 시 after 문서에서 의미 있는 필드만 diff 형태로 반환."""
    result = []
    for k, v in after.items():
        if k in _INTERNAL_KEYS or v in (None, "", False, []):
            continue
        if isinstance(v, dict):
            for fk, fv in v.items():
                if fv not in (None, ""):
                    result.append({"path": fk, "before": None, "after": fv})
        else:
            result.append({"path": k, "before": None, "after": v})
    return result


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=10000),
    actor: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    category_group: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    admin: UserPublic = Depends(require_admin),
):
    db = MongoClientManager.get_db()
    asset_category_map = {
        "서버": MongoClientManager.ASSETS_SERVER_HISTORY,
        "네트워크": MongoClientManager.ASSETS_NETWORK_HISTORY,
        "정보보호시스템": MongoClientManager.ASSETS_SECURITY_HISTORY,
        "DBMS": MongoClientManager.ASSETS_DBMS_HISTORY,
        "VMware": MongoClientManager.ASSETS_VMWARE_HISTORY,
    }
    category_map = {
        **asset_category_map,
        "작업계획서": MongoClientManager.JOB_PLANS_HISTORY,
        "작업계획서(서비스외)": MongoClientManager.JOB_NON_SERVICE_PLANS_HISTORY,
        "작업결과서": MongoClientManager.JOB_RESULTS_HISTORY,
        "서버실 점검": MongoClientManager.INSPECTION_HISTORY,
        "당직": MongoClientManager.WATCH_HISTORY,
        "로그인": MongoClientManager.AUTH_LOGS,
        "활동": MongoClientManager.ACTIVITY_LOGS,
    }

    if category and category in category_map:
        target_categories = {category: category_map[category]}
    elif category_group == "assets":
        target_categories = asset_category_map
    else:
        target_categories = category_map

    # 공통 필터 조건
    query: dict = {}
    if actor:
        query["changed_by"] = {"$regex": actor, "$options": "i"}
    if action:
        query["action"] = action.upper()
    if from_date or to_date:
        dt_filter: dict = {}
        if from_date:
            dt_filter["$gte"] = datetime.fromisoformat(from_date)
        if to_date:
            dt_filter["$lte"] = datetime.fromisoformat(to_date)
        query["changed_at"] = dt_filter

    # Build email→name lookup for display
    users_col = MongoClientManager.get_users_collection()
    email_to_name: dict[str, str] = {
        doc["email"]: doc.get("full_name") or doc["email"]
        async for doc in users_col.find({}, {"email": 1, "full_name": 1})
    }

    all_items: list[dict] = []
    for cat_name, col_name in target_categories.items():
        col = db[col_name]
        async for doc in col.find(query):
            raw_by = doc.get("changed_by", "")
            all_items.append({
                "id": str(doc["_id"]),
                "category": cat_name,
                "asset_id": str(doc.get("asset_id", "")),
                "action": doc.get("action", ""),
                "source": doc.get("source"),
                "changed_at": doc.get("changed_at"),
                "changed_by": email_to_name.get(raw_by, raw_by),
                "diff": doc.get("diff") or (
                    _diff_from_after(doc.get("after") or {})
                    if doc.get("action") == "CREATE" and doc.get("after")
                    else None
                ),
            })

    all_items.sort(key=lambda x: x["changed_at"] or datetime.min, reverse=True)
    total = len(all_items)
    start = (page - 1) * page_size
    paged = all_items[start: start + page_size]

    return AuditLogResponse(
        total=total,
        items=[AuditLogItem(**item) for item in paged],
    )


class AdminChangePasswordRequest(BaseModel):
    new_password: str


@router.post("/users/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_change_password(
    user_id: str,
    body: AdminChangePasswordRequest,
    admin: UserPublic = Depends(require_admin),
):
    from app.core.security import hash_password
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 6자 이상이어야 합니다.")
    users = MongoClientManager.get_users_collection()
    _id = parse_oid(user_id, "잘못된 사용자 ID입니다.")
    doc = await users.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    await users.update_one({"_id": _id}, {"$set": {"hashed_password": hash_password(body.new_password)}})


@router.post("/users/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_pending_user(
    request_id: str,
    body: RejectRequest,
    admin: UserPublic = Depends(require_admin),
):
    pending = MongoClientManager.get_pending_users_collection()
    _id = parse_oid(request_id, "잘못된 요청 ID입니다.")

    p = await pending.find_one({"_id": _id})
    if not p:
        raise HTTPException(status_code=404, detail="가입 신청을 찾을 수 없습니다.")

    if p.get("status") != "PENDING":
        raise HTTPException(
            status_code=409, detail=f"대기 중인 신청이 아닙니다 (상태={p.get('status')})"
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
