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
        col = MongoClientManager.get_pilot_poll_state_collection()
        now = datetime.now(timezone.utc)

        last_checked = await self._get_last_checked(col)

        jql = f'labels = "{self.label}"'
        if last_checked:
            fmt = last_checked.strftime("%Y-%m-%d %H:%M")
            jql += f' AND updated >= "{fmt}"'

        issues = await self.jira.search(
            jql,
            fields=["summary", "description", "status", "labels", "assignee", "project", "updated"],
        )

        for issue in issues:
            issue_key = issue["key"]
            updated = issue["fields"]["updated"]
            if not await self._is_already_sent(col, issue_key, updated):
                await self._forward_to_pilot(issue)
                await self._mark_sent(col, issue_key, updated)

        await self._set_last_checked(col, now)

    async def _forward_to_pilot(self, issue: dict) -> None:
        payload = {
            "webhookEvent": "jira:issue_updated",
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

    async def _is_already_sent(self, col, issue_key: str, updated: str) -> bool:
        doc = await col.find_one({"_id": f"sent:{issue_key}"})
        if doc and doc.get("updated") == updated:
            return True
        return False

    async def _mark_sent(self, col, issue_key: str, updated: str) -> None:
        await col.update_one(
            {"_id": f"sent:{issue_key}"},
            {"$set": {"updated": updated, "sent_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
