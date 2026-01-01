# app/routers/assets_servers.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.mongo import MongoClientManager
from app.models.assets import (
    ServerAssetCreate,
    ServerAssetReplace,
    ServerAssetPatch,
    ServerAssetOut,
    AssetHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.utils.time import TimeUtil

router = APIRouter()


def oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def to_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.setdefault("fields", {})
    return doc


def diff_docs(before: dict, after: dict) -> List[dict]:
    changes: List[dict] = []

    def walk(path: str, a: Any, b: Any):
        if type(a) != type(b):
            changes.append({"path": path, "before": a, "after": b})
            return
        if isinstance(a, dict):
            keys = set(a.keys()) | set(b.keys())
            for k in sorted(keys):
                walk(f"{path}.{k}" if path else k, a.get(k), b.get(k))
            return
        if a != b:
            changes.append({"path": path, "before": a, "after": b})

    walk("", before, after)
    return changes


async def write_history(
    asset_id: str,
    action: str,
    changed_by: str,
    before: Optional[dict],
    after: Optional[dict],
    patch: Optional[dict],
):
    h = MongoClientManager.get_assets_server_history_collection()
    doc = {
        "asset_id": asset_id,
        "action": action,
        "changed_at": TimeUtil.now_utc(),
        "changed_by": changed_by,
        "patch": patch,
        "diff": (
            diff_docs(before or {}, after or {})
            if before is not None and after is not None
            else None
        ),
        "before": before,
        "after": after,
    }
    await h.insert_one(doc)


# -------------------
# routes
# -------------------
@router.get("", response_model=List[ServerAssetOut])
async def list_servers(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_assets_servers_collection()
    q = {} if include_deleted else {"is_deleted": {"$ne": True}}

    items: List[ServerAssetOut] = []
    async for doc in col.find(q).sort("ip", 1):
        items.append(ServerAssetOut(**to_out(doc)))
    return items


@router.post("", response_model=ServerAssetOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerAssetCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_assets_servers_collection()

    # prevent duplicates
    if await col.find_one({"ip": body.ip, "is_deleted": {"$ne": True}}):
        raise HTTPException(status_code=409, detail="IP already exists")

    now = TimeUtil.now_utc()
    doc = {
        "ip": body.ip,
        "name": body.name,
        "fields": body.fields or {},
        "created_at": now,
        "created_by": current_user.email,
        "updated_at": now,
        "updated_by": current_user.email,
        "version": 1,
        "is_deleted": False,
    }
    res = await col.insert_one(doc)
    doc["_id"] = res.inserted_id

    out = to_out(doc)
    await write_history(
        asset_id=out["id"],
        action="CREATE",
        changed_by=current_user.email,
        before=None,
        after=out,
        patch=None,
    )
    return ServerAssetOut(**out)


@router.put("/{server_id}", response_model=ServerAssetOut)
async def replace_server(
    server_id: str,
    body: ServerAssetReplace,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_assets_servers_collection()
    _id = oid(server_id)

    existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")

    # ip conflict if changed
    if body.ip != existing["ip"]:
        if await col.find_one({"ip": body.ip, "is_deleted": {"$ne": True}}):
            raise HTTPException(status_code=409, detail="IP already exists")

    now = TimeUtil.now_utc()
    new_doc = {
        "ip": body.ip,
        "name": body.name,
        "fields": body.fields or {},
        "updated_at": now,
        "updated_by": current_user.email,
        "version": int(existing.get("version", 1)) + 1,
        "is_deleted": False,
        # keep created meta
        "created_at": existing.get("created_at"),
        "created_by": existing.get("created_by"),
    }

    await col.update_one({"_id": _id}, {"$set": new_doc})

    after = {**existing, **new_doc, "_id": _id}
    before_out = to_out(existing)
    after_out = to_out(after)

    await write_history(
        asset_id=after_out["id"],
        action="UPDATE",
        changed_by=current_user.email,
        before=before_out,
        after=after_out,
        patch={"replace": True},
    )

    return ServerAssetOut(**after_out)


@router.patch("/{server_id}", response_model=ServerAssetOut)
async def patch_server(
    server_id: str,
    body: ServerAssetPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_assets_servers_collection()
    _id = oid(server_id)

    existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")

    # optimistic lock (optional)
    if body.version is not None and int(existing.get("version", 1)) != body.version:
        raise HTTPException(
            status_code=409, detail="Version conflict. Reload and retry."
        )

    update: Dict[str, Any] = {}

    if body.ip is not None and body.ip != existing["ip"]:
        if await col.find_one({"ip": body.ip, "is_deleted": {"$ne": True}}):
            raise HTTPException(status_code=409, detail="IP already exists")
        update["ip"] = body.ip

    if body.name is not None:
        update["name"] = body.name

    if body.fields is not None:
        if not isinstance(body.fields, dict):
            raise HTTPException(status_code=400, detail="fields must be an object")
        update["fields"] = body.fields

    if not update:
        return ServerAssetOut(**to_out(existing))

    now = TimeUtil.now_utc()
    update["updated_at"] = now
    update["updated_by"] = current_user.email
    update["version"] = int(existing.get("version", 1)) + 1

    await col.update_one({"_id": _id}, {"$set": update})

    after = {**existing, **update, "_id": _id}
    before_out = to_out(existing)
    after_out = to_out(after)

    await write_history(
        asset_id=after_out["id"],
        action="UPDATE",
        changed_by=current_user.email,
        before=before_out,
        after=after_out,
        patch={"$set": update},
    )

    return ServerAssetOut(**after_out)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_assets_servers_collection()
    _id = oid(server_id)

    existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")

    now = TimeUtil.now_utc()
    update = {
        "is_deleted": True,
        "updated_at": now,
        "updated_by": current_user.email,
        "version": int(existing.get("version", 1)) + 1,
    }
    await col.update_one({"_id": _id}, {"$set": update})

    after = {**existing, **update, "_id": _id}

    await write_history(
        asset_id=server_id,
        action="DELETE",
        changed_by=current_user.email,
        before=to_out(existing),
        after=to_out(after),
        patch={"$set": update},
    )

    return


@router.get("/{server_id}/history", response_model=List[AssetHistoryOut])
async def get_history(
    server_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    h = MongoClientManager.get_assets_server_history_collection()
    cursor = h.find({"asset_id": server_id}).sort("changed_at", -1)

    items: List[AssetHistoryOut] = []
    async for doc in cursor:
        doc = to_out(doc)
        items.append(AssetHistoryOut(**doc))
    return items
