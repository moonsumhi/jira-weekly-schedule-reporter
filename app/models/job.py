# app/models/job.py
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

# 작업 구분
JobCategory = Literal["정기", "긴급", "임시"]

# 작업 상태
JobStatus = Literal["초안", "승인대기", "승인됨", "완료", "취소"]

# 이력 액션
JobAction = Literal["CREATE", "UPDATE", "DELETE"]

# 작업 결과
JobOutcome = Literal["성공", "부분성공", "실패"]


class JobWorkStep(BaseModel):
    """작업 절차 단계"""
    order: int = Field(..., description="순서")
    task: str = Field(..., min_length=1, description="작업 내용")
    person: str = Field(..., min_length=1, description="담당자")
    duration: Optional[str] = Field(default=None, description="예상 소요 시간")


class ServiceWorkPlanBase(BaseModel):
    """작업계획서(서비스) 기본 필드"""
    # 기본 정보
    title: str = Field(..., min_length=1, description="작업명")
    work_date: str = Field(..., description="작업 일시 (YYYY-MM-DD HH:MM)")
    worker: str = Field(..., min_length=1, description="작업자")
    requester: str = Field(..., min_length=1, description="신청자")
    system_name: str = Field(..., min_length=1, description="시스템명")
    category: JobCategory = Field(default="정기", description="작업 구분")

    # 작업 내용
    purpose: str = Field(..., min_length=1, description="작업 목적")
    scope: str = Field(..., min_length=1, description="작업 범위")
    detail: str = Field(..., min_length=1, description="작업 상세 내용")

    # 영향도 분석
    service_affected: bool = Field(default=False, description="서비스 영향 여부")
    downtime: Optional[str] = Field(default=None, description="서비스 중단 시간")
    impact_scope: Optional[str] = Field(default=None, description="영향 범위")

    # 사전 준비
    backup_done: bool = Field(default=False, description="백업 여부")
    backup_details: Optional[str] = Field(default=None, description="백업 내용")

    # 작업 절차
    steps: List[JobWorkStep] = Field(default_factory=list, description="작업 절차")

    # 롤백 계획
    rollback_possible: bool = Field(default=True, description="롤백 가능 여부")
    rollback_steps: Optional[str] = Field(default=None, description="롤백 절차")
    rollback_duration: Optional[str] = Field(default=None, description="롤백 소요 시간")

    # 결과 (작업 완료 후 기록)
    result_notes: Optional[str] = Field(default=None, description="작업 결과 특이 사항")

    # 작업 결과 상세
    work_summary: Optional[str] = Field(default=None, description="수행 작업 요약")
    outcome: Optional[JobOutcome] = Field(default=None, description="작업 결과")
    issues_found: Optional[str] = Field(default=None, description="발생 문제")
    resolution: Optional[str] = Field(default=None, description="조치 내용")


class ServiceWorkPlanCreate(ServiceWorkPlanBase):
    pass


class ServiceWorkPlanPatch(BaseModel):
    title: Optional[str] = None
    work_date: Optional[str] = None
    worker: Optional[str] = None
    requester: Optional[str] = None
    system_name: Optional[str] = None
    category: Optional[JobCategory] = None
    purpose: Optional[str] = None
    scope: Optional[str] = None
    detail: Optional[str] = None
    service_affected: Optional[bool] = None
    downtime: Optional[str] = None
    impact_scope: Optional[str] = None
    backup_done: Optional[bool] = None
    backup_details: Optional[str] = None
    steps: Optional[List[JobWorkStep]] = None
    rollback_possible: Optional[bool] = None
    rollback_steps: Optional[str] = None
    rollback_duration: Optional[str] = None
    status: Optional[JobStatus] = None
    result_notes: Optional[str] = None
    work_summary: Optional[str] = None
    outcome: Optional[JobOutcome] = None
    issues_found: Optional[str] = None
    resolution: Optional[str] = None
    version: Optional[int] = None


class ServiceWorkPlanOut(BaseModel):
    id: str
    title: str
    work_date: str
    worker: str
    requester: str
    system_name: str
    category: JobCategory
    purpose: str
    scope: str
    detail: str
    service_affected: bool
    downtime: Optional[str] = None
    impact_scope: Optional[str] = None
    backup_done: bool
    backup_details: Optional[str] = None
    steps: List[JobWorkStep] = Field(default_factory=list)
    rollback_possible: bool
    rollback_steps: Optional[str] = None
    rollback_duration: Optional[str] = None
    status: JobStatus = "초안"
    result_notes: Optional[str] = None
    work_summary: Optional[str] = None
    outcome: Optional[JobOutcome] = None
    issues_found: Optional[str] = None
    resolution: Optional[str] = None

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class ServiceWorkPlanHistoryOut(BaseModel):
    id: str
    plan_id: str
    action: JobAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None


