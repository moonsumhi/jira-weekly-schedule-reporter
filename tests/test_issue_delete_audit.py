"""Issue identity remains in the audit trail after successful hard deletion."""
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.middleware import activity_logger
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm import issues


class IssueDeleteAuditTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, *, recurring=False, denied=False, missing=False, failure=False, project=True):
        pid, iid = ObjectId(), ObjectId()
        issue = {'_id': iid, 'project_id': pid, 'number': 42, 'title': '월간 서버 점검 - 10월 1차'}
        if recurring:
            issue.update(recurring_template_id=ObjectId(), occurrence_date='2026-10-15')
        user = UserPublic(id=str(ObjectId()), email='test@example.com')
        logs = SimpleNamespace(insert_one=AsyncMock())
        documents = SimpleNamespace(delete_one=AsyncMock(side_effect=RuntimeError('delete failed') if failure else None))
        related = SimpleNamespace(delete_many=AsyncMock())
        projects = SimpleNamespace(find_one=AsyncMock(return_value={'key': 'OPS'} if project else None))
        app = FastAPI()
        app.include_router(issues.router, prefix='/pm/projects')
        app.add_middleware(activity_logger.ActivityLoggerMiddleware)
        app.dependency_overrides[get_current_user] = lambda: user
        with ExitStack() as stack:
            for name, value in [('get_activity_logs_collection', logs), ('get_pm_issues_collection', documents),
                                ('get_pm_issue_comments_collection', related), ('get_pm_issue_history_collection', related),
                                ('get_pm_projects_collection', projects)]:
                stack.enter_context(patch.object(M, name, return_value=value))
            stack.enter_context(patch.object(issues, 'require_pm_member', AsyncMock(side_effect=HTTPException(403) if denied else None)))
            stack.enter_context(patch.object(issues, 'get_issue_or_404', AsyncMock(return_value=issue, side_effect=HTTPException(404) if missing else None)))
            stack.enter_context(patch.object(activity_logger, 'decode_token', return_value=user.email))
            async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url='http://test') as client:
                response = await client.delete(f'/pm/projects/{pid}/issues/{iid}', headers={'Authorization': 'Bearer test'})
        return response, logs, documents, str(iid)

    async def test_regular_and_recurring_deletion_logs_identity_once(self):
        for recurring in (False, True):
            with self.subTest(recurring=recurring):
                response, logs, documents, iid = await self.exercise(recurring=recurring)
                self.assertEqual(response.status_code, 204)
                documents.delete_one.assert_awaited_once()
                logs.insert_one.assert_awaited_once()
                doc = logs.insert_one.await_args.args[0]
                self.assertEqual(doc['action'], 'DELETE')
                self.assertEqual(doc['asset_id'], iid)
                self.assertEqual(doc['changed_by'], 'test@example.com')
                self.assertEqual(doc['diff'][:2], [
                    {'path': '이슈 번호', 'before': 'OPS-42', 'after': None},
                    {'path': '이슈 제목', 'before': '월간 서버 점검 - 10월 1차', 'after': None},
                ])
                self.assertIn({'path': '동작', 'before': None, 'after': 'delete_issue'}, doc['diff'])

    async def test_failed_requests_have_no_success_audit(self):
        for options, status in (({'denied': True}, 403), ({'missing': True}, 404), ({'failure': True}, 500)):
            with self.subTest(options=options):
                response, logs, documents, _ = await self.exercise(**options)
                self.assertEqual(response.status_code, status)
                logs.insert_one.assert_not_awaited()
                if status != 500:
                    documents.delete_one.assert_not_awaited()

    async def test_missing_project_keeps_issue_number(self):
        response, logs, _, _ = await self.exercise(project=False)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(logs.insert_one.await_args.args[0]['diff'][0]['before'], '42')
