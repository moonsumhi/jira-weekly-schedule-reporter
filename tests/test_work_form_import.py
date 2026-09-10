import unittest
from app.services.work_form_import import map_document, EXTRA


class OriginalFormImportTests(unittest.TestCase):
    def test_fields_images_order_and_unmatched_content(self):
        sections = [
            {'title': '기본 정보', 'fields': [{'label': '작업명', 'type': 'text'}, {'label': '구분', 'type': 'select'}]},
            {'title': '개발 내용', 'multiple': True, 'fields': [{'label': '제목', 'type': 'text'}, {'label': '세부 작업 내용', 'type': 'textarea'}]},
        ]
        markdown = '# 작업계획서\n\n## 작업 개요\n\n### 작 업 명\n\n점검\n\n### 구분\n\n□ 서버 ■ 개발\n\n## 개발 내용\n\n### 1번째 항목\n\n| 제목 |\n| --- |\n| 개선 |\n\n#### 세부 작업 내용\n\n작업 전\n\n![사진](/api/uploads/a.png)\n\n| 테스트 | 결과 |\n| --- | --- |\n| 점검 | 정상 |\n\n작업 후\n\n## 별도 참고\n\n누락하면 안 되는 내용'
        data, warnings = map_document(markdown, sections)
        self.assertNotIn('문서 본문', data)
        self.assertEqual(data['기본 정보']['작업명'], '점검')
        self.assertEqual(data['기본 정보']['구분'], '개발')
        row = data['개발 내용'][0]
        self.assertEqual(row['제목'], '개선')
        self.assertEqual(row['세부 작업 내용__format'], 'markdown')
        body = row['세부 작업 내용']
        self.assertLess(body.index('작업 전'), body.index('![사진]'))
        self.assertLess(body.index('![사진]'), body.index('| 테스트'))
        self.assertLess(body.index('| 테스트'), body.index('작업 후'))
        self.assertIn('누락하면 안 되는 내용', data[EXTRA][0]['내용'])
        self.assertTrue(warnings)

    def test_repeated_tables_and_unrecognized_field_survive(self):
        sections = [{'title': '작업 대상', 'multiple': True, 'fields': [{'label': 'IP', 'type': 'text'}]}]
        markdown = '## 작업 대상\n\n| IP |\n| --- |\n| 첫번째 |\n\n| IP |\n| --- |\n| 두번째 |\n\n#### 별도 메모\n\n보존'
        data, _ = map_document(markdown, sections)
        self.assertEqual([r['IP'] for r in data['작업 대상']], ['첫번째', '두번째'])
        self.assertIn('보존', data[EXTRA][0]['내용'])