class NonServiceWorkPlanBase(BaseModel):
    """작업계획서(비서비스) 기본 필드"""
    title: str = Field(..., min_length=1, description="작업명")
    work_date: str = Field(..., description="작업 일시 (YYYY-MM-DD HH:MM)")
    worker: str = Field(..., min_length=1, description="작업자")
    requester: str = Field(..., min_length=1, description="신청자")
    system_name: str = Field(..., min_length=1, description="시스템명")
    category: JobCategory = Field(default="정기", description="작업 구분")
    purpose: str = Field(..., min_length=1, description="작업 목적")
    scope: str = Field(..., min_length=1, description="작업 범위")
    detail: str = Field(..., min_length=1, description="작업 상세 내용")
    backup_done: bool = Field(default=False, description="백업 여부")
    backup_details: Optional[str] = Field(default=None, description="백업 내용")
    steps: List[JobWorkStep] = Field(default_factory=list, description="작업 절차")
    rollback_possible: bool = Field(default=True, description="롤백 가능 여부")
    rollback_steps: Optional[str] = Field(default=None, description="롤백 절차")
    rollback_duration: Optional[str] = Field(default=None, description="롤백 소요 시간")
    result_notes: Optional[str] = Field(default=None, description="작업 결과 특이 사항")


class NonServiceWorkPlanCreate(NonServiceWorkPlanBase):
    pass


class NonServiceWorkPlanPatch(BaseModel):
    title: Optional[str] = None
    work_date: Optional[str] = None
    worker: Optional[str] = None
    requester: Optional[str] = None
    system_name: Optional[str] = None
    category: Optional[JobCategory] = None
    purpose: Optional[str] = None
    scope: Optional[str] = None
    detail: Optional[str] = None
    backup_done: Optional[bool] = None
    backup_details: Optional[str] = None
    steps: Optional[List[JobWorkStep]] = None
    rollback_possible: Optional[bool] = None
    rollback_steps: Optional[str] = None
    rollback_duration: Optional[str] = None
    status: Optional[JobStatus] = None
    result_notes: Optional[str] = None
    version: Optional[int] = None


class NonServiceWorkPlanOut(BaseModel):
    id: str
    title: str
    work_date: str
    worker: str
    requester: str
    system_name: str
    category: JobCategory
    purpose: str
    scope: str
    detail: str
    backup_done: bool
    backup_details: Optional[str] = None
    steps: List[JobWorkStep] = Field(default_factory=list)
    rollback_possible: bool
    rollback_steps: Optional[str] = None
    rollback_duration: Optional[str] = None
    status: JobStatus = "초안"
    result_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class NonServiceWorkPlanHistoryOut(BaseModel):
    id: str
    plan_id: str
    action: JobAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None


class JobWorkStepResult(BaseModel):
    """작업 결과 단계"""
    order: int = Field(..., description="순서")
    task: str = Field(..., min_length=1, description="작업 내용")
    person: str = Field(..., min_length=1, description="담당자")
    completed: bool = Field(default=True, description="완료 여부")
    notes: Optional[str] = Field(default=None, description="비고")


class ServiceWorkResultBase(BaseModel):
    """작업 결과서 기본 필드"""
    title: str = Field(..., min_length=1, description="작업명")
    work_date: str = Field(..., description="작업 일시 (YYYY-MM-DD HH:MM)")
    worker: str = Field(..., min_length=1, description="작업자")
    requester: str = Field(..., min_length=1, description="신청자")
    system_name: str = Field(..., min_length=1, description="시스템명")
    category: JobCategory = Field(default="정기", description="작업 구분")
    result: JobOutcome = Field(..., description="작업 결과")
    actual_start_time: Optional[str] = Field(default=None, description="실제 시작 시간")
    actual_end_time: Optional[str] = Field(default=None, description="실제 종료 시간")
    summary: str = Field(..., min_length=1, description="작업 요약")
    service_affected: bool = Field(default=False, description="서비스 영향 여부")
    actual_downtime: Optional[str] = Field(default=None, description="실제 중단 시간")
    step_results: List[JobWorkStepResult] = Field(default_factory=list, description="작업 절차 결과")
    issues_occurred: bool = Field(default=False, description="문제 발생 여부")
    issue_details: Optional[str] = Field(default=None, description="문제 내용")
    action_taken: Optional[str] = Field(default=None, description="조치 내용")
    post_check_done: bool = Field(default=False, description="사후 점검 여부")
    post_check_details: Optional[str] = Field(default=None, description="사후 점검 내용")
    plan_id: Optional[str] = Field(default=None, description="연관 작업계획서 ID")
    notes: Optional[str] = Field(default=None, description="비고")


