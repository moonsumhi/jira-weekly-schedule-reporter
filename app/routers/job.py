# app/routers/job.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
