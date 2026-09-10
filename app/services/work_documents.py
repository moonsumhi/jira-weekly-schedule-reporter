"""Work documents: ordered Markdown import, durable snapshots and HWPX export."""
import base64
import io
import re
import subprocess
import tempfile
import uuid
from html import escape as escape_html
from pathlib import Path
from urllib.parse import unquote, urlparse
from zipfile import ZipFile

from lxml import html
from markdown_it import MarkdownIt
from PIL import Image

UPLOAD_ROOT = Path('/app/uploads')
DOCUMENT_SECTION = '문서 본문'


def escape(text: str) -> str:
    return re.sub(r'([\\`*_{}\[\]<>#+!|])', r'\\\1', text)


def store_image(raw: bytes) -> str:
    image = Image.open(io.BytesIO(raw))
    image.load()
    image.thumbnail((2400, 2400))
    output = io.BytesIO()
    image.save(output, format='PNG')
    directory = UPLOAD_ROOT / 'work_documents' / 'images'
    directory.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + '.png'
    (directory / name).write_bytes(output.getvalue())
    return '/api/uploads/work_documents/images/' + name


def html_markdown(source: str, image_reader) -> str:
    """Walk in document order, including images between text inside table cells."""
    root = html.fragment_fromstring(source, create_parent='div')

    def walk(node):
        if not isinstance(node.tag, str):
            return ''
        tag = node.tag.lower() if isinstance(node.tag, str) else ''
        if tag in ('script', 'style', 'head'):
            return ''
        if tag == 'img':
            src = node.get('src', '')
            return f'![사진](<{image_reader(src)}>)'
        if tag == 'br':
            return '\n'
        if tag == 'a':
            label = ''.join(node.itertext())
            href = node.get('href', '')
            if urlparse(href).scheme in ('http', 'https', 'mailto'):
                return f'[{escape(label)}](<{href.replace(">", "%3E").replace("<", "%3C")}>)'
            return escape(label)
        if tag == 'table':
            source_rows = node.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')
            if not source_rows:
                return ''
            cell_rows = [row.xpath('./td|./th') for row in source_rows]
            def label(cell):
                return re.sub(r'\s+', '', ''.join(cell.itertext()))
            # Omit only the cover approval table, keeping the document title.
            # Worker/reviewer tables in the body remain part of the document.
            cover_labels = {label(cell) for cell in cell_rows[0]}
            cover_title = next((value for value in cover_labels if re.fullmatch(
                r'작업(?:계획|결과)서(?:\(서비스(?:외)?\))?', value)), None)
            if (cover_title and {'작업자', '담당자', '데이터운영팀담당자', '데이터운영팀장'} <= cover_labels
                    and not node.xpath('preceding::table|ancestor::table')):
                return '\n\n# ' + cover_title + '\n\n'
            # These job forms use merged cells to arrange label/value pairs,
            # not an eleven-column dataset. Keep each value with its label.
            if cell_rows[0] and label(cell_rows[0][0]) == '작업명':
                labels = {'작업명', '작업일시', '서비스명', '회사명/성함/직책', '중요도', '목적', '구분', '서비스영향도'}
                parts = []
                for cells in cell_rows:
                    current, values = None, []
                    for cell in cells:
                        if label(cell) in labels:
                            if current is not None:
                                parts.extend([f'### {current}', (' ' if current == '구분' else '\n\n').join(values)])
                            current, values = ''.join(cell.itertext()).strip(), []
                        else:
                            values.append(walk(cell).strip())
                    if current is not None:
                        parts.extend([f'### {current}', (' ' if current == '구분' else '\n\n').join(values)])
                return '\n\n' + '\n\n'.join(parts) + '\n\n'
            # A nested test table cannot live inside a Markdown pipe-table cell.
            # Lift the containing record into a section so its text, pictures,
            # and inner tables remain in their original order.
            if node.xpath('.//table'):
                header = cell_rows[0]
                has_header = all(not cell.xpath('.//table|.//img') and len(label(cell)) < 40 for cell in header)
                headers = [walk(cell).strip() for cell in header] if has_header else []
                parts = []
                for index, cells in enumerate(cell_rows[1:] if has_header else cell_rows, 1):
                    parts.append(f'### {index}번째 항목')
                    compact = []
                    def flush():
                        if compact:
                            parts.append('| ' + ' | '.join(name for name, _ in compact) + ' |\n| ' + ' | '.join('---' for _ in compact) + ' |\n| ' + ' | '.join(value for _, value in compact) + ' |')
                            compact.clear()
                    for c, cell in enumerate(cells):
                        name = headers[c] if c < len(headers) else f'{c + 1}번째 내용'
                        value = walk(cell).strip()
                        if not cell.xpath('.//table|.//img') and len(value) < 160:
                            compact.append((name.replace('\n', ' '), value.replace('\n', '<br>')))
                        else:
                            flush()
                            parts.extend([f'#### {name}', value])
                    flush()
                return '\n\n' + '\n\n'.join(parts) + '\n\n'
            grid = {}
            owners = {}
            def span(cell, name):
                try:
                    return max(1, min(100, int(cell.get(name, '1'))))
                except ValueError:
                    return 1
            for r, row in enumerate(source_rows):
                c = 0
                for cell in row.xpath('./td|./th'):
                    colspan, rowspan = span(cell, 'colspan'), span(cell, 'rowspan')
                    while any((r, c + offset) in grid for offset in range(colspan)):
                        c += 1
                    # Paragraph boundaries must not become four line breaks per cell.
                    value = re.sub(r'\n[ \t]*\n+', '\n', walk(cell).strip()).replace('\n', '<br>')
                    value = re.sub(r'(?<!\\)\|', r'\\|', value)
                    for dr in range(min(rowspan, len(source_rows) - r)):
                        for dc in range(colspan):
                            grid[r + dr, c + dc] = value if dr == dc == 0 else ''
                            owners[r + dr, c + dc] = value
                    c += colspan
            if not grid:
                return ''
            width = max(c for _, c in grid) + 1
            rows = [[grid.get((r, c), '') for c in range(width)] for r in range(len(source_rows))]
            # Collapse the two-level headings used by target, time, and
            # before/after tables. The second row is a heading, not data.
            second_labels = {label(cell) for cell in cell_rows[1]} if len(cell_rows) > 1 else set()
            is_grouped_header = ({'IP', 'HOSTNAME'} <= second_labels or {'시작', '종료'} <= second_labels
                                 or {'작업전', '작업후'} <= second_labels)
            if is_grouped_header and len(rows) > 1:
                rows = [[owners.get((1, c), '') or owners.get((0, c), '') for c in range(width)]] + rows[2:]
                if {'시작', '종료'} <= second_labels:
                    for c, value in enumerate(rows[0]):
                        parent = owners.get((0, c), '')
                        if parent and parent != value:
                            rows[0][c] = parent + ' / ' + value
                if not rows[0][0] and {'IP', 'HOSTNAME'} <= second_labels:
                    rows[0][0] = 'No.'
            title = ''
            for c, value in enumerate(rows[0]):
                normalized = re.sub(r'\s+|<br>', '', value)
                if width > 1 and re.fullmatch(r'작업(?:계획|결과)서(?:\(서비스(?:외)?\))?', normalized):
                    title = '# ' + normalized + '\n\n'
                    rows = [row[:c] + row[c + 1:] for row in rows]
                    width -= 1
                    break
            result = ['| ' + ' | '.join(row) + ' |' for row in rows]
            result.insert(1, '| ' + ' | '.join(['---'] * width) + ' |')
            return '\n\n' + title + '\n'.join(result) + '\n\n'
        def text(value):
            # Ignore pretty-printed XHTML indentation between block elements.
            return '' if value and not value.strip() and '\n' in value else escape(value or '')
        value = text(node.text)
        for child in node:
            value += walk(child) + text(child.tail)
        if tag in ('strong', 'b'):
            return '**' + value + '**'
        if tag in ('em', 'i'):
            return '*' + value + '*'
        if re.fullmatch(r'h[1-6]', tag):
            return '\n\n' + '#' * int(tag[1]) + ' ' + value.strip() + '\n\n'
        if tag == 'li':
            return '\n- ' + value.strip() + '\n'
        if tag in ('p', 'div', 'ul', 'ol'):
            section = re.fullmatch(r'\[([^\[\]\n]+)\]', ''.join(node.itertext()).strip()) if tag == 'p' else None
            if section and not node.xpath('.//table|.//img'):
                return '\n\n## ' + escape(section.group(1)) + '\n\n'
            return '\n\n' + value.strip() + '\n\n'
        return value

    return re.sub(r'\n{3,}', '\n\n', walk(root)).strip() + '\n'


