from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = "/app/uploads/pm"
MAX_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain", "text/csv", "text/html",
    "application/json", "application/xml", "text/xml",
    "application/zip",
    "video/mp4",
}
# 브라우저가 표준 MIME 타입을 보내지 않는 확장자 (한글 문서, 로그/설정 파일 등) → 확장자로 허용 판단
# .zip: Windows에서는 브라우저가 application/zip이 아니라 application/x-zip-compressed로
# 보내는 경우가 흔해 ALLOWED_TYPES만으로는 거부되므로 확장자로도 허용한다.
ALLOWED_EXTENSIONS_FALLBACK = {".hwp", ".hwpx", ".log", ".yaml", ".yml", ".zip"}


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
        raise HTTPException(status_code=413, detail="파일 크기가 100MB를 초과합니다.")

    content_type = file.content_type or "application/octet-stream"
    ext = os.path.splitext(file.filename or "")[1].lower()
    if content_type not in ALLOWED_TYPES and ext not in ALLOWED_EXTENSIONS_FALLBACK:
        raise HTTPException(status_code=415, detail="지원하지 않는 파일 형식입니다.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
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
