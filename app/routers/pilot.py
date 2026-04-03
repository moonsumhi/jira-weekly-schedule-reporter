"""Pilot callback endpoints for task completion notifications."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, PlainSerializer

from app.db.mongo import MongoClientManager


# MongoDB returns naive datetime. Serialize as UTC ISO with 'Z' suffix.
def _serialize_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[datetime, PlainSerializer(_serialize_utc)]

router = APIRouter()


class TaskCallbackRequest(BaseModel):
    """Pilot task completion callback payload."""

    task_id: str
    issue_key: str
    status: Literal["pending", "completed", "failed"]
    pr_url: str | None = None
    error: str | None = None
    # Optional metadata (provided on pending)
    summary: str | None = None
    project_key: str | None = None
    issue_url: str | None = None


class TaskOut(BaseModel):
    """Task status output."""

    issue_key: str
    issue_url: str | None = None
    summary: str | None = None
    project_key: str | None = None
    status: str
    sent_at: UtcDatetime | None = None
    completed_at: UtcDatetime | None = None
    failed_at: UtcDatetime | None = None
    pr_url: str | None = None
    error: str | None = None


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks():
    """
    List all Pilot tasks with their status.
    """
    col = MongoClientManager.get_pilot_poll_state_collection()
    cursor = col.find({"_id": {"$regex": "^processed:"}}).sort("sent_at", -1)

    tasks = []
    async for doc in cursor:
        issue_key = doc["_id"].replace("processed:", "")
        # status가 없는 오래된 데이터는 "legacy"로 표시
        status = doc.get("status")
        if status is None:
            status = "legacy"
        tasks.append(
            TaskOut(
                issue_key=issue_key,
                issue_url=doc.get("issue_url"),
                summary=doc.get("summary"),
                project_key=doc.get("project_key"),
                status=status,
                sent_at=doc.get("sent_at"),
                completed_at=doc.get("completed_at"),
                failed_at=doc.get("failed_at"),
                pr_url=doc.get("pr_url"),
                error=doc.get("error"),
            )
        )

    return tasks


@router.post("/callback")
async def task_callback(payload: TaskCallbackRequest):
    """
    Receive task completion callback from Pilot.

    When Pilot finishes processing a task (success or failure),
    it calls this endpoint to notify the backend.
    """
    col = MongoClientManager.get_pilot_poll_state_collection()

    if payload.status == "pending":
        update: dict = {
            "status": "pending",
            "sent_at": datetime.now(timezone.utc),
        }
        if payload.summary is not None:
            update["summary"] = payload.summary
        if payload.project_key is not None:
            update["project_key"] = payload.project_key
        if payload.issue_url is not None:
            update["issue_url"] = payload.issue_url
        await col.update_one(
            {"_id": f"processed:{payload.issue_key}"},
            {"$set": update},
            upsert=True,
        )
        print(f"[Pilot Callback] Task {payload.issue_key} pending")
    elif payload.status == "completed":
        await col.update_one(
            {"_id": f"processed:{payload.issue_key}"},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc),
                    "pr_url": payload.pr_url,
                }
            },
            upsert=True,
        )
        print(f"[Pilot Callback] Task {payload.issue_key} completed, PR: {payload.pr_url}")
    else:
        await col.update_one(
            {"_id": f"processed:{payload.issue_key}"},
            {
                "$set": {
                    "status": "failed",
                    "failed_at": datetime.now(timezone.utc),
                    "error": payload.error,
                }
            },
            upsert=True,
        )
        print(f"[Pilot Callback] Task {payload.issue_key} failed: {payload.error}")

    return {"ok": True}


