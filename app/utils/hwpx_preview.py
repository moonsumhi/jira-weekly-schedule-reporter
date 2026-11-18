"""Render HWPX content without executing document code or extracting ZIP paths."""
import base64
from html import escape
from pathlib import Path
import re
from zipfile import ZipFile

from lxml import etree

from app.utils.html_preview import HWP_BASE_CSS

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_XML_BYTES = 10 * 1024 * 1024


def render_hwpx_preview(path: Path) -> str:
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('HWPX 미리보기는 50MB 이하 파일만 지원합니다.')
    with ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(item.file_size for item in entries) > MAX_ARCHIVE_BYTES:
            raise ValueError('문서의 압축 해제 크기가 미리보기 한도를 초과합니다.')
        if len({item.filename for item in entries}) != len(entries):
            raise ValueError('문서에 중복된 파일 항목이 있습니다.')

        def xml(name):
            if archive.getinfo(name).file_size > MAX_XML_BYTES:
                raise ValueError('문서 XML이 미리보기 한도를 초과합니다.')
            parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
            root = etree.fromstring(archive.read(name), parser)
            if root.getroottree().docinfo.doctype:
                raise ValueError('DTD가 포함된 문서는 미리보기할 수 없습니다.')
            return root

        images = {}
        if 'Contents/content.hpf' in archive.namelist():
            for item in xml('Contents/content.hpf').iter():
                href = item.get('href', '')
                if item.get('id') and href.startswith(('BinData/', '../BinData/')):
                    name = href.removeprefix('../')
                    if '..' not in Path(name).parts and name in archive.namelist():
                        images[item.get('id')] = name

        rendered_image_bytes = 0

        def image(node):
            nonlocal rendered_image_bytes
            for child in node.iter():
                name = images.get(child.get('binaryItemIDRef'))
                if not name:
                    continue
                data = archive.read(name)
                rendered_image_bytes += len(data)
                if rendered_image_bytes > MAX_ARCHIVE_BYTES:
                    raise ValueError('문서 이미지가 미리보기 한도를 초과합니다.')
                mime = None
                if data.startswith(b'\x89PNG\r\n\x1a\n'):
                    mime = 'image/png'
                elif data.startswith(b'\xff\xd8\xff'):
                    mime = 'image/jpeg'
                elif data.startswith((b'GIF87a', b'GIF89a')):
                    mime = 'image/gif'
                elif data.startswith(b'BM'):
                    mime = 'image/bmp'
                elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
                    mime = 'image/webp'
                if mime:
                    encoded = base64.b64encode(data).decode('ascii')
                    return f'<img alt="문서 이미지" src="data:{mime};base64,{encoded}">'
            return '<span>[표시할 수 없는 이미지]</span>'

        def convert(node):
            if not isinstance(node.tag, str):
                return ''
            tag = etree.QName(node).localname
            if tag in ('secPr', 'linesegarray'):
                return ''
            if tag == 'pic':
                return image(node)
            if tag == 'lineBreak':
                return '<br>'
            if tag == 'tab':
                return '&#9;'
            content = escape(node.text or '') if tag == 't' else ''
            for child in node:
                content += convert(child)
                if tag == 't':
                    content += escape(child.tail or '')
            if tag == 'tc':
                attributes = ''
                for span in node:
                    if isinstance(span.tag, str) and etree.QName(span).localname == 'cellSpan':
                        for source, target in (('rowSpan', 'rowspan'), ('colSpan', 'colspan')):
                            value = span.get(source, '1')
                            if value.isdecimal() and 1 <= int(value) <= 1000:
                                attributes += f' {target}="{int(value)}"'
                return f'<td{attributes}>{content}</td>'
            # Paragraphs may contain tables, which cannot be nested in HTML <p>.
            markup = {'p': 'div', 'tbl': 'table', 'tr': 'tr'}.get(tag)
            return f'<{markup}>{content}</{markup}>' if markup else content

        sections = sorted(
            (name for name in archive.namelist() if re.fullmatch(r'Contents/section\d+\.xml', name)),
            key=lambda name: int(re.search(r'\d+', name).group()),
        )
        if not sections:
            raise ValueError('HWPX 문서의 본문을 찾을 수 없습니다.')
        body = ''.join(f'<section>{convert(xml(name))}</section>' for name in sections)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        + HWP_BASE_CSS
        + '<style>body{background:#fff}section{margin-bottom:24px}td{min-width:40px}'
        'div{min-height:1em;white-space:pre-wrap;overflow-wrap:anywhere}</style>'
        '</head><body>' + body + '</body></html>'
    )
