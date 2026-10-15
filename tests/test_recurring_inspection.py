"""반복 업무의 월별 점검 연결 및 실패 후 재시도 회귀 테스트."""
import unittest
from copy import deepcopy
from datetime import datetime
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from bson import ObjectId
from app.models.pm.recurring_issue import RecurringIssueTemplateCreate, RecurringIssueTemplatePatch
from app.services.pm import recurring_issue_service as recurring
from app.services import inspection_service as inspection


class RecurringInspectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.template = {'_id': ObjectId(), 'project_id': ObjectId(),
                         'created_by_id': ObjectId(), 'name': '점검',
                         'blueprint': {'title': '월간 작업'},
                         'rule': {'days_of_month': [1], 'time': '00:00'},
                         'include_in_inspection': True, 'lead_days': 3}
        self.issues = []
        self.items = []
        async def insert(doc):
            doc = {**doc, '_id': ObjectId()}
            self.issues.append(doc)
            return SimpleNamespace(inserted_id=doc['_id'])
        async def find(query):
            return next((d for d in self.issues if all(d.get(k) == v for k, v in query.items())), None)
        async def mutate(iid, pid, transform):
            transform(self.items)
        col = SimpleNamespace(insert_one=AsyncMock(side_effect=insert), find_one=AsyncMock(side_effect=find))
        for target, kwargs in [
            ('app.services.pm.recurring_issue_service._issues_col', {'return_value': col}),
            ('app.services.pm.recurring_issue_service.next_issue_number', {'new': AsyncMock(return_value=1)}),
            ('app.services.inspection_service.issue_snapshot', {'new': AsyncMock(return_value={'title': '월간 작업'})}),
            ('app.services.inspection_service.mutate', {'new': AsyncMock(side_effect=mutate)}),
        ]:
            p = patch(target, **kwargs)
            p.start()
            self.addCleanup(p.stop)

    async def test_manual_generation_registers_once_and_preserves_exclusion(self):
        result = await recurring.generate_month(self.template, 2026, 11)
        self.assertEqual(len(result['created']), 1)
        self.assertEqual(self.items[0]['month'], '2026-11')
        self.assertTrue(self.items[0]['common'])
        self.assertEqual(self.items[0]['assets'], [])
        self.items[0]['state'] = 'EXCLUDED'
        before = deepcopy(self.items)
        result = await recurring.generate_month(self.template, 2026, 11)
        self.assertEqual(len(result['skipped']), 1)
        self.assertEqual(self.items, before)
        self.assertEqual(len(self.issues), 1)

    async def test_automatic_lead_generation_uses_occurrence_month(self):
        await recurring.generate_due(self.template, datetime(2026, 10, 30))
        self.assertEqual(self.items[0]['month'], '2026-11')
        self.assertEqual(self.issues[0]['start_date'].month, 10)  # UTC 자정 경계
        await recurring.generate_due(self.template, datetime(2026, 10, 31))
        self.assertEqual(len(self.items), 1)

    async def test_existing_templates_default_off_and_updates_apply_to_future_issues(self):
        self.template.pop('include_in_inspection')
        await recurring.generate_month(self.template, 2026, 10)
        self.assertEqual(self.items, [])
        self.template['include_in_inspection'] = True
        await recurring.generate_month(self.template, 2026, 10)
        self.assertEqual(self.items, [])
        await recurring.generate_month(self.template, 2026, 11)
        self.assertEqual(self.items[0]['month'], '2026-11')
        self.template['include_in_inspection'] = False
        await recurring.generate_month(self.template, 2026, 12)
        self.assertEqual(len(self.items), 1)

    async def test_registration_failure_is_retried_without_duplicate_issue(self):
        with patch.object(inspection, 'mutate', new=AsyncMock(side_effect=RuntimeError('temporary'))):
            with self.assertRaises(RuntimeError):
                await recurring.generate_month(self.template, 2026, 11)
        self.assertEqual(len(self.issues), 1)
        await recurring.generate_month(self.template, 2026, 11)
        self.assertEqual(len(self.issues), 1)
        self.assertEqual(len(self.items), 1)

    def test_payload_defaults_and_patch_false(self):
        payload = {k: v for k, v in self.template.items() if k not in ('_id', 'created_by_id', 'include_in_inspection')}
        payload['project_id'] = str(payload['project_id'])
        self.assertFalse(RecurringIssueTemplateCreate(**payload).include_in_inspection)
        self.assertFalse(RecurringIssueTemplatePatch(include_in_inspection=False).model_dump()['include_in_inspection'])
        self.assertIsNone(RecurringIssueTemplatePatch().include_in_inspection)
