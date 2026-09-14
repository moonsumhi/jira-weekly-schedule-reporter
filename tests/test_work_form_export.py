import io
import unittest
from zipfile import ZipFile

from lxml import etree

from app.services.work_form_export import original_form_markup
from app.services.work_documents import export_docx, export_hwp, export_hwpx
from app.models.form_entry import FormDocumentExport


class OriginalFormExportTests(unittest.TestCase):
    def test_section_heading_and_basic_fields_follow_report_layout(self):
        form = {'title': '작업계획서', 'sections': [{
            'title': '기본 정보', 'multiple': False, 'fields': [
                {'label': '작업명', 'type': 'text'},
                {'label': '작업 일시', 'type': 'text'},
                {'label': '서비스 명', 'type': 'text'},
                {'label': '회사명/성함/직책', 'type': 'text'},
                {'label': '중요도', 'type': 'text'},
                {'label': '목적', 'type': 'textarea'},
            ],
        }], 'data': {'기본 정보': {
            '작업명': '데이터 분석포털', '작업 일시': '2026.09.03 17:00',
            '서비스 명': '운영 서버', '회사명/성함/직책': '김도현 선임',
            '중요도': '중', '목적': '배포 작업',
        }}}
        markup = original_form_markup(form)
        self.assertIn('<tr><th colspan="4" data-role="section-heading">작업 개요</th></tr>', markup)
        self.assertIn('<th>작업명</th><td>데이터 분석포털</td><th>작업 일시</th>', markup)
        self.assertIn('<th>목적</th><td colspan="3">배포 작업</td>', markup)

    def test_original_fields_stay_in_table_cells_in_both_formats(self):
        form = {'title': '작업결과서', 'sections': [
            {'title': '작업 대상', 'multiple': True, 'fields': [
                {'label': label, 'type': 'textarea'} for label in ['작업 대상', '비고', 'HOSTNAME']]},
            {'title': '작업 결과', 'multiple': True, 'fields': [
                {'label': '작업 전', 'type': 'textarea'}, {'label': '작업 후', 'type': 'textarea'}]},
        ], 'data': {
            '문서 본문': [{'내용': 'OLD SNAPSHOT'}],
            '작업 대상': [{'작업 대상': '웹서버', '비고': '정상', 'HOSTNAME': 'web01'}],
            '작업 결과': [{'작업 전': '변경 전\n\n| 항목 | 값 |\n|---|---|\n| 상태 | 준비 |\n\n마지막',
                         '작업 전__format': 'markdown', '작업 후': '완료'}],
        }}
        payload = FormDocumentExport(markdown='OLD SNAPSHOT', format='docx', original_form=form)
        markup = original_form_markup(payload.original_form.model_dump())
        self.assertNotIn('OLD SNAPSHOT', markup)
        self.assertIn('<p class="section-gap">&#160;</p>', markup)
        self.assertLess(markup.index('<th>HOSTNAME'), markup.index('<th>비고'))
        with ZipFile(io.BytesIO(export_docx(markup))) as archive:
            root = etree.fromstring(archive.read('word/document.xml'))
            self.assertTrue(root.xpath('//*[local-name()="tc"]//*[local-name()="tbl"]'))
            self.assertIn('완료', ''.join(root.itertext()))
        with ZipFile(io.BytesIO(export_hwpx(markup))) as archive:
            root = etree.fromstring(archive.read('Contents/section0.xml'))
            self.assertTrue(root.xpath('//*[local-name()="tc"]//*[local-name()="tbl"]'))
            self.assertIn('완료', ''.join(root.itertext()))
        self.assertTrue(export_hwp(markup).startswith(bytes.fromhex('d0cf11e0a1b11ae1')))

    def test_schedule_section_uses_detail_procedure_title(self):
        form = {
            'title': '작업계획서',
            'sections': [{
                'title': '작업 시간표', 'multiple': True,
                'fields': [{'label': '시작 시간', 'type': 'text'}],
            }],
            'data': {'작업 시간표': [{'시작 시간': '17:00'}]},
        }
        markup = original_form_markup(form)
        self.assertIn('data-role="section-heading">세부 작업 절차</th>', markup)

    def test_result_photo_fields_are_inlined_without_standalone_columns(self):
        form = {
            'title': '작업결과서',
            'sections': [{
                'title': '작업 결과',
                'multiple': True,
                'fields': [
                    {'label': '작업 전', 'type': 'textarea'},
                    {'label': '작업 후', 'type': 'textarea'},
                    {'label': '작업 전 사진', 'type': 'image'},
                    {'label': '작업 후 사진', 'type': 'image'},
                ],
            }],
            'data': {
                '작업 결과': [{
                    '작업 전': '변경 전',
                    '작업 후': '변경 후',
                    '작업 전 사진': ['/api/uploads/before.png'],
                    '작업 후 사진': ['/api/uploads/after.png'],
                }],
            },
        }
        markup = original_form_markup(form)
        self.assertNotIn('<th>작업 전 사진</th>', markup)
        self.assertNotIn('<th>작업 후 사진</th>', markup)
        self.assertIn('/api/uploads/before.png', markup)
        self.assertIn('/api/uploads/after.png', markup)
