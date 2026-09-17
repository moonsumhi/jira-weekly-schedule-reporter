"""Reports: real MongoDB isolated collections; never read or mutate application data."""
import asyncio
from copy import deepcopy
from datetime import timedelta
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.inspection_tasks import router as task_router
from app.routers.monthly_inspection_reports import router
from app.services import monthly_inspection_reports as svc, inspection_service as tasks


class MetricTests(unittest.TestCase):
    def test_zero_missing_and_percentages(self):
        for v in ('0', 0, '0%'):
            self.assertEqual(svc.pct(v), 0)
        for v in (None, '', '-', 'N/A', 'garbage', 'NaN', '-3%', '105%', 'Infinity'):
            self.assertIsNone(svc.pct(v))
        self.assertEqual(svc.pct('0.32'), 32)
        self.assertEqual(svc.pct('0.32%'), .32)
        self.assertEqual(svc.metric({'before_pct': '80%', 'after_pct': '0%'}, '50%')['value'], 0)
        self.assertEqual(svc.metric({'before_pct': '80%', 'after_pct': 'N/A'}, '50%')['basis'], '측정값')

    def test_monthly_reading_has_no_invented_before_after_comparison(self):
        for detail, expected in (({'after_pct': '0%'}, 0), ({'before_pct': '82%'}, 82),
                                 ({'before_pct': '80%', 'after_pct': '22%'}, 22)):
            with self.subTest(detail=detail):
                original = deepcopy(detail)
                reading = svc.metric(detail, None)
                self.assertEqual(reading, {'value': expected, 'basis': '측정값', 'delta': None})
                self.assertEqual(detail, original)
        self.assertEqual(svc.metric({}, '42%'), {'value': 42, 'basis': '요약 수치', 'delta': None})

    def test_real_filesystem_max_wins_total(self):
        d = svc.disk_metric({'disks': [{'filesystem': 'Total', 'pct': '50%'}, {'filesystem': '/', 'pct': '70%'}, {'filesystem': '/data', 'pct': '93%'}]}, {'disk_max': '60%'})
        self.assertEqual((d['value'], d['path']), (93, '/data'))
        self.assertEqual(svc.disk_metric({}, {})['value'], None)

    def test_ambiguous_summary_does_not_hide_detail_rows(self):
        source = {'summary': [{'host_name': 'same', 'ip': ''}], 'servers': [
            {'host_name': 'same', 'ip': '192.0.2.1'}, {'host_name': 'same', 'ip': '192.0.2.2'}]}
        rows = svc.resource_rows(source)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r['key'] for r in rows}), 3)

    def test_conflicting_ips_never_combine_summary_and_detail(self):
        rows = svc.resource_rows({'summary': [{'host_name': 'same', 'ip': '192.0.2.1', 'cpu': '90%'}],
                                  'servers': [{'host_name': 'same', 'ip': '192.0.2.2', 'cpu': {'after_pct': '0%'}}]})
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['cpu']['value'] for r in rows], [90, 0])


class ParticipantAssignmentTests(unittest.TestCase):
    def test_only_current_active_tasks_are_assigned_by_user_id(self):
        def task(issue_id, **values):
            return {'issue_id': issue_id, 'month': '2026-09', 'state': 'ACTIVE',
                    'issue': {'key': issue_id, 'title': issue_id, 'assignee_id': 'user-1',
                              'assignee_name': '같은 이름', 'status': 'TODO'}, **values}
        active = task('active')
        wrong_user = task('other', issue={**active['issue'], 'assignee_id': 'user-2'})
        unassigned = task('unassigned', issue={**active['issue'], 'assignee_id': None})
        doc = {'month': '2026-09', 'snapshot': {'tasks': [
            active, deepcopy(active), task('excluded', state='EXCLUDED'), task('rolled', state='ROLLED'),
            task('old', month='2026-08'), wrong_user, unassigned], 'carryover': [task('carryover')]}}
        original = deepcopy(doc)
        linked = svc.assigned_participant_tasks(doc, 'user-1')
        self.assertEqual([t['issue_id'] for t in linked], ['active'])
        self.assertEqual(doc, original)


