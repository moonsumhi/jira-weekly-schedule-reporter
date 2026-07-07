# app/models/assets.py
from datetime import datetime
from typing import Any, Dict, Optional, Literal, List

from pydantic import BaseModel, Field

# history action
AssetAction = Literal["CREATE", "UPDATE", "DELETE", "PURGE"]


class ServerAssetBase(BaseModel):
    ip: str = Field(default='')
    name: str = Field(..., min_length=1)
    asset_id: Optional[str] = Field(default=None)  # 유형별 PK (사용자 입력, 고유)
    asset_no: Optional[str] = Field(default=None)  # 자산번호 (일반 필드, 중복 허용)
    fields: Dict[str, Any] = Field(default_factory=dict)


class ServerAssetCreate(ServerAssetBase):
    pass


class ServerAssetReplace(ServerAssetBase):
    pass


class ServerAssetPatch(BaseModel):
    ip: Optional[str] = None
    name: Optional[str] = None
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    version: Optional[int] = None  # optimistic lock (optional)


class ServerAssetDelete(BaseModel):
    reason: Optional[str] = None


class ServerAssetOut(BaseModel):
    id: str
    ip: str
    name: str
    asset_id: Optional[str] = None
    asset_no: Optional[str] = None
    fields: Dict[str, Any]

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
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None
