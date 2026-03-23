from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional

from app.models.issue import GroupedResponse
from app.services.jira_service import JiraTaskService
from app.core.consts import ALLOWED_STATUSES
from app.jira.client import JiraClient
from app.jira.attachment import extract_text_from_attachment

router = APIRouter()
service = JiraTaskService()
jira_client = JiraClient()


@router.get("/", response_model=GroupedResponse, summary="담당자별 Issue 뽑기")
async def get_issues(
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
    try:
        return await service.fetch_grouped(start, end, assignees, date_field)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/advanced", response_model=GroupedResponse, summary="Fetch with extra JQL filters"
)
async def get_issues_advanced(
    start: str,
    end: str,
    assignees: Optional[List[str]] = Query(None),
    date_field: str = Query("updated", regex="^(updated|created|due)$"),
    project: Optional[str] = Query(
        None, description="Filter by project key, e.g., ABC"
    ),
    issuetypes: Optional[List[str]] = Query(None, description="e.g., Task,Bug"),
    status_cat: Optional[str] = Query(None, description="To Do|In Progress|Done"),
):
    extras = []
    if project:
        extras.append(f"project = {project}")
    if issuetypes:
        joined = ", ".join([f'"{t}"' for t in issuetypes])
        extras.append(f"issuetype in ({joined})")
    if status_cat:
        extras.append(f'statusCategory = "{status_cat}"')
    try:
        return await service.fetch_grouped(
            start, end, assignees, date_field, extra_filters=extras or None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/today-tasks")
async def today_tasks(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    assignees: Optional[List[str]] = Query(None, description="Filter by assignee"),
    status: Optional[List[str]] = Query(
        None,
        description="Filter by status",
    ),
):
    """
    Returns Jira tasks grouped by assignee, filtered by start/end date, assignees, and status.
    """
    # Validate statuses
    if status:
        invalid_status = [s for s in status if s not in ALLOWED_STATUSES]
        if invalid_status:
            return {"error": f"Invalid status: {invalid_status}"}

    status_filter = None
    if status:
        # Wrap each status in double quotes
        quoted_statuses = ",".join(f'"{s}"' for s in status)
        status_filter = f"status in ({quoted_statuses})"

    # Fetch tasks from JiraTaskService
    response = await service.fetch_grouped(
        start=start,
        end=end,
        assignees=assignees,
        date_field="due",
        extra_filters=[status_filter] if status_filter else None,
    )

    return response


@router.get("/{issue_key}/attachments", summary="이슈 첨부파일 텍스트 추출")
async def get_issue_attachments(issue_key: str):
    """
    Jira 이슈의 첨부파일을 다운로드하여 텍스트를 추출해 반환합니다.
    지원 형식: hwp, txt, md
    """
    try:
        issue = await jira_client.get_issue(issue_key, fields=["attachment"])
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))

    attachments = (issue.get("fields") or {}).get("attachment") or []
    results = []
    for att in attachments:
        text = await extract_text_from_attachment(att, jira_client.auth)
        if text is not None:
            results.append({"filename": att.get("filename", ""), "text": text})

    return {"issue_key": issue_key, "attachments": results}
