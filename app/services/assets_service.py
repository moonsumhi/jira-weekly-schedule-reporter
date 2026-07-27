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
    history_col=None,
    source: str = "manual",
):
    h = history_col if history_col is not None else MongoClientManager.get_assets_server_history_collection()
    doc = {
        "asset_id": asset_id,
        "action": action,
        "changed_at": TimeUtil.now_utc(),
        "changed_by": changed_by,
        "source": source,
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


async def _check_asset_id(col, asset_id: Optional[str], exclude_id=None) -> None:
    """asset_id 중복 체크 (유형별 PK). 비어있으면 스킵."""
    if not asset_id:
        return
    q: dict = {"asset_id": asset_id, "is_deleted": {"$ne": True}}
    if exclude_id is not None:
        q["_id"] = {"$ne": exclude_id}
    if await col.find_one(q):
        raise ValueError(f"asset_id '{asset_id}'이(가) 이미 사용 중입니다.")



def _ip_asset_type_query(ip: str, asset_type: str) -> dict:
    """IP + 자산유형 조합 중복 체크 쿼리. 서버(기본값)는 필드 미설정 도큐먼트도 포함."""
    base = {"ip": ip, "is_deleted": {"$ne": True}}
    if asset_type == "서버":
        return {**base, "$or": [{"fields.자산유형": "서버"}, {"fields.자산유형": {"$exists": False}}]}
    return {**base, "fields.자산유형": asset_type}


async def list_all_assets(*, include_deleted: bool) -> List[Dict[str, Any]]:
    """모든 자산 컬렉션을 $unionWith로 합쳐 반환."""
    db = MongoClientManager.get_db()
    all_cols = list(MongoClientManager.CATEGORY_COLLECTIONS.values())
    primary_col_name = all_cols[0][0]
    union_cols = [pair[0] for pair in all_cols[1:]]

    q = {} if include_deleted else {"is_deleted": {"$ne": True}}
    pipeline: List[Dict[str, Any]] = [{"$match": q}]
    for col_name in union_cols:
        pipeline.append({"$unionWith": {"coll": col_name, "pipeline": [{"$match": q}]}})
    pipeline.append({"$sort": {"ip": 1}})

    items: List[Dict[str, Any]] = []
    async for doc in db[primary_col_name].aggregate(pipeline):
        items.append(to_out(doc))
    return items


class AssetsService:

    def __init__(self, category: str = "서버"):
        col_name, hist_name = MongoClientManager.CATEGORY_COLLECTIONS.get(
            category, MongoClientManager.CATEGORY_COLLECTIONS["서버"]
        )
        self._col_name = col_name
        self._hist_col_name = hist_name

    def _col(self):
        return MongoClientManager.get_db()[self._col_name]

    def _hist(self):
        return MongoClientManager.get_db()[self._hist_col_name]

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
        asset_id: Optional[str] = None,
        asset_no: Optional[str] = None,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
        source: str = "manual",
    ) -> Dict[str, Any]:
        col = self._col()

        await _check_asset_id(col, asset_id)

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
        if asset_id:
            doc["asset_id"] = asset_id
        if asset_no:
            doc["asset_no"] = asset_no
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
            history_col=self._hist(),
            source=source,
        )
        return out

    async def replace(
        self,
        *,
        _id: ObjectId,
        ip: str,
        name: str,
        asset_id: Optional[str] = None,
        asset_no: Optional[str] = None,
        fields: Optional[Dict[str, Any]],
        actor_email: str,
    ) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("찾을 수 없습니다.")

        if asset_id != existing.get("asset_id"):
            await _check_asset_id(col, asset_id, exclude_id=_id)

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

        unset_fields: Dict[str, Any] = {}
        if asset_id:
            new_doc["asset_id"] = asset_id
        else:
            unset_fields["asset_id"] = ""
        if asset_no:
            new_doc["asset_no"] = asset_no
        else:
            unset_fields["asset_no"] = ""
        mongo_op: Dict[str, Any] = {"$set": new_doc}
        if unset_fields:
            mongo_op["$unset"] = unset_fields
        await col.update_one({"_id": _id}, mongo_op)

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
            history_col=self._hist(),
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
            raise KeyError("찾을 수 없습니다.")

        if (
            expected_version is not None
            and int(existing.get("version", 1)) != expected_version
        ):
            raise ValueError("다른 사용자가 먼저 수정했습니다. 새로고침 후 다시 시도해주세요.")

        update: Dict[str, Any] = {}

        ip = patch.get("ip")
        if ip is not None and ip != existing["ip"]:
            asset_type = existing.get("fields", {}).get("자산유형", "서버")
            if await col.find_one({**_ip_asset_type_query(ip, asset_type), "_id": {"$ne": _id}}):
                raise ValueError(f"자산유형 '{asset_type}'에 동일한 IP가 이미 존재합니다.")
            update["ip"] = ip

        if patch.get("name") is not None:
            update["name"] = patch["name"]

        unset: Dict[str, Any] = {}
        if "asset_id" in patch and patch["asset_id"] != existing.get("asset_id"):
            await _check_asset_id(col, patch["asset_id"], exclude_id=_id)
            if patch["asset_id"]:
                update["asset_id"] = patch["asset_id"]
            else:
                unset["asset_id"] = ""

        if "asset_no" in patch and patch["asset_no"] != existing.get("asset_no"):
            if patch["asset_no"]:
                update["asset_no"] = patch["asset_no"]
            else:
                unset["asset_no"] = ""

        if patch.get("fields") is not None:
            if not isinstance(patch["fields"], dict):
                raise ValueError("fields는 객체(object) 형식이어야 합니다.")
            update["fields"] = patch["fields"]

        if not update and not unset:
            return to_out(existing)

        now = TimeUtil.now_utc()
        update["updated_at"] = now
        update["updated_by"] = actor_email
        update["version"] = int(existing.get("version", 1)) + 1

        mongo_update: Dict[str, Any] = {"$set": update}
        if unset:
            mongo_update["$unset"] = unset
        await col.update_one({"_id": _id}, mongo_update)

        after = {**existing, **update, "_id": _id}
        for k in unset:
            after.pop(k, None)
        before_out = to_out(existing)
        after_out = to_out(after)

        await _write_history(
            asset_id=after_out["id"],
            action="UPDATE",
            changed_by=actor_email,
            before=before_out,
            after=after_out,
            patch={"$set": update},
            history_col=self._hist(),
        )
        return after_out

    async def delete(self, *, _id: ObjectId, actor_email: str, reason: Optional[str] = None) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": {"$ne": True}})
        if not existing:
            raise KeyError("찾을 수 없습니다.")

        now = TimeUtil.now_utc()
        update = {
            "is_deleted": True,
            "delete_reason": reason or "",
            "deleted_at": now,
            "deleted_by": actor_email,
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
            history_col=self._hist(),
        )
        return to_out(after)

    async def restore(self, *, _id: ObjectId, actor_email: str) -> Dict[str, Any]:
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": True})
        if not existing:
            raise KeyError("찾을 수 없거나 삭제된 상태가 아닙니다.")

        now = TimeUtil.now_utc()
        update = {
            "is_deleted": False,
            "updated_at": now,
            "updated_by": actor_email,
            "version": int(existing.get("version", 1)) + 1,
        }
        await col.update_one(
            {"_id": _id},
            {"$set": update, "$unset": {"delete_reason": "", "deleted_at": "", "deleted_by": ""}},
        )

        after = {**existing, **update, "_id": _id}
        after.pop("delete_reason", None)
        after.pop("deleted_at", None)
        after.pop("deleted_by", None)

        await _write_history(
            asset_id=str(_id),
            action="UPDATE",
            changed_by=actor_email,
            before=to_out(existing),
            after=to_out(after),
            patch={"$set": update},
            history_col=self._hist(),
        )
        return to_out(after)

    async def purge(self, *, _id: ObjectId, actor_email: str) -> None:
        """소프트 삭제된 자산을 완전히 삭제한다. 되돌릴 수 없다."""
        col = self._col()

        existing = await col.find_one({"_id": _id, "is_deleted": True})
        if not existing:
            raise KeyError("찾을 수 없거나 삭제된 상태가 아닙니다.")

        await _write_history(
            asset_id=str(_id),
            action="PURGE",
            changed_by=actor_email,
            before=to_out(existing),
            after=None,
            patch=None,
            history_col=self._hist(),
        )
        await col.delete_one({"_id": _id})

    async def get_history(self, *, server_id: str) -> List[Dict[str, Any]]:
        h = self._hist()
        cursor = h.find({"asset_id": server_id}).sort("changed_at", -1)
        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            items.append(to_out(doc))
        return items
