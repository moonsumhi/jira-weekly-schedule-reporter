"""Form entry CRUD endpoints — stores submitted data for a form template."""

import asyncio
import io
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

import anthropic
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()


class FormEntryCreate(BaseModel):
    template_id: str
    data: dict[str, Any]  # {sectionTitle: {fieldLabel: value}}


class FormEntryPatch(BaseModel):
    data: dict[str, Any]
    version: int


class FormEntryOut(BaseModel):
    id: str
    template_id: str
    data: dict[str, Any]
    version: int
    is_deleted: bool
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_out(doc: dict) -> FormEntryOut:
    def _fmt(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return FormEntryOut(
        id=str(doc["_id"]),
        template_id=doc.get("template_id", ""),
        data=doc.get("data", {}),
        version=doc.get("version", 1),
        is_deleted=doc.get("is_deleted", False),
        created_at=_fmt(doc.get("created_at")),
        created_by=doc.get("created_by"),
        updated_at=_fmt(doc.get("updated_at")),
        updated_by=doc.get("updated_by"),
    )


def _extract_pdf_text(content: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


async def _extract_hwp_text(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
        f.write(content)
        tmppath = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "hwp5txt", tmppath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass


async def _extract_form_data_with_claude(text: str, sections: list) -> dict:
    sections_desc = json.dumps(sections, ensure_ascii=False, indent=2)
    prompt = (
        "다음 작업계획서 문서에서 폼 데이터를 추출해주세요.\n\n"
        f"폼 구조:\n{sections_desc}\n\n"
        f"문서 내용:\n{text}\n\n"
        "위 폼 구조에 맞춰 JSON으로 데이터를 추출해주세요. "
        "각 섹션의 각 필드에 해당하는 값을 찾아서 채워주세요. "
        "multiple이 true인 섹션은 배열로, 아닌 경우는 객체로 반환하세요.\n\n"
        "반드시 다음 형식으로만 응답하세요 (JSON만, 설명 없이):\n"
        "{\"섹션제목\": {\"필드명\": \"값\"}, \"multiple섹션제목\": [{\"필드명\": \"값\"}]}"
    )
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text  # type: ignore[union-attr]
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


@router.post("/import")
async def import_entry_from_file(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    current_user: UserPublic = Depends(get_current_user),
) -> dict:
    """Parse a HWP/PDF file and extract form data using Claude AI."""
    tmpl_col = MongoClientManager.get_form_templates_collection()
    try:
        tmpl_oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template_id")
    tmpl = await tmpl_col.find_one({"_id": tmpl_oid})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    content = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        text = _extract_pdf_text(content)
    elif filename.endswith(".hwp"):
        text = await _extract_hwp_text(content)
    else:
        raise HTTPException(status_code=415, detail="지원하지 않는 파일 형식입니다. PDF 또는 HWP 파일을 업로드하세요.")

    if not text.strip():
        raise HTTPException(status_code=422, detail="파일에서 텍스트를 추출할 수 없습니다.")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI 추출 기능이 설정되지 않았습니다.")

    extracted = await _extract_form_data_with_claude(text, tmpl.get("sections", []))
    return {"data": extracted}


@router.get("", response_model=list[FormEntryOut])
async def list_entries(
    template_id: str = Query(...),
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    query: dict = {"template_id": template_id}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    cursor = col.find(query).sort("created_at", -1)
    return [_to_out(doc) async for doc in cursor]


@router.post("", response_model=FormEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: FormEntryCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    now = _now()
    doc = {
        "template_id": payload.template_id,
        "data": payload.data,
        "version": 1,
        "is_deleted": False,
        "created_at": now,
        "created_by": current_user.email,
        "updated_at": now,
        "updated_by": current_user.email,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{entry_id}", response_model=FormEntryOut)
async def patch_entry(
    entry_id: str,
    payload: FormEntryPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry id")

    now = _now()
    result = await col.find_one_and_update(
        {"_id": oid, "version": payload.version, "is_deleted": {"$ne": True}},
        {"$set": {"data": payload.data, "updated_at": now, "updated_by": current_user.email},
         "$inc": {"version": 1}},
        return_document=True,
    )
    if result is None:
        doc = await col.find_one({"_id": oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        raise HTTPException(status_code=409, detail="Version conflict")
    return _to_out(result)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid entry id")

    result = await col.update_one(
        {"_id": oid, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "updated_at": _now(), "updated_by": current_user.email}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
