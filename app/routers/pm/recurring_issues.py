# app/routers/pm/recurring_issues.py
"""반복 이슈 템플릿 API — 스케줄관리 이슈를 규칙에 따라 반복 생성.

- CRUD: 반복 업무 정의 관리
- POST /{id}/generate?year=&month= : 해당 월 회차 즉시 생성(수동 버튼)
- GET  /{id}/preview?year=&month=  : 회차 미리보기(생성 안 함)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.user import UserPublic
from app.models.pm.recurring_issue import (
    RecurringIssueTemplateCreate,
    RecurringIssueTemplatePatch,
    RecurringIssueTemplateOut,
    OccurrenceOut,
    GenerateResult,
)
from app.routers.auth import get_current_user
from app.services.pm.permission import require_pm_member
from app.services.pm import recurring_issue_service as svc

router = APIRouter()


@router.get("", response_model=List[RecurringIssueTemplateOut])
async def list_recurring_templates(
    project_id: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    if project_id:
        await require_pm_member(current_user, project_id)
    return await svc.list_templates(project_id)


@router.post("", response_model=RecurringIssueTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_recurring_template(
    body: RecurringIssueTemplateCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_member(current_user, body.project_id)
    return await svc.create_template(body.model_dump(), actor_email=current_user.email)


async def _load_or_404(template_id: str) -> dict:
    tpl = await svc.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="반복 템플릿을 찾을 수 없습니다.")
    return tpl


@router.get("/{template_id}", response_model=RecurringIssueTemplateOut)
async def get_recurring_template(
    template_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    tpl = await _load_or_404(template_id)
    await require_pm_member(current_user, str(tpl["project_id"]))
    return svc.to_out(tpl)


@router.patch("/{template_id}", response_model=RecurringIssueTemplateOut)
async def patch_recurring_template(
    template_id: str,
    body: RecurringIssueTemplatePatch,
    current_user: UserPublic = Depends(get_current_user),
):
    tpl = await _load_or_404(template_id)
    await require_pm_member(current_user, str(tpl["project_id"]))
    updated = await svc.patch_template(template_id, body.model_dump(), actor_email=current_user.email)
    return updated


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_template(
    template_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    tpl = await _load_or_404(template_id)
    await require_pm_member(current_user, str(tpl["project_id"]))
    await svc.delete_template(template_id)


def _default_year_month(year: Optional[int], month: Optional[int]) -> tuple[int, int]:
    now = datetime.now()
    return (year or now.year, month or now.month)


@router.get("/{template_id}/preview", response_model=List[OccurrenceOut])
async def preview_occurrences(
    template_id: str,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    current_user: UserPublic = Depends(get_current_user),
):
    tpl = await _load_or_404(template_id)
    await require_pm_member(current_user, str(tpl["project_id"]))
    y, m = _default_year_month(year, month)
    occs = svc.compute_occurrences(tpl, y, m)
    out: List[OccurrenceOut] = []
    for occ in occs:
        existing = await svc._existing_issue(tpl["_id"], occ["occurrence_date"])
        out.append(OccurrenceOut(
            occurrence_date=occ["occurrence_date"],
            round_label=occ["round_label"],
            title=occ["title"],
            issue_id=str(existing["_id"]) if existing else None,
            already_exists=bool(existing),
        ))
    return out


@router.post("/{template_id}/generate", response_model=GenerateResult)
async def generate_occurrences(
    template_id: str,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    current_user: UserPublic = Depends(get_current_user),
):
    tpl = await _load_or_404(template_id)
    await require_pm_member(current_user, str(tpl["project_id"]))
    y, m = _default_year_month(year, month)
    result = await svc.generate_month(tpl, y, m, actor_id=current_user.id)
    return GenerateResult(
        created=[OccurrenceOut(**x) for x in result["created"]],
        skipped=[OccurrenceOut(**x) for x in result["skipped"]],
    )
