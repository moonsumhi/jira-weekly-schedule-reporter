# app/services/rack_service.py
"""랙 목록·배치도·검색 조회.

랙 자체는 assets_racks(카테고리 "랙"), 배치는 rack_placements 가 원본이다.
자산 컬렉션이 카테고리별로 분리돼 있으므로, 배치도를 만들 때 자산정보는
카테고리별로 묶어 _id $in 으로 한 번에 조회한다(자산 1건씩 조회 금지).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager
from app.utils.mongo import oid

_SEARCH_CATEGORIES = ["서버", "네트워크", "정보보호시스템", "DBMS", "VMware"]
_SEARCH_LIMIT_PER_CAT = 20


def _placements_col():
    return MongoClientManager.get_rack_placements_collection()


def _rack_col():
    return MongoClientManager.get_asset_collection("랙")


# ── 점유율 계산 ──────────────────────────────────────────────────────────────

def _occupied_units(placements: List[dict]) -> Set[int]:
    units: Set[int] = set()
    for p in placements:
        for slot in p.get("occupied_slots", []):
            try:
                units.add(int(str(slot).split(":")[1]))
            except (IndexError, ValueError):
                continue
    return units


def _max_contiguous_free(total_u: int, occupied: Set[int]) -> int:
    best = run = 0
    for u in range(1, total_u + 1):
        if u in occupied:
            run = 0
        else:
            run += 1
            best = max(best, run)
    return best


def _rack_summary(rack: dict, placements: List[dict]) -> dict:
    fields = rack.get("fields") or {}
    try:
        total_u = int(fields.get("total_u"))
    except (TypeError, ValueError):
        total_u = 0
    occupied = _occupied_units(placements)
    used_u = len(occupied)
    free_u = max(total_u - used_u, 0)
    return {
        "rack_id": str(rack["_id"]),
        "asset_code": rack.get("asset_id"),
        "name": rack.get("name", ""),
        "server_room": fields.get("server_room"),
        "total_u": total_u,
        "used_u": used_u,
        "free_u": free_u,
        "usage_rate": round(used_u / total_u * 100, 1) if total_u else 0.0,
        "max_contiguous_free_u": _max_contiguous_free(total_u, occupied) if total_u else 0,
        "asset_count": len(placements),
        "status": fields.get("status"),
        "max_load_kg": _num(fields.get("max_load_kg")),
        "max_power_w": _num(fields.get("max_power_w")),
    }


def _num(v: Any) -> Optional[float]:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


# ── 카테고리 횡단 자산 일괄 조회 ──────────────────────────────────────────────

async def _resolve_assets(placements: List[dict]) -> Dict[str, dict]:
    """배치 목록의 자산정보를 카테고리별 $in 으로 일괄 조회. key = str(asset_ref_id)."""
    by_cat: Dict[str, List[ObjectId]] = {}
    for p in placements:
        by_cat.setdefault(p["asset_category"], []).append(p["asset_ref_id"])

    result: Dict[str, dict] = {}
    for category, ids in by_cat.items():
        col = MongoClientManager.get_asset_collection(category)
        async for a in col.find({"_id": {"$in": ids}}):
            result[str(a["_id"])] = a
    return result


# ── 랙 목록 ──────────────────────────────────────────────────────────────────

async def list_racks(server_room: Optional[str] = None) -> List[dict]:
    q: dict = {"is_deleted": {"$ne": True}}
    if server_room:
        q["fields.server_room"] = server_room
    racks = await _rack_col().find(q).sort("asset_id", 1).to_list(None)

    summaries: List[dict] = []
    for rack in racks:
        placements = await _placements_col().find({
            "rack_ref_id": rack["_id"], "is_deleted": False,
        }).to_list(None)
        summaries.append(_rack_summary(rack, placements))
    return summaries


# ── 랙 배치도 ────────────────────────────────────────────────────────────────

async def get_layout(rack_id: str) -> dict:
    rack_oid = oid(rack_id, "잘못된 랙 ID입니다.")
    rack = await _rack_col().find_one({"_id": rack_oid, "is_deleted": {"$ne": True}})
    if not rack:
        raise HTTPException(status_code=404, detail="랙을 찾을 수 없습니다.")

    placements = await _placements_col().find({
        "rack_ref_id": rack_oid, "is_deleted": False,
    }).sort("start_u", -1).to_list(None)

    assets = await _resolve_assets(placements)
    items: List[dict] = []
    for p in placements:
        a = assets.get(str(p["asset_ref_id"])) or {}
        items.append({
            "placement_id": str(p["_id"]),
            "asset_category": p["asset_category"],
            "asset_id": str(p["asset_ref_id"]),
            "asset_code": a.get("asset_id"),
            "asset_no": a.get("asset_no"),
            "name": a.get("name", "(삭제된 자산)"),
            "ip": a.get("ip"),
            "start_u": p["start_u"],
            "end_u": p["end_u"],
            "height_u": p["height_u"],
            "mount_side": p["mount_side"],
            "version": p.get("version", 1),
        })

    return {"rack": _rack_summary(rack, placements), "placements": items}


# ── 검색 ────────────────────────────────────────────────────────────────────

async def search_assets(q: str) -> List[dict]:
    q = (q or "").strip()
    if not q:
        return []
    rx = {"$regex": re.escape(q), "$options": "i"}
    query = {"is_deleted": {"$ne": True}, "$or": [
        {"asset_id": rx}, {"asset_no": rx}, {"name": rx},
        {"ip": rx}, {"fields.hostname": rx},
    ]}

    results: List[dict] = []
    rack_cache: Dict[str, dict] = {}
    for category in _SEARCH_CATEGORIES:
        col = MongoClientManager.get_asset_collection(category)
        async for a in col.find(query).limit(_SEARCH_LIMIT_PER_CAT):
            placement = await _placements_col().find_one({
                "asset_category": category, "asset_ref_id": a["_id"], "is_deleted": False,
            })
            placement_out = None
            if placement:
                rk_id = str(placement["rack_ref_id"])
                if rk_id not in rack_cache:
                    rack_cache[rk_id] = await _rack_col().find_one({"_id": placement["rack_ref_id"]}) or {}
                rk = rack_cache[rk_id]
                placement_out = {
                    "rack_id": rk_id,
                    "rack_name": rk.get("name"),
                    "server_room": (rk.get("fields") or {}).get("server_room"),
                    "start_u": placement["start_u"],
                    "end_u": placement["end_u"],
                }
            results.append({
                "asset_category": category,
                "asset_id": str(a["_id"]),
                "asset_code": a.get("asset_id"),
                "asset_no": a.get("asset_no"),
                "name": a.get("name", ""),
                "ip": a.get("ip"),
                "placement": placement_out,
            })
    return results


# ── 미배치 자산 ──────────────────────────────────────────────────────────────

_PLACEABLE_CATEGORIES = ["서버", "네트워크", "정보보호시스템"]


async def list_unplaced_assets(category: Optional[str] = None) -> List[dict]:
    """활성 배치가 없는 자산 목록. category 미지정 시 랙 U 배치 가능 카테고리 전체."""
    categories = [category] if category else _PLACEABLE_CATEGORIES
    out: List[dict] = []
    for cat in categories:
        placed = await _placements_col().distinct("asset_ref_id", {
            "asset_category": cat, "is_deleted": False,
        })
        col = MongoClientManager.get_asset_collection(cat)
        async for a in col.find({"_id": {"$nin": placed}, "is_deleted": {"$ne": True}}).sort("name", 1):
            out.append({
                "asset_category": cat,
                "asset_id": str(a["_id"]),
                "asset_code": a.get("asset_id"),
                "asset_no": a.get("asset_no"),
                "name": a.get("name", ""),
                "ip": a.get("ip"),
            })
    return out


# ── 배치 이력 ────────────────────────────────────────────────────────────────

async def get_rack_history(rack_id: str) -> List[dict]:
    rack_oid = oid(rack_id, "잘못된 랙 ID입니다.")
    hist = MongoClientManager.get_rack_placements_history_collection()
    docs = await hist.find({"$or": [
        {"rack_ref_id": rack_oid},
        {"before.rack_ref_id": str(rack_oid)},
        {"after.rack_ref_id": str(rack_oid)},
    ]}).sort("changed_at", -1).limit(200).to_list(None)

    rack_names: Dict[str, str] = {}

    async def _rack_name(rid: Optional[str]) -> Optional[str]:
        if not rid:
            return None
        if rid not in rack_names:
            try:
                rk = await _rack_col().find_one({"_id": ObjectId(rid)}, {"name": 1})
            except Exception:
                rk = None
            rack_names[rid] = (rk or {}).get("name", rid)
        return rack_names[rid]

    async def _pos(snap: Optional[dict]) -> Optional[dict]:
        if not snap:
            return None
        return {
            "rack_id": snap.get("rack_ref_id"),
            "rack_name": await _rack_name(snap.get("rack_ref_id")),
            "start_u": snap.get("start_u"),
            "end_u": snap.get("end_u"),
            "mount_side": snap.get("mount_side"),
        }

    out: List[dict] = []
    for d in docs:
        asset = None
        if d.get("asset_category") and d.get("asset_ref_id"):
            asset = await _get_asset_any(d["asset_category"], d["asset_ref_id"])
        out.append({
            "id": str(d["_id"]),
            "action": d.get("action", ""),
            "asset_category": d.get("asset_category"),
            "asset_id": str(d["asset_ref_id"]) if d.get("asset_ref_id") else None,
            "asset_name": (asset or {}).get("name") if asset else None,
            "before": await _pos(d.get("before")),
            "after": await _pos(d.get("after")),
            "changed_at": d.get("changed_at"),
            "changed_by": d.get("changed_by"),
        })
    return out


async def _get_asset_any(category: str, asset_ref_id: ObjectId) -> Optional[dict]:
    """삭제 여부와 무관하게 조회(이력 표시용)."""
    if category not in MongoClientManager.CATEGORY_COLLECTIONS:
        return None
    return await MongoClientManager.get_asset_collection(category).find_one({"_id": asset_ref_id})


# ── 정합성 점검 ──────────────────────────────────────────────────────────────

async def integrity_check() -> dict:
    from datetime import datetime, timezone

    from app.services.rack_placement_service import build_occupied_slots

    issues: List[dict] = []
    active = await _placements_col().find({"is_deleted": False}).to_list(None)
    for p in active:
        pid = str(p["_id"])
        asset = await _get_asset_any(p["asset_category"], p["asset_ref_id"])
        if not asset:
            issues.append({"type": "ORPHAN_ASSET_REFERENCE", "placement_id": pid,
                           "asset_category": p["asset_category"], "asset_id": str(p["asset_ref_id"]),
                           "detail": "배치가 가리키는 자산이 없습니다."})
        elif asset.get("is_deleted"):
            issues.append({"type": "DELETED_ASSET_STILL_PLACED", "placement_id": pid,
                           "asset_category": p["asset_category"], "asset_id": str(p["asset_ref_id"]),
                           "detail": "삭제된 자산이 배치되어 있습니다."})

        rack = await _rack_col().find_one({"_id": p["rack_ref_id"]})
        if not rack:
            issues.append({"type": "ORPHAN_RACK_REFERENCE", "placement_id": pid,
                           "detail": "배치가 가리키는 랙이 없습니다."})
        else:
            if rack.get("is_deleted"):
                issues.append({"type": "DELETED_RACK_STILL_USED", "placement_id": pid,
                               "detail": "삭제된 랙에 자산이 배치되어 있습니다."})
            try:
                total_u = int((rack.get("fields") or {}).get("total_u"))
                if p["end_u"] > total_u:
                    issues.append({"type": "OUT_OF_RANGE", "placement_id": pid,
                                   "detail": f"U{p['start_u']}~U{p['end_u']} 가 랙 {total_u}U 를 초과합니다."})
            except (TypeError, ValueError):
                pass

        expected = build_occupied_slots(p["start_u"], p["height_u"], p["mount_side"])
        if sorted(expected) != sorted(p.get("occupied_slots", [])):
            issues.append({"type": "SLOT_MISMATCH", "placement_id": pid,
                           "detail": "occupied_slots 가 start_u/height/side 와 일치하지 않습니다."})

    return {
        "checked_at": datetime.now(timezone.utc),
        "status": "WARNING" if issues else "OK",
        "issue_count": len(issues),
        "issues": issues,
    }


# ── 레거시 fields.rack_no/rack_unit_no → rack_placements 마이그레이션 ──────────

def _parse_unit(raw: str) -> Tuple[Optional[int], int]:
    """rack_unit_no 문자열에서 시작 U·높이를 추출. 파싱 불가 시 (None, 1)."""
    nums = re.findall(r"\d+", raw or "")
    if not nums:
        return None, 1
    start = int(nums[0])
    if len(nums) >= 2:
        end = int(nums[1])
        return start, max(end - start + 1, 1)
    return start, 1


async def _ensure_rack(rack_code: str, dry_run: bool, actor: str, created_codes: Set[str]) -> Optional[dict]:
    """rack_code 에 해당하는 랙 자산을 찾거나(없으면) 42U 로 생성."""
    rack = await _rack_col().find_one({
        "is_deleted": {"$ne": True},
        "$or": [{"asset_id": rack_code}, {"name": rack_code}],
    })
    if rack:
        return rack
    created_codes.add(rack_code)
    if dry_run:
        return None
    now = datetime.now(timezone.utc)
    doc = {
        "ip": "", "name": rack_code, "asset_id": rack_code,
        "fields": {"server_room": "", "total_u": 42, "status": "ACTIVE", "u_direction": "BOTTOM_UP"},
        "created_at": now, "created_by": actor, "updated_at": now, "updated_by": actor,
        "version": 1, "is_deleted": False,
    }
    res = await _rack_col().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def migrate_from_fields(dry_run: bool, actor: str) -> dict:
    """서버 등 자산의 레거시 fields.rack_no/rack_unit_no 를 랙 자산 + 배치로 이관한다.

    - rack_no 별로 assets_racks 를 42U 로 자동 생성(없을 때)
    - rack_unit_no 파싱 가능(U 있음) + 미배치 자산만 rack_placements 생성
    - rack_unit_no 비어있으면 위치를 지어내지 않고 건너뜀(집계만)
    멱등: 이미 배치된 자산은 건너뛴다. dry_run=True 면 아무것도 쓰지 않고 예상치만 반환.
    """
    from app.services import rack_placement_service as pls

    created_codes: Set[str] = set()
    placements_created = 0
    skipped_no_unit = 0
    skipped_already = 0
    skipped_conflict = 0

    for cat in _PLACEABLE_CATEGORIES:
        col = MongoClientManager.get_asset_collection(cat)
        cursor = col.find({"is_deleted": {"$ne": True}, "fields.rack_no": {"$nin": [None, ""]}})
        async for a in cursor:
            rack_code = str((a.get("fields") or {}).get("rack_no", "")).strip()
            if not rack_code:
                continue
            rack = await _ensure_rack(rack_code, dry_run, actor, created_codes)

            start_u, height_u = _parse_unit(str((a.get("fields") or {}).get("rack_unit_no", "")))
            if start_u is None:
                skipped_no_unit += 1
                continue
            if await _placements_col().find_one({"asset_category": cat, "asset_ref_id": a["_id"]}):
                skipped_already += 1
                continue
            if dry_run or rack is None:
                placements_created += 1  # 예상치 (실제 겹침은 실행 시 판정)
                continue
            try:
                await pls.create_placement({
                    "asset_category": cat, "asset_id": str(a["_id"]),
                    "rack_id": str(rack["_id"]), "start_u": start_u,
                    "height_u": height_u, "mount_side": "FULL",
                }, actor)
                placements_created += 1
            except HTTPException:
                skipped_conflict += 1

    return {
        "dry_run": dry_run,
        "racks_to_create" if dry_run else "racks_created": sorted(created_codes),
        "placements_created": placements_created,
        "skipped_no_unit": skipped_no_unit,
        "skipped_already_placed": skipped_already,
        "skipped_conflict": skipped_conflict,
    }
