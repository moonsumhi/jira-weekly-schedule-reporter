"""Render saved form fields as tables, independently of the Markdown snapshot.

The HTML returned by :func:`original_form_markup` is intentionally small and
semantic. Both the DOCX and HWPX exporters consume it, so keeping section
titles, column spans, and column width hints in this layer makes the two
formats follow the same report layout.
"""
from html import escape

from markdown_it import MarkdownIt


def original_form_markup(form: dict) -> str:
    renderer = MarkdownIt('commonmark', {'html': True, 'breaks': True}).enable('table')
    data = form['data']
    output = [f"<h1>{escape(form['title'])}</h1>"]

    def paired_image_label(section, field):
        image_label = field.get('pairedImage') or field.get('paired_image')
        if image_label:
            return image_label
        if section.get('title', '').replace(' ', '') != '작업결과':
            return None
        return {'작업 전': '작업 전 사진', '작업 후': '작업 후 사진'}.get(field.get('label'))

    def content(row, field):
        value = row.get(field['label'])
        if field.get('type') == 'image':
            images = value if isinstance(value, list) else [value]
            return ''.join(f'<p><img src="{escape(src, quote=True)}"></p>'
                           for src in images if isinstance(src, str) and src)
        if row.get(field['label'] + '__format') == 'markdown':
            return renderer.render(str(value or '').strip())
        text = str(value if value is not None else '').replace('\r\n', '\n').replace('\r', '\n').strip()
        return escape(text).replace('\n', '<br>')

    def table_widths(section, visible, columns):
        """Return readable relative widths for HWPX's table grid."""
        if not section.get('multiple'):
            if columns == 4 and any(field['label'] == '회사명/성함/직책' for field in visible):
                # Keep the long right-side label on one line where possible.
                return [16, 30, 22, 32]
            return [18, 32, 18, 32] if columns == 4 else [22, 78]
        title = section.get('title', '').replace(' ', '')
        if title == '작업대상' and columns == 5:
            return [6, 27, 24, 27, 16]
        if title in {'백업및복구방법', '백업및복구방안'} and columns == 3:
            return [6, 77, 17]
        if title in {'작업자', '작업자정보'} and columns == 6:
            return [6, 19, 18, 17, 19, 21]
        if title == '개발내용' and columns == 4:
            # 제목은 짧은 제목이 한 줄에 보이고, 리스크(상/중/하)는
            # 최소 폭만 사용하도록 세부 작업 내용에 남은 폭을 준다.
            return [6, 17, 10, 67]
        labels = {field['label'] for field in visible}
        if ({'시작 시간', '종료 시간'} <= labels
                or {'작업 시작 시간', '작업 종료 시간'} <= labels):
            if '비고' in labels and columns == 5:
                return [6, 12, 12, 55, 15]
            if columns == 4:
                return [6, 13, 13, 68]
        if '테스트 항목' in labels:
            if '비고' in labels and columns == 5:
                return [6, 14, 35, 30, 15]
            if columns == 4:
                return [6, 16, 40, 38]
        if '비고' in labels and columns == 3:
            return [6, 67, 27]
        if columns == 3:
            return [6, 74, 20]
        return [6] + [94 / max(columns - 1, 1)] * (columns - 1)

    def display_section_title(section):
        normalized = section['title'].replace(' ', '')
        if normalized == '기본정보':
            return '작업 개요'
        if normalized == '작업시간표':
            return '세부 작업 절차'
        fields = [field.get('label', '').replace(' ', '') for field in section.get('fields', [])]
        if normalized == '담당자' and any(label in {'검토의견', '서명', '검토내용'} for label in fields):
            return '검토/서명'
        return section['title']

    def attrs(columns, widths):
        weights = ','.join(f'{weight:g}' for weight in widths)
        return (f' class="work-section-table" data-column-widths="{escape(weights, quote=True)}"'
                f' data-column-count="{columns}"')

    for section in form['sections']:
        if section['title'] == '문서 본문':
            continue
        fields = section['fields']
        value = data.get(section['title'], [] if section.get('multiple') else {})
        rows = value if isinstance(value, list) else [value]
        rows = [row for row in rows if isinstance(row, dict)]
        paired = {paired_image_label(section, field) for field in fields}
        visible = [field for field in fields if field['label'] not in paired]
        if section['title'] == '작업 대상':
            notes = [field for field in visible if field['label'] == '비고']
            visible = [field for field in visible if field['label'] != '비고']
            index = next((i + 1 for i, field in enumerate(visible)
                          if field['label'].upper() == 'HOSTNAME'), len(visible))
            visible[index:index] = notes

        def cell(row, field):
            result = content(row, field)
            image_label = paired_image_label(section, field)
            if image_label:
                result += content(row, {'label': image_label, 'type': 'image'})
            return result

        if any(item.startswith('<table') for item in output):
            output.append('<p class="section-gap">&#160;</p>')
        columns = len(visible) + 1 if section.get('multiple') else 4
        widths = table_widths(section, visible, columns)
        output.append(f'<table{attrs(columns, widths)}>')
        output.append(f'<tr><th colspan="{columns}" data-role="section-heading">'
                      f'{escape(display_section_title(section))}' + '</th></tr>')
        if section.get('multiple'):
            output.append('<tr data-role="column-header"><th>No.</th>'
                          + ''.join(f"<th>{escape(field['label'])}</th>" for field in visible)
                          + '</tr>')
            for index, row in enumerate(rows):
                output.append(f'<tr><td>{index + 1}</td>'
                              + ''.join('<td>' + cell(row, field) + '</td>' for field in visible)
                              + '</tr>')
        else:
            row = rows[0] if rows else {}
            pending = []
            for field in visible:
                full_width = (field.get('fullWidth') or field.get('full_width')
                              or field.get('type') in {'textarea', 'image'})
                if full_width:
                    if pending:
                        if len(pending) == 1:
                            only = pending.pop()
                            output.append(f'<tr><th>{escape(only["label"])}</th><td>{cell(row, only)}</td>'
                                          '<th></th><td></td></tr>')
                        else:
                            left, right = pending
                            output.append(f'<tr><th>{escape(left["label"])}</th><td>{cell(row, left)}</td>'
                                          f'<th>{escape(right["label"])}</th><td>{cell(row, right)}</td></tr>')
                        pending.clear()
                    output.append(f'<tr><th>{escape(field["label"])}</th><td colspan="3">'
                                  f'{cell(row, field)}</td></tr>')
                    continue
                pending.append(field)
                if len(pending) == 2:
                    left, right = pending
                    output.append(f'<tr><th>{escape(left["label"])}</th><td>{cell(row, left)}</td>'
                                  f'<th>{escape(right["label"])}</th><td>{cell(row, right)}</td></tr>')
                    pending.clear()
            if pending:
                only = pending[0]
                output.append(f'<tr><th>{escape(only["label"])}</th><td>{cell(row, only)}</td>'
                              '<th></th><td></td></tr>')
        output.append('</table>')
    return '<div>' + ''.join(output).replace('\n', '&#10;') + '</div>'
