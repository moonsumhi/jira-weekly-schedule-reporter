"""Render saved form fields as tables, independently of the Markdown snapshot."""
from html import escape

from markdown_it import MarkdownIt


def original_form_markup(form: dict) -> str:
    renderer = MarkdownIt('commonmark', {'html': True, 'breaks': True}).enable('table')
    data = form['data']
    output = [f"<h1>{escape(form['title'])}</h1>"]

    def content(row, field):
        value = row.get(field['label'])
        if field.get('type') == 'image':
            images = value if isinstance(value, list) else [value]
            return ''.join(f'<p><img src="{escape(src, quote=True)}"></p>'
                           for src in images if isinstance(src, str) and src)
        if row.get(field['label'] + '__format') == 'markdown':
            return renderer.render(str(value or ''))
        return '<p>' + escape(str(value if value is not None else '')).replace('\n', '<br>') + '</p>'

    for section in form['sections']:
        if section['title'] == '문서 본문':
            continue
        fields = section['fields']
        value = data.get(section['title'], [] if section.get('multiple') else {})
        rows = value if isinstance(value, list) else [value]
        rows = [row for row in rows if isinstance(row, dict)]
        paired = {field.get('pairedImage') or field.get('paired_image') for field in fields}
        visible = [field for field in fields if field['label'] not in paired]
        if section['title'] == '작업 대상':
            notes = [field for field in visible if field['label'] == '비고']
            visible = [field for field in visible if field['label'] != '비고']
            index = next((i + 1 for i, field in enumerate(visible) if field['label'].upper() == 'HOSTNAME'), len(visible))
            visible[index:index] = notes

        def cell(row, field):
            result = content(row, field)
            image_label = field.get('pairedImage') or field.get('paired_image')
            if image_label:
                result += content(row, {'label': image_label, 'type': 'image'})
            return result

        output.append(f"<h2>{escape(section['title'])}</h2><table>")
        if section.get('multiple'):
            output.append('<tr><th>No.</th>' + ''.join(f"<th>{escape(field['label'])}</th>" for field in visible) + '</tr>')
            for index, row in enumerate(rows):
                output.append(f'<tr><td>{index + 1}</td>' + ''.join('<td>' + cell(row, field) + '</td>' for field in visible) + '</tr>')
        else:
            row = rows[0] if rows else {}
            for field in visible:
                output.append(f"<tr><th>{escape(field['label'])}</th><td>{cell(row, field)}</td></tr>")
        output.append('</table>')
    # One HTML block prevents Markdown parsing from splitting rich table cells.
    return '<div>' + ''.join(output).replace('\n', '&#10;') + '</div>'
