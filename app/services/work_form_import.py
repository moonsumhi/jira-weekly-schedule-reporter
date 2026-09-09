"""Map ordered document Markdown into editable template fields."""
import re
import unicodedata
from lxml import html
from markdown_it import MarkdownIt
from app.services.work_documents import html_markdown

EXTRA = '가져온 추가 내용'


def map_document(markdown: str, sections: list[dict]) -> tuple[dict, list[str]]:
    root = html.fragment_fromstring(MarkdownIt('commonmark', {'html': True}).enable('table').render(markdown), create_parent='div')
    def norm(s):
        """Normalize section/field labels across HWP export variants."""
        value = unicodedata.normalize('NFKC', str(s or '')).strip().lower()
        value = re.sub(r'[\s\u00a0\u3000]+', '', value)
        value = re.sub(r'[\[\]():：·•/\\._-]+', '', value)
        return value
    aliases = {'작업개요': '기본정보', '백업및복구방안': '백업및복구방법', '작업자': '작업자정보',
               '검토의견': '검토/서명', '세부작업절차': '작업시간표', '사전작업': '사전점검',
               '테스트계획': '테스트케이스', '테스트결과': '테스트케이스(성공)', '테스트결과분석': '테스트케이스(실패)'}
    data = {s['title']: [] if s.get('multiple') else {} for s in sections}
    extras = []

    def as_md(nodes):
        return html_markdown(''.join(html.tostring(n, encoding='unicode', with_tail=False) for n in nodes), lambda src: src).strip()

    def match(name, fields):
        key = norm(name)
        alternate = {'작업시간/시작': '시작시간', '작업시간/종료': '종료시간', '회사명': '소속'}
        return next((f for f in fields if norm(f['label']) == key), None) or next(
            (f for f in fields if norm(f['label']) == alternate.get(key)), None)

    def assign(row, field, nodes):
        name = field['label']
        value = as_md(nodes)
        if field.get('type') == 'image':
            row[name] = [src for node in nodes for src in node.xpath('.//img/@src|self::img/@src')]
            return
        plain = '\n'.join(''.join(n.itertext()) for n in nodes).strip()
        if field.get('type') == 'textarea':
            row[name], row[name + '__format'] = value, 'markdown'
        else:
            if field.get('type') == 'select' and '■' in plain:
                selected = re.findall(r'[■●✔✓]\s*([^□■●✔✓]+)', plain)
                plain = ', '.join(s.strip() for s in selected) or plain
            row[name] = plain

    blocks = []
    title, nodes = '', []
    for node in root:
        if node.tag == 'h2':
            if nodes:
                blocks.append((title, nodes))
            title, nodes = ''.join(node.itertext()), []
        else:
            nodes.append(node)
    if nodes:
        blocks.append((title, nodes))

    for title, nodes in blocks:
        key = aliases.get(norm(title), norm(title))
        candidates = [s for s in sections if norm(s['title']) == key]
        if norm(title) == '담당자':
            headings = {norm(''.join(n.itertext())) for node in nodes for n in node.xpath('.//th')}
            key = '작업자정보' if '역할' in headings else '검토/서명'
            candidates = [s for s in sections if norm(s['title']) == key]
        if not candidates:
            # The document title is already represented by the selected form.
            remaining = [n for n in nodes if n.tag != 'h1']
            if remaining:
                extras.append((title, as_md(remaining)))
            continue
        section = candidates[0]
        fields = section.get('fields', [])
        rows = []
        current = {}
        pending_field, pending_nodes = None, []

        def flush_field():
            nonlocal pending_field, pending_nodes
            if pending_field is not None:
                assign(current, pending_field, pending_nodes)
            elif pending_nodes:
                extras.append((title, as_md(pending_nodes)))
            pending_field, pending_nodes = None, []

        for node in nodes:
            heading = ''.join(node.itertext()).strip() if node.tag in ('h3', 'h4') else ''
            if node.tag == 'h3' and re.fullmatch(r'\d+번째 항목', heading):
                flush_field()
                if current:
                    rows.append(current)
                current = {}
                continue
            if node.tag in ('h3', 'h4'):
                flush_field()
                pending_field = match(heading, fields)
                if pending_field is None:
                    pending_nodes = [node]
                continue
            if pending_field is not None:
                pending_nodes.append(node)
                continue
            if pending_nodes:
                extras.append((title, as_md(pending_nodes)))
                pending_nodes = []
            if node.tag == 'table':
                table_rows = node.xpath('./thead/tr|./tbody/tr|./tr')
                if not table_rows:
                    continue
                headers = [''.join(c.itertext()).strip() for c in table_rows[0]]
                mapped = [match(h, fields) for h in headers]
                if not any(mapped):
                    extras.append((title, as_md([node])))
                    continue
                parsed = []
                for tr in table_rows[1:]:
                    row = {}
                    for i, cell in enumerate(tr):
                        field = mapped[i] if i < len(mapped) else None
                        if field:
                            assign(row, field, [cell])
                        elif i < len(headers) and norm(headers[i]).lower() not in ('no.', 'no', '번호') and ''.join(cell.itertext()).strip():
                            extras.append((title + ' / ' + headers[i], as_md([cell])))
                    if row:
                        parsed.append(row)
                if len(parsed) == 1:
                    if set(current) & set(parsed[0]):
                        rows.append(current)
                        current = {}
                    current.update(parsed[0])
                elif parsed:
                    if current:
                        rows.append(current)
                        current = {}
                    rows.extend(parsed)
            else:
                extras.append((title, as_md([node])))
        flush_field()
        if pending_nodes:
            extras.append((title, as_md(pending_nodes)))
        if current:
            rows.append(current)
        if section.get('multiple'):
            data[section['title']].extend(rows)
        else:
            for row in rows:
                data[section['title']].update(row)
    if extras:
        data[EXTRA] = [{'내용': '\n\n'.join((f'### {title}\n\n' if title else '') + value for title, value in extras if value), '내용__format': 'markdown'}]
    return data, ([f'양식에 대응하지 않는 내용은 「{EXTRA}」에 보존했습니다.'] if extras else [])
