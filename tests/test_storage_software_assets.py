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
        body = self.body('서버')
        body.pop('ip')
        response = await self.client.post('/assets/mcp-create', json=body)
        self.assertEqual(response.status_code, 422)
        self.assertIn('IP', response.json()['detail']['missing'])

    async def test_storage_without_management_ip_and_clearing(self):
        ids = []
        for name in ('DAS-01', 'DAS-02'):
            body = self.body('스토리지', name)
            body.pop('ip')
            response = await self.client.post('/assets/mcp-create', json=body)
            self.assertEqual(response.status_code, 201, response.text)
            ids.append(response.json()['asset']['id'])
        for ip in ('192.0.2.32', ''):
            response = await self.client.patch('/assets/' + ids[0], params={'category': '스토리지'}, json={'ip': ip})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['ip'], ip)

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

    async def test_optional_fields_and_multiple_linked_assets_round_trip(self):
        targets = []
        for category in ('서버', 'VMware'):
            response = await self.client.post('/assets', params={'category': category}, json={'name': category, 'ip': '192.0.2.40'})
            self.assertEqual(response.status_code, 201, response.text)
            targets.append(response.json()['id'])
        for category, extra in [
            ('스토리지', {'총물리용량': '2', '총물리용량단위': 'TB', '사용가능용량': '1000', '사용가능용량단위': 'GB', '연결방식': '["NFS","SMB"]'}),
            ('소프트웨어', {'라이선스수량': '50', '라이선스기준': '사용자', '라이선스식별번호': '00123', '사용권형태': '구독', '사용시작일': '2026-11-01', '사용권만료일': '2027-10-31'}),
        ]:
            body = self.body(category)
            body['fields'].update({**extra, '연결자산': ','.join(targets)})
            response = await self.client.post('/assets', params={'category': category}, json=body)
            self.assertEqual(response.status_code, 201, response.text)
            asset = response.json()
            self.assertEqual(asset['fields']['연결자산'], targets)
            fields = {**asset['fields'], '비고': '다른 필드 수정'}
            updated = await self.client.patch('/assets/' + asset['id'], params={'category': category}, json={'fields': fields, 'version': 1})
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertEqual(updated.json()['fields'], fields)
            resolved = await self.client.post('/assets/linked-assets/resolve', json={'asset_ids': targets})
            self.assertEqual([a['name'] for a in resolved.json()], ['서버', 'VMware'])
            found = await self.client.get('/assets/linked-assets/search', params={'search': 'VMware', 'category': 'VMware'})
            self.assertEqual([a['id'] for a in found.json()], targets[1:])

    async def test_invalid_or_deleted_connections_and_permissions(self):
        body = self.body('소프트웨어')
        response = await self.client.post('/assets', params={'category': '소프트웨어'}, json=body)
        asset = response.json()
        url = '/assets/' + asset['id']
        for target in (asset['id'], str(ObjectId())):
            response = await self.client.patch(url, params={'category': '소프트웨어'}, json={'fields': {**asset['fields'], '연결자산': [target]}})
            self.assertEqual(response.status_code, 409, response.text)
        target = (await self.client.post('/assets', params={'category': '서버'}, json={'name': '연결 서버'})).json()
        fields = {**asset['fields'], '연결자산': [target['id']]}
        self.assertEqual((await self.client.patch(url, params={'category': '소프트웨어'}, json={'fields': fields})).status_code, 200)
        await self.client.request('DELETE', '/assets/' + target['id'], params={'category': '서버'}, json={})
        resolved = (await self.client.post('/assets/linked-assets/resolve', json={'asset_ids': [target['id']]})).json()
        self.assertTrue(resolved[0]['is_deleted'])
        # Existing deleted links survive unrelated edits; new links to deleted assets fail.
        self.assertEqual((await self.client.patch(url, params={'category': '소프트웨어'}, json={'fields': fields})).status_code, 200)
        body['fields']['연결자산'] = [target['id']]
        self.assertEqual((await self.client.post('/assets', params={'category': '소프트웨어'}, json=body)).status_code, 409)
        self.user.permissions = []
        self.assertEqual((await self.client.get('/assets/linked-assets/search')).status_code, 403)
        self.assertEqual((await self.client.post('/assets/linked-assets/resolve', json={'asset_ids': []})).status_code, 403)

    async def test_optional_software_server_connections_and_reverse_lookup(self):
        servers = []
        for name in ('server-a', 'server-b'):
            response = await self.client.post('/assets', params={'category': '서버'}, json={'name': name})
            self.assertEqual(response.status_code, 201, response.text)
            servers.append(response.json()['id'])
        response = await self.client.post('/assets', params={'category': '소프트웨어'}, json=self.body('소프트웨어'))
        self.assertEqual(response.status_code, 201, response.text)
        software = response.json()
        url = '/assets/' + software['id']

        async def connected(identifier):
            result = await self.client.get('/assets/' + identifier + '/software', params={'category': '서버'})
            self.assertEqual(result.status_code, 200, result.text)
            return result.json()

        # Registration does not require a host, and a server has no phantom links.
        self.assertFalse(software['fields'].get('연결자산'))
        self.assertEqual(await connected(servers[0]), [])
        for selected in (servers, servers[1:], []):
            response = await self.client.patch(url, params={'category': '소프트웨어'}, json={
                'fields': {**software['fields'], '연결자산': selected}, 'version': software['version'],
            })
            self.assertEqual(response.status_code, 200, response.text)
            software = response.json()
            for server in servers:
                self.assertEqual([item['id'] for item in await connected(server)], [software['id']] if server in selected else [])
        self.assertFalse(software['is_deleted'])
        self.assertEqual(software['fields']['연결자산'], [])

        # A deleted software asset disappears from the server view, then returns on restore.
        await self.client.patch(url, params={'category': '소프트웨어'}, json={'fields': {**software['fields'], '연결자산': servers}})
        await self.client.request('DELETE', url, params={'category': '소프트웨어'}, json={})
        self.assertEqual(await connected(servers[0]), [])
        await self.client.post(url + '/restore', params={'category': '소프트웨어'})
        self.assertEqual([item['id'] for item in await connected(servers[0])], [software['id']])
        missing = await self.client.get('/assets/' + str(ObjectId()) + '/software')
        self.assertEqual(missing.status_code, 404)
        self.user.permissions = []
        forbidden = await self.client.get('/assets/' + servers[0] + '/software')
        self.assertEqual(forbidden.status_code, 403)

    async def linked_fixture(self):
        servers = []
        for category in ('서버', 'VMware'):
            result = await self.client.post('/assets', params={'category': category}, json={'name': category})
            self.assertEqual(result.status_code, 201, result.text)
            servers.append(result.json())
        body = self.body('소프트웨어', 'production-web')
        body['fields'].update({'운영체제': 'Nginx Plus', 'version': '1.26', '분류': 'WEB',
                              '라이선스수량': 8, '라이선스기준': '코어', '사용권형태': '구독',
                              '사용권만료일': '2027-11-01', '연결자산': [servers[0]['id']],
                              '사용자정의': {'note': '보존'}})
        result = await self.client.post('/assets', params={'category': '소프트웨어'}, json=body)
        self.assertEqual(result.status_code, 201, result.text)
        return servers, result.json()

    async def test_server_side_links_preserve_metadata_and_other_servers(self):
        servers, software = await self.linked_fixture()
        # MongoDB stores timestamps at millisecond precision; freshly created API
        # responses can still carry microseconds. Compare persisted data directly.
        def comparable(asset):
            return {key: value for key, value in asset.items() if not key.endswith('_at')}

        url = f"/assets/{servers[1]['id']}/software/{software['id']}"
        params = {'category': 'VMware'}
        original_fields = {k: v for k, v in software['fields'].items() if k != '연결자산'}
        for method, expected in [('PUT', [s['id'] for s in servers]), ('DELETE', [servers[0]['id']])]:
            result = await self.client.request(method, url, params=params)
            self.assertEqual(result.status_code, 200, result.text)
            updated = result.json()
            self.assertEqual(updated['fields']['연결자산'], expected)
            self.assertEqual({k: v for k, v in updated['fields'].items() if k != '연결자산'}, original_fields)
            self.assertFalse(updated['is_deleted'])
            self.assertEqual(updated['version'], software['version'] + 1)
            col = M.get_asset_collection('소프트웨어')
            before_repeat = await col.find_one({'_id': ObjectId(software['id'])})
            repeated = (await self.client.request(method, url, params=params)).json()
            self.assertEqual(comparable(repeated), comparable(updated))
            self.assertEqual(await col.find_one({'_id': ObjectId(software['id'])}), before_repeat)
            software = updated
            for server in servers:
                category = server['fields']['자산유형']
                connected = (await self.client.get('/assets/' + server['id'] + '/software', params={'category': category})).json()
                self.assertEqual([s['id'] for s in connected], [software['id']] if server['id'] in expected else [])
                current = (await self.client.get('/assets/' + server['id'], params={'category': category})).json()
                self.assertEqual(comparable(current), comparable(server))
            current = (await self.client.get('/assets/' + software['id'], params={'category': '소프트웨어'})).json()
            self.assertEqual(comparable(current), comparable(software))
        history = (await self.client.get('/assets/' + software['id'] + '/history', params={'category': '소프트웨어'})).json()
        updates = [entry for entry in history if entry['action'] == 'UPDATE']
        self.assertEqual(len(updates), 2)
        self.assertTrue(all('fields.연결자산' in entry['patch']['$set'] for entry in updates))

    async def test_server_side_links_reject_stale_concurrent_writes(self):
        from app.services import assets_service
        servers, software = await self.linked_fixture()
        col = M.get_asset_collection('소프트웨어')
        prepare = assets_service.prepare_details

        async def concurrent_edit(*args, **kwargs):
            normalized = await prepare(*args, **kwargs)
            await col.update_one({'_id': ObjectId(software['id'])}, {
                '$set': {'fields.연결자산': [], 'fields.비고': '동시 수정'}, '$inc': {'version': 1}})
            return normalized

        with patch.object(assets_service, 'prepare_details', side_effect=concurrent_edit):
            result = await self.client.put(f"/assets/{servers[1]['id']}/software/{software['id']}", params={'category': 'VMware'})
        self.assertEqual(result.status_code, 409, result.text)
        current = await col.find_one({'_id': ObjectId(software['id'])})
        self.assertEqual(current['fields']['연결자산'], [])
        self.assertEqual(current['fields']['비고'], '동시 수정')
        history = (await self.client.get('/assets/' + software['id'] + '/history', params={'category': '소프트웨어'})).json()
        self.assertEqual(len(history), 1)

    async def test_server_side_links_reject_deleted_missing_invalid_and_unauthorized_assets(self):
        servers, software = await self.linked_fixture()
        for server_id, sw_id, category, expected in [
            (str(ObjectId()), software['id'], '서버', 404),
            (servers[0]['id'], str(ObjectId()), '서버', 404),
            (servers[0]['id'], software['id'], '네트워크', 409),
            ('invalid', software['id'], '서버', 400),
        ]:
            result = await self.client.put(f'/assets/{server_id}/software/{sw_id}', params={'category': category})
            self.assertEqual(result.status_code, expected, result.text)
        await self.client.request('DELETE', '/assets/' + servers[1]['id'], params={'category': 'VMware'}, json={})
        result = await self.client.put(f"/assets/{servers[1]['id']}/software/{software['id']}", params={'category': 'VMware'})
        self.assertEqual(result.status_code, 404, result.text)
        await self.client.request('DELETE', '/assets/' + software['id'], params={'category': '소프트웨어'}, json={})
        result = await self.client.put(f"/assets/{servers[0]['id']}/software/{software['id']}")
        self.assertEqual(result.status_code, 404, result.text)
        self.user.permissions = []
        for method in ('PUT', 'DELETE'):
            result = await self.client.request(method, f"/assets/{servers[0]['id']}/software/{software['id']}")
            self.assertEqual(result.status_code, 403, result.text)
        self.assertEqual((await self.client.get('/assets/software/search')).status_code, 403)

    async def test_software_search_matches_product_name_identifier_version_and_excludes_deleted(self):
        _, software = await self.linked_fixture()
        for term in ('production-web', 'nginx', 'NEW-production', '1.26'):
            result = await self.client.get('/assets/software/search', params={'search': term})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual([s['id'] for s in result.json()], [software['id']])
        for term in ('서버', '.*'):
            self.assertEqual((await self.client.get('/assets/software/search', params={'search': term})).json(), [])
        await self.client.request('DELETE', '/assets/' + software['id'], params={'category': '소프트웨어'}, json={})
        self.assertEqual((await self.client.get('/assets/software/search')).json(), [])
