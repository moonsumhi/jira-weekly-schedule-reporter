# app/routers/watch_timetable.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.user import UserPublic
from app.models.watch import (
    WatchAssignmentCreate,
    WatchAssignmentReplace,
    WatchAssignmentPatch,
    WatchAssignmentOut,
)
from app.routers.auth import get_current_user
from app.services.watch_timetable import WatchTimetableService
from app.utils.mongo import oid

router = APIRouter()
svc = WatchTimetableService(enforce_no_overlap_per_assignee=True)


@router.get("", response_model=List[WatchAssignmentOut])
async def list_assignments(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(start=start, end=end, include_deleted=include_deleted)
    return [WatchAssignmentOut(**x) for x in items]


@router.post("", response_model=WatchAssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: WatchAssignmentCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.create(
            assignee=body.assignee,
            start=body.start,
            end=body.end,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return WatchAssignmentOut(**out)


@router.put("/{assignment_id}", response_model=WatchAssignmentOut)
async def replace_assignment(
    assignment_id: str,
    body: WatchAssignmentReplace,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.replace(
            _id=oid(assignment_id),
            assignee=body.assignee,
            start=body.start,
            end=body.end,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return WatchAssignmentOut(**out)


@router.patch("/{assignment_id}", response_model=WatchAssignmentOut)
async def patch_assignment(
    assignment_id: str,
    body: WatchAssignmentPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.patch(
            _id=oid(assignment_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return WatchAssignmentOut(**out)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await svc.delete(_id=oid(assignment_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return
