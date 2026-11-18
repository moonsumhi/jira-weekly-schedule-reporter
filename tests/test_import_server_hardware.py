import argparse
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts import import_server_hardware as importer


def empty_rows():
    return {name: [] for name in importer.SHEETS}


class HardwareImportTests(TestCase):
    def test_template_headers_are_accepted(self):
        path = Path(__file__).resolve().parents[1] / 'outputs/server-hardware-import/서버하드웨어_HostName_일괄등록.xlsx'
        self.assertEqual({name: len(rows) for name, rows in importer.read_rows(path).items()},
                         {name: 0 for name in importer.SHEETS})

    def test_korean_headers_map_to_hardware_fields(self):
        self.assertEqual(importer.header_key('Servers', '메인보드 상세 · 제조사'),
                         'hardware.boardManufacturer')
        self.assertEqual(importer.header_key('Servers', 'BIOS 상세 · 제조사'),
                         'hardware.biosManufacturer')
        self.assertEqual(importer.header_key('MemorySlots', '메모리 슬롯'), 'slot')
        self.assertEqual(importer.header_key('Networks', 'IP'), 'ipv4')

    def test_read_rows_accepts_filled_korean_template(self):
        import tempfile
        from openpyxl import load_workbook
        template = Path(__file__).resolve().parents[1] / 'outputs/server-hardware-import/서버하드웨어_HostName_일괄등록.xlsx'
        workbook = load_workbook(template)
        columns = {cell.value: cell.column for cell in workbook['Servers'][1] if cell.value}
        workbook['Servers'].cell(2, columns['HostName'], 'SERVER-1')
        workbook['Servers'].cell(2, columns['메인보드 상세 · 제조사'], 'FUJITSU')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'filled.xlsx'
            workbook.save(path)
            rows = importer.read_rows(path)
        self.assertEqual(rows['Servers'][0]['hostName'], 'server-1')
        self.assertEqual(rows['Servers'][0]['hardware.boardManufacturer'], 'FUJITSU')

    def test_merge_preserves_unmentioned_hardware_and_list_items(self):
        rows = empty_rows()
        rows['Servers'] = [{'hostName': 'server-1', 'hardware.boardModel': 'new-board', '_row': 2}]
        rows['MemorySlots'] = [
            {'hostName': 'server-1', 'slot': 'DIMM 1', 'serial': 'new-serial', '_row': 2},
            {'hostName': 'server-1', 'slot': 'DIMM 2', 'capacityGb': 32, '_row': 3},
        ]
        original = {'hardware': {'boardModel': 'old-board', 'boardSerial': 'keep'},
                    'memoryModules': [{'slot': 'DIMM 1', 'manufacturer': 'keep', 'serial': 'old-serial'}],
                    'disks': [{'name': 'sda', 'model': 'keep-disk'}]}
        result = importer.merge_system_info(original, rows, 'server-1')
        self.assertEqual(result['hardware']['boardModel'], 'new-board')
        self.assertEqual(result['hardware']['boardSerial'], 'keep')
        self.assertEqual(result['memoryModules'][0]['manufacturer'], 'keep')
        self.assertEqual(result['memoryModules'][0]['serial'], 'new-serial')
        self.assertEqual(result['memoryModules'][1]['capacityGb'], 32)
        self.assertEqual(result['disks'][0]['model'], 'keep-disk')

    def test_merge_rejects_duplicate_list_identity(self):
        rows = empty_rows()
        rows['Disks'] = [
            {'hostName': 'server-1', 'name': 'sda', '_row': 2},
            {'hostName': 'server-1', 'name': 'sda', '_row': 3},
        ]
        with self.assertRaisesRegex(ValueError, '중복'):
            importer.merge_system_info(None, rows, 'server-1')

    def test_apply_stops_before_any_write_on_version_conflict(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps({'baseUrl': 'http://example.invalid/api', 'changes': [
                {'hostName': 'server-1', 'assetId': 'AS-1', 'id': 'id1', 'version': 1, 'before': {}, 'after': {}},
            ]}), encoding='utf-8')
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'request_json', side_effect=[
                     [{'id': 'id1', 'name': 'server-1'}],
                     {'name': 'server-1', 'asset_id': 'AS-1', 'version': 2},
                 ]) as request:
                with self.assertRaisesRegex(ValueError, '버전'):
                    importer.apply(argparse.Namespace(plan=plan_path, base_url='http://example.invalid/api', confirm=True))
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.args[1], 'GET')

    def test_preview_writes_reviewable_plan_and_backup(self):
        import os
        import tempfile
        rows = empty_rows()
        rows['Servers'] = [{'hostName': 'server-1',
                            'cpu.model': 'Xeon', '_row': 2}]
        asset = {'id': 'mongo-id', 'asset_id': 'AS-1', 'ip': '10.0.0.1', 'name': 'server-1',
                 'version': 3, 'system_info': None, 'is_deleted': False}
        same_ip_other_host = {'id': 'other-id', 'asset_id': 'AS-2', 'ip': '10.0.0.1',
                              'name': 'server-2', 'version': 1, 'system_info': None}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'plan.json'
            args = argparse.Namespace(workbook=Path('example.xlsx'),
                                      base_url='http://example.invalid/api', output=output)
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'read_rows', return_value=rows), \
                 patch.object(importer, 'request_json', return_value=[asset, same_ip_other_host]):
                importer.preview(args)
            plan = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(plan['changes'][0]['after']['cpu']['model'], 'Xeon')
            self.assertEqual(plan['changes'][0]['hostName'], 'server-1')
            self.assertEqual(plan['changes'][0]['version'], 3)
            self.assertEqual(json.loads((Path(folder) / 'plan.backup.json').read_text(encoding='utf-8')), [asset])
            self.assertIn('cpu.model', (Path(folder) / 'plan.changes.csv').read_text(encoding='utf-8-sig'))

    def test_preview_rejects_duplicate_server_hostname(self):
        import os
        import tempfile
        rows = empty_rows()
        rows['Servers'] = [{'hostName': 'server-1', 'cpu.model': 'Xeon', '_row': 2}]
        assets = [
            {'id': 'id1', 'name': 'server-1'},
            {'id': 'id2', 'name': 'SERVER-1'},
        ]
        with tempfile.TemporaryDirectory() as folder:
            args = argparse.Namespace(workbook=Path('example.xlsx'),
                                      base_url='http://example.invalid/api',
                                      output=Path(folder) / 'plan.json')
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'read_rows', return_value=rows), \
                 patch.object(importer, 'request_json', return_value=assets):
                with self.assertRaisesRegex(ValueError, '중복'):
                    importer.preview(args)
            self.assertFalse(args.output.exists())

    def test_apply_stops_when_server_hostname_changes(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps({'baseUrl': 'http://example.invalid/api', 'changes': [
                {'hostName': 'server-1', 'assetId': None, 'id': 'id1', 'version': 1,
                 'before': {}, 'after': {}},
            ]}), encoding='utf-8')
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'request_json', side_effect=[
                     [{'id': 'id1', 'name': 'server-1'}],
                     {'name': 'server-2', 'asset_id': None, 'version': 1},
                 ]) as request:
                with self.assertRaisesRegex(ValueError, 'HostName'):
                    importer.apply(argparse.Namespace(plan=plan_path,
                                                      base_url='http://example.invalid/api', confirm=True))
            self.assertEqual(request.call_count, 2)

    def test_apply_stops_if_hostname_becomes_duplicate(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps({'baseUrl': 'http://example.invalid/api', 'changes': [
                {'hostName': 'server-1', 'assetId': None, 'id': 'id1', 'version': 1,
                 'before': {}, 'after': {}},
            ]}), encoding='utf-8')
            assets = [{'id': 'id1', 'name': 'server-1'}, {'id': 'id2', 'name': 'SERVER-1'}]
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'request_json', return_value=assets) as request:
                with self.assertRaisesRegex(ValueError, 'HostName 매칭'):
                    importer.apply(argparse.Namespace(plan=plan_path,
                                                      base_url='http://example.invalid/api', confirm=True))
            self.assertEqual(request.call_count, 1)

    def test_apply_sends_versioned_hardware_patch(self):
        import os
        import tempfile
        before = importer.SystemInformation().model_dump(mode='json', by_alias=True)
        after = importer.SystemInformation(cpu={'model': 'Xeon'}).model_dump(mode='json', by_alias=True)
        with tempfile.TemporaryDirectory() as folder:
            plan_path = Path(folder) / 'plan.json'
            plan_path.write_text(json.dumps({'baseUrl': 'http://example.invalid/api', 'changes': [
                {'hostName': 'server-1', 'assetId': 'AS-1', 'id': 'id1', 'name': 'server-1', 'version': 2,
                 'before': before, 'after': after},
            ]}), encoding='utf-8')
            current = {'name': 'server-1', 'asset_id': 'AS-1', 'version': 2, 'system_info': before}
            with patch.dict(os.environ, {'ASSET_IMPORT_TOKEN': 'test-token'}), \
                 patch.object(importer, 'request_json', side_effect=[
                     [{'id': 'id1', 'name': 'server-1'}], current, {'id': 'id1'},
                 ]) as request:
                importer.apply(argparse.Namespace(plan=plan_path,
                                                  base_url='http://example.invalid/api', confirm=True))
            self.assertEqual([call.args[1] for call in request.call_args_list], ['GET', 'GET', 'PATCH'])
            self.assertEqual(request.call_args_list[2].kwargs['payload'],
                             {'version': 2, 'system_info': after})
