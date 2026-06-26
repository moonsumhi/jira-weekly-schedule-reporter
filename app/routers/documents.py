"""Document management — folder/file upload, listing, full-text search."""

import io
import logging
import mimetypes
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.utils.mongo import fmt_dt
from app.utils.mongo import oid as parse_oid

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("/app/uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db():
    return MongoClientManager.get_db()


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_text(content: bytes, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    try:
        if ext == "pdf":
            return _extract_pdf(content)
        elif ext in ("xlsx", "xls"):
            return _extract_excel(content)
        elif ext == "hwp":
            return _extract_hwp(content)
        elif ext == "docx":
            return _extract_docx(content)
        elif ext in ("txt", "md", "csv"):
            return content.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning("Text extraction failed for .%s: %s", ext, e)
    return ""


def _extract_pdf(content: bytes) -> str:
    import fitz
    doc = fitz.open(stream=content, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def _extract_excel(content: bytes) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"[{ws.title}]")
        for row in ws.iter_rows(values_only=True):
            row_text = " ".join(str(c) for c in row if c is not None)
            if row_text.strip():
                parts.append(row_text)
    return "\n".join(parts)


def _extract_hwp(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["hwp5txt", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout
    except Exception as e:
        logger.warning("HWP extraction failed: %s", e)
        return ""
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _extract_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ── Folder helpers ─────────────────────────────────────────────────────────────

async def _ensure_folder_path(db, path_parts: list, user_email: str) -> Optional[str]:
    """Ensure folder hierarchy exists, return leaf folder id string."""
    parent_id: Optional[str] = None
    for part in path_parts:
        existing = await db["document_folders"].find_one(
            {"name": part, "parent_id": parent_id}
        )
        if existing:
            parent_id = str(existing["_id"])
        else:
            doc = {
                "name": part,
                "parent_id": parent_id,
                "created_at": _now(),
                "created_by": user_email,
            }
            result = await db["document_folders"].insert_one(doc)
            parent_id = str(result.inserted_id)
    return parent_id


# ── Serializer ────────────────────────────────────────────────────────────────

def _file_out(f: dict, include_text: bool = False) -> dict:
    out = {
        "id": str(f["_id"]),
        "name": f["name"],
        "folder_id": f.get("folder_id"),
        "extension": f.get("extension", ""),
        "mime_type": f.get("mime_type", ""),
        "size": f.get("size", 0),
        "created_at": fmt_dt(f.get("created_at")),
        "created_by": f.get("created_by"),
    }
    if include_text:
        out["text_content"] = f.get("text_content", "")
    return out


def _snippet(text: str, q: str, context: int = 120) -> str:
    idx = text.lower().find(q.lower())
    if idx == -1:
        return text[:context * 2] if text else ""
    start = max(0, idx - context)
    end = min(len(text), idx + len(q) + context)
    s = text[start:end]
    if start > 0:
        s = "…" + s
    if end < len(text):
        s = s + "…"
    return s


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    paths: List[str] = Form(...),
    current_user: UserPublic = Depends(get_current_user),
):
    """Upload files preserving folder structure (paths = relative paths per file)."""
    db = _db()
    uploaded = []

    for file, rel_path in zip(files, paths):
        content = await file.read()
        parts = Path(rel_path).parts  # e.g. ("폴더", "서브폴더", "파일.pdf")

        folder_id: Optional[str] = None
        if len(parts) > 1:
            folder_id = await _ensure_folder_path(
                db, list(parts[:-1]), current_user.email
            )

        filename = parts[-1]
        extension = Path(filename).suffix
        file_uuid = str(uuid.uuid4())
        save_path = UPLOAD_DIR / f"{file_uuid}{extension}"
        save_path.write_bytes(content)

        text_content = _extract_text(content, extension)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        doc = {
            "name": filename,
            "folder_id": folder_id,
            "extension": extension.lstrip(".").lower(),
            "mime_type": mime_type,
            "file_path": str(save_path),
            "text_content": text_content,
            "size": len(content),
            "is_deleted": False,
            "created_at": _now(),
            "created_by": current_user.email,
        }
        result = await db["document_files"].insert_one(doc)
        uploaded.append(str(result.inserted_id))

    return {"uploaded": len(uploaded), "ids": uploaded}


@router.get("/folders")
async def list_folders(current_user: UserPublic = Depends(get_current_user)):
    db = _db()
    folders = await db["document_folders"].find().to_list(length=None)
    return [
        {
            "id": str(f["_id"]),
            "name": f["name"],
            "parent_id": f.get("parent_id"),
            "created_at": fmt_dt(f.get("created_at")),
        }
        for f in folders
    ]


@router.get("/root-files")
async def list_root_files(current_user: UserPublic = Depends(get_current_user)):
    db = _db()
    files = await db["document_files"].find(
        {"folder_id": None, "is_deleted": {"$ne": True}}
    ).to_list(length=None)
    return [_file_out(f) for f in files]


@router.get("/folders/{folder_id}/files")
async def list_files_in_folder(
    folder_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    db = _db()
    files = await db["document_files"].find(
        {"folder_id": folder_id, "is_deleted": {"$ne": True}}
    ).to_list(length=None)
    return [_file_out(f) for f in files]


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    current_user: UserPublic = Depends(get_current_user),
):
    db = _db()
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    files = await db["document_files"].find(
        {
            "is_deleted": {"$ne": True},
            "$or": [
                {"name": {"$regex": pattern}},
                {"text_content": {"$regex": pattern}},
            ],
        }
    ).to_list(length=200)

    results = []
    for f in files:
        item = _file_out(f)
        item["snippet"] = _snippet(f.get("text_content", ""), q)
        results.append(item)
    return results


@router.get("/files/{file_id}")
async def get_file_meta(
    file_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    db = _db()
    f = await db["document_files"].find_one({"_id": parse_oid(file_id)})
    if not f:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return _file_out(f, include_text=True)


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    db = _db()
    f = await db["document_files"].find_one({"_id": parse_oid(file_id)})
    if not f:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    file_path = Path(f["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="파일이 서버에 없습니다.")

    return FileResponse(
        path=str(file_path),
        media_type=f.get("mime_type", "application/octet-stream"),
        filename=f["name"],
        headers={"Content-Disposition": f'inline; filename="{f["name"]}"'},
    )


@router.patch("/files/{file_id}")
async def update_file(
    file_id: str,
    body: dict,
    current_user: UserPublic = Depends(get_current_user),
):
    db = _db()
    f = await db["document_files"].find_one({"_id": parse_oid(file_id)})
    if not f:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    update: dict = {}
    if "name" in body and body["name"]:
        update["name"] = body["name"]
    if "folder_id" in body:
        update["folder_id"] = body["folder_id"]  # None 허용 (루트로 이동)

    if not update:
        raise HTTPException(status_code=400, detail="변경할 내용이 없습니다.")

    await db["document_files"].update_one(
        {"_id": parse_oid(file_id)},
        {"$set": update},
    )
    updated = await db["document_files"].find_one({"_id": parse_oid(file_id)})
    return _file_out(updated)


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 삭제할 수 있습니다.")
    db = _db()
    f = await db["document_files"].find_one({"_id": parse_oid(file_id)})
    if not f:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    file_path = Path(f["file_path"])
    if file_path.exists():
        file_path.unlink()

    await db["document_files"].update_one(
        {"_id": parse_oid(file_id)},
        {"$set": {"is_deleted": True}},
    )
    return {"ok": True}


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 삭제할 수 있습니다.")
    db = _db()
    count = await db["document_files"].count_documents(
        {"folder_id": folder_id, "is_deleted": {"$ne": True}}
    )
    if count > 0:
        raise HTTPException(
            status_code=400, detail="폴더 안에 파일이 있습니다. 파일을 먼저 삭제해주세요."
        )
    await db["document_folders"].delete_one({"_id": parse_oid(folder_id)})
    return {"ok": True}
