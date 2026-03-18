# app/routers/job_non_service.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.job import (
    NonServiceWorkPlanCreate,
    NonServiceWorkPlanPatch,
    NonServiceWorkPlanOut,
    NonServiceWorkPlanHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.job_non_service_service import NonServiceWorkPlanService
from app.utils.mongo import oid

router = APIRouter()
svc = NonServiceWorkPlanService()


@router.get("", response_model=List[NonServiceWorkPlanOut])
async def list_plans(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(include_deleted=include_deleted)
    return [NonServiceWorkPlanOut(**x) for x in items]


@router.get("/{plan_id}", response_model=NonServiceWorkPlanOut)
async def get_plan(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await svc.get(_id=oid(plan_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return NonServiceWorkPlanOut(**doc)


@router.post("", response_model=NonServiceWorkPlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: NonServiceWorkPlanCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    out = await svc.create(
        data=body.model_dump(),
        actor_email=current_user.email,
    )
    return NonServiceWorkPlanOut(**out)


@router.patch("/{plan_id}", response_model=NonServiceWorkPlanOut)
async def patch_plan(
    plan_id: str,
    body: NonServiceWorkPlanPatch,
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
    return NonServiceWorkPlanOut(**out)


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


@router.get("/{plan_id}/history", response_model=List[NonServiceWorkPlanHistoryOut])
async def get_history(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.get_history(plan_id=plan_id)
    return [NonServiceWorkPlanHistoryOut(**x) for x in items]