class PrefixDB:
    def __init__(self, db):
        self.db, self.prefix, self.names = db, 'test_monthly_report_' + uuid4().hex + '_', set()
    def __getitem__(self, name):
        self.names.add(name)
        return self.db[self.prefix + name]
    async def cleanup(self):
        for name in self.names:
            await self.db.drop_collection(self.prefix + name)


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Explicit disposable MongoDB tests only')
class ReportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = PrefixDB(M.get_db())
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.month_patch = patch.object(tasks, 'current_month', return_value='2026-09')
        self.month_patch.start()
        await svc.indexes()
        self.uid, self.pid, self.aid, self.iid, self.sid, self.old_sid = [ObjectId() for _ in range(6)]
        self.user = UserPublic(id=str(self.uid), email='report-test@example.com', full_name='점검자', permissions=['server_check'])
        await M.get_pm_projects_collection().insert_one({'_id': self.pid, 'key': 'TEST', 'name': '운영'})
        await M.get_pm_project_members_collection().insert_one({'user_id': self.uid, 'project_id': self.pid, 'role': 'DEVELOPER'})
        await M.get_users_collection().insert_one({'_id': self.uid, 'full_name': '점검자'})
        await M.get_assets_servers_collection().insert_one({'_id': self.aid, 'name': 'WEB-01', 'ip': '192.0.2.1'})
        self.issue = {'_id': self.iid, 'project_id': self.pid, 'number': 23, 'title': 'git migration', 'status': 'DONE', 'assignee_id': self.uid}
        await M.get_pm_issues_collection().insert_one(self.issue)
        await tasks.register(self.issue, '2026-09', await tasks.resolve_assets([str(self.aid)]), False, self.user)
        self.source = {'_id': self.sid, 'report_date': '2026-09-17', 'report_title': '9월 점검', 'uploaded_at': svc.now(), 'uploaded_by': '점검자',
            'summary': [{'host_name': 'web-01', 'ip': '192.0.2.1', 'cpu': '0%', 'ram': 'N/A', 'disk_max': '50%', 'log_errors': ''}],
            'servers': [{'host_name': 'web-01', 'ip': '192.0.2.1', 'cpu': {'before_pct': '20%', 'after_pct': '0%'},
                         'ram': {'before_pct': '82%', 'after_pct': 'N/A'}, 'disks': [{'filesystem': 'Total', 'pct': '50%'}, {'filesystem': '/data', 'pct': '95%'}],
                         'hw_checks': [{'item': 'Disk LED', 'ng': True}], 'security_checks': [{'item': '패치', 'result': '미확인'}]}]}
        await M.get_db()[M.HEALTH_REPORTS].insert_one(deepcopy(self.source))
        old = deepcopy(self.source); old.update(_id=self.old_sid, report_date='2026-08-20')
        old['servers'][0]['cpu']['after_pct'] = '10%'
        old['servers'][0]['disks'][1]['pct'] = '90%'
        await M.get_db()[M.HEALTH_REPORTS].insert_one(old)
        app = FastAPI(); app.include_router(router, prefix='/reports'); app.include_router(task_router, prefix='/tasks')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose(); await self.db.cleanup(); self.month_patch.stop(); self.db_patch.stop()
        M.get_client().close(); M._client = None

    async def preview(self, **overrides):
        body = {'month': '2026-09', 'project_ids': [str(self.pid)], 'source_id': str(self.sid), 'comparison_id': str(self.old_sid), **overrides}
        response = await self.client.post('/reports/preview', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def create(self, preview=None, client_id=None):
        p = preview or await self.preview()
        response = await self.client.post('/reports', json={'preview_id': p['id'], 'client_id': client_id or uuid4().hex})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def edit(self, doc, **values):
        body = {k: doc[k] for k in ('title', 'inspection_date', 'purpose', 'overview', 'limitations', 'include_appendix')}
        response = await self.client.patch('/reports/' + doc['id'], json={**body, 'version': doc['version'], **values})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def action_context(self, doc, **target):
        response = await self.client.get(f"/reports/{doc['id']}/action", params=target)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def write_action(self, doc, context, **values):
        return await self.client.put(f"/reports/{doc['id']}/action", json={
            'row_key': doc['snapshot']['servers'][0]['key'], 'version': context['version'],
            'action_token': context['action_token'], 'memo': '로그 정리 후 정상 동작 확인',
            'images': [], 'is_resolved': False, **values})

    async def test_action_edit_updates_source_and_report_without_refreshing_metrics(self):
        doc = await self.create()
        before = deepcopy(doc['snapshot']['servers'][0])
        ctx = await self.action_context(doc, row_key=before['key'])
        self.assertIsNone(ctx['action'])
        # Shared source data can change without silently replacing captured measurements.
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'servers.0.cpu.after_pct': '99%'}})
        response = await self.write_action(doc, ctx)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json(); updated = data['report']
        self.assertEqual(data['warning'], '')
        self.assertEqual(updated['version'], doc['version'] + 1)
        self.assertEqual(updated['snapshot']['servers'][0]['cpu'], before['cpu'])
        action = updated['snapshot']['servers'][0]['action']
        source_action = await M.get_db()[M.HEALTH_ACTIONS].find_one({'_id': ObjectId(action['id'])})
        self.assertEqual(source_action['report_id'], str(self.sid))
        self.assertEqual(source_action['memo'], action['memo'])
        self.assertFalse(action['is_resolved'])
        image = 'data:image/png;base64,aGVsbG8='
        await M.get_db()[M.HEALTH_ACTIONS].update_one({'_id': source_action['_id']}, {'$set': {'images': [image]}})
        ctx = await self.action_context(updated, row_key=before['key'])
        self.assertEqual(ctx['action']['images'], [image])
        result = await self.write_action(updated, ctx, memo='검증 완료', images=ctx['action']['images'], is_resolved=True)
        self.assertEqual(result.status_code, 200, result.text)
        final_action = result.json()['report']['snapshot']['servers'][0]['action']
        self.assertEqual(final_action['images'], [image])
        self.assertTrue(final_action['is_resolved'])

    async def test_action_edit_access_scope_and_final_are_checked_before_source_write(self):
        doc = await self.create(); row = doc['snapshot']['servers'][0]
        ctx = await self.action_context(doc, row_key=row['key'])
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        # server_check grants report editing without membership in the task's project.
        response = await self.write_action(doc, ctx)
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()['report']; ctx = await self.action_context(doc, row_key=row['key'])
        for target in ({'row_key': 'unrelated'}, {'row_key': None, 'action_id': str(ObjectId())}):
            response = await self.write_action(doc, ctx, **target)
            self.assertEqual(response.status_code, 404, response.text)
        self.user = self.user.model_copy(update={'permissions': []})
        self.assertEqual((await self.write_action(doc, ctx)).status_code, 403)
        self.user = self.user.model_copy(update={'permissions': ['server_check']})
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {'$set': {'state': 'FINAL'}})
        original = await M.get_db()[M.HEALTH_ACTIONS].find_one({'report_id': str(self.sid)})
        self.assertEqual((await self.write_action(doc, ctx, memo='확정본 수정')).status_code, 409)
        self.assertEqual(await M.get_db()[M.HEALTH_ACTIONS].find_one({'report_id': str(self.sid)}), original)
        self.assertEqual((await self.client.get(f"/reports/{doc['id']}/action", params={'row_key': row['key']})).status_code, 409)

    async def test_action_edit_conflicts_keep_other_writers_changes(self):
        doc = await self.create(); key = doc['snapshot']['servers'][0]['key']
        ctx = await self.action_context(doc, row_key=key)
        responses = await asyncio.gather(self.write_action(doc, ctx, memo='첫 번째'), self.write_action(doc, ctx, memo='두 번째'))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual(await M.get_db()[M.HEALTH_ACTIONS].count_documents({'report_id': str(self.sid)}), 1)
        doc = next(r.json()['report'] for r in responses if r.status_code == 200)
        ctx = await self.action_context(doc, row_key=key)
        # The original resource editor does not bump a version; token checks still detect its changes.
        await M.get_db()[M.HEALTH_ACTIONS].update_one({'report_id': str(self.sid)}, {'$set': {'memo': '자원 점검에서 수정'}})
        self.assertEqual((await self.write_action(doc, ctx)).status_code, 409)
        latest = await M.get_db()[M.HEALTH_ACTIONS].find_one({'report_id': str(self.sid)})
        self.assertEqual(latest['memo'], '자원 점검에서 수정')
        fresh = await self.action_context(doc, row_key=key)
        doc = await self.edit(doc, overview='보고서 수정')
        self.assertEqual((await self.write_action(doc, fresh)).status_code, 409)

    async def test_action_edit_rejects_missing_or_ambiguous_source_and_wrong_month(self):
        doc = await self.create(); key = doc['snapshot']['servers'][0]['key']
        ctx = await self.action_context(doc, row_key=key)
        duplicate = deepcopy(self.source['servers'][0]); duplicate['ip'] = '192.0.2.2'
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$push': {'servers': duplicate}})
        self.assertEqual((await self.write_action(doc, ctx)).status_code, 409)
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'servers': self.source['servers'], 'report_date': '2026-08-20'}})
        self.assertEqual((await self.write_action(doc, ctx)).status_code, 422)
        await M.get_db()[M.HEALTH_REPORTS].delete_one({'_id': self.sid})
        self.assertEqual((await self.write_action(doc, ctx)).status_code, 422)
        self.assertEqual(await M.get_db()[M.HEALTH_ACTIONS].count_documents({}), 0)

    async def test_action_edit_unmatched_action_uses_exact_id_and_source(self):
        result = await M.get_db()[M.HEALTH_ACTIONS].insert_one({'report_id': str(self.sid), 'host_name': 'legacy-server',
            'memo': '대상 확인', 'is_resolved': False, 'images': []})
        doc = await self.create(); action_id = str(result.inserted_id)
        ctx = await self.action_context(doc, action_id=action_id)
        response = await self.write_action(doc, ctx, row_key=None, action_id=action_id, memo='호스트명 변경 확인', is_resolved=True)
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()['report']['snapshot']
        self.assertEqual(updated['unmatched_actions'][0]['memo'], '호스트명 변경 확인')
        self.assertIsNone(updated['servers'][0]['action'])

    async def test_action_save_merges_concurrent_report_edit_without_overwriting_notes(self):
        doc = await self.create(); ctx = await self.action_context(doc, row_key=doc['snapshot']['servers'][0]['key'])
        original_change = svc.change_report
        calls = 0
        async def concurrent_change(document, user, values):
            nonlocal calls
            calls += 1
            if calls == 1:
                await original_change(document, user, {'limitations': '다른 작성자의 참고 사항'})
            return await original_change(document, user, values)
        with patch.object(svc, 'change_report', side_effect=concurrent_change):
            response = await self.write_action(doc, ctx)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['warning'], '')
        self.assertEqual(response.json()['report']['limitations'], '다른 작성자의 참고 사항')
        self.assertEqual(response.json()['report']['snapshot']['servers'][0]['action']['memo'], '로그 정리 후 정상 동작 확인')

    async def test_action_retry_uses_newest_source_when_another_editor_saves_same_action(self):
        doc = await self.create(); ctx = await self.action_context(doc, row_key=doc['snapshot']['servers'][0]['key'])
        original_change = svc.change_report
        calls = 0
        async def concurrent_change(document, user, values):
            nonlocal calls
            calls += 1
            if calls == 1:
                await M.get_db()[M.HEALTH_ACTIONS].update_one({'report_id': str(self.sid)}, {'$set': {'memo': '더 최근 조치'}})
                await original_change(document, user, {'overview': '동시 수정'})
            return await original_change(document, user, values)
        with patch.object(svc, 'change_report', side_effect=concurrent_change):
            response = await self.write_action(doc, ctx)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['report']['snapshot']['servers'][0]['action']['memo'], '더 최근 조치')

    async def test_action_save_cannot_rewrite_concurrently_finalized_report(self):
        doc = await self.create(); ctx = await self.action_context(doc, row_key=doc['snapshot']['servers'][0]['key'])
        original_change = svc.change_report
        async def finalize_first(document, user, values):
            await original_change(document, user, {'state': 'FINAL'})
            return await original_change(document, user, values)
        with patch.object(svc, 'change_report', side_effect=finalize_first):
            response = await self.write_action(doc, ctx)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['warning'])
        frozen = response.json()['report']
        self.assertEqual(frozen['state'], 'FINAL')
        self.assertEqual(frozen['snapshot'], doc['snapshot'])
        self.assertEqual(await M.get_db()[M.HEALTH_ACTIONS].count_documents({}), 1)

    async def test_preview_zero_max_disk_comparison_and_automatic_hostname_match(self):
        p = await self.preview(); row = p['snapshot']['servers'][0]
        self.assertEqual(row['cpu']['value'], 0)
        self.assertEqual(row['cpu']['delta'], -10)
        self.assertEqual((row['disk']['value'], row['disk']['path'], row['disk']['delta']), (95, '/data', 5))
        self.assertEqual(row['asset']['id'], str(self.aid)); self.assertIsNone(row['candidate'])
        self.assertEqual(p['snapshot']['stats']['danger'], 1)
        self.assertEqual(len(p['snapshot']['missing_asset_resources']), 0)
        await self.create(p)
        next_p = await self.preview()
        self.assertEqual(next_p['snapshot']['servers'][0]['mapping_state'], 'automatic')
        self.assertEqual(len(next_p['snapshot']['missing_asset_resources']), 0)

    async def test_same_month_sources_and_no_silent_fallback(self):
        response = await self.client.post('/reports/preview', json={'month': '2026-09', 'source_id': str(self.old_sid)})
        self.assertEqual(response.status_code, 422)
        p = await self.preview(source_id=None, comparison_id=None)
        self.assertIsNone(p['snapshot']['source']); self.assertEqual(p['snapshot']['stats']['servers'], 0)
        response = await self.client.post('/reports/preview', json={'month': '2026-09', 'source_id': str(self.sid), 'comparison_id': str(self.sid)})
        self.assertEqual(response.status_code, 422)

    async def test_server_check_user_without_membership_can_edit_entire_report(self):
        doc = await self.create()
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).status_code, 200)
        self.assertEqual([d['id'] for d in (await self.client.get('/reports?month=2026-09')).json()], [doc['id']])
        path = f"/reports/{doc['id']}/tasks/{self.iid}/2026-09"
        response = await self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['issue_id'], str(self.iid))
        response = await self.client.put(path + '/result', json={'version': 0, 'content': '공동 작성한 결과', 'performed_on': '2026-09-17'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['updated_by_id'], self.user.id)
        self.assertEqual((await self.client.put(path + '/result', json={'version': 0, 'content': '충돌'})).status_code, 409)
        doc = (await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': doc['version']})).json()
        self.assertEqual(doc['snapshot']['tasks'][0]['result']['content'], '공동 작성한 결과')
        response = await self.save_participants(doc, [self.participant()])
        self.assertEqual(response.status_code, 200, response.text)
        doc = await self.edit(response.json(), overview='공동 편집', limitations='후속 점검 예정')
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        self.assertEqual(len(p['snapshot']['tasks']), 1)
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc['overview'], '공동 편집')
        self.assertEqual(len(doc['participants']), 1)
        response = await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})
        self.assertEqual(response.status_code, 200, response.text)
        final = response.json()
        self.assertEqual((await self.client.put(path + '/result', json={'version': 1, 'content': '확정본 수정'})).status_code, 409)
        response = await self.client.post('/reports/' + doc['id'] + '/revisions')
        self.assertEqual(response.status_code, 201, response.text)
        revised = await self.edit(response.json(), overview='개정 의견')
        self.assertEqual(revised['overview'], '개정 의견')
        self.assertEqual((await self.client.get('/reports/' + final['id'])).json(), final)
        # Sharing a report does not grant PM membership or widen unrelated inspection actions.
        self.assertEqual(await M.get_pm_project_members_collection().count_documents({'user_id': ObjectId(self.user.id)}), 0)
        self.assertEqual((await self.client.put(f'/tasks/{self.iid}/2026-09/result', json={'version': 1, 'content': '직접 수정'})).status_code, 403)

    async def test_report_routes_require_server_check_permission(self):
        p = await self.preview()
        doc = await self.create(p)
        self.user = self.user.model_copy(update={'permissions': []})
        base = '/reports/' + doc['id']
        calls = [
            ('get', '/reports?month=2026-09', None), ('get', '/reports/options?month=2026-09', None),
            ('get', '/reports/participant-options', None), ('get', base, None),
            ('post', '/reports/preview', {'month': '2026-09'}),
            ('post', '/reports', {'preview_id': p['id'], 'client_id': uuid4().hex}),
            ('patch', base, {'version': doc['version'], 'title': '권한 없음', 'inspection_date': doc['inspection_date']}),
            ('put', base + '/participants', {'version': doc['version'], 'participants': []}),
            ('post', base + '/refresh', {'version': doc['version'], 'preview_id': p['id']}),
            ('post', base + '/sync-results', {'version': doc['version']}),
            ('post', base + '/finalize', {'version': doc['version']}),
            ('post', base + '/revisions', None),
            ('get', f'{base}/tasks/{self.iid}/2026-09', None),
            ('put', f'{base}/tasks/{self.iid}/2026-09/result', {'version': 0, 'content': '권한 없음'}),
        ]
        for method, path, body in calls:
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 403, response.text)
        saved = await M.get_db()[svc.REPORTS].find_one({'_id': ObjectId(doc['id'])})
        self.assertEqual(saved['version'], doc['version'])
        self.assertEqual(saved['state'], 'DRAFT')

    async def test_report_creation_includes_inspection_tasks_across_projects(self):
        other_project = ObjectId()
        await M.get_pm_projects_collection().insert_one({'_id': other_project, 'key': 'OTHER', 'name': '다른 프로젝트'})
        issue = {**self.issue, '_id': ObjectId(), 'project_id': other_project, 'number': 1}
        await M.get_pm_issues_collection().insert_one(issue)
        await tasks.register(issue, '2026-09', [], True, self.user)
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        response = await self.client.post('/reports/preview', json={'month': '2026-09'})
        self.assertEqual(response.status_code, 200, response.text)
        p = response.json()
        self.assertEqual({t['issue_id'] for t in p['snapshot']['tasks']}, {str(self.iid), str(issue['_id'])})
        self.assertEqual({p['id'] for p in p['projects']}, {str(self.pid), str(other_project)})
        doc = await self.create(p)
        self.assertEqual(doc['snapshot']['stats']['planned'], 2)

    async def test_report_result_endpoint_only_allows_included_occurrences(self):
        doc = await self.create()
        extra = {**self.issue, '_id': ObjectId(), 'number': 24}
        await M.get_pm_issues_collection().insert_one(extra)
        await tasks.register(extra, '2026-09', [], True, self.user)
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        for issue_id, month in [(extra['_id'], '2026-09'), (self.iid, '2026-10'), (ObjectId(), '2026-09')]:
            path = f"/reports/{doc['id']}/tasks/{issue_id}/{month}"
            self.assertEqual((await self.client.get(path)).status_code, 404)
            self.assertEqual((await self.client.put(path + '/result', json={'version': 0, 'content': '범위 밖'})).status_code, 404)
        extra_doc = await tasks.collection().find_one({'_id': extra['_id']})
        self.assertNotIn('result', extra_doc['occurrences'][0])

    async def test_automatic_sources_use_latest_inspection_per_month_and_include_images(self):
        current_id, previous_id = ObjectId(), ObjectId()
        rows = [
            (current_id, '2026-09-18', -1, '4%'),
            (ObjectId(), '2026-09-10', 10, '99%'),
            (previous_id, '2026-08-29', -2, '20%'),
            (ObjectId(), '2026-10-01', 20, '90%'),
        ]
        for source_id, report_date, upload_days, cpu in rows:
            source = deepcopy(self.source)
            source.update(_id=source_id, report_date=report_date, uploaded_at=svc.now() + timedelta(days=upload_days))
            source['servers'][0]['cpu']['after_pct'] = cpu
            await M.get_db()[M.HEALTH_REPORTS].insert_one(source)
        image = 'data:image/png;base64,AAAA'
        await M.get_db()[M.HEALTH_ACTIONS].insert_one({'report_id': str(current_id), 'host_name': 'web-01', 'memo': '조치 확인', 'images': [image]})
        response = await self.client.post('/reports/preview', json={'month': '2026-09'})
        self.assertEqual(response.status_code, 200, response.text)
        p = response.json()
        self.assertEqual(p['snapshot']['source']['id'], str(current_id))
        self.assertEqual(p['snapshot']['comparison']['id'], str(previous_id))
        self.assertEqual(p['snapshot']['servers'][0]['cpu']['delta'], -16)
        self.assertEqual(p['snapshot']['servers'][0]['action']['images'], [image])
        self.assertEqual(len(p['snapshot']['tasks']), 1)
        doc = await self.create(p)
        self.assertTrue(doc['include_images'])
        self.assertEqual(doc['snapshot'], p['snapshot'])

    async def test_automatic_comparison_never_uses_same_month_or_older_month(self):
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.old_sid}, {'$set': {'report_date': '2026-07-20'}})
        earlier = deepcopy(self.source)
        earlier.update(_id=ObjectId(), report_date='2026-09-01')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(earlier)
        response = await self.client.post('/reports/preview', json={'month': '2026-09'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['snapshot']['source']['id'], str(self.sid))
        self.assertIsNone(response.json()['snapshot']['comparison'])
        self.assertIsNone(response.json()['snapshot']['servers'][0]['cpu']['delta'])
        response = await self.client.post('/reports/preview', json={'month': '2026-10'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()['snapshot']['source'])
        self.assertIsNone(response.json()['snapshot']['comparison'])
        self.assertIn('no_source', [w['code'] for w in response.json()['snapshot']['warnings']])

    async def test_automatic_comparison_crosses_year_boundary(self):
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'report_date': '2026-01-10'}})
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.old_sid}, {'$set': {'report_date': '2025-12-20'}})
        response = await self.client.post('/reports/preview', json={'month': '2026-01'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['snapshot']['source']['id'], str(self.sid))
        self.assertEqual(response.json()['snapshot']['comparison']['id'], str(self.old_sid))

    async def test_automatic_refresh_uses_new_month_data_and_enables_images_for_old_drafts(self):
        doc = await self.create(await self.preview(include_images=False))
        doc = await self.edit(doc, overview='기존 종합 의견')
        newer = deepcopy(self.source)
        newer.update(_id=ObjectId(), report_date='2026-09-25')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(newer)
        response = await self.client.post('/reports/preview', json={
            'month': doc['month'], 'project_ids': doc['project_ids'], 'report_id': doc['id'], 'version': doc['version']})
        self.assertEqual(response.status_code, 200, response.text)
        p = response.json()
        self.assertEqual(p['snapshot']['source']['id'], str(newer['_id']))
        # Preview alone does not mutate the saved draft.
        saved = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertFalse(saved['include_images'])
        self.assertEqual(saved['snapshot']['source']['id'], str(self.sid))
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['include_images'])
        self.assertEqual(response.json()['overview'], '기존 종합 의견')
        self.assertEqual(response.json()['snapshot']['source']['id'], str(newer['_id']))

    async def test_create_race_and_retry_idempotent(self):
        p = await self.preview(); key = uuid4().hex
        docs = await asyncio.gather(*(self.create(p, key if i < 2 else uuid4().hex) for i in range(4)))
        self.assertEqual(len({d['id'] for d in docs}), 1)
        self.assertEqual(await M.get_db()[svc.REPORTS].count_documents({}), 1)

    async def test_server_check_user_can_read_and_refresh_after_project_deletion(self):
        doc = await self.create()
        await M.get_pm_projects_collection().delete_one({'_id': self.pid})
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).status_code, 200)
        self.assertEqual(len((await self.client.get('/reports?month=2026-09')).json()), 1)
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        self.assertEqual(p['projects'], doc['projects'])
        self.assertEqual(len(p['snapshot']['tasks']), 1)
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})
        self.assertEqual(response.status_code, 200, response.text)

    async def test_same_idempotency_key_cannot_create_different_report(self):
        p = await self.preview(); key = uuid4().hex
        await self.create(p, key)
        other = await self.preview(source_id=None, comparison_id=None)
        response = await self.client.post('/reports', json={'preview_id': other['id'], 'client_id': key})
        self.assertEqual(response.status_code, 409)

    async def test_hostname_matches_even_with_shared_or_changed_ip(self):
        await M.get_assets_servers_collection().insert_one({'name': 'another-host', 'ip': '192.0.2.1'})
        for ip in ('192.0.2.1', '198.51.100.1', ''):
            await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'ip': ip}})
            row = (await self.preview())['snapshot']['servers'][0]
            self.assertEqual(row['asset']['id'], str(self.aid))
            self.assertEqual(row['mapping_state'], 'automatic')

    async def test_correcting_asset_hostname_connects_current_and_next_month(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'incorrect'}})
        row = (await self.preview())['snapshot']['servers'][0]
        self.assertIsNone(row['asset'])
        self.assertEqual(row['candidate']['id'], str(self.aid))
        self.assertEqual(row['mapping_issue'], 'hostname_mismatch')
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': ' WEB-01. '}})
        october = deepcopy(self.source); october.update(_id=ObjectId(), report_date='2026-10-15')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(october)
        for month, sid, old in [('2026-09', self.sid, self.old_sid), ('2026-10', october['_id'], self.sid)]:
            p = await self.preview(month=month, source_id=str(sid), comparison_id=str(old))
            self.assertEqual(p['snapshot']['servers'][0]['asset']['id'], str(self.aid))
            await self.create(p)
        self.assertEqual(await M.get_db()[svc.MAPPINGS].count_documents({}), 0)

    async def test_legacy_alias_does_not_override_canonical_hostname(self):
        row = (await self.preview())['snapshot']['servers'][0]
        wrong_id = (await M.get_assets_servers_collection().insert_one({'name': 'wrong-host', 'ip': '192.0.2.99'})).inserted_id
        for baseline in ({}, {'asset_identity': {'name': 'wrong-host', 'ips': ['192.0.2.99']}}):
            await M.get_db()[svc.MAPPINGS].replace_one({'_id': row['identity_key']}, {'_id': row['identity_key'], 'asset_id': str(wrong_id), **baseline}, upsert=True)
            current = (await self.preview())['snapshot']['servers'][0]
            self.assertEqual(current['asset']['id'], str(self.aid))
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'incorrect'}})
        self.assertIsNone((await self.preview())['snapshot']['servers'][0]['asset'])
        self.assertEqual(await M.get_db()[svc.MAPPINGS].count_documents({}), 1)

    async def test_hostname_corrections_do_not_mutate_saved_reports(self):
        doc = await self.create()
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {'$set': {'state': 'FINAL'}})
        frozen = (await self.client.get('/reports/' + doc['id'])).json()['snapshot']
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'changed'}})
        self.assertIsNone((await self.preview())['snapshot']['servers'][0]['asset'])
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['snapshot'], frozen)
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'web-01'}})
        self.assertEqual((await self.preview())['snapshot']['servers'][0]['asset']['id'], str(self.aid))
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['snapshot'], frozen)

    async def test_duplicate_asset_or_measurement_hostnames_require_review(self):
        duplicate_id = (await M.get_assets_servers_collection().insert_one({'name': 'Web-01.', 'ip': '198.51.100.1'})).inserted_id
        row = (await self.preview())['snapshot']['servers'][0]
        self.assertIsNone(row['asset']); self.assertEqual(row['mapping_issue'], 'ambiguous_hostname')
        await M.get_assets_servers_collection().delete_one({'_id': duplicate_id})
        duplicate = deepcopy(self.source['servers'][0]); duplicate['ip'] = '198.51.100.10'
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$push': {'servers': duplicate}})
        rows = (await self.preview())['snapshot']['servers']
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['asset'] is None and r['mapping_issue'] == 'ambiguous_hostname' for r in rows))

    async def test_deleted_or_missing_hostname_never_automatically_connects(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        self.assertIsNone((await self.preview())['snapshot']['servers'][0]['asset'])
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': False, 'name': '이름 없음'}})
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'summary': [], 'servers': [{'host_name': '', 'ip': '192.0.2.1'}]}})
        row = (await self.preview())['snapshot']['servers'][0]
        self.assertIsNone(row['asset']); self.assertEqual(row['mapping_issue'], 'missing_hostname')

    async def test_exception_connection_stays_in_report_and_never_becomes_alias(self):
        source_before = await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid})
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'exception-target'}})
        row = (await self.preview())['snapshot']['servers'][0]
        p = await self.preview(mappings=[{'row_key': row['key'], 'asset_id': str(self.aid)}])
        self.assertEqual(p['snapshot']['servers'][0]['mapping_state'], 'manual')
        doc = await self.create(p)
        self.assertEqual(doc['snapshot']['servers'][0]['asset']['id'], str(self.aid))
        self.assertEqual(await M.get_db()[svc.MAPPINGS].count_documents({}), 0)
        self.assertEqual(await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid}), source_before)
        # A fresh preview, even in the same month, never infers an exception from other reports.
        self.assertIsNone((await self.preview())['snapshot']['servers'][0]['asset'])
        october = deepcopy(self.source); october.update(_id=ObjectId(), report_date='2026-10-15')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(october)
        p = await self.preview(month='2026-10', source_id=str(october['_id']), comparison_id=str(self.sid))
        self.assertIsNone(p['snapshot']['servers'][0]['asset'])
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['snapshot'], doc['snapshot'])

    async def test_refresh_keeps_only_this_reports_same_source_exception_and_can_clear_it(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'exception-target'}})
        row = (await self.preview())['snapshot']['servers'][0]
        doc = await self.create(await self.preview(mappings=[{'row_key': row['key'], 'asset_id': str(self.aid)}]))
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        self.assertEqual(p['snapshot']['servers'][0]['mapping_state'], 'manual')
        p = await self.preview(report_id=doc['id'], version=doc['version'], mappings=[])
        self.assertIsNone(p['snapshot']['servers'][0]['asset'])
        replacement = deepcopy(self.source); replacement.update(_id=ObjectId(), report_date='2026-09-20')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(replacement)
        p = await self.preview(report_id=doc['id'], version=doc['version'], source_id=str(replacement['_id']))
        self.assertIsNone(p['snapshot']['servers'][0]['asset'])
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        self.assertIsNone(p['snapshot']['servers'][0]['asset'])

    async def test_exception_connection_validates_source_rows_and_active_assets(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'exception-target'}})
        row = (await self.preview())['snapshot']['servers'][0]
        mapping = {'row_key': row['key'], 'asset_id': str(self.aid)}
        cases = [
            {'mappings': [mapping]},
            {'source_id': str(self.old_sid), 'mappings': [mapping]},
            {'source_id': str(self.sid), 'mappings': [mapping, mapping]},
            {'source_id': str(self.sid), 'mappings': [{**mapping, 'row_key': 'stale'}]},
            {'source_id': str(self.sid), 'mappings': [{**mapping, 'asset_id': str(ObjectId())}]},
        ]
        for body in cases:
            response = await self.client.post('/reports/preview', json={'month': '2026-09', **body})
            self.assertEqual(response.status_code, 422, response.text)
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        response = await self.client.post('/reports/preview', json={'month': '2026-09', 'source_id': str(self.sid), 'mappings': [mapping]})
        self.assertEqual(response.status_code, 422)

    async def test_automatic_match_wins_after_hostname_correction_and_duplicate_rows_allow_explicit_choice(self):
        other = (await M.get_assets_servers_collection().insert_one({'name': 'other', 'ip': '192.0.2.99'})).inserted_id
        row = (await self.preview())['snapshot']['servers'][0]
        p = await self.preview(mappings=[{'row_key': row['key'], 'asset_id': str(other)}])
        self.assertEqual(p['snapshot']['servers'][0]['asset']['id'], str(self.aid))
        self.assertEqual(p['snapshot']['servers'][0]['mapping_state'], 'automatic')
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'summary': []}, '$push': {'servers': deepcopy(self.source['servers'][0])}})
        rows = (await self.preview())['snapshot']['servers']
        p = await self.preview(mappings=[{'row_key': rows[1]['key'], 'asset_id': str(other)}])
        self.assertIsNone(p['snapshot']['servers'][0]['asset'])
        self.assertEqual(p['snapshot']['servers'][1]['asset']['id'], str(other))
        self.assertEqual(await M.get_db()[svc.MAPPINGS].count_documents({}), 0)

    async def test_expired_or_other_users_preview_not_consumed(self):
        p = await self.preview()
        await M.get_db()[svc.PREVIEWS].update_one({'_id': ObjectId(p['id'])}, {'$set': {'owner': str(ObjectId())}})
        res = await self.client.post('/reports', json={'preview_id': p['id'], 'client_id': uuid4().hex})
        self.assertEqual(res.status_code, 409)
        await M.get_db()[svc.PREVIEWS].update_one({'_id': ObjectId(p['id'])}, {'$set': {'owner': self.user.id, 'expires_at': svc.now() - timedelta(minutes=1)}})
        res = await self.client.post('/reports', json={'preview_id': p['id'], 'client_id': uuid4().hex})
        self.assertEqual(res.status_code, 409)

    async def test_result_shared_and_concurrent_writes_conflict(self):
        doc = await self.create()
        url = f'/tasks/{self.iid}/2026-09/result'
        body = {'version': 0, 'content': '이관 완료, 서비스 확인', 'performed_on': '2026-09-17', 'follow_up': '다음 주 재확인'}
        self.assertEqual((await self.client.put(url, json=body)).status_code, 200)
        self.assertEqual((await self.client.put(url, json=body)).status_code, 409)
        items = (await self.client.get('/tasks?month=2026-09')).json()['items']
        self.assertEqual(items[0]['result']['content'], body['content'])
        res = await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': doc['version']})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['snapshot']['tasks'][0]['result']['content'], body['content'])
        self.assertNotIn('missing_result', [w['code'] for w in res.json()['snapshot']['warnings']])
        self.assertEqual((await M.get_pm_issues_collection().find_one({'_id': self.iid}))['status'], 'DONE')

    async def test_finalization_allows_optional_notes_and_freezes_everything(self):
        doc = await self.create()
        self.assertTrue(doc['snapshot']['warnings'])
        self.assertEqual(doc['limitations'], '')
        res = await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})
        self.assertEqual(res.status_code, 200); final = res.json()
        self.assertEqual(final['limitations'], '')
        self.assertEqual(final['snapshot']['warnings'], doc['snapshot']['warnings'])
        await M.get_db()[M.HEALTH_REPORTS].delete_many({})
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'status': 'TODO', 'title': '변경'}})
        await M.get_assets_servers_collection().delete_many({})
        await self.client.put(f'/tasks/{self.iid}/2026-09/result', json={'version': 0, 'content': '나중 결과'})
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(fetched['snapshot'], final['snapshot'])
        self.assertEqual(fetched['snapshot']['tasks'][0]['issue']['title'], 'git migration')
        self.assertEqual((await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': final['version']})).status_code, 409)
        revs = await asyncio.gather(*(self.client.post('/reports/' + doc['id'] + '/revisions') for _ in range(3)))
        self.assertTrue(all(r.status_code == 201 for r in revs))
        self.assertEqual(len({r.json()['id'] for r in revs}), 1)
        self.assertEqual(revs[0].json()['revision'], 2)
        self.assertEqual(revs[0].json()['state'], 'DRAFT')

    async def test_manual_notes_survive_refresh_and_can_be_cleared_before_finalization(self):
        doc = await self.create()
        doc = await self.edit(doc, limitations='다음 정기 점검 전 UPS 배터리 교체 일정 확인')
        preview = await self.preview(report_id=doc['id'], version=doc['version'])
        refreshed = await self.client.post('/reports/' + doc['id'] + '/refresh', json={
            'version': doc['version'], 'preview_id': preview['id']})
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(refreshed.json()['limitations'], doc['limitations'])
        cleared = await self.edit(refreshed.json(), limitations='')
        final = await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': cleared['version']})
        self.assertEqual(final.status_code, 200, final.text)
        self.assertEqual(final.json()['limitations'], '')

    async def test_work_plan_references_refresh_and_freeze_without_copying_document_body(self):
        tid, eid = ObjectId(), ObjectId()
        await M.get_form_templates_collection().insert_one({'_id': tid, 'menu': 'job', 'jira_issue_key': 'JOB-PLAN-SERVICE', 'title': '작업계획서(서비스)'})
        await M.get_form_entries_collection().insert_one({'_id': eid, 'template_id': str(tid), 'version': 1,
            'data': {'기본 정보': {'작업명': 'Git 이관 계획'}, '문서 본문': [{'내용': '원본 전체 내용'}]}})
        self.user.permissions.append('job')
        linked = await self.client.put(f'/tasks/{self.iid}/2026-09/work-plans', json={'work_plan_ids': [str(eid)], 'version': 0})
        self.assertEqual(linked.status_code, 200, linked.text)
        self.user.permissions.remove('job')  # Report visibility still follows server_check permission.
        doc = await self.create()
        saved = doc['snapshot']['tasks'][0]['work_plans'][0]
        self.assertEqual((saved['title'], saved['version']), ('Git 이관 계획', 1))
        self.assertNotIn('current', saved)
        self.assertNotIn('data', saved)
        await M.get_form_entries_collection().update_one({'_id': eid}, {'$set': {'data.기본 정보.작업명': '수정한 이관 계획', 'version': 2}})
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(fetched['snapshot']['tasks'][0]['work_plans'][0], saved)
        preview = await self.preview(report_id=doc['id'], version=doc['version'])
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': preview['id']})
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc['snapshot']['tasks'][0]['work_plans'][0]['version'], 2)
        doc = await self.edit(doc, limitations='결과는 점검 종료 후 확인')
        response = await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})
        self.assertEqual(response.status_code, 200, response.text)
        final = response.json()
        await M.get_form_entries_collection().delete_one({'_id': eid})
        await tasks.collection().update_one({'_id': self.iid}, {'$set': {'occurrences.0.work_plans': []}})
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(fetched['snapshot'], final['snapshot'])
        self.assertEqual(fetched['snapshot']['tasks'][0]['work_plans'][0]['title'], '수정한 이관 계획')

    async def test_refresh_exact_preview_preserves_manual_content_and_rejects_conflicts(self):
        doc = await self.create()
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        edited = await self.edit(doc, overview='수기로 작성한 의견')
        res = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})
        self.assertEqual(res.status_code, 409)
        p = await self.preview(report_id=doc['id'], version=edited['version'])
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'servers.0.cpu.after_pct': '99%'}})
        res = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': edited['version'], 'preview_id': p['id']})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['overview'], '수기로 작성한 의견')
        self.assertEqual(res.json()['snapshot']['servers'][0]['cpu']['value'], 0)
        retry = await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': edited['version'], 'preview_id': p['id']})
        self.assertEqual(retry.json()['version'], res.json()['version'])

    async def test_counts_multi_asset_rolled_excluded_and_older_pending(self):
        for number, state, status, month in [(24, 'ACTIVE', 'IMPLEMENTED', '2026-09'), (25, 'ROLLED', 'TODO', '2026-09'), (26, 'EXCLUDED', 'TODO', '2026-09'), (27, 'ACTIVE', 'TODO', '2026-08')]:
            issue = {**self.issue, '_id': ObjectId(), 'number': number, 'status': status}
            await M.get_pm_issues_collection().insert_one(issue)
            await tasks.register(issue, month, await tasks.resolve_assets([str(self.aid)]), False, self.user)
            await tasks.collection().update_one({'_id': issue['_id']}, {'$set': {'occurrences.0.state': state}})
        p = await self.preview(); s = p['snapshot']['stats']
        self.assertEqual((s['planned'], s['done'], s['pending'], s['rolled'], s['excluded'], s['completion_rate']), (4, 1, 1, 1, 1, 33))
        self.assertEqual(len(p['snapshot']['carryover']), 1)

    async def test_duplicate_host_actions_preserved_separately_and_images_optional(self):
        duplicate = deepcopy(self.source['servers'][0]); duplicate['ip'] = '192.0.2.2'
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$push': {'servers': duplicate}})
        await M.get_db()[M.HEALTH_ACTIONS].insert_one({'report_id': str(self.sid), 'host_name': 'web-01', 'memo': '조치', 'images': ['data:image/png;base64,AAAA', 'data:image/svg+xml;base64,AAAA']})
        p = await self.preview(include_images=True)
        self.assertEqual(len(p['snapshot']['unmatched_actions']), 1)
        self.assertEqual(len(p['snapshot']['unmatched_actions'][0]['images']), 1)
        self.assertTrue(all(r['action'] is None for r in p['snapshot']['servers']))
        p = await self.preview(include_images=False)
        self.assertEqual(p['snapshot']['unmatched_actions'][0]['images'], [])

    async def save_participants(self, doc, people):
        return await self.client.put('/reports/' + doc['id'] + '/participants', json={'version': doc['version'], 'participants': people})

    def participant(self, **values):
        return {'user_id': str(self.uid), 'roles': ['RESOURCE_CHECK', 'WORK_EXECUTION'],
                'work_summary': 'CPU·메모리 확인 후 저장소 이전 및 서비스 동작을 검증했습니다.',
                'issue_ids': [str(self.iid)], **values}

    async def test_participant_search_minimal_fields_and_literal_query(self):
        other_id = ObjectId()
        await M.get_users_collection().insert_many([
            {'_id': other_id, 'full_name': '김협업', 'email': 'helper@example.com', 'team': '데이터활용팀', 'hashed_password': 'never-expose', 'permissions': []},
            {'full_name': '차단 사용자', 'email': 'blocked@example.com', 'is_blocked': True},
            {'full_name': '삭제 사용자', 'email': 'deleted@example.com', 'is_deleted': True},
        ])
        await M.get_pending_users_collection().insert_one({'full_name': '승인 대기', 'email': 'pending@example.com'})
        response = await self.client.get('/reports/participant-options?q=활용팀')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['users'][0], {'id': str(other_id), 'name': '김협업', 'email': 'helper@example.com', 'team': '데이터활용팀'})
        self.assertEqual({r['value'] for r in data['roles']}, set(svc.PARTICIPANT_ROLES))
        self.assertEqual((await self.client.get('/reports/participant-options?q=.*')).json()['users'], [])
        users = (await self.client.get('/reports/participant-options')).json()['users']
        self.assertEqual(len(users), 2)

    async def test_participants_use_canonical_identity_and_explicit_task_links(self):
        other_id = ObjectId()
        await M.get_users_collection().insert_one({'_id': other_id, 'full_name': '박검토', 'team': '데이터운영팀', 'permissions': []})
        doc = await self.create()
        res = await self.save_participants(doc, [self.participant(name='위조 이름', team='위조 팀'),
            self.participant(user_id=str(other_id), roles=['REVIEW'], issue_ids=[], work_summary='점검 결과를 검토했습니다.')])
        self.assertEqual(res.status_code, 200, res.text)
        people = res.json()['participants']
        self.assertEqual(people[0]['name'], '점검자')
        self.assertEqual(people[0]['roles'][0], {'value': 'RESOURCE_CHECK', 'label': '서버·자원 점검'})
        self.assertEqual(people[0]['tasks'], [{'issue_id': str(self.iid), 'month': '2026-09', 'key': 'TEST-23', 'title': 'git migration'}])
        self.assertEqual(people[1]['name'], '박검토')
        self.assertEqual(people[1]['team'], '데이터운영팀')
        self.assertEqual((await M.get_pm_issues_collection().find_one({'_id': self.iid}))['assignee_id'], self.uid)
        self.assertEqual(await M.get_pm_project_members_collection().count_documents({'user_id': other_id}), 0)

    async def test_assigned_work_needs_no_manual_link_and_does_not_overwrite_prose(self):
        other_id = ObjectId()
        await M.get_users_collection().insert_one({'_id': other_id, 'full_name': '점검자'})
        doc = await self.create()
        response = await self.save_participants(doc, [
            self.participant(issue_ids=[], assigned_tasks=[{'issue_id': 'forged'}]),
            self.participant(user_id=str(other_id), issue_ids=[]),
        ])
        self.assertEqual(response.status_code, 200, response.text)
        people = response.json()['participants']
        self.assertEqual(people[0]['tasks'], [])
        self.assertEqual(people[0]['assigned_tasks'], [{
            'issue_id': str(self.iid), 'month': '2026-09', 'key': 'TEST-23', 'title': 'git migration',
        }])
        self.assertEqual(people[0]['work_summary'], self.participant()['work_summary'])
        self.assertEqual(people[1]['assigned_tasks'], [])
        stored = await M.get_db()[svc.REPORTS].find_one({'_id': ObjectId(doc['id'])})
        self.assertEqual(stored['participants'], people)

    async def test_refresh_moves_assigned_work_but_preserves_manual_participation(self):
        other_id = ObjectId()
        await M.get_users_collection().insert_one({'_id': other_id, 'full_name': '새 담당자'})
        doc = (await self.save_participants(await self.create(), [
            self.participant(), self.participant(user_id=str(other_id), issue_ids=[], work_summary='추가 작업'),
        ])).json()
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {
            'assignee_id': other_id, 'title': '담당자가 바뀐 작업',
        }})
        before_refresh = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(before_refresh['participants'], doc['participants'])
        preview = await self.preview(report_id=doc['id'], version=doc['version'])
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={
            'version': doc['version'], 'preview_id': preview['id'],
        })
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc['participants'][0]['assigned_tasks'], [])
        self.assertEqual(doc['participants'][0]['tasks'][0]['issue_id'], str(self.iid))
        self.assertEqual(doc['participants'][0]['work_summary'], self.participant()['work_summary'])
        self.assertEqual(doc['participants'][1]['assigned_tasks'][0]['title'], '담당자가 바뀐 작업')
        # Removing the task from captured sources clears only automatic assignments.
        await tasks.collection().delete_one({'_id': self.iid})
        preview = await self.preview(report_id=doc['id'], version=doc['version'])
        response = await self.client.post('/reports/' + doc['id'] + '/refresh', json={
            'version': doc['version'], 'preview_id': preview['id'],
        })
        self.assertEqual(response.status_code, 200, response.text)
        people = response.json()['participants']
        self.assertTrue(all(not p['assigned_tasks'] for p in people))
        self.assertEqual(people[0]['tasks'][0]['issue_id'], str(self.iid))

    async def test_legacy_draft_derives_assignments_and_final_keeps_captured_work(self):
        doc = (await self.save_participants(await self.create(), [self.participant(issue_ids=[])])).json()
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {
            '$unset': {'participants.0.assigned_tasks': ''},
        })
        legacy = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(legacy['version'], doc['version'])
        self.assertEqual(legacy['participants'][0]['assigned_tasks'][0]['issue_id'], str(self.iid))
        # A legacy FINAL must not be enriched or changed when read.
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {'$set': {'state': 'FINAL'}})
        self.assertNotIn('assigned_tasks', (await self.client.get('/reports/' + doc['id'])).json()['participants'][0])
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {'$set': {'state': 'DRAFT'}})
        doc = await self.edit(legacy, limitations='자료 누락은 후속 점검')
        final = (await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})).json()
        captured = deepcopy(final['participants'])
        await M.get_pm_issues_collection().update_one({'_id': self.iid}, {'$set': {'assignee_id': None, 'title': '바뀐 작업'}})
        await M.get_users_collection().delete_one({'_id': self.uid})
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['participants'], captured)
        revision = (await self.client.post('/reports/' + doc['id'] + '/revisions')).json()
        self.assertEqual(revision['participants'], captured)

    async def test_participant_validation_is_atomic(self):
        doc = await self.create()
        blocked_id = ObjectId()
        await M.get_users_collection().insert_one({'_id': blocked_id, 'full_name': '차단', 'is_blocked': True})
        invalid = [
            [self.participant(), self.participant(user_id=str(self.uid).upper())],
            [self.participant(roles=[])], [self.participant(roles=['INVALID'])],
            [self.participant(roles=['LEAD', 'LEAD'])],
            [self.participant(user_id=str(ObjectId()))], [self.participant(user_id=str(blocked_id))],
            [self.participant(issue_ids=[str(ObjectId())])],
            [self.participant(issue_ids=[str(self.iid), str(self.iid).upper()])],
            [self.participant(work_summary='x' * 5001)],
        ]
        for people in invalid:
            res = await self.save_participants(doc, people)
            self.assertEqual(res.status_code, 422, res.text)
        saved = await svc.get_report(doc['id'], self.user)
        self.assertEqual(saved['version'], doc['version'])
        self.assertEqual(saved['participants'], [])

    async def test_participants_survive_refresh_edit_and_result_sync(self):
        doc = await self.create()
        doc = (await self.save_participants(doc, [self.participant()])).json()
        people = deepcopy(doc['participants'])
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        doc = (await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})).json()
        self.assertEqual(doc['participants'], people)
        doc = await self.edit(doc, overview='종합 의견 수정')
        self.assertEqual(doc['participants'], people)
        res = await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': doc['version']})
        self.assertEqual(res.json()['participants'], people)

    async def test_final_participant_history_survives_user_changes_and_revision(self):
        doc = await self.create()
        doc = (await self.save_participants(doc, [self.participant()])).json()
        doc = await self.edit(doc, limitations='자료 미확인 항목은 후속 점검합니다.')
        final = (await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})).json()
        await M.get_users_collection().update_one({'_id': self.uid}, {'$set': {'full_name': '바뀐 이름', 'team': '바뀐 팀'}})
        self.assertEqual((await self.save_participants(final, [])).status_code, 409)
        revision = (await self.client.post('/reports/' + doc['id'] + '/revisions')).json()
        self.assertEqual(revision['participants'], final['participants'])
        res = await self.save_participants(revision, [self.participant(roles=['LEAD'], work_summary='개정본 업무 수정')])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['participants'][0]['name'], '점검자')
        await M.get_users_collection().delete_one({'_id': self.uid})
        saved_final = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(saved_final['participants'], final['participants'])
        self.assertNotEqual(res.json()['participants'][0]['roles'], saved_final['participants'][0]['roles'])

    async def test_existing_deleted_participant_can_be_retained_or_removed(self):
        doc = await self.create()
        doc = (await self.save_participants(doc, [self.participant()])).json()
        await M.get_users_collection().delete_one({'_id': self.uid})
        res = await self.save_participants(doc, [self.participant(work_summary='보존된 참여 기록 보완')])
        self.assertEqual(res.status_code, 200)
        doc = (await self.save_participants(res.json(), [])).json()
        self.assertEqual(doc['participants'], [])
        self.assertEqual((await self.save_participants(doc, [self.participant()])).status_code, 422)

    async def test_participant_permission_version_and_legacy_report(self):
        doc = await self.create()
        await M.get_db()[svc.REPORTS].update_one({'_id': ObjectId(doc['id'])}, {'$unset': {'participants': ''}})
        first = await self.save_participants(doc, [self.participant()])
        self.assertEqual(first.status_code, 200)
        self.assertEqual((await self.save_participants(doc, [])).status_code, 409)
        self.user = self.user.model_copy(update={'id': str(ObjectId())})
        self.assertEqual((await self.save_participants(first.json(), [])).status_code, 200)
        self.user = self.user.model_copy(update={'permissions': []})
        self.assertEqual((await self.client.get('/reports/participant-options')).status_code, 403)
        self.assertEqual((await self.save_participants(first.json(), [])).status_code, 403)

    async def test_previously_linked_work_survives_removal_from_refreshed_source(self):
        doc = await self.create()
        doc = (await self.save_participants(doc, [self.participant()])).json()
        await tasks.collection().delete_one({'_id': self.iid})
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        doc = (await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})).json()
        self.assertEqual(doc['snapshot']['tasks'], [])
        res = await self.save_participants(doc, [self.participant(work_summary='이전에 수행한 작업 기록')])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['participants'][0]['tasks'][0]['title'], 'git migration')

    async def test_plan_sourced_tasks_without_projects_support_reports_participants_and_shared_results(self):
        tid, eid = ObjectId(), ObjectId()
        await M.get_form_templates_collection().insert_one({'_id': tid, 'menu': 'Job', 'jira_issue_key': 'JOB-PLAN-SERVICE', 'title': '작업계획서'})
        await M.get_form_entries_collection().insert_one({'_id': eid, 'template_id': str(tid), 'version': 1,
            'data': {'기본 정보': {'작업명': '독립 계획 작업'}}, 'asset_ids': [str(self.aid)], 'linked_assets': []})
        self.user.permissions = ['server_check', 'job']
        await M.get_pm_project_members_collection().delete_many({})
        response = await self.client.post('/tasks/from-work-plan', json={'month': '2026-09', 'work_plan_id': str(eid),
            'asset_ids': [str(self.aid)], 'assignee_id': str(self.uid), 'planned_on': '2026-09-17'})
        self.assertEqual(response.status_code, 201, response.text)
        task_id = response.json()['issue_id']
        self.user.permissions = ['server_check']
        doc = await self.create(await self.preview(project_ids=[]))
        self.assertEqual(len(doc['snapshot']['tasks']), 1)
        row = doc['snapshot']['tasks'][0]
        self.assertEqual((row['source_type'], row['work_plan']['id']), ('WORK_PLAN', str(eid)))
        self.assertEqual((row['planned_start'], row['planned_end']), ('2026-09-17', '2026-09-17'))
        response = await self.save_participants(doc, [self.participant(issue_ids=[])])
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc['participants'][0]['assigned_tasks'][0]['issue_id'], task_id)
        response = await self.client.put(f"/reports/{doc['id']}/tasks/{task_id}/2026-09/result", json={
            'version': 0, 'content': '계획대로 완료', 'performed_on': '2026-09-17', 'follow_up': ''})
        self.assertEqual(response.status_code, 200, response.text)
        current = (await self.client.get('/tasks', params={'month': '2026-09', 'issue_id': task_id})).json()['items'][0]
        self.assertEqual(current['result']['content'], '계획대로 완료')
        doc = (await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': doc['version']})).json()
        self.assertEqual(doc['snapshot']['tasks'][0]['result']['content'], '계획대로 완료')
        final = (await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})).json()
        await M.get_form_entries_collection().update_one({'_id': eid}, {'$set': {'is_deleted': True, 'data.기본 정보.작업명': '변경된 제목'}})
        stored = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(stored['snapshot'], final['snapshot'])
        self.assertEqual(stored['participants'], final['participants'])
        self.assertEqual((await self.client.put(f"/reports/{doc['id']}/tasks/{task_id}/2026-09/result", json={
            'version': 1, 'content': '수정 금지'})).status_code, 409)

    async def save_notes(self, doc, notes):
        return await self.client.put('/reports/' + doc['id'] + '/notes', json={'version': doc['version'], 'notes': notes})

    async def test_additional_notes_add_edit_delete_preserve_other_report_content(self):
        doc = await self.create()
        original_snapshot = deepcopy(doc['snapshot'])
        await M.get_pm_project_members_collection().delete_many({})
        notes = [{'id': 'first', 'content': '첫 번째 확인 사항\n담당자 확인 필요'},
                 {'id': 'second', 'content': '<script>plain text</script>'}]
        response = await self.save_notes(doc, notes)
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc['additional_notes'], notes)
        notes[0]['content'] = '첫 번째 항목 수정'
        doc = (await self.save_notes(doc, notes)).json()
        self.assertEqual(doc['additional_notes'], notes)
        doc = (await self.save_notes(doc, [notes[1]])).json()
        self.assertEqual(doc['additional_notes'], [notes[1]])
        self.assertEqual(doc['snapshot'], original_snapshot)
        doc = (await self.save_notes(doc, [])).json()
        self.assertEqual(doc['additional_notes'], [])
        self.assertEqual(doc['limitations'], '')
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(fetched['additional_notes'], [])

    async def test_legacy_notes_are_one_item_and_reads_do_not_rewrite_stored_reports(self):
        doc = await self.create()
        col = M.get_db()[svc.REPORTS]
        legacy_text = '기존 내용\n\n여러 문단도 하나의 항목으로 보존'
        await col.update_one({'_id': ObjectId(doc['id'])}, {'$set': {'limitations': legacy_text}, '$unset': {'additional_notes': ''}})
        stored = await col.find_one({'_id': ObjectId(doc['id'])})
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        legacy = {'id': 'legacy', 'content': legacy_text}
        self.assertEqual(fetched['additional_notes'], [legacy])
        self.assertEqual(await col.find_one({'_id': ObjectId(doc['id'])}), stored)
        response = await self.save_notes(fetched, [legacy, {'id': 'new-item', 'content': '새 항목'}])
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(updated['additional_notes'][0], legacy)
        self.assertEqual(updated['limitations'], '')
        # Old report editors cannot flatten the list or accidentally delete it.
        body = {k: updated[k] for k in ('title', 'inspection_date', 'purpose', 'overview', 'include_appendix')}
        response = await self.client.patch('/reports/' + doc['id'], json={**body, 'version': updated['version'], 'overview': '제목 외 편집'})
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(len(updated['additional_notes']), 2)
        self.assertEqual((await self.client.patch('/reports/' + doc['id'], json={**body, 'version': updated['version'], 'limitations': '목록 덮어쓰기'})).status_code, 409)
        updated = await self.edit(updated, overview='구형 클라이언트에서 종합 의견 수정')
        self.assertEqual(len(updated['additional_notes']), 2)
        updated = (await self.save_notes(updated, [])).json()
        self.assertEqual((await self.client.get('/reports/' + updated['id'])).json()['additional_notes'], [])

    async def test_additional_notes_conflicts_do_not_lose_other_writers_items(self):
        doc = await self.create()
        doc = (await self.save_notes(doc, [{'id': 'first', 'content': '기존 항목'}])).json()
        responses = await asyncio.gather(
            self.save_notes(doc, []), self.save_notes(doc, [{'id': 'first', 'content': '다른 작성자의 수정'}]))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        winner = next(r.json() for r in responses if r.status_code == 200)
        fetched = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(fetched['additional_notes'], winner['additional_notes'])
        self.assertEqual((await self.save_notes(doc, [{'id': 'stale', 'content': '오래된 화면'}])).status_code, 409)

    async def test_additional_notes_validate_content_ids_limits_and_permission(self):
        doc = await self.create()
        invalid = [[{'id': 'x', 'content': '   '}], [{'id': 'x', 'content': 'x' * 5001}],
                   [{'id': '', 'content': '내용'}], [{'id': 'x', 'content': 'a'}, {'id': 'x', 'content': 'b'}],
                   [{'id': str(i), 'content': '항목'} for i in range(101)]]
        for notes in invalid:
            self.assertEqual((await self.save_notes(doc, notes)).status_code, 422)
        self.assertEqual((await self.client.get('/reports/' + doc['id'])).json()['version'], doc['version'])
        self.user.permissions = []
        self.assertEqual((await self.save_notes(doc, [{'id': 'x', 'content': '내용'}])).status_code, 403)
        self.user.permissions = ['server_check']
        response = await self.save_notes(doc, [{'id': 'x', 'content': '  내용  '}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['additional_notes'][0]['content'], '내용')

    async def test_additional_notes_survive_refresh_result_sync_and_frozen_revision(self):
        doc = await self.create()
        notes = [{'id': 'one', 'content': 'UPS 일정 확인'}, {'id': 'two', 'content': '배치 로그 확인'}]
        doc = (await self.save_notes(doc, notes)).json()
        p = await self.preview(report_id=doc['id'], version=doc['version'])
        doc = (await self.client.post('/reports/' + doc['id'] + '/refresh', json={'version': doc['version'], 'preview_id': p['id']})).json()
        self.assertEqual(doc['additional_notes'], notes)
        doc = (await self.client.post('/reports/' + doc['id'] + '/sync-results', json={'version': doc['version']})).json()
        self.assertEqual(doc['additional_notes'], notes)
        final = (await self.client.post('/reports/' + doc['id'] + '/finalize', json={'version': doc['version']})).json()
        self.assertEqual((await self.save_notes(final, [])).status_code, 409)
        revision = (await self.client.post('/reports/' + doc['id'] + '/revisions')).json()
        self.assertEqual(revision['additional_notes'], notes)
        self.assertEqual((await self.save_notes(revision, [notes[0]])).status_code, 200)
        self.assertEqual((await self.client.get('/reports/' + final['id'])).json()['additional_notes'], notes)

    async def test_legacy_final_notes_keep_original_text_and_allow_revision_edit(self):
        doc = await self.create()
        col = M.get_db()[svc.REPORTS]
        await col.update_one({'_id': ObjectId(doc['id'])}, {'$set': {'state': 'FINAL', 'limitations': '확정 당시 내용'}, '$unset': {'additional_notes': ''}})
        original = await col.find_one({'_id': ObjectId(doc['id'])})
        final = (await self.client.get('/reports/' + doc['id'])).json()
        self.assertEqual(final['additional_notes'], [{'id': 'legacy', 'content': '확정 당시 내용'}])
        self.assertEqual((await self.save_notes(final, [])).status_code, 409)
        revision = (await self.client.post('/reports/' + doc['id'] + '/revisions')).json()
        self.assertEqual((await self.save_notes(revision, [])).status_code, 200)
        self.assertEqual(await col.find_one({'_id': ObjectId(doc['id'])}), original)
