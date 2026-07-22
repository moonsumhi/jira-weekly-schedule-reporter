from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.db.mongo import MongoClientManager
from app.models.isms_vulnerability import (
    FilterOptionsOut,
    VulnerabilityActionPatch,
    VulnerabilityCreate,
    VulnerabilityListPage,
    VulnerabilityOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()

UPLOAD_DIR = "/app/uploads/isms-p"
ACTION_STATUS_UNREACHABLE = "접속불가"


async def require_isms_p(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    # 권한 문자열은 관리자 화면에서 menu.slug 그대로 부여되므로 'isms-p'(하이픈)와 일치해야 한다
    if current_user.is_admin or "isms-p" in (current_user.permissions or []):
        return current_user
    raise HTTPException(status_code=403, detail="ISMS-P 취약점 관리 권한이 없습니다.")


def _secure_filename(filename: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    return safe or "file"


def _to_out(doc: dict, cascade_count: int = 0) -> VulnerabilityOut:
    return VulnerabilityOut(
        id=str(doc["_id"]),
        cascade_count=cascade_count,
        check_date=doc.get("check_date"),
        asset_category=doc.get("asset_category"),
        asset_type=doc.get("asset_type"),
        zone=doc.get("zone"),
        asset_name=doc.get("asset_name"),
        hostname=doc.get("hostname"),
        ip_address=doc.get("ip_address"),
        classification=doc.get("classification"),
        check_code=doc.get("check_code"),
        check_item=doc.get("check_item"),
        risk_level=doc.get("risk_level"),
        check_result=doc.get("check_result"),
        assignee=doc.get("assignee"),
        control_status=doc.get("control_status"),
        action_plan=doc.get("action_plan"),
        planned_date=doc.get("planned_date"),
        action_status=doc.get("action_status"),
        action_details=doc.get("action_details"),
        before_text=doc.get("before_text"),
        after_text=doc.get("after_text"),
        notes=doc.get("notes"),
        action_difficulty=doc.get("action_difficulty"),
        source_sheet=doc.get("source_sheet"),
        before_files=doc.get("before_files") or [],
        after_files=doc.get("after_files") or [],
        created_at=fmt_dt(doc.get("created_at")),
        updated_at=fmt_dt(doc.get("updated_at")),
    )


# ── 필터 옵션 (드롭다운용 distinct 값) ───────────────────────────────────
@router.get("/filter-options", response_model=FilterOptionsOut)
async def get_filter_options(current_user: UserPublic = Depends(require_isms_p)):
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    asset_types = [v for v in await col.distinct("source_sheet") if v]
    assignees = [v for v in await col.distinct("assignee") if v]
    return FilterOptionsOut(asset_types=sorted(asset_types), assignees=sorted(assignees))


# ── 목록 (서버사이드 페이지네이션 + 필터) ────────────────────────────────
@router.get("", response_model=VulnerabilityListPage)
async def list_vulnerabilities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    control_status: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    action_status: Optional[str] = Query(None),
    planned_date_from: Optional[str] = Query(None),
    planned_date_to: Optional[str] = Query(None),
    current_user: UserPublic = Depends(require_isms_p),
):
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    q: dict = {}

    if asset_type and asset_type != "전체":
        q["source_sheet"] = asset_type
    if risk_level and risk_level != "전체":
        q["risk_level"] = risk_level
    if control_status and control_status != "전체":
        q["control_status"] = control_status
    if assignee and assignee.strip():
        q["assignee"] = assignee.strip()

    if action_status == "완료":
        q["action_status"] = {"$regex": "완료"}
    elif action_status == "미조치":
        q["$or"] = [
            {"action_status": None},
            {"action_status": ""},
            {"action_status": "미조치"},
        ]
    elif action_status == ACTION_STATUS_UNREACHABLE:
        q["action_status"] = ACTION_STATUS_UNREACHABLE

    if planned_date_from or planned_date_to:
        pd: dict = {}
        if planned_date_from:
            pd["$gte"] = planned_date_from
        if planned_date_to:
            pd["$lte"] = planned_date_to
        q["planned_date"] = pd

    if search and search.strip():
        term = search.strip()
        search_or = [
            {f: {"$regex": term, "$options": "i"}}
            for f in ("check_code", "check_item", "hostname", "asset_name", "ip_address")
        ]
        if "$or" in q:
            q["$and"] = [{"$or": q.pop("$or")}, {"$or": search_or}]
        else:
            q["$or"] = search_or

    total = await col.count_documents(q)
    docs = await col.find(q).sort("_id", 1).skip(skip).limit(limit).to_list(None)
    return VulnerabilityListPage(items=[_to_out(d) for d in docs], total=total)


@router.get("/{vuln_id}", response_model=VulnerabilityOut)
async def get_vulnerability(vuln_id: str, current_user: UserPublic = Depends(require_isms_p)):
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    doc = await col.find_one({"_id": parse_oid(vuln_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="취약점을 찾을 수 없습니다")
    return _to_out(doc)


@router.post("", response_model=VulnerabilityOut, status_code=201)
async def create_vulnerability(
    body: VulnerabilityCreate,
    current_user: UserPublic = Depends(require_isms_p),
):
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    doc = body.model_dump()
    doc["before_files"] = []
    doc["after_files"] = []
    doc["source_sheet"] = "manual"
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = None
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{vuln_id}", response_model=VulnerabilityOut)
async def patch_vulnerability(
    vuln_id: str,
    body: VulnerabilityActionPatch,
    current_user: UserPublic = Depends(require_isms_p),
):
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    _id = parse_oid(vuln_id)

    existing = await col.find_one({"_id": _id})
    if not existing:
        raise HTTPException(status_code=404, detail="취약점을 찾을 수 없습니다")
    old_status = existing.get("action_status")

    update = body.model_dump(exclude_unset=True)
    update["updated_at"] = datetime.now(timezone.utc)
    doc = await col.find_one_and_update({"_id": _id}, {"$set": update}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="취약점을 찾을 수 없습니다")

    cascade_count = 0
    ip = doc.get("ip_address")
    assignee = doc.get("assignee")
    new_status = update.get("action_status")

    # 같은 IP라도 담당자가 다르면 접속 가능 여부가 다를 수 있으므로, 같은 담당자가 맡은 레코드끼리만 전파한다
    if ip and assignee:
        if new_status == ACTION_STATUS_UNREACHABLE and old_status != ACTION_STATUS_UNREACHABLE:
            result = await col.update_many(
                {
                    "ip_address": ip,
                    "assignee": assignee,
                    "_id": {"$ne": _id},
                    "action_status": {"$ne": ACTION_STATUS_UNREACHABLE},
                },
                {"$set": {"action_status": ACTION_STATUS_UNREACHABLE, "updated_at": update["updated_at"]}},
            )
            cascade_count = result.modified_count
        elif old_status == ACTION_STATUS_UNREACHABLE and new_status is not None and new_status != ACTION_STATUS_UNREACHABLE:
            # 접속불가 해제: 같은 담당자·같은 IP의 다른 접속불가 레코드도 함께 미조치로 되돌린다
            result = await col.update_many(
                {
                    "ip_address": ip,
                    "assignee": assignee,
                    "_id": {"$ne": _id},
                    "action_status": ACTION_STATUS_UNREACHABLE,
                },
                {"$set": {"action_status": "미조치", "updated_at": update["updated_at"]}},
            )
            cascade_count = result.modified_count

    return _to_out(doc, cascade_count=cascade_count)


@router.post("/{vuln_id}/upload/{file_type}")
async def upload_vuln_file(
    vuln_id: str,
    file_type: str,
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(require_isms_p),
):
    if file_type not in ("before", "after"):
        raise HTTPException(status_code=400, detail="file_type은 before/after만 허용됩니다")
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    _id = parse_oid(vuln_id)
    doc = await col.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="취약점을 찾을 수 없습니다")

    content = await file.read()
    dest_dir = os.path.join(UPLOAD_DIR, vuln_id, file_type)
    os.makedirs(dest_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{_secure_filename(file.filename or 'file')}"
    with open(os.path.join(dest_dir, stored_name), "wb") as f:
        f.write(content)

    files_key = f"{file_type}_files"
    new_entry = {"name": stored_name, "original": file.filename or stored_name}
    updated = await col.find_one_and_update(
        {"_id": _id},
        {"$push": {files_key: new_entry}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    return {"success": True, "files": updated.get(files_key) or []}


@router.delete("/{vuln_id}/files/{file_type}/{filename}")
async def delete_vuln_file(
    vuln_id: str,
    file_type: str,
    filename: str,
    current_user: UserPublic = Depends(require_isms_p),
):
    if file_type not in ("before", "after"):
        raise HTTPException(status_code=400, detail="file_type은 before/after만 허용됩니다")
    col = MongoClientManager.get_isms_vulnerabilities_collection()
    _id = parse_oid(vuln_id)

    safe_name = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, vuln_id, file_type, safe_name)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass

    files_key = f"{file_type}_files"
    updated = await col.find_one_and_update(
        {"_id": _id},
        {"$pull": {files_key: {"name": safe_name}}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="취약점을 찾을 수 없습니다")
    return {"success": True, "files": updated.get(files_key) or []}
