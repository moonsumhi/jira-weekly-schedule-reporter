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

    docs = await col.find(query).sort("order", 1).to_list(None)
    enriched = [await enrich_issue(d) for d in docs]

    # 하위작업 batch 조회
    task_oids = [ObjectId(issue["id"]) for issue in enriched]
    subtask_map: Dict[str, List] = {}
    if task_oids:
        users_col = MongoClientManager.get_users_collection()
        sub_docs = await col.find({
            "project_id": ObjectId(project_id),
            "type": "SUB_TASK",
            "parent_issue_id": {"$in": task_oids},
        }).sort("order", 1).to_list(None)

        # 담당자 이름 batch 조회
        assignee_ids = list({d["assignee_id"] for d in sub_docs if d.get("assignee_id")})
        user_map: Dict[str, str] = {}
        if assignee_ids:
            async for u in users_col.find({"_id": {"$in": assignee_ids}}, {"full_name": 1, "email": 1}):
                user_map[str(u["_id"])] = u.get("full_name") or u.get("email", "")

        for d in sub_docs:
            parent_id = str(d["parent_issue_id"])
            subtask_map.setdefault(parent_id, []).append({
                "id": str(d["_id"]),
                "number": d["number"],
                "title": d["title"],
                "status": d["status"],
                "priority": d["priority"],
                "assignee_name": user_map.get(str(d["assignee_id"])) if d.get("assignee_id") else None,
            })

    for issue in enriched:
        issue["subtasks"] = subtask_map.get(issue["id"], [])

    board: Dict[str, List] = {s: [] for s in ISSUE_STATUS_ORDER}
    for issue in enriched:
        board[issue["status"]].append(issue)

    return board