def import_document(content: bytes, filename: str) -> tuple[str, list[str]]:
    suffix = Path(filename).suffix.lower()
    warnings = ['원본의 글꼴·페이지 배치·병합 표는 달라질 수 있습니다. 저장 전에 내용을 확인해 주세요.']
    if suffix == '.hwpx':
        from lxml import etree
        with ZipFile(io.BytesIO(content)) as archive:
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            manifest = etree.fromstring(archive.read('Contents/content.hpf'), parser)
            paths = {}
            for item in manifest.iter():
                href = item.get('href', '')
                if item.get('id') and 'BinData/' in href:
                    paths[item.get('id')] = href[href.index('BinData/'):]
            def convert(node):
                tag = etree.QName(node).localname
                if tag == 'pic':
                    for image in node.iter():
                        key = image.get('binaryItemIDRef')
                        if key and key in paths:
                            return '<img src="' + store_image(archive.read(paths[key])) + '"/>'
                    raise ValueError('한글 문서의 사진을 읽지 못했습니다.')
                if tag == 't':
                    return escape_html(node.text or '') + ''.join(convert(child) for child in node)
                if tag == 'lineBreak':
                    return '<br>'
                if tag in ('secPr', 'ctrl', 'linesegarray'):
                    return ''
                text = ''.join(convert(child) for child in node)
                markup = {'p': 'p', 'tbl': 'table', 'tr': 'tr', 'tc': 'td'}.get(tag)
                if tag == 'tc':
                    spans = node.xpath('./*[local-name()="cellSpan"]')
                    attributes = ''
                    if spans:
                        for xml_name, html_name in (('colSpan', 'colspan'), ('rowSpan', 'rowspan')):
                            value = spans[0].get(xml_name, '1')
                            if value.isdigit():
                                attributes += f' {html_name}="{value}"'
                    return f'<td{attributes}>{text}</td>'
                return f'<{markup}>{text}</{markup}>' if markup else text
            names = sorted((name for name in archive.namelist() if re.fullmatch(r'Contents/section\d+\.xml', name)),
                           key=lambda name: int(re.search(r'\d+', name).group()))
            source = ''.join(convert(etree.fromstring(archive.read(name), parser)) for name in names)
            return html_markdown(source, lambda src: src), warnings
    if suffix == '.pdf':
        import fitz
        parts = []
        with fitz.open(stream=content, filetype='pdf') as document:
            for index, page in enumerate(document):
                parts.append(f'## {index + 1}페이지\n')
                if not page.get_text().strip():
                    src = store_image(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes('png'))
                    parts.append(f'![페이지 {index + 1}](<{src}>)\n')
                    warnings.append(f'{index + 1}페이지는 텍스트가 없어 페이지 이미지로 보존했습니다.')
                    continue
                for block in page.get_text('dict', sort=True)['blocks']:
                    if block['type'] == 1:
                        parts.append(f"![사진](<{store_image(block['image'])}>)\n")
                    else:
                        parts.append('\n'.join(escape(''.join(span['text'] for span in line['spans']))
                                               for line in block.get('lines', [])) + '\n')
        return '\n'.join(parts), warnings
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / ('source' + suffix)
        source.write_bytes(content)
        if suffix == '.doc':
            subprocess.run(['libreoffice', '-env:UserInstallation=file://' + str(root / 'profile'),
                            '--headless', '--convert-to', 'docx', '--outdir', str(root), str(source)],
                           check=True, capture_output=True, timeout=90)
            source = root / 'source.docx'
            suffix = '.docx'
        if suffix == '.docx':
            import mammoth
            def convert(image):
                with image.open() as stream:
                    return {'src': store_image(stream.read())}
            with source.open('rb') as stream:
                result = mammoth.convert_to_html(stream, convert_image=mammoth.images.img_element(convert))
            warnings.extend(message.message for message in result.messages)
            return html_markdown(result.value, lambda src: src), warnings
        if suffix == '.hwp':
            output = root / 'converted'
            subprocess.run(['hwp5html', '--output', str(output), str(source)],
                           check=True, capture_output=True, timeout=90)
            index = output / 'index.xhtml'
            if not index.exists():
                raise ValueError('한글 문서 HTML 변환 결과가 없습니다.')
            def read_image(src):
                if src.startswith('data:'):
                    return store_image(base64.b64decode(src.split(',', 1)[1]))
                path = (output / unquote(src)).resolve()
                if not path.is_relative_to(output.resolve()):
                    raise ValueError('잘못된 이미지 경로입니다.')
                return store_image(path.read_bytes())
            return html_markdown(index.read_text(encoding='utf-8'), read_image), warnings
    raise ValueError('HWP, HWPX, DOC, DOCX, PDF 파일을 선택해 주세요.')


