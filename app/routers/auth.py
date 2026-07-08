# app/routers/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.db.mongo import MongoClientManager
from app.models.user import UserCreate, UserPublic, Token
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.core.config import settings

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_user_by_email(email: str) -> Optional[dict]:
    users = MongoClientManager.get_users_collection()
    return await users.find_one({"email": email})


async def get_pending_by_email(email: str) -> Optional[dict]:
    pending = MongoClientManager.get_pending_users_collection()
    return await pending.find_one({"email": email})


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def get_current_user(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
) -> UserPublic:
    from app.utils.ip import is_internal_ip

    email = decode_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    internal = await is_internal_ip(request)

    # 내부망: 활동(요청)이 있을 때마다 만료시간을 연장(슬라이딩 세션).
    # 이렇게 하면 계속 사용 중일 땐 로그인이 유지되고, ACCESS_TOKEN_EXPIRE_MINUTES(내부망) 동안
    # 아무 요청도 없어야만(=안 움직였을 때) 실제로 로그아웃된다.
    if internal:
        refreshed = create_access_token(
            subject=email,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        response.headers["X-Refreshed-Token"] = refreshed

    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        team=user.get("team"),
        is_admin=bool(user.get("is_admin", False)),
        permissions=user.get("permissions", []),
        is_internal=internal,
    )


class RegisterPendingResponse(BaseModel):
    status: Literal["PENDING"]
    request_id: str
    message: str


@router.post(
    "/register",
    response_model=RegisterPendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register(user: UserCreate):
    users = MongoClientManager.get_users_collection()
    pending = MongoClientManager.get_pending_users_collection()

    # 1) 이미 정식 가입된 이메일이면 거부
    existing = await users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2) 이미 pending 신청이 있으면 상태에 따라 안내
    existing_pending = await pending.find_one({"email": user.email})
    if existing_pending:
        st = existing_pending.get("status", "PENDING")
        if st == "PENDING":
            raise HTTPException(
                status_code=400, detail="Registration is already pending admin approval"
            )
        if st == "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="Request is approved but account not created; contact admin",
            )

    # reject 당한거면 해당 이메일로 다시 신청할 수 있도록 함

    doc = {
        "email": user.email,
        "full_name": user.full_name,
        "team": user.team,
        "hashed_password": hash_password(user.password),
        "status": "PENDING",
        "requested_at": datetime.now(timezone.utc),
        "reviewed_at": None,
        "reviewed_by": None,
        "reject_reason": None,
    }
    result = await pending.insert_one(doc)

    return RegisterPendingResponse(
        status="PENDING",
        request_id=str(result.inserted_id),
        message="Registration request submitted. Waiting for admin approval.",
    )


@router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "-")
    )
    auth_logs = MongoClientManager.get_auth_logs_collection()
    now = datetime.now(timezone.utc)

    async def _log(actor: str, action: str, reason: str):
        await auth_logs.insert_one({
            "action": action,
            "changed_at": now,
            "changed_by": actor,
            "diff": [{"path": "IP", "before": None, "after": client_ip},
                     {"path": "사유", "before": None, "after": reason}],
        })

    user = await authenticate_user(email, password)
    if user and user.get("is_blocked"):
        await _log(email, "LOGIN_FAILED", "차단된 계정")
        raise HTTPException(status_code=403, detail="차단된 계정입니다. 관리자에게 문의하세요.")
    if not user:
        p = await get_pending_by_email(email)
        if p:
            st = p.get("status", "PENDING")
            if st == "PENDING":
                await _log(email, "LOGIN_FAILED", "승인 대기 중")
                raise HTTPException(status_code=403, detail="Waiting for admin approval")
            if st == "REJECTED":
                reason = p.get("reject_reason")
                msg = "Registration request was rejected by admin"
                if reason:
                    msg = f"{msg}: {reason}"
                await _log(email, "LOGIN_FAILED", f"가입 거절됨: {reason or ''}")
                raise HTTPException(status_code=403, detail=msg)
        await _log(email, "LOGIN_FAILED", "이메일/비밀번호 불일치")
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    users = MongoClientManager.get_users_collection()
    await users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": now}},
    )
    await auth_logs.insert_one({
        "action": "LOGIN",
        "changed_at": now,
        "changed_by": user["email"],
        "diff": [{"path": "IP", "before": None, "after": client_ip}],
    })

    origin = request.headers.get("Origin", "")
    is_external_port = ":9001" in origin
    expire_minutes = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES_EXTERNAL
        if is_external_port
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token_expires = timedelta(minutes=expire_minutes)
    access_token = create_access_token(
        subject=user["email"],
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


@router.get("/home-ping", status_code=204)
async def home_ping(current_user: UserPublic = Depends(get_current_user)):
    """메인 페이지 방문 로깅용 (미들웨어가 VIEW 기록)"""
    return None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ColPreset(BaseModel):
    name: str
    cols: list[str]


class UserPrefs(BaseModel):
    asset_col_presets: list[ColPreset] = []


@router.get("/prefs", response_model=UserPrefs)
async def get_prefs(current_user: UserPublic = Depends(get_current_user)):
    users = MongoClientManager.get_users_collection()
    doc = await users.find_one({"email": current_user.email}, {"prefs": 1})
    raw = (doc or {}).get("prefs", {})
    presets = raw.get("asset_col_presets", [])
    return UserPrefs(asset_col_presets=[ColPreset(**p) for p in presets])


@router.put("/prefs", response_model=UserPrefs)
async def save_prefs(
    body: UserPrefs,
    current_user: UserPublic = Depends(get_current_user),
):
    if len(body.asset_col_presets) > 3:
        raise HTTPException(status_code=400, detail="프리셋은 최대 3개까지 저장 가능합니다.")
    users = MongoClientManager.get_users_collection()
    await users.update_one(
        {"email": current_user.email},
        {"$set": {"prefs.asset_col_presets": [p.model_dump() for p in body.asset_col_presets]}},
    )
    return body



@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="새 비밀번호는 6자 이상이어야 합니다.")

    users = MongoClientManager.get_users_collection()
    user = await get_user_by_email(current_user.email)
    if not user or not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")

    await users.update_one(
        {"email": current_user.email},
        {"$set": {"hashed_password": hash_password(body.new_password)}}
    )
