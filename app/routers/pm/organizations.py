from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.organization import (
    OrganizationCreate, OrganizationPatch, OrganizationOut,
    OrgMemberAdd, OrgMemberOut, OrgMemberRolePatch,
)
from app.models.pm.project import ProjectOut
from app.routers.auth import get_current_user

router = APIRouter()


def _org_to_out(doc: dict) -> OrganizationOut:
    return OrganizationOut(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _proj_to_out(doc: dict) -> ProjectOut:
    return ProjectOut(
        id=str(doc["_id"]),
        org_id=str(doc["org_id"]),
        name=doc["name"],
        key=doc["key"],
        description=doc.get("description"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ── 조직 CRUD ──────────────────────────────────────────────────────

@router.get("", response_model=List[OrganizationOut])
async def list_organizations(current_user: UserPublic = Depends(get_current_user)):
    """전체 조직 목록 반환 (백오피스 회원 공용)."""
    docs = await MongoClientManager.get_pm_organizations_collection().find({}).sort("created_at", -1).to_list(None)
    return [_org_to_out(d) for d in docs]


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    orgs_col = MongoClientManager.get_pm_organizations_collection()

    if await orgs_col.find_one({"slug": body.slug}):
        raise HTTPException(status_code=409, detail="이미 사용 중인 slug입니다.")

    now = datetime.now(timezone.utc)
    result = await orgs_col.insert_one({
        "name": body.name,
        "slug": body.slug,
        "created_at": now,
        "updated_at": now,
    })

    doc = await orgs_col.find_one({"_id": result.inserted_id})
    return _org_to_out(doc)


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(org_id: str, current_user: UserPublic = Depends(get_current_user)):
    doc = await MongoClientManager.get_pm_organizations_collection().find_one({"_id": ObjectId(org_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")
    return _org_to_out(doc)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(org_id: str, current_user: UserPublic = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 조직을 삭제할 수 있습니다.")

    project_count = await MongoClientManager.get_pm_projects_collection().count_documents(
        {"org_id": ObjectId(org_id)}
    )
    if project_count > 0:
        raise HTTPException(status_code=409, detail=f"조직에 프로젝트 {project_count}개가 있습니다. 프로젝트를 먼저 삭제해 주세요.")

    col = MongoClientManager.get_pm_organizations_collection()
    result = await col.delete_one({"_id": ObjectId(org_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")

    await MongoClientManager.get_pm_org_members_collection().delete_many({"org_id": ObjectId(org_id)})


@router.patch("/{org_id}", response_model=OrganizationOut)
async def patch_organization(
    org_id: str,
    body: OrganizationPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 조직 정보를 수정할 수 있습니다.")
    col = MongoClientManager.get_pm_organizations_collection()

    update = {k: v for k, v in body.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)

    doc = await col.find_one_and_update(
        {"_id": ObjectId(org_id)},
        {"$set": update},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")
    return _org_to_out(doc)


# ── 조직 멤버 관리 ──────────────────────────────────────────────────

async def _member_to_out(doc: dict) -> OrgMemberOut:
    user_email = doc.get("user_email", "")
    user_name = doc.get("user_name", "")
    if not user_email or not user_name:
        user = await MongoClientManager.get_users_collection().find_one(
            {"_id": doc["user_id"]}, {"email": 1, "full_name": 1}
        )
        if user:
            user_email = user_email or user.get("email", "")
            user_name = user_name or user.get("full_name") or ""
    return OrgMemberOut(
        id=str(doc["_id"]),
        org_id=str(doc["org_id"]),
        user_id=str(doc["user_id"]),
        user_email=user_email,
        user_name=user_name,
        role=doc["role"],
        joined_at=doc["joined_at"],
    )


@router.get("/{org_id}/members", response_model=List[OrgMemberOut])
async def list_org_members(org_id: str, current_user: UserPublic = Depends(get_current_user)):
    docs = await MongoClientManager.get_pm_org_members_collection().find(
        {"org_id": ObjectId(org_id)}
    ).sort("joined_at", 1).to_list(None)
    return [await _member_to_out(d) for d in docs]


@router.post("/{org_id}/members", response_model=OrgMemberOut, status_code=status.HTTP_201_CREATED)
async def add_org_member(
    org_id: str,
    body: OrgMemberAdd,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 멤버를 추가할 수 있습니다.")

    org_col = MongoClientManager.get_pm_organizations_collection()
    if not await org_col.find_one({"_id": ObjectId(org_id)}):
        raise HTTPException(status_code=404, detail="조직을 찾을 수 없습니다.")

    users_col = MongoClientManager.get_users_collection()
    user_doc = await users_col.find_one({"_id": ObjectId(body.user_id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    members_col = MongoClientManager.get_pm_org_members_collection()
    if await members_col.find_one({"org_id": ObjectId(org_id), "user_id": ObjectId(body.user_id)}):
        raise HTTPException(status_code=409, detail="이미 조직 멤버입니다.")

    now = datetime.now(timezone.utc)
    result = await members_col.insert_one({
        "org_id": ObjectId(org_id),
        "user_id": ObjectId(body.user_id),
        "user_email": user_doc["email"],
        "user_name": user_doc.get("full_name") or "",
        "role": body.role,
        "joined_at": now,
    })
    doc = await members_col.find_one({"_id": result.inserted_id})

    # 조직 소속 프로젝트에 자동 추가 (이미 멤버인 경우 스킵)
    project_role = "ADMIN" if body.role == "ADMIN" else "DEVELOPER"
    projects_col = MongoClientManager.get_pm_projects_collection()
    project_members_col = MongoClientManager.get_pm_project_members_collection()
    org_projects = await projects_col.find({"org_id": ObjectId(org_id)}).to_list(None)
    user_id_obj = ObjectId(body.user_id)
    for project in org_projects:
        pid = project["_id"]
        already = await project_members_col.find_one({"project_id": pid, "user_id": user_id_obj})
        if not already:
            await project_members_col.insert_one({
                "project_id": pid,
                "user_id": user_id_obj,
                "user_email": user_doc["email"],
                "user_name": user_doc.get("full_name") or "",
                "role": project_role,
                "joined_at": now,
            })

    return await _member_to_out(doc)


@router.patch("/{org_id}/members/{user_id}", response_model=OrgMemberOut)
async def patch_org_member_role(
    org_id: str,
    user_id: str,
    body: OrgMemberRolePatch,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 역할을 변경할 수 있습니다.")

    members_col = MongoClientManager.get_pm_org_members_collection()
    doc = await members_col.find_one_and_update(
        {"org_id": ObjectId(org_id), "user_id": ObjectId(user_id)},
        {"$set": {"role": body.role}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="해당 멤버를 찾을 수 없습니다.")
    return await _member_to_out(doc)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    org_id: str,
    user_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 멤버를 제거할 수 있습니다.")

    result = await MongoClientManager.get_pm_org_members_collection().delete_one(
        {"org_id": ObjectId(org_id), "user_id": ObjectId(user_id)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="해당 멤버를 찾을 수 없습니다.")


# ── 조직 내 프로젝트 목록 ───────────────────────────────────────────

@router.get("/{org_id}/projects", response_model=List[ProjectOut])
async def list_org_projects(org_id: str, current_user: UserPublic = Depends(get_current_user)):
    """조직에 속한 모든 프로젝트 반환."""
    docs = await MongoClientManager.get_pm_projects_collection().find(
        {"org_id": ObjectId(org_id)}
    ).sort("created_at", -1).to_list(None)
    return [_proj_to_out(d) for d in docs]