def markdown_from_data(data: dict) -> str | None:
    rows = data.get(DOCUMENT_SECTION)
    if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict):
        row = rows[0]
        if row.get('내용__format') == 'markdown' and isinstance(row.get('내용'), str):
            return row['내용']
    return None


def save_markdown_snapshot(data: dict) -> dict:
    markdown = markdown_from_data(data)
    if markdown is None:
        return {}
    directory = UPLOAD_ROOT / 'work_documents' / 'markdown'
    directory.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + '.md'
    (directory / name).write_text(markdown, encoding='utf-8')
    return {'document_format': 'markdown', 'markdown_file': str(directory / name)}


def local_image(src: str) -> bytes:
    parsed = urlparse(src)
    # Never fetch user-controlled URLs: only embed files from our upload directory.
    path = unquote(parsed.path)
    if not path.startswith('/api/uploads/'):
        raise ValueError('서버에 업로드된 사진만 한글 파일에 포함할 수 있습니다.')
    target = (UPLOAD_ROOT / path[len('/api/uploads/'):]).resolve()
    if not target.is_relative_to(UPLOAD_ROOT.resolve()) or not target.is_file():
        raise ValueError('사진 파일을 찾을 수 없습니다. 상세 화면에서 사진을 다시 첨부해 주세요.')
    return target.read_bytes()


