# app/models/inspection.py
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

# history action
InspectionAction = Literal["CREATE", "UPDATE", "DELETE"]


class InspectionChecklistBase(BaseModel):
    """서버실 점검표 기본 필드"""
    inspection_month: str = Field(..., min_length=7, description="점검 월 (YYYY-MM)")
    person_in_charge: str = Field(..., min_length=1, description="담당자")
    system_room_result: str = Field(..., min_length=1, description="시스템실 점검 결과")
    resource_usage_abnormal: bool = Field(default=False, description="자원사용량 이상 여부")
    notes: Optional[str] = Field(default=None, description="비고")


class InspectionChecklistCreate(InspectionChecklistBase):
    pass


class InspectionChecklistReplace(InspectionChecklistBase):
    pass


class InspectionChecklistPatch(BaseModel):
    inspection_month: Optional[str] = None
    person_in_charge: Optional[str] = None
    system_room_result: Optional[str] = None
    resource_usage_abnormal: Optional[bool] = None
    notes: Optional[str] = None
    version: Optional[int] = None  # optimistic lock (optional)


class InspectionChecklistOut(BaseModel):
    id: str
    inspection_month: str
    person_in_charge: str
    system_room_result: str
    resource_usage_abnormal: bool
    notes: Optional[str] = None

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class InspectionHistoryOut(BaseModel):
    id: str
    checklist_id: str
    action: InspectionAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None
