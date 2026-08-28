# app/services/rack_placement_service.py
"""랙 배치의 단일 원본(rack_placements) 관리.

원칙(설계 확정안):
- 자산·랙 참조는 불변인 Mongo _id 로 조인한다(사용자 편집 가능한 asset_id 아님).
- 자산 1개당 배치 문서 1건만 유지. 반출은 소프트삭제, 재배치는 기존 문서 재활성화.
- 이동은 같은 문서를 원자적으로 업데이트(version 낙관적 잠금).
- U 중복은 사전 조회로 친절한 메시지 + occupied_slots unique index 로 최종 차단.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoClientManager
from app.utils.mongo import oid

_PLACEABLE_MODE = "RACK_U"          # 랙 U 를 직접 점유하는 카테고리만 배치 가능
_RACK_BLOCKED_STATUS = {"폐기"}      # 이 상태의 랙에는 신규 배치 차단


def _col():
    return MongoClientManager.get_rack_placements_collection()


def _hist():
    return MongoClientManager.get_rack_placements_history_collection()


# ── 점유 슬롯 ────────────────────────────────────────────────────────────────

def build_occupied_slots(start_u: int, height_u: int, mount_side: str) -> List[str]:
    """점유 슬롯 문자열 목록을 생성한다. 예: FULL U18~19 → [F:18,R:18,F:19,R:19].

    전/후면을 슬롯에 인코딩하므로 FRONT 장비와 REAR 장비가 같은 U 를 공유해도
    충돌하지 않고, FULL 은 양면을 모두 차지한다.
    """
    units = range(start_u, start_u + height_u)
    if mount_side == "FULL":
        sides = ("F", "R")
    elif mount_side == "FRONT":
        sides = ("F",)
    elif mount_side == "REAR":
        sides = ("R",)
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 장착 방향: {mount_side}")
    return [f"{side}:{u}" for u in units for side in sides]


# ── 조회 헬퍼 ────────────────────────────────────────────────────────────────

async def _get_asset(category: str, asset_ref_id: ObjectId) -> Optional[dict]:
    if category not in MongoClientManager.CATEGORY_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 카테고리: {category}")
    col = MongoClientManager.get_asset_collection(category)
    return await col.find_one({"_id": asset_ref_id, "is_deleted": {"$ne": True}})


async def _get_rack(rack_ref_id: ObjectId) -> Optional[dict]:
    col = MongoClientManager.get_asset_collection("랙")
    return await col.find_one({"_id": rack_ref_id, "is_deleted": {"$ne": True}})


def _rack_total_u(rack: dict) -> int:
    try:
        return int((rack.get("fields") or {}).get("total_u"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="랙에 전체 U(total_u)가 설정되어 있지 않습니다.")


async def _find_conflicts(
    rack_ref_id: ObjectId, slots: List[str], exclude_id: Optional[ObjectId] = None,
) -> List[dict]:
    q: dict = {"rack_ref_id": rack_ref_id, "is_deleted": False, "occupied_slots": {"$in": slots}}
    if exclude_id is not None:
        q["_id"] = {"$ne": exclude_id}
    return await _col().find(q).to_list(None)


async def _conflict_summaries(docs: List[dict]) -> List[dict]:
    out: List[dict] = []
    for d in docs:
        asset = await _get_asset(d["asset_category"], d["asset_ref_id"])
        out.append({
            "asset_category": d["asset_category"],
            "asset_id": str(d["asset_ref_id"]),
            "name": (asset or {}).get("name") if asset else None,
            "start_u": d["start_u"],
            "end_u": d["end_u"],
        })
    return out


# ── 직렬화 ──────────────────────────────────────────────────────────────────

def to_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "asset_category": doc["asset_category"],
        "asset_id": str(doc["asset_ref_id"]),
        "rack_id": str(doc["rack_ref_id"]),
        "start_u": doc["start_u"],
        "height_u": doc["height_u"],
        "end_u": doc["end_u"],
        "mount_side": doc["mount_side"],
        "occupied_slots": doc.get("occupied_slots", []),
        "version": doc.get("version", 1),
        "is_deleted": doc.get("is_deleted", False),
        "created_at": doc.get("created_at"),
        "created_by": doc.get("created_by"),
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
    }


# ── 이력 ────────────────────────────────────────────────────────────────────

def _snapshot(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    return {
        "rack_ref_id": str(doc.get("rack_ref_id")),
        "start_u": doc.get("start_u"),
        "end_u": doc.get("end_u"),
        "mount_side": doc.get("mount_side"),
    }


async def _write_history(action: str, before: Optional[dict], after: Optional[dict], actor: str) -> None:
    ref = after or before or {}
    await _hist().insert_one({
        "entity_type": "rack_placement",
        "asset_category": ref.get("asset_category"),
        "asset_ref_id": ref.get("asset_ref_id"),
        "rack_ref_id": ref.get("rack_ref_id"),
        "action": action,
        "before": _snapshot(before),
        "after": _snapshot(after),
        "changed_at": datetime.now(timezone.utc),
        "changed_by": actor,
    })


# ── 검증 ────────────────────────────────────────────────────────────────────

async def _validate_target(
    category: str, rack_ref_id: ObjectId, start_u: int, height_u: int, mount_side: str,
    exclude_id: Optional[ObjectId] = None,
) -> Dict[str, Any]:
    """랙/자산 카테고리/범위/겹침을 검증하고 end_u·occupied_slots 를 계산해 반환."""
    mode = (MongoClientManager.ASSET_CATEGORY_CONFIG.get(category) or {}).get("placement_mode")
    if mode != _PLACEABLE_MODE:
        raise HTTPException(status_code=400, detail=f"'{category}' 카테고리는 랙 U 에 직접 배치할 수 없습니다.")

    rack = await _get_rack(rack_ref_id)
    if not rack:
        raise HTTPException(status_code=404, detail="랙을 찾을 수 없습니다.")
    if (rack.get("fields") or {}).get("status") in _RACK_BLOCKED_STATUS:
        raise HTTPException(status_code=400, detail="폐기된 랙에는 배치할 수 없습니다.")

    total_u = _rack_total_u(rack)
    end_u = start_u + height_u - 1
    if end_u > total_u:
        raise HTTPException(
            status_code=400,
            detail=f"랙 범위를 초과합니다. (U{start_u}~U{end_u}, 랙 전체 {total_u}U)",
        )

    slots = build_occupied_slots(start_u, height_u, mount_side)
    conflicts = await _find_conflicts(rack_ref_id, slots, exclude_id=exclude_id)
    if conflicts:
        raise HTTPException(status_code=409, detail={
            "code": "RACK_SLOT_OCCUPIED",
            "message": "선택한 U 중 일부가 이미 사용 중입니다.",
            "conflicts": await _conflict_summaries(conflicts),
        })
    return {"rack": rack, "end_u": end_u, "occupied_slots": slots}


# ── CRUD ────────────────────────────────────────────────────────────────────

# ── 자산 필드 미러 (placements → fields.rack_no/rack_unit_no) ─────────────────
# 실제 위치의 단일 원본은 rack_placements 이며, 기존 서버 폼/컬럼/Export 호환을 위해
# 배치 변경 시 자산의 rack_no·rack_unit_no 를 파생값으로 동기화한다(읽기전용 취급).

async def _mirror_to_asset(category: str, asset_ref_id: ObjectId, rack: dict, start_u: int, end_u: int) -> None:
    rack_code = (rack.get("asset_id") or rack.get("name") or "") if rack else ""
    unit = str(start_u) if start_u == end_u else f"{start_u}-{end_u}"
    await MongoClientManager.get_asset_collection(category).update_one(
        {"_id": asset_ref_id},
        {"$set": {"fields.rack_no": rack_code, "fields.rack_unit_no": unit}},
    )


async def _clear_asset_mirror(category: str, asset_ref_id: ObjectId) -> None:
    await MongoClientManager.get_asset_collection(category).update_one(
        {"_id": asset_ref_id},
        {"$set": {"fields.rack_no": "", "fields.rack_unit_no": ""}},
    )


async def get_active_placement(category: str, asset_ref_id: ObjectId) -> Optional[dict]:
    return await _col().find_one({
        "asset_category": category, "asset_ref_id": asset_ref_id, "is_deleted": False,
    })


async def create_placement(data: dict, actor: str) -> dict:
    category = data["asset_category"]
    asset_ref_id = oid(data["asset_id"], "잘못된 자산 ID입니다.")
    rack_ref_id = oid(data["rack_id"], "잘못된 랙 ID입니다.")
    start_u, height_u, mount_side = data["start_u"], data["height_u"], data["mount_side"]

    asset = await _get_asset(category, asset_ref_id)
    if not asset:
        raise HTTPException(status_code=404, detail="자산을 찾을 수 없습니다.")

    calc = await _validate_target(category, rack_ref_id, start_u, height_u, mount_side)
    now = datetime.now(timezone.utc)

    existing = await _col().find_one({"asset_category": category, "asset_ref_id": asset_ref_id})
    if existing and not existing.get("is_deleted", False):
        raise HTTPException(status_code=409, detail={
            "code": "ASSET_ALREADY_PLACED",
            "message": "이미 랙에 배치된 자산입니다. 위치 변경은 이동(PUT)을 사용하세요.",
        })

    set_fields = {
        "asset_category": category,
        "asset_ref_id": asset_ref_id,
        "rack_ref_id": rack_ref_id,
        "start_u": start_u,
        "height_u": height_u,
        "end_u": calc["end_u"],
        "mount_side": mount_side,
        "occupied_slots": calc["occupied_slots"],
        "is_deleted": False,
        "deleted_at": None,
        "deleted_by": None,
        "updated_at": now,
        "updated_by": actor,
    }
    try:
        if existing:  # 반출됐던 자산 재배치 → 기존 문서 재활성화
            doc = await _col().find_one_and_update(
                {"_id": existing["_id"]},
                {"$set": set_fields, "$inc": {"version": 1}},
                return_document=ReturnDocument.AFTER,
            )
        else:
            set_fields.update({"created_at": now, "created_by": actor, "version": 1})
            res = await _col().insert_one(set_fields)
            doc = await _col().find_one({"_id": res.inserted_id})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail={
            "code": "RACK_SLOT_OCCUPIED",
            "message": "선택한 U 가 방금 다른 사용자에 의해 선점되었습니다. 다시 시도해 주세요.",
        })

    await _mirror_to_asset(category, asset_ref_id, calc["rack"], start_u, calc["end_u"])
    await _write_history("PLACE", before=None, after=doc, actor=actor)
    return to_out(doc)


async def move_placement(placement_id: str, data: dict, actor: str) -> dict:
    pid = oid(placement_id, "잘못된 배치 ID입니다.")
    current = await _col().find_one({"_id": pid})
    if not current or current.get("is_deleted", False):
        raise HTTPException(status_code=404, detail="배치를 찾을 수 없습니다. (반출된 자산은 재배치를 사용하세요)")

    expected = data.get("expected_version")
    if expected is not None and expected != current.get("version"):
        raise HTTPException(status_code=409, detail={
            "code": "VERSION_CONFLICT",
            "message": "다른 사용자가 먼저 수정했습니다. 최신 배치도를 다시 불러오세요.",
        })

    rack_ref_id = oid(data["rack_id"], "잘못된 랙 ID입니다.")
    start_u, height_u, mount_side = data["start_u"], data["height_u"], data["mount_side"]
    calc = await _validate_target(
        current["asset_category"], rack_ref_id, start_u, height_u, mount_side, exclude_id=pid,
    )
    now = datetime.now(timezone.utc)
    try:
        doc = await _col().find_one_and_update(
            {"_id": pid, "version": current["version"], "is_deleted": False},
            {"$set": {
                "rack_ref_id": rack_ref_id,
                "start_u": start_u,
                "height_u": height_u,
                "end_u": calc["end_u"],
                "mount_side": mount_side,
                "occupied_slots": calc["occupied_slots"],
                "updated_at": now,
                "updated_by": actor,
            }, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail={
            "code": "RACK_SLOT_OCCUPIED",
            "message": "선택한 U 가 방금 다른 사용자에 의해 선점되었습니다. 다시 시도해 주세요.",
        })
    if not doc:  # version 필터 불일치 = 동시 수정
        raise HTTPException(status_code=409, detail={
            "code": "VERSION_CONFLICT",
            "message": "다른 사용자가 먼저 수정했습니다. 최신 배치도를 다시 불러오세요.",
        })

    await _mirror_to_asset(current["asset_category"], current["asset_ref_id"], calc["rack"], start_u, calc["end_u"])
    await _write_history("MOVE", before=current, after=doc, actor=actor)
    return to_out(doc)


async def remove_placement(placement_id: str, actor: str) -> dict:
    pid = oid(placement_id, "잘못된 배치 ID입니다.")
    current = await _col().find_one({"_id": pid})
    if not current:
        raise HTTPException(status_code=404, detail="배치를 찾을 수 없습니다.")
    if current.get("is_deleted", False):
        return to_out(current)

    now = datetime.now(timezone.utc)
    doc = await _col().find_one_and_update(
        {"_id": pid},
        {"$set": {"is_deleted": True, "deleted_at": now, "deleted_by": actor,
                  "updated_at": now, "updated_by": actor},
         "$inc": {"version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    await _clear_asset_mirror(current["asset_category"], current["asset_ref_id"])
    await _write_history("REMOVE", before=current, after=doc, actor=actor)
    return to_out(doc)
