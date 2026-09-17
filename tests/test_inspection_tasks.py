"""실제 MongoDB의 임시 컬렉션으로 권한·동시 등록·이월·완료 이력 검증.

INSPECTION_TEST_MONGO=1일 때만 통합 테스트 실행. 기존 컬렉션을 읽거나 변경하지 않는다.
"""
import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.inspection_tasks import Registration, Change, router
from app.routers.pm.issues import router as issue_router
from app.services import inspection_service as svc
from app.services.inspection_scheduler import InspectionScheduler


class InputTests(unittest.TestCase):
    def test_month_and_targets_are_validated(self):
        iid = str(ObjectId())
        for month in ('2026-13', '2026-00', '2026-9', 'bad'):
            with self.assertRaises(ValidationError):
                Registration(month=month, issue_id=iid, common=True)
        for targets in ({}, {'common': True, 'asset_ids': [iid]}, {'asset_ids': [iid, iid]}):
            with self.assertRaises(ValidationError):
                Registration(month='2026-09', issue_id=iid, **targets)
        Registration(month='2026-09', issue_id=iid, common=True)
        Registration(month='2026-09', issue_id=iid, asset_ids=[iid])

    def test_rollover_requires_reason(self):
        with self.assertRaises(ValidationError):
            Change(action='rollover', reason='  ')
        self.assertEqual(Change(action='exclude', reason=' 취소 ').reason, '취소')

    def test_year_rollover(self):
        self.assertEqual(svc.next_month('2026-12'), '2027-01')


