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

    def test_candidate_report_never_modifies_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, frontend, report = [Path(directory) / name for name in ('backend.json', 'frontend.json', 'report.json')]
            backend.write_text('{"data":{"ESXi|7.0":"2025-10"}}')
            frontend.write_text('{"ESXi|7.0":"2025-10"}')
            original = (backend.read_bytes(), frontend.read_bytes())
            def fetch(slug):
                if slug == 'esxi':
                    return [{'cycle': '7.0', 'eol': '2099-01-01', 'technicalGuidance': '2099-01-01'}]
                return []
            with patch.object(updater, 'fetch_product', side_effect=fetch):
                updater.build_snapshot(backend, frontend, report)
            self.assertEqual(original, (backend.read_bytes(), frontend.read_bytes()))
            data = json.loads(report.read_text())
            self.assertEqual(data['status'], 'unreviewed_candidates_only')
            self.assertEqual(data['changes']['ESXi|7.0']['candidate'], '2099-01')
            self.assertEqual(data['changes']['ESXi|7.0']['reviewed'], '2025-10')
            updater.write_reviewed_snapshot(backend, frontend)
            rendered = json.loads(backend.read_text())['data']
            self.assertEqual(rendered['ESXi|7.0'], '2025-10')
            self.assertEqual(rendered['ESXi|7.0|technicalGuidance'], '2027-04-02')

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
                self.assertEqual({k: v for k, v in data.items() if k.startswith(('ESXi|', 'vCenter|'))}, json.loads(frontend.read_text()))
                original = backend.read_bytes()
                frontend.unlink()
                updater.build_snapshot(backend, frontend)
                self.assertEqual(original, backend.read_bytes())
                self.assertEqual({k: v for k, v in data.items() if k.startswith(('ESXi|', 'vCenter|'))}, json.loads(frontend.read_text()))
            with patch.object(updater, 'fetch_product', side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError):
                    updater.build_snapshot(backend, frontend)
            self.assertEqual(original, backend.read_bytes())
            self.assertEqual({k: v for k, v in data.items() if k.startswith(('ESXi|', 'vCenter|'))}, json.loads(frontend.read_text()))


if __name__ == '__main__':
    unittest.main()
