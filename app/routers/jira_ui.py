# app/routers/jira_ui.py
import os
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.jira_service import JiraTaskService
from app.utils.time import KST

router = APIRouter()

_service = JiraTaskService()

# BASE_DIR = app/ 의 절대 경로
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@router.get("/example-jql", tags=["utility"])
async def preview_jql(
    start: str,
    end: str,
    assignees: Optional[List[str]] = None,
    date_field: str = "updated",
):
    return {"jql": _service.preview_jql(start, end, assignees, date_field)}


@router.get(
    "/ui",
    response_class=HTMLResponse,
    tags=["ui"],
    summary="Minimal browser UI for quick viewing",
)
async def ui(
    request: Request,
    start: str = Query(
        ...,
        description="Start date/datetime (e.g., 2025-08-01 or 2025-08-01T09:00+09:00)",
    ),
    end: str = Query(..., description="End date/datetime (inclusive)"),
    assignees: Optional[List[str]] = Query(
        None, description="Multiple assignees allowed: ?assignees=a&assignees=b"
    ),
    date_field: str = Query(
        "updated",
        regex="^(updated|created|due)$",
        description="Which field to filter on",
    ),
):
    grouped = await _service.fetch_grouped(start, end, assignees, date_field)

    def fmt(dt):
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M") if dt else "-"

    STATUS_CSS = {"해야 할 일": "todo", "진행 중": "in-progress", "완료": "done"}

    now = datetime.now(timezone.utc).astimezone(KST)

    groups = []
    for g in grouped.groups:
        issues = []
        for it in g.issues:
            status_class = STATUS_CSS.get(it.status, "unknown")

            due_dt = it.duedate.astimezone(KST) if it.duedate else None
            is_overdue = due_dt and due_dt < now and it.status not in ["완료", "Done"]
            due_class = "overdue" if is_overdue else ""

            issues.append(
                {
                    "key": it.key,
                    "summary": it.summary,
                    "status": it.status,
                    "status_class": status_class,
                    "due_class": due_class,
                    "created": fmt(it.created),
                    "updated": fmt(it.updated),
                    "duedate": fmt(it.duedate),
                    "url": it.url,
                }
            )
        groups.append({"assignee": g.assignee, "count": g.count, "issues": issues})

    return templates.TemplateResponse(
        "jira-weekly-task.html",
        {
            "request": request,
            "start": fmt(grouped.start),
            "end": fmt(grouped.end),
            "date_field": grouped.date_field,
            "groups": groups,
        },
    )
