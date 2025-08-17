from __future__ import annotations
from typing import Dict, Any, List
import httpx

from app.core.config import settings


class JiraClient:
    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        token: str | None = None,
    ):
        self.base_url = base_url or settings.JIRA_BASE_URL
        self.email = email or settings.JIRA_EMAIL
        self.token = token or settings.JIRA_API_TOKEN

    @property
    def auth(self):
        return (self.email, self.token)

    async def search(
        self, jql: str, fields: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/search"
        start_at, max_results = 0, 100
        all_issues: List[Dict[str, Any]] = []
        fields = fields or [
            "summary",
            "status",
            "assignee",
            "created",
            "updated",
            "duedate",
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                payload = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": fields,
                }
                r = await client.post(url, json=payload, auth=self.auth)
                if r.status_code == 401:
                    raise RuntimeError("Jira authentication failed. Check email/token.")
                if r.status_code >= 400:
                    raise RuntimeError(f"Jira error {r.status_code}: {r.text}")
                data = r.json()
                all_issues.extend(data.get("issues", []))
                fetched = data.get("maxResults", max_results)
                total = data.get("total", 0)
                start_at += fetched
                if start_at >= total:
                    break
            return all_issues

    def issue_url(self, key: str) -> str:
        return f"{self.base_url}/browse/{key}"
