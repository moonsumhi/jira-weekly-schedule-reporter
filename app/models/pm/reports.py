from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════════
# 수기 항목 (Manual Items for Weekly Reports)
# ════════════════════════════════════════════════════════════════════

class ManualItemCreate(BaseModel):
    section: str  # MAIN_AGENDA | ISSUE_RISK | DECISION_REQUIRED
    title: str
    owner: Optional[str] = None
    linked_sr_id: Optional[str] = None
    linked_issue_id: Optional[str] = None
    include_in_report: bool = True
    sort_order: int = 10
    # MAIN_AGENDA 전용
    category: Optional[str] = None
    content: Optional[str] = None
    agenda_status: Optional[str] = None
    # ISSUE_RISK 전용
    item_type: Optional[str] = None
    impact: Optional[str] = None
    action_plan: Optional[str] = None
    # DECISION_REQUIRED 전용
    background: Optional[str] = None
    options: Optional[str] = None
    requested_decision: Optional[str] = None
    desired_date: Optional[datetime] = None


class ManualItemPatch(BaseModel):
    title: Optional[str] = None
    owner: Optional[str] = None
    include_in_report: Optional[bool] = None
    sort_order: Optional[int] = None
    category: Optional[str] = None
    content: Optional[str] = None
    agenda_status: Optional[str] = None
    item_type: Optional[str] = None
    impact: Optional[str] = None
    action_plan: Optional[str] = None
    background: Optional[str] = None
    options: Optional[str] = None
    requested_decision: Optional[str] = None
    desired_date: Optional[datetime] = None


class ManualItemOut(BaseModel):
    id: str
    section: str
    title: str
    owner: Optional[str] = None
    linked_sr_id: Optional[str] = None
    linked_issue_id: Optional[str] = None
    include_in_report: bool = True
    sort_order: int = 0
    category: Optional[str] = None
    content: Optional[str] = None
    agenda_status: Optional[str] = None
    item_type: Optional[str] = None
    impact: Optional[str] = None
    action_plan: Optional[str] = None
    background: Optional[str] = None
    options: Optional[str] = None
    requested_decision: Optional[str] = None
    desired_date: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: datetime


class WeeklyReportStatusPatch(BaseModel):
    status: str  # DRAFT | REVIEWING | CONFIRMED


class SrItem(BaseModel):
    sr_no: str
    title: str
    status: str
    status_label: str
    request_type: str
    request_type_label: str
    requester_name: str
    requester_department: str
    assignee_name: Optional[str] = None
    is_urgent: bool = False
    desired_due_date: Optional[datetime] = None
    created_at: datetime


class SrSummary(BaseModel):
    new_this_week: List[SrItem] = Field(default_factory=list)      # 이번 주 신규 접수
    completed_this_week: List[SrItem] = Field(default_factory=list) # 이번 주 완료
    pending_items: List[SrItem] = Field(default_factory=list)       # 미접수 (SUBMITTED)
    open_items: List[SrItem] = Field(default_factory=list)          # 처리 중 전체 (비완료·비취소)
    by_status: dict = Field(default_factory=dict)                   # 상태별 카운트
    total_open: int = 0
    total_new: int = 0
    total_completed: int = 0


class ReportStats(BaseModel):
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    delayed: int = 0
    todo: int = 0
    completion_rate: int = 0  # 정수 %


class WorkItem(BaseModel):
    issue_id: str
    issue_number: int
    title: str
    type: str
    project_id: str
    project_name: str
    org_name: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str
    priority: str
    epic_title: Optional[str] = None
    sprint_name: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    is_delayed: bool = False
    story_points: Optional[int] = None


class ProjectBreakdown(BaseModel):
    project_id: str
    project_name: str
    org_name: Optional[str] = None
    stats: ReportStats = Field(default_factory=ReportStats)
    completed: List[WorkItem] = Field(default_factory=list)
    in_progress: List[WorkItem] = Field(default_factory=list)
    delayed: List[WorkItem] = Field(default_factory=list)
    upcoming: List[WorkItem] = Field(default_factory=list)


class PersonBreakdown(BaseModel):
    user_id: str
    user_name: str
    stats: ReportStats = Field(default_factory=ReportStats)
    completed: List[WorkItem] = Field(default_factory=list)
    in_progress: List[WorkItem] = Field(default_factory=list)
    delayed: List[WorkItem] = Field(default_factory=list)
    upcoming: List[WorkItem] = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# 주간 보고
# ════════════════════════════════════════════════════════════════════

class WeeklyReportCreate(BaseModel):
    report_year: int
    report_week: int
    start_date: datetime
    end_date: datetime
    title: str
    department: Optional[str] = None
    admin_comment: Optional[str] = None


class WeeklyReportPatch(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    admin_comment: Optional[str] = None


class WeeklyReportOut(BaseModel):
    id: str
    report_year: int
    report_week: int
    start_date: datetime
    end_date: datetime
    title: str
    department: Optional[str] = None
    status: str = "DRAFT"
    by_project: List[ProjectBreakdown] = Field(default_factory=list)
    by_person: List[PersonBreakdown] = Field(default_factory=list)
    all_items: List[WorkItem] = Field(default_factory=list)
    upcoming_items: List[WorkItem] = Field(default_factory=list)
    stats: ReportStats = Field(default_factory=ReportStats)
    manual_items: List[ManualItemOut] = Field(default_factory=list)
    sr_summary: Optional[SrSummary] = None
    admin_comment: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    updated_at: datetime
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════
# 월간 보고
# ════════════════════════════════════════════════════════════════════

class MonthlyReportCreate(BaseModel):
    report_year: int
    report_month: int
    title: str
    department: Optional[str] = None
    admin_comment: Optional[str] = None


class MonthlyReportPatch(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    admin_comment: Optional[str] = None


class MonthlyReportOut(BaseModel):
    id: str
    report_year: int
    report_month: int
    title: str
    department: Optional[str] = None
    by_project: List[ProjectBreakdown] = Field(default_factory=list)
    by_person: List[PersonBreakdown] = Field(default_factory=list)
    all_items: List[WorkItem] = Field(default_factory=list)
    upcoming_items: List[WorkItem] = Field(default_factory=list)
    stats: ReportStats = Field(default_factory=ReportStats)
    admin_comment: Optional[str] = None
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    updated_at: datetime
