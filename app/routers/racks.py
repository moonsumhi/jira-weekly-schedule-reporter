# app/routers/racks.py
"""랙 배치도 및 랙 배치(placement) API.

랙 자산 자체의 CRUD 는 기존 자산 API(/assets?category=랙)를 그대로 재사용한다.
여기서는 조회(배치도·목록·검색)와 배치 관계(생성·이동·반출)만 다룬다.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.models.racks import (
    AssetSearchResult,
    IntegrityReport,
    PlacementHistoryOut,
    RackLayoutResponse,
    RackPlacementCreate,
    RackPlacementOut,
    RackPlacementUpdate,
    RackSummary,
    UnplacedAsset,
)
from app.models.user import UserPublic
from app.routers.admin import require_admin
from app.routers.auth import get_current_user
from app.routers.permissions import require_asset_access
from app.services import rack_placement_service as placement_svc
from app.services import rack_service as rack_svc

router = APIRouter()


@router.get("", response_model=List[RackSummary])
async def list_racks(
    server_room: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    return await rack_svc.list_racks(server_room)


@router.get("/assets/search", response_model=List[AssetSearchResult])
async def search_assets(
    q: str = Query(..., min_length=1),
    current_user: UserPublic = Depends(get_current_user),
):
    return await rack_svc.search_assets(q)


@router.get("/assets/unplaced", response_model=List[UnplacedAsset])
async def list_unplaced(
    category: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    return await rack_svc.list_unplaced_assets(category)


@router.get("/integrity-check", response_model=IntegrityReport)
async def integrity_check(
    current_user: UserPublic = Depends(require_admin),
):
    return await rack_svc.integrity_check()


@router.post("/migrate-from-fields")
async def migrate_from_fields(
    dry_run: bool = Query(True),
    current_user: UserPublic = Depends(require_admin),
):
    """레거시 fields.rack_no/rack_unit_no → 랙 자산 + 배치 이관 (dry_run 기본)."""
    return await rack_svc.migrate_from_fields(dry_run, actor=current_user.email)


@router.get("/{rack_id}/history", response_model=List[PlacementHistoryOut])
async def rack_history(
    rack_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    return await rack_svc.get_rack_history(rack_id)


@router.get("/{rack_id}/layout", response_model=RackLayoutResponse)
async def get_layout(
    rack_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    return await rack_svc.get_layout(rack_id)


@router.post("/placements", response_model=RackPlacementOut, status_code=status.HTTP_201_CREATED)
async def create_placement(
    body: RackPlacementCreate,
    current_user: UserPublic = Depends(require_asset_access),
):
    return await placement_svc.create_placement(body.model_dump(), actor=current_user.email)


@router.put("/placements/{placement_id}", response_model=RackPlacementOut)
async def move_placement(
    placement_id: str,
    body: RackPlacementUpdate,
    current_user: UserPublic = Depends(require_asset_access),
):
    return await placement_svc.move_placement(placement_id, body.model_dump(), actor=current_user.email)


@router.delete("/placements/{placement_id}", response_model=RackPlacementOut)
async def remove_placement(
    placement_id: str,
    current_user: UserPublic = Depends(require_asset_access),
):
    return await placement_svc.remove_placement(placement_id, actor=current_user.email)
