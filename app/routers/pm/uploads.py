from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = "/app/uploads/pm"
MAX_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "text/csv",
    "application/zip",
}


class AttachmentOut(BaseModel):
    file_id: str
    original_name: str
    url: str
    size: int
    content_type: str


@router.post("/uploads", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
) -> AttachmentOut:
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="지원하지 않는 파일 형식입니다.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)

    with open(path, "wb") as f:
        f.write(content)

    return AttachmentOut(
        file_id=stored_name,
        original_name=file.filename or stored_name,
        url=f"/api/uploads/pm/{stored_name}",
        size=len(content),
        content_type=content_type,
    )
