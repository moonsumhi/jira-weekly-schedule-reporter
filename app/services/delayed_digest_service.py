"""매일 09:00 KST에 지연된 SR/PM 이슈를 담당자별로 묶어 메일로 알려준다.

app/services/jira_poller.py의 백그라운드 루프 구조(asyncio.create_task + start/stop)를
그대로 따른다.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager
from app.services.sr.sr_service import compute_is_delayed
from app.utils.mail_notify import send_delayed_digest
from app.utils.time import KST, next_9am_kst

logger = logging.getLogger(__name__)


class DelayedDigestService:
    def __init__(self):
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("DelayedDigestService started")

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("DelayedDigestService stopped")

    async def _loop(self) -> None:
        await self._catch_up_if_missed()
        while True:
            now = datetime.now(timezone.utc)
            wake_at = next_9am_kst(now)
            sleep_seconds = max((wake_at - now).total_seconds(), 1.0)
            logger.info("DelayedDigestService: 다음 실행까지 %.0f초 대기 (%s)", sleep_seconds, wake_at)
            await asyncio.sleep(sleep_seconds)
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("DelayedDigestService 실행 실패")

    async def _catch_up_if_missed(self) -> None:
        """서버가 09시~재시작 사이에 다운되어 그날 걸 놓친 경우, 즉시 한 번 실행."""
        now = datetime.now(timezone.utc)
        now_kst = now.astimezone(KST)
        today_str = now_kst.strftime("%Y-%m-%d")
        if now_kst.hour < 9:
            return
        col = MongoClientManager.get_delayed_digest_state_collection()
        state = await col.find_one({"_id": "state"})
        if state and state.get("last_run_date") == today_str:
            return
        logger.info("DelayedDigestService: 오늘 실행 기록이 없어 즉시 1회 실행")
        try:
            await self._run_once()
        except Exception:
            logger.exception("DelayedDigestService catch-up 실행 실패")

    async def _run_once(self) -> None:
        now = datetime.now(timezone.utc)

        sr_by_assignee, issue_by_assignee = await self._collect_delayed(now)
        assignee_ids = set(sr_by_assignee) | set(issue_by_assignee)
        if not assignee_ids:
            logger.info("DelayedDigestService: 지연 건 없음")
            await self._mark_ran(now)
            return

        user_map = await self._load_users(assignee_ids)

        sent = 0
        for assignee_id in assignee_ids:
            user = user_map.get(assignee_id)
            if not user or not user.get("email"):
                logger.warning("DelayedDigestService: 담당자 이메일 없음 (assignee_id=%s)", assignee_id)
                continue
            try:
                await send_delayed_digest(
                    to_email=user["email"],
                    to_name=user.get("full_name") or "-",
                    sr_items=sr_by_assignee.get(assignee_id, []),
                    issue_items=issue_by_assignee.get(assignee_id, []),
                )
                sent += 1
            except Exception:
                logger.exception("DelayedDigestService: 발송 실패 (assignee_id=%s)", assignee_id)

        logger.info("DelayedDigestService: %d명에게 발송 시도", sent)
        await self._mark_ran(now)

    async def _collect_delayed(self, now: datetime) -> tuple[dict, dict]:
        sr_col = MongoClientManager.get_db()[MongoClientManager.SERVICE_REQUESTS]
        sr_by_assignee: dict[str, list[dict]] = defaultdict(list)
        async for doc in sr_col.find({
            "$or": [
                {"planned_due_date": {"$exists": True, "$ne": None}},
                {"desired_due_date": {"$exists": True, "$ne": None}},
            ]
        }):
            if not compute_is_delayed(doc):
                continue
            assignee_id = doc.get("assignee_id")
            if not assignee_id:
                continue
            # 완료목표일 우선, 없으면 희망완료일 (compute_is_delayed와 동일 기준)
            due_date = doc.get("planned_due_date") or doc.get("desired_due_date")
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            sr_by_assignee[str(assignee_id)].append({
                "sr_no": doc.get("sr_no") or "-",
                "title": doc.get("title") or "-",
                "days_late": (now.date() - due_date.date()).days,
            })

        issues_col = MongoClientManager.get_pm_issues_collection()
        raw_issues = []
        async for doc in issues_col.find({"status": {"$ne": "DONE"}, "due_date": {"$exists": True, "$ne": None}}):
            due_date = doc["due_date"]
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
            if due_date >= now:
                continue
            raw_issues.append((doc, due_date))

        project_key_map: dict[str, str] = {}
        project_ids = {doc.get("project_id") for doc, _ in raw_issues if doc.get("project_id")}
        if project_ids:
            projects_col = MongoClientManager.get_pm_projects_collection()
            async for proj in projects_col.find({"_id": {"$in": list(project_ids)}}):
                project_key_map[str(proj["_id"])] = proj.get("key") or "?"

        issue_by_assignee: dict[str, list[dict]] = defaultdict(list)
        for doc, due_date in raw_issues:
            assignee_id = doc.get("assignee_id")
            if not assignee_id:
                continue
            project_key = project_key_map.get(str(doc.get("project_id")), "?")
            issue_by_assignee[str(assignee_id)].append({
                "key": f"{project_key}-{doc.get('number')}",
                "title": doc.get("title") or "-",
                "days_late": (now.date() - due_date.date()).days,
            })

        return dict(sr_by_assignee), dict(issue_by_assignee)

    async def _load_users(self, assignee_ids: set[str]) -> dict[str, dict]:
        from bson import ObjectId
        oids = []
        for aid in assignee_ids:
            try:
                oids.append(ObjectId(aid))
            except Exception:
                continue
        users_col = MongoClientManager.get_users_collection()
        result: dict[str, dict] = {}
        async for user in users_col.find({"_id": {"$in": oids}}, {"email": 1, "full_name": 1}):
            result[str(user["_id"])] = {"email": user.get("email"), "full_name": user.get("full_name")}
        return result

    async def _mark_ran(self, now: datetime) -> None:
        today_str = now.astimezone(KST).strftime("%Y-%m-%d")
        col = MongoClientManager.get_delayed_digest_state_collection()
        await col.update_one({"_id": "state"}, {"$set": {"last_run_date": today_str}}, upsert=True)
