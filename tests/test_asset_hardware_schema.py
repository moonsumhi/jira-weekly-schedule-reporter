"""Hardware inventory accepts new fields while keeping legacy inventory usable."""
import unittest

from pydantic import ValidationError

from app.models.asset_system_info import SystemInformation


class AssetHardwareSchemaTests(unittest.TestCase):
    def test_extended_inventory_round_trip_in_database_and_api_formats(self):
        payload = {
            'cpu': {'sockets': 2, 'coresPerSocket': 16, 'frequencyMhz': 3200.5,
                    'threadList': '0-63', 'numaNodes': 2},
            'memory': {'totalGb': 128, 'installedSlots': 4, 'totalSlots': 8},
            'hardware': {'boardModel': 'Board', 'boardVersion': 'v2',
                         'boardFeatures': 'Feature', 'biosRevision': '1.2',
                         'biosFeatures': 'UEFI', 'biosDate': '2026-11-11'},
            'memoryModules': [{'slot': 'A1', 'partNumber': 'PN-001',
                               'specification': 'DDR5-4800', 'formFactor': 'DIMM', 'sizeBytes': 17179869184}],
            'disks': [{'name': 'sda', 'sizeBytes': 1099511627776, 'manufacturer': 'Vendor',
                       'kernelName': 'sda', 'partitionLabel': 'system',
                       'filesystemLabel': 'root', 'uuid': 'disk-uuid', 'revision': 'R1'}],
            'partitions': [{'mountPoint': '/', 'source': '/dev/sda1',
                            'sizeBytes': 1073741824, 'usedBytes': 536870912,
                            'availableBytes': 536870912, 'usedPercent': 50.5,
                            'filesystem': 'ext4'}],
            'networkInterfaces': [{'name': 'bond0', 'ipv4': '192.0.2.10',
                                   'netmask': '255.255.255.0', 'gateway': '192.0.2.1',
                                   'bondingOptions': 'mode=802.3ad miimon=100'}],
            'gpus': [{'manufacturer': 'Vendor', 'productName': 'GPU-1', 'coreCodename': 'Core-1'}],
        }
        info = SystemInformation.model_validate(payload)
        stored = info.model_dump(mode='json')
        self.assertEqual(stored['partitions'][0]['size_bytes'], 1073741824)
        api = SystemInformation.model_validate(stored).model_dump(mode='json', by_alias=True)
        for section, fields in payload.items():
            if isinstance(fields, list):
                for index, row in enumerate(fields):
                    for key, value in row.items():
                        self.assertEqual(api[section][index][key], value)
            else:
                for key, value in fields.items():
                    self.assertEqual(api[section][key], value)

    def test_legacy_values_survive_new_optional_fields(self):
        info = SystemInformation.model_validate({
            'cpu': {'core_count': 8, 'frequency': '3.6 GHz'},
            'hardware': {'board_model': 'Legacy', 'bios_version': '1.0'},
            'disks': [{'capacity': '1 TB', 'serial': 'old-serial'}],
        })
        self.assertEqual(info.cpu.frequency, '3.6 GHz')
        self.assertEqual(info.disks[0].capacity, '1 TB')
        self.assertEqual(info.hardware.board_model, 'Legacy')
        self.assertEqual(info.partitions, [])
        self.assertEqual(info.gpus, [])
        self.assertIsNone(info.cpu.frequency_mhz)

    def test_invalid_capacity_percentage_and_entry_counts_are_rejected(self):
        for payload in [
            {'partitions': [{'sizeBytes': -1}]},
            {'partitions': [{'sizeBytes': 1.5}]},
            {'partitions': [{'sizeBytes': 9007199254740992}]},
            {'partitions': [{'usedPercent': 100.1}]},
            {'partitions': [{}] * 513},
            {'cpu': {'frequencyMhz': -1}},
            {'cpu': {'coresPerSocket': 0}},
            {'memory': {'installedSlots': -1}},
            {'memoryModules': [{'sizeBytes': -1}]},
            {'memoryModules': [{'sizeBytes': 1.5}]},
            {'gpus': [{}] * 129},
            {'networkInterfaces': [{'bondingOptions': 'x' * 4001}]},
        ]:
            with self.subTest(payload=str(payload)[:100]):
                with self.assertRaises(ValidationError):
                    SystemInformation.model_validate(payload)

    def test_unrecognized_fields_are_not_silently_dropped(self):
        with self.assertRaises(ValidationError):
            SystemInformation.model_validate({'partitions': [{'unknown': 'value'}]})


if __name__ == '__main__':
    unittest.main()
