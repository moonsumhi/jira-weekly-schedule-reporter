"""관리자/처리자용 SR API: 전체 목록, 검토, 배정, 상태 변경, Excel 다운로드, 통계."""
from __future__ import annotations

import io
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.sr.service_request import (
    SROut, SRListItem, SRListPage, SRPatch, SRInlinePatch, SRRequesterChange,
    SRReview, SRAssign, SRStatusChange, SRDueDateChange, SRProcessingPatch,
    SRStats, SR_STATUS_LABEL, REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL,
)
from app.routers.auth import get_current_user
from app.utils.time import KST
from app.services.sr.sr_service import (
    get_sr_or_404, record_sr_history, record_status_history,
    record_due_date_history, sr_to_out, require_sr_operator,
    require_sr_manager, require_sr_admin, compute_is_delayed,
    is_sr_operator,
)
from app.services.notification_service import create_notification, notify_users
from app.services.sr.excel_export import export_detail, stream_export

router = APIRouter()


def _user_label(user: UserPublic) -> str:
    return user.full_name or user.email


async def _attach_comment_counts(items: list[dict]) -> None:
    """목록에 실린 SR들의 댓글 개수를 한 번의 집계로 채워넣는다 (N+1 방지)."""
    sr_ids = [i["id"] for i in items]
    if not sr_ids:
        return
    comments_col = MongoClientManager.get_db()[MongoClientManager.SR_COMMENTS]
    pipeline = [
        {"$match": {"sr_id": {"$in": sr_ids}, "deleted_at": None}},
        {"$group": {"_id": "$sr_id", "count": {"$sum": 1}}},
    ]
    counts = {row["_id"]: row["count"] async for row in comments_col.aggregate(pipeline)}
    for i in items:
        i["comment_count"] = counts.get(i["id"], 0)


# ── 전체 SR 목록 ──────────────────────────────────────────────────────

