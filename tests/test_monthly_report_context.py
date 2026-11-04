import unittest
from io import BytesIO
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.models.pm.reports import MonthlyReportPatch
from app.models.user import UserPublic
from app.routers.pm import monthly_reports
from app.services import monthly_report_context as context


def utc(month, day, hour=0):
    return datetime(2024, month, day, hour, tzinfo=timezone.utc)


class Cursor:
    def __init__(self, values): self.values = values
    def sort(self, *_args): return self
    async def to_list(self, _length): return self.values


class MonthlyContextTests(unittest.IsolatedAsyncioTestCase):
    def test_operational_data_obeys_separate_menu_permissions(self):
        summary = {"sr": {"received": 2}, "inspection_reports": [{"title": "결과"}]}
        report = SimpleNamespace(operational_summary=summary)
        user = UserPublic(id=str(ObjectId()), email="pm@example.com", permissions=["pm", "sr"])
        monthly_reports._mask_operational(report, user)
        self.assertEqual(report.operational_summary["sr"], {"received": 2})
        self.assertIsNone(report.operational_summary["inspection_reports"])
        self.assertEqual(len(summary["inspection_reports"]), 1)

    async def test_comparison_and_operational_data_use_snapshot_and_month_boundaries(self):
        a, b = ObjectId(), ObjectId()
        previous = {"_id": ObjectId(), "title": "전월", "stats": {"completed": 4}}
        report_col = SimpleNamespace(find_one=AsyncMock(return_value=previous))
        sr_docs = [
            {"_id": a, "created_at": utc(1, 2), "status": "COMPLETED", "actual_completed_at": utc(2, 1)},
            {"_id": b, "created_at": utc(1, 5), "status": "COMPLETED", "actual_completed_at": utc(1, 25)},
        ]
        histories = [
            {"sr_id": str(a), "previous_status": "", "new_status": "SUBMITTED", "changed_at": utc(1, 2)},
            {"sr_id": str(a), "previous_status": "IN_PROGRESS", "new_status": "COMPLETED", "changed_at": utc(2, 1)},
            {"sr_id": str(b), "previous_status": "", "new_status": "SUBMITTED", "changed_at": utc(1, 5)},
            {"sr_id": str(b), "previous_status": "IN_PROGRESS", "new_status": "COMPLETED", "changed_at": utc(1, 25)},
        ]
        inspections = [
            {"_id": ObjectId(), "scope_key": "one", "title": "점검 최신", "snapshot": {"stats": {"planned": 5, "done": 4}}},
            {"_id": ObjectId(), "scope_key": "one", "title": "구버전", "snapshot": {"stats": {"planned": 99}}},
        ]
        db = {
            M.SERVICE_REQUESTS: SimpleNamespace(find=lambda _q: Cursor(sr_docs)),
            M.SR_STATUS_HISTORIES: SimpleNamespace(find=lambda _q: Cursor(histories)),
            "monthly_inspection_reports": SimpleNamespace(find=lambda _q: Cursor(inspections)),
        }
        start, end = monthly_reports._month_range(2024, 1)
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=report_col), patch.object(M, "get_db", return_value=db):
            comparison, summary = await context.capture_context(2024, 1, "운영팀", start, end)
        self.assertEqual(comparison["report_id"], str(previous["_id"]))
        query = report_col.find_one.await_args.args[0]
        self.assertEqual((query["report_year"], query["report_month"], query["department"], query["status"]), (2023, 12, "운영팀", "CONFIRMED"))
        self.assertEqual(query["aggregation_version"], context.AGGREGATION_VERSION)
        self.assertEqual(summary["sr"], {"received": 2, "completed": 1, "open": 1})
        self.assertEqual(len(summary["inspection_reports"]), 1)
        self.assertEqual(summary["inspection_reports"][0]["done"], 4)

    async def test_edit_rejects_stale_content_and_keeps_user_input(self):
        user = UserPublic(id=str(ObjectId()), email="test@example.com")
        col = SimpleNamespace(find_one=AsyncMock(return_value={"status": "REVIEWING"}), find_one_and_update=AsyncMock(return_value=None))
        body = MonthlyReportPatch(highlights={"accomplishments": "새 성과"}, expected_updated_at=utc(1, 1))
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=col), patch.object(monthly_reports, "_require_pm"):
            with self.assertRaises(HTTPException) as exc:
                await monthly_reports.patch_monthly_report(str(ObjectId()), body, user)
        self.assertEqual(exc.exception.status_code, 409)
        query, update = col.find_one_and_update.await_args.args
        self.assertEqual(query["updated_at"], utc(1, 1))
        self.assertEqual(update["$set"]["highlights"]["accomplishments"], "새 성과")
        self.assertNotIn("expected_updated_at", update["$set"])

    async def test_excel_includes_summary_and_safe_text_without_restricted_metrics(self):
        import openpyxl

        user = UserPublic(id=str(ObjectId()), email="pm@example.com", permissions=["pm"])
        doc = {
            "_id": ObjectId(), "report_year": 2024, "report_month": 1, "title": "월간 보고",
            "created_by": ObjectId(user.id), "created_at": utc(1, 1), "updated_at": utc(1, 1),
            "highlights": {"accomplishments": "=1+1"},
            "insights": [{"id": "a", "kind": "ISSUE_RISK", "title": "=2+2"}],
            "operational_summary": {"sr": {"received": 1}, "inspection_reports": [{"title": "비공개 점검"}]},
        }
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc))
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=col), \
             patch.object(monthly_reports, "_require_pm"), patch.object(monthly_reports, "_user_name", AsyncMock(return_value="사용자")):
            response = await monthly_reports.export_monthly_detail(str(doc["_id"]), user)
            content = b"".join([chunk async for chunk in response.body_iterator])
        workbook = openpyxl.load_workbook(BytesIO(content))
        self.assertEqual(workbook["월간 요약"]["B1"].value, "=1+1")
        self.assertEqual(workbook["월간 요약"]["B1"].data_type, "s")
        self.assertEqual(workbook["주요 항목"]["B2"].data_type, "s")
        self.assertNotIn("SR 현황", [cell.value for cell in workbook["월간 요약"]["A"]])
