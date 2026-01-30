from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.db.mongo import MongoClientManager
from app.jira.client import JiraClient

logger = logging.getLogger(__name__)


class JiraPollerService:
    def __init__(self):
        self.interval = settings.PILOT_POLL_INTERVAL
        self.label = settings.PILOT_LABEL
        self.gateway_url = settings.PILOT_GATEWAY_URL.rstrip("/")
        self.jira = JiraClient()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "JiraPollerService started (interval=%ds, label=%s)",
            self.interval,
            self.label,
        )

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("JiraPollerService stopped")

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Polling failed")
            await asyncio.sleep(self.interval)

    async def _poll_once(self) -> None:
        print(f"[Poller] Starting poll...")
        col = MongoClientManager.get_pilot_poll_state_collection()
        now = datetime.now(timezone.utc)

        last_checked = await self._get_last_checked(col)

        jql = f'labels = "{self.label}"'
        if last_checked:
            fmt = last_checked.strftime("%Y-%m-%d %H:%M")
            jql += f' AND updated >= "{fmt}"'

        print(f"[Poller] JQL: {jql}")
        issues = await self.jira.search(
            jql,
            fields=["summary", "description", "status", "labels", "assignee", "project", "updated"],
        )
        print(f"[Poller] Found {len(issues)} issues")

        for issue in issues:
            issue_key = issue["key"]
            # 이미 Pilot에 전달된 이슈는 건너뛰기
            if await self._is_processed(col, issue_key):
                print(f"[Poller] Skipping {issue_key} (already processed)")
                continue
            await self._forward_to_pilot(issue)
            await self._mark_pending(col, issue_key, issue)

        await self._set_last_checked(col, now)

    async def _forward_to_pilot(self, issue: dict) -> None:
        # jira:issue_created 사용 - issue_updated는 changelog 검사로 인해 스킵됨
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": issue,
        }
        url = f"{self.gateway_url}/webhooks/jira"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Forwarded %s to Pilot", issue["key"])

    # --- state helpers ---

    async def _get_last_checked(self, col) -> datetime | None:
        doc = await col.find_one({"_id": "last_checked"})
        if doc:
            return doc["value"]
        return None

    async def _set_last_checked(self, col, dt: datetime) -> None:
        await col.update_one(
            {"_id": "last_checked"},
            {"$set": {"value": dt}},
            upsert=True,
        )

    async def _is_processed(self, col, issue_key: str) -> bool:
        """이슈가 이미 Pilot에 전달되었는지 확인 (pending 또는 completed)"""
        doc = await col.find_one({"_id": f"processed:{issue_key}"})
        return doc is not None

    async def _mark_pending(self, col, issue_key: str, issue: dict) -> None:
        """이슈를 pending으로 마킹 (Pilot에 전달됨, 완료 대기 중)"""
        fields = issue.get("fields", {})
        jira_base = settings.JIRA_BASE_URL.rstrip("/")
        await col.update_one(
            {"_id": f"processed:{issue_key}"},
            {"$set": {
                "status": "pending",
                "sent_at": datetime.now(timezone.utc),
                "summary": fields.get("summary", ""),
                "project_key": fields.get("project", {}).get("key", ""),
                "issue_url": f"{jira_base}/browse/{issue_key}",
            }},
            upsert=True,
        )
        print(f"[Poller] Marked {issue_key} as pending (waiting for Pilot callback)")