class PrefixDB:
    def __init__(self, db):
        self.db, self.prefix, self.names = db, 'test_inspection_' + uuid4().hex + '_', set()

    def __getitem__(self, name):
        self.names.add(name)
        return self.db[self.prefix + name]

    async def cleanup(self):
        for name in self.names:
            await self.db.drop_collection(self.prefix + name)


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', '명시적 테스트 MongoDB 실행만 허용')
class InspectionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = PrefixDB(M.get_db())
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.month_patch = patch.object(svc, 'current_month', return_value='2026-09')
        self.month_patch.start()
        self.uid, self.pid, self.iid, self.aid = [ObjectId() for _ in range(4)]
        self.user = UserPublic(id=str(self.uid), email='inspection-test@example.com', full_name='점검 테스트', permissions=['server_check'])
        await M.get_pm_projects_collection().insert_one({'_id': self.pid, 'key': 'TEST', 'name': '테스트 프로젝트'})
        await M.get_pm_project_members_collection().insert_one({'user_id': self.uid, 'project_id': self.pid, 'role': 'DEVELOPER'})
        await M.get_users_collection().insert_one({'_id': self.uid, 'full_name': '점검 테스트', 'permissions': ['server_check']})
        self.issue = {'_id': self.iid, 'project_id': self.pid, 'number': 1, 'title': '로그 정리', 'status': 'TODO',
                      'assignee_id': self.uid, 'due_date': datetime(2026, 9, 30, tzinfo=timezone.utc)}
        await M.get_pm_issues_collection().insert_one(self.issue)
        await M.get_assets_servers_collection().insert_one({'_id': self.aid, 'name': 'web-test', 'ip': '192.0.2.10',
                                                           'fields': {'서버명': '테스트 서버', '상태': '운영'}, 'is_deleted': False})
        app = FastAPI()
        app.include_router(router, prefix='/inspection-tasks')
        app.include_router(issue_router, prefix='/pm/projects')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.cleanup()
        self.month_patch.stop()
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    def registration(self, month='2026-09'):
        return {'month': month, 'issue_id': str(self.iid), 'asset_ids': [str(self.aid)]}

    async def register(self, month='2026-09'):
        response = await self.client.post('/inspection-tasks', json=self.registration(month))
        self.assertEqual(response.status_code, 201, response.text)

    async def rows(self, month='2026-09', **params):
        response = await self.client.get('/inspection-tasks', params={'month': month, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['items']

    async def test_new_pm_issue_schedule_link_and_status_update(self):
        response = await self.client.post(f'/pm/projects/{self.pid}/issues', json={
            'title': '새 점검 작업', 'status': 'TODO', 'assignee_id': str(self.uid),
            'start_date': '2026-09-17T00:00:00+09:00', 'due_date': '2026-09-17T23:59:59+09:00'})
        self.assertEqual(response.status_code, 201, response.text)
        new_id = response.json()['id']
        response = await self.client.post('/inspection-tasks', json={
            'month': '2026-09', 'issue_id': new_id, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 201, response.text)
        response = await self.client.patch(f'/pm/projects/{self.pid}/issues/{new_id}', json={'status': 'DONE'})
        self.assertEqual(response.status_code, 200, response.text)
        rows = await self.rows()
        self.assertEqual(rows[0]['issue']['status'], 'DONE')
        doc = await svc.collection().find_one({'_id': ObjectId(new_id)})
        self.assertEqual(doc['occurrences'][0]['completed_snapshot']['status'], 'DONE')
        history = await M.get_pm_issue_history_collection().find({'issue_id': ObjectId(new_id)}).to_list(None)
        self.assertTrue(any(h['field'] == 'status' for h in history))

    async def test_menu_migration_is_idempotent(self):
        from app.db.startup import migrate_inspection_tasks
        await M.get_menus_collection().insert_one({'slug': 'server_check', 'submenus': [
            {'title': '요약', 'link': '/inspection/health-summary'},
            {'title': '월별 비교', 'link': '/inspection/health-compare'}]})
        await migrate_inspection_tasks()
        await migrate_inspection_tasks()
        menu = await M.get_menus_collection().find_one({'slug': 'server_check'})
        self.assertEqual(len(menu['submenus']), 3)
        self.assertEqual(sum(m['link'] == '/inspection/monthly-reports' for m in menu['submenus']), 1)
        self.assertEqual(menu['submenus'][0]['link'], '/inspection/tasks')
        self.assertFalse(any(m['link'] == '/inspection/health-summary' for m in menu['submenus']))
        self.assertFalse(any(m['link'] == '/inspection/health-compare' for m in menu['submenus']))
        self.assertEqual([m['title'] for m in menu['submenus'] if m['link'] == '/inspection/health-servers'], ['자원 점검'])
        # Menus that already have both entries must keep a single resource page.
        await M.get_menus_collection().update_one({'slug': 'server_check'}, {'$push': {
            'submenus': {'$each': [
                {'title': '요약', 'link': '/inspection/health-summary'},
                {'title': '월별 비교', 'link': '/inspection/health-compare'},
            ]}}})
        await migrate_inspection_tasks()
        self.assertEqual((await M.get_menus_collection().find_one({'slug': 'server_check'}))['submenus'], menu['submenus'])

    async def test_register_multiple_assets_and_search(self):
        aid2 = ObjectId()
        await M.get_assets_servers_collection().insert_one({'_id': aid2, 'name': 'db-test', 'ip': '192.0.2.11'})
        body = self.registration()
        body['asset_ids'].append(str(aid2))
        response = await self.client.post('/inspection-tasks', json=body)
        self.assertEqual(response.status_code, 201)
        rows = await self.rows()
        self.assertEqual(len(rows[0]['assets']), 2)
        response = await self.client.get('/inspection-tasks/assets', params={'search': '테스트 서버'})
        self.assertEqual(response.json()[0]['id'], str(self.aid))
        response = await self.client.get('/inspection-tasks/assets', params={'search': '.*'})
        self.assertEqual(response.json(), [])  # 정규식 입력도 리터럴 검색

    async def test_concurrent_registration_is_unique(self):
        responses = await asyncio.gather(*[self.client.post('/inspection-tasks', json=self.registration()) for _ in range(5)])
        self.assertEqual(sorted(r.status_code for r in responses), [201, 409, 409, 409, 409])
        self.assertEqual(len(await self.rows()), 1)

    async def test_permissions_and_membership(self):
        await self.register()
        self.user = self.user.model_copy(update={'permissions': []})
        self.assertEqual((await self.client.get('/inspection-tasks', params={'month': '2026-09'})).status_code, 403)
        self.user = self.user.model_copy(update={'permissions': ['server_check'], 'id': str(ObjectId())})
        self.assertEqual(await self.rows(), [])
        response = await self.client.post('/inspection-tasks', json=self.registration('2026-10'))
        self.assertEqual(response.status_code, 403)
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'exclude', 'reason': '권한 없음'})
        self.assertEqual(response.status_code, 403)

    async def test_missing_assets_and_invalid_month_do_not_register(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        self.assertEqual((await self.client.post('/inspection-tasks', json=self.registration())).status_code, 422)
        self.assertEqual(await self.rows(), [])
        self.assertEqual((await self.client.get('/inspection-tasks', params={'month': '2026-99'})).status_code, 422)

    async def test_rollover_is_atomic_and_retains_due_date(self):
        await self.register('2026-08')
        self.assertTrue((await self.rows())[0]['overdue'])
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-08', json={'action': 'rollover', 'reason': '점검 시간 부족'})
        self.assertEqual(response.status_code, 200, response.text)
        current = await self.rows()
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]['from_month'], '2026-08')
        old = await self.rows('2026-08')
        self.assertEqual(old[0]['state'], 'ROLLED')
        self.assertEqual(old[0]['to_month'], '2026-09')
        issue = await M.get_pm_issues_collection().find_one({'_id': self.iid})
        self.assertEqual(issue['due_date'].day, 30)
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-08', json={'action': 'rollover', 'reason': '재시도'})
        self.assertEqual(response.status_code, 409)

    async def test_rollover_conflict_leaves_source_active(self):
        await self.register('2026-08')
        await self.register('2026-09')
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-08', json={'action': 'rollover', 'reason': '중복'})
        self.assertEqual(response.status_code, 409)
        old = await self.rows('2026-08')
        self.assertEqual(old[0]['state'], 'ACTIVE')

    async def test_completed_history_survives_reopening(self):
        await self.register('2026-08')
        done = {**self.issue, 'status': 'DONE'}
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'status': 'DONE'}})
        await svc.capture_completion(done)
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'status': 'IN_PROGRESS'}})
        await svc.capture_completion({**self.issue, 'status': 'IN_PROGRESS'})
        self.assertEqual(await self.rows(), [])
        self.assertEqual((await self.rows('2026-08'))[0]['issue']['status'], 'DONE')
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-08', json={'action': 'targets', 'common': True})
        self.assertEqual(response.status_code, 409)

    async def test_live_status_and_current_month_reopening(self):
        await self.register()
        for status in ('IMPLEMENTED', 'DONE', 'TODO'):
            await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'status': status}})
            await svc.capture_completion({**self.issue, 'status': status})
            self.assertEqual((await self.rows())[0]['issue']['status'], status)
        doc = await svc.collection().find_one({'_id': self.iid})
        self.assertNotIn('completed_snapshot', doc['occurrences'][0])

    async def test_asset_snapshot_and_deleted_issue_remain_visible(self):
        await self.register()
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'renamed', 'ip': '192.0.2.20'}})
        row = (await self.rows())[0]
        self.assertEqual(row['assets'][0]['name'], 'web-test')
        self.assertEqual(row['assets'][0]['current']['name'], 'renamed')
        await M.get_assets_servers_collection().delete_one({'_id': self.aid})
        await M.get_pm_issues_collection().delete_one({'_id': self.iid})
        row = (await self.rows())[0]
        self.assertTrue(row['assets'][0]['is_deleted'])
        self.assertTrue(row['issue_deleted'])
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'exclude', 'reason': '이슈 삭제'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((await self.rows())[0]['state'], 'EXCLUDED')

    async def test_exclusion_can_be_reconnected_without_losing_history(self):
        await self.register()
        response = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={'action': 'exclude', 'reason': '잘못 연결'})
        self.assertEqual(response.status_code, 200)
        await self.register()
        rows = await self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['state'], 'ACTIVE')
        self.assertEqual(rows[0]['history'][0]['reason'], '잘못 연결')
        self.assertEqual(rows[0]['history'][1]['action'], 'reconnect')

    async def test_inspection_date_uses_override(self):
        self.assertEqual((await svc.inspection_date('2026-09')).isoformat(), '2026-09-17')
        await M.get_ddays_collection().insert_one({'title': '서버 점검일 2026-09', 'date': '2026-09-24'})
        self.assertEqual((await svc.inspection_date('2026-09')).isoformat(), '2026-09-24')

    async def test_reminders_are_grouped_and_not_resent(self):
        await self.register()
        await self.register('2026-08')
        clock = datetime(2026, 9, 14, 9, tzinfo=svc.KST)
        with patch('app.services.inspection_scheduler.datetime') as dt:
            dt.now.return_value = clock
            scheduler = InspectionScheduler()
            await asyncio.gather(scheduler._run_once(), scheduler._run_once())
            await scheduler._run_once()
        notifications = await M.get_db()[M.NOTIFICATIONS].find({}).to_list(None)
        self.assertEqual(len(notifications), 1)
        self.assertIn('1건', notifications[0]['message'])
        self.assertEqual(notifications[0]['target_type'], 'SYSTEM')
        self.assertIn('mine=1', notifications[0]['target_url'])


if __name__ == '__main__':
    unittest.main()
