"""Real MongoDB tests; only UUID-prefixed disposable collections are touched."""
import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.asset_work_history import router
from app.services import inspection_service as inspections


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Requires explicit isolated MongoDB test run')
class AssetNoteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        real_db = M.get_db()
        prefix = 'test_asset_notes_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                self.names.add(prefix + name)
                return real_db[prefix + name]

        self.real_db = real_db
        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.aid, self.bid, self.tid, self.uid = [ObjectId() for _ in range(4)]
        self.user = UserPublic(id=str(self.uid), email='notes@example.com', full_name='작성자', permissions=['asset', 'job'])
        await M.get_assets_servers_collection().insert_many([
            {'_id': self.aid, 'name': 'web-01', 'fields': {'자산유형': '서버'}},
            {'_id': self.bid, 'name': 'web-02'},
        ])
        await M.get_form_templates_collection().insert_one({'_id': self.tid, 'menu': 'Job', 'title': '작업결과서'})
        await M.get_asset_notes_collection().create_index([('asset_id', 1), ('client_id', 1)], unique=True)
        app = FastAPI()
        app.include_router(router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.url = f'/assets/{self.aid}'

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    def values(self, **changes):
        return {'content': '  인증서 갱신 후 서비스 정상 확인\n추가 관찰 필요  ', 'occurred_on': '2026-09-16',
                'client_id': uuid4().hex, **changes}

    async def create(self, **changes):
        response = await self.client.post(self.url + '/notes', json=self.values(**changes))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def history(self, **params):
        response = await self.client.get(self.url + '/work-history', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def inspection_issue(self, *, member=True):
        pid = ObjectId()
        await M.get_pm_projects_collection().insert_one({'_id': pid, 'key': 'OPS'})
        if member:
            await M.get_pm_project_members_collection().insert_one({'user_id': self.uid, 'project_id': pid})
        issue = {'_id': ObjectId(), 'project_id': pid, 'number': 1, 'title': '인증서 확인', 'status': 'TODO'}
        await M.get_pm_issues_collection().insert_one(issue)
        return issue

    async def link_inspection(self, issue, month, asset_id=None, *, common=False):
        assets = [] if common else await inspections.resolve_assets([str(asset_id or self.aid)])
        await inspections.register(issue, month, assets, common, self.user)

    async def test_inspection_history_enforces_menu_membership_and_occurrence_targets(self):
        await self.create()
        issue = await self.inspection_issue()
        await self.link_inspection(issue, '2026-09')
        await self.link_inspection(issue, '2026-10', self.bid)
        await self.link_inspection(issue, '2026-11', common=True)
        private = await self.inspection_issue(member=False)
        await self.link_inspection(private, '2026-09')
        self.assertEqual((await self.history())['total'], 1)
        self.user.permissions = ['asset', 'server_check']
        history = await self.history()
        self.assertEqual(history['total'], 2)
        tasks = [item for item in history['items'] if item['type'] == 'inspection']
        self.assertEqual([(item['issue_id'], item['month']) for item in tasks], [(str(issue['_id']), '2026-09')])
        self.assertEqual(tasks[0]['id'], f"{issue['_id']}:2026-09")
        self.user.id = str(ObjectId())
        self.assertEqual((await self.history())['total'], 1)
        self.user.is_admin = True
        self.assertEqual((await self.history())['total'], 3)

    async def test_inspection_history_preserves_monthly_snapshots_and_deleted_references(self):
        self.user.permissions.append('server_check')
        issue = await self.inspection_issue()
        with patch.object(inspections, 'current_month', return_value='2026-09'):
            await self.link_inspection({**issue, 'status': 'DONE', 'title': '8월 완료 기록'}, '2026-08')
            await self.link_inspection(issue, '2026-07')
            await inspections.change_occurrence(str(issue['_id']), '2026-07', 'exclude', '작업 취소', self.user)
            await self.link_inspection(issue, '2026-09')
            await inspections.change_occurrence(str(issue['_id']), '2026-09', 'rollover', '검증 일정 변경', self.user)
            await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'renamed', 'is_deleted': True}})
            tasks = {item['month']: item for item in (await self.history())['items']}
            self.assertEqual(tasks['2026-08']['issue']['status'], 'DONE')
            self.assertEqual(tasks['2026-08']['issue']['title'], '8월 완료 기록')
            self.assertEqual(tasks['2026-09']['state'], 'ROLLED')
            self.assertEqual(tasks['2026-09']['to_month'], '2026-10')
            self.assertEqual(tasks['2026-09']['reason'], '검증 일정 변경')
            self.assertEqual(tasks['2026-10']['from_month'], '2026-09')
            self.assertEqual(tasks['2026-10']['issue']['status'], 'TODO')
            self.assertEqual(tasks['2026-07']['state'], 'EXCLUDED')
            self.assertEqual(tasks['2026-07']['reason'], '작업 취소')
            self.assertEqual(tasks['2026-08']['assets'][0]['name'], 'web-01')
            self.assertEqual(tasks['2026-08']['assets'][0]['current']['name'], 'renamed')
            self.assertTrue(tasks['2026-08']['assets'][0]['is_deleted'])
            monthly = await inspections.list_tasks(self.user, '2026-09', asset_id=str(self.aid), all_months=True)
            for task in monthly:
                self.assertEqual(tasks[task['month']]['issue'], task['issue'])
            await M.get_pm_issues_collection().delete_one({'_id': issue['_id']})
            deleted = (await self.history())['items']
            self.assertEqual(len(deleted), 4)
            self.assertTrue(all(item['issue_deleted'] for item in deleted))
            self.assertEqual(next(item for item in deleted if item['month'] == '2026-08')['issue']['status'], 'DONE')

    async def test_three_way_pagination_keeps_distinct_months_of_same_issue(self):
        self.user.permissions.append('server_check')
        note = await self.create()
        issue = await self.inspection_issue()
        for month in ('2026-07', '2026-08', '2026-09'):
            await self.link_inspection(issue, month)
        stamp = datetime(2026, 9, 16, tzinfo=timezone.utc)
        await M.get_asset_notes_collection().update_many({}, {'$set': {'created_at': stamp}})
        await inspections.collection().update_many({}, {'$set': {'occurrences.$[].created_at': stamp}})
        await M.get_form_entries_collection().insert_one({
            '_id': ObjectId(note['id']), 'template_id': str(self.tid), 'asset_ids': [str(self.aid)],
            'data': {}, 'created_at': stamp})
        all_items = (await self.history(limit=100))['items']
        pages = [await self.history(offset=offset, limit=2) for offset in (0, 2, 4, 6)]
        self.assertEqual([page['total'] for page in pages], [5] * 4)
        self.assertEqual([item for page in pages for item in page['items']], all_items)
        self.assertEqual(len({(item['type'], item['id']) for item in all_items}), 5)
        self.assertEqual([item['month'] for item in all_items if item['type'] == 'inspection'], ['2026-09', '2026-08', '2026-07'])
        self.user.permissions.remove('job')
        self.assertEqual((await self.history())['total'], 4)

    async def test_note_is_asset_local_and_preserves_plain_text(self):
        note = await self.create(content='  <script>literal text</script>\n두 번째 줄  ', created_by='위조')
        self.assertEqual(note['content'], '<script>literal text</script>\n두 번째 줄')
        self.assertEqual(note['created_by'], '작성자')
        self.assertEqual(note['occurred_on'], '2026-09-16')
        self.assertTrue(note['can_edit'])
        self.assertEqual(await M.get_form_entries_collection().count_documents({}), 0)
        history = await self.history()
        self.assertEqual(history['total'], 1)
        self.assertEqual(history['items'][0]['type'], 'note')
        self.assertEqual(history['items'][0]['id'], note['id'])
        other = await self.client.get(f'/assets/{self.bid}/work-history')
        self.assertEqual(other.json()['total'], 0)

    async def test_create_retry_is_idempotent_and_input_is_validated(self):
        values = self.values()
        responses = await asyncio.gather(*(self.client.post(self.url + '/notes', json=values) for _ in range(3)))
        self.assertEqual([r.status_code for r in responses], [201] * 3)
        self.assertEqual(len({r.json()['id'] for r in responses}), 1)
        changed = await self.client.post(self.url + '/notes', json={**values, 'content': '변경된 내용'})
        self.assertEqual(changed.status_code, 409)
        for invalid in ({'content': ' \n '}, {'content': 'a' * 5001}, {'occurred_on': '2026-02-30'}, {'client_id': 'bad'}):
            response = await self.client.post(self.url + '/notes', json=self.values(**invalid))
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.history())['total'], 1)

    async def test_edit_delete_use_versions_and_keep_author(self):
        note = await self.create()
        url = self.url + '/notes/' + note['id']
        body = {'content': '조치 완료', 'occurred_on': '2026-09-15', 'version': 1}
        response = await self.client.patch(url, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['version'], 2)
        self.assertEqual(response.json()['created_by'], note['created_by'])
        self.assertEqual((await self.client.patch(url, json={**body, 'content': '오래된 수정'})).status_code, 409)
        self.assertEqual((await self.client.request('DELETE', url, json={'version': 1})).status_code, 409)
        self.assertEqual((await self.history())['items'][0]['content'], '조치 완료')
        self.assertEqual((await self.client.request('DELETE', url, json={'version': 2})).status_code, 204)
        self.assertEqual((await self.history())['total'], 0)
        self.assertEqual((await self.client.get(url)).status_code, 404)
        stored = await M.get_asset_notes_collection().find_one({'_id': ObjectId(note['id'])})
        self.assertTrue(stored['is_deleted'])
        self.assertEqual(stored['content'], '조치 완료')

    async def test_access_ownership_asset_scope_and_admin(self):
        note = await self.create()
        url = self.url + '/notes/' + note['id']
        self.user.id = str(ObjectId())
        self.assertFalse((await self.client.get(url)).json()['can_edit'])
        self.assertEqual((await self.client.patch(url, json={'content': '다른 사람', 'occurred_on': '2026-09-16', 'version': 1})).status_code, 403)
        self.assertEqual((await self.client.request('DELETE', url, json={'version': 1})).status_code, 403)
        other_url = f'/assets/{self.bid}/notes/{note["id"]}'
        self.assertEqual((await self.client.get(other_url)).status_code, 404)
        self.user.permissions = ['job']
        for route in (url, self.url + '/work-history'):
            self.assertEqual((await self.client.get(route)).status_code, 403)
        self.assertEqual((await self.client.post(self.url + '/notes', json=self.values())).status_code, 403)
        self.user.is_admin = True
        response = await self.client.patch(url, json={'content': '관리자 수정', 'occurred_on': '2026-09-16', 'version': 1})
        self.assertEqual(response.status_code, 200, response.text)

    async def test_deleted_or_missing_asset_cannot_be_written(self):
        note = await self.create()
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        self.assertFalse((await self.history())['items'][0]['can_edit'])
        self.assertEqual((await self.client.post(self.url + '/notes', json=self.values())).status_code, 409)
        url = self.url + '/notes/' + note['id']
        self.assertEqual((await self.client.patch(url, json={'content': '수정', 'occurred_on': '2026-09-16', 'version': 1})).status_code, 409)
        self.assertEqual((await self.client.request('DELETE', url, json={'version': 1})).status_code, 409)
        self.assertEqual((await self.client.post(f'/assets/{ObjectId()}/notes', json=self.values())).status_code, 404)

    async def test_mixed_history_pagination_and_document_permission(self):
        stamp = datetime(2026, 9, 16, tzinfo=timezone.utc)
        notes = [await self.create(content=f'기록 {i}') for i in range(3)]
        await M.get_asset_notes_collection().update_many({}, {'$set': {'created_at': stamp}})
        await M.get_form_entries_collection().insert_many([
            {'_id': ObjectId(), 'template_id': str(self.tid), 'asset_ids': [str(self.aid)], 'data': {}, 'created_at': stamp},
            {'_id': ObjectId(notes[0]['id']), 'template_id': str(self.tid), 'asset_ids': [str(self.aid)], 'data': {}, 'created_at': stamp},
        ])
        all_items = (await self.history(limit=100))['items']
        pages = [await self.history(offset=offset, limit=2) for offset in (0, 2, 4)]
        self.assertEqual([page['total'] for page in pages], [5] * 3)
        self.assertEqual([item for page in pages for item in page['items']], all_items)
        self.assertEqual(len({(item['type'], item['id']) for item in all_items}), 5)
        self.user.permissions = ['asset']
        history = await self.history()
        self.assertEqual(history['total'], 3)
        self.assertTrue(all(item['type'] == 'note' for item in history['items']))
        self.user.permissions.append('job')
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'is_deleted': True}})
        self.assertEqual((await self.history())['total'], 3)
