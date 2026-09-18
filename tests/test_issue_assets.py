"""Issue/asset links, tested only with disposable UUID-prefixed MongoDB collections."""
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
from app.routers.pm.issues import router as issues_router
from app.routers.asset_work_history import router as history_router
from app.services import inspection_service as inspections


@unittest.skipUnless(os.environ.get('WORK_DOCUMENT_TEST_MONGO') == '1', 'Explicit isolated MongoDB run required')
class IssueAssetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        prefix = 'test_issue_assets_' + uuid4().hex + '_'
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                self.names.add(prefix + name)
                return self.real_db[prefix + name]

        self.db_patch = patch.object(M, 'get_db', return_value=TestDB())
        self.db_patch.start()
        self.aid, self.bid, self.pid, self.uid = [ObjectId() for _ in range(4)]
        self.user = UserPublic(id=str(self.uid), email='issue-assets@example.com', full_name='운영 담당', permissions=['asset', 'pm', 'job'])
        await M.get_pm_projects_collection().insert_one({'_id': self.pid, 'key': 'OPS', 'name': '운영'})
        await M.get_pm_project_members_collection().insert_one({'project_id': self.pid, 'user_id': self.uid, 'role': 'DEVELOPER'})
        await M.get_users_collection().insert_one({'_id': self.uid, 'full_name': '운영 담당'})
        await M.get_assets_servers_collection().insert_many([
            {'_id': self.aid, 'name': 'web-01', 'ip': '192.0.2.10', 'fields': {'자산유형': '서버', '서버명': '서비스 서버', '비밀': 'hidden'}},
            {'_id': self.bid, 'name': 'db-01', 'ip': '192.0.2.11'},
        ])
        await M.get_asset_collection('네트워크').insert_one({'name': 'switch-01', 'fields': {'자산유형': '네트워크'}})
        app = FastAPI()
        app.include_router(issues_router, prefix='/pm/projects')
        app.include_router(history_router, prefix='/assets')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')
        self.url = f'/pm/projects/{self.pid}/issues'

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def create(self, **values):
        response = await self.client.post(self.url, json={'title': '서버 작업', 'type': 'STORY', **values})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def history(self, asset_id=None, **params):
        response = await self.client.get(f'/assets/{asset_id or self.aid}/work-history', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def link_inspection(self, issue, month='2026-09', asset_id=None):
        doc = await M.get_pm_issues_collection().find_one({'_id': ObjectId(issue['id'])})
        assets = await inspections.resolve_assets([str(asset_id or self.aid)])
        await inspections.register(doc, month, assets, False, self.user)

    async def test_optional_links_and_bidirectional_current_metadata(self):
        plain = await self.create()
        self.assertEqual(plain['linked_assets'], [])
        issue = await self.create(asset_ids=[str(self.aid), str(self.bid)], start_date='2026-09-16T01:00:00Z', due_date='2026-09-17T09:00:00Z')
        self.assertEqual([asset['id'] for asset in issue['linked_assets']], [str(self.aid), str(self.bid)])
        for asset_id in (self.aid, self.bid):
            history = await self.history(asset_id)
            self.assertEqual(history['total'], 1)
            row = history['items'][0]
            self.assertEqual(row['type'], 'issue')
            self.assertEqual(row['issue']['key'], 'OPS-2')
            self.assertEqual(row['id'], issue['id'])
            self.assertTrue(row['start_date'].startswith('2026-09-16'))
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'name': 'renamed'}})
        detail = (await self.client.get(self.url + '/' + issue['id'])).json()
        self.assertEqual(detail['linked_assets'][0]['name'], 'renamed')
        listed = (await self.client.get(self.url)).json()
        self.assertEqual(next(row for row in listed if row['id'] == issue['id'])['linked_assets'][0]['name'], 'renamed')

    async def test_invalid_targets_fail_before_creating_or_changing_issue(self):
        bad_values = [['invalid'], [str(ObjectId())], [str(self.aid)] * 2,
                      [str(ObjectId()) for _ in range(101)], None]
        for values in bad_values:
            response = await self.client.post(self.url, json={'title': 'invalid', 'asset_ids': values})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await M.get_pm_issues_collection().count_documents({}), 0)
        issue = await self.create(asset_ids=[str(self.aid)])
        for values in bad_values:
            response = await self.client.patch(self.url + '/' + issue['id'], json={'title': 'must not change', 'asset_ids': values})
            self.assertEqual(response.status_code, 422, response.text)
        stored = await M.get_pm_issues_collection().find_one({'_id': ObjectId(issue['id'])})
        self.assertEqual(stored['title'], '서버 작업')
        self.assertEqual(stored['asset_ids'], [str(self.aid)])

    async def test_patch_omission_detach_deleted_asset_and_human_history(self):
        issue = await self.create(asset_ids=[str(self.aid)])
        url = self.url + '/' + issue['id']
        response = await self.client.patch(url, json={'status': 'DONE'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['linked_assets'][0]['id'], str(self.aid))
        self.assertEqual((await self.history())['items'][0]['issue']['status'], 'DONE')
        await M.get_assets_servers_collection().update_one({'_id': self.aid}, {'$set': {'is_deleted': True}})
        response = await self.client.patch(url, json={'asset_ids': [str(self.aid), str(self.bid)]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['linked_assets'][0]['is_deleted'])
        denied = await self.client.post(self.url, json={'title': 'new', 'asset_ids': [str(self.aid)]})
        self.assertEqual(denied.status_code, 422)
        history = await M.get_pm_issue_history_collection().find({'field': 'asset_ids'}).to_list(None)
        self.assertEqual(history[0]['old_value'], 'web-01')
        self.assertEqual(history[0]['new_value'], 'web-01, db-01')
        self.assertEqual(await M.get_pm_issue_history_collection().count_documents({'field': 'linked_assets'}), 0)
        response = await self.client.patch(url, json={'asset_ids': []})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['linked_assets'], [])
        self.assertEqual((await self.history())['total'], 0)
        self.assertEqual((await self.history(self.bid))['total'], 0)

    async def test_search_and_history_permissions_and_linked_sr_endpoint(self):
        issue = await self.create(asset_ids=[str(self.aid)])
        self.user.permissions = ['pm']
        url = f'/pm/projects/{self.pid}/asset-options'
        result = await self.client.get(url, params={'search': '192.0.2.10'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual([asset['id'] for asset in result.json()], [str(self.aid)])
        self.assertEqual(set(result.json()[0]), {'id', 'category', 'name', 'ip', 'asset_name', 'is_deleted'})
        self.assertEqual((await self.client.get(url, params={'search': '.*'})).json(), [])
        self.assertEqual(len((await self.client.get(url)).json()), 3)
        self.assertEqual((await self.client.get(f'/assets/{self.aid}/work-history')).status_code, 403)
        self.user.permissions = ['asset']
        self.assertEqual((await self.history())['total'], 0)
        self.user.permissions.append('pm')
        self.user.id = str(ObjectId())
        self.assertEqual((await self.history())['total'], 0)
        self.assertEqual((await self.client.get(url)).status_code, 403)
        self.assertEqual((await self.client.patch(self.url + '/' + issue['id'], json={'asset_ids': []})).status_code, 403)
        self.assertEqual((await self.client.get('/pm/projects/linked/' + issue['id'])).json()['linked_assets'], [])
        self.user.is_admin = True
        self.assertEqual((await self.history())['total'], 1)

    async def test_all_asset_categories_search_link_edit_and_appear_in_history(self):
        targets = {'서버': str(self.aid)}
        for category in M.CATEGORY_COLLECTIONS:
            if category == '서버':
                continue
            identifier = ObjectId()
            targets[category] = str(identifier)
            await M.get_asset_collection(category).insert_one({
                '_id': identifier, 'name': f'{category}-연결', 'asset_no': f'LINK-{category}',
                'fields': {'자산명': f'{category} 작업 대상', '비밀': 'must not expose'}})
        search_url = f'/pm/projects/{self.pid}/asset-options'
        found = (await self.client.get(search_url)).json()
        self.assertEqual({asset['category'] for asset in found}, set(M.CATEGORY_COLLECTIONS))
        for category, identifier in targets.items():
            found = (await self.client.get(search_url, params={'category': category})).json()
            self.assertTrue(found)
            self.assertTrue(all(asset['category'] == category for asset in found))
            self.assertIn(identifier, [asset['id'] for asset in found])
            if category != '서버':
                for search in (f'LINK-{category}', f'{category} 작업 대상'):
                    found = (await self.client.get(search_url, params={'search': search})).json()
                    self.assertEqual([asset['id'] for asset in found], [identifier])
        self.assertEqual((await self.client.get(search_url, params={'category': 'invalid'})).status_code, 422)
        issue = await self.create(asset_ids=list(targets.values()))
        self.assertEqual({asset['category']: asset['id'] for asset in issue['linked_assets']}, targets)
        self.assertNotIn('must not expose', str(issue))
        for identifier in targets.values():
            self.assertEqual((await self.history(identifier))['items'][0]['id'], issue['id'])

        network_id = targets['네트워크']
        await M.get_asset_collection('네트워크').update_one({'_id': ObjectId(network_id)}, {'$set': {'name': '갱신된 스위치'}})
        url = self.url + '/' + issue['id']
        detail = (await self.client.get(url)).json()
        self.assertEqual(next(asset['name'] for asset in detail['linked_assets'] if asset['id'] == network_id), '갱신된 스위치')
        await M.get_asset_collection('DBMS').update_one({'_id': ObjectId(targets['DBMS'])}, {'$set': {'is_deleted': True}})
        await M.get_asset_collection('VMware').delete_one({'_id': ObjectId(targets['VMware'])})
        changed = await self.client.patch(url, json={'asset_ids': list(targets.values())})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual({asset['category'] for asset in changed.json()['linked_assets'] if asset['is_deleted']}, {'DBMS', 'VMware'})
        rejected = await self.client.post(self.url, json={'title': 'new', 'asset_ids': [targets['DBMS']]})
        self.assertEqual(rejected.status_code, 422)
        changed = await self.client.patch(url, json={'asset_ids': [targets['랙']]})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual((await self.history(network_id))['total'], 0)
        self.assertEqual((await self.history(targets['랙']))['total'], 1)

    async def test_inspection_deduplication_respects_asset_state_and_permission(self):
        issue = await self.create(asset_ids=[str(self.aid), str(self.bid)])
        await self.link_inspection(issue)
        self.assertEqual((await self.history())['items'][0]['type'], 'issue')
        self.user.permissions.append('server_check')
        self.assertEqual((await self.history())['total'], 1)
        self.assertEqual((await self.history())['items'][0]['type'], 'inspection')
        self.assertEqual((await self.history(self.bid))['items'][0]['type'], 'issue')
        await inspections.change_occurrence(issue['id'], '2026-09', 'exclude', '일반 작업으로 진행', self.user)
        self.assertEqual({row['type'] for row in (await self.history())['items']}, {'inspection', 'issue'})
        await self.link_inspection(issue, '2026-10')
        self.assertTrue(all(row['type'] == 'inspection' for row in (await self.history())['items']))
        await self.client.delete(self.url + '/' + issue['id'])
        self.assertEqual((await self.history(self.bid))['total'], 0)
        self.assertTrue(all(row['issue_deleted'] for row in (await self.history())['items']))

    async def test_four_type_pagination_and_counts(self):
        self.user.permissions.append('server_check')
        stamp = datetime(2026, 9, 16, tzinfo=timezone.utc)
        for i in range(4):
            await self.create(title=f'작업 {i}', asset_ids=[str(self.aid)])
        issue = await self.create(asset_ids=[str(self.aid)])
        await self.link_inspection(issue)
        await self.link_inspection(issue, '2026-08')
        await self.client.post(f'/assets/{self.aid}/notes', json={'content': '운영 기록', 'occurred_on': '2026-09-16', 'client_id': uuid4().hex})
        tid = ObjectId()
        await M.get_form_templates_collection().insert_one({'_id': tid, 'title': '작업결과서', 'menu': 'Job'})
        await M.get_form_entries_collection().insert_one({'template_id': str(tid), 'asset_ids': [str(self.aid)], 'data': {}, 'created_at': stamp})
        await M.get_pm_issues_collection().update_many({}, {'$set': {'created_at': stamp}})
        all_items = (await self.history(limit=100))['items']
        pages = [await self.history(offset=offset, limit=3) for offset in (0, 3, 6, 9)]
        self.assertEqual([page['total'] for page in pages], [8] * 4)
        self.assertEqual([item for page in pages for item in page['items']], all_items)
        self.assertEqual({item['type'] for item in all_items}, {'note', 'document', 'inspection', 'issue'})
        self.assertEqual(len({(item['type'], item['id']) for item in all_items}), 8)

    async def test_past_completed_inspection_does_not_hide_reopened_issue(self):
        self.user.permissions.append('server_check')
        with patch.object(inspections, 'current_month', return_value='2026-09'):
            issue = await self.create(asset_ids=[str(self.aid)], status='DONE')
            await self.link_inspection(issue, '2026-08')
            response = await self.client.patch(self.url + '/' + issue['id'], json={'status': 'TODO'})
            self.assertEqual(response.status_code, 200, response.text)
            rows = (await self.history())['items']
            self.assertEqual(len(rows), 2)
            self.assertEqual(next(row for row in rows if row['type'] == 'issue')['issue']['status'], 'TODO')
            self.assertEqual(next(row for row in rows if row['type'] == 'inspection')['issue']['status'], 'DONE')
