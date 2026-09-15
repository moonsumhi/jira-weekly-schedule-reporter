"""Map ordered document Markdown into editable template fields."""
import re
import unicodedata
import logging
from lxml import html
from markdown_it import MarkdownIt
from app.services.work_documents import html_markdown

EXTRA = '가져온 추가 내용'
logger = logging.getLogger(__name__)


def map_document(markdown: str, sections: list[dict]) -> tuple[dict, list[str]]:
    root = html.fragment_fromstring(MarkdownIt('commonmark', {'html': True}).enable('table').render(markdown), create_parent='div')
    def norm(s):
        """Normalize section/field labels across HWP export variants."""
        value = unicodedata.normalize('NFKC', str(s or '')).strip().lower()
        value = re.sub(r'[\s\u00a0\u3000]+', '', value)
        value = re.sub(r'[\[\]():：·•/\\._-]+', '', value)
        return value
    # Keys are normalized source titles. Values are preferred target section
    # titles used by the current work-document templates.
    aliases = {'작업개요': '기본정보', '백업및복구방안': '백업및복구방법', '작업자': '작업자정보',
               '검토서명': '검토의견', '검토의견': '검토/서명', '세부작업절차': '작업시간표', '사전작업': '사전점검',
               '테스트계획': '테스트케이스', '테스트결과': '테스트케이스', '테스트결과분석': '테스트케이스',
               '테스트케이스성공': '테스트케이스', '테스트케이스실패': '테스트케이스'}
    preferred_alias_sources = {
        '작업개요', '백업및복구방안', '작업자', '검토서명', '세부작업절차',
        '사전작업', '테스트계획', '테스트결과', '테스트결과분석',
        '테스트케이스성공', '테스트케이스실패',
    }
    data = {s['title']: [] if s.get('multiple') else {} for s in sections}
    extras = []
    logger.info('작업 문서 Import 매핑 시작: template_sections=%s', [s.get('title') for s in sections])

    def as_md(nodes):
        return html_markdown(''.join(html.tostring(n, encoding='unicode', with_tail=False) for n in nodes), lambda src: src).strip()

    def work_period_fields(fields):
        start = next((field for field in fields if norm(field.get('label')) == '작업기간시작'), None)
        end = next((field for field in fields if norm(field.get('label')) == '작업기간종료'), None)
        return start, end

    def split_work_period(value):
        """원본의 한 칸짜리 작업 일시를 결과서의 시작/종료 필드로 분리한다."""
        source = ' '.join(str(value or '').split())
        if not source:
            return '', ''
        times = list(re.finditer(r'(\d{1,2}):(\d{2})', source))
        if not times:
            return source, ''
        date = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', source)
        prefix = ''
        if date:
            year, month, day = date.groups()
            prefix = f'{year}-{month.zfill(2)}-{day.zfill(2)}T'
        first = times[0]
        start = f'{prefix}{first.group(1).zfill(2)}:{first.group(2)}'
        if len(times) == 1:
            return start, ''
        second = times[1]
        # 종료 일시가 별도 날짜를 가진 경우 그 날짜를 우선 사용한다.
        after_start = source[first.end():second.start()]
        end_date = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', after_start)
        end_prefix = prefix
        if end_date:
            year, month, day = end_date.groups()
            end_prefix = f'{year}-{month.zfill(2)}-{day.zfill(2)}T'
        return start, f'{end_prefix}{second.group(1).zfill(2)}:{second.group(2)}'

    def assign_work_period(row, fields, nodes):
        start_field, end_field = work_period_fields(fields)
        if not start_field or not end_field:
            return False
        plain = '\n'.join(''.join(node.itertext()) for node in nodes).strip()
        start, end = split_work_period(plain)
        if start:
            row[start_field['label']] = start
        if end:
            row[end_field['label']] = end
        return bool(start or end)

    def match(name, fields):
        key = norm(name)
        alternate = {
            '작업시작': '작업시작시간',
            '작업시작시각': '작업시작시간',
            '작업종료': '작업종료시간',
            '작업종료시각': '작업종료시간',
            '회사명': '소속',
            # 작업결과서 원본의 "테스트 결과 / 시간"은 새 템플릿의
            # 테스트 케이스 "시간"(또는 "결과 시간") 필드에 저장한다.
            '테스트결과시간': '시간',
            '결과시간': '시간',
        }
        exact = [f for f in fields if norm(f['label']) == key]
        if exact:
            return exact[0]
        alias = alternate.get(key)
        if alias:
            matches = [f for f in fields if norm(f['label']) == alias]
            if matches:
                return matches[0]
            # 일부 결과서 템플릿은 시간 필드를 "결과 시간"으로 표시한다.
            if alias == '시간':
                matches = [f for f in fields if norm(f['label']) == '결과시간']
                if matches:
                    return matches[0]
        # Deployed templates use both legacy labels (시작 시간/종료 시간)
        # and canonical labels (작업 시작 시간/작업 종료 시간). HWP and
        # Word exports may also reorder the words to 작업 시간 시작/종료.
        time_aliases = {
            '작업시작': {'작업시작시간', '시작시간'},
            '작업시작시각': {'작업시작시간', '시작시간'},
            '작업시작시간': {'작업시작시간', '시작시간'},
            '작업시간시작': {'작업시작시간', '시작시간'},
            '시작시간': {'작업시작시간', '시작시간'},
            '작업종료': {'작업종료시간', '종료시간'},
            '작업종료시각': {'작업종료시간', '종료시간'},
            '작업종료시간': {'작업종료시간', '종료시간'},
            '작업시간종료': {'작업종료시간', '종료시간'},
            '종료시간': {'작업종료시간', '종료시간'},
        }.get(key)
        if time_aliases:
            matches = [f for f in fields if norm(f['label']) in time_aliases]
            if len(matches) == 1:
                return matches[0]
        # Handle labels split differently by HWP/Word table exports.
        semantic = {
            '작업시작시간': ('작업시작', '시작시간'),
            '작업종료시간': ('작업종료', '종료시간'),
            '성함직책': ('성함', '직책'),
            '테스트결과시간': ('테스트결과', '시간'),
        }.get(key)
        if semantic:
            matches = [f for f in fields if all(token in norm(f['label']) for token in semantic)]
            if len(matches) == 1:
                return matches[0]
        return None

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
        source_key = norm(title)
        # Prefer the canonical target for known source titles. Fall back to an
        # exact title when a custom template does not define that target.
        preferred_title = aliases.get(source_key) if source_key in preferred_alias_sources else None
        key = source_key
        if preferred_title:
            key = preferred_title
        candidates = [s for s in sections if norm(s['title']) == norm(key)]
        if not candidates and preferred_title:
            key = source_key
            candidates = [s for s in sections if norm(s['title']) == source_key]
        if not candidates and source_key in aliases and source_key not in preferred_alias_sources:
            key = aliases[source_key]
            candidates = [s for s in sections if norm(s['title']) == norm(key)]
        # The schedule section has two names in deployed templates. Treat
        # them as the same section so imports keep working after the display
        # title is standardized to "세부 작업 절차".
        if not candidates and norm(key) == '작업시간표':
            key = '세부 작업 절차'
            candidates = [s for s in sections if norm(s['title']) == norm(key)]
        if not candidates and norm(key) == '세부작업절차':
            key = '작업 시간표'
            candidates = [s for s in sections if norm(s['title']) == norm(key)]
        if source_key == '담당자' and not candidates:
            headings = {norm(''.join(n.itertext())) for node in nodes for n in node.xpath('.//th')}
            key = '작업자정보' if '역할' in headings else '검토/서명'
            # ``검토/서명`` contains a separator that ``norm`` removes. Use
            # the normalized key here as well, otherwise 담당자 blocks fall
            # through to 가져온 추가 내용 even when the review section exists.
            candidates = [s for s in sections if norm(s['title']) == norm(key)]
        if not candidates:
            logger.warning('작업 문서 Import 섹션 매핑 실패: source_title=%r normalized=%r', title, key)
            # The document title is already represented by the selected form.
            remaining = [n for n in nodes if n.tag != 'h1']
            if remaining:
                extras.append((title, as_md(remaining)))
            continue
        section = candidates[0]
        fields = section.get('fields', [])
        logger.debug('작업 문서 Import 섹션 매핑: source_title=%r target_section=%r fields=%s', title, section.get('title'), [f.get('label') for f in fields])
        rows = []
        current = {}
        pending_field, pending_nodes = None, []

        def flush_field():
            nonlocal pending_field, pending_nodes
            if pending_field is not None:
                if pending_field.get('label') == '__work_period__':
                    assign_work_period(current, fields, pending_nodes)
                else:
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
                if pending_field is None and norm(heading) == '작업일시':
                    # 구 양식의 작업 일시는 새 결과서 양식에서 시작/종료로 분리된다.
                    pending_field = {'label': '__work_period__'} if all(work_period_fields(fields)) else None
                if pending_field is None:
                    logger.warning('작업 문서 Import 필드 매핑 실패: section=%r source_field=%r', title, heading)
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
                # "항목 | 내용" 형태의 기본 정보 표는 첫 열이 실제 필드명이다.
                # 이 형식은 Markdown/HWP 변환 결과에서 자주 사용된다.
                key_value_table = (
                    len(headers) >= 2
                    and norm(headers[0]) in {'항목', '항목명', '구분'}
                    and norm(headers[1]) in {'내용', '값', '데이터'}
                )
                if key_value_table:
                    parsed_row = {}
                    for tr in table_rows[1:]:
                        cells = list(tr)
                        if len(cells) < 2:
                            continue
                        source_label = ''.join(cells[0].itertext()).strip()
                        field = match(source_label, fields)
                        if field:
                            assign(parsed_row, field, [cells[1]])
                        elif norm(source_label) == '작업일시':
                            assign_work_period(parsed_row, fields, [cells[1]])
                        elif source_label and ''.join(cells[1].itertext()).strip():
                            extras.append((title + ' / ' + source_label, as_md([cells[1]])))
                    if parsed_row:
                        if set(current) & set(parsed_row):
                            rows.append(current)
                            current = {}
                        current.update(parsed_row)
                    continue
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
                        elif i < len(headers) and norm(headers[i]) == '작업일시':
                            assign_work_period(row, fields, [cell])
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
