# app/routers/auth.py
from datetime import timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

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
    )


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(user: UserCreate):
    users = MongoClientManager.get_users_collection()

    existing = await users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hash_password(user.password),
    }
    result = await users.insert_one(doc)

    return UserPublic(
        id=str(result.inserted_id),
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user["email"], expires_delta=access_token_expires
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user
