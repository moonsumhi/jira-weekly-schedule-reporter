"""Import rollback exercises disposable, isolated MongoDB collections."""
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.assets import router
from app.routers.auth import get_current_user


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB tests only')
class AssetImportRollbackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        self.prefix = 'test_import_rollback_' + uuid4().hex + '_'
        self.names = set()
        parent = self

        class TestDB:
            def __getitem__(self, name):
                full = name if name.startswith(parent.prefix) else parent.prefix + name
                parent.names.add(full)
                return parent.real_db[full]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.user = UserPublic(id=str(ObjectId()), email='import-test@example.com', permissions=['asset'])
        app = FastAPI()
        app.include_router(router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def start(self):
        result = await self.client.post('/assets/imports', json={'filename': 'test.xlsx'})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['id']

    @staticmethod
    def mcp_body(**extra):
        return {'category': '서버', 'name': 'host-01', 'ip': '192.0.2.50', 'asset_no': 'A-100',
                'fields': {'구분': '운영', '서버명': '테스트 자산', '설명': '검증',
                           '운영체제': 'Rocky Linux', 'version': '9.4'}, **extra}

    async def test_mcp_schema_and_atomic_system_info_lifecycle_rollback(self):
        schema = (await self.client.get('/assets/mcp-schema')).json()
        self.assertIn('SystemInformation', schema['schema']['$defs'])
        body = self.mcp_body(system_info={'cpu': {'model': 'Test CPU', 'core_count': 16}, 'memory': {'total_gb': 64}})
        response = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        asset = result['asset']
        self.assertEqual(asset['system_info']['cpu']['coreCount'], 16)
        self.assertEqual(asset['fields']['eos_date'], '2024-11')
        self.assertEqual(asset['fields']['eol_date'], '2024-11')
        batch = result['batch_id']
        self.user.is_admin = True
        batches = (await self.client.get('/assets/imports')).json()
        self.assertEqual(batches[0]['source'], 'mcp')
        self.assertEqual(batches[0]['id'], batch)
        self.assertEqual((await self.rollback(batch)).json()['deleted'], 1)
        history = (await self.client.get('/assets/' + asset['id'] + '/history', params={'category': '서버'})).json()
        self.assertEqual({h['source'] for h in history}, {'mcp', 'import_rollback'})

    async def test_mcp_validation_errors_do_not_create_any_asset_or_batch(self):
        bad = self.mcp_body(fields={'구분': '운영'})
        response = await self.client.post('/assets/mcp-create', json=bad)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn('자산명', response.json()['detail']['missing'])
        bad_info = self.mcp_body(system_info={'cpu': {'core_count': -1}})
        self.assertEqual((await self.client.post('/assets/mcp-create', json=bad_info)).status_code, 422)
        self.assertEqual(await M.get_db()['asset_import_batches'].count_documents({}), 0)
        self.assertEqual(await M.get_asset_collection('서버').count_documents({}), 0)

    async def test_mcp_duplicate_ip_requires_confirmation_and_id_is_always_unique(self):
        first = self.mcp_body(asset_id='SRV-001')
        response = await self.client.post('/assets/mcp-create', json=first)
        self.assertEqual(response.status_code, 201, response.text)
        duplicate = await self.client.post('/assets/mcp-create', json=self.mcp_body(asset_id='SRV-002'))
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(duplicate.json()['detail']['code'], 'DUPLICATE_IP')
        self.assertEqual(len(duplicate.json()['detail']['candidates']), 1)
        confirmed = await self.client.post('/assets/mcp-create', json=self.mcp_body(asset_id='SRV-002', confirm_duplicate_ip=True))
        self.assertEqual(confirmed.status_code, 201, confirmed.text)
        duplicate_id = await self.client.post('/assets/mcp-create', json=self.mcp_body(asset_id='SRV-001', confirm_duplicate_ip=True))
        self.assertEqual(duplicate_id.status_code, 409, duplicate_id.text)
        self.assertEqual(duplicate_id.json()['detail']['code'], 'DUPLICATE_ASSET_ID')

    async def test_mcp_unverified_dates_and_unsupported_system_info(self):
        body = self.mcp_body(fields={'구분': '운영', '서버명': '테스트', '설명': '검증', '운영체제': '확인되지 않은 제품', 'version': '99'})
        response = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(response.status_code, 201, response.text)
        fields = response.json()['asset']['fields']
        self.assertEqual(fields['eos_action_status'], 'REVIEW_REQUIRED')
        self.assertEqual(fields['eol_status'], 'REVIEW_REQUIRED')
        invalid = {**body, 'category': '네트워크', 'system_info': {'cpu': {'model': 'x'}}}
        self.assertEqual((await self.client.post('/assets/mcp-create', json=invalid)).status_code, 422)

    async def test_mcp_rejects_lifecycle_values_that_disagree_with_evidence(self):
        body = self.mcp_body()
        body['fields']['eos_date'] = '2099-01'
        response = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()['detail']['field'], 'eos_date')
        self.assertEqual(await M.get_asset_collection('서버').count_documents({}), 0)

    async def test_manual_and_mcp_registration_share_lifecycle_result(self):
        body = self.mcp_body()
        manual = await self.client.post('/assets', params={'category': '서버', 'auto_lifecycle': 'true'},
                                        json={'ip': '192.0.2.51', 'name': body['name'], 'asset_no': body['asset_no'], 'fields': body['fields']})
        mcp = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(manual.status_code, 201, manual.text)
        self.assertEqual(mcp.status_code, 201, mcp.text)
        left, right = manual.json()['fields'], mcp.json()['asset']['fields']
        for key in ('eos_date', 'eos_action_status', 'eol_date', 'eol_status'):
            self.assertEqual(left[key], right[key], key)

    async def test_auto_lifecycle_is_opt_in_for_existing_imports(self):
        original = {'운영체제': 'Rocky Linux', 'version': '9.4', 'eos_date': '2099-01', 'eos_action_status': 'ACTIVE'}
        asset = await self.client.post('/assets', params={'category': '서버'},
                                       json={'ip': '', 'name': 'historical', 'fields': original})
        self.assertEqual(asset.status_code, 201, asset.text)
        self.assertEqual(asset.json()['fields']['eos_date'], '2099-01')

    async def create(self, name, batch=None, category='서버'):
        params = {'category': category}
        if batch:
            params['import_batch_id'] = batch
        response = await self.client.post('/assets', params=params, json={'name': name, 'ip': '', 'fields': {'비고': '원본'}})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def update(self, asset, batch=None, **body):
        params = {'category': '서버'}
        if batch:
            params['import_batch_id'] = batch
        response = await self.client.patch('/assets/' + asset['id'], params=params, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def finish(self, batch):
        response = await self.client.post(f'/assets/imports/{batch}/finish')
        self.assertEqual(response.status_code, 204, response.text)

    async def rollback(self, batch):
        self.user.is_admin = True
        return await self.client.post(f'/assets/imports/{batch}/rollback')

    async def test_restores_existing_and_soft_deletes_new_with_multiple_writes(self):
        existing = await self.create('기존')
        batch = await self.start()
        await self.update(existing, batch, fields={'비고': '변경'})
        await self.update(existing, batch, name='변경된 이름', fields={'비고': '다시 변경'})
        created = await self.create('신규', batch)
        await self.update(created, batch, fields={'비고': '추가 변경'})
        await self.finish(batch)
        response = await self.rollback(batch)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'restored': 1, 'deleted': 1, 'conflicts': []})
        current = (await self.client.get('/assets/' + existing['id'], params={'category': '서버'})).json()
        self.assertEqual(current['name'], '기존')
        self.assertEqual(current['fields']['비고'], '원본')
        self.assertGreater(current['version'], 3)
        deleted = (await self.client.get('/assets/' + created['id'], params={'category': '서버'})).json()
        self.assertTrue(deleted['is_deleted'])
        self.assertEqual((await self.rollback(batch)).status_code, 409)
        history = (await self.client.get('/assets/' + existing['id'] + '/history', params={'category': '서버'})).json()
        self.assertEqual(history[0]['action'], 'UPDATE')
        self.assertEqual(history[0]['source'], 'import_rollback')
        self.assertTrue(any(d['path'] == 'name' and d['after'] == '기존' for d in history[0]['diff']))

    async def test_later_changes_are_skipped_and_can_be_retried(self):
        a = await self.create('수정 자산')
        batch = await self.start()
        await self.update(a, batch, name='Import 이름')
        await self.update(a, name='다른 사용자의 변경')
        created = await self.create('새 자산', batch)
        await self.update(created, name='이후 변경')
        await self.finish(batch)
        result = (await self.rollback(batch)).json()
        self.assertEqual((result['restored'], result['deleted'], len(result['conflicts'])), (0, 0, 2))
        current = (await self.client.get('/assets/' + a['id'], params={'category': '서버'})).json()
        self.assertEqual(current['name'], '다른 사용자의 변경')
        self.assertEqual((await self.rollback(batch)).json()['restored'], 0)

    async def test_import_rejects_stale_version_without_overwriting_newer_edit(self):
        asset = await self.create('기존')
        batch = await self.start()
        await self.update(asset, name='다른 사용자 수정')
        response = await self.client.patch('/assets/' + asset['id'], params={'category': '서버', 'import_batch_id': batch},
                                           json={'name': '오래된 값', 'version': asset['version']})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.rollback(batch)).json()['restored'], 0)
        current = (await self.client.get('/assets/' + asset['id'], params={'category': '서버'})).json()
        self.assertEqual(current['name'], '다른 사용자 수정')

    async def test_import_will_not_absorb_intervening_edits_into_rollback(self):
        asset = await self.create('기존')
        batch = await self.start()
        await self.update(asset, batch, name='Import 첫 변경')
        newer = await self.update(asset, name='다른 사람의 변경')
        response = await self.client.patch('/assets/' + asset['id'], params={'category': '서버', 'import_batch_id': batch},
                                           json={'name': 'Import 두 번째 변경', 'version': newer['version']})
        self.assertEqual(response.status_code, 409, response.text)
        result = (await self.rollback(batch)).json()
        self.assertEqual(len(result['conflicts']), 1)
        self.assertEqual((await self.client.get('/assets/' + asset['id'], params={'category': '서버'})).json()['name'], '다른 사람의 변경')

    async def test_only_admin_can_list_and_rollback_and_batch_owner_controls_writes(self):
        batch = await self.start()
        self.assertEqual((await self.client.get('/assets/imports')).status_code, 403)
        self.assertEqual((await self.client.post(f'/assets/imports/{batch}/rollback')).status_code, 403)
        self.user.email = 'other@example.com'
        response = await self.client.post('/assets', params={'category': '서버', 'import_batch_id': batch}, json={'name': '금지', 'ip': '', 'fields': {}})
        self.assertEqual(response.status_code, 409)
        self.user.is_admin = True
        self.assertEqual((await self.client.get('/assets/imports')).status_code, 200)

    async def test_import_history_can_be_paged(self):
        created = [await self.start() for _ in range(3)]
        self.user.is_admin = True
        first = await self.client.get('/assets/imports', params={'skip': 0, 'limit': 2})
        second = await self.client.get('/assets/imports', params={'skip': 2, 'limit': 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        ids = [item['id'] for item in first.json() + second.json()]
        self.assertEqual(len(ids), 3)
        self.assertEqual(set(ids), set(created))

    async def test_in_flight_batch_and_previously_rolled_back_batch_are_rejected(self):
        batch = await self.start()
        col = M.get_db()['asset_import_batches']
        await col.update_one({'_id': ObjectId(batch)}, {'$set': {'active_requests': 1}})
        self.assertEqual((await self.rollback(batch)).status_code, 409)
        await col.update_one({'_id': ObjectId(batch)}, {'$set': {'active_requests': 0}})
        self.assertEqual((await self.rollback(batch)).status_code, 200)
        self.user.is_admin = False
        response = await self.client.post('/assets', params={'category': '서버', 'import_batch_id': batch}, json={'name': '금지', 'ip': '', 'fields': {}})
        self.assertEqual(response.status_code, 409)

    async def test_placement_makes_new_asset_a_conflict(self):
        batch = await self.start()
        asset = await self.create('배치된 자산', batch)
        await M.get_rack_placements_collection().insert_one({'asset_category': '서버', 'asset_ref_id': ObjectId(asset['id']), 'is_deleted': False})
        await self.finish(batch)
        result = (await self.rollback(batch)).json()
        self.assertEqual((result['deleted'], len(result['conflicts'])), (0, 1))
        current = await M.get_asset_collection('서버').find_one({'_id': ObjectId(asset['id'])})
        self.assertFalse(current['is_deleted'])

    async def test_new_asset_with_work_history_is_not_deleted(self):
        batch = await self.start()
        asset = await self.create('운영 이력이 있는 자산', batch)
        await M.get_asset_notes_collection().insert_one({'asset_id': asset['id'], 'is_deleted': False})
        await self.finish(batch)
        result = (await self.rollback(batch)).json()
        self.assertEqual((result['deleted'], len(result['conflicts'])), (0, 1))

    async def test_rollback_releases_asset_id_for_reimport_and_safe_trash_restore(self):
        col = M.get_asset_collection('서버')
        await col.create_index('asset_id', unique=True, partialFilterExpression={'asset_id': {'$type': 'string'}})
        batch = await self.start()
        response = await self.client.post('/assets', params={'category': '서버', 'import_batch_id': batch},
                                          json={'name': '오입력', 'ip': '', 'asset_id': 'A-001', 'fields': {}})
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        await self.finish(batch)
        self.assertEqual((await self.rollback(batch)).json()['deleted'], 1)
        stored = await col.find_one({'_id': ObjectId(created['id'])})
        self.assertNotIn('asset_id', stored)
        replacement = await self.client.post('/assets', params={'category': '서버'},
                                             json={'name': '정상', 'ip': '', 'asset_id': 'A-001', 'fields': {}})
        self.assertEqual(replacement.status_code, 201, replacement.text)
        restore = await self.client.post(f'/assets/{created["id"]}/restore', params={'category': '서버'})
        self.assertEqual(restore.status_code, 409, restore.text)

    async def test_batch_id_is_canonical_for_journal_and_rollback(self):
        batch = await self.start()
        created = await self.create('대문자 식별자', batch.upper())
        await self.finish(batch)
        result = (await self.rollback(batch)).json()
        self.assertEqual(result['deleted'], 1)
        stored = await M.get_asset_collection('서버').find_one({'_id': ObjectId(created['id'])})
        self.assertTrue(stored['is_deleted'])
