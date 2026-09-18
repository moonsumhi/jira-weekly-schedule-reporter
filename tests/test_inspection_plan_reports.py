"""Plan/result separation and submitted-plan preservation with isolated MongoDB data."""
import os
import unittest
from copy import deepcopy

from bson import ObjectId

import test_monthly_inspection_reports as fixtures
from app.db.mongo import MongoClientManager as M
from app.services import inspection_service as tasks, monthly_inspection_reports as reports


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Explicit disposable MongoDB tests only')
class PlanReportTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.ReportTests.asyncSetUp
    asyncTearDown = fixtures.ReportTests.asyncTearDown
    preview = fixtures.ReportTests.preview
    create = fixtures.ReportTests.create
    edit = fixtures.ReportTests.edit

    async def make_plan(self):
        preview = await self.preview(kind='PLAN')
        return await self.create(preview)

    async def finalize(self, doc):
        response = await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def refresh(self, doc):
        preview = await self.preview(kind=doc.get('kind', 'RESULT'), report_id=doc['id'], version=doc['version'])
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={
            'version': doc['version'], 'preview_id': preview['id']})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_plan_without_measurements_and_distinct_task_resource_targets(self):
        await M.get_db()[M.HEALTH_REPORTS].delete_many({})
        resource_id = ObjectId()
        await M.get_assets_servers_collection().insert_one({'_id': resource_id, 'name': 'RESOURCE-01', 'ip': '192.0.2.2'})
        await M.get_db()[M.APP_SETTINGS].insert_one({'_id': 'inspection_resource_targets', 'version': 1, 'asset_ids': [str(resource_id)]})
        # Explicit resource IDs from the fixture must not be read by a plan preview.
        plan = await self.make_plan()
        self.assertEqual(plan['kind'], 'PLAN')
        self.assertIn('계획서', plan['title'])
        self.assertIsNone(plan['snapshot']['source'])
        self.assertEqual(plan['snapshot']['servers'], [])
        self.assertEqual(plan['snapshot']['warnings'], [])
        self.assertEqual(plan['snapshot']['resource_targets'][0]['id'], str(resource_id))
        self.assertEqual(plan['snapshot']['tasks'][0]['assets'][0]['id'], str(self.aid))
        self.assertNotIn('result', plan['snapshot']['tasks'][0])
        self.assertEqual(plan['participants'][0]['user_id'], str(self.uid))
        self.assertEqual(plan['participants'][0]['assigned_tasks'][0]['issue_id'], str(self.iid))
        self.assertIn('CPU', plan['resource_checks'])
        changed = await self.edit(plan, resource_checks='운영 상태 확인', planned_time='10:00 ~ 12:00')
        changed = await self.edit(changed, overview='서비스 중단 없음')
        self.assertEqual(changed['resource_checks'], '운영 상태 확인')
        self.assertEqual(changed['planned_time'], '10:00 ~ 12:00')

    async def test_plan_excludes_removed_and_old_occurrences_but_keeps_work_plans(self):
        extra_ids = []
        for number, state, month in [(24, 'EXCLUDED', '2026-09'), (25, 'ROLLED', '2026-09'), (26, 'ACTIVE', '2026-08')]:
            iid = ObjectId()
            issue = {**self.issue, '_id': iid, 'number': number, 'status': 'TODO'}
            await M.get_pm_issues_collection().insert_one(issue)
            await tasks.register(issue, month, [], True, self.user)
            await tasks.collection().update_one({'_id': iid}, {'$set': {'occurrences.0.state': state}})
            extra_ids.append(str(iid))
        # Plan-only monthly tasks use the same snapshot path without creating a PM issue.
        task_id, entry_id = ObjectId(), ObjectId()
        source_task = await tasks.collection().find_one({'_id': self.iid})
        source_task['_id'] = task_id
        source_task.update(source_type='WORK_PLAN', work_plan_id=str(entry_id), project_id=None)
        source_task['occurrences'][0].pop('completed_snapshot', None)
        source_task['occurrences'][0].update(work_plan_snapshot={'id': str(entry_id), 'title': '작업계획서', 'template_title': '계획서', 'is_deleted': False},
                                            planned_on='2026-09-17', issue_snapshot={'id': str(task_id), 'project_id': '', 'key': '작업계획서', 'title': '작업계획서', 'status': 'TODO', 'assignee_id': str(self.uid), 'assignee_name': '점검자'})
        await tasks.collection().insert_one(source_task)
        plan = await self.make_plan()
        ids = [t['issue_id'] for t in plan['snapshot']['tasks']]
        self.assertIn(str(self.iid), ids)
        self.assertIn(str(task_id), ids)
        self.assertFalse(set(extra_ids) & set(ids))

    async def test_plan_result_coexist_and_legacy_results_remain_visible(self):
        plan = await self.make_plan()
        result = await self.create()
        self.assertNotEqual(plan['id'], result['id'])
        self.assertIn('결과서', result['title'])
        self.assertIsNone(result['snapshot']['plan'])  # Unsubmitted plans cannot be a baseline.
        await M.get_db()[reports.REPORTS].update_one({'_id': ObjectId(result['id'])}, {'$unset': {'kind': ''}})
        for kind, expected in [('PLAN', plan['id']), ('RESULT', result['id'])]:
            response = await self.client.get('/reports', params={'month': '2026-09', 'kind': kind})
            self.assertEqual([r['id'] for r in response.json()], [expected])
        default = await self.client.get('/reports', params={'month': '2026-09'})
        self.assertEqual([r['id'] for r in default.json()], [result['id']])
        read = await self.client.get('/reports/' + result['id'])
        self.assertEqual(read.json()['kind'], 'RESULT')
        retry = await self.make_plan()
        self.assertEqual(retry['id'], plan['id'])

    async def test_final_plan_and_result_baseline_survive_live_changes_and_plan_revision(self):
        await M.get_db()[M.APP_SETTINGS].insert_one({'_id': 'inspection_resource_targets', 'version': 1, 'asset_ids': [str(self.aid)]})
        plan = await self.edit(await self.make_plan(), planned_time='10:00 ~ 12:00', resource_checks='디스크 확인', overview='백업 후 진행')
        plan = await self.finalize(plan)
        baseline = deepcopy(plan)
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'title': '변경된 작업', 'assignee_id': None}})
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'RENAMED'}})
        await M.get_db()[M.APP_SETTINGS].update_one({'_id': 'inspection_resource_targets'}, {'$set': {'asset_ids': []}})
        result = await self.create()
        self.assertEqual(result['snapshot']['plan']['id'], plan['id'])
        self.assertEqual(result['snapshot']['plan']['tasks'][0]['issue']['title'], 'git migration')
        self.assertEqual(result['snapshot']['tasks'][0]['issue']['title'], '변경된 작업')
        self.assertEqual(result['snapshot']['plan']['resource_targets'][0]['name'], 'WEB-01')
        read = await self.client.get('/reports/' + plan['id'])
        self.assertEqual(read.json(), baseline)
        revised = await self.client.post('/reports/' + plan['id'] + '/revisions')
        self.assertEqual(revised.status_code, 201, revised.text)
        revised = await self.refresh(revised.json())
        self.assertEqual(revised['kind'], 'PLAN')
        self.assertEqual(revised['resource_checks'], '디스크 확인')
        self.assertEqual(revised['planned_time'], '10:00 ~ 12:00')
        self.assertEqual(revised['overview'], '백업 후 진행')
        self.assertEqual(revised['snapshot']['resource_targets'], [])
        self.assertEqual(revised['snapshot']['tasks'][0]['issue']['title'], '변경된 작업')
        revised = await self.finalize(revised)
        refreshed_result = await self.refresh(result)
        self.assertEqual(refreshed_result['snapshot']['plan'], result['snapshot']['plan'])
        latest = await self.preview()
        self.assertEqual(latest['snapshot']['plan']['id'], revised['id'])
        # Saving results or a revised plan never changes the already submitted original.
        read = await self.client.get('/reports/' + plan['id'])
        self.assertEqual(read.json(), baseline)

    async def test_plan_rejects_result_writes_kind_switches_and_stale_edits(self):
        plan = await self.make_plan()
        raw = await tasks.collection().find_one({'_id': self.iid})
        for suffix, body in [('/sync-results', {'version': plan['version']}),
                             (f"/tasks/{self.iid}/2026-09/result", {'version': 0, 'content': 'not a plan', 'performed_on': None, 'follow_up': ''}),
                             ('/action', {'version': plan['version'], 'row_key': 'fake', 'memo': 'not a plan'})]:
            method = self.client.post if suffix == '/sync-results' else self.client.put
            response = await method('/reports/' + plan['id'] + suffix, json=body)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await tasks.collection().find_one({'_id': self.iid}), raw)
        switch = await self.client.post('/reports/preview', json={'month': '2026-09', 'kind': 'RESULT', 'project_ids': plan['project_ids'], 'report_id': plan['id'], 'version': plan['version']})
        self.assertEqual(switch.status_code, 422, switch.text)
        changed = await self.edit(plan, overview='준비 내용')
        stale = await self.client.put('/reports/' + plan['id'] + '/notes', json={'version': plan['version'], 'notes': []})
        self.assertEqual(stale.status_code, 409, stale.text)
        final = await self.finalize(changed)
        locked = await self.client.put('/reports/' + plan['id'] + '/notes', json={'version': final['version'], 'notes': []})
        self.assertEqual(locked.status_code, 409, locked.text)
        self.user.permissions = []
        denied = await self.client.get('/reports/' + plan['id'])
        self.assertEqual(denied.status_code, 403, denied.text)
