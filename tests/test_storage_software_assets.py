"""Storage/software asset CRUD and links against disposable MongoDB collections."""
import os
import unittest
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

import test_asset_import_rollback as fixtures
from app.db.mongo import MongoClientManager as M
from app.db.startup import migrate_storage_software_submenus
from app.models.asset_link import LinkedAsset
from app.routers.assets import router as assets_router
from app.routers.auth import get_current_user
from app.routers.inspection_tasks import router as inspection_router
from app.services import asset_links, rack_placement_service


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Disposable MongoDB only')
class StorageSoftwareTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.AssetImportRollbackTests.asyncSetUp(self)
        self.categories_patch = patch.object(M, 'CATEGORY_COLLECTIONS', {
            category: (self.prefix + collection, self.prefix + history)
            for category, (collection, history) in M.CATEGORY_COLLECTIONS.items()
        })
        self.categories_patch.start()
        await self.client.aclose()
        self.user.permissions.append('server_check')
        app = FastAPI()
        app.include_router(assets_router, prefix='/assets')
        app.include_router(inspection_router, prefix='/inspection-tasks')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        try:
            await fixtures.AssetImportRollbackTests.asyncTearDown(self)
        finally:
            self.categories_patch.stop()

    def body(self, category, name='asset-01'):
        return {
            'category': category, 'name': name, 'asset_no': 'NEW-' + name,
            'ip': '192.0.2.30' if category == '스토리지' else '',
            'fields': {'구분': '운영', '서버명': category + ' 자산', '설명': '유형 검증',
                       '운영체제': category + ' 제품', 'version': '1.10'},
        }

    async def test_crud_lists_history_and_inspection_links_for_both_categories(self):
        ids = []
        for category in ('스토리지', '소프트웨어'):
            body = self.body(category)
            body.pop('category')
            created = await self.client.post('/assets', params={'category': category}, json=body)
            self.assertEqual(created.status_code, 201, created.text)
            asset = created.json()
            ids.append(asset['id'])
            self.assertEqual(asset['fields']['자산유형'], category)
            self.assertEqual(asset['fields']['version'], '1.10')
            self.assertEqual((await M.get_asset_collection(category).find_one({'_id': ObjectId(asset['id'])}))['name'], body['name'])
            listed = await self.client.get('/assets', params={'category': category})
            self.assertEqual([a['id'] for a in listed.json()], [asset['id']])
            found = await self.client.get('/inspection-tasks/assets', params={'category': category, 'search': category + ' 자산'})
            self.assertEqual(found.status_code, 200, found.text)
            self.assertEqual([a['id'] for a in found.json()], [asset['id']])
            changed = await self.client.patch('/assets/' + asset['id'], params={'category': category},
                json={'fields': {'version': '1.11'}, 'version': 1})
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertEqual(changed.json()['fields']['version'], '1.11')
            history = await self.client.get('/assets/' + asset['id'] + '/history', params={'category': category})
            self.assertEqual({h['action'] for h in history.json()}, {'CREATE', 'UPDATE'})
        all_assets = (await self.client.get('/assets')).json()
        self.assertEqual({a['fields']['자산유형'] for a in all_assets}, {'스토리지', '소프트웨어'})
        links = [LinkedAsset(**item) for item in await asset_links.selected_assets(ids)]
        self.assertEqual([item.category for item in links], ['스토리지', '소프트웨어'])
        for asset_id, category in zip(ids, ('스토리지', '소프트웨어')):
            deleted = await self.client.request('DELETE', '/assets/' + asset_id, params={'category': category}, json={'reason': '검증'})
            self.assertEqual(deleted.status_code, 200, deleted.text)
            self.assertEqual((await self.client.get('/inspection-tasks/assets', params={'category': category})).json(), [])
            restored = await self.client.post('/assets/' + asset_id + '/restore', params={'category': category})
            self.assertEqual(restored.status_code, 200, restored.text)

    async def test_software_without_ip_and_ip_clearing(self):
        ids = []
        for name in ('software-01', 'software-02'):
            body = self.body('소프트웨어', name)
            body.pop('ip')
            response = await self.client.post('/assets/mcp-create', json=body)
            self.assertEqual(response.status_code, 201, response.text)
            ids.append(response.json()['asset']['id'])
        url = '/assets/' + ids[0]
        for ip in ('192.0.2.31', ''):
            response = await self.client.patch(url, params={'category': '소프트웨어'}, json={'ip': ip})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['ip'], ip)
        body = self.body('스토리지')
        body.pop('ip')
        response = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(response.status_code, 422)
        self.assertIn('IP', response.json()['detail']['missing'])

    async def test_existing_menus_are_preserved_and_new_entries_are_idempotent(self):
        original = {'title': '운영 자산', 'link': '/asset/list', 'icon': 'custom', 'require_admin': True}
        menus = M.get_menus_collection()
        await menus.insert_one({'slug': 'asset', 'submenus': [original], 'sub_order': ['/asset/list']})
        for _ in range(2):
            await migrate_storage_software_submenus()
        menu = await menus.find_one({'slug': 'asset'})
        self.assertEqual(menu['submenus'][0], original)
        self.assertEqual(menu['sub_order'], ['/asset/list'])
        self.assertEqual([s['title'] for s in menu['submenus'][1:]], ['스토리지', '소프트웨어'])

    async def test_software_cannot_occupy_physical_rack_units(self):
        with self.assertRaises(HTTPException) as error:
            await rack_placement_service._validate_target('소프트웨어', ObjectId(), 1, 1, 'FRONT')
        self.assertEqual(error.exception.status_code, 400)