class ServiceWorkResultCreate(ServiceWorkResultBase):
    pass


class ServiceWorkResultPatch(BaseModel):
    title: Optional[str] = None
    work_date: Optional[str] = None
    worker: Optional[str] = None
    requester: Optional[str] = None
    system_name: Optional[str] = None
    category: Optional[JobCategory] = None
    result: Optional[JobOutcome] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    summary: Optional[str] = None
    service_affected: Optional[bool] = None
    actual_downtime: Optional[str] = None
    step_results: Optional[List[JobWorkStepResult]] = None
    issues_occurred: Optional[bool] = None
    issue_details: Optional[str] = None
    action_taken: Optional[str] = None
    post_check_done: Optional[bool] = None
    post_check_details: Optional[str] = None
    plan_id: Optional[str] = None
    notes: Optional[str] = None
    version: Optional[int] = None


class ServiceWorkResultOut(BaseModel):
    id: str
    title: str
    work_date: str
    worker: str
    requester: str
    system_name: str
    category: JobCategory
    result: JobOutcome
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    summary: str
    service_affected: bool
    actual_downtime: Optional[str] = None
    step_results: List[JobWorkStepResult] = Field(default_factory=list)
    issues_occurred: bool
    issue_details: Optional[str] = None
    action_taken: Optional[str] = None
    post_check_done: bool
    post_check_details: Optional[str] = None
    plan_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class ServiceWorkResultHistoryOut(BaseModel):
    id: str
    result_id: str
    action: JobAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None


class JobResultBase(BaseModel):
    """작업 결과서(간소) 기본 필드"""
    title: str = Field(..., min_length=1, description="작업명")
    work_date: str = Field(..., description="작업 일시 (YYYY-MM-DD HH:MM)")
    worker: str = Field(..., min_length=1, description="작업자")
    requester: str = Field(..., min_length=1, description="신청자")
    system_name: str = Field(..., min_length=1, description="시스템명")
    category: JobCategory = Field(default="정기", description="작업 구분")
    work_summary: str = Field(..., min_length=1, description="수행 작업 요약")
    issues_found: Optional[str] = Field(default=None, description="발생 문제")
    resolution: Optional[str] = Field(default=None, description="조치 내용")
    service_impact_actual: Optional[str] = Field(default=None, description="실제 서비스 영향")
    outcome: JobOutcome = Field(default="성공", description="작업 결과")
    next_steps: Optional[str] = Field(default=None, description="후속 조치")
    related_plan_id: Optional[str] = Field(default=None, description="연관 작업계획서 ID")


class JobResultCreate(JobResultBase):
    pass


class JobResultPatch(BaseModel):
    title: Optional[str] = None
    work_date: Optional[str] = None
    worker: Optional[str] = None
    requester: Optional[str] = None
    system_name: Optional[str] = None
    category: Optional[JobCategory] = None
    work_summary: Optional[str] = None
    issues_found: Optional[str] = None
    resolution: Optional[str] = None
    service_impact_actual: Optional[str] = None
    outcome: Optional[JobOutcome] = None
    next_steps: Optional[str] = None
    related_plan_id: Optional[str] = None
    status: Optional[JobStatus] = None
    version: Optional[int] = None


class JobResultOut(BaseModel):
    id: str
    title: str
    work_date: str
    worker: str
    requester: str
    system_name: str
    category: JobCategory
    work_summary: str
    issues_found: Optional[str] = None
    resolution: Optional[str] = None
    service_impact_actual: Optional[str] = None
    outcome: JobOutcome = "성공"
    next_steps: Optional[str] = None
    related_plan_id: Optional[str] = None
    status: JobStatus = "초안"
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    version: Optional[int] = None
    is_deleted: Optional[bool] = None


class JobResultHistoryOut(BaseModel):
    id: str
    plan_id: str
    action: JobAction
    changed_at: datetime
    changed_by: str
    patch: Optional[Dict[str, Any]] = None
    diff: Optional[List[dict]] = None
