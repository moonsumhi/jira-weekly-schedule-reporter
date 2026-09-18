"""SR processing edits keep workflow state and record only actual changes."""
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.sr import admin_requests as router
from app.services.sr import sr_issue_bridge


class SRProcessingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.id, self.assignee, self.next_assignee = ObjectId(), ObjectId(), ObjectId()
        self.user = UserPublic(id=str(ObjectId()), email='manager@example.com', full_name='관리자', permissions=['sr_manager'])
        self.stamp = datetime(2026, 9, 18, 1, 2, 3, 123000)
        self.doc = dict(_id=self.id, sr_no='SR-2026-0010', title='점검 요청', status='COMPLETED',
                        request_type='SERVER_INFRA', priority='MEDIUM', requester_id=ObjectId(),
                        requester_name='요청자', requester_department='운영팀', requester_email='request@example.com',
                        is_urgent=False, compliance_related=False, created_by='요청자', updated_by='담당자',
                        created_at=self.stamp, updated_at=self.stamp, assignee_id=self.assignee, assignee_name='기존 담당자',
                        planned_start_date=datetime(2026, 9, 19), planned_due_date=datetime(2026, 9, 20),
                        deployment_required=True, security_review_required=False, process_result='처리 결과 보존',
                        actual_completed_at=self.stamp, requester_confirmed=True, deployed=True,
                        converted_issue_id=str(ObjectId()))
        self.conflict = False

        async def update(query, operation):
            if self.conflict:
                return SimpleNamespace(matched_count=0)
            self.assertEqual(query['updated_at'], self.doc['updated_at'])
            self.assertEqual(query['status'], self.doc['status'])
            self.doc.update(operation['$set'])
            return SimpleNamespace(matched_count=1)

        self.col = SimpleNamespace(find_one=AsyncMock(side_effect=lambda *args, **kwargs: deepcopy(self.doc)),
                                   update_one=AsyncMock(side_effect=update))
        self.users = SimpleNamespace(find_one=AsyncMock(return_value={'_id': self.next_assignee, 'full_name': '새 담당자', 'email': 'next@example.com'}))
        self.histories, self.due_history, self.status_history = AsyncMock(), AsyncMock(), AsyncMock()
        self.bridge, self.create_issue, self.notify = AsyncMock(), AsyncMock(), AsyncMock()
        self.assignment_notice = AsyncMock()
        for p in (
            patch.object(M, 'get_db', return_value={M.SERVICE_REQUESTS: self.col}),
            patch.object(M, 'get_users_collection', return_value=self.users),
            patch.object(router, 'record_sr_history', self.histories),
            patch.object(router, 'record_due_date_history', self.due_history),
            patch.object(router, 'record_status_history', self.status_history),
            patch.object(router, 'create_notification', self.notify),
            patch.object(router, '_notify_assignment', self.assignment_notice),
            patch.object(sr_issue_bridge, 'update_pm_issue_assignee', self.bridge),
            patch.object(sr_issue_bridge, 'auto_create_pm_issue', self.create_issue),
        ):
            p.start(); self.addCleanup(p.stop)
        app = FastAPI()
        app.include_router(router.router, prefix='/sr')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.addAsyncCleanup(self.client.aclose)

    async def save(self, **values):
        return await self.client.patch(f'/sr/{self.id}/processing', json={'expected_updated_at': self.stamp.isoformat() + 'Z', **values})

    async def test_edit_and_clear_fields_keeps_state_and_records_history(self):
        original = deepcopy(self.doc)
        response = await self.save(planned_start_date=None, planned_due_date=None,
                                   deployment_required=False, security_review_required=True)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertIsNone(data['planned_start_date'])
        self.assertIsNone(data['planned_due_date'])
        self.assertFalse(data['deployment_required'])
        self.assertTrue(data['security_review_required'])
        for key in ('status', 'process_result', 'actual_completed_at', 'deployed', 'requester_confirmed', 'assignee_id', 'converted_issue_id'):
            self.assertEqual(self.doc[key], original[key])
        self.assertEqual({call.args[1] for call in self.histories.await_args_list}, {
            'FIELD_CHANGE:planned_start_date', 'FIELD_CHANGE:planned_due_date',
            'FIELD_CHANGE:deployment_required', 'FIELD_CHANGE:security_review_required'})
        self.due_history.assert_awaited_once_with(str(self.id), original['planned_due_date'], None, None, '관리자')
        self.status_history.assert_not_awaited()
        self.bridge.assert_not_awaited()
        self.create_issue.assert_not_awaited()
        self.notify.assert_not_awaited()
        self.assignment_notice.assert_not_awaited()

    async def test_assignee_change_uses_registered_name_and_existing_issue_only(self):
        # A different user with the same display name still changes the ID and gets an audit entry.
        self.users.find_one.return_value['full_name'] = '기존 담당자'
        response = await self.save(assignee_id=str(self.next_assignee))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['assignee_id'], str(self.next_assignee))
        self.assignment_notice.assert_awaited_once()
        self.assertEqual(response.json()['assignee_name'], '기존 담당자')
        self.assertEqual(response.json()['status'], 'COMPLETED')
        self.bridge.assert_awaited_once_with(self.doc['converted_issue_id'], str(self.next_assignee))
        self.histories.assert_awaited_once_with(str(self.id), 'ASSIGNEE_CHANGE', '기존 담당자', '기존 담당자', '관리자')
        self.create_issue.assert_not_awaited()
        self.status_history.assert_not_awaited()

    async def test_noop_does_not_write_or_emit_history(self):
        response = await self.save(assignee_id=str(self.assignee), deployment_required=True,
                                   planned_start_date='2026-09-19T09:00:00+09:00')
        self.assertEqual(response.status_code, 200, response.text)
        self.col.update_one.assert_not_awaited()
        self.histories.assert_not_awaited()
        self.users.find_one.assert_not_awaited()

    async def test_dates_validate_with_existing_other_endpoint_and_kst(self):
        response = await self.save(planned_start_date='2026-09-22T00:00:00+09:00')
        self.assertEqual(response.status_code, 422, response.text)
        self.col.update_one.assert_not_awaited()
        response = await self.save(planned_start_date='2026-09-21T00:00:00+09:00', planned_due_date='2026-09-21T23:59:59+09:00')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.histories.await_args_list[0].args[3], '2026-09-21')
        self.assertEqual(self.histories.await_args_list[1].args[3], '2026-09-21')

    async def test_only_managers_can_edit_and_closed_unassigned_requests_are_protected(self):
        self.user.permissions = ['sr_operator']
        response = await self.save(deployment_required=False)
        self.assertEqual(response.status_code, 403)
        self.col.find_one.assert_not_awaited()
        self.user.permissions = ['sr_manager']
        for status in ('DRAFT', 'CLOSED', 'CANCELLED', 'REJECTED'):
            self.doc['status'] = status
            response = await self.save(deployment_required=False)
            self.assertEqual(response.status_code, 400, response.text)
        self.doc.update(status='APPROVED', assignee_id=None)
        response = await self.save(deployment_required=False)
        self.assertEqual(response.status_code, 400)
        self.col.update_one.assert_not_awaited()

    async def test_stale_dialog_and_concurrent_changes_cannot_overwrite(self):
        response = await self.save(deployment_required=False, expected_updated_at='2026-09-17T00:00:00Z')
        self.assertEqual(response.status_code, 409)
        self.col.update_one.assert_not_awaited()
        self.conflict = True
        response = await self.save(deployment_required=False)
        self.assertEqual(response.status_code, 409)
        self.assertTrue(self.doc['deployment_required'])
        self.histories.assert_not_awaited()
        self.bridge.assert_not_awaited()

    async def test_invalid_values_and_unknown_fields_do_not_write(self):
        for values in ({'deployment_required': None}, {'security_review_required': None}, {'assignee_id': None},
                       {'assignee_id': 'invalid'}, {'status': 'IN_PROGRESS'}, {'assignee_name': 'forged'},
                       {'planned_due_date': 'invalid'}):
            response = await self.save(**values)
            self.assertEqual(response.status_code, 422, response.text)
        self.users.find_one.return_value = None
        response = await self.save(assignee_id=str(self.next_assignee))
        self.assertEqual(response.status_code, 422)
        self.col.update_one.assert_not_awaited()
