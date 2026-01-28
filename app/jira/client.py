from __future__ import annotations
from typing import Dict, Any, List, Optional
import httpx
import asyncio

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
        self, jql: str, fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/search/jql"  # enhanced search
        max_results = 100  # per request (Jira allows up to 1000; 100 is a good default)
        fields = fields or [
            "summary",
            "status",
            "assignee",
            "created",
            "updated",
            "duedate",
        ]

        all_issues: List[Dict[str, Any]] = []
        next_token: Optional[str] = None

        # Basic headers are fine; use your existing auth (Basic or Bearer)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=30.0, headers=headers, auth=self.auth
        ) as client:
            while True:
                payload: Dict[str, Any] = {
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": fields,
                    "fieldsByKeys": False,
                    # Useful expansion so you can map field IDs <-> names if needed
                    "expand": "names,schema",
                }
                if next_token:
                    payload["nextPageToken"] = next_token

                r = await client.post(url, json=payload)

                # Handle common errors explicitly
                if r.status_code == 401:
                    raise RuntimeError("Jira authentication failed. Check email/token.")
                if r.status_code == 429:
                    # Respect server backoff if present
                    retry_after = int(r.headers.get("Retry-After", "2"))
                    await asyncio.sleep(retry_after)
                    continue
                if r.status_code >= 400:
                    raise RuntimeError(f"Jira error {r.status_code}: {r.text}")

                data = r.json()
                issues = data.get("issues", [])
                all_issues.extend(issues)

                # Enhanced search paginates via nextPageToken
                next_token = data.get("nextPageToken")
                if not next_token or not issues:
                    break
        return all_issues

    def issue_url(self, key: str) -> str:
        return f"{self.base_url}/browse/{key}"
