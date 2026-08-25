"""매일 09:00 KST에 활성 반복 이슈 템플릿을 확인해 도래한 회차를 자동 생성한다.

생성은 (recurring_template_id, occurrence_date) 로 idempotent 하므로, 재시작/재실행에
안전하다(중복 안 만듦). 그래서 별도 실행상태 저장 없이, 시작 시 1회 즉시 실행(catch-up)
후 매일 09시에 반복한다. app/services/delayed_digest_service.py 구조를 따른다.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.db.mongo import MongoClientManager
from app.services.pm import recurring_issue_service as svc
from app.utils.time import next_9am_kst

logger = logging.getLogger(__name__)


class RecurringIssueScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("RecurringIssueScheduler started")

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("RecurringIssueScheduler stopped")

    async def _loop(self) -> None:
        # 시작 시 1회 즉시 실행 (서버가 꺼져 있던 동안 도래한 회차 보정 — idempotent 하므로 안전)
        try:
            await self._run_once()
        except Exception:
            logger.exception("RecurringIssueScheduler 초기 실행 실패")

        while True:
            now = datetime.now(timezone.utc)
            wake_at = next_9am_kst(now)
            sleep_seconds = max((wake_at - now).total_seconds(), 1.0)
            logger.info("RecurringIssueScheduler: 다음 실행까지 %.0f초 대기 (%s)", sleep_seconds, wake_at)
            await asyncio.sleep(sleep_seconds)
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("RecurringIssueScheduler 실행 실패")

    async def _run_once(self) -> None:
        now = datetime.now(timezone.utc)
        col = MongoClientManager.get_recurring_issue_templates_collection()
        templates = await col.find({"active": True, "auto_enabled": True}).to_list(None)
        if not templates:
            return

        total = 0
        for tpl in templates:
            try:
                created = await svc.generate_due(tpl, now)
                total += len(created)
                if created:
                    logger.info(
                        "반복 이슈 자동 생성: template=%s(%s) %d건",
                        tpl.get("name"), tpl["_id"], len(created),
                    )
            except Exception:
                logger.exception("반복 이슈 생성 실패: template=%s", tpl.get("_id"))
        if total:
            logger.info("RecurringIssueScheduler: 이번 실행 총 %d건 생성", total)