def export_hwpx(markdown: str) -> bytes:
    from hwpx import HwpxDocument
    document = HwpxDocument.new()
    rendered = MarkdownIt('commonmark', {'html': True}).enable('table').render(markdown)
    root = html.fragment_fromstring(rendered, create_parent='div')

    def emit(node, add_paragraph, width_mm=150):
        tag = node.tag.lower() if isinstance(node.tag, str) else ''
        if tag in ('script', 'style'):
            return
        if tag == 'table':
            rows = node.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')
            if not rows:
                return
            cols = max(len(row.xpath('./td|./th')) for row in rows)
            table = add_paragraph('').add_table(rows=len(rows), cols=cols, width=round(width_mm * 7200 / 25.4))
            for r, row in enumerate(rows):
                for c, cell in enumerate(row.xpath('./td|./th')):
                    emit(cell, table.cell(r, c).add_paragraph, width_mm / cols - 4)
            return
        paragraph = None
        def text(value, bold=False, italic=False):
            nonlocal paragraph
            if value:
                if paragraph is None:
                    paragraph = add_paragraph('')
                heading = int(tag[1]) if re.fullmatch(r'h[1-6]', tag) else 0
                style = document.styles.ensure_run(bold=bold or bool(heading), italic=italic,
                                                   size=max(12, 22 - heading * 2) if heading else 10)
                paragraph.add_run(value, char_pr_id_ref=style)
        def inline(element, bold=False, italic=False):
            nonlocal paragraph
            if element.tag == 'img':
                raw = local_image(element.get('src', ''))
                picture = Image.open(io.BytesIO(raw))
                picture.load()
                buf = io.BytesIO()
                picture.save(buf, format='PNG')
                # The public document API embeds BinData, then move its picture run
                # into the destination paragraph (also works inside table cells).
                image_width = min(width_mm, 200 * picture.width / picture.height)
                holder = document.add_picture(buf.getvalue(), 'png', width_mm=image_width,
                                              height_mm=image_width * picture.height / picture.width)
                target = add_paragraph('')
                run = holder.element.getparent()
                source_p = run.getparent()
                source_p.remove(run)
                target.element.append(run)
                source_p.getparent().remove(source_p)
                paragraph = None
                return
            if element.tag == 'br':
                paragraph = None
                return
            if element.tag in ('script', 'style'):
                return
            bold = bold or element.tag in ('b', 'strong', 'th')
            italic = italic or element.tag in ('i', 'em')
            if element.tag == 'li':
                text('• ')
            text(element.text, bold, italic)
            for child in element:
                inline(child, bold, italic)
                text(child.tail, bold, italic)
        if tag in ('div', 'ul', 'ol', 'blockquote') or (tag in ('td', 'th') and any(child.tag in ('p', 'table', 'div', 'ul', 'ol') for child in node)):
            if node.text and node.text.strip():
                add_paragraph(node.text)
            for child in node:
                emit(child, add_paragraph, width_mm)
            return
        inline(node)

    for child in root:
        emit(child, document.add_paragraph)
    stream = io.BytesIO()
    document.save_to_stream(stream)
    return stream.getvalue()


