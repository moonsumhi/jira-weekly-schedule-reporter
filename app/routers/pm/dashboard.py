from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services.pm.issue_service import enrich_issue

router = APIRouter()


@router.get("")
async def get_dashboard(current_user: UserPublic = Depends(get_current_user)):
    """대시보드: 내 이슈 요약 및 프로젝트별 진행 현황."""
    uid = ObjectId(current_user.id)
    issues_col = MongoClientManager.get_pm_issues_collection()
    members_col = MongoClientManager.get_pm_project_members_collection()
    projects_col = MongoClientManager.get_pm_projects_collection()

    # 내 프로젝트 목록
    memberships = await members_col.find({"user_id": uid}).to_list(None)
    project_ids = [m["project_id"] for m in memberships]

    # 내 담당 이슈 (완료 제외)
    my_issues_docs = await issues_col.find({
        "assignee_id": uid,
        "status": {"$ne": "DONE"},
    }).sort("updated_at", -1).limit(50).to_list(None)
    my_issues = [await enrich_issue(d) for d in my_issues_docs]

    # 내가 만든 이슈 (담당 이슈와 중복 제거, 완료 제외)
    my_issue_ids = {d["id"] for d in my_issues}
    reported_docs = await issues_col.find({
        "reporter_id": uid,
        "status": {"$ne": "DONE"},
    }).sort("updated_at", -1).limit(50).to_list(None)
    reported_issues = [
        await enrich_issue(d) for d in reported_docs
        if str(d["_id"]) not in my_issue_ids
    ]

    # 프로젝트별 상태 통계
    project_stats = []
    for pid in project_ids:
        project = await projects_col.find_one({"_id": pid}, {"name": 1, "key": 1})
        if not project:
            continue
        pipeline = [
            {"$match": {"project_id": pid}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        status_counts = await issues_col.aggregate(pipeline).to_list(None)
        project_stats.append({
            "project_id": str(pid),
            "project_name": project["name"],
            "project_key": project["key"],
            "status_counts": {s["_id"]: s["count"] for s in status_counts},
        })

    # 최근 변경이력 (내 프로젝트 이슈 기준)
    history_col = MongoClientManager.get_pm_issue_history_collection()
    recent_history = await history_col.find({
        "issue_id": {"$in": await issues_col.distinct("_id", {"project_id": {"$in": project_ids}})}
    }).sort("created_at", -1).limit(10).to_list(None)

    return {
        "my_issues": my_issues,
        "reported_issues": reported_issues,
        "project_stats": project_stats,
        "recent_history_count": len(recent_history),
    }
