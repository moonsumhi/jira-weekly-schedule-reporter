# app/models/pm/recurring_issue.py
"""반복 이슈 템플릿 — 스케줄관리 이슈를 규칙에 따라 반복 생성한다.

작업 종류(배포·점검·백업 등)는 하드코딩하지 않는다. 템플릿은 이슈 내용(blueprint)과
반복 규칙(rule)만 담는 범용 정의이며, 배경 스케줄러(자동)와 즉시 생성 버튼(수동)이
같은 로직으로 회차 이슈를 만든다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class WeekdayOccurrence(BaseModel):
    """매월 N째주 X요일 지정. (예: 첫째주 월요일 → week=1, weekday=0)"""
    week: int = Field(..., description="1~5 = 첫째~다섯째주, -1 = 마지막주")
    weekday: int = Field(..., ge=0, le=6, description="0=월 … 6=일")

    @field_validator("week")
    @classmethod
    def _valid_week(cls, v: int) -> int:
        if v not in (1, 2, 3, 4, 5, -1):
            raise ValueError(f"week 는 1~5 또는 -1(마지막)이어야 합니다: {v}")
        return v


class RecurrenceRule(BaseModel):
    """반복 규칙 — 매월, 두 가지 방식.

    mode="day_of_month" : 매월 특정일들 (days_of_month, 예: [5, 19])
    mode="weekday"      : 매월 N째주 X요일들 (weekdays, 예: 첫째주 월요일)
    """
    freq: Literal["monthly"] = "monthly"
    mode: Literal["day_of_month", "weekday"] = "day_of_month"
    days_of_month: List[int] = Field(default_factory=list, description="매월 회차일 (mode=day_of_month)")
    weekdays: List[WeekdayOccurrence] = Field(default_factory=list, description="N째주 X요일 (mode=weekday)")
    time: str = Field(default="09:00", description="회차 시각 HH:MM (start/due 시간)")

    @field_validator("days_of_month")
    @classmethod
    def _valid_days(cls, v: List[int]) -> List[int]:
        for d in v:
            if not (1 <= d <= 31):
                raise ValueError(f"days_of_month 값은 1~31 이어야 합니다: {d}")
        return sorted(set(v))

    @field_validator("time")
    @classmethod
    def _valid_time(cls, v: str) -> str:
        try:
            hh, mm = v.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
        except Exception:
            raise ValueError(f"time 은 HH:MM 형식이어야 합니다: {v}")
        return v

    @model_validator(mode="after")
    def _require_one(self) -> "RecurrenceRule":
        if self.mode == "day_of_month" and not self.days_of_month:
            raise ValueError("mode=day_of_month 이면 days_of_month 가 최소 1개 필요합니다.")
        if self.mode == "weekday" and not self.weekdays:
            raise ValueError("mode=weekday 이면 weekdays 가 최소 1개 필요합니다.")
        return self


class IssueBlueprint(BaseModel):
    """생성할 이슈의 공통 내용 (title 은 베이스, 회차 라벨이 뒤에 붙는다)."""
    title: str = Field(..., min_length=1, description="이슈 제목 베이스")
    description: Optional[str] = None
    type: str = "TASK"
    priority: str = "MEDIUM"
    assignee_id: Optional[str] = None
    label_ids: List[str] = Field(default_factory=list)
    story_points: Optional[int] = Field(default=None, ge=0, le=999)
    effort_md: Optional[str] = None
    show_on_dashboard: bool = False


class RecurringIssueTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, description="반복 업무 이름")
    project_id: str = Field(..., description="이슈를 생성할 프로젝트")
    blueprint: IssueBlueprint
    rule: RecurrenceRule
    lead_days: int = Field(default=0, ge=0, le=60, description="작업일 며칠 전에 미리 생성(0=당일)")
    auto_enabled: bool = Field(default=True, description="배경 스케줄러 자동 생성 on/off")
    active: bool = True


class RecurringIssueTemplateCreate(RecurringIssueTemplateBase):
    pass


class RecurringIssueTemplatePatch(BaseModel):
    name: Optional[str] = None
    blueprint: Optional[IssueBlueprint] = None
    rule: Optional[RecurrenceRule] = None
    lead_days: Optional[int] = Field(default=None, ge=0, le=60)
    auto_enabled: Optional[bool] = None
    active: Optional[bool] = None


class RecurringIssueTemplateOut(RecurringIssueTemplateBase):
    id: str
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class OccurrenceOut(BaseModel):
    """회차 하나 (미리보기/생성 결과용)."""
    occurrence_date: str            # YYYY-MM-DD
    round_label: str                # "8월 2차"
    title: str                      # "{베이스} - 8월 2차"
    issue_id: Optional[str] = None  # 생성됐으면 이슈 id
    already_exists: bool = False    # 이미 있어서 건너뜀


class GenerateResult(BaseModel):
    created: List[OccurrenceOut] = Field(default_factory=list)
    skipped: List[OccurrenceOut] = Field(default_factory=list)
