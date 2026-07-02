from __future__ import annotations

from typing import Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.issue import IssueOut, ISSUE_STATUS_ORDER
from app.routers.auth import get_current_user
from app.services.pm.issue_service import enrich_issue

router = APIRouter()


@router.get("/{project_id}/board")
async def get_board(
    project_id: str,
    sprint_id: Optional[str] = Query(None),
    current_user: UserPublic = Depends(get_current_user),
) -> Dict[str, List[IssueOut]]:
    """칸반 보드: 상태별로 그룹핑된 이슈 반환."""
    col = MongoClientManager.get_pm_issues_collection()

    query: dict = {"project_id": ObjectId(project_id), "type": "TASK"}
    if sprint_id:
        query["sprint_id"] = ObjectId(sprint_id)
    else:
        # 스프린트 미지정 시 백로그 제외한 활성 이슈
        query["status"] = {"$ne": "BACKLOG"}

    docs = await col.find(query).sort("order", 1).to_list(None)
    enriched = [await enrich_issue(d) for d in docs]

    board: Dict[str, List] = {s: [] for s in ISSUE_STATUS_ORDER}
    for issue in enriched:
        board[issue["status"]].append(issue)

    return board
