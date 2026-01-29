"""Pilot callback endpoints for task completion notifications."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo import MongoClientManager

router = APIRouter()


class TaskCallbackRequest(BaseModel):
    """Pilot task completion callback payload."""

    task_id: str
    issue_key: str
    status: Literal["completed", "failed"]
    pr_url: str | None = None
    error: str | None = None


class TaskOut(BaseModel):
    """Task status output."""

    issue_key: str
    status: str
    sent_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
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
        tasks.append(
            TaskOut(
                issue_key=issue_key,
                status=doc.get("status", "unknown"),
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

    if payload.status == "completed":
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
