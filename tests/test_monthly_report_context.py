import os
import unittest
from io import BytesIO
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.models.pm.reports import MonthlyReportPatch
from app.models.user import UserPublic
from app.routers.pm import monthly_reports
from app.services import monthly_report_context as context
from app.services.monthly_inspection_issues import summarize_inspection


def utc(month, day, hour=0):
    return datetime(2024, month, day, hour, tzinfo=timezone.utc)


class Cursor:
    def __init__(self, values): self.values = values
    def sort(self, *_args): return self
    async def to_list(self, _length): return self.values


class MonthlyContextTests(unittest.IsolatedAsyncioTestCase):
    def test_inspection_issues_include_findings_actions_and_incomplete_issues(self):
        doc = {
            'additional_notes': [{'content': '다음 점검 전 확인'}],
            'snapshot': {
                'source': {'id': 'source'}, 'thresholds': {'warning': 80, 'danger': 90},
                'servers': [
                    {'key': 'a', 'host_name': 'server-a', 'ip': '192.0.2.1',
                     'cpu': {'value': 92}, 'ram': {'value': 50}, 'disk': {'value': 84, 'path': '/data'},
                     'findings': [{'label': 'CPU 92%', 'level': 'danger'}, {'label': '로그 오류', 'level': 'warning'}],
                     'action_items': '로그 확인', 'action': {'is_resolved': False, 'memo': '정리 예정', 'images': ['secret-image']}},
                    {'key': 'b', 'host_name': 'server-b', 'cpu': {'value': 30}, 'ram': {'value': 40},
                     'disk': {'value': 50}, 'findings': [], 'action_items': '이상 없음'},
                    {'key': 'c', 'host_name': 'server-c', 'cpu': {'value': None}, 'ram': {'value': 30},
                     'disk': {'value': 30}, 'findings': []},
                ],
                'unmatched_actions': [{'id': 'u', 'host_name': '미확인', 'is_resolved': False, 'memo': '대상 확인'},
                                      {'id': 'done', 'is_resolved': True, 'memo': '완료'}],
                'missing_asset_resources': [{'id': 'missing', 'name': '작업 대상', 'ip': '192.0.2.3'}],
                'tasks': [{'issue_id': '1', 'month': '2024-01', 'state': 'ROLLED', 'reason': '작업 이월',
                           'issue': {'key': 'TEST-1', 'title': '패치', 'status': 'IN_PROGRESS', 'assignee_name': '담당자'}, 'result': {'follow_up': '다음 달 처리'}},
                          {'issue_id': '2', 'month': '2024-01', 'state': 'ACTIVE', 'issue': {'title': '미완료 작업', 'status': 'TODO'}, 'result': {}},
                          {'issue_id': '3', 'month': '2024-01', 'state': 'ACTIVE', 'overdue': True,
                           'issue': {'title': '완료 작업', 'status': 'DONE'}, 'result': {'follow_up': '완료 후 확인'}},
                          {'issue_id': '4', 'month': '2024-01', 'state': 'ACTIVE', 'issue': {'title': '기존 완료 상태', 'status': 'IMPLEMENTED'}},
                          {'issue_id': '5', 'month': '2024-01', 'state': 'EXCLUDED', 'issue': {'title': '제외 작업', 'status': 'TODO'}},
                          {'issue_id': '6', 'month': '2024-01', 'state': 'ACTIVE', 'source_type': 'WORK_PLAN', 'issue': {'title': '작업 계획서', 'status': 'TODO'}}],
                'carryover': [{'issue_id': '7', 'month': '2023-12', 'state': 'ROLLED', 'issue': {'title': '이전 월 이슈', 'status': 'TODO'}}],
            },
        }
        result = summarize_inspection(doc)
        self.assertEqual([item['host_name'] for item in result['issues']], ['server-a', 'server-c', '작업 대상', '미확인'])
        self.assertEqual(result['issues'][0]['severity'], 'danger')
        self.assertEqual([x['label'] for x in result['issues'][0]['findings']], ['CPU 92%', '디스크 84% · /data', '로그 오류'])
        self.assertEqual(result['issues'][0]['action_memo'], '정리 예정')
        self.assertNotIn('images', result['issues'][0])
        self.assertEqual([item['title'] for item in result['incomplete_issues']], ['패치', '미완료 작업'])
        self.assertEqual(result['incomplete_issues'][0]['detail'], '다음 달 처리')
        self.assertEqual(result['incomplete_issues'][0]['reason'], '작업 이월')
        self.assertEqual(result['incomplete_issues'][1]['status'], '할 일')
        self.assertTrue(result['task_data_available'])
        self.assertEqual(result['notes'], ['다음 점검 전 확인'])
        self.assertTrue(result['source_available'])

    def test_legacy_notes_and_missing_source_are_not_labeled_normal(self):
        result = summarize_inspection({'limitations': '점검 범위 확인 필요', 'snapshot': {}})
        self.assertEqual(result['notes'], ['점검 범위 확인 필요'])
        self.assertFalse(result['source_available'])
        self.assertEqual(result['issues'], [])
        self.assertFalse(result['task_data_available'])
        self.assertFalse(summarize_inspection({'snapshot': {'source': {'id': 'source'}, 'servers': []}})['source_available'])

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
        inspection_find = MagicMock(return_value=Cursor(inspections))
        db = {
            M.SERVICE_REQUESTS: SimpleNamespace(find=lambda _q: Cursor(sr_docs)),
            M.SR_STATUS_HISTORIES: SimpleNamespace(find=lambda _q: Cursor(histories)),
            "monthly_inspection_reports": SimpleNamespace(find=inspection_find),
        }
        start, end = monthly_reports._month_range(2024, 1)
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=report_col), patch.object(M, "get_db", return_value=db):
            comparison, summary = await context.capture_context(2024, 1, "운영팀", start, end)
        self.assertEqual(comparison["report_id"], str(previous["_id"]))
        query = report_col.find_one.await_args.args[0]
        self.assertEqual((query["report_year"], query["report_month"], query["department"], query["status"]), (2023, 12, "운영팀", "CONFIRMED"))
        self.assertEqual(query["aggregation_version"], context.AGGREGATION_VERSION)
        self.assertEqual(summary["sr"], {"received": 2, "completed": 1, "open": 1})
        inspection_query = inspection_find.call_args.args[0]
        self.assertEqual(inspection_query["month"], "2023-12")
        self.assertEqual(inspection_query["state"], "FINAL")
        self.assertEqual(inspection_query["kind"], {"$in": ["RESULT", None]})
        self.assertIn("$lte", inspection_query["finalized_at"])
        self.assertEqual(summary["inspection_month"], "2023-12")
        self.assertEqual(len(summary["inspection_reports"]), 1)
        self.assertEqual(summary["inspection_reports"][0]["done"], 4)

    async def test_inspection_month_is_previous_month_not_report_month(self):
        report_col = SimpleNamespace(find_one=AsyncMock(return_value=None))
        inspection_find = MagicMock(return_value=Cursor([]))
        db = {
            M.SERVICE_REQUESTS: SimpleNamespace(find=lambda _q: Cursor([])),
            M.SR_STATUS_HISTORIES: SimpleNamespace(find=lambda _q: Cursor([])),
            "monthly_inspection_reports": SimpleNamespace(find=inspection_find),
        }
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=report_col), patch.object(M, "get_db", return_value=db):
            for year, month, expected in ((2024, 2, '2024-01'), (2026, 11, '2026-10')):
                with self.subTest(report_month=(year, month)):
                    start, end = monthly_reports._month_range(year, month)
                    _, summary = await context.capture_context(year, month, "운영팀", start, end)
                    self.assertEqual(inspection_find.call_args.args[0]['month'], expected)
                    self.assertEqual(summary['inspection_month'], expected)

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
             patch.object(monthly_reports, "_require_pm"), patch.object(monthly_reports, "_sync_snapshot", AsyncMock(side_effect=lambda doc: doc)), \
             patch.object(monthly_reports, "_user_name", AsyncMock(return_value="사용자")):
            response = await monthly_reports.export_monthly_detail(str(doc["_id"]), user)
            content = b"".join([chunk async for chunk in response.body_iterator])
        workbook = openpyxl.load_workbook(BytesIO(content))
        self.assertEqual(workbook["월간 요약"]["B1"].value, "=1+1")
        self.assertEqual(workbook["월간 요약"]["B1"].data_type, "s")
        self.assertEqual(workbook["주요 항목"]["B2"].data_type, "s")
        self.assertNotIn("SR 현황", [cell.value for cell in workbook["월간 요약"]["A"]])
        self.assertNotIn("비공개 점검", [cell.value for cell in workbook["월간 요약"]["B"]])

    async def test_excel_labels_inspection_month_and_legacy_snapshot(self):
        import openpyxl

        user = UserPublic(id=str(ObjectId()), email="pm@example.com", permissions=["pm", "server_check"])
        doc = {
            "_id": ObjectId(), "report_year": 2024, "report_month": 2, "title": "월간 보고",
            "created_by": ObjectId(user.id), "created_at": utc(2, 1), "updated_at": utc(2, 1),
            "operational_summary": {"inspection_month": "2024-01", "inspection_detail_version": 2,
                                    "inspection_reports": [{"title": "점검 결과", "source_available": True,
                                        "issues": [{"host_name": "server-a", "ip": "192.0.2.1", "findings": [{"label": "CPU 92%"}],
                                                    "action_status": "pending", "action_memo": "확인 중"}],
                                        "task_data_available": True,
                                        "incomplete_issues": [{"status": "이월", "title": "패치", "detail": "다음 달 처리"}],
                                        "notes": ["점검 추가 내용"]}]},
        }
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc))
        with patch.object(M, "get_pm_monthly_reports_collection", return_value=col), \
             patch.object(monthly_reports, "_require_pm"), patch.object(monthly_reports, "_sync_snapshot", AsyncMock(side_effect=lambda doc: doc)), \
             patch.object(monthly_reports, "_user_name", AsyncMock(return_value="사용자")):
            for month, expected in (("2024-01", "서버 점검 (2024-01)"), (None, "서버 점검 (기준 변경 전)")):
                with self.subTest(inspection_month=month):
                    if month:
                        doc["operational_summary"]["inspection_month"] = month
                    else:
                        doc["operational_summary"].pop("inspection_month", None)
                    response = await monthly_reports.export_monthly_detail(str(doc["_id"]), user)
                    content = b"".join([chunk async for chunk in response.body_iterator])
                    workbook = openpyxl.load_workbook(BytesIO(content))
                    self.assertIn(expected, [cell.value for cell in workbook["월간 요약"]["A"]])
                    contents = [cell.value for cell in workbook["월간 요약"]["B"] if cell.value]
                    self.assertTrue(any('CPU 92%' in value and '확인 중' in value for value in contents))
                    self.assertTrue(any('다음 달 처리' in value for value in contents))
            doc['operational_summary']['inspection_detail_version'] = 1
            doc['operational_summary']['inspection_reports'][0].pop('incomplete_issues')
            response = await monthly_reports.export_monthly_detail(str(doc['_id']), user)
            content = b"".join([chunk async for chunk in response.body_iterator])
            workbook = openpyxl.load_workbook(BytesIO(content))
            contents = [cell.value for cell in workbook['월간 요약']['B'] if cell.value]
            self.assertTrue(any('재집계하면 미완료 이슈' in value for value in contents))
            self.assertTrue(any('CPU 92%' in value for value in contents))


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB tests only')
class MonthlyInspectionMongoTests(unittest.IsolatedAsyncioTestCase):
    async def test_previous_year_final_result_only_and_latest_revision(self):
        M._client = None
        real_db = M.get_db()
        prefix = 'test_monthly_inspection_' + uuid4().hex + '_'
        names = set()

        class TestDB:
            def __getitem__(self, name):
                full = prefix + name
                names.add(full)
                return real_db[full]

        test_db = TestDB()
        try:
            reports = test_db['monthly_inspection_reports']
            completed = datetime(2023, 12, 31, tzinfo=timezone.utc)
            await reports.insert_many([
                {'month': '2023-12', 'scope_key': 'server', 'revision': 1, 'state': 'FINAL', 'kind': 'RESULT', 'finalized_at': completed, 'title': '구버전'},
                {'month': '2023-12', 'scope_key': 'server', 'revision': 2, 'state': 'FINAL', 'kind': 'RESULT', 'finalized_at': completed,
                 'title': '전월 최신', 'snapshot': {'stats': {'done': 4}, 'source': {'id': 'source'},
                     'servers': [{'key': 'db', 'host_name': 'DB-01', 'cpu': {'value': 91}, 'ram': {'value': 20},
                                  'disk': {'value': 30}, 'findings': [], 'action': {'is_resolved': False, 'memo': '확인 예정'}}]}},
                {'month': '2023-12', 'scope_key': 'draft', 'revision': 1, 'state': 'DRAFT', 'kind': 'RESULT', 'finalized_at': completed, 'title': '미확정'},
                {'month': '2023-12', 'scope_key': 'plan', 'revision': 1, 'state': 'FINAL', 'kind': 'PLAN', 'finalized_at': completed, 'title': '계획서'},
                {'month': '2023-12', 'scope_key': 'future', 'revision': 1, 'state': 'FINAL', 'kind': 'RESULT', 'finalized_at': datetime(2999, 1, 1, tzinfo=timezone.utc), 'title': '미래 확정'},
                {'month': '2024-01', 'scope_key': 'current', 'revision': 1, 'state': 'FINAL', 'kind': 'RESULT', 'finalized_at': completed, 'title': '당월'},
            ])
            start, end = monthly_reports._month_range(2024, 1)
            with patch.object(M, 'get_db', return_value=test_db):
                _, summary = await context.capture_context(2024, 1, '운영팀', start, end)
            self.assertEqual(summary['inspection_month'], '2023-12')
            self.assertEqual([r['title'] for r in summary['inspection_reports']], ['전월 최신'])
            self.assertEqual(summary['inspection_reports'][0]['done'], 4)
            self.assertEqual(summary['inspection_detail_version'], 2)
            issue = summary['inspection_reports'][0]['issues'][0]
            self.assertEqual((issue['host_name'], issue['severity'], issue['action_memo']), ('DB-01', 'danger', '확인 예정'))
        finally:
            for name in names:
                await real_db.drop_collection(name)
            M.get_client().close()
            M._client = None
