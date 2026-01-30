# app/routers/inspection.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.inspection import (
    InspectionChecklistCreate,
    InspectionChecklistReplace,
    InspectionChecklistPatch,
    InspectionChecklistOut,
    InspectionHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.inspection_service import InspectionChecklistService
from app.utils.mongo import oid

router = APIRouter()
svc = InspectionChecklistService()


@router.get("", response_model=List[InspectionChecklistOut])
async def list_checklists(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(include_deleted=include_deleted)
    return [InspectionChecklistOut(**x) for x in items]


@router.post("", response_model=InspectionChecklistOut, status_code=status.HTTP_201_CREATED)
async def create_checklist(
    body: InspectionChecklistCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.create(
            inspection_month=body.inspection_month,
            person_in_charge=body.person_in_charge,
            system_room_result=body.system_room_result,
            resource_usage_abnormal=body.resource_usage_abnormal,
            notes=body.notes,
            actor_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return InspectionChecklistOut(**out)


@router.put("/{checklist_id}", response_model=InspectionChecklistOut)
async def replace_checklist(
    checklist_id: str,
    body: InspectionChecklistReplace,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.replace(
            _id=oid(checklist_id),
            inspection_month=body.inspection_month,
            person_in_charge=body.person_in_charge,
            system_room_result=body.system_room_result,
            resource_usage_abnormal=body.resource_usage_abnormal,
            notes=body.notes,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return InspectionChecklistOut(**out)


@router.patch("/{checklist_id}", response_model=InspectionChecklistOut)
async def patch_checklist(
    checklist_id: str,
    body: InspectionChecklistPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.patch(
            _id=oid(checklist_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return InspectionChecklistOut(**out)


@router.delete("/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checklist(
    checklist_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await svc.delete(_id=oid(checklist_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/{checklist_id}/history", response_model=List[InspectionHistoryOut])
async def get_history(
    checklist_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.get_history(checklist_id=checklist_id)
    return [InspectionHistoryOut(**x) for x in items]
