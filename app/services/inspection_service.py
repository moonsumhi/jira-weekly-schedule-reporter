# app/services/inspection_service.py
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
    checklist_id: str,
    action: str,
    changed_by: str,
    before: Optional[dict],
    after: Optional[dict],
    patch: Optional[dict],
):
    h = MongoClientManager.get_inspection_history_collection()
    doc = {
        "checklist_id": checklist_id,
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


class InspectionChecklistService:

    @staticmethod
    def _col():
        return MongoClientManager.get_inspection_checklists_collection()

    async def list(self, *, include_deleted: bool) -> List[Dict[str, Any]]:
        q = {} if include_deleted else {"is_deleted": {"$ne": True}}
        items: List[Dict[str, Any]] = []
        async for doc in self._col().find(q).sort("inspection_month", -1):
            items.append(to_out(doc))
        return items

    async def create(
        self,
        *,
        inspection_month: str,
        person_in_charge: str,
        system_room_result: str,
        resource_usage_abnormal: bool,
        notes: Optional[str],
        actor_email: str,
    ) -> Dict[str, Any]:
        col = self._col()

        # Check for duplicate entry for same month
        if await col.find_one({"inspection_month": inspection_month, "is_deleted": {"$ne": True}}):
            raise ValueError("해당 월의 점검표가 이미 존재합니다.")

        now = TimeUtil.now_utc()
        doc = {
            "inspection_month": inspection_month,
            "person_in_charge": person_in_charge,
            "system_room_result": system_room_result,
            "resource_usage_abnormal": resource_usage_abnormal,
            "notes": notes,
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
            checklist_id=out["id"],
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
        inspection_month: str,
        person_in_charge: str,
        system_room_result: str,
        resource_usage_abnormal: bool,
        notes: Optional[str],
        actor_email: str,
    ) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("Not found")

        if inspection_month != existing["inspection_month"]:
            if await col.find_one({"inspection_month": inspection_month, "is_deleted": {"$ne": True}}):
                raise ValueError("해당 월의 점검표가 이미 존재합니다.")

        now = TimeUtil.now_utc()
        new_doc = {
            "inspection_month": inspection_month,
            "person_in_charge": person_in_charge,
            "system_room_result": system_room_result,
            "resource_usage_abnormal": resource_usage_abnormal,
            "notes": notes,
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
            checklist_id=after_out["id"],
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

        inspection_month = patch.get("inspection_month")
        if inspection_month is not None and inspection_month != existing["inspection_month"]:
            if await col.find_one({"inspection_month": inspection_month, "is_deleted": {"$ne": True}}):
                raise ValueError("해당 월의 점검표가 이미 존재합니다.")
            update["inspection_month"] = inspection_month

        if patch.get("person_in_charge") is not None:
            update["person_in_charge"] = patch["person_in_charge"]

        if patch.get("system_room_result") is not None:
            update["system_room_result"] = patch["system_room_result"]

        if patch.get("resource_usage_abnormal") is not None:
            update["resource_usage_abnormal"] = patch["resource_usage_abnormal"]

        if "notes" in patch:
            update["notes"] = patch["notes"]

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
            checklist_id=after_out["id"],
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
            checklist_id=str(_id),
            action="DELETE",
            changed_by=actor_email,
            before=to_out(existing),
            after=to_out(after),
            patch={"$set": update},
        )

    async def get_history(self, *, checklist_id: str) -> List[Dict[str, Any]]:
        h = MongoClientManager.get_inspection_history_collection()
        cursor = h.find({"checklist_id": checklist_id}).sort("changed_at", -1)
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            items.append(to_out(doc))
        return items
