import unittest
from io import BytesIO
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.models.user import UserPublic
from app.routers.pm import monthly_feedback as feedback
from app.routers.pm import monthly_reports
from app.models.pm.reports import MonthlyReportCreate
from app.services import monthly_report_scheduler as scheduler


class Cursor:
    def __init__(self, values): self.values = values
    async def to_list(self, _length): return self.values


def user(uid=None, team='데이터운영팀'):
    return UserPublic(id=str(uid or ObjectId()), email='user@example.com', team=team, permissions=['pm'])


class FeedbackTests(unittest.IsolatedAsyncioTestCase):
    def assignment(self, assignee):
        return {'_id': ObjectId(), 'assignee_id': assignee.id, 'requester_id': str(ObjectId()),
                'status': 'REQUESTED', 'updated_at': datetime.now(timezone.utc),
                'target_report_id': str(ObjectId()), 'source_report_id': str(ObjectId()),
                'title': '다음 달 안건', 'comment': '보고서에 넣지 않을 메모', 'content': '이전 초안',
                'assignee_name': '담당자', 'due_date': ''}

    async def test_submit_immediately_adds_assignee_text_to_next_report(self):
        assignee = user()
        doc = self.assignment(assignee)
        claimed = {**doc, 'status': 'APPLYING', 'content': '담당자가 완성한 내용'}
        finished = {**claimed, 'status': 'APPLIED'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(side_effect=[claimed, finished]))
        reports = SimpleNamespace(find_one_and_update=AsyncMock(return_value={'_id': ObjectId()}))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(feedback, '_notify', AsyncMock()) as notify:
            result = await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content=claimed['content']), assignee)
        query, update = reports.find_one_and_update.await_args.args
        self.assertEqual(query['_id'], ObjectId(doc['target_report_id']))
        self.assertEqual(query['insights.id'], {'$ne': f"feedback-{doc['_id']}"})
        self.assertEqual(update['$push']['insights']['kind'], 'MAIN_AGENDA')
        self.assertEqual(update['$push']['insights']['content'], claimed['content'])
        self.assertEqual(result['status'], 'APPLIED')
        self.assertEqual(notify.await_args.args[0], doc['requester_id'])
        self.assertEqual(notify.await_args.args[4], doc['target_report_id'])
        self.assertEqual(notify.await_args.kwargs['notification_type'], 'STATUS_CHANGED')

    async def test_save_keeps_draft_without_adding_agenda(self):
        assignee = user()
        doc = self.assignment(assignee)
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(return_value={**doc, 'status': 'WRITING'}))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection') as reports, \
             patch.object(feedback, '_notify', AsyncMock()) as notify:
            result = await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='save', content='초안'), assignee)
        self.assertEqual(result['status'], 'WRITING')
        reports.assert_not_called()
        notify.assert_not_awaited()

    async def test_empty_submission_rejected_without_writes(self):
        assignee = user()
        doc = self.assignment(assignee)
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock())
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}):
            with self.assertRaises(HTTPException) as ctx:
                await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content='  '), assignee)
        self.assertEqual(ctx.exception.status_code, 400)
        col.find_one_and_update.assert_not_awaited()

    async def test_repeated_completion_does_not_add_or_notify_twice(self):
        assignee = user()
        doc = {**self.assignment(assignee), 'status': 'APPLIED'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock())
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection') as reports, \
             patch.object(feedback, '_notify', AsyncMock()) as notify:
            result = await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content='다시 전송'), assignee)
        self.assertEqual(result['status'], 'APPLIED')
        reports.assert_not_called()
        col.find_one_and_update.assert_not_awaited()
        notify.assert_not_awaited()

    async def test_confirmed_target_keeps_submitted_text_as_draft(self):
        assignee = user()
        doc = self.assignment(assignee)
        claimed = {**doc, 'status': 'APPLYING', 'content': '보관할 내용'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(return_value=claimed), update_one=AsyncMock())
        reports = SimpleNamespace(find_one_and_update=AsyncMock(return_value=None), find_one=AsyncMock(return_value=None))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(feedback, '_notify', AsyncMock()) as notify:
            with self.assertRaises(HTTPException) as ctx:
                await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content=claimed['content']), assignee)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(col.find_one_and_update.await_args.args[1]['$set']['content'], claimed['content'])
        self.assertEqual(col.update_one.await_args.args[1]['$set']['status'], 'WRITING')
        self.assertEqual(reports.find_one_and_update.await_args.args[0]['status'], {'$ne': 'CONFIRMED'})
        notify.assert_not_awaited()

    async def test_retry_recovers_report_write_without_replacing_saved_text(self):
        assignee = user()
        doc = {**self.assignment(assignee), 'status': 'APPLYING', 'content': '이미 반영된 원문'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(return_value={**doc, 'status': 'APPLIED'}))
        reports = SimpleNamespace(find_one_and_update=AsyncMock(return_value=None), find_one=AsyncMock(return_value={'_id': ObjectId()}))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(feedback, '_notify', AsyncMock()):
            result = await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content='다른 내용'), assignee)
        self.assertEqual(result['status'], 'APPLIED')
        self.assertEqual(reports.find_one_and_update.await_args.args[1]['$push']['insights']['content'], doc['content'])
        self.assertEqual(col.find_one_and_update.await_count, 1)

    def test_other_teams_cannot_use_feedback(self):
        with self.assertRaises(HTTPException) as ctx:
            feedback._team(user(team='데이터구축팀'))
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_only_assignee_can_write(self):
        doc = {'_id': ObjectId(), 'assignee_id': str(ObjectId()), 'requester_id': str(ObjectId()),
               'status': 'REQUESTED', 'updated_at': datetime.now(timezone.utc)}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}):
            with self.assertRaises(HTTPException) as ctx:
                await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='submit', content='내용'), user())
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_december_request_creates_january_target_and_notifies_assignee(self):
        requester = user()
        assignee_id, source_id, target_id = ObjectId(), ObjectId(), ObjectId()
        source = {'_id': source_id, 'report_year': 2026, 'report_month': 12, 'department': scheduler.TEAM, 'status': 'CONFIRMED'}
        reports = SimpleNamespace(find_one=AsyncMock(return_value=source))
        users = SimpleNamespace(find_one=AsyncMock(return_value={'_id': assignee_id, 'full_name': '담당자', 'permissions': ['pm']}))
        col = SimpleNamespace(insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id=ObjectId())))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(feedback.M, 'get_users_collection', return_value=users), \
             patch.object(feedback, 'ensure_monthly_report', AsyncMock(return_value={'_id': target_id, 'status': 'DRAFT'})) as ensure, \
             patch.object(feedback, '_notify', AsyncMock()) as notify:
            result = await feedback.create_feedback(feedback.FeedbackCreate(source_report_id=str(source_id), title='안건', comment='피드백', assignee_id=str(assignee_id)), requester)
        ensure.assert_awaited_once_with(2027, 1)
        self.assertEqual(result['target_report_id'], str(target_id))
        self.assertEqual(result['status'], 'REQUESTED')
        self.assertEqual(notify.await_args.args[0], str(assignee_id))

    async def test_apply_writes_only_report_content_once(self):
        requester = user()
        doc = {'_id': ObjectId(), 'assignee_id': str(ObjectId()), 'requester_id': requester.id,
               'status': 'SUBMITTED', 'updated_at': datetime.now(timezone.utc), 'target_report_id': str(ObjectId()),
               'title': '안건', 'comment': '팀장님 메모', 'content': '보고 내용', 'assignee_name': '담당자', 'due_date': ''}
        claimed = {**doc, 'status': 'APPLYING'}
        finished = {**claimed, 'status': 'APPLIED'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(side_effect=[claimed, finished]))
        reports = SimpleNamespace(find_one_and_update=AsyncMock(return_value={'_id': ObjectId()}))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(feedback, '_notify', AsyncMock()):
            result = await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='apply'), requester)
        query, update = reports.find_one_and_update.await_args.args
        self.assertEqual(query['insights.id'], {'$ne': f"feedback-{doc['_id']}"})
        self.assertEqual(update['$push']['insights']['content'], '보고 내용')
        self.assertEqual(result['status'], 'APPLIED')

    async def test_legacy_report_hides_exact_multiline_memo(self):
        fid = ObjectId()
        original = '팀장님 코멘트: 첫 번째\n\n두 번째\n\n작성한 보고 내용'
        item = SimpleNamespace(id=f'feedback-{fid}', content=original)
        untouched = SimpleNamespace(id='ordinary', content='원래 내용')
        out = SimpleNamespace(insights=[item, untouched])
        col = SimpleNamespace(find=lambda *_args: Cursor([{'_id': fid, 'comment': '첫 번째\n\n두 번째'}]))
        with patch.object(monthly_reports.MongoClientManager, 'get_db', return_value={'pm_monthly_feedback': col}):
            await monthly_reports._hide_feedback_memos(out)
        self.assertEqual(item.content, '작성한 보고 내용')
        self.assertEqual(untouched.content, '원래 내용')

    async def test_excel_excludes_legacy_private_memo(self):
        import openpyxl
        requester, fid, report_id = user(), ObjectId(), ObjectId()
        now = datetime.now(timezone.utc)
        doc = {'_id': report_id, 'report_year': 2026, 'report_month': 11, 'title': '보고',
               'created_by': ObjectId(requester.id), 'created_at': now, 'updated_at': now,
               'insights': [{'id': f'feedback-{fid}', 'kind': 'MAIN_AGENDA', 'title': '안건',
                             'content': '팀장님 코멘트: 비공개 메모\n\n보고 내용'}]}
        reports = SimpleNamespace(find_one=AsyncMock(return_value=doc))
        notes = SimpleNamespace(find=lambda *_args: Cursor([{'_id': fid, 'comment': '비공개 메모'}]))
        with patch.object(monthly_reports.MongoClientManager, 'get_db', return_value={'pm_monthly_feedback': notes}), \
             patch.object(monthly_reports.MongoClientManager, 'get_pm_monthly_reports_collection', return_value=reports), \
             patch.object(monthly_reports, '_user_name', AsyncMock(return_value='작성자')):
            response = await monthly_reports.export_monthly_detail(str(report_id), requester)
            content = b''.join([chunk async for chunk in response.body_iterator])
        workbook = openpyxl.load_workbook(BytesIO(content))
        self.assertEqual(workbook['주요 항목']['C2'].value, '보고 내용')

    async def test_apply_does_not_change_confirmed_report(self):
        requester = user()
        doc = {'_id': ObjectId(), 'assignee_id': str(ObjectId()), 'requester_id': requester.id,
               'status': 'SUBMITTED', 'updated_at': datetime.now(timezone.utc), 'target_report_id': str(ObjectId()),
               'title': '안건', 'comment': '코멘트', 'content': '작성 내용', 'assignee_name': '담당자', 'due_date': ''}
        claimed = {**doc, 'status': 'APPLYING'}
        col = SimpleNamespace(find_one=AsyncMock(return_value=doc), find_one_and_update=AsyncMock(return_value=claimed), update_one=AsyncMock())
        reports = SimpleNamespace(find_one_and_update=AsyncMock(return_value=None), find_one=AsyncMock(return_value=None))
        with patch.object(feedback.M, 'get_db', return_value={'pm_monthly_feedback': col}), \
             patch.object(feedback.M, 'get_pm_monthly_reports_collection', return_value=reports):
            with self.assertRaises(HTTPException) as ctx:
                await feedback.act(str(doc['_id']), feedback.FeedbackAction(action='apply'), requester)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(reports.find_one_and_update.await_args.args[0]['status'], {'$ne': 'CONFIRMED'})
        col.update_one.assert_awaited_once()

    async def test_existing_team_report_is_reused(self):
        report = {'_id': ObjectId(), 'department': scheduler.TEAM}
        col = SimpleNamespace(find=lambda _query: Cursor([report]), insert_one=AsyncMock())
        with patch.object(scheduler.M, 'get_pm_monthly_reports_collection', return_value=col):
            self.assertIs(await scheduler.ensure_monthly_report(2026, 11), report)
        col.insert_one.assert_not_awaited()

    async def test_manual_creation_rejects_existing_team_report(self):
        col = SimpleNamespace(find_one=AsyncMock(return_value={'_id': ObjectId()}), insert_one=AsyncMock())
        with patch.object(monthly_reports.MongoClientManager, 'get_pm_monthly_reports_collection', return_value=col):
            with self.assertRaises(HTTPException) as ctx:
                await monthly_reports.create_monthly_report(MonthlyReportCreate(report_year=2026, report_month=11, title='월간 보고'), user())
        self.assertEqual(ctx.exception.status_code, 409)
        col.insert_one.assert_not_awaited()

    async def test_report_with_active_feedback_cannot_be_deleted(self):
        feedback_col = SimpleNamespace(find_one=AsyncMock(return_value={'_id': ObjectId()}))
        reports = SimpleNamespace(update_one=AsyncMock())
        with patch.object(monthly_reports.MongoClientManager, 'get_db', return_value={'pm_monthly_feedback': feedback_col}), \
             patch.object(monthly_reports.MongoClientManager, 'get_pm_monthly_reports_collection', return_value=reports):
            with self.assertRaises(HTTPException) as ctx:
                await monthly_reports.delete_monthly_report(str(ObjectId()), user())
        self.assertEqual(ctx.exception.status_code, 409)
        reports.update_one.assert_not_awaited()

    async def test_ambiguous_existing_team_reports_do_not_create_duplicate(self):
        col = SimpleNamespace(find=lambda _query: Cursor([{'department': scheduler.TEAM}, {'department': scheduler.TEAM}]), insert_one=AsyncMock())
        with patch.object(scheduler.M, 'get_pm_monthly_reports_collection', return_value=col):
            with self.assertRaises(ValueError):
                await scheduler.ensure_monthly_report(2026, 11)
        col.insert_one.assert_not_awaited()

    async def test_scheduler_catches_up_missed_months_after_restart(self):
        state = SimpleNamespace(find_one=AsyncMock(return_value={'last_month': 202611}), update_one=AsyncMock())
        with patch.object(scheduler.M, 'get_db', return_value={'pm_scheduler_state': state}), \
             patch.object(scheduler, 'ensure_monthly_report', AsyncMock()) as ensure:
            await scheduler.MonthlyReportScheduler()._run_once(datetime(2027, 2, 1, tzinfo=timezone.utc))
        self.assertEqual([call.args for call in ensure.await_args_list], [(2026, 12), (2027, 1), (2027, 2)])
        self.assertEqual(state.update_one.await_count, 3)
