from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.issue import IssueOut
from app.routers.auth import get_current_user
from app.services.pm.issue_service import enrich_issue

router = APIRouter()


@router.get("/work-status", response_model=List[IssueOut])
async def get_work_status(
    start_date: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    project_id: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
):
    """기간 내 업데이트된 이슈 또는 마감 예정 미완료 이슈 조회 (크로스 프로젝트)."""
    uid = ObjectId(current_user.id)
    issues_col = MongoClientManager.get_pm_issues_collection()
    members_col = MongoClientManager.get_pm_project_members_collection()

    # 사용자가 속한 프로젝트 목록
    memberships = await members_col.find({"user_id": uid}).to_list(None)
    all_project_ids = [m["project_id"] for m in memberships]

    if not all_project_ids:
        return []

    # 특정 프로젝트 필터
    if project_id:
        pid = ObjectId(project_id)
        if pid not in all_project_ids:
            return []
        project_ids = [pid]
    else:
        project_ids = all_project_ids

    # 날짜 파싱 (UTC 기준 하루 범위)
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        return []

    # 기간 내 업데이트된 이슈 OR 기간 내 마감인 미완료 이슈
    query: dict = {
        "project_id": {"$in": project_ids},
        "$or": [
            {"updated_at": {"$gte": start_dt, "$lt": end_dt}},
            {
                "status": {"$ne": "DONE"},
                "due_date": {"$gte": start_dt, "$lt": end_dt},
            },
        ],
    }

    docs = await issues_col.find(query).sort([("assignee_id", 1), ("status", 1), ("order", 1)]).to_list(None)
    return [await enrich_issue(d) for d in docs]
