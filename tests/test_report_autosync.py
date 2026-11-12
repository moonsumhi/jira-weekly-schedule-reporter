"""Reports follow source issues while preserving authored text and confirmed snapshots."""
import unittest
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.models.pm.reports import WeeklyReportStatusPatch
from app.routers.pm import weekly_reports, monthly_reports
from app.services.report_snapshot import sync_report_snapshot


class ReportAutoSyncTests(unittest.IsolatedAsyncioTestCase):
    def setup_report(self, module, status='DRAFT'):
        self.user = UserPublic(id=str(ObjectId()), email='report@example.com', permissions=['pm'])
        self.doc = {
            '_id': ObjectId(), 'status': status, 'title': '작성자가 정한 제목', 'department': '운영팀',
            'report_year': 2026, 'report_month': 11, 'report_week': 46,
            'start_date': datetime(2026, 11, 9, tzinfo=timezone.utc),
            'end_date': datetime(2026, 11, 15, tzinfo=timezone.utc),
            'updated_at': datetime(2026, 11, 12, tzinfo=timezone.utc),
            'manual_items': [{'title': '수기로 작성한 공지'}],
            'highlights': {'accomplishments': '수동 작성 성과'}, 'insights': [{'title': '수동 안건'}],
            'edit_history': [{'action': '작성'}], 'admin_comment': '검토 의견',
            'all_items': [{'title': '수정 전 업무'}], 'stats': {'total': 1},
        }
        self.writes = []
        async def find(query):
            return deepcopy(self.doc) if self.doc.get('deleted_at') is None else None
        async def update(query, changes, **kwargs):
            if any(self.doc.get(key) != value for key, value in query.items()):
                return None
            self.writes.append(deepcopy(changes))
            self.doc.update(deepcopy(changes.get('$set', {})))
            for key, value in changes.get('$push', {}).items():
                self.doc.setdefault(key, []).append(value)
            return deepcopy(self.doc)
        self.col = SimpleNamespace(find_one=AsyncMock(side_effect=find), find_one_and_update=AsyncMock(side_effect=update))
        self.source = {'title': '최신 업무', 'status': 'DONE'}
        item = SimpleNamespace(model_dump=lambda: deepcopy(self.source))
        self.aggregate = AsyncMock(return_value=([item], [], [], [], SimpleNamespace(model_dump=lambda: {'total': 1, 'completed': 1})))
        stack = ExitStack()
        kind = 'weekly' if module is weekly_reports else 'monthly'
        stack.enter_context(patch.object(M, f'get_pm_{kind}_reports_collection', return_value=self.col))
        stack.enter_context(patch.object(module, 'aggregate_period', self.aggregate))
        stack.enter_context(patch.object(module, '_doc_to_out', side_effect=lambda d: d))
        stack.enter_context(patch.object(module, '_enrich', AsyncMock(side_effect=lambda d, *_: d)))
        if kind == 'weekly':
            stack.enter_context(patch.object(module, '_aggregate_sr', AsyncMock(return_value=SimpleNamespace(model_dump=lambda: {}))))
        else:
            stack.enter_context(patch.object(module, 'capture_context', AsyncMock(return_value=(None, {'inspection_reports': []}))))
        return stack

    async def test_detail_get_tracks_changes_without_touching_authored_content_or_edit_version(self):
        for module in (weekly_reports, monthly_reports):
            for status in ('DRAFT', 'REVIEWING'):
                with self.subTest(module=module.__name__, status=status), self.setup_report(module, status):
                    before = deepcopy(self.doc)
                    get = module.get_weekly_report if module is weekly_reports else module.get_monthly_report
                    result = await get(str(self.doc['_id']), self.user)
                    self.assertEqual(result['all_items'], [self.source])
                    self.source.update(title='다시 수정한 제목', status='IN_PROGRESS')
                    result = await get(str(self.doc['_id']), self.user)
                    self.assertEqual(result['all_items'], [self.source])
                    for key in ('manual_items', 'highlights', 'insights', 'admin_comment', 'title', 'department', 'updated_at', 'edit_history'):
                        self.assertEqual(result[key], before[key])
                        self.assertTrue(all(key not in change['$set'] for change in self.writes))
                    if module is monthly_reports:
                        self.assertTrue(self.aggregate.await_args.kwargs['monthly_actuals'])

    async def test_confirmed_and_archived_reports_keep_their_snapshot(self):
        for module in (weekly_reports, monthly_reports):
            for status in ('CONFIRMED', 'ARCHIVED'):
                with self.subTest(module=module.__name__, status=status), self.setup_report(module, status):
                    get = module.get_weekly_report if module is weekly_reports else module.get_monthly_report
                    result = await get(str(self.doc['_id']), self.user)
                    self.assertEqual(result['all_items'], [{'title': '수정 전 업무'}])
                    self.aggregate.assert_not_awaited()
                    self.assertEqual(self.writes, [])

    async def test_confirmation_captures_latest_issues_and_unlock_resumes_live_data(self):
        for module in (weekly_reports, monthly_reports):
            with self.subTest(module=module.__name__), self.setup_report(module, 'REVIEWING'):
                change = module.change_report_status if module is weekly_reports else module.change_monthly_report_status
                result = await change(str(self.doc['_id']), WeeklyReportStatusPatch(status='CONFIRMED'), self.user)
                self.assertEqual(result['status'], 'CONFIRMED')
                self.assertEqual(result['all_items'], [self.source])
                self.source['title'] = '확정 후 수정한 업무'
                result = await change(str(self.doc['_id']), WeeklyReportStatusPatch(status='REVIEWING'), self.user)
                self.assertEqual(result['all_items'], [self.source])
                self.assertIsNone(result['confirmed_at'])

    async def test_concurrent_confirmation_wins_over_automatic_refresh(self):
        for module in (weekly_reports, monthly_reports):
            with self.subTest(module=module.__name__), self.setup_report(module):
                saved = deepcopy(self.doc['all_items'])
                async def confirm(*_args, **_kwargs):
                    self.doc['status'] = 'CONFIRMED'
                    return None
                self.col.find_one_and_update.side_effect = confirm
                result = await module._sync_snapshot(deepcopy(self.doc))
                self.assertEqual(result['status'], 'CONFIRMED')
                self.assertEqual(result['all_items'], saved)

    async def test_unchanged_data_does_not_write_again(self):
        with self.setup_report(weekly_reports):
            await weekly_reports._sync_snapshot(deepcopy(self.doc))
            self.writes.clear()
            await weekly_reports._sync_snapshot(deepcopy(self.doc))
            self.assertEqual(self.writes, [])

    async def test_legacy_report_without_status_is_live(self):
        with self.setup_report(weekly_reports):
            self.doc.pop('status')
            result = await weekly_reports._sync_snapshot(deepcopy(self.doc))
            self.assertEqual(result['all_items'], [self.source])

    async def test_deleted_during_refresh_returns_not_found(self):
        doc = {'_id': ObjectId(), 'status': 'DRAFT'}
        col = SimpleNamespace(find_one_and_update=AsyncMock(return_value=None), find_one=AsyncMock(return_value=None))
        with self.assertRaises(HTTPException) as error:
            await sync_report_snapshot(col, doc, AsyncMock(return_value={'stats': {'total': 2}}))
        self.assertEqual(error.exception.status_code, 404)

    async def test_newer_snapshot_cannot_be_overwritten_by_an_older_request(self):
        with self.setup_report(weekly_reports):
            stale = deepcopy(self.doc)
            self.doc['aggregated_at'] = datetime(2026, 11, 12, 1, tzinfo=timezone.utc)
            result = await weekly_reports._sync_snapshot(stale)
            self.assertEqual(result['all_items'], [self.source])
            self.assertEqual(self.col.find_one_and_update.await_count, 2)

    async def test_source_failure_does_not_replace_the_saved_snapshot(self):
        with self.setup_report(weekly_reports):
            self.aggregate.side_effect = RuntimeError('temporary failure')
            with self.assertRaises(RuntimeError):
                await weekly_reports._sync_snapshot(deepcopy(self.doc))
            self.assertEqual(self.doc['all_items'], [{'title': '수정 전 업무'}])
            self.assertEqual(self.writes, [])
