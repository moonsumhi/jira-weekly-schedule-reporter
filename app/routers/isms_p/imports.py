from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.db.mongo import MongoClientManager
from app.models.isms_vulnerability import ImportLogOut, ImportResultOut, RollbackResultOut
from app.models.user import UserPublic
from app.routers.isms_p.vulnerabilities import require_isms_p
from app.services.isms_vuln_import import import_all, rollback_import
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


@router.get("/import-history", response_model=list[ImportLogOut])
async def list_import_history(current_user: UserPublic = Depends(require_isms_p)):
    col = MongoClientManager.get_isms_import_logs_collection()
    docs = await col.find({}).sort("_id", -1).to_list(None)
    return [
        ImportLogOut(
            id=str(d["_id"]),
            created_at=fmt_dt(d.get("created_at")),
            records_before=d.get("records_before", 0),
            inserted=d.get("inserted", 0),
            updated=d.get("updated", 0),
            records_after=d.get("records_after", 0),
            uploader_email=d.get("uploader_email"),
            note=d.get("note"),
            rolled_back=bool(d.get("rolled_back", False)),
            can_rollback=not d.get("rolled_back", False),
        )
        for d in docs
    ]


@router.post("/import", response_model=ImportResultOut)
async def import_excel(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(require_isms_p),
):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="xlsx/xlsm 파일만 업로드할 수 있습니다.")

    content = await file.read()
    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        result = await import_all(tmp_path, actor_email=current_user.email)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return ImportResultOut(**result)


@router.post("/rollback/{log_id}", response_model=RollbackResultOut)
async def rollback_import_log(log_id: str, current_user: UserPublic = Depends(require_isms_p)):
    parse_oid(log_id)  # 형식 검증
    try:
        result = await rollback_import(log_id)
    except ValueError as e:
        status = 404 if str(e) == "가져오기 이력을 찾을 수 없습니다." else 400
        raise HTTPException(status_code=status, detail=str(e))
    return RollbackResultOut(**result)
