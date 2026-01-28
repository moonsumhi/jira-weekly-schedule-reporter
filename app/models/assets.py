# app/models/assets.py
from datetime import datetime
from typing import Any, Dict, Optional, Literal, List

from pydantic import BaseModel, Field

# history action
AssetAction = Literal["CREATE", "UPDATE", "DELETE"]


class ServerAssetBase(BaseModel):
    ip: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    fields: Dict[str, Any] = Field(default_factory=dict)


class ServerAssetCreate(ServerAssetBase):
    pass


class ServerAssetReplace(ServerAssetBase):
    pass


class ServerAssetPatch(BaseModel):
    ip: Optional[str] = None
    name: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    version: Optional[int] = None  # optimistic lock (optional)


class ServerAssetOut(BaseModel):
    id: str
    ip: str
    name: str
    fields: Dict[str, Any]

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class AssetHistoryOut(BaseModel):
    id: str
    asset_id: str
    action: AssetAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None
