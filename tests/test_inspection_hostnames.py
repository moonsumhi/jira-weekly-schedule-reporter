"""Hostname bulk corrections: conservative IP matching, authorization and stale previews."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from bson import ObjectId

from app.db.mongo import MongoClientManager as M
from app.services import inspection_hostnames as svc, monthly_inspection_reports as reports
import test_inspection_resources as fixture


class MatchingTests(unittest.TestCase):
    def rows(self, records, assets):
        return svc.candidates(reports.resource_rows({'summary': records}), assets)

    def test_each_ip_is_compared_exactly_with_normalized_ipv6_and_cidr(self):
        assets = [{'_id': ObjectId(), 'name': 'old', 'ip': '49.50.1.49'},
                  {'_id': ObjectId(), 'name': 'v6-old', 'ip': '2001:db8::1'}]
        rows = self.rows([{'host_name': 'web-new', 'ip': '192.168.122.1, 49.50.1.49/24; 127.0.0.1'},
                          {'host_name': 'v6-new', 'ip': '2001:0db8:0000::1\n192.0.2.99'}], assets)
        self.assertEqual([r['status'] for r in rows], ['ready', 'ready'])
        self.assertEqual(rows[0]['matched_ips'], ['49.50.1.49'])
        self.assertEqual(rows[1]['matched_ips'], ['2001:db8::1'])
        self.assertEqual(self.rows([{'host_name': 'not-a-match', 'ip': '49.50.1.4'}], assets)[0]['status'], 'review')

    def test_common_bridge_ip_is_excluded_while_unique_interfaces_still_match(self):
        assets = [{'_id': ObjectId(), 'name': 'old-a', 'ip': '49.50.1.49, 192.168.122.1'},
                  {'_id': ObjectId(), 'name': 'old-b', 'ip': '49.50.1.50; 192.168.122.1'}]
        rows = self.rows([{'host_name': 'new-a', 'ip': '49.50.1.49, 192.168.122.1'},
                          {'host_name': 'new-b', 'ip': '192.168.122.1 49.50.1.50'}], assets)
        self.assertEqual([r['status'] for r in rows], ['ready', 'ready'])
        self.assertEqual([r['ignored_ips'] for r in rows], [['192.168.122.1']] * 2)

    def test_multiple_ip_matches_and_duplicate_asset_ips_are_never_guessed(self):
        assets = [{'_id': ObjectId(), 'name': 'a', 'ip': '192.0.2.1'},
                  {'_id': ObjectId(), 'name': 'b', 'ip': '192.0.2.2'}]
        row = self.rows([{'host_name': 'new', 'ip': '192.0.2.1,192.0.2.2'}], assets)[0]
        self.assertEqual(row['status'], 'review'); self.assertIsNone(row['asset_id'])
        assets[1]['ip'] = '192.0.2.1'
        self.assertEqual(self.rows([{'host_name': 'new', 'ip': '192.0.2.1'}], assets)[0]['status'], 'review')

    def test_no_ip_missing_hostname_shared_ip_and_hostname_collision(self):
        assets = [{'_id': ObjectId(), 'name': 'old', 'ip': '192.0.2.1'},
                  {'_id': ObjectId(), 'name': 'new', 'ip': '192.0.2.2'}]
        for hostname, ip in [('', '192.0.2.1'), ('-', '192.0.2.1'), ('new', '192.0.2.1'),
                             ('other', 'garbage'), ('other', '127.0.0.1, 0.0.0.0, fe80::1')]:
            with self.subTest(hostname=hostname, ip=ip):
                self.assertEqual(self.rows([{'host_name': hostname, 'ip': ip}], assets)[0]['status'], 'review')
        rows = self.rows([{'host_name': 'a', 'ip': '192.0.2.1'}, {'host_name': 'b', 'ip': '192.0.2.1'}], assets)
        self.assertTrue(all(r['status'] == 'review' for r in rows))

    def test_several_rows_cannot_rename_the_same_asset_and_hostname_is_unique(self):
        asset = {'_id': ObjectId(), 'name': 'old', 'ip': '192.0.2.1,192.0.2.2'}
        for names in [('new-a', 'new-b'), ('same-name', 'same-name')]:
            rows = self.rows([{'host_name': names[0], 'ip': '192.0.2.1'},
                              {'host_name': names[1], 'ip': '192.0.2.2'}], [asset])
            self.assertTrue(all(r['status'] == 'review' for r in rows))


@unittest.skipUnless(os.environ.get('INSPECTION_TEST_MONGO') == '1', 'Explicit disposable MongoDB tests only')
class HostnameTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixture.ResourceTests.asyncSetUp(self)
        self.user = self.user.model_copy(update={'is_admin': True})
        self.path = f'/resources/{self.sid}/hostnames'
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {
            'name': 'old-web', 'version': 3, 'fields': {'자산명': '웹 서버', '위치': 'rack-a'}}})
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {
            'summary.0.ip': '192.168.122.1, 192.0.2.1'}})

    asyncTearDown = fixture.ResourceTests.asyncTearDown

    async def preview(self):
        response = await self.client.get(self.path + '/preview')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def apply(self, preview, ids=None):
        return await self.client.post(self.path + '/apply', json={
            'revision': preview['revision'], 'asset_ids': ids if ids is not None else [str(self.aid)]})

    async def test_admin_only_even_with_both_menu_permissions_and_internal_only(self):
        for values in ({'is_admin': False, 'permissions': ['server_check', 'asset']},
                       {'is_admin': True, 'is_internal': False}):
            self.user = self.user.model_copy(update=values)
            self.assertEqual((await self.client.get(self.path + '/preview')).status_code, 403)
            response = await self.client.post(self.path + '/apply', json={'revision': '0' * 64, 'asset_ids': [str(self.aid)]})
            self.assertEqual(response.status_code, 403)

    async def test_apply_only_selected_hostname_with_history_and_live_resource_link(self):
        col = M.get_assets_servers_collection()
        before = await col.find_one({'_id': self.aid})
        other = await col.find_one({'_id': self.bid})
        source = await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid})
        preview = await self.preview()
        self.assertEqual(preview['rows'][0]['matched_ips'], ['192.0.2.1'])
        self.assertEqual(await col.find_one({'_id': self.aid}), before)
        response = await self.apply(preview)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'updated_ids': [str(self.aid)], 'skipped': []})
        after = await col.find_one({'_id': self.aid})
        self.assertEqual(after['name'], 'web-01'); self.assertEqual(after['version'], 4)
        for key in ('ip', 'fields'):
            self.assertEqual(after[key], before[key])
        self.assertEqual(await col.find_one({'_id': self.bid}), other)
        self.assertEqual(await M.get_db()[M.HEALTH_REPORTS].find_one({'_id': self.sid}), source)
        history = await M.get_assets_server_history_collection().find_one({'asset_id': str(self.aid)})
        self.assertEqual(history['changed_by'], self.user.email)
        self.assertEqual(history['before']['name'], 'old-web')
        self.assertEqual(history['after']['name'], 'web-01')
        self.assertEqual(history['source'], 'inspection_hostname')
        self.assertEqual(history['patch']['inspection_source_id'], str(self.sid))
        resources = (await self.client.get('/resources?month=2026-09')).json()
        self.assertEqual(resources['records'][0]['asset']['id'], str(self.aid))
        self.assertEqual((await self.preview())['rows'][0]['status'], 'unchanged')
        self.assertEqual((await self.apply(preview)).status_code, 409)
        self.assertEqual(await M.get_assets_server_history_collection().count_documents({}), 1)

    async def test_deleted_assets_other_categories_and_forged_selection_are_excluded(self):
        preview = await self.preview()
        for ids in ([str(self.bid)], [str(ObjectId())], [str(self.aid)] * 2, []):
            response = await self.apply(preview, ids)
            self.assertEqual(response.status_code, 422, response.text)
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        await M.get_asset_collection('네트워크').insert_one({'name': 'switch', 'ip': '192.0.2.1'})
        row = (await self.preview())['rows'][0]
        self.assertEqual(row['status'], 'review'); self.assertIsNone(row['asset_id'])
        self.assertEqual(await M.get_assets_server_history_collection().count_documents({}), 0)

    async def test_stale_source_or_inventory_requires_new_review_before_any_write(self):
        original = await M.get_assets_servers_collection().find_one({'_id': self.aid})
        for change in ({'name': 'someone-edited'}, {'ip': '192.0.2.9'}, {'version': 4}, {'is_deleted': True}):
            preview = await self.preview()
            await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': change})
            self.assertEqual((await self.apply(preview)).status_code, 409)
            await M.get_assets_servers_collection().replace_one({'_id': self.aid}, deepcopy(original))
        preview = await self.preview()
        await M.get_db()[M.HEALTH_REPORTS].update_one({'_id': self.sid}, {'$set': {'summary.0.host_name': 'newer-web'}})
        self.assertEqual((await self.apply(preview)).status_code, 409)
        self.assertEqual(await M.get_assets_server_history_collection().count_documents({}), 0)

    async def test_concurrent_edit_during_apply_is_skipped_without_overwriting(self):
        preview = await self.preview()
        original_preview = svc.preview
        async def concurrent_preview(source_id):
            result = await original_preview(source_id)
            await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'edited-during-apply'}, '$inc': {'version': 1}})
            return result
        with patch.object(svc, 'preview', side_effect=concurrent_preview):
            response = await self.apply(preview)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['updated_ids'], [])
        self.assertEqual(response.json()['skipped'][0]['asset_id'], str(self.aid))
        self.assertEqual((await M.get_assets_servers_collection().find_one({'_id': self.aid}))['name'], 'edited-during-apply')
        self.assertEqual(await M.get_assets_server_history_collection().count_documents({}), 0)

    async def test_missing_source_and_new_ip_ambiguity_block_apply(self):
        preview = await self.preview()
        await M.get_assets_servers_collection().insert_one({'name': 'duplicate-ip', 'ip': '192.0.2.1'})
        self.assertEqual((await self.apply(preview)).status_code, 409)
        self.assertEqual((await self.preview())['rows'][0]['status'], 'review')
        await M.get_db()[M.HEALTH_REPORTS].delete_one({'_id': self.sid})
        self.assertEqual((await self.apply(preview)).status_code, 422)
        self.assertEqual((await self.client.get('/resources/invalid/hostnames/preview')).status_code, 400)
