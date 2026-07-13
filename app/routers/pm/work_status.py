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
    issues_col = MongoClientManager.get_pm_issues_collection()

    # 날짜 파싱 (UTC 기준 하루 범위)
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        return []

    # 특정 프로젝트 필터 (선택)
    project_filter: dict = {}
    if project_id:
        project_filter = {"project_id": ObjectId(project_id)}

    # 기간 내 업데이트된 이슈 OR 기간 내 마감인 미완료 이슈 (전체 프로젝트)
    query: dict = {
        **project_filter,
        "$or": [
            {"updated_at": {"$gte": start_dt, "$lt": end_dt}},
            {
                "status": {"$ne": "DONE"},
                "due_date": {"$gte": start_dt, "$lt": end_dt},
            },
        ],
    }

    docs = await issues_col.find(query).sort([("assignee_id", 1), ("status", 1), ("order", 1)]).to_list(None)

    # 하위작업이 있는 TASK는 TASK 대신 하위작업들을 반환
    task_oids = [d["_id"] for d in docs if d.get("type") == "TASK"]
    all_subtask_docs: list = []
    tasks_with_subtasks: set = set()
    if task_oids:
        sub_docs = await issues_col.find(
            {"type": "SUB_TASK", "parent_issue_id": {"$in": task_oids}}
        ).to_list(None)
        all_subtask_docs = sub_docs
        tasks_with_subtasks = {str(d["parent_issue_id"]) for d in sub_docs}

    subtask_ids_from_fetch = {str(d["_id"]) for d in all_subtask_docs}
    result_docs = []
    for d in docs:
        if d.get("type") == "TASK" and str(d["_id"]) in tasks_with_subtasks:
            continue  # 하위작업이 있는 TASK 제외
        if d.get("type") == "SUB_TASK" and str(d["_id"]) in subtask_ids_from_fetch:
            continue  # 이미 아래에서 일괄 추가
        result_docs.append(d)
    result_docs.extend(all_subtask_docs)

    return [await enrich_issue(d) for d in result_docs]
