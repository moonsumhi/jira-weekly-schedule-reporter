"""Attendance balances retain fractional days through manual-item writes."""
import unittest
from contextlib import ExitStack
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager as M
from app.models.pm.reports import ManualItemCreate, ManualItemPatch
from app.models.user import UserPublic
from app.routers.pm import weekly_reports
from app.services.report_attendance import attendance_remaining


class AttendanceArithmeticTests(unittest.TestCase):
    def test_fractional_days_are_exact(self):
        for accrued, used, expected in [
            ('15.123', '10', '5.123'), ('0.3', '0.1', '0.2'),
            ('12.3456', '7.222', '5.1236'), ('15.000', '15', '0'),
            (0, 0, '0'), ('0', '1.125', '-1.125'), ('1e-3', '.0001', '0.0009'),
            ('100000000000000000000', '.001', '99999999999999999999.999'),
        ]:
            with self.subTest(accrued=accrued, used=used):
                self.assertEqual(attendance_remaining(accrued, used), expected)

    def test_blank_input_clears_balance(self):
        for empty in ('', ' ', None):
            self.assertIsNone(attendance_remaining(empty, '1'))
            self.assertIsNone(attendance_remaining('15', empty))

    def test_invalid_input_is_rejected(self):
        for invalid in ('-1', 'NaN', 'Infinity', 'abc', '1,5'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                attendance_remaining(invalid, '0')


class AttendanceWriteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = UserPublic(id=str(ObjectId()), email='report@example.com', permissions=['pm'])
        self.item = {'_id': ObjectId(), 'section': 'ATTENDANCE', 'title': '담당자',
                     'category': '15.123', 'item_type': '10', 'action_plan': '잘못된 기존 값'}
        self.doc = {'_id': ObjectId(), 'status': 'DRAFT', 'manual_items': [self.item]}
        self.col = SimpleNamespace(find_one=AsyncMock(side_effect=lambda *_: deepcopy(self.doc)),
                                   find_one_and_update=AsyncMock(return_value=deepcopy(self.doc)))
        stack = self.enterContext(ExitStack())
        stack.enter_context(patch.object(M, 'get_pm_weekly_reports_collection', return_value=self.col))
        stack.enter_context(patch.object(weekly_reports, '_doc_to_out', side_effect=lambda d: d))
        stack.enter_context(patch.object(weekly_reports, '_enrich', AsyncMock(side_effect=lambda d, *_: d)))

    async def update(self, **fields):
        await weekly_reports.update_manual_item(str(self.doc['_id']), str(self.item['_id']), ManualItemPatch(**fields), self.user)
        return self.col.find_one_and_update.await_args.args[1]['$set']

    async def test_create_calculates_instead_of_trusting_supplied_balance(self):
        await weekly_reports.add_manual_item(str(self.doc['_id']), ManualItemCreate(
            section='ATTENDANCE', title='담당자', category='15.123', item_type='10', action_plan='999'), self.user)
        saved = self.col.find_one_and_update.await_args.args[1]['$push']['manual_items']
        self.assertEqual(saved['action_plan'], '5.123')
        self.assertEqual(saved['category'], '15.123')

    async def test_partial_update_uses_other_stored_value(self):
        saved = await self.update(item_type='10.001')
        self.assertEqual(saved['manual_items.$[item].action_plan'], '5.122')
        self.assertNotIn('manual_items.$[item].category', saved)

    async def test_clear_explicitly_removes_balance_and_zero_is_saved(self):
        saved = await self.update(category=None)
        self.assertIsNone(saved['manual_items.$[item].action_plan'])
        self.assertIsNone(saved['manual_items.$[item].category'])
        saved = await self.update(category='0', item_type='0')
        self.assertEqual(saved['manual_items.$[item].action_plan'], '0')

    async def test_direct_balance_edit_is_recalculated(self):
        saved = await self.update(action_plan='999')
        self.assertEqual(saved['manual_items.$[item].action_plan'], '5.123')

    async def test_unrelated_fields_and_other_sections_keep_their_values(self):
        saved = await self.update(include_in_report=False)
        self.assertNotIn('manual_items.$[item].action_plan', saved)
        self.item['section'] = 'ISSUE_RISK'
        saved = await self.update(category='보안', item_type='리스크', action_plan='조치 예정')
        self.assertEqual(saved['manual_items.$[item].action_plan'], '조치 예정')

    async def test_invalid_input_and_confirmed_report_are_not_written(self):
        with self.assertRaises(HTTPException) as error:
            await self.update(category='NaN')
        self.assertEqual(error.exception.status_code, 422)
        self.doc['status'] = 'CONFIRMED'
        with self.assertRaises(HTTPException) as error:
            await self.update(category='15')
        self.assertEqual(error.exception.status_code, 403)
        self.col.find_one_and_update.assert_not_awaited()
