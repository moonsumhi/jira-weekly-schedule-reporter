"""요청자용 SR API: 접수, 내 목록, 상세, 수정, 취소, 댓글."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.sr.service_request import (
    SRCreate, SRPatch, SROut, SRListItem, SRComment, SRCommentOut, SRHistoryOut,
)
from app.routers.auth import get_current_user
from app.services.sr.sr_service import (
    next_sr_number, get_sr_or_404, record_sr_history,
    record_status_history, sr_to_out, is_sr_requester,
)

router = APIRouter()


def _user_label(user: UserPublic) -> str:
    return user.full_name or user.email


# ── SR 접수 ──────────────────────────────────────────────────────────

@router.post("", response_model=SROut, status_code=201)
async def create_sr(
    body: SRCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    if body.is_urgent and not body.urgent_reason:
        raise HTTPException(status_code=400, detail="긴급 요청은 긴급 사유를 입력해야 합니다.")

    now = datetime.now(timezone.utc)
    year = now.year
    sr_no = await next_sr_number(year)
    status = "SUBMITTED" if body.submit else "DRAFT"

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    doc = {
        "sr_no": sr_no,
        "title": body.title,
        "status": status,
        "request_type": body.request_type,
        "requester_id": ObjectId(current_user.id),
        "requester_name": body.requester_name,
        "requester_department": body.requester_department,
        "requester_email": body.requester_email,
        "related_system": body.related_system,
        "related_menu": body.related_menu,
        "related_url": body.related_url,
        "background": body.background,
        "description": body.description,
        "purpose": body.purpose,
        "desired_due_date": body.desired_due_date,
        "desired_deploy_date": body.desired_deploy_date,
        "is_urgent": body.is_urgent,
        "urgent_reason": body.urgent_reason,
        "impact_scope": body.impact_scope,
        "priority": body.priority,
        "impact_if_not_processed": body.impact_if_not_processed,
        "compliance_related": body.compliance_related,
        "completion_criteria": body.completion_criteria,
        "reviewer_name": body.reviewer_name,
        "note": body.note,
        "attachments": [a.model_dump() for a in body.attachments],
        "type_detail": body.type_detail,
        # 검토/처리 필드 초기값
        "review_result": None,
        "reviewer_id": None,
        "reviewer_user_name": None,
        "reviewed_at": None,
        "review_comment": None,
        "reject_reason": None,
        "hold_reason": None,
        "pending_info_content": None,
        "assignee_id": None,
        "assignee_name": None,
        "planned_start_date": None,
        "planned_due_date": None,
        "actual_completed_at": None,
        "process_result": None,
        "deployed": False,
        "deployed_at": None,
        "requester_confirmed": False,
        "related_project_id": None,
        "related_issue_id": None,
        "converted_issue_id": None,
        "converted_task_id": None,
        "estimated_effort": None,
        "deployment_required": False,
        "security_review_required": False,
        # 메타
        "created_at": now,
        "created_by": _user_label(current_user),
        "updated_at": now,
        "updated_by": _user_label(current_user),
        "deleted_at": None,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id

    await record_status_history(
        str(result.inserted_id), "", status, None, _user_label(current_user)
    )

    return SROut(**sr_to_out(doc))


# ── 내 SR 목록 ────────────────────────────────────────────────────────

@router.get("/my", response_model=List[SRListItem])
async def list_my_srs(
    status: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    related_system: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    desired_due_date_from: Optional[str] = Query(None),
    desired_due_date_to: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    q: dict = {
        "requester_id": ObjectId(current_user.id),
        "deleted_at": None,
    }
    if status:
        q["status"] = status
    if request_type:
        q["request_type"] = request_type
    if related_system:
        q["related_system"] = {"$regex": related_system, "$options": "i"}
    if priority:
        q["priority"] = priority
    if desired_due_date_from or desired_due_date_to:
        dfilter: dict = {}
        if desired_due_date_from:
            dfilter["$gte"] = datetime.fromisoformat(desired_due_date_from)
        if desired_due_date_to:
            dfilter["$lte"] = datetime.fromisoformat(desired_due_date_to)
        q["desired_due_date"] = dfilter

    docs = await col.find(q).sort("created_at", -1).to_list(None)
    return [SRListItem(**sr_to_out(d)) for d in docs]


# ── SR 상세 ───────────────────────────────────────────────────────────

@router.get("/{sr_id}", response_model=SROut)
async def get_sr(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await get_sr_or_404(sr_id)
    # 요청자는 본인 SR만 열람 가능 (관리자/처리자는 예외)
    if (
        not current_user.is_admin
        and "sr_operator" not in (current_user.permissions or [])
        and "sr_manager" not in (current_user.permissions or [])
        and str(doc["requester_id"]) != current_user.id
    ):
        raise HTTPException(status_code=403, detail="본인의 SR만 조회할 수 있습니다.")
    return SROut(**sr_to_out(doc))


# ── SR 수정 (접수 전 또는 추가 확인 요청 상태) ─────────────────────────

@router.put("/{sr_id}", response_model=SROut)
async def update_sr(
    sr_id: str,
    body: SRPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await get_sr_or_404(sr_id)

    # 본인 SR 확인
    if str(doc["requester_id"]) != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="본인의 SR만 수정할 수 있습니다.")

    if body.is_urgent is True and not body.urgent_reason and not doc.get("urgent_reason"):
        raise HTTPException(status_code=400, detail="긴급 요청은 긴급 사유를 입력해야 합니다.")

    now = datetime.now(timezone.utc)
    updates: dict = {"updated_at": now, "updated_by": _user_label(current_user)}
    track_fields = (
        "title", "description", "background", "purpose",
        "desired_deploy_date",
        "priority", "impact_scope", "is_urgent", "urgent_reason",
        "related_system", "related_menu", "related_url",
        "completion_criteria", "note",
    )

    patch_data = body.model_dump(exclude_none=True)
    do_submit = patch_data.pop("submit", None)

    for field, value in patch_data.items():
        old_val = doc.get(field)
        updates[field] = value
        if field in track_fields and str(old_val) != str(value):
            await record_sr_history(sr_id, f"FIELD_CHANGE:{field}", str(old_val), str(value), _user_label(current_user))

    if do_submit:
        if doc["status"] == "DRAFT":
            updates["status"] = "SUBMITTED"
            await record_status_history(sr_id, "DRAFT", "SUBMITTED", None, _user_label(current_user))
        elif doc["status"] == "PENDING_INFO":
            updates["status"] = "SUBMITTED"
            await record_status_history(sr_id, "PENDING_INFO", "SUBMITTED", None, _user_label(current_user))

    # desired_due_date 변경은 sr_due_date_histories 에만 기록 (sr_histories 이중 기록 방지)
    if body.desired_due_date is not None and body.desired_due_date != doc.get("desired_due_date"):
        from app.services.sr.sr_service import record_due_date_history
        await record_due_date_history(sr_id, doc.get("desired_due_date"), body.desired_due_date, None, _user_label(current_user))

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── SR 취소 ───────────────────────────────────────────────────────────

@router.post("/{sr_id}/cancel", response_model=SROut)
async def cancel_sr(
    sr_id: str,
    reason: str = Query(..., description="취소 사유"),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await get_sr_or_404(sr_id)
    if str(doc["requester_id"]) != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="본인의 SR만 취소할 수 있습니다.")
    if doc["status"] in ("CLOSED", "CANCELLED"):
        raise HTTPException(status_code=400, detail="이미 종료된 SR입니다.")

    now = datetime.now(timezone.utc)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one(
        {"_id": ObjectId(sr_id)},
        {"$set": {"status": "CANCELLED", "updated_at": now, "updated_by": _user_label(current_user)}},
    )
    await record_status_history(sr_id, doc["status"], "CANCELLED", reason, _user_label(current_user))
    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── 댓글 ─────────────────────────────────────────────────────────────

@router.post("/{sr_id}/comments", response_model=SRCommentOut, status_code=201)
async def add_comment(
    sr_id: str,
    body: SRComment,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await get_sr_or_404(sr_id)

    # 요청자는 자신의 SR에만 댓글 가능, 내부 메모 불가
    is_internal_allowed = (
        current_user.is_admin
        or "sr_operator" in (current_user.permissions or [])
        or "sr_manager" in (current_user.permissions or [])
    )
    if body.is_internal and not is_internal_allowed:
        raise HTTPException(status_code=403, detail="내부 메모 작성 권한이 없습니다.")

    if (
        not is_internal_allowed
        and str(doc["requester_id"]) != current_user.id
    ):
        raise HTTPException(status_code=403, detail="댓글을 작성할 수 없습니다.")

    now = datetime.now(timezone.utc)
    col = MongoClientManager.get_db()[MongoClientManager.SR_COMMENTS]
    comment_doc = {
        "sr_id": sr_id,
        "writer_id": current_user.id,
        "writer_name": _user_label(current_user),
        "content": body.content,
        "is_internal": body.is_internal,
        "attachments": [a.model_dump() for a in body.attachments],
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    result = await col.insert_one(comment_doc)
    comment_doc["_id"] = result.inserted_id
    comment_doc["id"] = str(result.inserted_id)
    return SRCommentOut(**comment_doc)


@router.get("/{sr_id}/comments", response_model=List[SRCommentOut])
async def list_comments(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await get_sr_or_404(sr_id)

    is_internal_allowed = (
        current_user.is_admin
        or "sr_operator" in (current_user.permissions or [])
        or "sr_manager" in (current_user.permissions or [])
    )
    col = MongoClientManager.get_db()[MongoClientManager.SR_COMMENTS]
    q: dict = {"sr_id": sr_id, "deleted_at": None}
    if not is_internal_allowed:
        q["is_internal"] = False

    docs = await col.find(q).sort("created_at", 1).to_list(None)
    result = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        result.append(SRCommentOut(**d))
    return result


@router.get("/{sr_id}/history", response_model=List[SRHistoryOut])
async def list_history(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await get_sr_or_404(sr_id)
    db = MongoClientManager.get_db()

    status_col = db[MongoClientManager.SR_STATUS_HISTORIES]
    field_col  = db[MongoClientManager.SR_HISTORIES]

    result: List[SRHistoryOut] = []

    async for d in status_col.find({"sr_id": sr_id}):
        result.append(SRHistoryOut(
            id=str(d["_id"]),
            sr_id=sr_id,
            action_type="STATUS_CHANGE",
            before_value=d.get("previous_status"),
            after_value=d.get("new_status"),
            changed_by=d.get("changed_by", ""),
            changed_at=d["changed_at"],
        ))

    async for d in field_col.find({"sr_id": sr_id}):
        result.append(SRHistoryOut(
            id=str(d["_id"]),
            sr_id=sr_id,
            action_type=d.get("action_type", "FIELD_CHANGE"),
            before_value=d.get("before_value"),
            after_value=d.get("after_value"),
            changed_by=d.get("changed_by", ""),
            changed_at=d["changed_at"],
        ))

    result.sort(key=lambda x: x.changed_at)
    return result
