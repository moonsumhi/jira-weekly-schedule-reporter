import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.lifecycle_mapping import update_vmware_dates
from app.scripts import update_eos_snapshot as updater


class VmwareSnapshotTests(unittest.TestCase):
    def test_dates_are_separate_and_false_clears_guidance(self):
        data = {}
        update_vmware_dates(data, 'ESXi', {
            'cycle': '7.0', 'eol': '2025-10-02', 'technicalGuidance': '2027-04-02',
        })
        self.assertEqual(data['ESXi|7.0|generalSupport'], '2025-10-02')
        self.assertEqual(data['ESXi|7.0|technicalGuidance'], '2027-04-02')
        update_vmware_dates(data, 'ESXi', {'cycle': '7.0', 'technicalGuidance': 'bad'})
        self.assertEqual(data['ESXi|7.0|technicalGuidance'], '2027-04-02')
        update_vmware_dates(data, 'ESXi', {'cycle': '7.0', 'technicalGuidance': False})
        self.assertNotIn('ESXi|7.0|technicalGuidance', data)

    def test_generator_syncs_frontend_and_preserves_failed_product(self):
        def fetch(slug):
            if slug == 'vcenter':
                raise OSError('offline')
            return [{'cycle': '7.0', 'eol': '2025-10-02', 'technicalGuidance': '2027-04-02'}] if slug == 'esxi' else []

        with tempfile.TemporaryDirectory() as directory:
            backend = Path(directory) / 'backend.json'
            frontend = Path(directory) / 'frontend.json'
            backend.write_text(json.dumps({'data': {'vCenter|7.0|technicalGuidance': '2027-04-02'}}))
            with patch.object(updater, 'fetch_product', side_effect=fetch):
                updater.build_snapshot(backend, frontend)
                data = json.loads(backend.read_text())['data']
                self.assertEqual(data['ESXi|7.0'], '2025-10')
                self.assertEqual(data['ESXi|7.0|generalSupport'], '2025-10-02')
                self.assertEqual(data['ESXi|7.0|technicalGuidance'], '2027-04-02')
                self.assertEqual(data, json.loads(frontend.read_text()))
                original = backend.read_bytes()
                frontend.unlink()
                updater.build_snapshot(backend, frontend)
                self.assertEqual(original, backend.read_bytes())
                self.assertEqual(data, json.loads(frontend.read_text()))
            with patch.object(updater, 'fetch_product', side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError):
                    updater.build_snapshot(backend, frontend)
            self.assertEqual(original, backend.read_bytes())
            self.assertEqual(data, json.loads(frontend.read_text()))


if __name__ == '__main__':
    unittest.main()
