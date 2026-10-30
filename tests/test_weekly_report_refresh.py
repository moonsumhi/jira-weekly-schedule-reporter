"""Weekly report refresh is available until confirmation, including races."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.pm import weekly_reports


class WeeklyReportRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, status, *, concurrent_change=False):
        report_id = ObjectId()
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        doc = {
            "_id": report_id,
            "start_date": datetime(2026, 10, 26, tzinfo=timezone.utc),
            "end_date": datetime(2026, 11, 1, tzinfo=timezone.utc),
            "manual_items": [{"title": "수동 공지"}],
        }
        if status is not None:
            doc["status"] = status
        col = SimpleNamespace(
            find_one=AsyncMock(return_value=doc),
            find_one_and_update=AsyncMock(return_value=None if concurrent_change else doc),
        )
        aggregate = AsyncMock(return_value=([], [], [], [], SimpleNamespace(model_dump=lambda: {"total": 0})))
        with patch.object(MongoClientManager, "get_pm_weekly_reports_collection", return_value=col), \
             patch.object(weekly_reports, "_require_pm"), \
             patch.object(weekly_reports, "aggregate_period", aggregate), \
             patch.object(weekly_reports, "_aggregate_sr", AsyncMock(return_value=SimpleNamespace(model_dump=lambda: {}))), \
             patch.object(weekly_reports, "_doc_to_out", side_effect=lambda value: value), \
             patch.object(weekly_reports, "_enrich", AsyncMock(side_effect=lambda value, _doc: value)):
            try:
                result = await weekly_reports.refresh_weekly_report(str(report_id), user)
            except HTTPException as exc:
                result = exc
        return result, col, aggregate

    async def test_draft_and_reviewing_refresh_without_changing_manual_content(self):
        for status in ("DRAFT", "REVIEWING", None):
            with self.subTest(status=status):
                result, col, aggregate = await self.exercise(status)
                self.assertEqual(result["manual_items"], [{"title": "수동 공지"}])
                aggregate.assert_awaited_once()
                query, update = col.find_one_and_update.await_args.args
                self.assertEqual(query["$or"][0], {"status": {"$in": ["DRAFT", "REVIEWING"]}})
                self.assertIsNone(query["deleted_at"])
                self.assertNotIn("manual_items", update["$set"])
                self.assertNotIn("status", update["$set"])

    async def test_confirmed_report_is_not_refreshed(self):
        result, col, aggregate = await self.exercise("CONFIRMED")
        self.assertEqual(result.status_code, 409)
        aggregate.assert_not_awaited()
        col.find_one_and_update.assert_not_awaited()

    async def test_confirmation_during_aggregation_rejects_update(self):
        result, col, aggregate = await self.exercise("REVIEWING", concurrent_change=True)
        self.assertEqual(result.status_code, 409)
        aggregate.assert_awaited_once()
        col.find_one_and_update.assert_awaited_once()
