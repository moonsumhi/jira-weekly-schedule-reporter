# app/routers/job_result.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.job import (
    ServiceWorkResultCreate,
    ServiceWorkResultPatch,
    ServiceWorkResultOut,
    ServiceWorkResultHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.job_result_service import ServiceWorkResultService
from app.utils.mongo import oid

router = APIRouter()
svc = ServiceWorkResultService()


@router.get("", response_model=List[ServiceWorkResultOut])
async def list_results(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(include_deleted=include_deleted)
    return [ServiceWorkResultOut(**x) for x in items]


@router.get("/{result_id}", response_model=ServiceWorkResultOut)
async def get_result(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await svc.get(_id=oid(result_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return ServiceWorkResultOut(**doc)


@router.post("", response_model=ServiceWorkResultOut, status_code=status.HTTP_201_CREATED)
async def create_result(
    body: ServiceWorkResultCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    out = await svc.create(
        data=body.model_dump(),
        actor_email=current_user.email,
    )
    return ServiceWorkResultOut(**out)


@router.patch("/{result_id}", response_model=ServiceWorkResultOut)
async def patch_result(
    result_id: str,
    body: ServiceWorkResultPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.patch(
            _id=oid(result_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServiceWorkResultOut(**out)


@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await svc.delete(_id=oid(result_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/{result_id}/history", response_model=List[ServiceWorkResultHistoryOut])
async def get_history(
    result_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.get_history(result_id=result_id)
    return [ServiceWorkResultHistoryOut(**x) for x in items]
