"""Readable SR workbooks and a portable bundle of their original attachments."""
from __future__ import annotations

import io
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import SpooledTemporaryFile
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import html
from markdown_it import MarkdownIt
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.page import PageMargins
from PIL import Image, ImageOps, UnidentifiedImageError

from app.models.sr.service_request import IMPACT_SCOPE_LABEL, REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL, SR_STATUS_LABEL
from app.services.sr.export_labels import DETAIL_LABELS, DETAIL_OPTIONS
from app.utils.time import KST

UPLOAD_ROOT = Path('/app/uploads')
XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
NAVY, BLUE, PALE, INK, MUTED = '243C5A', '365F91', 'EEF3F8', '243447', '64748B'
LINE = Side(style='thin', color='DCE4ED')
REVIEW_LABELS = {'APPROVED': '승인', 'REJECTED': '반려', 'ON_HOLD': '보류', 'PENDING_INFO': '추가 확인 요청'}
FIELD_LABELS = {
    'ASSIGNEE_CHANGE': '담당자', 'planned_start_date': '처리 예정 시작일',
    'deployment_required': '배포 필요', 'security_review_required': '보안 검토 필요',
    'title': '제목', 'description': '요청 내용', 'background': '요청 배경', 'purpose': '요청 목적',
    'desired_due_date': '희망 완료일', 'desired_deploy_date': '희망 배포일', 'planned_due_date': '완료 목표일',
    'priority': '중요도', 'impact_scope': '영향 범위', 'is_urgent': '긴급 여부', 'urgent_reason': '긴급 사유',
    'related_system': '관련 시스템', 'related_menu': '관련 메뉴', 'related_url': '관련 URL',
    'completion_criteria': '완료 기준', 'note': '비고', 'requester_id': '요청자', 'assignee_id': '담당자',
    'requester_name': '요청자', 'requester_department': '요청 부서', 'requester_email': '이메일',
    'type_detail': '유형별 상세 내용', 'attachments': '첨부파일',
}


def clean(value):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value if value is not None else ''))


def safe_filename(value, fallback='첨부파일'):
    value = unicodedata.normalize('NFC', clean(value))
    value = re.sub(r'[<>:"/\\|?*\r\n\t]', '_', value).strip(' .')
    if not value:
        return fallback
    stem, suffix = str(Path(value).stem), Path(value).suffix[:16]
    return stem[:120] + suffix


def date_text(value, *, time=False):
    if not value:
        return '—'
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime('%Y-%m-%d %H:%M' if time else '%Y-%m-%d')
    except (TypeError, ValueError):
        return clean(value)


def rich_root(value):
    rendered = MarkdownIt('commonmark', {'html': True, 'breaks': True}).enable('table').render(clean(value))
    return html.fragment_fromstring(rendered, create_parent='div')


