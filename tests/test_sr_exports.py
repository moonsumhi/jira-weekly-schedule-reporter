"""Exercise SR download routes and generated workbooks without accessing MongoDB."""
import io
import unittest
import tempfile
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import unquote

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.sr import admin_requests
from app.services.sr import excel_export


class SRExportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.uploads = tempfile.TemporaryDirectory()
        self.addCleanup(self.uploads.cleanup)
        self.upload_root = Path(self.uploads.name)
        (self.upload_root / 'sr').mkdir()
        (self.upload_root / 'pm').mkdir()
        root_patch = patch.object(excel_export, 'UPLOAD_ROOT', self.upload_root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.sr_id = str(ObjectId())
        self.user = UserPublic(id=str(ObjectId()), email='export@example.com', is_admin=True)
        self.doc = {'_id': ObjectId(self.sr_id), 'sr_no': 'SR-2026-0176', 'title': '서버 점검 요청',
                    'status': 'CLOSED', 'request_type': 'SERVER_INFRA', 'priority': 'MEDIUM',
                    'requester_name': '김요청', 'requester_department': '운영팀',
                    'description': '한글 요청 내용\n두 번째 줄', 'process_result': '처리 완료',
                    'requester_id': str(ObjectId()), 'requester_email': 'requester@example.com',
                    'is_urgent': False, 'compliance_related': False, 'created_by': '김요청', 'updated_by': '김처리',
                    'updated_at': datetime(2026, 9, 17, tzinfo=timezone.utc),
                    'created_at': datetime(2026, 9, 17, tzinfo=timezone.utc)}
        def collection(rows):
            cursor = SimpleNamespace(to_list=AsyncMock(return_value=rows))
            cursor.sort = Mock(return_value=cursor)
            return SimpleNamespace(find=Mock(return_value=cursor))
        self.service = collection([self.doc])
        self.service.find_one = AsyncMock(return_value=self.doc)
        self.db = {
            M.SERVICE_REQUESTS: self.service,
            M.SR_COMMENTS: collection([{'writer_name': '김처리', 'content': '댓글 내용', 'is_internal': True}]),
            M.SR_STATUS_HISTORIES: collection([{'previous_status': 'IN_PROGRESS', 'new_status': 'CLOSED', 'reason': '확인 완료'}]),
            M.SR_HISTORIES: collection([{'action_type': 'FIELD_CHANGE:title', 'before_value': '이전 제목', 'after_value': '서버 점검 요청'}]),
        }
        self.db_patch = patch.object(M, 'get_db', return_value=self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        app = FastAPI()
        app.include_router(admin_requests.router, prefix='/admin/schedule/service-requests')
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url='http://test')
        self.addAsyncCleanup(self.client.aclose)

    async def download(self, path):
        response = await self.client.get('/admin/schedule/service-requests' + path)
        self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
        self.assertEqual(response.headers['content-type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        disposition = response.headers['content-disposition']
        self.assertTrue(disposition.isascii())
        filename = unquote(disposition.split("filename*=UTF-8''", 1)[1])
        workbook = load_workbook(io.BytesIO(response.content))
        self.addCleanup(workbook.close)
        return filename, workbook

    @staticmethod
    def text(sheet):
        return '\n'.join(str(cell.value) for row in sheet for cell in row if cell.value is not None)

    def file(self, name, content=b'original document', image=False, folder='sr'):
        stored = str(ObjectId()) + Path(name).suffix
        path = self.upload_root / folder / stored
        if image:
            Image.new('RGB', (1200, 700), '#356595').save(path)
        else:
            path.write_bytes(content)
        return {'file_id': stored, 'original_name': name, 'url': f'/api/uploads/{folder}/{stored}',
                'size': path.stat().st_size, 'content_type': 'image/png' if image else 'application/octet-stream'}

    async def bundle(self):
        response = await self.client.get(f'/admin/schedule/service-requests/{self.sr_id}/export')
        self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
        self.assertEqual(response.headers['content-type'], 'application/zip')
        archive = ZipFile(io.BytesIO(response.content))
        self.addCleanup(archive.close)
        workbook_name = next(name for name in archive.namelist() if name.endswith('.xlsx') and '/' not in name)
        workbook = load_workbook(io.BytesIO(archive.read(workbook_name)))
        self.addCleanup(workbook.close)
        return response, archive, workbook

    async def test_detail_export_has_one_request_sheet_without_processing_comments_or_history(self):
        self.doc.update(related_system='업무 시스템', background='요청 배경 설명', note='요청 비고',
                        review_comment='검토 의견 비공개', reject_reason='반려 사유 비공개')
        original = deepcopy(self.doc)
        filename, workbook = await self.download(f'/{self.sr_id}/export')
        self.assertEqual(filename, 'SR상세_SR-2026-0176.xlsx')
        self.assertEqual(workbook.sheetnames, ['요청 내용'])
        info = self.text(workbook.active)
        self.assertIn(self.doc['title'], info)
        self.assertIn(self.doc['description'], info)
        for expected in ('업무 시스템', '요청 배경 설명', '요청 비고'):
            self.assertIn(expected, info)
        for excluded in ('처리 완료', '댓글 내용', '내부 메모', '확인 완료', '이전 제목', '검토 의견 비공개', '반려 사유 비공개', '김요청', '김처리'):
            self.assertNotIn(excluded, info)
        for name in (M.SR_COMMENTS, M.SR_STATUS_HISTORIES, M.SR_HISTORIES):
            self.db[name].find.assert_not_called()
        for sheet in workbook:
            self.assertFalse(sheet.sheet_view.showGridLines)
            self.assertEqual(sheet.freeze_panes, 'A5')
            self.assertEqual(sheet.page_setup.fitToWidth, 1)
            self.assertTrue(sheet.print_area)
            self.assertTrue(sheet.merged_cells.ranges)
        self.assertEqual(self.doc, original)

    async def test_request_images_and_files_share_one_sheet_and_comment_files_are_excluded(self):
        image = self.file('점검 화면.png', image=True)
        first = self.file('작업 자료.pdf', b'first PDF')
        second = self.file('작업 자료.pdf', b'second PDF')
        self.doc['attachments'] = [image, first]
        comments = self.db[M.SR_COMMENTS].find.return_value.to_list.return_value
        comments[0]['attachments'] = [second, image]
        self.doc['description'] = f"# 작업 요청\n내용 **확인**\n![점검]({image['url']})"
        response, archive, workbook = await self.bundle()
        files = [name for name in archive.namelist() if name.startswith('첨부파일/')]
        self.assertEqual(len(files), 2)
        self.assertEqual(len(set(files)), 2)
        self.assertIn(b'first PDF', [archive.read(name) for name in files])
        self.assertNotIn(b'second PDF', [archive.read(name) for name in files])
        self.assertEqual(response.headers['x-export-warnings'], '0')
        self.assertEqual(workbook.sheetnames, ['요청 내용'])
        self.assertEqual(len(workbook.active._images), 1)
        self.assertNotIn('댓글 1', self.text(workbook.active))
        self.assertIn('내용 확인', self.text(workbook.active))
        self.assertNotIn('![점검]', self.text(workbook.active))
        links = [c.hyperlink.target for row in workbook.active for c in row if c.hyperlink]
        self.assertEqual(links, [name for name in files if name.endswith('.pdf')])

    async def test_inline_pm_html_images_and_gif_webp_are_embedded(self):
        inline = self.file('본문.png', image=True, folder='pm')
        self.doc['description'] = f'<p>본문 설명<br>다음 줄</p><img src="{inline["url"]}">'
        attachments = []
        for extension in ('gif', 'webp'):
            item = self.file(f'화면.{extension}', b'')
            Image.new('RGB', (90, 45), 'blue').save(self.upload_root / 'sr' / item['file_id'])
            item['content_type'] = 'image/' + extension
            attachments.append(item)
        self.doc['attachments'] = attachments
        _, workbook = await self.download(f'/{self.sr_id}/export')
        self.assertEqual(workbook.sheetnames, ['요청 내용'])
        self.assertEqual(len(workbook.active._images), 3)
        self.assertNotIn('<p>', self.text(workbook.active))
        self.assertIn('본문 설명\n다음 줄', self.text(workbook.active))

    async def test_missing_broken_and_external_images_are_reported_without_losing_export(self):
        broken = self.file('깨진 이미지.png', b'not an image')
        broken['content_type'] = 'image/png'
        self.doc['attachments'] = [broken, {'file_id': 'missing.pdf', 'original_name': '없는 문서.pdf'}]
        self.doc['description'] = '![외부](https://example.invalid/private.png)'
        response, archive, workbook = await self.bundle()
        self.assertEqual(response.headers['x-export-warnings'], '3')
        self.assertIn(b'not an image', [archive.read(name) for name in archive.namelist()])
        text = self.text(workbook.active)
        self.assertIn('원본 파일을 찾을 수 없습니다', text)
        self.assertIn('이미지 미리보기를 만들 수 없습니다', text)
        self.assertIn('외부 이미지는 포함되지 않았습니다', text)
        self.assertNotIn('처리 완료', text)

    async def test_type_details_tables_long_text_and_formula_input_are_preserved(self):
        self.doc['title'] = '=HYPERLINK("https://example.invalid", "do not run")'
        self.doc['description'] = '한글 설명과 줄바꿈을 모두 보존합니다. ' * 2000
        self.doc['type_detail'] = {'targetServer': 'server-01', 'workType': 'restart',
                                  'verificationMethod': '**재기동** 후 서비스 확인',
                                  'firewallRules': [{'sourceIp': '10.0.0.1', 'destinationIp': '10.0.0.2', 'portProtocol': 'TCP/443'}]}
        _, workbook = await self.download(f'/{self.sr_id}/export')
        text = self.text(workbook.active)
        for expected in ('대상 서버 / 시스템', '서버 재기동', '재기동 후 서비스 확인', '출발지 IP / 대역', 'TCP/443'):
            self.assertIn(expected, text)
        self.assertIn(self.doc['description'].replace('\n', '').strip(), text.replace('\n', ''))
        for sheet in workbook:
            for row in sheet:
                self.assertTrue(all(cell.data_type != 'f' for cell in row))
            self.assertTrue(all((dimension.height or 0) <= 409 for dimension in sheet.row_dimensions.values()))

    async def test_embedded_image_keeps_its_position_between_text_and_is_not_repeated_as_attachment(self):
        image = self.file('본문 이미지.png', image=True)
        self.doc['attachments'] = [image]
        self.doc['description'] = f"이미지 위 설명\n\n![점검]({image['url']})\n\n이미지 아래 설명"
        _, workbook = await self.download(f'/{self.sr_id}/export')
        sheet = workbook.active
        self.assertEqual(len(sheet._images), 1)
        picture = sheet._images[0]
        above = next(c.row for row in sheet for c in row if c.value == '이미지 위 설명')
        below = next(c.row for row in sheet for c in row if c.value == '이미지 아래 설명')
        image_row = picture.anchor._from.row + 1
        self.assertLess(above, image_row)
        self.assertLess(image_row, below)
        self.assertGreaterEqual(sum(sheet.row_dimensions[r].height or 15 for r in range(image_row, below)) * 4 / 3,
                                picture.anchor.ext.cy / 9525)
        with Image.open(io.BytesIO(picture._data())) as embedded:
            self.assertEqual(embedded.getpixel((0, 0))[:3], (53, 101, 149))
        self.assertNotIn('첨부파일', self.text(sheet))

    async def test_processing_and_comment_images_do_not_change_request_only_download(self):
        image = self.file('처리 증적.png', image=True)
        self.doc['process_result'] = f"![처리 결과]({image['url']})"
        self.doc['review_comment'] = f"![검토]({image['url']})"
        self.db[M.SR_COMMENTS].find.return_value.to_list.return_value[0]['attachments'] = [image]
        _, workbook = await self.download(f'/{self.sr_id}/export')
        self.assertEqual(workbook.sheetnames, ['요청 내용'])
        self.assertEqual(len(workbook.active._images), 0)

    async def test_request_field_order_editor_label_options_and_html_table(self):
        self.doc['request_type'] = 'IMPROVEMENT'
        self.doc['description'] = '<p>개선 설명</p><table><tr><th>항목</th><th>기준</th></tr><tr><td>응답 시간</td><td>3초</td></tr></table><p>표 아래 설명</p>'
        self.doc['type_detail'] = {'expectedEffect': '조회 시간 단축', 'currentProblem': '현재 속도가 느림'}
        _, workbook = await self.download(f'/{self.sr_id}/export')
        text = self.text(workbook.active)
        for value in ('개선 요청 내용', '개선 설명', '응답 시간', '3초', '표 아래 설명'):
            self.assertIn(value, text)
        self.assertLess(text.index('현재 속도가 느림'), text.index('개선 설명'))
        self.assertLess(text.index('표 아래 설명'), text.index('조회 시간 단축'))

    async def test_firewall_and_user_tables_retain_every_request_column(self):
        self.doc['request_type'] = 'FIREWALL'
        self.doc['description'] = None
        self.doc['type_detail'] = {'requestKind': 'new', 'environment': 'production',
            'firewallRules': [{'sourceIp': '192.0.2.10', 'sourceHost': 'WEB-01', 'destinationIp': '192.0.2.20',
                               'destinationHost': 'DB-01', 'portProtocol': 'TCP/443', 'portPurpose': '웹 서비스'}],
            'purpose': '업무 연계', 'direction': 'inbound', 'duration': 'temporary', 'expiryDate': '2026-10-01'}
        _, workbook = await self.download(f'/{self.sr_id}/export')
        text = self.text(workbook.active)
        for value in ('신규 오픈', '운영', '192.0.2.10', 'WEB-01', '192.0.2.20', 'DB-01', 'TCP/443', '웹 서비스', '업무 연계', '2026-10-01'):
            self.assertIn(value, text)
        self.doc['request_type'] = 'BACKOFFICE_EAA'
        self.doc['type_detail'] = {'researchNumber': '연구-2026', 'mappedVmInfo': 'VM-01',
                                   'userList': [{'name': '사용자 A', 'email': 'a@example.com', 'note': '계정 메모'}], 'etc': '추가 요청'}
        _, workbook = await self.download(f'/{self.sr_id}/export')
        text = self.text(workbook.active)
        for value in ('연구-2026', 'VM-01', '사용자 A', 'a@example.com', '계정 메모', '추가 요청'):
            self.assertIn(value, text)

    async def test_request_datetime_matches_local_input_and_converts_explicit_timezone(self):
        for value in ('2026-09-18T07:00', '2026-09-17T22:00:00Z'):
            self.doc['type_detail'] = {'workDatetime': value}
            _, workbook = await self.download(f'/{self.sr_id}/export')
            self.assertIn('2026-09-18 07:00', self.text(workbook.active))

    async def test_attachment_paths_stay_inside_uploads_and_archive_names_are_safe(self):
        outside = self.upload_root.parent / (self.upload_root.name + '-secret.txt')
        outside.write_text('must not export')
        self.addCleanup(outside.unlink)
        (self.upload_root / 'sr' / 'escape.txt').symlink_to(outside)
        safe = self.file('../../동일\\파일.pdf', b'safe original')
        self.doc['attachments'] = [safe,
            {'file_id': '../' + outside.name, 'original_name': '../../secret.txt'},
            {'file_id': 'escape.txt', 'original_name': 'symlink.txt'}]
        response, archive, _ = await self.bundle()
        self.assertEqual(response.headers['x-export-warnings'], '2')
        for name in archive.namelist():
            self.assertFalse(name.startswith('/'))
            self.assertNotIn('..', Path(name).parts)
            self.assertNotIn('\\', name)
            self.assertNotEqual(archive.read(name), b'must not export')

    async def test_list_export_reaches_static_route_and_downloads_workbook(self):
        filename, workbook = await self.download('/export')
        self.assertTrue(filename.startswith('SR목록_'))
        self.assertEqual(workbook.sheetnames, ['SR목록'])
        self.assertEqual(workbook.active['A2'].value, self.doc['sr_no'])
        self.assertEqual(workbook.active['B2'].value, self.doc['title'])
        self.service.find_one.assert_not_awaited()

    async def test_filename_with_unicode_and_delimiters_remains_one_safe_header(self):
        self.doc['sr_no'] = 'SR-한글 "검토"; ✓\r\n예시'
        filename, _ = await self.download(f'/{self.sr_id}/export')
        self.assertEqual(filename, 'SR상세_SR-한글 _검토_; ✓__예시.xlsx')

    async def test_export_permissions_are_unchanged(self):
        self.user.is_admin = False
        self.user.permissions = ['sr_manager']
        for path in ('/export', f'/{self.sr_id}/export'):
            response = await self.client.get('/admin/schedule/service-requests' + path)
            self.assertEqual(response.status_code, 403, response.text)
        self.service.find_one.assert_not_awaited()
        self.service.find.assert_not_called()

    async def test_invalid_or_missing_sr_returns_json_error(self):
        response = await self.client.get('/admin/schedule/service-requests/not-an-id/export')
        self.assertEqual(response.status_code, 400)
        self.service.find_one.return_value = None
        response = await self.client.get(f'/admin/schedule/service-requests/{self.sr_id}/export')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('content-disposition', response.headers)

    async def test_detail_json_route_still_resolves_after_static_export_route(self):
        response = await self.client.get(f'/admin/schedule/service-requests/{self.sr_id}')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['sr_no'], self.doc['sr_no'])
