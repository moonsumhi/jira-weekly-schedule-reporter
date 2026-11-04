# app/models/assets.py
from datetime import datetime
from typing import Any, Dict, Optional, Literal, List

from pydantic import BaseModel, Field
from app.models.asset_system_info import SystemInformation

# history action
AssetAction = Literal["CREATE", "UPDATE", "DELETE", "PURGE"]


class ServerAssetBase(BaseModel):
    ip: str = Field(default='')
    name: str = Field(..., min_length=1)
    asset_id: Optional[str] = Field(default=None)  # 유형별 PK (사용자 입력, 고유)
    asset_no: Optional[str] = Field(default=None)  # 자산번호 (일반 필드, 중복 허용)
    fields: Dict[str, Any] = Field(default_factory=dict)


class ServerAssetCreate(ServerAssetBase):
    system_info: Optional[SystemInformation] = None


class McpAssetCreate(ServerAssetCreate):
    """MCP 자산 등록 요청. system_info는 서버 자산에만 사용할 수 있다."""
    category: Literal['서버', '네트워크', '정보보호시스템', 'DBMS', 'VMware']
    ip: str = Field(..., min_length=1, description='IP 주소 (필수)')
    asset_no: str = Field(..., min_length=1, description='자산번호 (필수)')
    fields: Dict[str, Any] = Field(..., description='구분, 서버명, 설명, 운영체제 필수. DBMS는 version 또는 db_series, 정보보호시스템은 제조사 추가')
    db_series: Optional[str] = Field(default=None, description='DBMS 시리즈. version이 없는 경우 사용')
    confirm_duplicate_ip: bool = Field(default=False, description='동일 유형의 IP 중복을 사용자에게 확인받은 경우에만 true')


class ServerAssetReplace(ServerAssetBase):
    pass


class ServerAssetPatch(BaseModel):
    ip: Optional[str] = None
    name: Optional[str] = None
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    version: Optional[int] = None  # optimistic lock (optional)
    system_info: Optional[SystemInformation] = None


class ServerAssetDelete(BaseModel):
    reason: Optional[str] = None


class ServerAssetOut(BaseModel):
    id: str
    ip: str
    name: str
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    fields: Dict[str, Any]
    system_info: Optional[SystemInformation] = None

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None
    delete_reason: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None


class AssetHistoryOut(BaseModel):
    id: str
    asset_id: str
    action: AssetAction
    changed_at: datetime
    changed_by: str
    source: Optional[str] = None
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None
