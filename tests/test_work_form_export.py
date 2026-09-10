import io
import unittest
from zipfile import ZipFile

from lxml import etree

from app.services.work_form_export import original_form_markup
from app.services.work_documents import export_docx, export_hwp, export_hwpx
from app.models.form_entry import FormDocumentExport


class OriginalFormExportTests(unittest.TestCase):
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
