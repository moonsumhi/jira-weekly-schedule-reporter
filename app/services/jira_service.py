from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.utils.time import TimeUtil, TimeProvider, KST
from app.jira.jql_builder import JqlBuilder
from app.jira.client import JiraClient
from app.models.issue import Issue, AssigneeGroup, GroupedResponse
from dateutil import parser as dtparser


class JiraTaskService:
    def __init__(
        self,
        client: JiraClient | None = None,
        time_provider: TimeProvider | None = None,
        default_fields: Optional[List[str]] = None,
    ) -> None:
        self.client = client or JiraClient()
        self.time = time_provider or TimeProvider()
        self.default_fields = default_fields or [
            "summary",
            "status",
            "assignee",
            "created",
            "updated",
            "duedate",
            "customfield_10015",
        ]

    @staticmethod
    def _parse_dt(val: Optional[str]) -> Optional[datetime]:
        if not val:
            return None
        return dtparser.isoparse(val).astimezone(timezone.utc)

    def _to_issue_model(self, raw: Dict[str, Any]) -> Issue:
        f = raw.get("fields", {})
        assignee = f.get("assignee") or {}
        assignee_name = (
            assignee.get("displayName") if isinstance(assignee, dict) else None
        )
        status_name = (f.get("status") or {}).get("name", "")
        return Issue(
            key=raw.get("key"),
            summary=f.get("summary", ""),
            status=status_name,
            assignee=assignee_name,
            created=self._parse_dt(f.get("created")),
            updated=self._parse_dt(f.get("updated")),
            duedate=self._parse_dt(f.get("duedate")),
            start=self._parse_dt(f.get("customfield_10015")),
            url=self.client.issue_url(raw.get("key")),
        )

    @staticmethod
    def _sort_key(i: Issue):
        return (
            i.duedate
            or i.updated
            or i.created
            or datetime.min.replace(tzinfo=timezone.utc)
        )

    @staticmethod
    def _group_by_assignee(issues: List[Issue]) -> List[AssigneeGroup]:
        buckets: Dict[str, List[Issue]] = {}
        for iss in issues:
            key = iss.assignee or "Unassigned"
            buckets.setdefault(key, []).append(iss)
        groups: List[AssigneeGroup] = []
        for name, items in buckets.items():
            items.sort(key=JiraTaskService._sort_key)
            groups.append(AssigneeGroup(assignee=name, count=len(items), issues=items))
        groups.sort(key=lambda g: (g.assignee.lower() if g.assignee else "zzz"))
        return groups

    async def fetch_grouped(
        self,
        start: str,
        end: str,
        assignees: Optional[List[str]],
        date_field: str,
        *,
        extra_filters: Optional[List[str]] = None,
    ) -> GroupedResponse:
        s_utc = TimeUtil.ensure_utc(start)
        e_utc = TimeUtil.ensure_utc(end)
        if e_utc < s_utc:
            raise ValueError("end must be >= start")

        builder = (
            JqlBuilder()
            .with_field(date_field)
            .between(s_utc, e_utc)
            .with_assignees(assignees or [])
            .order_by("ASC")
        )

        jql = builder.build()

        if extra_filters:
            order_idx = jql.rfind(" ORDER BY ")
            if order_idx == -1:
                jql = jql + " AND (" + ") AND (".join(extra_filters) + ")"
            else:
                core = jql[:order_idx]
                order = jql[order_idx:]
                jql = core + " AND (" + ") AND (".join(extra_filters) + ")" + order

        raw = await self.client.search(jql, self.default_fields)
        issues = [self._to_issue_model(r) for r in raw]
        groups = self._group_by_assignee(issues)

        return GroupedResponse(
            date_field=date_field,
            start=s_utc.astimezone(KST),
            end=e_utc.astimezone(KST),
            timezone="Asia/Seoul",
            total=len(issues),
            groups=groups,
        )

    def preview_jql(
        self,
        start: str,
        end: str,
        assignees: Optional[List[str]],
        date_field: str = "updated",
    ) -> str:
        s_utc = TimeUtil.ensure_utc(start)
        e_utc = TimeUtil.ensure_utc(end)
        return (
            JqlBuilder()
            .with_field(date_field)
            .between(s_utc, e_utc)
            .with_assignees(assignees or [])
            .build()
        )
