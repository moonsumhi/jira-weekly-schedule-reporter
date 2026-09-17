"""Asset-backed recurring inspection targets, with isolated disposable MongoDB collections."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.inspection_resources import router, SETTING
from app.routers.monthly_inspection_reports import Preview
from app.services import monthly_inspection_reports as reports
from test_monthly_inspection_reports import PrefixDB


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Explicit disposable MongoDB tests only')
class ResourceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = PrefixDB(M.get_db())
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.aid, self.bid, self.sid = [ObjectId() for _ in range(3)]
        self.user = UserPublic(id=str(ObjectId()), email='resource-test@example.com', full_name='점검자', permissions=['server_check'])
        await M.get_assets_servers_collection().insert_many([
            {'_id': self.aid, 'name': 'WEB-01', 'ip': '192.0.2.1'},
            {'_id': self.bid, 'name': 'DB-01', 'ip': '192.0.2.2'}])
        self.source = {'_id': self.sid, 'report_date': '2026-09-17', 'report_title': '9월 자원',
                       'summary': [{'host_name': 'web-01', 'ip': '192.0.2.1', 'cpu': '0%', 'ram': '82%', 'disk_max': '95%'}]}
        await M.get_db()[M.HEALTH_REPORTS].insert_one(deepcopy(self.source))
        app = FastAPI(); app.include_router(router, prefix='/resources')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose(); await self.db.cleanup(); self.db_patch.stop()
        M.get_client().close(); M._client = None

    async def save(self, ids=None, version=0):
        response = await self.client.put('/resources/targets', json={'version': version, 'asset_ids': ids if ids is not None else [str(self.aid)]})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def month(self, month='2026-09'):
        response = await self.client.get('/resources', params={'month': month})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_empty_targets_do_not_import_uploaded_servers(self):
        data = await self.month()
        self.assertEqual(data['items'], [])
        self.assertEqual(len(data['other_records']), 1)
        self.assertEqual((await self.client.get('/resources/targets')).json(), {'version': 0, 'assets': []})

    async def test_targets_are_live_asset_references_and_survive_missing_month(self):
        await self.save([str(self.aid), str(self.bid)])
        config = await M.get_db()[M.APP_SETTINGS].find_one({'_id': SETTING})
        self.assertNotIn('assets', config)
        data = await self.month()
        self.assertEqual(data['items'][0]['records'][0]['cpu']['value'], 0)
        self.assertEqual(data['items'][0]['records'][0]['mapping_state'], 'automatic')
        self.assertEqual(data['items'][1]['records'], [])
        await M.get_assets_servers_collection().update_one({'_id': self.bid}, {'$set': {'name': 'DB-RENAMED', 'ip': '192.0.2.22'}})
        data = await self.month('2026-10')
        self.assertIsNone(data['source'])
        self.assertEqual(len(data['items']), 2)
        self.assertTrue(all(not i['records'] for i in data['items']))
        self.assertEqual(data['items'][1]['asset']['name'], 'DB-RENAMED')
        self.assertEqual(data['items'][1]['asset']['ip'], '192.0.2.22')

    async def test_target_save_detects_concurrent_changes(self):
        await self.save()
        for version in (0, 2):
            response = await self.client.put('/resources/targets', json={'version': version, 'asset_ids': []})
            self.assertEqual(response.status_code, 409)
        await self.save([str(self.bid)], 1)
        response = await self.client.put('/resources/targets', json={'version': 1, 'asset_ids': []})
        self.assertEqual(response.status_code, 409)
        self.assertEqual((await self.month())['items'][0]['asset']['id'], str(self.bid))

    async def test_rejects_duplicate_missing_deleted_targets(self):
        await M.get_assets_servers_collection().update_one({'_id': self.bid}, {'$set': {'is_deleted': True}})
        for ids in ([str(self.aid), str(self.aid)], [str(ObjectId())], [str(self.bid)]):
            response = await self.client.put('/resources/targets', json={'version': 0, 'asset_ids': ids})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.month())['version'], 0)

    async def test_target_removal_preserves_sources_and_frozen_reports(self):
        await self.save()
        row = (await self.month())['records'][0]
        frozen = {'_id': ObjectId(), 'state': 'FINAL', 'snapshot': {'servers': [row]}}
        await M.get_db()[reports.REPORTS].insert_one(deepcopy(frozen))
        await self.save([], 1)
        self.assertEqual((await self.month())['items'], [])
        self.assertEqual((await self.month())['other_records'][0]['asset']['id'], str(self.aid))
        self.assertEqual(await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid}), self.source)
        self.assertEqual(await M.get_db()[reports.REPORTS].find_one({'_id': frozen['_id']}), frozen)
        self.assertEqual(await M.get_db()[reports.MAPPINGS].count_documents({}), 0)

    async def test_asset_hostname_fix_is_shared_with_reports_and_next_month(self):
        await self.save()
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'outdated'}})
        data = await self.month()
        self.assertEqual(data['items'][0]['records'], [])
        self.assertEqual(data['other_records'][0]['candidate']['id'], str(self.aid))
        self.assertEqual(data['other_records'][0]['mapping_issue'], 'hostname_mismatch')
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'WEB-01'}})
        october = deepcopy(self.source); october.update(_id=ObjectId(), report_date='2026-10-15')
        await M.get_db()[M.HEALTH_REPORTS].insert_one(october)
        for month in ('2026-09', '2026-10'):
            data = await self.month(month)
            self.assertEqual(data['items'][0]['records'][0]['asset']['id'], str(self.aid))
            _, snapshot = await reports.snapshot(Preview(month=month))
            self.assertEqual(snapshot['servers'][0]['asset']['id'], str(self.aid))
        self.assertEqual(await M.get_db()[reports.MAPPINGS].count_documents({}), 0)

    async def test_reports_share_automatic_target_matching(self):
        await self.save()
        _, snapshot = await reports.snapshot(Preview(month='2026-09'))
        self.assertEqual(snapshot['servers'][0]['asset']['id'], str(self.aid))
        self.assertEqual(snapshot['servers'][0]['mapping_state'], 'automatic')

    async def test_preview_exception_is_request_only_and_never_changes_inventory_or_targets(self):
        await self.save([str(self.aid), str(self.bid)])
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'old-host'}})
        data = await self.month()
        row = data['other_records'][0]
        body = {'month': '2026-09', 'source_id': str(self.sid), 'mappings': [{'row_key': row['key'], 'asset_id': str(self.bid)}]}
        response = await self.client.post('/resources/preview', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['items'][1]['records'][0]['mapping_state'], 'manual')
        self.assertEqual(await self.month(), data)
        self.assertEqual((await M.get_assets_servers_collection().find_one({'_id': self.aid}))['name'], 'old-host')
        self.assertEqual(await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid}), self.source)
        self.assertEqual(await M.get_db()[reports.MAPPINGS].count_documents({}), 0)
        self.assertEqual(await M.get_db()[reports.PREVIEWS].count_documents({}), 0)
        for override in ({'month': '2026-10'}, {'source_id': ''}, {'mappings': body['mappings'] * 2}):
            response = await self.client.post('/resources/preview', json={**body, **override})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.put(f'/resources/{self.sid}/mappings', json=body)).status_code, 410)

    async def test_ip_match_without_hostname_only_suggests_asset_to_review(self):
        await self.save()
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'old-host'}})
        row = (await self.month())['records'][0]
        self.assertIsNone(row['asset']); self.assertEqual(row['candidate']['id'], str(self.aid))
        await M.get_assets_servers_collection().update_one({'_id': self.bid}, {'$set': {'ip': '192.0.2.1'}})
        row = (await self.month())['records'][0]
        self.assertIsNone(row['asset']); self.assertIsNone(row['candidate'])

    async def test_deleted_targets_stay_visible_until_removed(self):
        await self.save()
        await M.get_assets_servers_collection().delete_one({'_id': self.aid})
        data = await self.month()
        self.assertTrue(data['items'][0]['asset']['is_deleted'])
        self.assertEqual(data['items'][0]['records'], [])
        await self.save([], 1)

    async def test_latest_same_month_and_strict_previous_calendar_month(self):
        await self.save()
        july = deepcopy(self.source); july.update(_id=ObjectId(), report_date='2026-07-17')
        latest = deepcopy(self.source); latest.update(_id=ObjectId(), report_date='2026-09-20')
        await M.get_db()[M.HEALTH_REPORTS].insert_many([july, latest])
        data = await self.month()
        self.assertEqual(data['source']['id'], str(latest['_id']))
        self.assertIsNone(data['comparison'])
        self.assertEqual((await self.month('2026-10'))['records'], [])

    async def test_browse_same_month_uploads_without_changing_latest_or_report_snapshot(self):
        await self.save()
        latest = deepcopy(self.source)
        latest.update(_id=ObjectId(), report_date='2026-09-20')
        latest['summary'][0]['cpu'] = '40%'
        august = deepcopy(self.source)
        august.update(_id=ObjectId(), report_date='2026-08-17')
        await M.get_db()[M.HEALTH_REPORTS].insert_many([latest, august])
        data = await self.month()
        self.assertEqual([s['id'] for s in data['sources']], [str(latest['_id']), str(self.sid)])
        response = await self.client.get('/resources', params={'month': '2026-09', 'source_id': str(self.sid)})
        self.assertEqual(response.status_code, 200, response.text)
        older = response.json()
        self.assertEqual(older['source']['id'], str(self.sid))
        self.assertEqual(older['records'][0]['cpu']['value'], 0)
        self.assertEqual(older['items'][0]['records'][0]['cpu']['value'], 0)
        self.assertEqual(older['comparison']['id'], str(august['_id']))
        self.assertEqual((await self.month())['source']['id'], str(latest['_id']))
        _, snapshot = await reports.snapshot(Preview(month='2026-09'))
        self.assertEqual(snapshot['source']['id'], str(latest['_id']))
        self.assertEqual((await self.month('2026-10'))['sources'], [])

    async def test_browse_rejects_wrong_month_missing_or_invalid_upload(self):
        for month, source_id in [('2026-08', str(self.sid)), ('2026-09', str(ObjectId())), ('2026-09', 'invalid')]:
            response = await self.client.get('/resources', params={'month': month, 'source_id': source_id})
            self.assertIn(response.status_code, (400, 422), response.text)

    async def test_requires_server_check_permission(self):
        self.user = self.user.model_copy(update={'permissions': ['asset']})
        for method, path, body in [('GET', '/resources?month=2026-09', None), ('GET', '/resources/targets', None), ('POST', '/resources/preview', {'month': '2026-09', 'source_id': str(self.sid), 'mappings': []}), ('PUT', '/resources/targets', {'version': 0, 'asset_ids': []}), ('PUT', f'/resources/{self.sid}/mappings', {'mappings': [{'row_key': 'row', 'asset_id': str(self.aid)}]})]:
            response = await self.client.request(method, path, json=body)
            self.assertEqual(response.status_code, 403)