def export_hwp(markdown: str) -> bytes:
    """Produce an actual HWP 5 binary for Hancom Office 2010."""
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / 'document.hwpx'
        target = Path(temporary) / 'document.hwp'
        source.write_bytes(export_hwpx(markdown))
        subprocess.run(['hwp', 'convert', str(source), '-o', str(target)],
                       check=True, capture_output=True, timeout=90)
        output = target.read_bytes()
        if not output.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
            raise ValueError('올바른 HWP 파일을 생성하지 못했습니다.')
        return output


def export_docx(markdown: str) -> bytes:
    from docx import Document
    from docx.shared import Mm, Pt
    from docx.oxml.ns import qn
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Mm(20)
    normal = document.styles['Normal']
    normal.font.name, normal.font.size = 'Noto Sans CJK KR', Pt(10)
    normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Noto Sans CJK KR')
    root = html.fragment_fromstring(MarkdownIt('commonmark', {'html': True}).enable('table').render(markdown), create_parent='div')

    def emit(node, container, width=170):
        tag = node.tag.lower() if isinstance(node.tag, str) else ''
        if tag in ('script', 'style'):
            return
        if tag == 'table':
            rows = node.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')
            if not rows:
                return
            cols = max(len(row.xpath('./td|./th')) for row in rows)
            table = container.add_table(rows=len(rows), cols=cols)
            table.style = 'Table Grid'
            table.autofit = True
            for r, row in enumerate(rows):
                for c, cell in enumerate(row.xpath('./td|./th')):
                    emit(cell, table.cell(r, c), max(10, width / cols - 4))
            return
        if tag in ('div', 'ul', 'ol', 'blockquote') or (tag in ('td', 'th') and any(child.tag in ('p', 'table', 'div', 'ul', 'ol') for child in node)):
            if node.text and node.text.strip():
                container.add_paragraph(node.text)
            for child in node:
                emit(child, container, width)
            return
        heading = int(tag[1]) if re.fullmatch(r'h[1-6]', tag) else 0
        paragraph = container.add_paragraph(style=f'Heading {heading}' if heading else None)

        def inline(element, bold=False, italic=False):
            if element.tag in ('script', 'style'):
                return
            if element.tag == 'img':
                raw = local_image(element.get('src', ''))
                with Image.open(io.BytesIO(raw)) as photo:
                    photo.load()
                    stream = io.BytesIO()
                    photo.save(stream, format='PNG')
                    picture_width = min(width, 200 * photo.width / photo.height)
                paragraph.add_run().add_picture(io.BytesIO(stream.getvalue()), width=Mm(picture_width))
                return
            if element.tag == 'br':
                paragraph.add_run().add_break()
                return
            bold = bold or element.tag in ('strong', 'b', 'th')
            italic = italic or element.tag in ('em', 'i')
            def text(value):
                if value:
                    run = paragraph.add_run(value)
                    run.bold, run.italic = bold, italic
            if element.tag == 'li':
                text('• ')
            text(element.text)
            for child in element:
                inline(child, bold, italic)
                text(child.tail)
        inline(node)

    for child in root:
        emit(child, document)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()
