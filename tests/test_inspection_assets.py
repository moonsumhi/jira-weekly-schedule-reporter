"""All-category inspection targets, using disposable MongoDB collections."""
import os
import unittest

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import test_inspection_tasks as fixtures
from app.db.mongo import MongoClientManager as M
from app.routers.auth import get_current_user
from app.routers.inspection_tasks import router as tasks_router
from app.routers.inspection_resources import router as resources_router
from app.routers.asset_work_history import router as history_router
from app.routers.monthly_inspection_reports import Preview
from app.services import inspection_service as tasks, monthly_inspection_reports as reports
from app.services.inspection_plan_reports import planning_snapshot


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Explicit disposable MongoDB tests only')
class InspectionAssetTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = fixtures.InspectionIntegrationTests.asyncTearDown
    rows = fixtures.InspectionIntegrationTests.rows
    registration = fixtures.InspectionIntegrationTests.registration

    async def asyncSetUp(self):
        await fixtures.InspectionIntegrationTests.asyncSetUp(self)
        await self.client.aclose()
        app = FastAPI()
        app.include_router(tasks_router, prefix='/inspection-tasks')
        app.include_router(resources_router, prefix='/resources')
        app.include_router(history_router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asset(self, category, **values):
        identifier = ObjectId()
        await M.get_asset_collection(category).insert_one({
            '_id': identifier, 'name': f'{category}-01', 'asset_no': f'CAT-{category}',
            'fields': {'장비명': f'{category} 점검 대상', '상태': '운영'}, **values})
        return str(identifier)

    async def test_all_categories_register_refresh_and_change_targets(self):
        ids = [str(self.aid)]
        for category in M.CATEGORY_COLLECTIONS:
            if category != '서버':
                ids.append(await self.asset(category))
        response = await self.client.get('/inspection-tasks/assets')
        self.assertEqual({a['category'] for a in response.json()}, set(M.CATEGORY_COLLECTIONS))
        response = await self.client.get('/inspection-tasks/assets', params={'ids': ','.join(ids)})
        self.assertEqual([a['id'] for a in response.json()], ids)
        response = await self.client.post('/inspection-tasks', json={**self.registration(), 'asset_ids': ids})
        self.assertEqual(response.status_code, 201, response.text)
        row = (await self.rows())[0]
        self.assertEqual([a['id'] for a in row['assets']], ids)
        self.assertFalse(any(a['is_deleted'] for a in row['assets']))
        network_id = next(a['id'] for a in row['assets'] if a['category'] == '네트워크')
        await M.get_asset_collection('네트워크').update_one({'_id': ObjectId(network_id)}, {'$set': {'name': '변경된 스위치'}})
        row = (await self.rows(asset_id=network_id))[0]
        network = next(a for a in row['assets'] if a['id'] == network_id)
        self.assertEqual(network['name'], '네트워크-01')
        self.assertEqual(network['current']['name'], '변경된 스위치')
        self.assertEqual(network['current']['category'], '네트워크')
        changed = await self.client.patch(f'/inspection-tasks/{self.iid}/2026-09', json={
            'action': 'targets', 'asset_ids': [network_id], 'common': False})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(len((await self.rows())[0]['assets']), 1)
        self.user.permissions.append('asset')
        history = await self.client.get(f'/assets/{network_id}/work-history')
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()['items'][0]['assets'][0]['current']['category'], '네트워크')

    async def test_category_search_identifiers_and_deleted_asset_validation(self):
        identifier = await self.asset('정보보호시스템', name='firewall', ip='192.0.2.22',
                                      asset_no='SEC-022', asset_id='DEVICE-022', fields={'장비명': '내부 방화벽'})
        for search in ('firewall', '192.0.2.22', 'SEC-022', 'DEVICE-022', '내부 방화벽'):
            response = await self.client.get('/inspection-tasks/assets', params={'search': search})
            self.assertEqual([a['id'] for a in response.json()], [identifier])
        self.assertEqual((await self.client.get('/inspection-tasks/assets', params={'search': '.*'})).json(), [])
        for category, expected in [('서버', str(self.aid)), ('정보보호시스템', identifier)]:
            response = await self.client.get('/inspection-tasks/assets', params={'category': category})
            self.assertEqual([a['id'] for a in response.json()], [expected])
        self.assertEqual((await self.client.get('/inspection-tasks/assets', params={'category': 'invalid'})).status_code, 422)
        await M.get_asset_collection('정보보호시스템').update_one({'_id': ObjectId(identifier)}, {'$set': {'is_deleted': True}})
        self.assertEqual((await self.client.get('/inspection-tasks/assets', params={'search': 'firewall'})).json(), [])
        response = await self.client.post('/inspection-tasks', json={**self.registration(), 'asset_ids': [identifier]})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.rows(), [])

    async def test_work_plan_task_accepts_non_server_asset(self):
        identifier = await self.asset('DBMS')
        template_id, entry_id = ObjectId(), ObjectId()
        await M.get_form_templates_collection().insert_one({
            '_id': template_id, 'menu': 'Job', 'jira_issue_key': 'JOB-PLAN-SERVICE', 'title': '작업계획서'})
        await M.get_form_entries_collection().insert_one({
            '_id': entry_id, 'template_id': str(template_id), 'data': {'기본 정보': {'작업명': 'DBMS 패치'}}, 'asset_ids': [], 'linked_assets': []})
        self.user.permissions.append('job')
        response = await self.client.post('/inspection-tasks/from-work-plan', json={
            'month': '2026-09', 'work_plan_id': str(entry_id), 'asset_ids': [identifier],
            'planned_on': '2026-09-17', 'assignee_id': None})
        self.assertEqual(response.status_code, 201, response.text)
        row = (await self.rows())[0]
        self.assertEqual(row['source_type'], 'WORK_PLAN')
        self.assertEqual(row['assets'][0]['current']['category'], 'DBMS')
        response = await self.client.patch(f"/inspection-tasks/{row['issue_id']}/2026-09/plan", json={
            'version': row['task_version'], 'asset_ids': [str(self.aid), identifier], 'common': False})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len((await self.rows())[0]['assets']), 2)

    async def test_reports_preserve_categories_without_non_server_measurement_warnings(self):
        identifier = await self.asset('네트워크')
        await tasks.register(self.issue, '2026-09', await tasks.resolve_assets([str(self.aid), identifier]), False, self.user)
        body = Preview(month='2026-09')
        _, snapshot = await reports.snapshot(body)
        self.assertEqual([a['id'] for a in snapshot['missing_asset_resources']], [str(self.aid)])
        self.assertEqual(snapshot['tasks'][0]['assets'][1]['category'], '네트워크')
        _, plan = await planning_snapshot(body)
        self.assertEqual(plan['tasks'][0]['assets'][1]['category'], '네트워크')
        self.assertEqual(plan['resource_targets'], [])

    async def test_resource_targets_stay_server_only_and_permissions_still_apply(self):
        identifier = await self.asset('랙')
        response = await self.client.put('/resources/targets', json={'version': 0, 'asset_ids': [identifier]})
        self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.put('/resources/targets', json={'version': 0, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 200, response.text)
        self.user.permissions = []
        self.assertEqual((await self.client.get('/inspection-tasks/assets')).status_code, 403)
        self.assertEqual((await self.client.get(f'/assets/{identifier}/work-history')).status_code, 403)
