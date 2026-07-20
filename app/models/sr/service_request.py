from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.mention import MentionedUser

# ── 타입 정의 ─────────────────────────────────────────────────────────

SRStatus = Literal[
    "DRAFT",        # 임시저장
    "SUBMITTED",    # 접수
    "REVIEWING",    # 검토 중
    "PENDING_INFO", # 추가 확인 요청
    "REJECTED",     # 반려
    "APPROVED",     # 승인
    "ASSIGNED",     # 담당자 배정
    "IN_PROGRESS",  # 처리 중
    "COMPLETED",    # 처리 완료
    "CONFIRMING",   # 요청자 확인 중
    "CLOSED",       # 최종 완료
    "ON_HOLD",      # 보류
    "CANCELLED",    # 취소
]

SR_STATUS_LABEL: Dict[str, str] = {
    "DRAFT": "임시저장",
    "SUBMITTED": "접수",
    "REVIEWING": "검토 중",
    "PENDING_INFO": "추가 확인 요청",
    "REJECTED": "반려",
    "APPROVED": "승인",
    "ASSIGNED": "담당자 배정",
    "IN_PROGRESS": "처리 중",
    "COMPLETED": "처리 완료",
    "CONFIRMING": "요청자 확인 중",
    "CLOSED": "최종 완료",
    "ON_HOLD": "보류",
    "CANCELLED": "취소",
}

RequestType = Literal[
    "IMPROVEMENT",   # 기능 개선 요청
    "BUG_FIX",       # 오류 수정 요청
    "DATA_REQUEST",  # 데이터 요청
    "PERMISSION",    # 권한 요청
    "CONFIG_CHANGE", # 설정 변경 요청
    "SERVER_INFRA",  # 서버/인프라 요청
    "SECURITY",      # 보안 조치 요청
    "FIREWALL",      # 방화벽 신청
    "ETC",           # 기타
]

REQUEST_TYPE_LABEL: Dict[str, str] = {
    "IMPROVEMENT": "기능 개선 요청",
    "BUG_FIX": "오류 수정 요청",
    "DATA_REQUEST": "데이터 요청",
    "PERMISSION": "권한 요청",
    "CONFIG_CHANGE": "설정 변경 요청",
    "SERVER_INFRA": "서버/인프라 요청",
    "SECURITY": "보안 조치 요청",
    "FIREWALL": "방화벽 신청",
    "ETC": "기타",
}

ImpactScope = Literal["PERSONAL", "DEPARTMENT", "ALL_USERS", "EXTERNAL_USERS", "EXTERNAL_SERVICE"]

IMPACT_SCOPE_LABEL: Dict[str, str] = {
    "PERSONAL": "개인",
    "DEPARTMENT": "부서",
    "ALL_USERS": "전체 사용자",
    "EXTERNAL_USERS": "외부 사용자",
    "EXTERNAL_SERVICE": "대외 서비스",
}

SRPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

SR_PRIORITY_LABEL: Dict[str, str] = {
    "CRITICAL": "긴급",
    "HIGH": "높음",
    "MEDIUM": "보통",
    "LOW": "낮음",
}

ReviewResult = Literal["APPROVED", "REJECTED", "ON_HOLD", "PENDING_INFO"]

# ── 첨부파일 ──────────────────────────────────────────────────────────

class SRAttachment(BaseModel):
    file_id: str
    original_name: str
    url: str
    size: int
    content_type: str

# ── 요청자용 입력 모델 ─────────────────────────────────────────────────

class SRCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    requester_name: str
    requester_department: str
    requester_email: str
    request_type: RequestType
    related_system: Optional[str] = None
    related_menu: Optional[str] = None
    related_url: Optional[str] = None
    background: Optional[str] = None
    description: Optional[str] = Field(None, min_length=1)
    purpose: Optional[str] = None
    desired_due_date: datetime
    desired_deploy_date: Optional[datetime] = None
    is_urgent: bool = False
    urgent_reason: Optional[str] = None
    impact_scope: Optional[ImpactScope] = None
    priority: SRPriority = "MEDIUM"
    impact_if_not_processed: Optional[str] = None
    compliance_related: bool = False
    completion_criteria: Optional[str] = None
    reviewer_name: Optional[str] = None
    note: Optional[str] = None
    attachments: List[SRAttachment] = []
    type_detail: Optional[Dict[str, Any]] = None  # 요청 유형별 추가 입력 항목
    submit: bool = False  # True=접수, False=임시저장


class SRPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    requester_name: Optional[str] = None
    requester_department: Optional[str] = None
    requester_email: Optional[str] = None
    request_type: Optional[RequestType] = None
    related_system: Optional[str] = None
    related_menu: Optional[str] = None
    related_url: Optional[str] = None
    background: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    desired_due_date: Optional[datetime] = None
    desired_deploy_date: Optional[datetime] = None
    is_urgent: Optional[bool] = None
    urgent_reason: Optional[str] = None
    impact_scope: Optional[ImpactScope] = None
    priority: Optional[SRPriority] = None
    impact_if_not_processed: Optional[str] = None
    compliance_related: Optional[bool] = None
    completion_criteria: Optional[str] = None
    reviewer_name: Optional[str] = None
    note: Optional[str] = None
    attachments: Optional[List[SRAttachment]] = None
    type_detail: Optional[Dict[str, Any]] = None
    submit: Optional[bool] = None


# ── 관리자/담당자용 입력 모델 ──────────────────────────────────────────

