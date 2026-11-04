import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as Mongo
from app.models.user import UserPublic
from app.models.pm.reports import MonthlyReportPatch, WeeklyReportStatusPatch
from app.routers.pm import monthly_reports, report_agg


def dt(month, day, hour=0, minute=0):
    return datetime(2024, month, day, hour, minute, tzinfo=timezone.utc)


class Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args):
        return self

    async def to_list(self, _length):
        return self.docs


class MonthlyActualsTests(unittest.IsolatedAsyncioTestCase):
    async def test_month_end_status_and_completion_use_kst_and_history(self):
        project = ObjectId()
        ids = [ObjectId() for _ in range(6)]
        docs = [
            {"_id": ident, "project_id": project, "number": i, "title": str(i), "type": "TASK",
             "status": status, "created_at": created, "start_date": dt(1, 10), "due_date": dt(1, 20)}
            for i, (ident, status, created) in enumerate(zip(
                ids, ["DONE", "DONE", "DONE", "IN_PROGRESS", "TODO", "DONE"],
                [dt(1, 1), dt(1, 1), dt(1, 1), dt(2, 2), dt(1, 1), dt(1, 15)]
            ))
        ]
        docs[4]["start_date"] = docs[4]["due_date"] = dt(2, 10)
        events = [
            {"_id": ObjectId(), "issue_id": ids[0], "field": "status", "old_value": "진행 중", "new_value": "완료", "created_at": dt(1, 31, 14, 59)},
            {"_id": ObjectId(), "issue_id": ids[1], "field": "status", "old_value": "진행 중", "new_value": "완료", "created_at": dt(1, 31, 15)},
            {"_id": ObjectId(), "issue_id": ids[2], "field": "status", "old_value": "진행 중", "new_value": "완료", "created_at": datetime(2023, 12, 20, tzinfo=timezone.utc)},
        ]
        class Issues:
            def find(self, query):
                if query.get("type") == "TASK":
                    return Cursor([])
                cutoff = query["$or"][0]["created_at"]["$lte"]
                return Cursor([d for d in docs if d["created_at"] <= cutoff])

        project_col = SimpleNamespace(find_one=AsyncMock(return_value={"_id": project, "name": "프로젝트"}))
        empty = SimpleNamespace(find_one=AsyncMock(return_value=None), find=lambda *_: Cursor([]))
        history = SimpleNamespace(find=lambda *_: Cursor(events))
        start, end = monthly_reports._month_range(2024, 1)
        self.assertEqual(start, datetime(2023, 12, 31, 15, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2024, 1, 31, 14, 59, 59, 999999, tzinfo=timezone.utc))
        with patch.object(Mongo, "get_pm_issues_collection", return_value=Issues()), \
             patch.object(Mongo, "get_pm_projects_collection", return_value=project_col), \
             patch.object(Mongo, "get_pm_organizations_collection", return_value=empty), \
             patch.object(Mongo, "get_users_collection", return_value=empty), \
             patch.object(Mongo, "get_pm_sprints_collection", return_value=empty), \
             patch.object(Mongo, "get_pm_issue_history_collection", return_value=history), \
             patch.object(Mongo, "get_pm_project_members_collection", return_value=empty):
            next_start, next_end = monthly_reports._next_month_range(2024, 1)
            items, upcoming, _, _, stats = await report_agg.aggregate_period(start, end, next_start, next_end, monthly_actuals=True)
        self.assertEqual({item.issue_id: item.status for item in items}, {
            str(ids[0]): "DONE", str(ids[1]): "IN_PROGRESS", str(ids[5]): "DONE",
        })
        self.assertEqual((stats.total, stats.completed, stats.in_progress), (3, 2, 1))
        self.assertEqual([item.issue_id for item in upcoming], [str(ids[4])])

    async def test_confirmed_report_blocks_refresh_and_edits(self):
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        col = SimpleNamespace(find_one=AsyncMock(return_value={"status": "CONFIRMED"}), find_one_and_update=AsyncMock())
        with patch.object(Mongo, "get_pm_monthly_reports_collection", return_value=col), patch.object(monthly_reports, "_require_pm"), \
             patch.object(monthly_reports, "aggregate_period", AsyncMock()) as aggregate:
            with self.assertRaises(HTTPException) as refresh:
                await monthly_reports.refresh_monthly_report(str(ObjectId()), user)
            with self.assertRaises(HTTPException) as edit:
                await monthly_reports.patch_monthly_report(str(ObjectId()), MonthlyReportPatch(title="변경"), user)
        self.assertEqual((refresh.exception.status_code, edit.exception.status_code), (409, 409))
        aggregate.assert_not_awaited()
        col.find_one_and_update.assert_not_awaited()

    async def test_status_transition_records_confirmation_and_unlock(self):
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        col = SimpleNamespace(find_one_and_update=AsyncMock(return_value={"status": "ok"}))
        with patch.object(Mongo, "get_pm_monthly_reports_collection", return_value=col), patch.object(monthly_reports, "_require_pm"), \
             patch.object(monthly_reports, "_doc_to_out", side_effect=lambda d: d), \
             patch.object(monthly_reports, "_enrich", AsyncMock(side_effect=lambda d, _doc, _user: d)):
            for status in ("REVIEWING", "CONFIRMED", "REVIEWING"):
                await monthly_reports.change_monthly_report_status(str(ObjectId()), WeeklyReportStatusPatch(status=status), user)
        updates = [call.args[1]["$set"] for call in col.find_one_and_update.await_args_list]
        self.assertEqual(updates[1]["confirmed_by"], ObjectId(user.id))
        self.assertIsNotNone(updates[1]["confirmed_at"])
        self.assertIsNone(updates[2]["confirmed_by"])
        self.assertIsNone(updates[2]["confirmed_at"])

    async def test_confirmation_during_refresh_prevents_write(self):
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        col = SimpleNamespace(find_one=AsyncMock(return_value={"status": "REVIEWING", "report_year": 2024, "report_month": 1}),
                              find_one_and_update=AsyncMock(return_value=None))
        stats = SimpleNamespace(model_dump=lambda: {})
        with patch.object(Mongo, "get_pm_monthly_reports_collection", return_value=col), \
             patch.object(monthly_reports, "_require_pm"), \
             patch.object(monthly_reports, "capture_context", AsyncMock(return_value=(None, None))), \
             patch.object(monthly_reports, "aggregate_period", AsyncMock(return_value=([], [], [], [], stats))):
            with self.assertRaises(HTTPException) as exc:
                await monthly_reports.refresh_monthly_report(str(ObjectId()), user)
        self.assertEqual(exc.exception.status_code, 409)
        query = col.find_one_and_update.await_args.args[0]
        self.assertEqual(query["$or"][0], {"status": {"$in": ["DRAFT", "REVIEWING"]}})

    async def test_confirmed_report_cannot_be_deleted(self):
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        col = SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(matched_count=0)),
                              find_one=AsyncMock(return_value={"status": "CONFIRMED"}))
        feedback_col = SimpleNamespace(find_one=AsyncMock(return_value=None))
        with patch.object(Mongo, "get_pm_monthly_reports_collection", return_value=col), patch.object(Mongo, "get_db", return_value={"pm_monthly_feedback": feedback_col}), patch.object(monthly_reports, "_require_pm"):
            with self.assertRaises(HTTPException) as exc:
                await monthly_reports.delete_monthly_report(str(ObjectId()), user)
        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(col.update_one.await_args.args[0]["status"], {"$ne": "CONFIRMED"})
