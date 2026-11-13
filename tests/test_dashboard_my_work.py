"""Home work items are assignee-scoped and do not lose older overdue issues."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm import dashboard


class Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args):
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length):
        return [dict(doc) for doc in self.docs]


class DashboardMyWorkTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, records):
        user_id, other_id = ObjectId(), ObjectId()
        user = UserPublic(id=str(user_id), email='worker@example.com', permissions=['pm'])
        docs = [dict(_id=ObjectId(), assignee_id=user_id if owner == 'me' else other_id if owner == 'other' else None,
                     reporter_id=user_id, status=status, type=issue_type, marker=marker)
                for owner, status, marker, issue_type in records]
        queries = []

        def find(query):
            queries.append(query)
            return Cursor([doc for doc in docs if doc['assignee_id'] == query.get('assignee_id')
                           and doc['status'] not in query.get('status', {}).get('$nin', [])
                           and doc['type'] != query.get('type', {}).get('$ne')])

        async def enrich(doc):
            return {'id': str(doc['_id']), 'assignee_id': str(doc['assignee_id']), 'status': doc['status'], 'marker': doc['marker']}

        app = FastAPI()
        app.include_router(dashboard.router, prefix='/pm/dashboard')
        app.dependency_overrides[get_current_user] = lambda: user
        with patch.object(dashboard.MongoClientManager, 'get_pm_issues_collection', return_value=SimpleNamespace(find=find)), \
             patch.object(dashboard, 'enrich_issue', AsyncMock(side_effect=enrich)), \
             patch.object(dashboard, 'attach_linked_sr_info', AsyncMock()) as attach:
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                response = await client.get('/pm/dashboard/my-issues', params={'assignee_id': str(other_id)})
            self.assertEqual(response.status_code, 200, response.text)
            attach.assert_awaited_once()
        return response.json(), queries, user_id

    async def test_only_current_assignee_open_issues_even_when_client_supplies_another_user(self):
        rows, queries, user_id = await self.exercise([
            ('me', 'TODO', 'mine', 'TASK'), ('me', 'IN_PROGRESS', 'working', 'STORY'),
            ('me', 'BACKLOG', 'backlog', 'TASK'), ('me', 'TODO', 'epic', 'EPIC'),
            ('me', 'DONE', 'done', 'TASK'), ('me', 'IMPLEMENTED', 'legacy', 'TASK'),
            ('other', 'IN_PROGRESS', 'reported-by-me', 'TASK'), (None, 'TODO', 'unassigned', 'TASK'),
        ])
        self.assertEqual([row['marker'] for row in rows], ['mine', 'working', 'backlog'])
        self.assertEqual(queries[0]['assignee_id'], user_id)
        self.assertEqual(queries[0]['type'], {'$ne': 'EPIC'})

    async def test_more_than_fifty_recent_issues_do_not_hide_older_work(self):
        rows, _, _ = await self.exercise([('me', 'TODO', str(i), 'TASK') for i in range(60)] + [('me', 'IN_PROGRESS', 'old-overdue', 'TASK')])
        self.assertEqual(len(rows), 61)
        self.assertEqual(rows[-1]['marker'], 'old-overdue')

    async def test_empty_assignment_returns_an_empty_list(self):
        rows, _, _ = await self.exercise([])
        self.assertEqual(rows, [])
