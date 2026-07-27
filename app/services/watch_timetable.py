# app/services/watch_timetable.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.utils.time import TimeUtil
from app.utils.mongo import to_out


def _diff_docs(before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []

    def walk(path: str, a: Any, b: Any) -> None:
        if type(a) != type(b):
            changes.append({"path": path, "before": a, "after": b})
            return
        if isinstance(a, dict):
            for key in set(list(a.keys()) + list(b.keys())):
                walk(f"{path}.{key}" if path else key, a.get(key), b.get(key))
            return
        if a != b:
            changes.append({"path": path, "before": a, "after": b})

    walk("", before, after)
    return changes


async def _write_watch_history(
    assignment_id: str,
    action: str,
    changed_by: str,
    before: Optional[Dict[str, Any]],
    after: Optional[Dict[str, Any]],
) -> None:
    col = MongoClientManager.get_watch_history_collection()
    await col.insert_one({
        "assignment_id": assignment_id,
        "action": action,
        "changed_at": TimeUtil.now_utc(),
        "changed_by": changed_by,
        "before": before,
        "after": after,
        "diff": (
            _diff_docs(before or {}, after or {})
            if before is not None and after is not None
            else None
        ),
    })


class WatchTimetableService:
    """
    Watch timetable CRUD + overlap rules.
    Keeps router thin.
    """

    def __init__(self, *, enforce_no_overlap_per_assignee: bool = True):
        self.enforce_no_overlap_per_assignee = enforce_no_overlap_per_assignee

    def _col(self):
        return MongoClientManager.get_watch_assignments_collection()

    @staticmethod
    def _validate_range(start: datetime, end: datetime):
        if end <= start:
            raise ValueError("종료 시각은 시작 시각 이후여야 합니다.")

    async def _check_overlap(
        self,
        *,
        assignee: str,
        start: datetime,
        end: datetime,
        exclude_id: Optional[ObjectId] = None,
    ):
        """
        Overlap if existing.start < end AND existing.end > start
        """
        q: Dict[str, Any] = {
            "is_deleted": {"$ne": True},
            "start": {"$lt": end},
            "end": {"$gt": start},
        }
        if self.enforce_no_overlap_per_assignee:
            q["assignee"] = assignee

        if exclude_id is not None:
            q["_id"] = {"$ne": exclude_id}

        if await self._col().find_one(q):
            msg = "기존 배정과 시간이 겹칩니다."
            if self.enforce_no_overlap_per_assignee:
                msg = "동일 담당자의 기존 배정과 시간이 겹칩니다."
            raise ValueError(msg)

    async def list(
        self,
        *,
        start: Optional[datetime],
        end: Optional[datetime],
        include_deleted: bool,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {} if include_deleted else {"is_deleted": {"$ne": True}}

        # FullCalendar range loading (overlap window)
        if start is not None:
            q.setdefault("end", {})
            q["end"]["$gte"] = start
        if end is not None:
            q.setdefault("start", {})
            q["start"]["$lte"] = end

        items: List[Dict[str, Any]] = []
        async for doc in self._col().find(q).sort("start", 1):
            items.append(to_out(doc))
        return items

    async def create(
        self,
        *,
        assignee: str,
        start: datetime,
        end: datetime,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
    ) -> Dict[str, Any]:
        self._validate_range(start, end)
        await self._check_overlap(assignee=assignee, start=start, end=end)

        now = TimeUtil.now_utc()
        doc = {
            "assignee": assignee,
            "start": start,
            "end": end,
            "fields": fields or {},
            "created_at": now,
            "created_by": actor_email,
            "updated_at": now,
            "updated_by": actor_email,
            "version": 1,
            "is_deleted": False,
        }

        res = await self._col().insert_one(doc)
        doc["_id"] = res.inserted_id
        out = to_out(doc)
        await _write_watch_history(out["id"], "CREATE", actor_email, None, out)
        return out

    async def replace(
        self,
        *,
        _id: ObjectId,
        assignee: str,
        start: datetime,
        end: datetime,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
    ) -> Dict[str, Any]:
        self._validate_range(start, end)

        existing = await self._col().find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("찾을 수 없습니다.")

        await self._check_overlap(
            assignee=assignee, start=start, end=end, exclude_id=_id
        )

        now = TimeUtil.now_utc()
        new_doc = {
            "assignee": assignee,
            "start": start,
            "end": end,
            "fields": fields or {},
            "updated_at": now,
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
            "is_deleted": False,
            # keep created meta
            "created_at": existing.get("created_at"),
            "created_by": existing.get("created_by"),
        }

        await self._col().update_one({"_id": _id}, {"$set": new_doc})
        out = to_out({**existing, **new_doc, "_id": _id})
        await _write_watch_history(out["id"], "UPDATE", actor_email, to_out(existing), out)
        return out

    async def patch(
        self,
        *,
        _id: ObjectId,
        patch: Dict[str, Any],
        actor_email: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        existing = await self._col().find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("찾을 수 없습니다.")

        if (
            expected_version is not None
            and int(existing.get("version", 1)) != expected_version
        ):
            raise ValueError("다른 사용자가 먼저 수정했습니다. 새로고침 후 다시 시도해주세요.")

        update: Dict[str, Any] = {}
        for k in ("assignee", "start", "end", "fields"):
            if k in patch and patch[k] is not None:
                update[k] = patch[k]

        if not update:
            return to_out(existing)

        new_start = update.get("start", existing["start"])
        new_end = update.get("end", existing["end"])
        self._validate_range(new_start, new_end)

        new_assignee = update.get("assignee", existing["assignee"])
        await self._check_overlap(
            assignee=new_assignee,
            start=new_start,
            end=new_end,
            exclude_id=_id,
        )

        update["updated_at"] = TimeUtil.now_utc()
        update["updated_by"] = actor_email
        update["version"] = int(existing.get("version", 1)) + 1

        await self._col().update_one({"_id": _id}, {"$set": update})
        out = to_out({**existing, **update, "_id": _id})
        await _write_watch_history(out["id"], "UPDATE", actor_email, to_out(existing), out)
        return out

    async def delete(self, *, _id: ObjectId, actor_email: str) -> None:
        existing = await self._col().find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("찾을 수 없습니다.")

        update = {
            "is_deleted": True,
            "updated_at": TimeUtil.now_utc(),
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
        }
        await self._col().update_one({"_id": _id}, {"$set": update})
        await _write_watch_history(str(_id), "DELETE", actor_email, to_out(existing), None)
