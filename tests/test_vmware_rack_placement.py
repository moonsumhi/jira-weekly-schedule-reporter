import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from fastapi import HTTPException
from app.db.mongo import MongoClientManager
from app.services import rack_service, rack_placement_service


class VmwareRackTests(unittest.IsolatedAsyncioTestCase):
    async def test_unplaced_list_includes_vmware_and_filters_active_placements(self):
        placed_id = ObjectId()
        available = {'_id': ObjectId(), 'name': 'esxi-host', 'ip': '192.0.2.10'}
        requested = []
        collections = {}
        placements = MagicMock()
        placements.distinct = AsyncMock(return_value=[placed_id])

        def collection(category):
            requested.append(category)
            cursor = MagicMock()
            cursor.__aiter__.return_value = [available] if category == 'VMware' else []
            col = MagicMock()
            col.find.return_value.sort.return_value = cursor
            collections[category] = col
            return col

        with patch.object(rack_service, '_placements_col', return_value=placements), patch.object(
            MongoClientManager, 'get_asset_collection', side_effect=collection,
        ):
            rows = await rack_service.list_unplaced_assets()
        self.assertIn('VMware', requested)
        self.assertNotIn('DBMS', requested)
        self.assertEqual(rows, [{
            'asset_category': 'VMware', 'asset_id': str(available['_id']),
            'asset_code': None, 'asset_no': None, 'name': 'esxi-host', 'ip': '192.0.2.10',
        }])
        placements.distinct.assert_any_await('asset_ref_id', {'asset_category': 'VMware', 'is_deleted': False})
        collections['VMware'].find.assert_called_once_with({
            '_id': {'$nin': [placed_id]}, 'is_deleted': {'$ne': True},
        })

    async def test_vmware_passes_placement_validation(self):
        rack = {'fields': {'total_u': 42}}
        with patch.object(rack_placement_service, '_get_rack', AsyncMock(return_value=rack)), patch.object(
            rack_placement_service, '_find_conflicts', AsyncMock(return_value=[]),
        ):
            result = await rack_placement_service._validate_target('VMware', ObjectId(), 3, 2, 'FRONT')
            self.assertEqual(result['end_u'], 4)
            self.assertEqual(result['occupied_slots'], ['F:3', 'F:4'])
            with self.assertRaises(HTTPException) as error:
                await rack_placement_service._validate_target('VMware', ObjectId(), 42, 2, 'FRONT')
            self.assertEqual(error.exception.status_code, 400)

    async def test_logical_dbms_still_cannot_occupy_rack_units(self):
        with self.assertRaises(HTTPException) as error:
            await rack_placement_service._validate_target('DBMS', ObjectId(), 1, 1, 'FRONT')
        self.assertEqual(error.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main()
