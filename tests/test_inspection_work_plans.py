"""Isolated MongoDB regression checks for monthly occurrence/work-plan links."""
import asyncio
import os
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.inspection_tasks import router
from app.routers.asset_work_history import router as asset_router
from app.services import inspection_service as svc, inspection_work_plans as plans


class PrefixDB:
    def __init__(self, db):
        self.db, self.prefix, self.names = db, 'test_inspection_plans_' + uuid4().hex + '_', set()
    def __getitem__(self, name):
        self.names.add(name)
        return self.db[self.prefix + name]
    async def cleanup(self):
        for name in self.names:
            await self.db.drop_collection(self.prefix + name)


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Requires isolated MongoDB run')
class InspectionPlanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = PrefixDB(M.get_db())
        self.patch = patch.object(M, 'get_db', return_value=self.db)
        self.patch.start()
        self.month_patch = patch.object(svc, 'current_month', return_value='2026-09')
        self.month_patch.start()
        self.uid, self.pid, self.iid, self.aid, self.tid, self.eid = [ObjectId() for _ in range(6)]
        self.user = UserPublic(id=str(self.uid), email='plan-test@example.com', full_name='점검자', permissions=['server_check', 'job'])
        await M.get_pm_projects_collection().insert_one({'_id': self.pid, 'key': 'TEST', 'name': '프로젝트'})
        await M.get_pm_project_members_collection().insert_one({'user_id': self.uid, 'project_id': self.pid, 'role': 'DEVELOPER'})
        self.issue = {'_id': self.iid, 'project_id': self.pid, 'number': 1, 'title': 'Git 이관', 'status': 'TODO', 'assignee_id': None}
        await M.get_pm_issues_collection().insert_one(self.issue)
        self.asset = {'id': str(self.aid), 'name': 'web-01', 'ip': '192.0.2.1', 'asset_name': '', 'is_deleted': False}
        await M.get_assets_servers_collection().insert_one({'_id': self.aid, 'name': 'web-01', 'ip': '192.0.2.1', 'fields': {}})
        await M.get_form_templates_collection().insert_one({'_id': self.tid, 'menu': 'Job', 'jira_issue_key': 'JOB-PLAN-SERVICE', 'title': '작업계획서(서비스)'})
        self.entry = {'_id': self.eid, 'template_id': str(self.tid), 'data': {'기본 정보': {'작업명': 'Git migration', '작업 기간 (시작)': '2026-09-17'}, '문서 본문': [{'제목': 'Git migration', '내용': '원본 계획서 내용'}]},
                      'linked_assets': [self.asset], 'asset_ids': [str(self.aid)], 'version': 1, 'created_at': datetime(2026, 8, 1, tzinfo=timezone.utc)}
        await M.get_form_entries_collection().insert_one(deepcopy(self.entry))
        app = FastAPI(); app.include_router(router, prefix='/inspection-tasks'); app.include_router(asset_router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose(); await self.db.cleanup(); self.patch.stop(); self.month_patch.stop()
        M.get_client().close(); M._client = None

    async def register(self, month='2026-09', **values):
        r = await self.client.post('/inspection-tasks', json={'month': month, 'issue_id': str(self.iid), 'asset_ids': [str(self.aid)], **values})
        self.assertEqual(r.status_code, 201, r.text)
        return r

    async def links(self, ids=None, version=0, month='2026-09'):
        return await self.client.put(f'/inspection-tasks/{self.iid}/{month}/work-plans', json={'work_plan_ids': [str(self.eid)] if ids is None else ids, 'version': version})

    async def rows(self, **params):
        r = await self.client.get('/inspection-tasks', params={'month': '2026-09', **params})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['items']

    async def test_link_open_metadata_and_reverse_lookup_without_modifying_plan_or_issue(self):
        original = await M.get_form_entries_collection().find_one({'_id': self.eid})
        await self.register()
        self.assertEqual((await self.links()).status_code, 200)
        row = (await self.rows())[0]
        self.assertEqual(row['work_plans'][0]['title'], 'Git migration')
        self.assertEqual(row['work_plans'][0]['current']['linked_assets'][0]['id'], str(self.aid))
        self.assertEqual(len(await self.rows(work_plan_id=str(self.eid), all_months=True)), 1)
        self.assertEqual(await M.get_form_entries_collection().find_one({'_id': self.eid}), original)
        self.assertEqual(await M.get_pm_issues_collection().find_one({'_id': self.iid}), self.issue)
        self.assertEqual((await self.links([], 1)).status_code, 200)
        self.assertEqual(await self.rows(work_plan_id=str(self.eid), all_months=True), [])

    async def test_creation_is_atomic_and_invalid_links_do_not_register_task(self):
        r = await self.client.post('/inspection-tasks', json={'month': '2026-09', 'issue_id': str(self.iid), 'common': True, 'work_plan_ids': [str(ObjectId())]})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(await svc.collection().count_documents({}), 0)
        await self.register(work_plan_ids=[str(self.eid)])
        self.assertEqual((await self.rows())[0]['work_plans_version'], 1)

    async def test_selection_validates_ids_duplicates_and_document_type(self):
        await self.register()
        self.assertEqual((await self.links(['invalid'])).status_code, 400)
        for ids in ([str(self.eid)] * 2, [str(ObjectId())]):
            self.assertEqual((await self.links(ids)).status_code, 422)
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'jira_issue_key': 'JOB-RESULT', 'title': '작업결과서'}})
        self.assertEqual((await self.links()).status_code, 422)
        self.assertEqual((await self.rows())[0]['work_plans'], [])

    async def test_permissions_cover_menu_job_and_project_membership(self):
        await self.register()
        self.user.permissions = ['server_check']
        self.assertEqual((await self.links()).status_code, 403)
        self.assertEqual((await self.client.get('/inspection-tasks/work-plans')).status_code, 403)
        self.user.permissions = ['job']
        self.assertEqual((await self.links()).status_code, 403)
        self.user.permissions = ['server_check', 'job']
        await M.get_pm_project_members_collection().delete_many({})
        self.assertEqual((await self.links()).status_code, 403)
        self.assertEqual(await self.rows(work_plan_id=str(self.eid)), [])

    async def test_concurrent_changes_and_targets_preserve_links(self):
        await self.register()
        responses = await asyncio.gather(self.links(), self.links([]))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        await self.links(version=1)
        r = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'targets', 'common': True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((await self.rows())[0]['work_plans'][0]['id'], str(self.eid))

    async def test_rollover_reconnect_and_month_filter_preserve_selected_occurrence(self):
        await self.register(work_plan_ids=[str(self.eid)])
        r = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'rollover', 'reason': '다음 달 진행'})
        self.assertEqual(r.status_code, 200)
        rows = await self.rows(all_months=True, work_plan_id=str(self.eid))
        self.assertEqual([r['month'] for r in rows], ['2026-09', '2026-10'])
        self.assertEqual((await self.links([], 0, '2026-10')).status_code, 200)
        rows = await self.rows(all_months=True, work_plan_id=str(self.eid))
        self.assertEqual([r['month'] for r in rows], ['2026-09'])
        self.assertEqual((await self.links([], 1)).status_code, 409)

    async def test_excluded_reconnect_retains_links_when_not_explicitly_replaced(self):
        await self.register(work_plan_ids=[str(self.eid)])
        await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'exclude', 'reason': '일정 조정'})
        await self.register()
        self.assertEqual((await self.rows())[0]['work_plans'][0]['id'], str(self.eid))

    async def test_completed_past_record_is_immutable(self):
        await self.register('2026-08', work_plan_ids=[str(self.eid)])
        completed = {**self.issue, 'status': 'DONE'}
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'status': 'DONE'}})
        await svc.capture_completion(completed)
        self.assertEqual((await self.links([], 1, '2026-08')).status_code, 409)

    async def test_deleted_document_retains_history_and_can_be_removed(self):
        await self.register(work_plan_ids=[str(self.eid)])
        await M.get_form_entries_collection().update_one({'_id': self.eid}, {'$set': {'is_deleted': True}})
        row = (await self.rows())[0]
        self.assertEqual(row['work_plans'][0]['title'], 'Git migration')
        self.assertTrue(row['work_plans'][0]['unavailable'])
        self.assertEqual((await self.links(version=1)).status_code, 200)
        self.assertEqual((await self.links([], 2)).status_code, 200)

    async def test_search_finds_old_documents_and_filters_related_assets(self):
        await M.get_form_entries_collection().insert_many([{
            '_id': ObjectId(), 'template_id': str(self.tid), 'data': {'기본 정보': {'작업명': f'다른 작업 {i}'}},
            'version': 1, 'created_at': datetime(2026, 9, 1, tzinfo=timezone.utc)} for i in range(40)])
        response = await self.client.get('/inspection-tasks/work-plans', params={'search': 'git migration'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([p['id'] for p in response.json()['items']], [str(self.eid)])
        response = await self.client.get('/inspection-tasks/work-plans')
        self.assertTrue(response.json()['has_more'])
        self.assertEqual(len(response.json()['items']), 30)
        response = await self.client.get('/inspection-tasks/work-plans', params={'asset_ids': str(self.aid)})
        self.assertEqual([p['id'] for p in response.json()['items']], [str(self.eid)])
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'title': '운영 변경 계획'}})
        self.assertEqual(len((await plans.search_plans('Git'))['items']), 1)
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'menu': 'Jira'}})
        self.assertEqual((await plans.search_plans())['items'], [])

    async def direct_plan(self, **values):
        return await self.client.post('/inspection-tasks/from-work-plan', json={
            'month': '2026-09', 'work_plan_id': str(self.eid), 'asset_ids': [str(self.aid)],
            'planned_on': '2026-09-17', **values})

    async def edit_plan(self, row, **values):
        return await self.client.patch(f"/inspection-tasks/{row['issue_id']}/{row['month']}/plan", json={
            'version': row['task_version'], **values})

    async def test_direct_plan_without_project_creates_no_issue_and_has_asset_and_reverse_history(self):
        await self.register()
        await M.get_pm_project_members_collection().delete_many({})
        original = await M.get_form_entries_collection().find_one({'_id': self.eid})
        response = await self.direct_plan()
        self.assertEqual(response.status_code, 201, response.text)
        rows = await self.rows()
        self.assertEqual(len(rows), 1)  # inaccessible PM issue stays hidden
        row = rows[0]
        self.assertEqual(row['source_type'], 'WORK_PLAN')
        self.assertEqual(row['issue']['title'], 'Git migration')
        self.assertEqual(row['work_plan']['id'], str(self.eid))
        self.assertEqual(row['planned_on'], '2026-09-17')
        self.assertEqual(row['assets'][0]['current']['name'], 'web-01')
        self.assertEqual(row['issue']['project_id'], '')
        self.assertEqual(await M.get_pm_issues_collection().count_documents({}), 1)
        self.assertEqual(await M.get_form_entries_collection().find_one({'_id': self.eid}), original)
        self.assertEqual(len(await self.rows(all_months=True, work_plan_id=str(self.eid), asset_id=str(self.aid))), 1)
        self.user.permissions = ['server_check', 'asset']
        response = await self.client.get(f'/assets/{self.aid}/work-history')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([x['issue_id'] for x in response.json()['items']], [row['issue_id']])
        self.assertEqual((await self.edit_plan(row, status='IN_PROGRESS')).status_code, 200)
        self.user.permissions = ['asset']
        self.assertEqual((await self.edit_plan(row, status='DONE')).status_code, 403)

    async def test_direct_plan_concurrent_registration_and_updates_are_guarded(self):
        responses = await asyncio.gather(self.direct_plan(), self.direct_plan(work_plan_id=str(self.eid).upper()))
        self.assertEqual(sorted(r.status_code for r in responses), [201, 409])
        row = (await self.rows())[0]
        responses = await asyncio.gather(self.edit_plan(row, status='DONE'), self.edit_plan(row, status='IN_PROGRESS'))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual(await svc.collection().count_documents({}), 1)
        self.assertEqual((await self.edit_plan(row, status='TODO')).status_code, 409)
        self.assertEqual((await self.client.put(f"/inspection-tasks/{row['issue_id']}/2026-09/work-plans", json={
            'version': 0, 'work_plan_ids': []})).status_code, 409)

    async def test_direct_plan_validation_and_permissions_do_not_leave_partial_tasks(self):
        for values in ({'work_plan_id': str(ObjectId())}, {'assignee_id': str(ObjectId())},
                       {'asset_ids': [str(ObjectId())]}, {'asset_ids': []}, {'planned_on': '2026-09-99'}):
            with self.subTest(values=values):
                self.assertEqual((await self.direct_plan(**values)).status_code, 422)
        self.user.permissions = ['server_check']
        self.assertEqual((await self.direct_plan()).status_code, 403)
        self.user.permissions = ['job']
        self.assertEqual((await self.direct_plan()).status_code, 403)
        self.user.permissions = ['server_check', 'job']
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'jira_issue_key': 'JOB-RESULT'}})
        self.assertEqual((await self.direct_plan()).status_code, 422)
        self.assertEqual(await svc.collection().count_documents({}), 0)

    async def test_direct_plan_completion_is_per_month_and_freezes_historical_identity(self):
        await M.get_users_collection().insert_one({'_id': self.uid, 'full_name': '점검자'})
        self.assertEqual((await self.direct_plan(assignee_id=str(self.uid))).status_code, 201)
        row = (await self.rows())[0]
        self.assertEqual((await self.edit_plan(row, status='DONE')).status_code, 200)
        row = (await self.rows())[0]
        self.assertEqual((await self.edit_plan(row, assignee_id=None, planned_on='2026-09-18')).status_code, 200)
        self.assertEqual((await self.direct_plan(month='2026-10', planned_on='2026-10-15')).status_code, 201)
        await M.get_form_entries_collection().update_one({'_id': self.eid}, {'$set': {'data.기본 정보.작업명': '새 제목', 'version': 2}})
        with patch.object(svc, 'current_month', return_value='2026-10'):
            rows = await self.rows(all_months=True)
            old = next(r for r in rows if r['month'] == '2026-09')
            current = next(r for r in rows if r['month'] == '2026-10')
            self.assertEqual((old['issue']['title'], old['issue']['status'], old['issue']['assignee_id']), ('Git migration', 'DONE', None))
            self.assertEqual((current['issue']['title'], current['issue']['status']), ('새 제목', 'TODO'))
            self.assertEqual((await self.edit_plan(old, status='TODO')).status_code, 409)
            self.assertEqual((await self.edit_plan(current, status='IN_PROGRESS')).status_code, 200)
        self.assertEqual(await M.get_pm_issues_collection().find_one({'_id': self.iid}), self.issue)

    async def test_direct_plan_results_rollover_reconnect_and_deleted_source(self):
        await self.direct_plan()
        row = (await self.rows())[0]
        task_id = row['issue_id']
        response = await self.client.put(f'/inspection-tasks/{task_id}/2026-09/result', json={
            'version': 0, 'content': '중간 결과', 'follow_up': '다음 달 확인', 'performed_on': '2026-09-17'})
        self.assertEqual(response.status_code, 200, response.text)
        await self.client.patch(f'/inspection-tasks/{task_id}/2026-09', json={'action': 'exclude', 'reason': '일정 변경'})
        self.assertEqual((await self.direct_plan()).status_code, 201)
        row = (await self.rows())[0]
        self.assertEqual(row['result']['content'], '중간 결과')
        self.assertEqual((await self.edit_plan(row, status='IN_PROGRESS')).status_code, 200)
        response = await self.client.patch(f'/inspection-tasks/{task_id}/2026-09', json={'action': 'rollover', 'reason': '다음 달 진행'})
        self.assertEqual(response.status_code, 200, response.text)
        rows = await self.rows(all_months=True)
        old, current = sorted(rows, key=lambda r: r['month'])
        self.assertEqual((old['state'], current['state']), ('ROLLED', 'ACTIVE'))
        self.assertEqual(current['planned_on'], '2026-10-15')
        self.assertEqual(current['assets'][0]['id'], str(self.aid))
        self.assertEqual(current['issue']['status'], 'IN_PROGRESS')
        self.assertNotIn('result', current)
        self.assertEqual((await self.edit_plan(current, status='TODO')).status_code, 200)
        self.assertEqual(next(r for r in await self.rows(all_months=True) if r['month'] == '2026-09')['issue']['status'], 'IN_PROGRESS')
        await M.get_form_entries_collection().update_one({'_id': self.eid}, {'$set': {'is_deleted': True}})
        current = next(r for r in await self.rows(all_months=True) if r['month'] == '2026-10')
        self.assertTrue(current['issue_deleted'])
        self.assertEqual(current['work_plan']['title'], 'Git migration')
        self.assertEqual((await self.edit_plan(current, status='DONE')).status_code, 409)
        self.assertEqual((await self.direct_plan(month='2026-11')).status_code, 422)

    async def test_direct_plan_invalid_partial_edits_are_rejected(self):
        await self.direct_plan()
        row = (await self.rows())[0]
        for values in ({}, {'status': None}, {'status': 'INVALID'}, {'planned_on': None},
                       {'asset_ids': []}, {'common': True}, {'common': False, 'asset_ids': []}):
            with self.subTest(values=values):
                self.assertEqual((await self.edit_plan(row, **values)).status_code, 422)
        self.assertEqual((await self.rows())[0]['task_version'], row['task_version'])

    async def test_direct_plan_reminder_without_pm_membership(self):
        from app.services.inspection_scheduler import InspectionScheduler
        await M.get_users_collection().insert_one({'_id': self.uid, 'full_name': '점검자', 'permissions': ['server_check']})
        await M.get_pm_project_members_collection().delete_many({})
        await self.direct_plan(assignee_id=str(self.uid))
        with patch('app.services.inspection_scheduler.datetime') as clock:
            clock.now.return_value = datetime(2026, 9, 17, 9, tzinfo=svc.KST)
            scheduler = InspectionScheduler()
            await scheduler._run_once()
            await scheduler._run_once()
        notifications = await M.get_db()[M.NOTIFICATIONS].find({}).to_list(None)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['recipient_user_id'], str(self.uid))
        self.assertIn('1건', notifications[0]['message'])
