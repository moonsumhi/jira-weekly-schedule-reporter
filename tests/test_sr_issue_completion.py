"""SR completion opt-in tests with mocked collections; no application data is touched."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.models.sr.service_request import SRStatusChange
from app.services.sr.sr_issue_bridge import prepare_issue_completion, complete_linked_issues


class SrIssueCompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sr_id, self.issue_id, self.project_id = [ObjectId() for _ in range(3)]
        self.sr = {'_id': self.sr_id, 'converted_issue_id': str(self.issue_id)}
        self.user = SimpleNamespace(id=str(ObjectId()), is_admin=False)
        self.issue = {'_id': self.issue_id, 'project_id': self.project_id, 'status': 'IN_PROGRESS'}

    async def test_default_and_no_leave_schedule_untouched(self):
        body = SRStatusChange(status='COMPLETED', process_result='finished')
        self.assertFalse(body.complete_linked_issues)
        with patch('app.services.sr.sr_issue_bridge.MongoClientManager.get_pm_issues_collection') as collection:
            self.assertEqual(await prepare_issue_completion(self.sr, self.user, False, body.status), [])
            collection.assert_not_called()
        with patch('app.routers.pm.issues.patch_issue', new_callable=AsyncMock) as update:
            await complete_linked_issues([], self.user)
            update.assert_not_awaited()

    async def test_yes_resolves_only_server_owned_links_and_checks_membership(self):
        collection = Mock()
        collection.find.return_value.to_list = AsyncMock(return_value=[self.issue])
        with patch('app.services.sr.sr_issue_bridge.MongoClientManager.get_pm_issues_collection', return_value=collection), \
                patch('app.services.pm.permission.require_pm_member', new_callable=AsyncMock) as authorize:
            pending = await prepare_issue_completion(self.sr, self.user, True, 'COMPLETED')
        self.assertEqual(pending, [self.issue])
        authorize.assert_awaited_once_with(self.user, str(self.project_id))
        query = collection.find.call_args.args[0]
        self.assertEqual(query['$or'][0]['_id']['$in'], [self.issue_id])
        self.assertEqual(query['$or'][1]['linked_sr_id']['$in'], [str(self.sr_id), self.sr_id])

    async def test_unauthorized_project_is_rejected_before_any_completion(self):
        collection = Mock()
        collection.find.return_value.to_list = AsyncMock(return_value=[self.issue])
        with patch('app.services.sr.sr_issue_bridge.MongoClientManager.get_pm_issues_collection', return_value=collection), \
                patch('app.services.pm.permission.require_pm_member', new_callable=AsyncMock,
                      side_effect=HTTPException(403, 'not a member')):
            with self.assertRaises(HTTPException) as error:
                await prepare_issue_completion(self.sr, self.user, True, 'COMPLETED')
        self.assertEqual(error.exception.status_code, 403)

    async def test_already_done_and_legacy_implemented_do_not_duplicate_updates(self):
        collection = Mock()
        collection.find.return_value.to_list = AsyncMock(return_value=[
            {**self.issue, 'status': status} for status in ('DONE', 'IMPLEMENTED')])
        with patch('app.services.sr.sr_issue_bridge.MongoClientManager.get_pm_issues_collection', return_value=collection):
            self.assertEqual(await prepare_issue_completion(self.sr, self.user, True, 'COMPLETED'), [])

    async def test_opt_in_is_invalid_for_other_sr_statuses(self):
        with self.assertRaises(HTTPException) as error:
            await prepare_issue_completion(self.sr, self.user, True, 'IN_PROGRESS')
        self.assertEqual(error.exception.status_code, 422)

    async def test_yes_uses_normal_issue_update_with_done_status(self):
        with patch('app.routers.pm.issues.patch_issue', new_callable=AsyncMock) as update:
            await complete_linked_issues([self.issue], self.user)
        project_id, issue_id, body, actor = update.call_args.args
        self.assertEqual((project_id, issue_id), (str(self.project_id), str(self.issue_id)))
        self.assertEqual(body.model_dump(exclude_unset=True), {'status': 'DONE'})
        self.assertIs(actor, self.user)

    async def test_sr_status_handler_passes_explicit_choice_and_saves_sr_in_both_cases(self):
        from app.db.mongo import MongoClientManager as M
        from app.routers.sr import admin_requests as endpoint

        self.user.is_admin = True
        self.user.full_name = 'Operator'
        self.user.email = 'operator@example.test'
        for choice in (False, True):
            sr = {**self.sr, 'status': 'IN_PROGRESS', 'requester_id': ObjectId(), 'title': 'Request'}
            col = SimpleNamespace(update_one=AsyncMock(), find_one=AsyncMock(return_value=sr))
            pending = [self.issue] if choice else []
            with patch.object(endpoint, 'get_sr_or_404', AsyncMock(return_value=sr)), \
                    patch.object(M, 'get_db', return_value={M.SERVICE_REQUESTS: col}), \
                    patch('app.services.sr.sr_issue_bridge.prepare_issue_completion', AsyncMock(return_value=pending)) as prepare, \
                    patch('app.services.sr.sr_issue_bridge.complete_linked_issues', AsyncMock()) as complete, \
                    patch.object(endpoint, 'record_status_history', AsyncMock()), \
                    patch.object(endpoint, 'create_notification', AsyncMock()), \
                    patch('app.utils.mail_notify.send_sr_notification', AsyncMock()), \
                    patch.object(endpoint, 'sr_to_out', return_value={}), \
                    patch.object(endpoint, 'SROut'):
                await endpoint.change_status(str(self.sr_id), SRStatusChange(
                    status='COMPLETED', process_result='finished', complete_linked_issues=choice), self.user)
            prepare.assert_awaited_once_with(sr, self.user, choice, 'COMPLETED')
            complete.assert_awaited_once_with(pending, self.user)
            self.assertEqual(col.update_one.call_args.args[1]['$set']['status'], 'COMPLETED')


if __name__ == '__main__':
    unittest.main()
