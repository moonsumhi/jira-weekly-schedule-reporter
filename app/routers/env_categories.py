"""관리자가 화면에서 직접 관리하는 동적 설정 값(카테고리 → 항목) CRUD.

예: '대상 시스템' 카테고리 아래 SR 접수 폼 드롭다운에 쓰일 시스템 목록.
카테고리 문서 안에 items를 임베드하는 구조라 items CRUD는 문서를 통째로
읽고 파이썬에서 리스트를 수정한 뒤 다시 저장하는 방식으로 처리한다.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.db.mongo import MongoClientManager
from app.models.env_category import (
    EnvCategoryCreate,
    EnvCategoryOut,
    EnvCategoryPatch,
    EnvItem,
    EnvItemCreate,
    EnvItemPatch,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.admin import require_admin
from app.utils.mongo import oid as parse_oid

router = APIRouter()


def _to_out(doc: dict) -> EnvCategoryOut:
    items = sorted(doc.get("items", []), key=lambda i: i.get("sort_order", 0))
    return EnvCategoryOut(
        id=str(doc["_id"]),
        key=doc.get("key", ""),
        label=doc.get("label", ""),
        is_system=bool(doc.get("is_system", False)),
        items=items,
    )


async def _get_category_or_404(category_id: str) -> dict:
    col = MongoClientManager.get_env_categories_collection()
    _oid = parse_oid(category_id, "잘못된 카테고리 ID입니다.")
    doc = await col.find_one({"_id": _oid})
    if not doc:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")
    return doc


@router.get("", response_model=list[EnvCategoryOut])
async def list_categories(current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_env_categories_collection()
    docs = [doc async for doc in col.find({})]
    return [_to_out(doc) for doc in docs]


@router.get("/by-key/{key}", response_model=list[EnvItem])
async def list_active_items_by_key(key: str, current_user: UserPublic = Depends(get_current_user)):
    col = MongoClientManager.get_env_categories_collection()
    doc = await col.find_one({"key": key})
    if not doc:
        return []
    items = [i for i in doc.get("items", []) if i.get("is_active", True)]
    items.sort(key=lambda i: i.get("sort_order", 0))
    return items


@router.post("", response_model=EnvCategoryOut, status_code=201)
async def create_category(payload: EnvCategoryCreate, _=Depends(require_admin)):
    col = MongoClientManager.get_env_categories_collection()
    if await col.find_one({"key": payload.key}):
        raise HTTPException(status_code=400, detail="이미 존재하는 카테고리 키입니다.")
    doc = {
        "key": payload.key,
        "label": payload.label,
        "is_system": False,
        "items": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{category_id}", response_model=EnvCategoryOut)
async def patch_category(category_id: str, payload: EnvCategoryPatch, _=Depends(require_admin)):
    col = MongoClientManager.get_env_categories_collection()
    _oid = parse_oid(category_id, "잘못된 카테고리 ID입니다.")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")
    doc = await col.find_one_and_update({"_id": _oid}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")
    return _to_out(doc)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: str, _=Depends(require_admin)):
    doc = await _get_category_or_404(category_id)
    if doc.get("is_system"):
        raise HTTPException(status_code=400, detail="시스템 기본 카테고리는 삭제할 수 없습니다.")
    col = MongoClientManager.get_env_categories_collection()
    await col.delete_one({"_id": doc["_id"]})


@router.post("/{category_id}/items", response_model=EnvCategoryOut, status_code=201)
async def add_item(category_id: str, payload: EnvItemCreate, _=Depends(require_admin)):
    doc = await _get_category_or_404(category_id)
    items = doc.get("items", [])
    if any(i.get("label", "").strip().lower() == payload.label.strip().lower() for i in items):
        raise HTTPException(status_code=400, detail="이미 존재하는 항목입니다.")
    next_order = (max((i.get("sort_order", 0) for i in items), default=-1)) + 1
    items.append({
        "id": str(uuid4()),
        "label": payload.label,
        "sort_order": next_order,
        "is_active": True,
    })
    col = MongoClientManager.get_env_categories_collection()
    await col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
    doc["items"] = items
    return _to_out(doc)


@router.patch("/{category_id}/items/{item_id}", response_model=EnvCategoryOut)
async def patch_item(category_id: str, item_id: str, payload: EnvItemPatch, _=Depends(require_admin)):
    doc = await _get_category_or_404(category_id)
    items = doc.get("items", [])
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다.")
    found = False
    for item in items:
        if item.get("id") == item_id:
            item.update(update)
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
    col = MongoClientManager.get_env_categories_collection()
    await col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
    doc["items"] = items
    return _to_out(doc)


@router.delete("/{category_id}/items/{item_id}", response_model=EnvCategoryOut)
async def delete_item(category_id: str, item_id: str, _=Depends(require_admin)):
    doc = await _get_category_or_404(category_id)
    items = doc.get("items", [])
    new_items = [i for i in items if i.get("id") != item_id]
    if len(new_items) == len(items):
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
    col = MongoClientManager.get_env_categories_collection()
    await col.update_one({"_id": doc["_id"]}, {"$set": {"items": new_items}})
    doc["items"] = new_items
    return _to_out(doc)
