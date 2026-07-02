from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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
