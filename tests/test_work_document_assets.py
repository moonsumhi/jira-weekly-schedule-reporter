"""Run with WORK_DOCUMENT_TEST_MONGO=1; every collection has a disposable UUID prefix."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.form_entries import router
from app.services import work_documents


class PrefixDB:
    def __init__(self, db):
        self.db, self.prefix, self.names = db, 'test_work_assets_' + uuid4().hex + '_', set()

    def __getitem__(self, name):
        self.names.add(name)
        return self.db[self.prefix + name]

    async def cleanup(self):
        for name in self.names:
            await self.db.drop_collection(self.prefix + name)


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Requires explicit isolated MongoDB test run')
class WorkDocumentAssetsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = PrefixDB(M.get_db())
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.file_patch = patch.object(work_documents, 'UPLOAD_ROOT', Path(self.tmp.name))
        self.file_patch.start()
        self.uid, self.tid, self.aid, self.bid = [ObjectId() for _ in range(4)]
        self.user = UserPublic(id=str(self.uid), email='work-assets@example.com', full_name='작업자', permissions=['job', 'asset'])
        await M.get_form_templates_collection().insert_one({'_id': self.tid, 'menu': 'Job', 'title': '작업계획서(서비스)', 'is_deleted': False})
        await M.get_assets_servers_collection().insert_many([
            {'_id': self.aid, 'name': 'web-01', 'ip': '192.0.2.1', 'fields': {'자산유형': '서버', '서버명': '포털'}},
            {'_id': self.bid, 'name': 'web-02', 'ip': '192.0.2.2', 'fields': {}},
        ])
        self.data = {'기본 정보': {'작업명': 'git migration', '작업 기간 (시작)': '2026-09-17T09:00'},
                     '문서 본문': [{'제목': 'git migration', '내용': '# 기존 문서\n\n본문 보존', '내용__format': 'markdown'}]}
        app = FastAPI()
        app.include_router(router, prefix='/form-entries')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.cleanup()
        self.db_patch.stop()
        self.file_patch.stop()
        self.tmp.cleanup()
        M.get_client().close()
        M._client = None

    async def create(self, **values):
        response = await self.client.post('/form-entries', json={
            'template_id': str(self.tid), 'data': self.data, 'asset_ids': [str(self.aid), str(self.bid)], **values,
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def history(self, asset_id=None, **params):
        response = await self.client.get(f'/form-entries/by-asset/{asset_id or self.aid}', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_create_reads_both_directions_without_changing_document(self):
        entry = await self.create()
        self.assertEqual(entry['data'], self.data)
        self.assertEqual([a['name'] for a in entry['linked_assets']], ['web-01', 'web-02'])
        for asset_id in (self.aid, self.bid):
            history = await self.history(asset_id)
            self.assertEqual(history['total'], 1)
            self.assertEqual(history['items'][0]['id'], entry['id'])
            self.assertEqual(history['items'][0]['title'], 'git migration')
            self.assertEqual(history['items'][0]['work_date'], '2026-09-17T09:00')
        get = await self.client.get('/form-entries/' + entry['id'])
        self.assertEqual(get.json()['linked_assets'], entry['linked_assets'])
        stored = await M.get_form_entries_collection().find_one({'_id': ObjectId(entry['id'])})
        self.assertNotIn('asset_ids', stored['data'])
        self.assertEqual(Path(stored['markdown_file']).read_text(), self.data['문서 본문'][0]['내용'])

    async def test_existing_document_link_unlink_and_delete(self):
        entry = await self.create(asset_ids=[])
        self.assertEqual((await self.history())['total'], 0)
        url = '/form-entries/' + entry['id']
        linked = await self.client.patch(url, json={'data': self.data, 'version': 1, 'asset_ids': [str(self.aid)]})
        self.assertEqual(linked.status_code, 200, linked.text)
        self.assertEqual((await self.history())['total'], 1)
        detached = await self.client.patch(url, json={'data': self.data, 'version': 2, 'asset_ids': []})
        self.assertEqual(detached.json()['linked_assets'], [])
        self.assertEqual((await self.history())['total'], 0)
        await self.client.patch(url, json={'data': self.data, 'version': 3, 'asset_ids': [str(self.aid)]})
        self.assertEqual((await self.client.delete(url)).status_code, 204)
        self.assertEqual((await self.history())['total'], 0)

    async def test_legacy_patch_does_not_clear_links_and_reads_current_asset_names(self):
        entry = await self.create()
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'renamed-web'}})
        response = await self.client.patch('/form-entries/' + entry['id'], json={'data': self.data, 'version': 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['linked_assets'][0]['name'], 'renamed-web')
        listed = await self.client.get('/form-entries', params={'template_id': str(self.tid)})
        self.assertEqual(listed.json()[0]['linked_assets'][0]['name'], 'renamed-web')
        self.assertEqual((await self.history())['total'], 1)

    async def test_deleted_asset_keeps_existing_history_but_cannot_be_added(self):
        entry = await self.create()
        await M.get_assets_servers_collection().delete_one({'_id': self.aid})
        response = await self.client.get('/form-entries/' + entry['id'])
        self.assertEqual(response.json()['linked_assets'][0]['name'], 'web-01')
        self.assertTrue(response.json()['linked_assets'][0]['is_deleted'])
        response = await self.client.patch('/form-entries/' + entry['id'], json={'data': self.data, 'version': 1, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.history())['total'], 1)
        rejected = await self.client.post('/form-entries', json={'template_id': str(self.tid), 'data': self.data, 'asset_ids': [str(self.aid)]})
        self.assertEqual(rejected.status_code, 422)

    async def test_stale_version_is_atomic_and_duplicate_ids_are_rejected(self):
        entry = await self.create()
        response = await self.client.patch('/form-entries/' + entry['id'], json={'data': {'wrong': {}}, 'version': 0, 'asset_ids': []})
        self.assertEqual(response.status_code, 409)
        saved = (await self.client.get('/form-entries/' + entry['id'])).json()
        self.assertEqual(saved['data'], self.data)
        self.assertEqual(len(saved['linked_assets']), 2)
        for ids in ([str(self.aid)] * 2, ['invalid'], [str(ObjectId())]):
            response = await self.client.post('/form-entries', json={'template_id': str(self.tid), 'data': self.data, 'asset_ids': ids})
            self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.history())['total'], 1)

    async def test_permission_and_template_scope(self):
        entry = await self.create()
        self.user.permissions = ['asset']
        for url in ('/form-entries/asset-options', f'/form-entries/by-asset/{self.aid}'):
            self.assertEqual((await self.client.get(url)).status_code, 403)
        response = await self.client.post('/form-entries', json={'template_id': str(self.tid), 'data': self.data, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 403)
        response = await self.client.patch('/form-entries/' + entry['id'], json={'data': self.data, 'version': 1, 'asset_ids': []})
        self.assertEqual(response.status_code, 403)
        self.user.permissions = ['job']
        # A matching document title in another menu must not grant asset-link access.
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'menu': 'Jira'}})
        response = await self.client.post('/form-entries', json={'template_id': str(self.tid), 'data': self.data, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.history())['total'], 0)

    async def test_all_job_document_types_and_renamed_templates_can_link(self):
        expected = []
        for title, menu in [('작업계획서(서비스 외)', 'Job'), ('작업결과서', 'job'),
                            ('반입신청서', 'JOB'), ('새로운 운영 양식', 'JoB')]:
            template_id = ObjectId()
            await M.get_form_templates_collection().insert_one({'_id': template_id, 'menu': menu, 'title': title})
            entry = await self.create(template_id=str(template_id))
            self.assertEqual(entry['data'], self.data)
            expected.append(entry['id'])
            loaded = await self.client.get('/form-entries/' + entry['id'])
            self.assertEqual(len(loaded.json()['linked_assets']), 2)
        history = await self.history()
        self.assertEqual(history['total'], 4)
        self.assertEqual({item['id'] for item in history['items']}, set(expected))
        await M.get_form_templates_collection().update_one({'_id': template_id}, {'$set': {'title': '이름을 바꾼 양식'}})
        history = await self.history()
        self.assertIn('이름을 바꾼 양식', [item['template_title'] for item in history['items']])
        updated = await self.client.patch('/form-entries/' + entry['id'], json={
            'data': self.data, 'version': 1, 'asset_ids': [str(self.aid)]})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual((await self.history(self.bid))['total'], 3)

    async def test_intake_summary_original_file_and_link_changes(self):
        await M.get_form_templates_collection().update_one({'_id': self.tid}, {'$set': {'title': '반입신청서'}})
        data = {'신청자 정보': {'기관명': '테스트 기관', '신청일자': '2026.09.18'},
                '반입 파일 정보': {'처리 목적': '서버 이전 자료 반입', '내용 요약': '원문 유지'}}
        original = {'url': '/api/uploads/original.docx', 'original_name': '반입신청서.docx'}
        entry = await self.create(data=data, original_file=original)
        item = (await self.history())['items'][0]
        self.assertEqual(item['title'], '서버 이전 자료 반입')
        self.assertEqual(item['work_date'], '2026.09.18')
        self.assertEqual(item['date_label'], '신청일')
        result = await self.client.patch('/form-entries/' + entry['id'], json={
            'data': data, 'version': 1, 'asset_ids': []})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['data'], data)
        self.assertEqual(result.json()['original_file']['url'], original['url'])
        self.assertEqual((await self.history())['total'], 0)

    async def test_mixed_history_excludes_deleted_documents_and_templates(self):
        plan = await self.create()
        result_id, intake_id = ObjectId(), ObjectId()
        await M.get_form_templates_collection().insert_many([
            {'_id': result_id, 'title': '작업결과서', 'menu': 'Job'},
            {'_id': intake_id, 'title': '반입신청서', 'menu': 'Job'},
        ])
        result = await self.create(template_id=str(result_id))
        intake = await self.create(template_id=str(intake_id))
        first, second = await self.history(limit=2), await self.history(offset=2, limit=2)
        self.assertEqual(first['total'], 3)
        self.assertEqual([item['id'] for item in first['items'] + second['items']], [intake['id'], result['id'], plan['id']])
        await self.client.delete('/form-entries/' + result['id'])
        await M.get_form_templates_collection().update_one({'_id': intake_id}, {'$set': {'is_deleted': True}})
        history = await self.history()
        self.assertEqual(history['total'], 1)
        self.assertEqual(history['items'][0]['id'], plan['id'])
        rejected = await self.client.post('/form-entries', json={
            'template_id': str(intake_id), 'data': self.data, 'asset_ids': [str(self.aid)]})
        self.assertEqual(rejected.status_code, 422)

    async def test_asset_search_is_literal_and_excludes_deleted_assets(self):
        await M.get_assets_servers_collection().update_one({'_id': self.bid}, {'$set': {'is_deleted': True}})
        await M.get_asset_collection('네트워크').insert_one({'name': 'network', 'fields': {'자산유형': '네트워크'}})
        for term, expected in (('', 2), ('192.0.2.1', 1), ('포털', 1), ('.*', 0)):
            response = await self.client.get('/form-entries/asset-options', params={'search': term})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), expected)

    async def test_all_asset_categories_are_preserved_in_documents_and_history(self):
        targets = {'서버': str(self.aid)}
        for category in M.CATEGORY_COLLECTIONS:
            if category == '서버':
                continue
            identifier = ObjectId()
            targets[category] = str(identifier)
            await M.get_asset_collection(category).insert_one({
                '_id': identifier, 'name': f'{category}-문서', 'asset_no': f'DOC-{category}',
                'fields': {'장비명': f'{category} 문서 대상', '비밀': 'must not expose'}})
        for category, identifier in targets.items():
            response = await self.client.get('/form-entries/asset-options', params={'category': category})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(all(asset['category'] == category for asset in response.json()))
            self.assertIn(identifier, [asset['id'] for asset in response.json()])
        self.assertEqual((await self.client.get('/form-entries/asset-options', params={'category': 'invalid'})).status_code, 422)
        for title in ('작업계획서', '작업결과서', '반입신청서'):
            tid = ObjectId()
            await M.get_form_templates_collection().insert_one({'_id': tid, 'menu': 'Job', 'title': title})
            entry = await self.create(template_id=str(tid), asset_ids=list(targets.values()))
            self.assertEqual(entry['data'], self.data)
            self.assertEqual({asset['category']: asset['id'] for asset in entry['linked_assets']}, targets)
            self.assertNotIn('must not expose', str(entry))
            for identifier in targets.values():
                self.assertIn(entry['id'], [item['id'] for item in (await self.history(identifier))['items']])
        network_id = targets['네트워크']
        await M.get_asset_collection('네트워크').update_one({'_id': ObjectId(network_id)}, {'$set': {'name': '변경된 스위치'}})
        detail = (await self.client.get('/form-entries/' + entry['id'])).json()
        self.assertEqual(next(asset['name'] for asset in detail['linked_assets'] if asset['id'] == network_id), '변경된 스위치')
        await M.get_asset_collection('네트워크').delete_one({'_id': ObjectId(network_id)})
        response = await self.client.patch('/form-entries/' + entry['id'], json={
            'data': self.data, 'version': 1, 'asset_ids': [network_id]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['linked_assets'][0]['is_deleted'])
        self.assertEqual(response.json()['linked_assets'][0]['category'], '네트워크')
        rejected = await self.client.post('/form-entries', json={
            'template_id': str(self.tid), 'data': self.data, 'asset_ids': [network_id]})
        self.assertEqual(rejected.status_code, 422)

    async def test_ambiguous_asset_ids_are_rejected_before_document_creation(self):
        await M.get_asset_collection('네트워크').insert_one({'_id': self.aid, 'name': 'duplicate'})
        response = await self.client.post('/form-entries', json={
            'template_id': str(self.tid), 'data': self.data, 'asset_ids': [str(self.aid)]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(await M.get_form_entries_collection().count_documents({}), 0)

    async def test_history_pagination_has_no_duplicates(self):
        entry = await self.create()
        stored = await M.get_form_entries_collection().find_one({'_id': ObjectId(entry['id'])})
        await M.get_form_entries_collection().insert_many([{**stored, '_id': ObjectId()} for _ in range(22)])
        first, second = await self.history(limit=20), await self.history(offset=20, limit=20)
        self.assertEqual(first['total'], 23)
        ids = [item['id'] for item in first['items'] + second['items']]
        self.assertEqual(len(ids), 23)
        self.assertEqual(len(set(ids)), 23)
