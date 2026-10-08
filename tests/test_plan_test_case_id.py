import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.db.startup import _PLAN_TEST_CASES, migrate_plan_test_case_id_field


class PlanTestCaseIdTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_plan_template_gets_id_first_without_replacing_other_fields(self):
        original_fields = [{'label': '설명', 'type': 'text'}]
        already_updated = [
            {'label': '테스트케이스 ID', 'type': 'text'},
            {'label': '설명', 'type': 'text'},
        ]

        async def templates():
            yield {'_id': 'old', 'sections': [{'title': '테스트 케이스', 'fields': original_fields}]}
            yield {'_id': 'new', 'sections': [{'title': '테스트 계획', 'fields': already_updated}]}

        collection = SimpleNamespace(find=Mock(return_value=templates()), update_one=AsyncMock())
        with patch('app.db.startup.MongoClientManager.get_form_templates_collection', return_value=collection):
            await migrate_plan_test_case_id_field()

        update = collection.update_one.await_args
        self.assertEqual(update.args[0], {'_id': 'old'})
        fields = update.args[1]['$set']['sections.0.fields']
        self.assertEqual([field['label'] for field in fields], ['테스트케이스 ID', '설명'])
        self.assertEqual(original_fields, [{'label': '설명', 'type': 'text'}])
        self.assertEqual(collection.update_one.await_count, 1)

    async def test_seeded_plan_template_has_id_before_description(self):
        self.assertEqual([field['label'] for field in _PLAN_TEST_CASES['fields'][:2]],
                         ['테스트케이스 ID', '설명'])
