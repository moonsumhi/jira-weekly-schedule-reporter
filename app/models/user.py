from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, List


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_admin: bool = False
    permissions: List[str] = []

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserPublic(UserBase):
    id: str
    is_internal: bool = True  # 내부 IP 접속 여부 (요청마다 동적으로 설정)


class RegisterPendingResponse(BaseModel):
    status: Literal["PENDING"]
    request_id: str
    message: str


class PendingUserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    status: Literal["PENDING", "APPROVED", "REJECTED"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
