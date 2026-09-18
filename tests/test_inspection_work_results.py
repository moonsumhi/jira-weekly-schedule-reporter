"""Work-result references share occurrence results and preserve report snapshots."""
import asyncio
import os
import unittest
from copy import deepcopy

from bson import ObjectId

import test_monthly_inspection_reports as fixtures
from app.db.mongo import MongoClientManager as M
from app.services import inspection_service as tasks


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Requires isolated MongoDB run')
class WorkResultTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.ReportTests.asyncSetUp
    asyncTearDown = fixtures.ReportTests.asyncTearDown
    preview = fixtures.ReportTests.preview
    create = fixtures.ReportTests.create

    async def entry(self, kind='RESULT', title='Git 이관 결과', asset_ids=None):
        tid, eid = ObjectId(), ObjectId()
        await M.get_form_templates_collection().insert_one({
            '_id': tid, 'menu': 'Job', 'jira_issue_key': 'JOB-' + kind,
            'title': '작업결과서' if kind == 'RESULT' else '작업계획서(서비스)'})
        await M.get_form_entries_collection().insert_one({
            '_id': eid, 'template_id': str(tid), 'version': 1, 'created_at': fixtures.svc.now(),
            'asset_ids': asset_ids if asset_ids is not None else [str(self.aid)],
            'linked_assets': [], 'data': {'기본 정보': {'작업명': title}, '문서 본문': [{'내용': '원본 본문'}]}})
        return str(eid)

    async def save(self, ids=None, version=0, **values):
        body = {'version': version, 'content': '', **values}
        if ids is not None:
            body['work_result_ids'] = ids
        return await self.client.put(f'/tasks/{self.iid}/2026-09/result', json=body)

    async def sync(self, doc):
        response = await self.client.post(f"/reports/{doc['id']}/sync-results", json={'version': doc['version']})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_search_only_results_and_validate_before_writing(self):
        self.user.permissions.append('job')
        result = await self.entry()
        other = await self.entry(title='백업 확인 결과', asset_ids=[])
        plan = await self.entry('PLAN-SERVICE', 'Git 이관 계획')
        url = '/tasks/work-results'
        response = await self.client.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({ref['id'] for ref in response.json()['items']}, {result, other})
        response = await self.client.get(url, params={'search': 'Git 이관', 'asset_ids': str(self.aid)})
        self.assertEqual([ref['id'] for ref in response.json()['items']], [result])
        for ids, status in (([plan], 422), ([result, result], 422), (['invalid'], 400), ([str(ObjectId())], 422), ([result] * 21, 422)):
            with self.subTest(ids=ids):
                response = await self.save(ids)
                self.assertEqual(response.status_code, status, response.text)
        stored = await tasks.collection().find_one({'_id': self.iid})
        self.assertNotIn('result', stored['occurrences'][0])

    async def test_report_and_monthly_task_share_results_and_keep_work_plans(self):
        self.user.permissions.append('job')
        plan, result = await self.entry('PLAN-SERVICE', 'Git 이관 계획'), await self.entry()
        await self.client.put(f'/tasks/{self.iid}/2026-09/work-plans', json={'work_plan_ids': [plan], 'version': 0})
        doc = await self.create()
        original = await M.get_form_entries_collection().find_one({'_id': ObjectId(result)})
        # Report editors do not need PM membership, but selecting job documents still needs job access.
        await M.get_pm_project_members_collection().delete_many({})
        response = await self.client.put(f"/reports/{doc['id']}/tasks/{self.iid}/2026-09/result", json={
            'version': 0, 'work_result_ids': [result], 'performed_on': '2026-09-17'})
        self.assertEqual(response.status_code, 200, response.text)
        doc = await self.sync(doc)
        task = doc['snapshot']['tasks'][0]
        self.assertEqual(task['work_plans'][0]['id'], plan)
        self.assertEqual(task['result']['work_results'][0]['id'], result)
        self.assertNotIn('missing_result', [w['code'] for w in doc['snapshot']['warnings']])
        self.assertNotIn('current', task['result']['work_results'][0])
        self.assertNotIn('data', task['result']['work_results'][0])
        self.assertEqual(await M.get_form_entries_collection().find_one({'_id': ObjectId(result)}), original)
        self.assertEqual(await M.get_pm_issues_collection().find_one({'_id': self.iid}), self.issue)
        await M.get_pm_project_members_collection().insert_one({'user_id': self.uid, 'project_id': self.pid, 'role': 'DEVELOPER'})
        response = await self.client.get('/tasks', params={'month': '2026-09', 'work_result_id': result, 'all_months': True})
        self.assertEqual(len(response.json()['items']), 1)
        self.assertEqual(response.json()['items'][0]['result']['work_results'][0]['id'], result)
        plan_preview = await self.preview(kind='PLAN', source_id=None, comparison_id=None)
        planned = plan_preview['snapshot']['tasks'][0]
        self.assertEqual(planned['work_plans'][0]['id'], plan)
        self.assertNotIn('result', planned)

    async def test_permissions_and_old_clients_preserve_existing_links(self):
        result = await self.entry()
        self.assertEqual((await self.client.get('/tasks/work-results')).status_code, 403)
        self.assertEqual((await self.save([result])).status_code, 403)
        self.user.permissions.append('job')
        self.assertEqual((await self.save([result])).status_code, 200)
        self.user.permissions.remove('job')
        response = await self.save(version=1, content='요약 수정')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['work_results'][0]['id'], result)
        self.assertEqual((await self.save([], version=2)).status_code, 403)
        self.assertEqual((await self.client.get('/tasks', params={'month': '2026-09', 'work_result_id': result})).status_code, 403)
        self.user.permissions = ['job']
        self.assertEqual((await self.save([result], version=2)).status_code, 403)

    async def test_concurrent_selection_and_unlink_are_atomic(self):
        self.user.permissions.append('job')
        result = await self.entry()
        responses = await asyncio.gather(self.save([result]), self.save([], content='다른 수정'))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual((await self.save([result], version=1)).status_code, 200)
        response = await self.save([], version=2)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['work_results'], [])
        rows = (await self.client.get('/tasks', params={'month': '2026-09', 'work_result_id': result})).json()['items']
        self.assertEqual(rows, [])

    async def test_reference_refresh_deleted_source_and_final_snapshot(self):
        self.user.permissions.append('job')
        result = await self.entry()
        await self.save([result])
        doc = await self.create()
        frozen = deepcopy(doc['snapshot'])
        await M.get_form_entries_collection().update_one({'_id': ObjectId(result)}, {'$set': {'version': 2, 'data.기본 정보.작업명': '최종 이관 결과'}})
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['snapshot'], frozen)
        doc = await self.sync(doc)
        ref = doc['snapshot']['tasks'][0]['result']['work_results'][0]
        self.assertEqual((ref['title'], ref['version']), ('최종 이관 결과', 2))
        self.assertNotIn('current', ref)
        final = (await self.client.post(f"/reports/{doc['id']}/finalize", json={'version': doc['version']})).json()
        await M.get_form_entries_collection().delete_one({'_id': ObjectId(result)})
        response = await self.save([result], version=1, content='추가 확인 완료')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['work_results'][0]['unavailable'])
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['snapshot'], final['snapshot'])
        self.assertEqual((await self.client.put(f"/reports/{doc['id']}/tasks/{self.iid}/2026-09/result", json={'version': 2, 'work_result_ids': []})).status_code, 409)

    async def test_plan_sourced_tasks_link_results_and_keep_source_plan(self):
        self.user.permissions.append('job')
        plan, result = await self.entry('PLAN-SERVICE', '독립 점검 계획'), await self.entry()
        response = await self.client.post('/tasks/from-work-plan', json={
            'month': '2026-09', 'work_plan_id': plan, 'asset_ids': [str(self.aid)], 'planned_on': '2026-09-17'})
        self.assertEqual(response.status_code, 201, response.text)
        task_id = response.json()['issue_id']
        response = await self.client.put(f'/tasks/{task_id}/2026-09/result', json={'version': 0, 'work_result_ids': [result]})
        self.assertEqual(response.status_code, 200, response.text)
        await M.get_pm_project_members_collection().delete_many({})
        doc = await self.create(await self.preview(project_ids=[]))
        task = doc['snapshot']['tasks'][0]
        self.assertEqual(task['work_plan']['id'], plan)
        self.assertEqual(task['result']['work_results'][0]['id'], result)
        # A result describes this occurrence and is not silently copied into next month's plan.
        response = await self.client.patch(f'/tasks/{task_id}/2026-09', json={'action': 'rollover', 'reason': '잔여 확인'})
        self.assertEqual(response.status_code, 200, response.text)
        rows = (await self.client.get('/tasks', params={'month': '2026-09', 'all_months': True, 'work_result_id': result})).json()['items']
        self.assertEqual([row['month'] for row in rows], ['2026-09'])
