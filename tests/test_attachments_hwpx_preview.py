import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi import HTTPException

from app.routers.attachments import hwpx_preview
from app.utils.hwpx_preview import render_hwpx_preview


class HwpxPreviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'sample.hwpx'

    def document(self, sections, extra=None):
        with ZipFile(self.path, 'w') as archive:
            for name, content in {**sections, **(extra or {})}.items():
                archive.writestr(name, content)

    async def test_renders_text_merged_table_image_and_sandbox_headers(self):
        self.document({'Contents/section0.xml': '''<sec><p><t>한글 &lt;script&gt;<lineBreak/>다음 줄</t></p>
          <tbl><tr><tc><cellSpan colSpan="2" rowSpan="1"/><p><t>표 내용</t></p></tc></tr></tbl>
          <pic><img binaryItemIDRef="image1"/></pic></sec>'''}, {
            'Contents/content.hpf': '<package><item id="image1" href="BinData/image1.png"/></package>',
            'BinData/image1.png': b'\x89PNG\r\n\x1a\nimage',
        })
        with patch('app.routers.attachments.UPLOADS_ROOT', Path(self.directory.name)):
            response = await hwpx_preview('sample.hwpx')
        html = response.body.decode()
        self.assertIn('한글 &lt;script&gt;<br>다음 줄', html)
        self.assertIn('colspan="2"', html)
        self.assertIn('표 내용', html)
        self.assertIn('src="data:image/png;base64,', html)
        self.assertIn('sandbox', response.headers['content-security-policy'])

    def test_sections_use_numeric_order_and_namespace_prefixes(self):
        self.document({f'Contents/section{number}.xml':
            f'<hp:sec xmlns:hp="urn:test"><hp:p><hp:t>section-{number}</hp:t></hp:p></hp:sec>'
            for number in (10, 2, 0)})
        html = render_hwpx_preview(self.path)
        self.assertLess(html.index('section-0'), html.index('section-2'))
        self.assertLess(html.index('section-2'), html.index('section-10'))

    def test_rejects_xml_entities_and_expanded_size_limit(self):
        self.document({'Contents/section0.xml': '<!DOCTYPE sec [<!ENTITY x SYSTEM "file:///etc/passwd">]><sec><t>&x;</t></sec>'})
        with self.assertRaises(ValueError):
            render_hwpx_preview(self.path)
        self.document({'Contents/section0.xml': '<sec><t>text</t></sec>'})
        with patch('app.utils.hwpx_preview.MAX_XML_BYTES', 4), self.assertRaises(ValueError):
            render_hwpx_preview(self.path)

    async def test_corrupt_document_returns_readable_error(self):
        self.path.write_bytes(b'not a zip')
        with patch('app.routers.attachments.UPLOADS_ROOT', Path(self.directory.name)):
            with self.assertRaises(HTTPException) as error:
                await hwpx_preview('sample.hwpx')
        self.assertEqual(error.exception.status_code, 422)

    async def test_rejects_path_traversal(self):
        with self.assertRaises(HTTPException) as error:
            await hwpx_preview('../sample.hwpx')
        self.assertEqual(error.exception.status_code, 400)
