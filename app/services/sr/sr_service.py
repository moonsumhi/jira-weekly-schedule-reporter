"""SR 비즈니스 로직: 번호 생성, 이력 기록, 지연 판단, 권한 검사."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic

# ── SR 역할 상수 ──────────────────────────────────────────────────────

SR_PERM_REQUESTER = "sr_requester"
SR_PERM_OPERATOR  = "sr_operator"
SR_PERM_MANAGER   = "sr_manager"

# ── 상태 전이 허용 규칙 (역할 → 허용 전이 집합) ─────────────────────────
# 각 값은 (from_statuses, to_status) 형태 대신
# 역할별 허용 target 상태만 관리한다.
# 세밀한 from→to 검증은 router에서 수행.

REQUESTER_ALLOWED_TARGETS = {"SUBMITTED", "CANCELLED"}
OPERATOR_ALLOWED_TARGETS  = {"SUBMITTED", "REVIEWING", "PENDING_INFO", "IN_PROGRESS", "COMPLETED", "CONFIRMING"}
MANAGER_ALLOWED_TARGETS   = {"SUBMITTED", "REVIEWING", "APPROVED", "REJECTED", "ON_HOLD", "PENDING_INFO", "ASSIGNED", "CONFIRMING", "CLOSED"}
ADMIN_ALLOWED_TARGETS     = None  # 모든 상태


# ── 권한 헬퍼 ─────────────────────────────────────────────────────────

def is_sr_admin(user: UserPublic) -> bool:
    return user.is_admin


def is_sr_manager(user: UserPublic) -> bool:
    return user.is_admin or SR_PERM_MANAGER in (user.permissions or [])


def is_sr_operator(user: UserPublic) -> bool:
    return (
        user.is_admin
        or SR_PERM_MANAGER in (user.permissions or [])
        or SR_PERM_OPERATOR in (user.permissions or [])
    )


def is_sr_requester(user: UserPublic) -> bool:
    return SR_PERM_REQUESTER in (user.permissions or []) or is_sr_operator(user)


def require_sr_operator(user: UserPublic):
    if not is_sr_operator(user):
        raise HTTPException(status_code=403, detail="SR 처리자 이상의 권한이 필요합니다.")


def require_sr_manager(user: UserPublic):
    if not is_sr_manager(user):
        raise HTTPException(status_code=403, detail="SR 관리자 이상의 권한이 필요합니다.")


def require_sr_admin(user: UserPublic):
    if not is_sr_admin(user):
        raise HTTPException(status_code=403, detail="시스템 관리자 권한이 필요합니다.")


# ── SR 번호 생성 ──────────────────────────────────────────────────────

async def next_sr_number(year: int) -> str:
    """SR-YYYY-XXXX 형식의 고유 번호 생성."""
    col = MongoClientManager.get_db()[MongoClientManager.SR_COUNTER]
    result = await col.find_one_and_update(
        {"_id": f"sr_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = result["seq"]
    return f"SR-{year}-{seq:04d}"


# ── SR 문서 조회 헬퍼 ─────────────────────────────────────────────────

async def get_sr_or_404(sr_id: str) -> dict:
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    try:
        oid = ObjectId(sr_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 SR ID입니다.")
    doc = await col.find_one({"_id": oid, "deleted_at": None})
    if not doc:
        raise HTTPException(status_code=404, detail="SR을 찾을 수 없습니다.")
    return doc


# ── 이력 기록 ─────────────────────────────────────────────────────────

async def record_sr_history(
    sr_id: str,
    action_type: str,
    before_value: Optional[str],
    after_value: Optional[str],
    changed_by: str,
):
    col = MongoClientManager.get_db()[MongoClientManager.SR_HISTORIES]
    await col.insert_one({
        "sr_id": sr_id,
        "action_type": action_type,
        "before_value": before_value,
        "after_value": after_value,
        "changed_by": changed_by,
        "changed_at": datetime.now(timezone.utc),
    })


async def record_status_history(
    sr_id: str,
    previous_status: str,
    new_status: str,
    reason: Optional[str],
    changed_by: str,
):
    col = MongoClientManager.get_db()[MongoClientManager.SR_STATUS_HISTORIES]
    await col.insert_one({
        "sr_id": sr_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "reason": reason,
        "changed_by": changed_by,
        "changed_at": datetime.now(timezone.utc),
    })


async def record_due_date_history(
    sr_id: str,
    previous_due_date: Optional[datetime],
    new_due_date: Optional[datetime],
    change_reason: Optional[str],
    changed_by: str,
):
    col = MongoClientManager.get_db()[MongoClientManager.SR_DUE_DATE_HISTORIES]
    await col.insert_one({
        "sr_id": sr_id,
        "previous_due_date": previous_due_date,
        "new_due_date": new_due_date,
        "change_reason": change_reason,
        "changed_by": changed_by,
        "changed_at": datetime.now(timezone.utc),
    })


# ── 지연 여부 계산 ────────────────────────────────────────────────────

def compute_is_delayed(doc: dict) -> bool:
    """처리 중인 SR이 처리 예정 완료일을 초과했는지 판단."""
    terminal = {"CLOSED", "CANCELLED", "REJECTED"}
    if doc.get("status") in terminal:
        return False
    now = datetime.now(timezone.utc)
    planned_due = doc.get("planned_due_date")
    desired_due = doc.get("desired_due_date")
    check_date = planned_due or desired_due
    if not check_date:
        return False
    if check_date.tzinfo is None:
        check_date = check_date.replace(tzinfo=timezone.utc)
    return now > check_date


# ── SR 문서 → 출력 변환 ───────────────────────────────────────────────

def sr_to_out(doc: dict, hide_internal: bool = False) -> dict:
    """MongoDB 문서를 API 출력 dict로 변환."""
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d["is_delayed"] = compute_is_delayed(doc)
    # ObjectId 필드 문자열 변환
    for field in ("requester_id", "assignee_id", "reviewer_id",
                  "related_project_id", "related_issue_id",
                  "converted_issue_id", "converted_task_id", "converted_project_id"):
        if d.get(field) and isinstance(d[field], ObjectId):
            d[field] = str(d[field])
    return d
