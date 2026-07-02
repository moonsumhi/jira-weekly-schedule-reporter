from __future__ import annotations

from fastapi import HTTPException
from bson import ObjectId

from app.db.mongo import MongoClientManager


async def require_pm_admin(user, project_id: str, roles: list[str] | None = None) -> None:
    """시스템 관리자거나 프로젝트 지정 역할이어야 통과."""
    if user.is_admin:
        return
    await require_project_member(user.id, project_id, roles=roles or ["ADMIN", "PROJECT_MANAGER"])


async def require_pm_member(user, project_id: str) -> None:
    """시스템 관리자거나 프로젝트 멤버(역할 무관)여야 통과."""
    if user.is_admin:
        return
    await require_project_member(user.id, project_id)


async def require_project_member(user_id: str, project_id: str, roles: list[str] | None = None) -> dict:
    """프로젝트 멤버 여부 확인. roles 지정 시 역할도 검증."""
    col = MongoClientManager.get_pm_project_members_collection()
    member = await col.find_one({"project_id": ObjectId(project_id), "user_id": ObjectId(user_id)})
    if not member:
        raise HTTPException(status_code=403, detail="프로젝트 멤버가 아닙니다.")
    if roles and member["role"] not in roles:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    return member


async def get_project_or_404(project_id: str) -> dict:
    col = MongoClientManager.get_pm_projects_collection()
    project = await col.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return project


async def get_issue_or_404(project_id: str, issue_id: str) -> dict:
    col = MongoClientManager.get_pm_issues_collection()
    issue = await col.find_one({"_id": ObjectId(issue_id), "project_id": ObjectId(project_id)})
    if not issue:
        raise HTTPException(status_code=404, detail="이슈를 찾을 수 없습니다.")
    return issue
