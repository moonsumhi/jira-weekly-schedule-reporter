# app/routers/job.py
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status

from app.models.job import (
    ServiceWorkPlanCreate,
    ServiceWorkPlanPatch,
    ServiceWorkPlanOut,
    ServiceWorkPlanHistoryOut,
    NonServiceWorkPlanCreate,
    NonServiceWorkPlanPatch,
    NonServiceWorkPlanOut,
    NonServiceWorkPlanHistoryOut,
    JobResultCreate,
    JobResultPatch,
    JobResultOut,
    JobResultHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.job_service import ServiceWorkPlanService, NonServiceWorkPlanService, JobResultService
from app.utils.mongo import oid

router = APIRouter()
svc = ServiceWorkPlanService()
ns_svc = NonServiceWorkPlanService()
result_svc = JobResultService()


# ─── 작업계획서(서비스 외) — must come BEFORE /{plan_id} ─────────────────────

@router.get("/non-service", response_model=List[NonServiceWorkPlanOut])
async def list_ns_plans(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await ns_svc.list(include_deleted=include_deleted)
    return [NonServiceWorkPlanOut(**x) for x in items]


@router.post("/non-service", response_model=NonServiceWorkPlanOut, status_code=status.HTTP_201_CREATED)
async def create_ns_plan(
    body: NonServiceWorkPlanCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    out = await ns_svc.create(data=body.model_dump(), actor_email=current_user.email)
    return NonServiceWorkPlanOut(**out)


@router.get("/non-service/{plan_id}", response_model=NonServiceWorkPlanOut)
async def get_ns_plan(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await ns_svc.get(_id=oid(plan_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return NonServiceWorkPlanOut(**doc)


@router.patch("/non-service/{plan_id}", response_model=NonServiceWorkPlanOut)
async def patch_ns_plan(
    plan_id: str,
    body: NonServiceWorkPlanPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await ns_svc.patch(
            _id=oid(plan_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return NonServiceWorkPlanOut(**out)


@router.delete("/non-service/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ns_plan(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await ns_svc.delete(_id=oid(plan_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/non-service/{plan_id}/history", response_model=List[NonServiceWorkPlanHistoryOut])
async def get_ns_history(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await ns_svc.get_history(plan_id=plan_id)
    return [NonServiceWorkPlanHistoryOut(**x) for x in items]


# ─── 첨부파일 텍스트 추출 (작업test3용) ─────────────────────────────────────

SUPPORTED_EXTENSIONS = {"hwp", "txt", "md"}


def _extract_hwp_bytes(data: bytes) -> str | None:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
            f.write(data)
            tmp_path = f.name
        result = subprocess.run(
            ["hwp5txt", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/result3/extract-attachment")
async def extract_attachment_text(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
):
    """업로드된 첨부파일(HWP/txt/md)에서 텍스트를 추출하여 반환."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_EXTENSIONS)}",
        )
    data = await file.read()
    if ext == "hwp":
        text = _extract_hwp_bytes(data)
        if text is None:
            raise HTTPException(status_code=422, detail="HWP 파일 텍스트 추출에 실패했습니다.")
    else:
        text = data.decode("utf-8", errors="replace")
    return {"filename": filename, "text": text}


# ─── 작업결과서 — must come BEFORE /{plan_id} ────────────────────────────────

@router.get("/result", response_model=List[JobResultOut])
async def list_results(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await result_svc.list(include_deleted=include_deleted)
    return [JobResultOut(**x) for x in items]


@router.post("/result", response_model=JobResultOut, status_code=status.HTTP_201_CREATED)
async def create_result(
    body: JobResultCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    out = await result_svc.create(data=body.model_dump(), actor_email=current_user.email)
    return JobResultOut(**out)


@router.get("/result/{result_id}", response_model=JobResultOut)
async def get_result(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await result_svc.get(_id=oid(result_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return JobResultOut(**doc)


@router.patch("/result/{result_id}", response_model=JobResultOut)
async def patch_result(
    result_id: str,
    body: JobResultPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await result_svc.patch(
            _id=oid(result_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return JobResultOut(**out)


@router.delete("/result/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await result_svc.delete(_id=oid(result_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/result/{result_id}/history", response_model=List[JobResultHistoryOut])
async def get_result_history(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await result_svc.get_history(plan_id=result_id)
    return [JobResultHistoryOut(**x) for x in items]


# ─── 작업계획서(서비스) ───────────────────────────────────────────────────────

@router.get("", response_model=List[ServiceWorkPlanOut])
async def list_plans(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(include_deleted=include_deleted)
    return [ServiceWorkPlanOut(**x) for x in items]


@router.get("/{plan_id}", response_model=ServiceWorkPlanOut)
async def get_plan(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await svc.get(_id=oid(plan_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return ServiceWorkPlanOut(**doc)


@router.post("", response_model=ServiceWorkPlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: ServiceWorkPlanCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    out = await svc.create(
        data=body.model_dump(),
        actor_email=current_user.email,
    )
    return ServiceWorkPlanOut(**out)


@router.patch("/{plan_id}", response_model=ServiceWorkPlanOut)
async def patch_plan(
    plan_id: str,
    body: ServiceWorkPlanPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.patch(
            _id=oid(plan_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServiceWorkPlanOut(**out)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await svc.delete(_id=oid(plan_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/{plan_id}/history", response_model=List[ServiceWorkPlanHistoryOut])
async def get_history(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.get_history(plan_id=plan_id)
    return [ServiceWorkPlanHistoryOut(**x) for x in items]
