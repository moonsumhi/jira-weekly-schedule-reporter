"""Exercise SR download routes and generated workbooks without accessing MongoDB."""
import io
import unittest
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


class SRExportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
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

    async def test_detail_export_downloads_korean_filename_and_all_four_sheets(self):
        original = deepcopy(self.doc)
        filename, workbook = await self.download(f'/{self.sr_id}/export')
        self.assertEqual(filename, 'SR상세_SR-2026-0176.xlsx')
        self.assertEqual(workbook.sheetnames, ['요청정보', '댓글', '상태이력', '필드변경이력'])
        info = dict(workbook['요청정보'].values)
        self.assertEqual(info['제목'], self.doc['title'])
        self.assertEqual(info['요청내용'], self.doc['description'])
        self.assertEqual(workbook['댓글']['B2'].value, '댓글 내용')
        self.assertEqual(workbook['상태이력']['C2'].value, '확인 완료')
        self.assertEqual(workbook['필드변경이력']['B2'].value, '이전 제목')
        self.assertEqual(self.doc, original)

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
        self.assertEqual(filename, f"SR상세_{self.doc['sr_no']}.xlsx")

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
