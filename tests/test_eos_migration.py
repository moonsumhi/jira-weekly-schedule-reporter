import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.scripts.audit_asset_eos import run


class Collection:
    def __init__(self, docs=(), conflict=False):
        self.docs = list(docs)
        self.writes = []
        self.backups = []
        self.conflict = conflict

    def find(self, query):
        async def iterator():
            for doc in self.docs:
                yield doc
        return iterator()

    async def insert_one(self, doc):
        self.backups.append(doc)
        return SimpleNamespace(inserted_id=len(self.backups))

    async def update_one(self, query, update):
        self.writes.append((query, update))
        return SimpleNamespace(modified_count=0 if self.conflict else 1)


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def check_run(self, apply=False, conflict=False, date='2030-12'):
        fields = {'운영체제': 'N9K-C9332C', 'eos_date': date, 'eos_action_status': 'ACTIVE'}
        assets = Collection([{'_id': 'example', 'fields': fields}], conflict)
        history = Collection()
        db = {'assets_network': assets, 'asset_lifecycle_audit': history}
        with patch('app.scripts.audit_asset_eos.MongoClientManager.get_db', return_value=db), patch('app.scripts.audit_asset_eos.MongoClientManager.CATEGORY_COLLECTIONS', {'네트워크': ('assets_network', 'unused')}):
            counts = await run(apply)
        return counts, assets, history, fields

    async def test_dry_run_has_no_writes(self):
        counts, assets, history, _ = await self.check_run()
        self.assertEqual(counts['changes'], 1)
        self.assertEqual(assets.writes, [])
        self.assertEqual(history.backups, [])

    async def test_apply_backs_up_and_compares_original_fields(self):
        counts, assets, history, fields = await self.check_run(apply=True)
        self.assertEqual(counts['applied'], 1)
        self.assertEqual(history.backups[0]['before']['eos_date'], '2030-12')
        self.assertEqual(assets.writes[0][0]['fields'], fields)
        self.assertEqual(assets.writes[0][1]['$set']['fields.eos_date'], '2029-01')

    async def test_concurrent_edit_is_not_overwritten(self):
        counts, _, history, _ = await self.check_run(apply=True, conflict=True)
        self.assertEqual(counts['conflicts'], 1)
        self.assertEqual(counts['applied'], 0)
        self.assertEqual(history.writes[0][1]['$set']['applied'], False)

    async def test_custom_date_is_preserved(self):
        counts, assets, history, _ = await self.check_run(apply=True, date='2028-02')
        self.assertEqual(counts['manual_review'], 1)
        self.assertEqual(assets.writes, [])
        self.assertEqual(history.backups, [])


if __name__ == '__main__':
    unittest.main()
