"""Form template CRUD endpoints."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any

from app.db.mongo import MongoClientManager

router = APIRouter()


class FormTemplateCreate(BaseModel):
    title: str
    jira_issue_key: str
    sections: list[Any]
    menu: str | None = None  # e.g. "Job", "Timetable"
    sort_order: int | None = None


class FormTemplatePatch(BaseModel):
    sort_order: int | None = None


class FormTemplateOut(BaseModel):
    id: str
    title: str
    jira_issue_key: str
    sections: list[Any]
    menu: str | None = None
    sort_order: int | None = None
    created_at: str | None = None


def _to_out(doc: dict) -> FormTemplateOut:
    created_at = doc.get("created_at")
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        created_at = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    return FormTemplateOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        jira_issue_key=doc.get("jira_issue_key", ""),
        sections=doc.get("sections", []),
        menu=doc.get("menu"),
        sort_order=doc.get("sort_order"),
        created_at=created_at,
    )


@router.get("", response_model=list[FormTemplateOut])
async def list_form_templates(menu: str | None = Query(default=None)):
    col = MongoClientManager.get_form_templates_collection()
    query = {}
    if menu is not None:
        query["menu"] = {"$regex": f"^{menu}$", "$options": "i"}
    docs = [doc async for doc in col.find(query)]
    # Sort: sort_order asc (None last), then created_at desc
    docs.sort(key=lambda d: (d.get("sort_order") is None, d.get("sort_order") or 0))
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=FormTemplateOut, status_code=201)
async def create_form_template(payload: FormTemplateCreate):
    col = MongoClientManager.get_form_templates_collection()
    now = datetime.now(timezone.utc)
    doc = {
        "title": payload.title,
        "jira_issue_key": payload.jira_issue_key,
        "sections": payload.sections,
        "created_at": now,
    }
    if payload.menu is not None:
        doc["menu"] = payload.menu
    if payload.sort_order is not None:
        doc["sort_order"] = payload.sort_order
    result = await col.find_one_and_replace(
        {"jira_issue_key": payload.jira_issue_key},
        doc,
        upsert=True,
        return_document=True,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to upsert form template")
    return _to_out(result)


@router.patch("/{template_id}", response_model=FormTemplateOut)
async def patch_form_template(template_id: str, payload: FormTemplatePatch):
    col = MongoClientManager.get_form_templates_collection()
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template id")
    update: dict = {}
    if payload.sort_order is not None:
        update["sort_order"] = payload.sort_order
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = await col.find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_out(doc)


@router.get("/{template_id}", response_model=FormTemplateOut)
async def get_form_template(template_id: str):
    col = MongoClientManager.get_form_templates_collection()
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template id")
    doc = await col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_out(doc)


@router.delete("/{template_id}", status_code=204)
async def delete_form_template(template_id: str):
    col = MongoClientManager.get_form_templates_collection()
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template id")
    result = await col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