class SRReview(BaseModel):
    result: ReviewResult
    comment: Optional[str] = None
    reject_reason: Optional[str] = None
    hold_reason: Optional[str] = None
    pending_info_content: Optional[str] = None
    related_project_id: Optional[str] = None
    related_issue_id: Optional[str] = None


class SRAssign(BaseModel):
    assignee_id: str
    assignee_name: str
    planned_start_date: Optional[datetime] = None
    planned_due_date: Optional[datetime] = None
    estimated_effort: Optional[str] = None
    deployment_required: bool = False
    security_review_required: bool = False


class SRStatusChange(BaseModel):
    status: SRStatus
    reason: Optional[str] = None
    process_result: Optional[str] = None
    deployed: Optional[bool] = None
    deployed_at: Optional[datetime] = None
    actual_completed_at: Optional[datetime] = None
    requester_confirmed: Optional[bool] = None
    actual_effort_md: Optional[float] = Field(None, ge=0)  # 작업자 실제 공수(MD)


class SRDueDateChange(BaseModel):
    """운영팀 완료목표일 변경 (manager 이상)."""
    planned_due_date: datetime
    change_reason: Optional[str] = None


class SREffortUpdate(BaseModel):
    """작업자 실제 공수(MD) 입력/수정."""
    actual_effort_md: float = Field(..., ge=0)


class SRComment(BaseModel):
    content: str = Field(default="")
    is_internal: bool = False
    attachments: List[SRAttachment] = []
    mentioned_user_ids: List[str] = []

    @model_validator(mode="after")
    def content_or_attachments_required(self) -> "SRComment":
        if not self.content.strip() and not self.attachments:
            raise ValueError("댓글 내용 또는 첨부파일이 필요합니다.")
        return self


# ── 출력 모델 ─────────────────────────────────────────────────────────

class SROut(BaseModel):
    id: str
    sr_no: str
    title: str
    status: SRStatus
    request_type: RequestType
    requester_id: str
    requester_name: str
    requester_department: str
    requester_email: str
    related_system: Optional[str] = None
    related_menu: Optional[str] = None
    related_url: Optional[str] = None
    background: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    desired_due_date: Optional[datetime] = None
    desired_deploy_date: Optional[datetime] = None
    is_urgent: bool
    urgent_reason: Optional[str] = None
    impact_scope: Optional[ImpactScope] = None
    priority: SRPriority
    impact_if_not_processed: Optional[str] = None
    compliance_related: bool
    completion_criteria: Optional[str] = None
    reviewer_name: Optional[str] = None
    note: Optional[str] = None
    attachments: List[SRAttachment] = []
    # 검토 정보
    review_result: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_user_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    reject_reason: Optional[str] = None
    hold_reason: Optional[str] = None
    pending_info_content: Optional[str] = None
    # 처리 정보
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    planned_start_date: Optional[datetime] = None
    planned_due_date: Optional[datetime] = None
    actual_completed_at: Optional[datetime] = None
    is_delayed: bool = False
    process_result: Optional[str] = None
    deployed: bool = False
    deployed_at: Optional[datetime] = None
    requester_confirmed: bool = False
    # 연결 정보
    related_project_id: Optional[str] = None
    related_issue_id: Optional[str] = None
    converted_issue_id: Optional[str] = None
    converted_task_id: Optional[str] = None
    converted_project_id: Optional[str] = None
    converted_issue_number: Optional[int] = None
    converted_issue_status: Optional[str] = None
    estimated_effort: Optional[str] = None
    actual_effort_md: Optional[float] = None
    deployment_required: bool = False
    security_review_required: bool = False
    # 유형별 추가 항목
    type_detail: Optional[Dict[str, Any]] = None
    # 메타
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    deleted_at: Optional[datetime] = None


class SRListItem(BaseModel):
    """목록 조회용 경량 출력 모델"""
    id: str
    sr_no: str
    title: str
    status: SRStatus
    request_type: RequestType
    requester_id: str
    requester_name: str
    requester_department: str
    related_system: Optional[str] = None
    priority: SRPriority
    is_urgent: bool
    desired_due_date: Optional[datetime] = None
    planned_due_date: Optional[datetime] = None
    actual_completed_at: Optional[datetime] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    is_delayed: bool = False
    # 연동 태스크 정보
    converted_issue_id: Optional[str] = None
    converted_project_id: Optional[str] = None
    converted_issue_number: Optional[int] = None
    converted_issue_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SRCommentOut(BaseModel):
    id: str
    sr_id: str
    writer_id: str
    writer_name: str
    content: str
    is_internal: bool
    attachments: List[SRAttachment] = []
    mentioned_users: List[MentionedUser] = []
    created_at: datetime
    updated_at: datetime


class SRHistoryOut(BaseModel):
    id: str
    sr_id: str
    action_type: str
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    changed_by: str
    changed_at: datetime


class SRListPage(BaseModel):
    items: List[SRListItem]
    total: int


class SRInlinePatch(BaseModel):
    """목록에서 인라인 편집 가능한 필드만."""
    priority:         Optional[SRPriority] = None
    desired_due_date: Optional[datetime]   = None
    assignee_id:      Optional[str]        = None
    assignee_name:    Optional[str]        = None


class SRStats(BaseModel):
    total: int
    submitted: int
    in_progress: int
    completed: int
    rejected: int
    on_hold: int
    delayed: int
    cancelled: int
    urgent_count: int
    by_type: Dict[str, int] = {}
    by_department: Dict[str, int] = {}
    by_system: Dict[str, int] = {}
    by_assignee: Dict[str, int] = {}
    avg_processing_days: Optional[float] = None
    on_time_rate: Optional[float] = None