@router.get("", response_model=SRListPage)
async def list_all_srs(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    requester_department: Optional[str] = Query(None),
    requester_name: Optional[str] = Query(None),
    related_system: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_urgent: Optional[bool] = Query(None),
    is_delayed: Optional[bool] = Query(None),
    my_assigned: Optional[bool] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    desired_due_from: Optional[str] = Query(None),
    desired_due_to: Optional[str] = Query(None),
    planned_due_from: Optional[str] = Query(None),
    planned_due_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None),
    descending: bool = Query(True),
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_operator(current_user)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]

    _SORT_FIELDS = {
        "created_at", "updated_at",
        "desired_due_date", "planned_due_date",
        "sr_no", "title", "assignee_name",
        "requester_name", "requester_department", "priority", "status",
    }
    sort_field = sort_by if sort_by in _SORT_FIELDS else "created_at"
    sort_dir   = -1 if descending else 1

    q: dict = {"deleted_at": None}
    # 자신에게 배정된 SR만 보기 (operator 전용 필터)
    if my_assigned:
        q["assignee_id"] = ObjectId(current_user.id)
    if status:
        # 쉼표 구분 복수 상태 지원: "SUBMITTED,REVIEWING" 또는 "!COMPLETED,!CLOSED"
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        includes = [s for s in statuses if not s.startswith("!")]
        excludes = [s[1:] for s in statuses if s.startswith("!")]
        if includes:
            q["status"] = {"$in": includes}
        elif excludes:
            q["status"] = {"$nin": ["DRAFT"] + excludes}
        else:
            q["status"] = {"$ne": "DRAFT"}
    else:
        # 특정 status 필터 없이 전체 조회 시 임시저장(DRAFT) 제외
        q["status"] = {"$ne": "DRAFT"}
    if search:
        keyword = search.strip()
        pattern = re.escape(keyword)
        or_conditions: list[dict] = [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"sr_no": {"$regex": pattern, "$options": "i"}},
            {"requester_name": {"$regex": pattern, "$options": "i"}},
        ]
        # 목록 화면은 제목 앞에 "[유형 라벨]"을 붙여서 보여주므로(title 필드 자체엔 없음),
        # 검색어가 유형 라벨(예: "오류 수정 요청")과 매칭되면 해당 request_type도 함께 찾는다.
        matching_types = [
            code for code, label in REQUEST_TYPE_LABEL.items()
            if keyword.lower() in label.lower()
        ]
        if matching_types:
            or_conditions.append({"request_type": {"$in": matching_types}})
        q["$or"] = or_conditions
    if request_type:
        q["request_type"] = request_type
    if requester_department:
        q["requester_department"] = {"$regex": requester_department, "$options": "i"}
    if requester_name:
        q["requester_name"] = {"$regex": requester_name, "$options": "i"}
    if related_system:
        q["related_system"] = {"$regex": related_system, "$options": "i"}
    if assignee_id:
        q["assignee_id"] = ObjectId(assignee_id)
    if priority:
        q["priority"] = priority
    if is_urgent is not None:
        q["is_urgent"] = is_urgent

    def _dt(s: str) -> datetime:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

    # 접수일(created_at)은 UTC 타임스탬프이고 사용자는 KST 날짜로 고른다.
    # KST 기준 시작일 0시 ~ 종료일 다음날 0시 미만(종료일 당일 포함)을 UTC로 변환해 비교한다.
    if created_from or created_to:
        cf: dict = {}
        if created_from:
            cf["$gte"] = KST.localize(datetime.fromisoformat(created_from)).astimezone(timezone.utc)
        if created_to:
            end_kst = KST.localize(datetime.fromisoformat(created_to)) + timedelta(days=1)
            cf["$lt"] = end_kst.astimezone(timezone.utc)
        q["created_at"] = cf

    if desired_due_from or desired_due_to:
        df: dict = {}
        if desired_due_from:
            df["$gte"] = _dt(desired_due_from)
        if desired_due_to:
            df["$lte"] = _dt(desired_due_to)
        q["desired_due_date"] = df

    if planned_due_from or planned_due_to:
        pf: dict = {}
        if planned_due_from:
            pf["$gte"] = _dt(planned_due_from)
        if planned_due_to:
            pf["$lte"] = _dt(planned_due_to)
        q["planned_due_date"] = pf

    # is_delayed 필터는 Python 연산이므로 페이지네이션 전에 전체 조회 후 필터링
    if is_delayed is not None:
        all_docs = await col.find(q).sort(sort_field, sort_dir).to_list(None)
        outs = [sr_to_out(d) for d in all_docs]
        outs = [o for o in outs if o["is_delayed"] == is_delayed]
        page = outs[skip: skip + limit]
        await _attach_comment_counts(page)
        return SRListPage(items=[SRListItem(**o) for o in page], total=len(outs))

    total = await col.count_documents(q)
    docs = await col.find(q).sort(sort_field, sort_dir).skip(skip).limit(limit).to_list(None)
    outs = [sr_to_out(d) for d in docs]
    await _attach_comment_counts(outs)
    return SRListPage(items=[SRListItem(**o) for o in outs], total=total)


# ── 인라인 필드 수정 (manager 이상) ─────────────────────────────────────