def plain_text(value):
    root = rich_root(value)
    for node in root.xpath('.//script|.//style'):
        node.drop_tree()
    for node in root.iterdescendants():
        if node.tag == 'img':
            node.tail = (' [이미지: 첨부파일 시트 참조] ' + (node.tail or ''))
        elif node.tag == 'br':
            node.tail = '\n' + (node.tail or '').lstrip('\n')
        elif node.tag == 'li':
            node.text = '• ' + (node.text or '')
        if node.tag in {'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'pre'}:
            node.tail = '\n' + (node.tail or '')
        elif node.tag in {'td', 'th'}:
            node.tail = '  |  ' + (node.tail or '')
    return re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', root.text_content()).strip()


def wrapped_lines(value, width=102):
    """Estimate Excel line wrapping including double-width Korean characters."""
    lines = []
    for raw in clean(value).split('\n'):
        line, used = '', 0
        for char in raw:
            size = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
            if used + size > width and line:
                lines.append(line)
                line, used = '', 0
            line += char
            used += size
        lines.append(line)
    return lines or ['—']


@dataclass
class Attachment:
    number: int
    name: str
    path: Path | None
    sources: list[str] = field(default_factory=list)
    image: bool = False
    warning: str = ''
    preview: bytes | None = None
    size: int = 0
    bundled: bool = False

    @property
    def archive_name(self):
        return f'첨부파일/{self.number:03d}_{safe_filename(self.name)}'


class Attachments:
    def __init__(self):
        self.items = []
        self.by_key = {}

    def add(self, source, attachment=None, url=None):
        attachment = attachment or {}
        raw_url = url or attachment.get('url', '')
        try:
            parsed = urlsplit(raw_url)
        except ValueError:
            parsed = urlsplit('')
        relative = unquote(parsed.path)
        match = re.fullmatch(r'/(?:api/)?uploads/(sr|pm)/([\w.\-]+)', relative) if not parsed.netloc and not parsed.scheme else None
        file_id = attachment.get('file_id', '')
        if match:
            relative = f'{match[1]}/{match[2]}'
        elif file_id and re.fullmatch(r'[\w.\-]+', file_id) and file_id not in ('.', '..'):
            relative = f'sr/{file_id}'
        else:
            relative = ''
        path = (UPLOAD_ROOT / relative).resolve() if relative else None
        if path and (not path.is_relative_to(UPLOAD_ROOT.resolve()) or not path.is_file()):
            path = None
        key = relative or raw_url or f'unknown-{len(self.items)}'
        if key in self.by_key:
            item = self.by_key[key]
            if source not in item.sources:
                item.sources.append(source)
            return item
        name = attachment.get('original_name') or Path(relative or parsed.path).name or '이미지'
        is_image = bool(url) or attachment.get('content_type', '').startswith('image/') or Path(name).suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
        item = Attachment(len(self.items) + 1, name, path, [source], is_image)
        if path is None:
            item.warning = '외부 이미지는 포함되지 않았습니다.' if parsed.netloc else '원본 파일을 찾을 수 없습니다.'
        self.by_key[key] = item
        self.items.append(item)
        return item

    def scan(self, value, source):
        if isinstance(value, dict):
            for key, text in value.items():
                self.scan(text, f'{source} · {DETAIL_LABELS.get(key, key)}')
        elif isinstance(value, list):
            for index, text in enumerate(value, 1):
                self.scan(text, f'{source} {index}')
        elif isinstance(value, str):
            for node in rich_root(value).xpath('.//img[@src]'):
                self.add(source, url=node.get('src'))

    def prepare(self, archive):
        for item in self.items:
            if item.path is None:
                continue
            try:
                item.size = item.path.stat().st_size
                # Original files are streamed into the temporary ZIP rather than read all at once.
                archive.write(item.path, item.archive_name)
                item.bundled = True
            except OSError:
                item.warning = '원본 파일을 읽을 수 없습니다.'
                continue
            if not item.image:
                continue
            try:
                with Image.open(item.path) as source:
                    source.seek(0)
                    preview = ImageOps.exif_transpose(source)
                    preview.thumbnail((1600, 1600))
                    preview = preview.convert('RGBA')
                    buf = io.BytesIO()
                    preview.save(buf, format='PNG')
                    item.preview = buf.getvalue()
            except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
                item.warning = '이미지 미리보기를 만들 수 없습니다. 첨부한 원본 파일을 확인해 주세요.'


class ReportSheet:
    def __init__(self, wb, name, sr_no, title):
        self.ws = wb.create_sheet(name)
        self.row = 1
        ws = self.ws
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.sheet_properties.tabColor = BLUE
        ws.page_setup.orientation = 'portrait'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins = PageMargins(left=.3, right=.3, top=.4, bottom=.4, header=.15, footer=.2)
        ws.oddFooter.center.text = '페이지 &P / &N'
        ws.oddFooter.right.text = clean(sr_no).replace('&', '&&')
        ws.print_options.horizontalCentered = True
        ws.freeze_panes = 'A5'
        ws.print_title_rows = '1:3'
        for col in range(1, 9):
            ws.column_dimensions[get_column_letter(col)].width = 13
        self.band(f'{sr_no}  ·  {name}', bg=NAVY, fg='FFFFFF', size=12, height=30)
        self.band(title, size=19, height=max(42, len(wrapped_lines(title, 70)) * 25))
        self.band(' | '.join(['요청정보', '상세내용', '댓글', '상태이력', '필드변경이력', '첨부파일']), fg=MUTED, size=9, height=24)
        self.row += 1

    def cell(self, row, first, last, value, *, bg=None, fg=INK, size=11, bold=False):
        ws = self.ws
        if last > first:
            ws.merge_cells(start_row=row, start_column=first, end_row=row, end_column=last)
        cell = ws.cell(row, first, clean(value))
        cell.data_type = 's'  # Uploaded text beginning with '=' must remain text, never a formula.
        cell.font = Font(name='맑은 고딕', size=size, color=fg, bold=bold)
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        for col in range(first, last + 1):
            c = ws.cell(row, col)
            if bg:
                c.fill = PatternFill('solid', fgColor=bg)
            c.border = Border(bottom=LINE)
        return cell

    def band(self, value, *, bg=None, fg=INK, size=11, height=28):
        cell = self.cell(self.row, 1, 8, value, bg=bg, fg=fg, size=size, bold=True)
        self.ws.row_dimensions[self.row].height = max(height, len(wrapped_lines(value, int(102 * 11 / size))) * (size + 6) + 12)
        self.row += 1
        return cell

    def section(self, title):
        self.row += 1
        self.band(title, bg=PALE, fg=BLUE, height=30)

    def pairs(self, left, right):
        for first, (label, value) in ((1, left), (5, right)):
            self.cell(self.row, first, first, label, bg=PALE, fg=MUTED, size=10, bold=True)
            self.cell(self.row, first + 1, first + 3, value or '—')
        lines = max(max(len(wrapped_lines(v or '—', 36)), len(wrapped_lines(label, 12))) for label, v in (left, right))
        self.ws.row_dimensions[self.row].height = max(36, lines * 17 + 12)
        self.row += 1

    def text(self, value):
        lines = wrapped_lines(value or '—')
        for start in range(0, len(lines), 12):
            part = lines[start:start + 12]
            self.cell(self.row, 1, 8, '\n'.join(part))
            self.ws.row_dimensions[self.row].height = max(30, len(part) * 17 + 14)
            self.row += 1

    def detail(self, label, value):
        if value is None or value == '':
            return
        self.section(label)
        self.text(plain_text(value))

    def table(self, headers, rows, spans=None):
        spans = spans or [8 // len(headers)] * len(headers)
        spans[-1] += 8 - sum(spans)
        first, columns = 1, []
        for span, header in zip(spans, headers):
            columns.append((first, first + span - 1, span * 13 - 2))
            self.cell(self.row, first, first + span - 1, header, bg=BLUE, fg='FFFFFF', bold=True, size=10)
            first += span
        self.ws.row_dimensions[self.row].height = 32
        self.row += 1
        for index, values in enumerate(rows):
            wrapped = [wrapped_lines(value, width) for value, (_, _, width) in zip(values, columns)]
            for start in range(0, max(map(len, wrapped)), 12):
                height = 1
                for lines, (first, last, _) in zip(wrapped, columns):
                    chunk = lines[start:start + 12]
                    height = max(height, len(chunk))
                    self.cell(self.row, first, last, '\n'.join(chunk), bg='F6F8FB' if index % 2 == 0 else 'FFFFFF', size=10)
                self.ws.row_dimensions[self.row].height = max(32, height * 16 + 12)
                self.row += 1
        if not rows:
            self.text('등록된 내역이 없습니다.')

    def finish(self):
        self.ws.print_area = f'A1:H{self.row - 1}'


def build_workbook(doc, comments, histories, field_histories, attachments):
    wb = Workbook()
    wb.remove(wb.active)
    sr_no, title = doc.get('sr_no') or str(doc['_id']), doc.get('title') or 'SR 요청'
    sheets = {name: ReportSheet(wb, name, sr_no, title) for name in ('요청정보', '상세내용', '댓글', '상태이력', '필드변경이력', '첨부파일')}
    info = sheets['요청정보']
    info.section('요청 개요')
    for left, right in (
        (('상태', SR_STATUS_LABEL.get(doc.get('status'), doc.get('status'))), ('중요도', SR_PRIORITY_LABEL.get(doc.get('priority'), '—'))),
        (('요청자', doc.get('requester_name')), ('요청 부서', doc.get('requester_department'))),
        (('요청 유형', REQUEST_TYPE_LABEL.get(doc.get('request_type'), '—')), ('담당자', doc.get('assignee_name'))),
        (('관련 시스템', doc.get('related_system')), ('접수일', date_text(doc.get('created_at'), time=True))),
        (('희망 완료일', date_text(doc.get('desired_due_date'))), ('완료 목표일', date_text(doc.get('planned_due_date')))),
        (('실제 완료일', date_text(doc.get('actual_completed_at'))), ('최종 수정', date_text(doc.get('updated_at'), time=True))),
    ):
        info.pairs(left, right)
    info.detail('요청 내용', doc.get('description'))
    info.detail('처리 결과', doc.get('process_result'))
    info.detail('검토 결과', REVIEW_LABELS.get(doc.get('review_result'), doc.get('review_result')))
    info.detail('검토 의견', doc.get('review_comment'))
    info.detail('반려 사유', doc.get('reject_reason'))
    info.detail('보류 사유', doc.get('hold_reason'))
    info.detail('추가 확인 요청', doc.get('pending_info_content'))
    info.section('첨부파일')
    info.text(f'총 {len(attachments.items)}개 · 이미지와 파일 목록은 첨부파일 시트에서 확인할 수 있습니다.' if attachments.items else '첨부파일이 없습니다.')

    detail = sheets['상세내용']
    detail.section('추가 요청 정보')
    for key in ('background', 'purpose', 'related_menu', 'related_url', 'completion_criteria', 'urgent_reason', 'impact_if_not_processed', 'note'):
        detail.detail(FIELD_LABELS.get(key, {'impact_if_not_processed': '미처리 시 영향'}.get(key, key)), doc.get(key))
    detail.pairs(('영향 범위', IMPACT_SCOPE_LABEL.get(doc.get('impact_scope'), '—')), ('긴급 여부', '긴급' if doc.get('is_urgent') else '일반'))
    detail.pairs(('요청자 이메일', doc.get('requester_email')), ('희망 배포일', date_text(doc.get('desired_deploy_date'))))
    detail.pairs(('작업 시작일', date_text(doc.get('planned_start_date'))), ('예상 공수', doc.get('estimated_effort')))
    detail.pairs(('배포 필요', '예' if doc.get('deployment_required') else '아니요'), ('보안 검토 필요', '예' if doc.get('security_review_required') else '아니요'))
    for key, value in (doc.get('type_detail') or {}).items():
        if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
            keys = list(dict.fromkeys(k for row in value for k in row))
            detail.section(DETAIL_LABELS.get(key, key))
            # Wide tables stay readable and retain every column, even for legacy fields.
            for start in range(0, len(keys), 6):
                subset = keys[start:start + 6]
                detail.table([DETAIL_LABELS.get(k, k) for k in subset], [[plain_text(row.get(k, '')) for k in subset] for row in value])
        else:
            mapped = DETAIL_OPTIONS.get(doc.get('request_type'), {}).get(key, {}).get(str(value), value)
            detail.detail(DETAIL_LABELS.get(key, key), mapped)

    sheet = sheets['댓글']
    positions = {str(comment.get('_id')): i for i, comment in enumerate(comments, 1) if comment.get('_id')}
    for index, comment in enumerate(comments, 1):
        parent = positions.get(str(comment.get('parent_id')))
        kind = '내부 메모' if comment.get('is_internal') else '댓글'
        sheet.section(f'{index:02d} · {comment.get("writer_name", "")} · {kind}' + (f' · #{parent} 답글' if parent else ''))
        sheet.text(date_text(comment.get('created_at'), time=True))
        sheet.text(plain_text(comment.get('content')) or '첨부파일만 등록된 댓글입니다.')
        related = [item for item in attachments.items if any(s.startswith(f'댓글 {index} ·') for s in item.sources)]
        if related:
            sheet.text('\n'.join(f'첨부 #{item.number} · {item.name}' for item in related))
    if not comments:
        sheet.text('등록된 댓글이 없습니다.')

    sheets['상태이력'].table(['변경 일시', '상태 변경', '변경자', '사유'], [
        [date_text(h.get('changed_at'), time=True), f'{SR_STATUS_LABEL.get(h.get("previous_status"), h.get("previous_status") or "—")} → {SR_STATUS_LABEL.get(h.get("new_status"), h.get("new_status") or "—")}', h.get('changed_by', ''), plain_text(h.get('reason'))]
        for h in histories], [2, 2, 1, 3])
    sheets['필드변경이력'].table(['변경 일시 / 변경자', '변경 항목', '이전 내용', '변경 내용'], [
        [f'{date_text(h.get("changed_at"), time=True)}\n{h.get("changed_by", "")}', FIELD_LABELS.get(h.get('action_type', '').removeprefix('FIELD_CHANGE:'), h.get('action_type', '')),
         plain_text(h.get('before_value')), plain_text(h.get('after_value'))] for h in field_histories], [2, 2, 2, 2])

    sheet = sheets['첨부파일']
    sheet.section('파일 목록')
    sheet.text('ZIP 압축을 풀면 엑셀과 첨부파일 폴더가 함께 나옵니다. 원본 파일은 첨부파일 폴더에 있습니다.' if attachments.items else '첨부파일이 없습니다.')
    for item in attachments.items:
        sheet.section(f'#{item.number} · {item.name}')
        sheet.text('등록 위치: ' + ', '.join(item.sources))
        if item.bundled:
            cell = sheet.cell(sheet.row, 1, 8, item.archive_name, fg=BLUE)
            cell.hyperlink = item.archive_name
            sheet.ws.row_dimensions[sheet.row].height = max(30, len(wrapped_lines(item.archive_name)) * 17 + 12)
            sheet.row += 1
        if item.warning:
            sheet.text('확인 필요: ' + item.warning)
    for item in attachments.items:
        if item.preview is None:
            continue
        sheet.ws.row_breaks.append(Break(id=sheet.row - 1))
        sheet.section(f'이미지 #{item.number} · {item.name}')
        sheet.text(' · '.join(item.sources))
        picture = ExcelImage(io.BytesIO(item.preview))
        ratio = min(1, 740 / picture.width, 600 / picture.height)
        picture.width, picture.height = picture.width * ratio, picture.height * ratio
        sheet.ws.add_image(picture, f'A{sheet.row}')
        count = math.ceil(picture.height / 20) + 1
        for row in range(sheet.row, sheet.row + count):
            sheet.ws.row_dimensions[row].height = 15
        sheet.row += count + 1
    for sheet in sheets.values():
        sheet.finish()
    return wb


def export_detail(doc, comments, histories, field_histories):
    attachments = Attachments()
    for item in doc.get('attachments') or []:
        attachments.add('요청 첨부파일', item)
    for index, comment in enumerate(comments, 1):
        source = f'댓글 {index} · {comment.get("writer_name", "")}'
        for item in comment.get('attachments') or []:
            attachments.add(source, item)
        attachments.scan(comment.get('content'), source)
    for key in ('description', 'background', 'purpose', 'process_result', 'review_comment', 'type_detail', 'note'):
        attachments.scan(doc.get(key), FIELD_LABELS.get(key, {'process_result': '처리 결과', 'review_comment': '검토 의견'}.get(key, key)))
    name = 'SR상세_' + safe_filename(doc.get('sr_no') or str(doc['_id']))
    output = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode='w+b')
    workbook = None
    try:
        if attachments.items:
            with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
                attachments.prepare(archive)
                workbook = build_workbook(doc, comments, histories, field_histories, attachments)
                with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode='w+b') as excel:
                    workbook.save(excel)
                    excel.seek(0)
                    with archive.open(name + '.xlsx', 'w', force_zip64=True) as member:
                        while chunk := excel.read(1024 * 1024):
                            member.write(chunk)
            media_type, extension = 'application/zip', '.zip'
        else:
            workbook = build_workbook(doc, comments, histories, field_histories, attachments)
            workbook.save(output)
            media_type, extension = XLSX_TYPE, '.xlsx'
        output.seek(0)
        return output, name + extension, media_type, sum(bool(item.warning) for item in attachments.items)
    except Exception:
        output.close()
        raise
    finally:
        if workbook:
            workbook.close()


def stream_export(output):
    try:
        while chunk := output.read(1024 * 1024):
            yield chunk
    finally:
        output.close()
