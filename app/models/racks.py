# app/models/racks.py
"""랙 배치(rack_placements) 요청/응답 모델.

랙 자체는 기존 자산 카테고리("랙")로 관리되므로 별도 모델이 필요 없다.
여기서는 "어느 자산이 어느 랙의 몇 U에 있는지"만 다룬다. 자산·랙 참조는
사용자 편집 가능한 asset_id 가 아니라 불변인 Mongo _id(문자열) 로 조인한다.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

MountSide = Literal["FULL", "FRONT", "REAR"]


class RackPlacementCreate(BaseModel):
    asset_category: str = Field(..., description="배치할 자산의 카테고리 (서버/네트워크/…)")
    asset_id: str = Field(..., description="배치할 자산의 Mongo _id (hex)")
    rack_id: str = Field(..., description="랙 자산의 Mongo _id (hex)")
    start_u: int = Field(..., ge=1, description="점유하는 가장 낮은 U")
    height_u: int = Field(..., ge=1, description="장비 높이(U)")
    mount_side: MountSide = "FULL"


class RackPlacementUpdate(BaseModel):
    """이동: 랙/시작U/높이/장착면 변경. expected_version 으로 낙관적 잠금."""
    rack_id: str
    start_u: int = Field(..., ge=1)
    height_u: int = Field(..., ge=1)
    mount_side: MountSide = "FULL"
    expected_version: Optional[int] = None


class RackPlacementOut(BaseModel):
    id: str
    asset_category: str
    asset_id: str
    rack_id: str
    start_u: int
    height_u: int
    end_u: int
    mount_side: MountSide
    occupied_slots: List[str]
    version: int
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class RackPlacementAsset(BaseModel):
    """배치도에서 한 칸을 차지하는 자산 + 위치 정보."""
    placement_id: str
    asset_category: str
    asset_id: str
    asset_code: Optional[str] = None   # 사용자 지정 자산번호(asset_id 필드)
    asset_no: Optional[str] = None
    name: str
    ip: Optional[str] = None
    start_u: int
    end_u: int
    height_u: int
    mount_side: MountSide
    version: int


class RackSummary(BaseModel):
    rack_id: str
    asset_code: Optional[str] = None
    name: str
    server_room: Optional[str] = None
    total_u: int
    used_u: int
    free_u: int
    usage_rate: float
    max_contiguous_free_u: int
    asset_count: int
    status: Optional[str] = None
    max_load_kg: Optional[float] = None
    max_power_w: Optional[float] = None


class UnplacedAsset(BaseModel):
    asset_category: str
    asset_id: str
    asset_code: Optional[str] = None
    asset_no: Optional[str] = None
    name: str
    ip: Optional[str] = None


class PlacementHistoryPos(BaseModel):
    rack_id: Optional[str] = None
    rack_name: Optional[str] = None
    start_u: Optional[int] = None
    end_u: Optional[int] = None
    mount_side: Optional[str] = None


class PlacementHistoryOut(BaseModel):
    id: str
    action: str
    asset_category: Optional[str] = None
    asset_id: Optional[str] = None
    asset_name: Optional[str] = None
    before: Optional[PlacementHistoryPos] = None
    after: Optional[PlacementHistoryPos] = None
    changed_at: datetime
    changed_by: Optional[str] = None


class IntegrityIssue(BaseModel):
    type: str
    placement_id: str
    asset_category: Optional[str] = None
    asset_id: Optional[str] = None
    detail: Optional[str] = None


class IntegrityReport(BaseModel):
    checked_at: datetime
    status: str            # OK | WARNING
    issue_count: int
    issues: List[IntegrityIssue] = Field(default_factory=list)


class RackLayoutResponse(BaseModel):
    rack: RackSummary
    placements: List[RackPlacementAsset] = Field(default_factory=list)


class AssetSearchResult(BaseModel):
    asset_category: str
    asset_id: str
    asset_code: Optional[str] = None
    asset_no: Optional[str] = None
    name: str
    ip: Optional[str] = None
    placement: Optional[dict] = None   # {rack_id, rack_name, server_room, start_u, end_u}
