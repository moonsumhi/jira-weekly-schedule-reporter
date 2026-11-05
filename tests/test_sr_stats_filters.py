"""The SR cards and list agree when filters and status categories are combined."""
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.sr.admin_requests import router


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB tests only')
class SRStatsFilterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        self.prefix = 'test_sr_stats_' + uuid4().hex + '_'
        self.names = set()
        parent = self

        class TestDB:
            def __getitem__(self, name):
                full = parent.prefix + name
                parent.names.add(full)
                return parent.real_db[full]

        self.db = TestDB()
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.user = UserPublic(id=str(ObjectId()), email='sr-test@example.com', is_admin=True)
        self.other = ObjectId()
        app = FastAPI()
        app.include_router(router, prefix='/sr')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        docs = []
        for index, (assignee, status) in enumerate([
            (self.user.id, 'IN_PROGRESS'), (self.user.id, 'COMPLETED'), (self.user.id, 'CONFIRMING'),
            (self.user.id, 'CLOSED'), (self.user.id, 'ON_HOLD'), (self.user.id, 'REJECTED'),
            (self.user.id, 'DRAFT'), (str(self.other), 'IN_PROGRESS'), (str(self.other), 'CLOSED'),
        ]):
            docs.append({'_id': ObjectId(), 'sr_no': f'SR-{index}', 'title': f'요청 {index}', 'status': status,
                         'request_type': 'SERVER_INFRA', 'requester_id': str(ObjectId()), 'requester_name': '요청자',
                         'requester_department': '운영팀' if index % 2 == 0 else '구축팀',
                         'priority': 'HIGH' if index == 0 else 'MEDIUM', 'is_urgent': index == 0,
                         'assignee_id': ObjectId(assignee), 'assignee_name': '담당자',
                         'created_at': created, 'updated_at': created,
                         'planned_due_date': datetime(2000, 1, 1, tzinfo=timezone.utc) if index == 0 else None,
                         'deleted_at': None})
        await self.db[M.SERVICE_REQUESTS].insert_many(docs)

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def fetch(self, path, params):
        response = await self.client.get('/sr' + path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_my_assigned_cards_match_list_status_groups(self):
        params = {'my_assigned': 'true'}
        stats = await self.fetch('/stats/summary', params)
        self.assertEqual((stats['total'], stats['in_progress'], stats['completed'], stats['on_hold'], stats['rejected']), (6, 3, 1, 1, 1))
        for selected, expected in [('', 'total'), ('IN_PROGRESS,COMPLETED,CONFIRMING', 'in_progress'),
                                   ('CLOSED', 'completed'), ('ON_HOLD', 'on_hold'), ('REJECTED', 'rejected')]:
            query = {**params, **({'status': selected} if selected else {})}
            result = await self.fetch('', query)
            self.assertEqual(result['total'], stats[expected], selected)
            self.assertTrue(all(item['assignee_id'] == self.user.id for item in result['items']))
        stats_with_status = await self.fetch('/stats/summary', {**params, 'status': 'CLOSED'})
        self.assertEqual(stats_with_status['total'], stats['total'])

    async def test_stats_and_list_share_search_multi_select_and_delay_filters(self):
        filters = {'my_assigned': 'true', 'requester_department_in': json.dumps(['운영팀', '구축팀']),
                   'is_urgent': 'true', 'is_delayed': 'true', 'search': '요청 0'}
        stats = await self.fetch('/stats/summary', filters)
        results = await self.fetch('', filters)
        self.assertEqual((stats['total'], stats['in_progress'], stats['delayed']), (1, 1, 1))
        self.assertEqual(results['total'], stats['total'])
        self.assertEqual(results['items'][0]['sr_no'], 'SR-0')
        none = await self.fetch('/stats/summary', {'my_assigned': 'true', 'assignee_id': str(self.other)})
        self.assertEqual(none['total'], 0)
