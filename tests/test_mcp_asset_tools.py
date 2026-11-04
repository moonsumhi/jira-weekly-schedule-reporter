"""MCP asset tools forward validated input without touching a live service."""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('MONGO_URI', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('APP_DB_NAME', 'unit_test')
path = Path(__file__).resolve().parents[1] / 'mcp-server' / 'server.py'
spec = importlib.util.spec_from_file_location('mcp_test_server', path)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class McpAssetToolTests(unittest.TestCase):
    def response(self, status, data):
        result = Mock(status_code=status, text=json.dumps(data, ensure_ascii=False))
        result.json.return_value = data
        return result

    def test_create_forwards_structured_system_info_and_returns_batch(self):
        response = self.response(201, {'asset': {'id': 'a'}, 'batch_id': 'b', 'lifecycle': {'eos': {'eos_date': '2024-11'}}})
        with patch.object(server, '_backend_post', return_value=response) as post:
            result = json.loads(server.create_asset('서버', 'host', '192.0.2.1', asset_no='A-1',
                fields={'구분': '운영', '서버명': '서버', '설명': '설명', '운영체제': 'Rocky Linux', 'version': '9.4'},
                system_info={'cpu': {'core_count': 16}}))
        self.assertTrue(result['ok'])
        self.assertEqual(result['batch_id'], 'b')
        self.assertEqual(post.call_args.args[0], '/assets/mcp-create')
        self.assertEqual(post.call_args.args[1]['system_info']['cpu']['core_count'], 16)
        self.assertFalse(post.call_args.args[1]['confirm_duplicate_ip'])

    def test_non_object_fields_are_rejected_before_network(self):
        with patch.object(server, '_backend_post') as post:
            for bad in ('[]', '[1]', 'null', 'not-json'):
                self.assertFalse(json.loads(server.create_asset('서버', 'host', fields=bad))['ok'])
            self.assertFalse(json.loads(server.create_asset('서버', 'host', system_info='[]'))['ok'])
        post.assert_not_called()

    def test_duplicate_response_is_returned_and_confirmation_is_explicit(self):
        response = self.response(409, {'detail': {'code': 'DUPLICATE_IP', 'candidates': [{'id': 'existing'}]}})
        with patch.object(server, '_backend_post', return_value=response) as post:
            result = json.loads(server.create_asset('서버', 'host'))
            self.assertEqual(result['detail']['code'], 'DUPLICATE_IP')
            self.assertIn('사용자에게 확인', result['note'])
            server.create_asset('서버', 'host', confirm_duplicate_ip=True)
            self.assertTrue(post.call_args.args[1]['confirm_duplicate_ip'])

    def test_schema_comes_from_backend_not_existing_asset_sample(self):
        response = self.response(200, {'schema': {'$defs': {'SystemInformation': {'type': 'object'}}}})
        with patch.object(server, '_backend_get', return_value=response) as get:
            result = json.loads(server.get_asset_schema('서버'))
        get.assert_called_once_with('/assets/mcp-schema')
        self.assertIn('SystemInformation', result['schema']['$defs'])

    def test_failure_does_not_silently_retry_uncertain_registration(self):
        with patch.object(server, '_backend_post', side_effect=TimeoutError('timeout')) as post:
            result = json.loads(server.create_asset('서버', 'host'))
        self.assertFalse(result['ok'])
        self.assertIn('재시도 전에', result['note'])
        post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
