"""Form template CRUD endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import MongoClientManager
from app.models.form_template import FormTemplateCreate, FormTemplatePatch, FormTemplateOut
from app.routers.admin import require_admin
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


def _to_out(doc: dict) -> FormTemplateOut:
    return FormTemplateOut(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        jira_issue_key=doc.get("jira_issue_key", ""),
        sections=doc.get("sections", []),
        menu=doc.get("menu"),
        sort_order=doc.get("sort_order"),
        is_deleted=bool(doc.get("is_deleted", False)),
        created_at=fmt_dt(doc.get("created_at")),
    )


@router.get("", response_model=list[FormTemplateOut])
async def list_form_templates(
    menu: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
):
    col = MongoClientManager.get_form_templates_collection()
    query: dict = {}
    if menu is not None:
        query["menu"] = {"$regex": f"^{menu}$", "$options": "i"}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    docs = [doc async for doc in col.find(query)]
    docs.sort(key=lambda d: (d.get("sort_order") is None, d.get("sort_order") or 0))
    return [_to_out(doc) for doc in docs]


@router.post("", response_model=FormTemplateOut, status_code=201)
async def create_form_template(payload: FormTemplateCreate, _=Depends(require_admin)):
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
async def patch_form_template(template_id: str, payload: FormTemplatePatch, _=Depends(require_admin)):
    col = MongoClientManager.get_form_templates_collection()
    _oid = parse_oid(template_id, "Invalid template id")
    update: dict = {}
    if payload.sort_order is not None:
        update["sort_order"] = payload.sort_order
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = await col.find_one_and_update(
        {"_id": _oid},
        {"$set": update},
        return_document=True,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_out(doc)


@router.get("/{template_id}", response_model=FormTemplateOut)
async def get_form_template(template_id: str):
    col = MongoClientManager.get_form_templates_collection()
    _oid = parse_oid(template_id, "Invalid template id")
    doc = await col.find_one({"_id": _oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_out(doc)


@router.delete("/{template_id}", response_model=FormTemplateOut)
async def delete_form_template(template_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_form_templates_collection()
    _oid = parse_oid(template_id, "Invalid template id")
    doc = await col.find_one_and_update(
        {"_id": _oid, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _to_out(doc)


@router.post("/{template_id}/restore", response_model=FormTemplateOut)
async def restore_form_template(template_id: str, _=Depends(require_admin)):
    col = MongoClientManager.get_form_templates_collection()
    _oid = parse_oid(template_id, "Invalid template id")
    doc = await col.find_one_and_update(
        {"_id": _oid, "is_deleted": True},
        {"$set": {"is_deleted": False, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Template not found or not deleted")
    return _to_out(doc)
