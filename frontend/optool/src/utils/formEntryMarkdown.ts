import type { FormSection } from '../services/formTemplates'

export function hasOriginalForm(sections: FormSection[], data: Record<string, unknown>): boolean {
  return sections.some(section => section.title !== '문서 본문' && Object.prototype.hasOwnProperty.call(data, section.title))
}

export function synchronizedDocument<T extends Record<string, unknown>>(title: string, sections: FormSection[], data: T, origin: string) {
  const original = { ...data }
  delete original['문서 본문']
  return { ...original, '문서 본문': [{ '제목': title, '내용': formEntryMarkdown(title, sections, original, origin), '내용__format': 'markdown' }] }
}

function escapeText(value: unknown): string {
  if (value == null) return ''
  const text = typeof value === 'string' ? value
    : typeof value === 'number' || typeof value === 'boolean' ? String(value)
      : JSON.stringify(value) ?? ''
  return text.replace(/\r\n?/g, '\n')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/([\\`*_{}[\]()#+.!|~-])/g, '\\$1')
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : {}
}

function fieldValue(value: unknown, type: string, label: string, origin: string): string {
  if (type !== 'image') return escapeText(value)
  const images = Array.isArray(value) ? value : [value]
  return images.filter((src): src is string => typeof src === 'string' && !!src.trim())
    .map((src) => {
      try {
        const url = new URL(src, origin)
        if (!['http:', 'https:'].includes(url.protocol)) return ''
        const destination = url.href.replace(/[<>|]/g, (char) => encodeURIComponent(char))
        return `![${escapeText(label)}](<${destination}>)`
      } catch {
        return ''
      }
    }).filter(Boolean).join('\n\n')
}

function markdownFieldValue(values: Record<string, unknown>, field: FormSection['fields'][number], origin: string): string {
  const raw = values[field.label]
  if (values[`${field.label}__format`] === 'markdown' && typeof raw === 'string') {
    return raw.replace(/(!\[[^\]]*\]\()<?(\/api\/uploads\/[^\s)>]+)>?(\))/g,
      (_match, start: string, path: string, end: string) => `${start}<${new URL(path, origin).href}>${end}`)
  }
  return fieldValue(raw, field.type, field.label, origin)
}

function tableCellValue(value: string): string {
  // Keep multiline Markdown readable inside one table cell and prevent pipes
  // in user-entered text from being interpreted as additional columns.
  return value.replace(/\r?\n/g, '<br>').replace(/(^|[^\\])\|/g, '$1\\|')
}

export function formEntryMarkdown(
  title: string,
  sections: FormSection[],
  data: Record<string, unknown>,
  origin: string,
): string {
  const documentRows = data['문서 본문']
  // Synced entries keep both the original field data and a generated Markdown
  // snapshot. Rebuild from the original data so formatting changes apply to
  // existing entries as well; legacy Markdown-only entries remain unchanged.
  if (!hasOriginalForm(sections, data) && Array.isArray(documentRows) && documentRows.length === 1) {
    const document = record(documentRows[0])
    if (document['내용__format'] === 'markdown' && typeof document['내용'] === 'string') {
      return document['내용'].replace(/(!\[[^\]]*\]\()<?(\/api\/uploads\/[^\s)>]+)>?(\))/g,
        (_match, start: string, path: string, end: string) => `${start}<${new URL(path, origin).href}>${end}`)
    }
  }
  const lines = [`# ${escapeText(title).replace(/\n/g, ' ')}`, '']
  for (const section of sections) {
    const displayTitle = section.title.replace(/\s/g, '') === '기본정보' ? '작업 개요' : section.title
    lines.push(`## ${escapeText(displayTitle).replace(/\n/g, ' ')}`, '')
    if (section.multiple) {
      const value = data[section.title]
      const rows = Array.isArray(value) ? value : value ? [value] : []
      const headers = ['No.', ...section.fields.map((field) => escapeText(field.label).replace(/\n/g, ' '))]
      lines.push(`| ${headers.join(' | ')} |`, `| ${headers.map(() => '---').join(' | ')} |`)
      rows.forEach((row, index) => {
        const values = section.fields.map((field) =>
          tableCellValue(markdownFieldValue(record(row), field, origin)))
        lines.push(`| ${[String(index + 1), ...values].join(' | ')} |`)
      })
      lines.push('')
      continue
    }

    const values = record(data[section.title])
    lines.push('| 항목 | 내용 |', '| --- | --- |')
    for (const field of section.fields) {
      const content = markdownFieldValue(values, field, origin)
      lines.push(`| ${escapeText(field.label).replace(/\n/g, ' ')} | ${tableCellValue(content)} |`)
    }
    lines.push('')
  }
  return `${lines.join('\n').trimEnd()}\n`
}

export function markdownFileName(title: string, id: string): string {
  const safeTitle = Array.from(title, (char) => char.charCodeAt(0) < 32 ? '_' : char).join('')
    .replace(/[<>:"/\\|?*]/g, '_').trim().slice(0, 100).replace(/[. ]+$/, '')
  return `${safeTitle || '문서'}_${id.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`
}
