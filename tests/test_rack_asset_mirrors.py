"""Rack rename regression tests using only disposable MongoDB collections."""
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.assets import router as assets_router
from app.routers.racks import router as racks_router
from app.routers.auth import get_current_user
from app.services.assets_service import AssetsService
from app.services import rack_placement_service as placements


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB tests only')
class RackAssetMirrorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        prefix = 'test_rack_mirror_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                full = name if name.startswith(prefix) else prefix + name
                self.names.add(full)
                return self.real_db[full]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.categories_patch = patch.object(M, 'CATEGORY_COLLECTIONS', {
            cat: (prefix + col, prefix + hist) for cat, (col, hist) in M.CATEGORY_COLLECTIONS.items()
        })
        self.db_patch.start()
        self.categories_patch.start()
        self.user = UserPublic(id=str(ObjectId()), email='rack-test@example.com', permissions=['asset'])
        app = FastAPI()
        app.include_router(assets_router, prefix='/assets')
        app.include_router(racks_router, prefix='/racks')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.rack = await AssetsService('랙').create(ip='', name='A1', asset_id='A1',
            fields={'total_u': 42, 'server_room': '서버실 1'}, actor_email=self.user.email)
        self.members = []
        for index, category in enumerate(['서버', '네트워크', '정보보호시스템', 'VMware']):
            asset = await AssetsService(category).create(ip=f'192.0.2.{index + 1}', name=f'asset-{index}',
                fields={'비고': '보존할 값'}, actor_email=self.user.email)
            placement = await placements.create_placement({
                'asset_category': category, 'asset_id': asset['id'], 'rack_id': self.rack['id'],
                'start_u': 1 + index * 2, 'height_u': 2, 'mount_side': 'FRONT',
            }, actor=self.user.email)
            self.members.append((category, asset, placement))

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.categories_patch.stop()
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def stored(self, category, ident):
        return await M.get_asset_collection(category).find_one({'_id': ObjectId(ident)})

    async def rename(self, name='A1 (SDDC 영역)', **more):
        response = await self.client.patch(f'/assets/{self.rack["id"]}', params={'category': '랙'}, json={'name': name, **more})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_rename_updates_all_physical_categories_without_moving_assets(self):
        history_count = await M.get_rack_placements_history_collection().count_documents({})
        updated = await self.rename(version=1)
        self.assertEqual(updated['asset_id'], 'A1')
        for category, asset, placement in self.members:
            stored = await self.stored(category, asset['id'])
            self.assertEqual(stored['fields']['rack_no'], 'A1 (SDDC 영역)')
            self.assertEqual(stored['fields']['rack_unit_no'], f'{placement["start_u"]}-{placement["end_u"]}')
            self.assertEqual(stored['fields']['위치'], '서버실 1')
            self.assertEqual(stored['fields']['비고'], '보존할 값')
            current = await placements.get_active_placement(category, ObjectId(asset['id']))
            self.assertEqual(current['rack_ref_id'], ObjectId(self.rack['id']))
            self.assertEqual(current['version'], placement['version'])
        self.assertEqual(await M.get_rack_placements_history_collection().count_documents({}), history_count)

    async def test_previously_renamed_rack_is_correct_on_detail_and_all_lists(self):
        # Reproduce a rename made before this fix: child mirrors still contain A1.
        await M.get_asset_collection('랙').update_one({'_id': ObjectId(self.rack['id'])}, {'$set': {'name': 'A1 (SDDC 영역)'}})
        all_assets = (await self.client.get('/assets')).json()
        for category, asset, _ in self.members:
            detail = (await self.client.get(f'/assets/{asset["id"]}', params={'category': category})).json()
            listed = (await self.client.get('/assets', params={'category': category})).json()
            for doc in [detail, next(x for x in listed if x['id'] == asset['id']), next(x for x in all_assets if x['id'] == asset['id'])]:
                self.assertEqual(doc['fields']['rack_no'], 'A1 (SDDC 영역)')
            # GET derives the current display value without changing stored history/data.
            self.assertEqual((await self.stored(category, asset['id']))['fields']['rack_no'], 'A1')
        category, asset, _ = self.members[0]
        for body in [{}, {'name': '호스트명만 변경'}]:
            saved = await self.client.patch(f'/assets/{asset["id"]}', params={'category': category}, json=body)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json()['fields']['rack_no'], 'A1 (SDDC 영역)')
        # Saving the already-renamed rack also repairs persisted mirrors.
        await self.rename()
        self.assertEqual((await self.stored('서버', self.members[0][1]['id']))['fields']['rack_no'], 'A1 (SDDC 영역)')

    async def test_asset_save_cannot_restore_a_stale_rack_name_or_unit(self):
        category, asset, placement = self.members[0]
        old_fields = (await self.stored(category, asset['id']))['fields']
        await self.rename()
        old_fields.update({'rack_unit_no': '99', '위치': '오래된 서버실', '비고': '편집한 비고'})
        response = await self.client.patch(f'/assets/{asset["id"]}', params={'category': category}, json={'fields': old_fields})
        self.assertEqual(response.status_code, 200, response.text)
        stored = await self.stored(category, asset['id'])
        self.assertEqual(stored['fields']['rack_no'], 'A1 (SDDC 영역)')
        self.assertEqual(stored['fields']['rack_unit_no'], '1-2')
        self.assertEqual(stored['fields']['위치'], '서버실 1')
        self.assertEqual(stored['fields']['비고'], '편집한 비고')
        response = await self.client.put(f'/assets/{asset["id"]}', params={'category': category},
            json={'name': asset['name'], 'ip': asset['ip'], 'fields': old_fields})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['fields']['rack_no'], 'A1 (SDDC 영역)')

    async def test_rename_joins_by_id_not_old_name_and_excludes_removed_or_moved_members(self):
        other = await AssetsService('랙').create(ip='', name='B1', fields={'total_u': 42, 'server_room': '서버실 2'}, actor_email=self.user.email)
        removed_category, removed, removed_placement = self.members[0]
        await placements.remove_placement(removed_placement['id'], actor=self.user.email)
        moved_category, moved, moved_placement = self.members[1]
        await placements.move_placement(moved_placement['id'], {'rack_id': other['id'], 'start_u': 10, 'height_u': 1, 'mount_side': 'FRONT'}, actor=self.user.email)
        legacy = await AssetsService().create(ip='192.0.2.100', name='unmanaged', fields={'rack_no': 'A1'}, actor_email=self.user.email)
        await self.rename()
        self.assertEqual((await self.stored(removed_category, removed['id']))['fields']['rack_no'], '')
        self.assertEqual((await self.stored(moved_category, moved['id']))['fields']['rack_no'], 'B1')
        self.assertEqual((await self.stored('서버', legacy['id']))['fields']['rack_no'], 'A1')
        # Unplaced assets can still have a manually chosen room, but not stale rack fields.
        result = await AssetsService().patch(_id=ObjectId(removed['id']), patch={'fields': {
            'rack_no': 'A1', 'rack_unit_no': '1-2', '위치': '별도 보관실',
        }}, actor_email=self.user.email)
        self.assertEqual(result['fields']['rack_no'], '')
        self.assertEqual(result['fields']['위치'], '별도 보관실')

    async def test_replace_rack_and_subsequent_placements_use_name_not_asset_code(self):
        response = await self.client.put(f'/assets/{self.rack["id"]}', params={'category': '랙'}, json={
            'name': 'A1 (SDDC 영역)', 'ip': '', 'asset_id': 'A1',
            'fields': {'total_u': 42, 'server_room': 'SDDC 서버실'},
        })
        self.assertEqual(response.status_code, 200, response.text)
        for category, asset, _ in self.members:
            fields = (await self.stored(category, asset['id']))['fields']
            self.assertEqual(fields['rack_no'], 'A1 (SDDC 영역)')
            self.assertEqual(fields['위치'], 'SDDC 서버실')
        category, asset, placement = self.members[0]
        await placements.move_placement(placement['id'], {'rack_id': self.rack['id'], 'start_u': 20, 'height_u': 2, 'mount_side': 'FRONT'}, actor=self.user.email)
        self.assertEqual((await self.stored(category, asset['id']))['fields']['rack_no'], 'A1 (SDDC 영역)')
        await placements.remove_placement(placement['id'], actor=self.user.email)
        await placements.create_placement({'asset_category': category, 'asset_id': asset['id'], 'rack_id': self.rack['id'],
            'start_u': 20, 'height_u': 1, 'mount_side': 'FRONT'}, actor=self.user.email)
        self.assertEqual((await self.stored(category, asset['id']))['fields']['rack_no'], 'A1 (SDDC 영역)')

    async def test_rejected_rename_does_not_change_member_fields(self):
        await self.rename(name='A2')
        response = await self.client.patch(f'/assets/{self.rack["id"]}', params={'category': '랙'}, json={'version': 1, 'name': 'stale'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual((await self.stored('서버', self.members[0][1]['id']))['fields']['rack_no'], 'A2')
