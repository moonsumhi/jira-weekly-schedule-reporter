# app/routers/assets.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.assets import (
    ServerAssetCreate,
    ServerAssetReplace,
    ServerAssetPatch,
    ServerAssetOut,
    AssetHistoryOut,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.assets_service import AssetsService
from app.utils.mongo import oid

router = APIRouter()
svc = AssetsService()


@router.get("", response_model=List[ServerAssetOut])
async def list_servers(
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.list(include_deleted=include_deleted)
    return [ServerAssetOut(**x) for x in items]


@router.post("", response_model=ServerAssetOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerAssetCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.create(
            ip=body.ip,
            name=body.name,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.put("/{server_id}", response_model=ServerAssetOut)
async def replace_server(
    server_id: str,
    body: ServerAssetReplace,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.replace(
            _id=oid(server_id),
            ip=body.ip,
            name=body.name,
            fields=body.fields,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.patch("/{server_id}", response_model=ServerAssetOut)
async def patch_server(
    server_id: str,
    body: ServerAssetPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        out = await svc.patch(
            _id=oid(server_id),
            patch=body.model_dump(),
            expected_version=body.version,
            actor_email=current_user.email,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ServerAssetOut(**out)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        await svc.delete(_id=oid(server_id), actor_email=current_user.email)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return


@router.get("/{server_id}/history", response_model=List[AssetHistoryOut])
async def get_history(
    server_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    items = await svc.get_history(server_id=server_id)
    return [AssetHistoryOut(**x) for x in items]
