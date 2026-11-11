"""Project-wide issue search permissions and pagination using isolated collections."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm.projects import router


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Requires explicit isolated MongoDB test run')
class ProjectIssueSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        prefix = 'test_project_issue_search_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                self.names.add(prefix + name)
                return self.real_db[prefix + name]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.user = UserPublic(id=str(ObjectId()), email='issue-search@example.com')
        self.visible, self.other, self.deleted = ObjectId(), ObjectId(), ObjectId()
        now = datetime.now(timezone.utc)
        await M.get_pm_projects_collection().insert_many([
            {'_id': self.visible, 'name': '검색 권한 프로젝트', 'key': 'VISIBLE'},
            {'_id': self.other, 'name': '다른 팀 프로젝트', 'key': 'PRIVATE'},
            {'_id': self.deleted, 'name': '삭제 프로젝트', 'key': 'DELETED', 'deleted_at': now},
        ])
        await M.get_pm_project_members_collection().insert_many([
            {'user_id': ObjectId(self.user.id), 'project_id': self.visible},
            {'user_id': ObjectId(self.user.id), 'project_id': self.deleted},
            {'user_id': ObjectId(), 'project_id': self.other},
        ])

        def issue(project_id, number, title='검색 대상', **values):
            return {
                '_id': ObjectId(), 'project_id': project_id, 'number': number,
                'title': title, 'type': 'TASK', 'status': 'TODO',
                'updated_at': now - timedelta(minutes=number), **values,
            }

        self.visible_issues = [
            issue(self.visible, 1), issue(self.visible, 2, status='IMPLEMENTED'),
            issue(self.visible, 3, type='SUB_TASK'),
        ]
        await M.get_pm_issues_collection().insert_many([
            *self.visible_issues,
            issue(self.other, 4), issue(self.deleted, 5), issue(ObjectId(), 6),
            issue(self.visible, 7, deleted_at=now), issue(self.visible, 8, is_deleted=True),
            issue(self.visible, 9, '정규식 (*) 제목'), issue(self.visible, 10, 'CPU 설정'),
        ])
        self.app = FastAPI()
        self.app.include_router(router, prefix='/pm/projects')
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def search(self, query='검색', **params):
        return await self.client.get('/pm/projects/search/issues', params={'q': query, **params})

    async def test_members_only_receive_accessible_projects_and_project_identity(self):
        response = await self.search()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual([item['number'] for item in data['items']], [1, 2, 3])
        self.assertFalse(data['hasMore'])
        for item in data['items']:
            self.assertEqual(item['projectId'], str(self.visible))
            self.assertEqual(item['projectName'], '검색 권한 프로젝트')
            self.assertEqual(item['projectKey'], 'VISIBLE')
            self.assertEqual(item['key'], f"VISIBLE-{item['number']}")
            self.assertNotIn('description', item)
        self.assertEqual(data['items'][1]['status'], 'DONE')
        self.assertEqual(data['items'][2]['type'], 'SUB_TASK')

    async def test_admin_can_search_other_projects_but_not_deleted_or_orphaned_issues(self):
        self.user.is_admin = True
        response = await self.search()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item['number'] for item in response.json()['items']], [1, 2, 3, 4])

    async def test_nonmember_cannot_find_private_project_by_matching_title(self):
        self.user.id = str(ObjectId())
        response = await self.search()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'items': [], 'hasMore': False})

    async def test_search_is_trimmed_case_insensitive_and_regex_is_literal(self):
        for query, number in [('  (*)  ', 9), ('cpu', 10)]:
            with self.subTest(query=query):
                response = await self.search(query)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([item['number'] for item in response.json()['items']], [number])
        self.assertEqual((await self.search('.*')).json()['items'], [])
        self.assertEqual((await self.search('   ')).json(), {'items': [], 'hasMore': False})

    async def test_pagination_keeps_stable_order_without_duplicates(self):
        first = (await self.search(limit=2)).json()
        second = (await self.search(limit=2, offset=2)).json()
        final = (await self.search(limit=2, offset=4)).json()
        self.assertEqual([item['number'] for item in first['items']], [1, 2])
        self.assertTrue(first['hasMore'])
        self.assertEqual([item['number'] for item in second['items']], [3])
        self.assertFalse(second['hasMore'])
        self.assertEqual(final, {'items': [], 'hasMore': False})

    async def test_query_and_pagination_bounds(self):
        for params in ({'q': ''}, {'q': 'a' * 201}, {'limit': 0}, {'limit': 101},
                       {'offset': -1}, {'offset': 1_000_001}):
            with self.subTest(params=params):
                response = await self.client.get('/pm/projects/search/issues', params={'q': '검색', **params})
                self.assertEqual(response.status_code, 422, response.text)

    async def test_authentication_is_required(self):
        self.app.dependency_overrides.clear()
        response = await self.search()
        self.assertEqual(response.status_code, 401)
