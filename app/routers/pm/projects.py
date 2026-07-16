from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.project import (
    ProjectCreate, ProjectPatch, ProjectOut,
    ProjectMemberAdd, ProjectMemberOut, ProjectMemberRolePatch,
)
from app.routers.auth import get_current_user
from app.services.pm.permission import require_pm_admin

router = APIRouter()


def _proj_to_out(doc: dict) -> ProjectOut:
    return ProjectOut(
        id=str(doc["_id"]),
        org_id=str(doc["org_id"]),
        name=doc["name"],
        key=doc["key"],
        description=doc.get("description"),
        is_sr_default=bool(doc.get("is_sr_default", False)),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ── 프로젝트 CRUD ──────────────────────────────────────────────────

@router.get("", response_model=List[ProjectOut])
async def list_projects(current_user: UserPublic = Depends(get_current_user)):
    """프로젝트 목록. 시스템 관리자는 전체, 일반 사용자는 멤버인 프로젝트만."""
    projects_col = MongoClientManager.get_pm_projects_collection()
    if current_user.is_admin:
        docs = await projects_col.find({}).sort("created_at", -1).to_list(None)
    else:
        members_col = MongoClientManager.get_pm_project_members_collection()
        member_docs = await members_col.find(
            {"user_id": ObjectId(current_user.id)}, {"project_id": 1}
        ).to_list(None)
        project_ids = [m["project_id"] for m in member_docs]
        docs = await projects_col.find({"_id": {"$in": project_ids}}).sort("created_at", -1).to_list(None)
    return [_proj_to_out(d) for d in docs]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    projects_col = MongoClientManager.get_pm_projects_collection()
    members_col = MongoClientManager.get_pm_project_members_collection()

    # 조직 내 key 중복 체크
    if await projects_col.find_one({"org_id": ObjectId(body.org_id), "key": body.key}):
        raise HTTPException(status_code=409, detail="이미 사용 중인 프로젝트 키입니다.")

    now = datetime.now(timezone.utc)
    result = await projects_col.insert_one({
        "org_id": ObjectId(body.org_id),
        "name": body.name,
        "key": body.key,
        "description": body.description,
        "created_at": now,
        "updated_at": now,
    })
    project_id = result.inserted_id

    users_col = MongoClientManager.get_users_collection()
    creator = await users_col.find_one({"_id": ObjectId(current_user.id)}, {"email": 1, "full_name": 1})

    # 생성자를 ADMIN으로 자동 추가
    await members_col.insert_one({
        "project_id": project_id,
        "user_id": ObjectId(current_user.id),
        "user_email": creator["email"] if creator else current_user.email,
        "user_name": creator.get("full_name") or "" if creator else "",
        "role": "ADMIN",
        "joined_at": now,
    })

    # 조직 멤버를 프로젝트에 자동 추가 (생성자 제외, 이미 추가된 경우 스킵)
    org_members_col = MongoClientManager.get_pm_org_members_collection()
    org_members = await org_members_col.find({"org_id": ObjectId(body.org_id)}).to_list(None)
    creator_id = ObjectId(current_user.id)
    for om in org_members:
        if om["user_id"] == creator_id:
            continue
        project_role = "ADMIN" if om["role"] == "ADMIN" else "DEVELOPER"
        already = await members_col.find_one({"project_id": project_id, "user_id": om["user_id"]})
        if not already:
            await members_col.insert_one({
                "project_id": project_id,
                "user_id": om["user_id"],
                "user_email": om["user_email"],
                "user_name": om.get("user_name") or "",
                "role": project_role,
                "joined_at": now,
            })

    doc = await projects_col.find_one({"_id": project_id})
    return _proj_to_out(doc)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, current_user: UserPublic = Depends(get_current_user)):
    doc = await MongoClientManager.get_pm_projects_collection().find_one({"_id": ObjectId(project_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return _proj_to_out(doc)


@router.patch("/{project_id}", response_model=ProjectOut)
async def patch_project(
    project_id: str,
    body: ProjectPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_admin(current_user, project_id)
    col = MongoClientManager.get_pm_projects_collection()

    # exclude_unset=True: 요청에서 명시적으로 보낸 필드만 업데이트 (None 포함)
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    update["updated_at"] = datetime.now(timezone.utc)

    doc = await col.find_one_and_update(
        {"_id": ObjectId(project_id)},
        {"$set": update},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return _proj_to_out(doc)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, current_user: UserPublic = Depends(get_current_user)):
    await require_pm_admin(current_user, project_id, roles=["ADMIN"])
    pid = ObjectId(project_id)

    # 이슈 ID 수집 (comment/history 삭제에 사용)
    issues_col = MongoClientManager.get_pm_issues_collection()
    issue_ids = [d["_id"] async for d in issues_col.find({"project_id": pid}, {"_id": 1})]

    # 연관 데이터 일괄 삭제
    await MongoClientManager.get_pm_issue_comments_collection().delete_many({"issue_id": {"$in": issue_ids}})
    await MongoClientManager.get_pm_issue_history_collection().delete_many({"issue_id": {"$in": issue_ids}})
    await issues_col.delete_many({"project_id": pid})
    await MongoClientManager.get_pm_project_members_collection().delete_many({"project_id": pid})
    await MongoClientManager.get_pm_sprints_collection().delete_many({"project_id": pid})
    await MongoClientManager.get_pm_labels_collection().delete_many({"project_id": pid})
    await MongoClientManager.get_pm_projects_collection().delete_one({"_id": pid})

    # 이 프로젝트를 참조하던 SR 연결 정보 초기화
    sr_col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
    str_pid = str(pid)
    await sr_col.update_many(
        {"$or": [{"related_project_id": pid}, {"converted_project_id": str_pid}]},
        {"$set": {"related_project_id": None, "converted_project_id": None,
                  "related_issue_id": None, "converted_issue_id": None}},
    )


# ── 프로젝트 멤버 ──────────────────────────────────────────────────

@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
async def list_project_members(project_id: str, current_user: UserPublic = Depends(get_current_user)):
    members_col = MongoClientManager.get_pm_project_members_collection()
    users_col = MongoClientManager.get_users_collection()

    members = await members_col.find({"project_id": ObjectId(project_id)}).to_list(None)
    result = []
    for m in members:
        user = await users_col.find_one({"_id": m["user_id"]}, {"email": 1, "full_name": 1})
        result.append(ProjectMemberOut(
            id=str(m["_id"]),
            project_id=str(m["project_id"]),
            user_id=str(m["user_id"]),
            user_email=user["email"] if user else "",
            user_name=user.get("full_name") or "" if user else "",
            role=m["role"],
            joined_at=m["joined_at"],
        ))
    return result


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: str,
    body: ProjectMemberAdd,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_admin(current_user, project_id)
    members_col = MongoClientManager.get_pm_project_members_collection()
    users_col = MongoClientManager.get_users_collection()

    target_user = await users_col.find_one({"_id": ObjectId(body.user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if await members_col.find_one({"project_id": ObjectId(project_id), "user_id": ObjectId(body.user_id)}):
        raise HTTPException(status_code=409, detail="이미 프로젝트 멤버입니다.")

    now = datetime.now(timezone.utc)
    user_email = target_user["email"]
    user_name = target_user.get("full_name") or ""
    result = await members_col.insert_one({
        "project_id": ObjectId(project_id),
        "user_id": ObjectId(body.user_id),
        "user_email": user_email,
        "user_name": user_name,
        "role": body.role,
        "joined_at": now,
    })
    m = await members_col.find_one({"_id": result.inserted_id})
    return ProjectMemberOut(
        id=str(m["_id"]),
        project_id=str(m["project_id"]),
        user_id=str(m["user_id"]),
        user_email=user_email,
        user_name=user_name,
        role=m["role"],
        joined_at=m["joined_at"],
    )


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
async def change_project_member_role(
    project_id: str,
    user_id: str,
    body: ProjectMemberRolePatch,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_admin(current_user, project_id, roles=["ADMIN"])
    members_col = MongoClientManager.get_pm_project_members_collection()
    users_col = MongoClientManager.get_users_collection()

    m = await members_col.find_one_and_update(
        {"project_id": ObjectId(project_id), "user_id": ObjectId(user_id)},
        {"$set": {"role": body.role}},
        return_document=True,
    )
    if not m:
        raise HTTPException(status_code=404, detail="멤버를 찾을 수 없습니다.")

    user = await users_col.find_one({"_id": ObjectId(user_id)}, {"email": 1, "full_name": 1})
    return ProjectMemberOut(
        id=str(m["_id"]),
        project_id=str(m["project_id"]),
        user_id=str(m["user_id"]),
        user_email=user["email"] if user else "",
        user_name=user.get("full_name") or "" if user else "",
        role=m["role"],
        joined_at=m["joined_at"],
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    user_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    await require_pm_admin(current_user, project_id, roles=["ADMIN"])
    await MongoClientManager.get_pm_project_members_collection().delete_one(
        {"project_id": ObjectId(project_id), "user_id": ObjectId(user_id)}
    )


# ── SR 기본 프로젝트 설정 ─────────────────────────────────────────────

@router.post("/{project_id}/set-sr-default", response_model=ProjectOut)
async def set_sr_default_project(
    project_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """이 프로젝트를 SR 기본 프로젝트로 지정 (기존 지정은 자동 해제)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    projects_col = MongoClientManager.get_pm_projects_collection()
    now = datetime.now(timezone.utc)
    # 기존 기본 프로젝트 해제
    await projects_col.update_many({"is_sr_default": True}, {"$set": {"is_sr_default": False, "updated_at": now}})
    # 새 기본 프로젝트 지정
    doc = await projects_col.find_one_and_update(
        {"_id": ObjectId(project_id)},
        {"$set": {"is_sr_default": True, "updated_at": now}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return _proj_to_out(doc)


@router.delete("/{project_id}/set-sr-default", status_code=status.HTTP_204_NO_CONTENT)
async def clear_sr_default_project(
    project_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """SR 기본 프로젝트 지정 해제."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    projects_col = MongoClientManager.get_pm_projects_collection()
    await projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"is_sr_default": False, "updated_at": datetime.now(timezone.utc)}},
    )
