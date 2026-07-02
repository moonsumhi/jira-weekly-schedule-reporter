from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.models.pm.sprint import SprintCreate, SprintPatch, SprintOut
from app.routers.auth import get_current_user

router = APIRouter()


async def _sprint_to_out(doc: dict) -> SprintOut:
    issue_count = await MongoClientManager.get_pm_issues_collection().count_documents(
        {"sprint_id": doc["_id"]}
    )
    return SprintOut(
        id=str(doc["_id"]),
        project_id=str(doc["project_id"]),
        name=doc["name"],
        goal=doc.get("goal"),
        status=doc["status"],
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        issue_count=issue_count,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get("/{project_id}/sprints", response_model=List[SprintOut])
async def list_sprints(project_id: str, current_user: UserPublic = Depends(get_current_user)):

    docs = await MongoClientManager.get_pm_sprints_collection().find(
        {"project_id": ObjectId(project_id)}
    ).sort("created_at", -1).to_list(None)
    return [await _sprint_to_out(d) for d in docs]


@router.post("/{project_id}/sprints", response_model=SprintOut, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    project_id: str,
    body: SprintCreate,
    current_user: UserPublic = Depends(get_current_user),
):

    col = MongoClientManager.get_pm_sprints_collection()
    now = datetime.now(timezone.utc)

    result = await col.insert_one({
        "project_id": ObjectId(project_id),
        "name": body.name,
        "goal": body.goal,
        "status": "PLANNED",
        "start_date": body.start_date,
        "end_date": body.end_date,
        "created_at": now,
        "updated_at": now,
    })
    doc = await col.find_one({"_id": result.inserted_id})
    return await _sprint_to_out(doc)


@router.patch("/{project_id}/sprints/{sprint_id}", response_model=SprintOut)
async def patch_sprint(
    project_id: str,
    sprint_id: str,
    body: SprintPatch,
    current_user: UserPublic = Depends(get_current_user),
):

    col = MongoClientManager.get_pm_sprints_collection()

    # ACTIVE 스프린트는 프로젝트당 하나만 허용
    if body.status == "ACTIVE":
        existing_active = await col.find_one({
            "project_id": ObjectId(project_id),
            "status": "ACTIVE",
            "_id": {"$ne": ObjectId(sprint_id)},
        })
        if existing_active:
            raise HTTPException(status_code=409, detail="이미 활성 스프린트가 있습니다.")

    update = {k: v for k, v in body.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)

    doc = await col.find_one_and_update(
        {"_id": ObjectId(sprint_id), "project_id": ObjectId(project_id)},
        {"$set": update},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="스프린트를 찾을 수 없습니다.")
    return await _sprint_to_out(doc)


@router.delete("/{project_id}/sprints/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint(
    project_id: str,
    sprint_id: str,
    current_user: UserPublic = Depends(get_current_user),
):

    # 스프린트 삭제 시 소속 이슈의 sprint_id를 null로 초기화
    await MongoClientManager.get_pm_issues_collection().update_many(
        {"sprint_id": ObjectId(sprint_id)},
        {"$set": {"sprint_id": None}},
    )
    await MongoClientManager.get_pm_sprints_collection().delete_one({"_id": ObjectId(sprint_id)})
