# app/services/assets_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.utils.mongo import to_out
from app.utils.time import TimeUtil


def _diff_docs(before: dict, after: dict) -> List[dict]:
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


async def _write_history(
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
            _diff_docs(before or {}, after or {})
            if before is not None and after is not None
            else None
        ),
        "before": before,
        "after": after,
    }
    await h.insert_one(doc)


class AssetsService:

    @staticmethod
    def _col():
        return MongoClientManager.get_assets_servers_collection()

    async def list(self, *, include_deleted: bool) -> List[Dict[str, Any]]:
        q = {} if include_deleted else {"is_deleted": {"$ne": True}}
        items: List[Dict[str, Any]] = []
        async for doc in self._col().find(q).sort("ip", 1):
            items.append(to_out(doc))
        return items

    async def create(
        self,
        *,
        ip: str,
        name: str,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
    ) -> Dict[str, Any]:
        col = self._col()

        if await col.find_one({"ip": ip, "is_deleted": {"$ne": True}}):
            raise ValueError("IP already exists")

        now = TimeUtil.now_utc()
        doc = {
            "ip": ip,
            "name": name,
            "fields": fields or {},
            "created_at": now,
            "created_by": actor_email,
            "updated_at": now,
            "updated_by": actor_email,
            "version": 1,
            "is_deleted": False,
        }
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id

        out = to_out(doc)
        await _write_history(
            asset_id=out["id"],
            action="CREATE",
            changed_by=actor_email,
            before=None,
            after=out,
            patch=None,
        )
        return out

    async def replace(
        self,
        *,
        _id: ObjectId,
        ip: str,
        name: str,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
    ) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("Not found")

        if ip != existing["ip"]:
            if await col.find_one({"ip": ip, "is_deleted": {"$ne": True}}):
                raise ValueError("IP already exists")

        now = TimeUtil.now_utc()
        new_doc = {
            "ip": ip,
            "name": name,
            "fields": fields or {},
            "updated_at": now,
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
            "is_deleted": False,
            "created_at": existing.get("created_at"),
            "created_by": existing.get("created_by"),
        }

        await col.update_one({"_id": _id}, {"$set": new_doc})

        after = {**existing, **new_doc, "_id": _id}
        before_out = to_out(existing)
        after_out = to_out(after)

        await _write_history(
            asset_id=after_out["id"],
            action="UPDATE",
            changed_by=actor_email,
            before=before_out,
            after=after_out,
            patch={"replace": True},
        )
        return after_out

    async def patch(
        self,
        *,
        _id: ObjectId,
        patch: Dict[str, Any],
        actor_email: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("Not found")

        if (
            expected_version is not None
            and int(existing.get("version", 1)) != expected_version
        ):
            raise ValueError("Version conflict. Reload and retry.")

        update: Dict[str, Any] = {}

        ip = patch.get("ip")
        if ip is not None and ip != existing["ip"]:
            if await col.find_one({"ip": ip, "is_deleted": {"$ne": True}}):
                raise ValueError("IP already exists")
            update["ip"] = ip

        if patch.get("name") is not None:
            update["name"] = patch["name"]

        if patch.get("fields") is not None:
            if not isinstance(patch["fields"], dict):
                raise ValueError("fields must be an object")
            update["fields"] = patch["fields"]

        if not update:
            return to_out(existing)

        now = TimeUtil.now_utc()
        update["updated_at"] = now
        update["updated_by"] = actor_email
        update["version"] = int(existing.get("version", 1)) + 1

        await col.update_one({"_id": _id}, {"$set": update})

        after = {**existing, **update, "_id": _id}
        before_out = to_out(existing)
        after_out = to_out(after)

        await _write_history(
            asset_id=after_out["id"],
            action="UPDATE",
            changed_by=actor_email,
            before=before_out,
            after=after_out,
            patch={"$set": update},
        )
        return after_out

    async def delete(self, *, _id: ObjectId, actor_email: str) -> None:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("Not found")

        now = TimeUtil.now_utc()
        update = {
            "is_deleted": True,
            "updated_at": now,
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
        }
        await col.update_one({"_id": _id}, {"$set": update})

        after = {**existing, **update, "_id": _id}

        await _write_history(
            asset_id=str(_id),
            action="DELETE",
            changed_by=actor_email,
            before=to_out(existing),
            after=to_out(after),
            patch={"$set": update},
        )

    async def get_history(self, *, server_id: str) -> List[Dict[str, Any]]:
        h = MongoClientManager.get_assets_server_history_collection()
        cursor = h.find({"asset_id": server_id}).sort("changed_at", -1)
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            items.append(to_out(doc))
        return items