@router.patch("/{sr_id}", response_model=SROut)
async def patch_sr_inline(
    sr_id: str,
    body: SRInlinePatch,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    doc = await get_sr_or_404(sr_id)
    now = datetime.now(timezone.utc)
    updates: dict = {"updated_at": now, "updated_by": _user_label(current_user)}

    # Keep explicitly supplied null values so inline edits can clear fields.
    patch = body.model_dump(exclude_unset=True)
    for field, value in patch.items():
        old_val = doc.get(field)
        db_value = ObjectId(value) if field == "assignee_id" and value else value
        updates[field] = db_value
        if field == "desired_due_date":
            if old_val != db_value:
                await record_due_date_history(
                    sr_id, old_val, db_value, None, _user_label(current_user),
                )
        elif str(old_val or "") != str(db_value or ""):
            await record_sr_history(
                sr_id, f"FIELD_CHANGE:{field}",
                str(old_val or ""), str(db_value or ""), _user_label(current_user),
            )

    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── 요청자 변경 (시스템 관리자) ────────────────────────────────────────

@router.patch("/{sr_id}/requester", response_model=SROut)
async def change_sr_requester(
    sr_id: str,
    body: SRRequesterChange,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_admin(current_user)
    doc = await get_sr_or_404(sr_id)

    try:
        requester_oid = ObjectId(body.requester_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 요청자 ID입니다.")

    users_col = MongoClientManager.get_users_collection()
    requester = await users_col.find_one({
        "_id": requester_oid,
        "is_blocked": {"$ne": True},
    })
    if not requester:
        raise HTTPException(status_code=404, detail="변경할 요청자를 찾을 수 없습니다.")

    if doc.get("requester_id") == requester_oid:
        return SROut(**sr_to_out(doc))

    requester_name = requester.get("full_name") or requester.get("email", "")
    requester_department = requester.get("team") or ""
    requester_email = requester.get("email", "")
    now = datetime.now(timezone.utc)
    actor = _user_label(current_user)

    updates = {
        "requester_id": requester_oid,
        "requester_name": requester_name,
        "requester_department": requester_department,
        "requester_email": requester_email,
        "updated_at": now,
        "updated_by": actor,
    }
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    result = await col.update_one(
        {"_id": ObjectId(sr_id), "requester_id": doc.get("requester_id")},
        {"$set": updates},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=409, detail="요청자가 이미 변경되었습니다. 새로고침 후 다시 시도해주세요.")

    history_fields = (
        ("requester_id", doc.get("requester_id"), requester_oid),
        ("requester_name", doc.get("requester_name"), requester_name),
        ("requester_department", doc.get("requester_department"), requester_department),
        ("requester_email", doc.get("requester_email"), requester_email),
    )
    for field, before, after in history_fields:
        if str(before or "") != str(after or ""):
            await record_sr_history(
                sr_id,
                f"FIELD_CHANGE:{field}",
                str(before or ""),
                str(after or ""),
                actor,
            )

    await create_notification(
        recipient_user_id=str(requester_oid),
        notification_type="REQUESTER_CHANGED",
        title="SR 요청자 지정",
        message=f"'{doc.get('title', '')}' SR의 요청자로 지정되었습니다.",
        sender_user_id=str(current_user.id),
        sender_name=actor,
        target_type="SR",
        target_id=sr_id,
        target_url=f"/pm/sr/{sr_id}",
    )

    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── SR 수정 (관리자) ──────────────────────────────────────────────────

@router.put("/{sr_id}", response_model=SROut)
async def update_sr_admin(
    sr_id: str,
    body: SRPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_admin(current_user)
    doc = await get_sr_or_404(sr_id)
    now = datetime.now(timezone.utc)
    updates: dict = {"updated_at": now, "updated_by": _user_label(current_user)}
    # Keep explicitly supplied null values so optional fields can be cleared.
    patch_data = body.model_dump(exclude_unset=True)
    patch_data.pop("submit", None)
    for field, value in patch_data.items():
        old_val = doc.get(field)
        updates[field] = value
        if old_val != value:
            await record_sr_history(sr_id, f"FIELD_CHANGE:{field}", str(old_val), str(value), _user_label(current_user))

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── SR 검토 ───────────────────────────────────────────────────────────

@router.post("/{sr_id}/review", response_model=SROut)
async def review_sr(
    sr_id: str,
    body: SRReview,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    doc = await get_sr_or_404(sr_id)

    if doc["status"] not in ("SUBMITTED", "REVIEWING", "PENDING_INFO"):
        raise HTTPException(status_code=400, detail="검토 가능한 상태가 아닙니다.")

    if body.result == "REJECTED" and not body.reject_reason:
        raise HTTPException(status_code=400, detail="반려 사유를 입력해야 합니다.")
    if body.result == "ON_HOLD" and not body.hold_reason:
        raise HTTPException(status_code=400, detail="보류 사유를 입력해야 합니다.")
    if body.result == "PENDING_INFO" and not body.pending_info_content:
        raise HTTPException(status_code=400, detail="추가 확인 요청 내용을 입력해야 합니다.")

    status_map = {
        "APPROVED": "APPROVED",
        "REJECTED": "REJECTED",
        "ON_HOLD": "ON_HOLD",
        "PENDING_INFO": "PENDING_INFO",
    }
    new_status = status_map[body.result]
    now = datetime.now(timezone.utc)

    updates: dict = {
        "status": new_status,
        "review_result": body.result,
        "reviewer_id": ObjectId(current_user.id),
        "reviewer_user_name": _user_label(current_user),
        "reviewed_at": now,
        "review_comment": body.comment,
        "reject_reason": body.reject_reason,
        "hold_reason": body.hold_reason,
        "pending_info_content": body.pending_info_content,
        "updated_at": now,
        "updated_by": _user_label(current_user),
    }
    if body.related_project_id:
        updates["related_project_id"] = ObjectId(body.related_project_id)
    if body.related_issue_id:
        updates["related_issue_id"] = ObjectId(body.related_issue_id)

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    await record_status_history(sr_id, doc["status"], new_status, body.comment, _user_label(current_user))

    updated = await col.find_one({"_id": ObjectId(sr_id)})

    _STATUS_KO = {
        "APPROVED": "승인", "REJECTED": "반려", "ON_HOLD": "보류",
        "PENDING_INFO": "추가 확인 요청",
    }
    requester_id = str(doc["requester_id"])
    sender = _user_label(current_user)
    status_ko = _STATUS_KO.get(new_status, new_status)
    await create_notification(
        recipient_user_id=requester_id,
        notification_type="STATUS_CHANGED",
        title=f"SR 검토 완료: {status_ko}",
        message=f"'{doc.get('title', '')}' SR이 {status_ko} 처리되었습니다.",
        sender_user_id=str(current_user.id),
        sender_name=sender,
        target_type="SR",
        target_id=sr_id,
        target_url=f"/pm/sr/{sr_id}",
    )

    return SROut(**sr_to_out(updated))


async def _notify_assignment(doc: dict, sr_id: str, current_user: UserPublic):
    sender = _user_label(current_user)
    target_url = f"/pm/sr/{sr_id}"
    requester_id = str(doc["requester_id"])
    # 요청자에게 담당자 배정 알림
    await create_notification(
        recipient_user_id=requester_id,
        notification_type="STATUS_CHANGED",
        title="SR 담당자 배정",
        message=f"'{doc.get('title', '')}' SR이 {doc.get('assignee_name', '')}님에게 배정되었습니다.",
        sender_user_id=str(current_user.id),
        sender_name=sender,
        target_type="SR",
        target_id=sr_id,
        target_url=target_url,
    )
    # 담당자에게 배정 알림 (자신이 배정자인 경우 제외)
    if str(doc["assignee_id"]) != str(current_user.id):
        await create_notification(
            recipient_user_id=str(doc["assignee_id"]),
            notification_type="ASSIGNED",
            title="SR 담당 배정",
            message=f"'{doc.get('title', '')}' SR의 담당자로 배정되었습니다.",
            sender_user_id=str(current_user.id),
            sender_name=sender,
            target_type="SR",
            target_id=sr_id,
            target_url=target_url,
        )

    from app.utils.mail_notify import send_sr_notification
    await send_sr_notification(doc, event="assigned")


# ── 배정 후 처리 정보 수정 ──────────────────────────────────────────

@router.patch("/{sr_id}/processing", response_model=SROut)
async def update_processing_info(
    sr_id: str,
    body: SRProcessingPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    doc = await get_sr_or_404(sr_id)
    if not doc.get("assignee_id") or doc["status"] in ("DRAFT", "CLOSED", "CANCELLED", "REJECTED"):
        raise HTTPException(400, "처리 정보를 수정할 수 있는 상태가 아닙니다.")

    def utc(value):
        return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value

    if utc(doc.get("updated_at")) != utc(body.expected_updated_at):
        raise HTTPException(409, "다른 사용자가 SR을 수정했습니다. 새로고침 후 다시 수정해 주세요.")
    updates = body.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
    start = updates.get("planned_start_date", doc.get("planned_start_date"))
    due = updates.get("planned_due_date", doc.get("planned_due_date"))
    if start and due and utc(start).astimezone(KST).date() > utc(due).astimezone(KST).date():
        raise HTTPException(422, "완료목표일은 처리 예정 시작일보다 빠를 수 없습니다.")
    if "assignee_id" in updates:
        updates["assignee_id"] = ObjectId(updates["assignee_id"])
        if str(updates["assignee_id"]) != str(doc["assignee_id"]):
            user = await MongoClientManager.get_users_collection().find_one({"_id": updates["assignee_id"]})
            if not user:
                raise HTTPException(422, "선택한 담당자가 존재하지 않습니다. 다시 선택해 주세요.")
            updates["assignee_name"] = user.get("full_name") or user["email"]

    def comparable(value):
        return utc(value) if isinstance(value, datetime) else str(value) if isinstance(value, ObjectId) else value

    changes = {key: value for key, value in updates.items() if comparable(doc.get(key)) != comparable(value)}
    if not changes:
        return SROut(**sr_to_out(doc))
    actor = _user_label(current_user)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    result = await col.update_one(
        {"_id": doc["_id"], "updated_at": doc.get("updated_at"), "status": doc["status"], "deleted_at": None},
        {"$set": {**changes, "updated_at": datetime.now(timezone.utc), "updated_by": actor}},
    )
    if result.matched_count != 1:
        raise HTTPException(409, "다른 사용자가 SR을 수정했습니다. 새로고침 후 다시 수정해 주세요.")

    def history_value(value):
        if isinstance(value, bool):
            return "필요" if value else "해당 없음"
        if isinstance(value, datetime):
            return utc(value).astimezone(KST).strftime("%Y-%m-%d")
        return str(value) if value is not None else None

    for key, value in changes.items():
        if key == "assignee_id":
            await record_sr_history(sr_id, "ASSIGNEE_CHANGE", doc.get("assignee_name"), updates["assignee_name"], actor)
        elif key != "assignee_name":
            await record_sr_history(sr_id, f"FIELD_CHANGE:{key}", history_value(doc.get(key)), history_value(value), actor)
    if "planned_due_date" in changes:
        await record_due_date_history(sr_id, doc.get("planned_due_date"), changes["planned_due_date"], None, actor)
    if "assignee_id" in changes and doc.get("converted_issue_id"):
        from app.services.sr.sr_issue_bridge import update_pm_issue_assignee
        await update_pm_issue_assignee(doc["converted_issue_id"], str(changes["assignee_id"]))
    updated = await col.find_one({"_id": doc["_id"]})
    if "assignee_id" in changes:
        await _notify_assignment(updated, sr_id, current_user)
    return SROut(**sr_to_out(updated))


# ── 담당자 배정 ───────────────────────────────────────────────────────

@router.post("/{sr_id}/assign", response_model=SROut)
async def assign_sr(
    sr_id: str,
    body: SRAssign,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    doc = await get_sr_or_404(sr_id)

    if doc["status"] not in ("APPROVED", "ASSIGNED", "IN_PROGRESS"):
        raise HTTPException(status_code=400, detail="승인된 SR에만 담당자를 배정할 수 있습니다.")

    now = datetime.now(timezone.utc)
    old_assignee = doc.get("assignee_name")

    updates: dict = {
        "status": "IN_PROGRESS",
        "assignee_id": ObjectId(body.assignee_id),
        "assignee_name": body.assignee_name,
        "deployment_required": body.deployment_required,
        "security_review_required": body.security_review_required,
        "updated_at": now,
        "updated_by": _user_label(current_user),
    }
    if body.planned_start_date:
        updates["planned_start_date"] = body.planned_start_date
    if body.planned_due_date:
        updates["planned_due_date"] = body.planned_due_date
        if body.planned_due_date != doc.get("planned_due_date"):
            await record_due_date_history(
                sr_id, doc.get("planned_due_date"), body.planned_due_date, None, _user_label(current_user)
            )
    if body.estimated_effort:
        updates["estimated_effort"] = body.estimated_effort

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    await record_sr_history(sr_id, "ASSIGNEE_CHANGE", old_assignee, body.assignee_name, _user_label(current_user))
    await record_status_history(sr_id, doc["status"], "IN_PROGRESS", None, _user_label(current_user))

    updated = await col.find_one({"_id": ObjectId(sr_id)})

    # PM 이슈 자동 생성/담당자 업데이트
    from app.services.sr.sr_issue_bridge import auto_create_pm_issue, update_pm_issue_assignee
    existing_issue_id = doc.get("converted_issue_id")
    if existing_issue_id:
        await update_pm_issue_assignee(existing_issue_id, body.assignee_id)
    else:
        result = await auto_create_pm_issue(updated, body.assignee_id, current_user.id)
        if result:
            issue_id, project_id = result
            patch = {"converted_issue_id": issue_id, "converted_project_id": project_id}
            await col.update_one({"_id": ObjectId(sr_id)}, {"$set": patch})
            updated.update(patch)

    await _notify_assignment(updated, sr_id, current_user)

    return SROut(**sr_to_out(updated))


# ── 상태 변경 ─────────────────────────────────────────────────────────

@router.post("/{sr_id}/status", response_model=SROut)
async def change_status(
    sr_id: str,
    body: SRStatusChange,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await get_sr_or_404(sr_id)
    old_status = doc["status"]
    new_status = body.status

    # 권한별 허용 상태 검증
    from app.services.sr.sr_service import (
        is_sr_admin, is_sr_manager, is_sr_operator,
        OPERATOR_ALLOWED_TARGETS, MANAGER_ALLOWED_TARGETS,
    )
    if is_sr_admin(current_user):
        pass  # 모든 상태 허용
    elif is_sr_manager(current_user):
        if new_status not in MANAGER_ALLOWED_TARGETS:
            raise HTTPException(status_code=403, detail=f"해당 상태로 변경할 권한이 없습니다: {new_status}")
    elif is_sr_operator(current_user):
        if new_status not in OPERATOR_ALLOWED_TARGETS:
            raise HTTPException(status_code=403, detail=f"해당 상태로 변경할 권한이 없습니다: {new_status}")
    else:
        raise HTTPException(status_code=403, detail="SR 처리자 이상의 권한이 필요합니다.")

    # 특수 조건 검증
    if new_status in ("REJECTED", "ON_HOLD", "CANCELLED") and not body.reason:
        raise HTTPException(status_code=400, detail="사유를 입력해야 합니다.")
    if new_status == "COMPLETED" and not body.process_result:
        raise HTTPException(status_code=400, detail="처리 결과를 입력해야 합니다.")

    now = datetime.now(timezone.utc)
    updates: dict = {"status": new_status, "updated_at": now, "updated_by": _user_label(current_user)}

    if body.process_result:
        updates["process_result"] = body.process_result
    if body.deployed is not None:
        updates["deployed"] = body.deployed
    if body.deployed_at:
        updates["deployed_at"] = body.deployed_at
    if body.actual_completed_at:
        updates["actual_completed_at"] = body.actual_completed_at
    elif new_status == "COMPLETED":
        updates["actual_completed_at"] = now
    if body.requester_confirmed is not None:
        updates["requester_confirmed"] = body.requester_confirmed

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one({"_id": ObjectId(sr_id)}, {"$set": updates})
    await record_status_history(sr_id, old_status, new_status, body.reason, _user_label(current_user))

    updated = await col.find_one({"_id": ObjectId(sr_id)})

    # Redmine과 동일하게 "완료" 상태로 처음 바뀔 때만 처리완료 메일 발송.
    # old_status != COMPLETED 체크로, 이미 완료된 SR을 재수정(배포여부/처리결과 등)
    # 하느라 이 엔드포인트가 다시 호출돼도 완료 메일이 중복 발송되지 않게 한다.
    if new_status == "COMPLETED" and old_status != "COMPLETED":
        from app.utils.mail_notify import send_sr_notification
        await send_sr_notification(updated, event="completed")

    _SR_STATUS_KO = {
        "SUBMITTED": "접수", "REVIEWING": "검토 중", "PENDING_INFO": "추가 확인 요청",
        "REJECTED": "반려", "APPROVED": "승인", "ASSIGNED": "담당자 배정",
        "IN_PROGRESS": "처리 중", "COMPLETED": "처리 완료",
        "CONFIRMING": "요청자 확인 중", "CLOSED": "최종 완료",
        "ON_HOLD": "보류", "CANCELLED": "취소",
    }
    new_status_ko = _SR_STATUS_KO.get(new_status, new_status)
    sender = _user_label(current_user)
    target_url = f"/pm/sr/{sr_id}"
    notify_ids = {str(doc["requester_id"])}
    if doc.get("assignee_id"):
        notify_ids.add(str(doc["assignee_id"]))
    notify_ids.discard(str(current_user.id))
    for uid in notify_ids:
        await create_notification(
            recipient_user_id=uid,
            notification_type="STATUS_CHANGED",
            title=f"SR 상태 변경: {new_status_ko}",
            message=f"'{doc.get('title', '')}' SR 상태가 {new_status_ko}(으)로 변경되었습니다.",
            sender_user_id=str(current_user.id),
            sender_name=sender,
            target_type="SR",
            target_id=sr_id,
            target_url=target_url,
        )

    return SROut(**sr_to_out(updated))


# ── 완료목표일 변경 (manager 이상) ─────────────────────────────────────

@router.post("/{sr_id}/planned-due-date", response_model=SROut)
async def change_planned_due_date(
    sr_id: str,
    body: SRDueDateChange,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    doc = await get_sr_or_404(sr_id)

    if doc["status"] in ("DRAFT", "CLOSED", "CANCELLED", "REJECTED"):
        raise HTTPException(status_code=400, detail="완료목표일을 변경할 수 있는 상태가 아닙니다.")

    now = datetime.now(timezone.utc)
    old_due = doc.get("planned_due_date")
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one(
        {"_id": ObjectId(sr_id)},
        {"$set": {
            "planned_due_date": body.planned_due_date,
            "updated_at": now,
            "updated_by": _user_label(current_user),
        }},
    )
    await record_due_date_history(
        sr_id, old_due, body.planned_due_date, body.change_reason, _user_label(current_user)
    )
    await record_sr_history(
        sr_id, "FIELD_CHANGE:planned_due_date",
        str(old_due)[:10] if old_due else None,
        str(body.planned_due_date)[:10], _user_label(current_user),
    )

    # 요청자에게 완료목표일 변경 알림
    await create_notification(
        recipient_user_id=str(doc["requester_id"]),
        notification_type="STATUS_CHANGED",
        title="SR 완료목표일 변경",
        message=f"'{doc.get('title', '')}' SR의 완료목표일이 {str(body.planned_due_date)[:10]}(으)로 변경되었습니다.",
        sender_user_id=str(current_user.id),
        sender_name=_user_label(current_user),
        target_type="SR",
        target_id=sr_id,
        target_url=f"/pm/sr/{sr_id}",
    )

    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── 내부 이슈 전환 ────────────────────────────────────────────────────

@router.post("/{sr_id}/convert-to-issue", response_model=SROut)
async def convert_to_issue(
    sr_id: str,
    issue_id: str = Query(...),
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_manager(current_user)
    doc = await get_sr_or_404(sr_id)
    now = datetime.now(timezone.utc)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one(
        {"_id": ObjectId(sr_id)},
        {"$set": {"converted_issue_id": issue_id, "updated_at": now, "updated_by": _user_label(current_user)}},
    )
    await record_sr_history(sr_id, "CONVERT_TO_ISSUE", None, issue_id, _user_label(current_user))
    updated = await col.find_one({"_id": ObjectId(sr_id)})
    return SROut(**sr_to_out(updated))


# ── SR 삭제 (soft delete) ─────────────────────────────────────────────

@router.delete("/{sr_id}", status_code=204)
async def delete_sr(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_admin(current_user)
    await get_sr_or_404(sr_id)
    now = datetime.now(timezone.utc)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    await col.update_one(
        {"_id": ObjectId(sr_id)},
        {"$set": {"deleted_at": now, "updated_at": now, "updated_by": _user_label(current_user)}},
    )


# ── 통계 ─────────────────────────────────────────────────────────────

@router.get("/stats/summary", response_model=SRStats)
async def get_stats(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_operator(current_user)
    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]

    q: dict = {"deleted_at": None}
    if date_from or date_to:
        df: dict = {}
        if date_from:
            df["$gte"] = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        if date_to:
            df["$lte"] = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        q["created_at"] = df

    docs = await col.find(q).to_list(None)

    stats = SRStats(
        total=len(docs),
        submitted=0, in_progress=0, completed=0,
        rejected=0, on_hold=0, delayed=0, cancelled=0, urgent_count=0,
    )
    processing_times: list[float] = []

    for d in docs:
        s = d.get("status", "")
        if s in ("SUBMITTED", "REVIEWING", "PENDING_INFO", "APPROVED", "ASSIGNED"):
            stats.submitted += 1
        if s in ("IN_PROGRESS", "COMPLETED", "CONFIRMING"):
            stats.in_progress += 1
        if s == "CLOSED":
            stats.completed += 1
        if s == "REJECTED":
            stats.rejected += 1
        if s == "ON_HOLD":
            stats.on_hold += 1
        if s == "CANCELLED":
            stats.cancelled += 1
        if d.get("is_urgent"):
            stats.urgent_count += 1
        if compute_is_delayed(d):
            stats.delayed += 1

        rt = d.get("request_type", "ETC")
        stats.by_type[rt] = stats.by_type.get(rt, 0) + 1

        dept = d.get("requester_department", "미지정")
        stats.by_department[dept] = stats.by_department.get(dept, 0) + 1

        sys_name = d.get("related_system") or "미지정"
        stats.by_system[sys_name] = stats.by_system.get(sys_name, 0) + 1

        assignee = d.get("assignee_name") or "미배정"
        stats.by_assignee[assignee] = stats.by_assignee.get(assignee, 0) + 1

        if d.get("actual_completed_at") and d.get("created_at"):
            delta = (d["actual_completed_at"] - d["created_at"]).total_seconds() / 86400
            processing_times.append(delta)

    if processing_times:
        stats.avg_processing_days = round(sum(processing_times) / len(processing_times), 1)

    closed_docs = [d for d in docs if d.get("status") == "CLOSED"]
    on_time = 0
    for d in closed_docs:
        completed_at = d.get("actual_completed_at")
        planned_due = d.get("planned_due_date") or d.get("desired_due_date")
        if completed_at and planned_due:
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            if planned_due.tzinfo is None:
                planned_due = planned_due.replace(tzinfo=timezone.utc)
            if completed_at <= planned_due:
                on_time += 1
    if closed_docs:
        stats.on_time_rate = round(on_time / len(closed_docs) * 100, 1)

    return stats


# ── Excel 다운로드 ────────────────────────────────────────────────────

@router.get("/export", response_class=StreamingResponse)
async def export_excel(
    status: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    is_delayed: Optional[bool] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_admin(current_user)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from datetime import date

    col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    q: dict = {"deleted_at": None}
    if status:
        q["status"] = status
    if request_type:
        q["request_type"] = request_type
    if date_from or date_to:
        df: dict = {}
        if date_from:
            df["$gte"] = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        if date_to:
            df["$lte"] = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        q["created_at"] = df

    all_docs = await col.find(q).sort("created_at", -1).to_list(None)
    if is_delayed is not None:
        docs = [d for d in all_docs if compute_is_delayed(d) == is_delayed]
    else:
        docs = all_docs

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SR목록"

    headers = [
        "SR번호", "요청제목", "요청부서", "요청자", "요청유형", "관련시스템",
        "중요도", "긴급여부", "희망완료일", "완료목표일", "실제완료일",
        "담당자", "상태", "지연여부", "접수일", "최종수정일",
    ]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    def _fmt_dt(dt):
        if not dt:
            return ""
        if hasattr(dt, "strftime"):
            return dt.strftime("%Y-%m-%d")
        return str(dt)[:10]

    for row_idx, d in enumerate(docs, 2):
        is_delayed = "Y" if compute_is_delayed(d) else "N"
        ws.append([
            d.get("sr_no", ""),
            d.get("title", ""),
            d.get("requester_department", ""),
            d.get("requester_name", ""),
            REQUEST_TYPE_LABEL.get(d.get("request_type", ""), d.get("request_type", "")),
            d.get("related_system", ""),
            SR_PRIORITY_LABEL.get(d.get("priority", ""), ""),
            "Y" if d.get("is_urgent") else "N",
            _fmt_dt(d.get("desired_due_date")),
            _fmt_dt(d.get("planned_due_date")),
            _fmt_dt(d.get("actual_completed_at")),
            d.get("assignee_name", ""),
            SR_STATUS_LABEL.get(d.get("status", ""), d.get("status", "")),
            is_delayed,
            _fmt_dt(d.get("created_at")),
            _fmt_dt(d.get("updated_at")),
        ])

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = 30
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 18
    ws.column_dimensions['B'].width = 48
    ws.column_dimensions['E'].width = 24
    ws.column_dimensions['F'].width = 26
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = 's'
            cell.font = Font(name='맑은 고딕', size=11, color='243447')
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            if cell.row % 2 == 0:
                cell.fill = PatternFill('solid', fgColor='F1F5F9')
        ws.row_dimensions[row[0].row].height = max(36, 18 * ((len(str(row[1].value or '')) + 22) // 23))
    ws.print_title_rows = '1:1'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    today = date.today().strftime("%Y-%m-%d")
    filename = f"SR목록_{today}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@router.get("/{sr_id}/export", response_class=StreamingResponse)
async def export_sr_detail(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_admin(current_user)
    doc = await get_sr_or_404(sr_id)
    output, filename, media_type, warnings = await run_in_threadpool(
        export_detail, doc)
    return StreamingResponse(
        stream_export(output), media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
            "X-Export-Warnings": str(warnings),
        },
        background=BackgroundTask(output.close),
    )


# Register the dynamic detail route after /export so the static path is not treated as an SR ID.
@router.get("/{sr_id}", response_model=SROut)
async def get_sr_admin(
    sr_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    require_sr_operator(current_user)
    doc = await get_sr_or_404(sr_id)
    return SROut(**sr_to_out(doc))
