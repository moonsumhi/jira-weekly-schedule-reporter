from __future__ import annotations

import os
import urllib.parse
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = "/app/uploads/sr"
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


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    name: str = "",
    current_user: UserPublic = Depends(get_current_user),
) -> FileResponse:
    # path traversal 방지
    safe_name = os.path.basename(file_id)
    path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    original_name = name or safe_name
    return FileResponse(
        path,
        filename=original_name,
        headers={"Content-Disposition": f'attachment; filename="{original_name}"; filename*=UTF-8\'\'{urllib.parse.quote(original_name)}'},
    )


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
        url=f"/api/uploads/sr/{stored_name}",
        size=len(content),
        content_type=content_type,
    )
