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
    mapping_messages: list[dict[str, object]] = []
    mapping_message_seen = set()

    def preview(value):
        text = re.sub(r'\s+', ' ', str(value or '')).strip()
        return text[:240] + ('…' if len(text) > 240 else '')

    def readable_reason(reason):
        return {
            '표의 열 제목과 템플릿 필드를 연결하지 못함': '이 표의 내용을 넣을 양식 칸을 찾지 못했습니다.',
            '표의 열 제목에 대응하는 템플릿 필드를 찾지 못함': '이 표의 내용을 넣을 양식 칸을 찾지 못했습니다.',
            '대응하는 템플릿 필드를 찾지 못함': '이 내용을 넣을 양식 칸을 찾지 못했습니다.',
            '대응하는 템플릿 섹션을 찾지 못함': '이 내용을 넣을 양식 구역을 찾지 못했습니다.',
            '표 또는 필드 형식으로 인식하지 못함': '표나 입력 칸으로 읽지 못한 내용입니다.',
            '필드 제목이 없어 원문 위치를 확인하지 못함': '항목 이름이 없어 어느 칸에 넣을지 확인하지 못했습니다.',
        }.get(str(reason or '').strip(), str(reason or 'Import 내용을 양식에 연결하지 못했습니다.'))

    def record_unmapped(section_title, field_title, reason, source_value='', row_number=None):
        # 문서 제목·머리말처럼 특정 섹션이나 필드에 속하지 않는 선행
        # 내용은 사용자가 수정할 수 있는 매핑 실패가 아니므로 표시하지 않는다.
        if not str(section_title or '').strip() and not str(field_title or '').strip():
            return
        location = str(section_title or '').strip() or '섹션 제목 없음'
        if field_title:
            location += f' / {str(field_title).strip()}'
        if row_number is not None:
            location += f' / {row_number}번째 행'
        message_key = (location, str(reason or '').strip(), preview(source_value))
        if message_key not in mapping_message_seen:
            mapping_message_seen.add(message_key)
            detail = {
                'section': str(section_title or '').strip(),
                'field': str(field_title or '').strip(),
                'row': row_number,
                'message': readable_reason(reason),
            }
            if source_value:
                detail['source_preview'] = preview(source_value)
            mapping_messages.append(detail)

    def markdown_cell(value):
        return str(value or '').replace('|', '\\|').replace('\n', ' ')
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
            # 테스트 케이스 "결과 시간"(또는 레거시 "시간") 필드에 저장한다.
            '테스트결과시간': '결과시간',
            '테스트결과시각': '결과시간',
            '테스트결과결과시간': '결과시간',
            '테스트결과결과시각': '결과시간',
            '결과시간': '결과시간',
            '결과시각': '결과시간',
            '시간': '결과시간',
        }
        exact = [f for f in fields if norm(f['label']) == key]
        if exact:
            return exact[0]
        alias = alternate.get(key)
        if alias:
            matches = [f for f in fields if norm(f['label']) == alias]
            if matches:
                return matches[0]
            # 결과서 템플릿 버전에 따라 "시간" 또는 "결과 시간"을 사용한다.
            if alias == '결과시간':
                matches = [f for f in fields if norm(f['label']) in {'결과시간', '시간'}]
                if matches:
                    # 현재 양식인 "결과 시간"을 레거시 "시간"보다 우선한다.
                    return next((f for f in matches if norm(f['label']) == '결과시간'), matches[0])
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
            '테스트결과시각': ('테스트결과', '시각'),
            '테스트결과결과시간': ('테스트결과', '결과시간'),
        }.get(key)
        if semantic:
            matches = [f for f in fields if all(token in norm(f['label']) for token in semantic)]
            if len(matches) == 1:
                return matches[0]
        return None

    def compound_fields(name, fields):
        """헤더 하나에 합쳐진 필드(예: ``성함/직책``)를 분리한다.

        운영계 일부 결과서는 담당자 표에서 ``성함 / 직책``을 하나의
        헤더로 내보내지만, 저장 템플릿은 ``성함``과 ``직책``을 별도
        필드로 갖는다. 이 경우 표 셀의 값도 같은 구분자로 나눠 각
        필드에 넣을 수 있도록 반환한다.
        """
        raw_name = str(name or '')
        parts = [part.strip() for part in re.split(r'[/／\n]', raw_name) if part.strip()]
        if len(parts) < 2:
            # HWP 표의 줄바꿈은 Markdown HTML 변환 과정에서 사라져
            # ``성함직책``처럼 붙을 수 있다. 대상 필드 레이블을 순서대로
            # 이어 붙인 형태인지도 확인한다.
            key = norm(raw_name)
            labels = [(norm(field.get('label')), field) for field in fields if norm(field.get('label'))]
            for left_key, left_field in labels:
                if not key.startswith(left_key) or key == left_key:
                    continue
                rest = key[len(left_key):]
                right = next((field for label_key, field in labels if label_key == rest), None)
                if right is not None and right is not left_field:
                    return [left_field, right]
            return []
        matched = []
        for part in parts:
            field = match(part, fields)
            if field is not None and field not in matched:
                matched.append(field)
        return matched

    def compound_values(cell):
        """표 셀에서 ``성함/직책``처럼 합쳐진 값을 순서대로 분리한다."""
        def text_with_breaks(node):
            chunks = []

            def walk(element):
                if element.text:
                    chunks.append(element.text)
                for child in element:
                    if isinstance(child.tag, str) and child.tag.lower() == 'br':
                        chunks.append('\n')
                    else:
                        walk(child)
                    if child.tail:
                        chunks.append(child.tail)

            walk(node)
            return ''.join(chunks)

        plain = text_with_breaks(cell).strip()
        return [part.strip() for part in re.split(r'[/／\n]', plain) if part.strip()]

    def assign_plain(row, field, value):
        """compound 헤더에서 분리한 일반 텍스트 값을 필드에 저장한다."""
        name = field['label']
        plain = str(value or '').strip()
        if field.get('type') == 'textarea':
            row[name], row[name + '__format'] = plain, 'markdown'
            return
        if field.get('type') == 'select' and '■' in plain:
            selected = re.findall(r'[■●✔✓]\s*([^□■●✔✓]+)', plain)
            plain = ', '.join(s.strip() for s in selected) or plain
        row[name] = plain

    def combined_header_groups(headers, mapped, fields):
        """여러 표 열을 템플릿의 복합 필드 하나로 묶는다.

        운영계 작업자 표는 ``성함``과 ``직책``을 별도 열로 내보내지만,
        현재 템플릿은 ``성함/직책`` 한 필드로 저장한다. 헤더 순서와
        레이블을 기준으로 이 변환을 안전하게 수행한다.
        """
        groups = {}
        used = set()
        for field in fields:
            label = str(field.get('label') or '')
            parts = [part.strip() for part in re.split(r'[/／]', label) if part.strip()]
            if len(parts) < 2:
                continue
            indices = []
            for part in parts:
                index = next(
                    (
                        i for i, header in enumerate(headers)
                        if i not in used
                        and mapped[i] is None
                        and norm(header) == norm(part)
                    ),
                    None,
                )
                if index is None:
                    indices = []
                    break
                indices.append(index)
            if len(indices) == len(parts):
                groups[indices[0]] = (field, indices)
                used.update(indices)
        return groups, {index for _, indices in groups.values() for index in indices}

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
            # 운영계 담당자 표는 ``성함/직책``만으로 구성된 경우도
            # 있으므로 역할 열이 없더라도 작업자 정보로 판단한다.
            worker_headings = {'회사명', '성함직책', '역할', '연락처'}
            key = '작업자정보' if headings & worker_headings else '검토/서명'
            # ``검토/서명`` contains a separator that ``norm`` removes. Use
            # the normalized key here as well, otherwise 담당자 blocks fall
            # through to 가져온 추가 내용 even when the review section exists.
            candidates = [s for s in sections if norm(s['title']) == norm(key)]
        if not candidates:
            # 운영계에서 섹션 제목은 ``담당자``로 유지하면서 실제 저장
            # 템플릿은 ``작업자 정보`` 또는 ``검토/서명``으로 바뀐 경우가
            # 있다. 표 헤더와 대상 필드의 겹치는 정도로 가장 알맞은
            # 섹션을 선택해 담당자 표가 추가 내용으로 빠지지 않게 한다.
            source_labels = set()
            for node in nodes:
                for header_node in node.xpath('.//th'):
                    raw_header = ''.join(header_node.itertext()).strip()
                    if not raw_header:
                        continue
                    source_labels.add(norm(raw_header))
                    # ``성함/직책``을 별도 필드로 저장하는 템플릿도
                    # 섹션 선택 단계에서 후보로 인식할 수 있게 한다.
                    source_labels.update(norm(part) for part in re.split(r'[/／]', raw_header) if part.strip())
            scored = []
            for candidate in sections:
                target_labels = {norm(field.get('label')) for field in candidate.get('fields', [])}
                overlap = source_labels & target_labels
                if not overlap:
                    continue
                score = len(overlap)
                if source_key == '담당자' and '성함직책' in source_labels:
                    if '성함직책' in target_labels:
                        score += 3
                    if '성함' in target_labels or '직책' in target_labels:
                        score += 1
                if source_key == '담당자':
                    candidate_key = norm(candidate.get('title'))
                    review_hint = source_labels & {'소속', '성함', '검토의견', '서명'}
                    worker_hint = source_labels & {'회사명', '역할', '연락처'}
                    if candidate_key in {'검토서명', '검토의견'}:
                        score += 4 * len(review_hint)
                    if candidate_key in {'작업자정보', '작업자'}:
                        score += 4 * len(worker_hint)
                scored.append((score, candidate))
            if scored:
                candidates = [max(scored, key=lambda item: item[0])[1]]
        if not candidates:
            logger.warning('작업 문서 Import 섹션 매핑 실패: source_title=%r normalized=%r', title, key)
            # The document title is already represented by the selected form.
            remaining = [n for n in nodes if n.tag != 'h1']
            record_unmapped(title, '', '대응하는 템플릿 섹션을 찾지 못함', as_md(remaining) if remaining else '')
            if remaining:
                extras.append((title, as_md(remaining)))
            continue
        section = candidates[0]
        fields = section.get('fields', [])
        logger.debug('작업 문서 Import 섹션 매핑: source_title=%r target_section=%r fields=%s', title, section.get('title'), [f.get('label') for f in fields])
        rows = []
        current = {}
        current_row_number = 1
        pending_field, pending_nodes = None, []
        result_section = norm(section.get('title')) == norm('작업 결과')
        pending_result_prefix = ''

        def flush_field():
            nonlocal pending_field, pending_nodes
            if pending_field is not None:
                if pending_field.get('label') == '__work_period__':
                    assign_work_period(current, fields, pending_nodes)
                else:
                    assign(current, pending_field, pending_nodes)
            elif pending_nodes:
                record_unmapped(
                    title,
                    '',
                    '필드 제목이 없어 원문 위치를 확인하지 못함',
                    as_md(pending_nodes),
                    row_number=current_row_number,
                )
                extras.append((title, as_md(pending_nodes)))
            pending_field, pending_nodes = None, []

        for node in nodes:
            # Some HWP exports put the short description (for example
            # ``-사용 여부 확인``) in a paragraph immediately before the
            # corresponding before/after table. Keep it with that table
            # instead of reporting it as an unmapped field.
            if result_section and node.tag not in ('table', 'h3', 'h4'):
                prefix = as_md([node]).strip()
                if prefix:
                    pending_result_prefix = '\n\n'.join(
                        part for part in (pending_result_prefix, prefix) if part
                    )
                continue
            heading = ''.join(node.itertext()).strip() if node.tag in ('h3', 'h4') else ''
            if node.tag == 'h3' and re.fullmatch(r'\d+번째 항목', heading):
                flush_field()
                if current:
                    rows.append(current)
                current = {}
                current_row_number = int(re.match(r'\d+', heading).group())
                continue
            if node.tag in ('h3', 'h4'):
                flush_field()
                pending_field = match(heading, fields)
                if pending_field is None and norm(heading) == '작업일시':
                    # 구 양식의 작업 일시는 새 결과서 양식에서 시작/종료로 분리된다.
                    pending_field = {'label': '__work_period__'} if all(work_period_fields(fields)) else None
                if pending_field is None:
                    logger.warning('작업 문서 Import 필드 매핑 실패: section=%r source_field=%r', title, heading)
                    record_unmapped(title, heading, '대응하는 템플릿 필드를 찾지 못함', row_number=current_row_number)
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
                def cell_text(cell):
                    chunks = []

                    def walk(element):
                        if element.text:
                            chunks.append(element.text)
                        for child in element:
                            if isinstance(child.tag, str) and child.tag.lower() == 'br':
                                chunks.append('\n')
                            else:
                                walk(child)
                            if child.tail:
                                chunks.append(child.tail)

                    walk(cell)
                    return ''.join(chunks).strip()

                headers = [cell_text(c) for c in table_rows[0]]

                # 작업결과서 HWP는 작업 전/후 표를 ``작업 결과 |``라는
                # 2열 표로 반복 저장하는 경우가 있다. 이 형태는 표의
                # 첫 행만 보면 템플릿 필드와 일치하지 않으므로 일반적인
                # 열 매핑에 맡기면 텍스트와 이미지가 모두 미매핑된다.
                # 각 표를 하나의 작업 결과 행으로 묶어 두 열의 Markdown을
                # 그대로 보존한다. 이미지도 Markdown 이미지로 유지되므로
                # 별도 사진 컬럼 없이 편집기에서 함께 수정할 수 있다.
                is_result_pair_table = (
                    norm(section.get('title')) == norm('작업 결과')
                    and len(headers) >= 2
                    and norm(headers[0]) in {'작업 결과', '작업결과'}
                )
                if is_result_pair_table:
                    before_parts = []
                    after_parts = []
                    if pending_result_prefix:
                        before_parts.append(pending_result_prefix)
                        pending_result_prefix = ''
                    for tr in table_rows[1:]:
                        cells = list(tr)
                        if not cells:
                            continue
                        before = as_md([cells[0]]).strip() if len(cells) >= 1 else ''
                        after = as_md([cells[1]]).strip() if len(cells) >= 2 else ''
                        if before:
                            before_parts.append(before)
                        if after:
                            after_parts.append(after)
                    if before_parts or after_parts:
                        rows.append({
                            '작업 전': '\n\n'.join(before_parts),
                            '작업 전__format': 'markdown',
                            '작업 후': '\n\n'.join(after_parts),
                            '작업 후__format': 'markdown',
                        })
                    continue

                mapped = [match(h, fields) for h in headers]
                compound_mapped = {
                    index: compound_fields(header, fields)
                    for index, header in enumerate(headers)
                    if mapped[index] is None and compound_fields(header, fields)
                }
                combined_mapped, combined_indices = combined_header_groups(headers, mapped, fields)
                # "항목 | 내용" 형태의 기본 정보 표는 첫 열이 실제 필드명이다.
                # 이 형식은 Markdown/HWP 변환 결과에서 자주 사용된다.
                key_value_table = (
                    len(headers) >= 2
                    and norm(headers[0]) in {'항목', '항목명', '구분'}
                    and norm(headers[1]) in {'내용', '값', '데이터'}
                )
                if key_value_table:
                    parsed_row = {}
                    key_value_values = {}
                    for row_number, tr in enumerate(table_rows[1:], start=1):
                        cells = list(tr)
                        if len(cells) < 2:
                            continue
                        source_label = cell_text(cells[0])
                        field = match(source_label, fields)
                        if field:
                            assign(parsed_row, field, [cells[1]])
                        else:
                            split_fields = compound_fields(source_label, fields)
                            if split_fields:
                                values = compound_values(cells[1])
                                if len(split_fields) == 1:
                                    assign_plain(parsed_row, split_fields[0], cell_text(cells[1]))
                                else:
                                    for split_field, value in zip(split_fields, values):
                                        assign_plain(parsed_row, split_field, value)
                            elif norm(source_label) == '작업일시':
                                assign_work_period(parsed_row, fields, [cells[1]])
                            elif source_label and ''.join(cells[1].itertext()).strip():
                                key_value_values[norm(source_label)] = (source_label, cell_text(cells[1]), row_number)
                    # ``항목 | 내용`` 표에서도 성함·직책이 별도 행으로
                    # 내려오는 운영계 변형을 복합 필드 하나로 합친다.
                    for field in fields:
                        parts = [part.strip() for part in re.split(r'[/／]', str(field.get('label') or '')) if part.strip()]
                        values = [key_value_values.get(norm(part), ('', ''))[1] for part in parts]
                        if len(parts) >= 2 and all(values):
                            assign_plain(parsed_row, field, ' / '.join(values))
                            for part in parts:
                                key_value_values.pop(norm(part), None)
                    for _, (source_label, value, row_number) in key_value_values.items():
                        if value:
                            record_unmapped(
                                title,
                                source_label,
                                '항목명이 템플릿 필드와 일치하지 않음',
                                value,
                                row_number=row_number,
                            )
                            extras.append((title + ' / ' + source_label, value))
                    if parsed_row:
                        if set(current) & set(parsed_row):
                            rows.append(current)
                            current = {}
                        current.update(parsed_row)
                    continue
                if not any(mapped) and not compound_mapped and not combined_mapped:
                    recorded_cell = False
                    for row_number, row in enumerate(table_rows[1:], start=1):
                        for index, cell in enumerate(row):
                            value = cell_text(cell)
                            header = headers[index] if index < len(headers) else ''
                            if not value or norm(header).lower() in ('no.', 'no', '번호'):
                                continue
                            record_unmapped(
                                title,
                                header,
                                '표의 열 제목과 템플릿 필드를 연결하지 못함',
                                value,
                                row_number=row_number,
                            )
                            recorded_cell = True
                    if not recorded_cell:
                        record_unmapped(
                            title,
                            ' / '.join(header for header in headers if header),
                            '표의 열 제목과 템플릿 필드를 연결하지 못함',
                        )
                    extras.append((title, as_md([node])))
                    continue
                parsed = []
                for row_number, tr in enumerate(table_rows[1:], start=1):
                    row = {}
                    for i, cell in enumerate(tr):
                        field = mapped[i] if i < len(mapped) else None
                        if field:
                            assign(row, field, [cell])
                        elif i in combined_mapped:
                            combined_field, indices = combined_mapped[i]
                            values = [cell_text(tr[index]) for index in indices]
                            assign_plain(row, combined_field, ' / '.join(value for value in values if value))
                        elif i in combined_indices:
                            continue
                        elif i in compound_mapped:
                            split_fields = compound_mapped[i]
                            values = compound_values(cell)
                            if len(split_fields) == 1:
                                assign_plain(row, split_fields[0], ''.join(cell.itertext()))
                            else:
                                for split_field, value in zip(split_fields, values):
                                    assign_plain(row, split_field, value)
                        elif i < len(headers) and norm(headers[i]) == '작업일시':
                            assign_work_period(row, fields, [cell])
                        elif i < len(headers) and norm(headers[i]).lower() not in ('no.', 'no', '번호') and cell_text(cell):
                            record_unmapped(
                                title,
                                headers[i],
                                '표의 열 제목에 대응하는 템플릿 필드를 찾지 못함',
                                cell_text(cell),
                                row_number=row_number,
                            )
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
                record_unmapped(
                    title,
                    '',
                    '표 또는 필드 형식으로 인식하지 못함',
                    as_md([node]),
                    row_number=current_row_number,
                )
                extras.append((title, as_md([node])))
        flush_field()
        if pending_nodes:
            record_unmapped(
                title,
                '',
                '필드 제목이 없어 원문 위치를 확인하지 못함',
                as_md(pending_nodes),
                row_number=current_row_number,
            )
            extras.append((title, as_md(pending_nodes)))
        if current:
            rows.append(current)
        if section.get('multiple'):
            data[section['title']].extend(rows)
        else:
            for row in rows:
                data[section['title']].update(row)

    # Keep source content that could not be placed in the selected template.
    # Mapping failures are shown in the import error dialog.
    if extras:
        original_parts = []
        for extra_title, extra_value in extras:
            if not extra_value:
                continue
            heading = f'### {extra_title}\n\n' if extra_title else ''
            original_parts.append(f'{heading}{extra_value}')
        if original_parts:
            data[EXTRA] = [{
                '내용': '## 원본 내용\n\n' + '\n\n'.join(original_parts),
                '내용__format': 'markdown',
            }]
    if not mapping_messages:
        return data, []
    return data, [
        {
            'summary': True,
            'message': f'Import에서 연결되지 않은 항목이 {len(mapping_messages)}건 있습니다.',
        },
        *mapping_messages,
    ]
