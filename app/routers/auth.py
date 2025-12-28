# app/routers/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/auth", tags=["auth"])

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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
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

    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        is_admin=bool(user.get("is_admin", False)),
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
        if st == "REJECTED":
            raise HTTPException(
                status_code=403, detail="Registration request was rejected by admin"
            )
        if st == "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="Request is approved but account not created; contact admin",
            )

    doc = {
        "email": user.email,
        "full_name": user.full_name,
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
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password

    user = await authenticate_user(email, password)
    if not user:
        # users에 없으면 pending 상태 확인해서 더 친절한 에러
        p = await get_pending_by_email(email)
        if p:
            st = p.get("status", "PENDING")
            if st == "PENDING":
                raise HTTPException(
                    status_code=403, detail="Waiting for admin approval"
                )
            if st == "REJECTED":
                reason = p.get("reject_reason")
                msg = "Registration request was rejected by admin"
                if reason:
                    msg = f"{msg}: {reason}"
                raise HTTPException(status_code=403, detail=msg)

        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["email"],
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user
