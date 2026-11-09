"""Work-status filtering, using only opt-in UUID-prefixed MongoDB collections."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm import work_status


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB run required')
class WorkStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        self.prefix = 'test_work_status_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                collection_name = self.prefix + name
                self.names.add(collection_name)
                return self.real_db[collection_name]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.enrich_patch = patch.object(work_status, 'enrich_issue', AsyncMock(side_effect=self.issue_out))
        self.enrich_patch.start()
        self.issues = M.get_pm_issues_collection()
        self.pid = ObjectId()
        self.number = 0
        self.start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 11, 8, tzinfo=timezone.utc)
        self.old = self.start - timedelta(days=10)

        user = UserPublic(id=str(ObjectId()), email='work-status@example.com', permissions=['pm'])
        app = FastAPI()
        app.include_router(work_status.router, prefix='/pm')
        app.dependency_overrides[get_current_user] = lambda: user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        try:
            await self.client.aclose()
            for name in self.names:
                self.assertTrue(name.startswith(self.prefix))
                await self.real_db.drop_collection(name)
        finally:
            self.enrich_patch.stop()
            self.db_patch.stop()
            M.get_client().close()
            M._client = None

    @staticmethod
    def issue_out(doc):
        result = dict(doc)
        result['id'] = str(result.pop('_id'))
        for field in ('project_id', 'epic_id', 'parent_issue_id'):
            result[field] = str(result[field]) if result.get(field) else None
        return result

    async def add_issue(self, issue_type='TASK', **values):
        self.number += 1
        doc = {
            '_id': ObjectId(), 'project_id': self.pid, 'number': self.number,
            'title': f'Work {self.number}', 'description': None,
            'type': issue_type, 'status': 'TODO', 'priority': 'MEDIUM',
            'assignee_id': None, 'assignee_name': None,
            'reporter_id': None, 'reporter_name': None,
            'sprint_id': None, 'epic_id': None, 'parent_issue_id': None,
            'label_ids': [], 'due_date': None, 'order': float(self.number),
            'created_at': self.old, 'updated_at': self.start,
            **values,
        }
        await self.issues.insert_one(doc)
        return doc

    async def fetch(self, **params):
        response = await self.client.get('/pm/work-status', params={
            'start_date': '2026-11-01', 'end_date': '2026-11-07', **params,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def assert_issues(self, rows, *docs):
        self.assertCountEqual([row['id'] for row in rows], [str(doc['_id']) for doc in docs])

    async def test_leaf_epic_and_standalone_task_are_visible(self):
        epic = await self.add_issue('EPIC')
        task = await self.add_issue()
        self.assert_issues(await self.fetch(), epic, task)

    async def test_child_tasks_hide_epics_even_when_old_or_completed(self):
        for status in ('TODO', 'DONE', 'IMPLEMENTED'):
            epic = await self.add_issue('EPIC')
            await self.add_issue(epic_id=epic['_id'], status=status, updated_at=self.old,
                                 due_date=self.old, assignee_id=ObjectId())
        self.assert_issues(await self.fetch())

    async def test_non_task_children_do_not_hide_epics(self):
        epics = []
        for child_type in ('STORY', 'BUG', 'SUB_TASK'):
            epic = await self.add_issue('EPIC')
            epics.append(epic)
            await self.add_issue(child_type, epic_id=epic['_id'], updated_at=self.old)
        self.assert_issues(await self.fetch(), *epics)

    async def test_subtasks_replace_parent_once_and_keep_epic_hidden(self):
        epic = await self.add_issue('EPIC')
        parent = await self.add_issue(epic_id=epic['_id'])
        matching_child = await self.add_issue('SUB_TASK', epic_id=epic['_id'], parent_issue_id=parent['_id'])
        older_child = await self.add_issue('SUB_TASK', epic_id=epic['_id'], parent_issue_id=parent['_id'],
                                         updated_at=self.old)
        standalone = await self.add_issue()
        self.assert_issues(await self.fetch(), matching_child, older_child, standalone)

    async def test_project_filter_and_cross_project_links_do_not_hide_leaf_epic(self):
        other_pid = ObjectId()
        epic = await self.add_issue('EPIC')
        task = await self.add_issue()
        other_epic = await self.add_issue('EPIC', project_id=other_pid)
        other_task = await self.add_issue(project_id=other_pid)
        await self.add_issue(project_id=other_pid, epic_id=epic['_id'], updated_at=self.old)

        self.assert_issues(await self.fetch(project_id=str(self.pid)), epic, task)
        self.assert_issues(await self.fetch(), epic, task, other_epic, other_task)

    async def test_updated_or_unfinished_due_filter_keeps_inclusive_end_day(self):
        updated_start = await self.add_issue('EPIC', updated_at=self.start)
        updated_end = await self.add_issue('EPIC', updated_at=self.end - timedelta(seconds=1))
        await self.add_issue('EPIC', updated_at=self.start - timedelta(seconds=1))
        await self.add_issue('EPIC', updated_at=self.end)
        due_start = await self.add_issue(updated_at=self.old, due_date=self.start)
        due_end = await self.add_issue(updated_at=self.old, due_date=self.end - timedelta(seconds=1))
        await self.add_issue(updated_at=self.old, due_date=self.start - timedelta(seconds=1))
        await self.add_issue(updated_at=self.old, due_date=self.end)
        for status in ('DONE', 'IMPLEMENTED'):
            await self.add_issue(status=status, updated_at=self.old, due_date=self.start)
        completed_update = await self.add_issue(status='DONE', due_date=self.start)

        self.assert_issues(await self.fetch(), updated_start, updated_end, due_start, due_end, completed_update)
