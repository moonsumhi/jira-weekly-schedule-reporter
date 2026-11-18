import unittest

from app.services.asset_type_details import normalize_details


class AssetTypeDetailsTests(unittest.TestCase):
    def test_storage_import_units_and_protocols(self):
        fields = normalize_details({'총물리용량': '2', '총물리용량단위': 'TB',
                                    '사용가능용량': '1000', '사용가능용량단위': 'GB',
                                    '연결방식': 'NFS, SMB, NFS', '디스크수량': '12'}, '스토리지')
        self.assertEqual(fields['연결방식'], ['NFS', 'SMB'])
        self.assertEqual(fields['사용가능용량'], 1000)
        self.assertEqual(fields['디스크수량'], 12)

    def test_capacity_comparison_uses_units(self):
        with self.assertRaisesRegex(ValueError, '총 물리 용량보다'):
            normalize_details({'총물리용량': 1, '총물리용량단위': 'TB',
                               '사용가능용량': 1, '사용가능용량단위': 'TiB'}, '스토리지')
        with self.assertRaisesRegex(ValueError, '단위'):
            normalize_details({'총물리용량': 10}, '스토리지')

    def test_invalid_numbers_are_rejected(self):
        for value in (-1, 'NaN', 'Infinity', True, 'not a number'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_details({'라이선스수량': value, '라이선스기준': '코어'}, '소프트웨어')
        with self.assertRaisesRegex(ValueError, '정수'):
            normalize_details({'디스크수량': 1.5}, '스토리지')

    def test_license_period_is_distinct_from_maintenance(self):
        fields = {'사용권형태': '구독', '사용시작일': '2026-11-01', '사용권만료일': '2027-10-31',
                  '유지보수종료일자': '2028-10-31', '라이선스식별번호': '000123', '라이선스수량': '0', '라이선스기준': '사용자'}
        normalized = normalize_details(fields, '소프트웨어')
        self.assertEqual(normalized['라이선스식별번호'], '000123')
        self.assertEqual(normalized['라이선스수량'], 0)
        normalized = normalize_details({**fields, '사용권형태': '영구'}, '소프트웨어')
        self.assertIsNone(normalized['사용권만료일'])
        self.assertEqual(normalized['유지보수종료일자'], '2028-10-31')

    def test_invalid_dates_and_missing_license_metric(self):
        for start, end in [('2026-12-01', '2026-11-01'), ('2026-02-30', '2027-01-01')]:
            with self.assertRaises(ValueError):
                normalize_details({'사용권형태': '구독', '사용시작일': start, '사용권만료일': end}, '소프트웨어')
        with self.assertRaisesRegex(ValueError, '라이선스 기준'):
            normalize_details({'라이선스수량': 5}, '소프트웨어')

    def test_old_assets_and_other_types_keep_their_fields(self):
        old = {'구분': '기존 분류', '제품명': '별도 제품 정보', 'custom': {'a': 1}}
        for category in ('스토리지', '소프트웨어', '서버'):
            self.assertEqual(normalize_details(old, category), old)
        self.assertEqual(normalize_details({'연결자산': 'legacy'}, '서버'), {'연결자산': 'legacy'})

    def test_excel_links_accept_json_and_reject_invalid_ids(self):
        ids = ['0123456789abcdef01234567', '0123456789abcdef01234568']
        self.assertEqual(normalize_details({'연결자산': ','.join(ids)}, '스토리지')['연결자산'], ids)
        self.assertEqual(normalize_details({'연결자산': '["' + ids[0] + '"]'}, '소프트웨어')['연결자산'], ids[:1])
        for value in ('wrong-id', '[broken', [123], {}):
            with self.assertRaises(ValueError):
                normalize_details({'연결자산': value}, '소프트웨어')
