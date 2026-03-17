# app/routers/job.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.job import (
    ServiceWorkPlanCreate,
    ServiceWorkPlanPatch,
    ServiceWorkPlanOut,
    ServiceWorkPlanHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.job_service import ServiceWorkPlanService
from app.utils.mongo import oid

router = APIRouter()
svc = ServiceWorkPlanService()


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
