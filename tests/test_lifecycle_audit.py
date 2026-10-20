import json
import unittest
from datetime import date
from pathlib import Path
from app.lifecycle_audit import AUDIT, asset_eos, network_entry, reviewed_eos_map, support_status


class LifecycleAuditTest(unittest.TestCase):
    def test_9332_official_date_and_aliases(self):
        for model in ('N9K-C9332C', 'Cisco Nexus 9332C', 'C9332C', 'N9K-C9332C='):
            self.assertEqual(network_entry(model)['date'], '2029-01-31')

    def test_other_sku_never_inherits(self):
        for model in ('N9K-C9332C-GX', 'Nexus 9372PX-E', 'ASR1001-HX', 'Juniper', 'Palo Alto'):
            self.assertIsNone(network_entry(model))
            self.assertEqual(asset_eos({'운영체제': model, 'eos_date': '2030-12'}, '네트워크')['eos_action_status'], 'REVIEW_REQUIRED')

    def test_backend_normalizes_vmware_import_labels(self):
        self.assertEqual(asset_eos({'운영체제': 'VMware ESXi', 'version': '7.0 U3'}, '서버')['eos_date'], '2025-10')
        self.assertEqual(asset_eos({'운영체제': 'VMware vCenter Server 8.0', 'version': ''}, '서버')['eos_date'], '2027-10')
        self.assertEqual(asset_eos({'운영체제': 'RHEL', 'version': '9'}, '서버')['eos_action_status'], 'VERSION_REQUIRED')

    def test_support_boundary(self):
        self.assertEqual(support_status('2029-01-31', date(2029, 1, 31)), 'ACTIVE')
        self.assertEqual(support_status('2029-01-31', date(2029, 2, 1)), 'EOS')
        self.assertEqual(support_status('2029-01', date(2029, 1, 1)), 'REVIEW_REQUIRED')
        self.assertEqual(support_status('2029-01', date(2029, 2, 1)), 'EOS')

    def test_feed_cannot_restore_unverified_or_override_review(self):
        result = reviewed_eos_map({'Oracle|19c': '2027-04', 'SAP HANA|2.0': '2030-12', 'Windows 11|Windows 11': '2034-10', 'Unknown|99': '2099-12'})
        self.assertEqual(result['Oracle|19c'], '2032-12')
        self.assertEqual(result['Oracle|21c'], '2027-07')
        for key in ('SAP HANA|2.0', 'Windows 11|Windows 11', 'Unknown|99'):
            self.assertNotIn(key, result)

    def test_guidance_cannot_be_injected_by_feed(self):
        result = reviewed_eos_map({'ESXi|7.0|technicalGuidance': '2099-01-01',
                                   'ESXi|9.0|technicalGuidance': '2099-01-01',
                                   'Unknown|1|technicalGuidance': '2099-01-01'})
        self.assertEqual(result['ESXi|7.0|technicalGuidance'], '2027-04-02')
        self.assertNotIn('ESXi|9.0|technicalGuidance', result)
        self.assertNotIn('Unknown|1|technicalGuidance', result)

    def test_researched_variants_remain_separate(self):
        self.assertEqual(network_entry('N3K-C3064PQ')['date'], '2018-01-31')
        self.assertEqual(network_entry('UCS-FI-6454')['date'], '2031-12-31')
        self.assertEqual(network_entry('HX-FI-6454')['date'], '')
        self.assertEqual(asset_eos({'운영체제': 'Windows 11', 'version': '23H2 Home/Pro'}, '서버')['eos_date'], '2025-11')
        self.assertEqual(asset_eos({'운영체제': 'Windows 11', 'version': '23H2 Enterprise/Education'}, '서버')['eos_date'], '2026-11')

    def test_sources_and_mirror(self):
        mirror = Path(__file__).resolve().parents[1] / 'frontend/optool/src/data/lifecycle_audit.json'
        self.assertEqual(AUDIT, json.loads(mirror.read_text()))
        for entry in [*AUDIT['network'], *AUDIT['software'].values(), *AUDIT['eol'].values()]:
            if entry['date']:
                self.assertTrue(entry['source'].startswith('https://'))
                self.assertTrue(entry['basis'])
                self.assertRegex(entry['date'], r'^\d{4}-\d{2}(-\d{2})?$')

    def test_legacy_catalog_fully_accounted(self):
        self.assertEqual(len(AUDIT['network']), 62)
        self.assertEqual(len(AUDIT['withdrawnManufacturerRules']), 32)


if __name__ == '__main__':
    unittest.main()
