"""Direct system-info editing through the existing asset API, on isolated collections."""
import asyncio
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
from app.services.assets_service import AssetsService


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Requires explicit isolated MongoDB test run')
class AssetSystemInfoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        prefix = 'test_system_info_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                self.names.add(prefix + name)
                return self.real_db[prefix + name]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.aid = ObjectId()
        self.user = UserPublic(id=str(ObjectId()), email='inventory@example.com', full_name='담당자', permissions=['asset'])
        await M.get_assets_servers_collection().insert_one({
            '_id': self.aid, 'name': 'server-01', 'ip': '192.0.2.1', 'version': 1,
            'fields': {'자산유형': '서버', '사양': '기존 사양'},
        })
        app = FastAPI()
        app.include_router(router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.url = f'/assets/{self.aid}?category=서버'

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    def info(self):
        return {
            'cpu': {'model': 'Example CPU', 'sockets': 1, 'coreCount': 6, 'logicalCpus': 12},
            'memory': {'totalGb': 32, 'totalSlots': 4},
            'memoryModules': [{'slot': 'A1', 'capacityGb': 16, 'status': '장착'}, {'slot': 'A2', 'status': '미장착'}],
            'disks': [{'name': 'sda', 'type': '디스크', 'capacity': '1 TB'},
                      {'name': 'sda1', 'type': '파티션', 'parent': 'sda', 'mountPoint': '/data', 'capacity': '500 GB'}],
            'hardware': {'boardModel': 'Example Board', 'biosDate': '2026-01-02'},
            'networkInterfaces': [{'name': 'bond0', 'type': '본딩', 'state': '활성', 'ipv4': '192.0.2.10/24\n192.0.2.11/24'},
                                  {'name': 'eth0', 'parent': 'bond0', 'mac': '02:00:00:00:00:01', 'mtu': 1500}],
            'notes': '직접 입력한 정보',
        }

    async def save(self, **kwargs):
        response = await self.client.patch(self.url, json={'version': 1, 'system_info': self.info(), **kwargs})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_direct_fields_round_trip_and_shared_save(self):
        saved = await self.save(name='renamed', fields={'자산유형': '서버', '사양': '변경된 구성'})
        self.assertEqual(saved['name'], 'renamed')
        self.assertEqual(saved['fields']['사양'], '변경된 구성')
        self.assertEqual(saved['version'], 2)
        doc = (await self.client.get(self.url)).json()
        self.assertEqual(doc['system_info'], saved['system_info'])
        self.assertEqual(doc['system_info']['cpu']['coreCount'], 6)
        self.assertEqual(doc['system_info']['disks'][1]['parent'], 'sda')
        self.assertEqual(doc['system_info']['hardware']['biosDate'], '2026-01-02')
        self.assertEqual(doc['system_info']['networkInterfaces'][0]['ipv4'], '192.0.2.10/24\n192.0.2.11/24')
        stored = await M.get_assets_servers_collection().find_one({'_id': self.aid})
        self.assertEqual(stored['system_info']['cpu']['core_count'], 6)
        self.assertNotIn('command', stored['system_info'])
        self.assertNotIn('raw_text', stored['system_info'])

    async def test_ordinary_asset_edits_preserve_system_information(self):
        saved = await self.save()
        updated = await self.client.patch(self.url, json={'version': 2, 'fields': {'사양': '구성만 편집'}})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['system_info'], saved['system_info'])
        history = await M.get_assets_server_history_collection().find({'asset_id': str(self.aid)}).to_list(None)
        self.assertEqual(len(history), 2)
        self.assertTrue(any(d['path'].startswith('system_info') for d in history[0]['diff']))

    async def test_unknown_values_remain_empty_and_entries_can_be_removed(self):
        await self.save()
        saved = await self.save(version=2, system_info={'cpu': {'model': '일부 정보만 입력'}, 'memory': {'totalGb': 0}})
        info = saved['system_info']
        self.assertIsNone(info['cpu']['coreCount'])
        self.assertEqual(info['memory']['totalGb'], 0)
        self.assertEqual(info['disks'], [])
        self.assertEqual(info['memoryModules'], [])
        cleared = await self.save(version=3, system_info=None)
        self.assertEqual(cleared['system_info']['cpu']['model'], '')

    async def test_invalid_form_rejects_entire_save(self):
        invalid = [
            {'cpu': {'coreCount': -1}}, {'cpu': {'sockets': 1.5}},
            {'memory': {'totalGb': -2}}, {'memoryModules': [{'capacityGb': -1}]},
            {'hardware': {'biosDate': '2026-02-30'}}, {'networkInterfaces': [{'mtu': 0}]},
            {'disks': [{}] * 257}, {'notes': 'x' * 4001}, {'raw_text': 'not an input format'},
        ]
        for info in invalid:
            with self.subTest(info=str(info)[:100]):
                response = await self.client.patch(self.url, json={'name': 'must-not-save', 'system_info': info})
                self.assertEqual(response.status_code, 422, response.text[:300])
        doc = (await self.client.get(self.url)).json()
        self.assertEqual(doc['name'], 'server-01')
        self.assertIsNone(doc['system_info'])
        self.assertEqual(doc['version'], 1)

    async def test_concurrent_saves_have_one_winner_and_no_partial_updates(self):
        responses = await asyncio.gather(*(self.client.patch(self.url, json={
            'version': 1, 'name': f'server-{i}', 'system_info': {'cpu': {'model': f'CPU-{i}'}},
        }) for i in range(3)))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409, 409])
        winner = next(r.json() for r in responses if r.status_code == 200)
        doc = (await self.client.get(self.url)).json()
        self.assertEqual(doc['system_info']['cpu']['model'], winner['system_info']['cpu']['model'])
        self.assertEqual(doc['name'], winner['name'])
        self.assertEqual(await M.get_assets_server_history_collection().count_documents({}), 1)
        stale = await self.client.patch(self.url, json={'version': 1, 'name': 'stale', 'system_info': {}})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual((await self.client.get(self.url)).json()['name'], winner['name'])

    async def test_permissions_server_scope_and_asset_lifecycle(self):
        self.user.permissions = []
        self.assertEqual((await self.client.patch(self.url, json={'system_info': self.info()})).status_code, 403)
        self.user.permissions = ['asset']
        nid = ObjectId()
        await M.get_asset_collection('네트워크').insert_one({'_id': nid, 'ip': '192.0.2.2', 'name': 'switch', 'fields': {'자산유형': '네트워크'}})
        response = await self.client.patch(f'/assets/{nid}?category=네트워크', json={'system_info': self.info()})
        self.assertEqual(response.status_code, 409)
        saved = await self.save()
        service = AssetsService()
        await service.delete(_id=self.aid, actor_email=self.user.email)
        self.assertEqual((await self.client.patch(self.url, json={'system_info': {}})).status_code, 404)
        self.assertEqual((await self.client.get(self.url)).json()['system_info'], saved['system_info'])
        await service.restore(_id=self.aid, actor_email=self.user.email)
        self.assertEqual((await self.client.get(self.url)).json()['system_info'], saved['system_info'])
        await service.delete(_id=self.aid, actor_email=self.user.email)
        await service.purge(_id=self.aid, actor_email=self.user.email)
        self.assertEqual((await self.client.get(self.url)).status_code, 404)

    async def test_legacy_asset_without_version_can_be_saved_with_expected_version(self):
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$unset': {'version': ''}})
        saved = await self.save()
        self.assertEqual(saved['version'], 2)
