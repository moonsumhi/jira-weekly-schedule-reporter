"""Resource status ignores imported hardware checks and retains other findings."""
from copy import deepcopy
import unittest

from app.services.monthly_inspection_reports import resource_rows


class ResourceStatusTests(unittest.TestCase):
    def source(self, cpu='10%', ram='30%', disk='40%', **detail):
        return {'servers': [{'host_name': 'sample', 'cpu': {'before_pct': cpu},
                            'ram': {'before_pct': ram},
                            'disks': [{'filesystem': '/', 'pct': disk}], **detail}]}

    def test_hardware_results_never_raise_status(self):
        for ng in (True, 'NG', 'N', '미선택', '☑', '', False):
            with self.subTest(ng=ng):
                source = self.source(hw_checks=[{'item': '청결 상태', 'ng': ng}])
                original = deepcopy(source)
                row = resource_rows(source)[0]
                self.assertEqual(row['level'], 'none')
                self.assertEqual(row['findings'], [])
                self.assertEqual(source, original)

    def test_usage_thresholds_remain(self):
        for metric in ('cpu', 'ram', 'disk'):
            for value, level in (('79%', 'none'), ('80%', 'warning'), ('89%', 'warning'), ('90%', 'danger')):
                with self.subTest(metric=metric, value=value):
                    row = resource_rows(self.source(**{metric: value}))[0]
                    self.assertEqual(row['level'], level)

    def test_other_checks_still_warn(self):
        for detail in ({'security_checks': [{'item': '패치', 'result': '취약'}]},
                       {'services': ['service down']}):
            with self.subTest(detail=detail):
                row = resource_rows(self.source(**detail))[0]
                self.assertEqual(row['level'], 'warning')
                self.assertEqual(len(row['findings']), 1)
        row = resource_rows({'summary': [{'host_name': 'sample', 'log_errors': '오류 발생'}]})[0]
        self.assertEqual(row['level'], 'warning')
