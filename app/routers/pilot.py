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
