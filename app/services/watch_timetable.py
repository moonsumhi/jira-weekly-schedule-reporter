# app/services/watch_timetable.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager
from app.utils.time import TimeUtil
from app.utils.mongo import to_out


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
            raise HTTPException(status_code=400, detail="end must be after start")

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
            msg = "Overlaps existing assignment"
            if self.enforce_no_overlap_per_assignee:
                msg += " for the same assignee"
            raise HTTPException(status_code=409, detail=msg)

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
        return to_out(doc)

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
            raise HTTPException(status_code=404, detail="Not found")

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
        return to_out({**existing, **new_doc, "_id": _id})

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
            raise HTTPException(status_code=404, detail="Not found")

        if (
            expected_version is not None
            and int(existing.get("version", 1)) != expected_version
        ):
            raise HTTPException(status_code=409, detail="Version conflict")

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
        return to_out({**existing, **update, "_id": _id})

    async def delete(self, *, _id: ObjectId, actor_email: str) -> None:
        existing = await self._col().find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise HTTPException(status_code=404, detail="Not found")

        update = {
            "is_deleted": True,
            "updated_at": TimeUtil.now_utc(),
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
        }
        await self._col().update_one({"_id": _id}, {"$set": update})
