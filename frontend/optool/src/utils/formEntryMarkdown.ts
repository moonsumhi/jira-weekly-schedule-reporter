import type { FormField, FormSection } from '../services/formTemplates'

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

function pairedImageLabel(section: FormSection, field: FormField): string | undefined {
  if (field.pairedImage) return field.pairedImage
  if (section.title.replace(/\s/g, '') !== '작업결과') return undefined
  return ({ '작업 전': '작업 전 사진', '작업 후': '작업 후 사진' } as Record<string, string>)[field.label]
}

function pairedFieldValue(values: Record<string, unknown>, section: FormSection, field: FormField, origin: string): string {
  const pairedLabel = pairedImageLabel(section, field)
  if (!pairedLabel) return ''
  const imageField = section.fields.find((candidate) => candidate.label === pairedLabel && candidate.type === 'image')
  const pairedField: FormField = imageField ?? { label: pairedLabel, type: 'image' }
  return markdownFieldValue(values, pairedField, origin)
}

function tableCellValue(value: string): string {
  // Keep multiline Markdown readable inside one table cell and prevent pipes
  // in user-entered text from being interpreted as additional columns.
  return value.replace(/\r?\n/g, '<br>').replace(/(^|[^\\])\|/g, '$1\\|')
}

function displaySectionTitle(section: FormSection): string {
  const normalized = section.title.replace(/\s/g, '')
  if (normalized === '기본정보') return '작업 개요'
  if (normalized === '작업시간표') return '세부 작업 절차'
  const fields = section.fields.map((field) => field.label.replace(/\s/g, ''))
  if (normalized === '담당자' && fields.some((label) => ['검토의견', '서명', '검토내용'].includes(label))) return '검토/서명'
  return section.title
}

function hasMeaningfulValue(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(hasMeaningfulValue)
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .some(([key, item]) => !key.endsWith('__format') && hasMeaningfulValue(item))
  }
  if (typeof value === 'string') return value.trim() !== ''
  return typeof value === 'number' || typeof value === 'boolean'
}

function normalizeStoredMarkdown(markdown: string): string {
  const renamed = markdown.split('\n').map((line) => {
    if (/^\s*(#{1,6}\s+|\*{2})작업\s*시간표(?:\s*\*{2})?\s*$/.test(line)) {
      return line.replace(/작업\s*시간표/, '세부 작업 절차')
    }
    return line
  })
  const cleaned: string[] = []
  let index = 0
  const isPipeRow = (line: string) => /^\s*\|.*\|\s*$/.test(line)
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim())
  const isSeparator = (line: string) => isPipeRow(line) && cells(line).every((cell) => /^:?-+:?$/.test(cell))
  const isEmptyRow = (line: string) => isPipeRow(line) && cells(line).every((cell) => cell === '')
  while (index < renamed.length) {
    const line = renamed[index] ?? ''
    if (isEmptyRow(line) && isSeparator(renamed[index + 1] ?? '')) {
      index += 2
      while (isEmptyRow(renamed[index] ?? '')) index += 1
      continue
    }
    cleaned.push(line)
    index += 1
  }
  return cleaned.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n'
}

export function formEntryMarkdown(
  title: string,
  sections: FormSection[],
  data: Record<string, unknown>,
  origin: string,
  options: { excludeField?: (section: FormSection, field: FormSection['fields'][number]) => boolean } = {},
): string {
  const documentRows = data['문서 본문']
  const document = Array.isArray(documentRows) && documentRows.length === 1 ? record(documentRows[0]) : null
  if (document?.['__markdown_override'] === 'true' && document['내용__format'] === 'markdown' && typeof document['내용'] === 'string') {
    return normalizeStoredMarkdown(document['내용']).replace(/(!\[[^\]]*\]\()<?(\/api\/uploads\/[^\s)>]+)>?(\))/g,
      (_match, start: string, path: string, end: string) => `${start}<${new URL(path, origin).href}>${end}`)
  }
  // Synced entries keep both the original field data and a generated Markdown
  // snapshot. Rebuild from the original data so formatting changes apply to
  // existing entries as well; legacy Markdown-only entries remain unchanged.
  if (!hasOriginalForm(sections, data) && Array.isArray(documentRows) && documentRows.length === 1) {
    if (document?.['내용__format'] === 'markdown' && typeof document['내용'] === 'string') {
      return normalizeStoredMarkdown(document['내용']).replace(/(!\[[^\]]*\]\()<?(\/api\/uploads\/[^\s)>]+)>?(\))/g,
        (_match, start: string, path: string, end: string) => `${start}<${new URL(path, origin).href}>${end}`)
    }
  }
  const extraSection = sections.find(section => section.title.replace(/\s/g, '') === '가져온추가내용')
  const extraValue = extraSection ? data[extraSection.title] : undefined
  const extraRows: unknown[] = (Array.isArray(extraValue) ? extraValue : extraValue ? [extraValue] : [])
    .filter((row: unknown) => hasMeaningfulValue(row))
  const extraField = extraSection?.fields.find(field => field.label.replace(/\s/g, '') === '내용') ?? extraSection?.fields[0]
  const splitExtraBlocks = (source: string): Array<{ title: string; content: string }> => {
    const blocks: Array<{ title: string; content: string }> = []
    const parts = source.split(/(?=^###\s+)/m)
    for (const part of parts) {
      const trimmed = part.trim()
      if (!trimmed) continue
      const heading = trimmed.match(/^###\s+(.+?)(?:\r?\n|$)/)
      if (heading) {
        blocks.push({ title: heading[1]?.trim() ?? '', content: trimmed.slice(heading[0].length).trim() })
      } else {
        blocks.push({ title: '', content: trimmed })
      }
    }
    return blocks
  }
  const extraBlocks: Array<{ title: string; content: string }> = extraField
    ? extraRows.flatMap((row: unknown) => splitExtraBlocks(markdownFieldValue(record(row), extraField, origin)))
    : []
  const movedExtraBlocks = extraBlocks.filter((block) => block.title.replace(/\s/g, '') === '담당자')
  const remainingExtraBlocks = extraBlocks.filter((block) => block.title.replace(/\s/g, '') !== '담당자')
  const lines = [`# ${escapeText(title).replace(/\n/g, ' ')}`, '']
  for (const section of sections) {
    if (section.title.replace(/\s/g, '') === '가져온추가내용') continue
    const displayTitle = displaySectionTitle(section)
    lines.push(`## ${escapeText(displayTitle).replace(/\n/g, ' ')}`, '')
    // Paired photos are rendered inside their corresponding text cell instead
    // of becoming separate Markdown table columns.
    const pairedLabels = new Set(section.fields.map((field) => pairedImageLabel(section, field)).filter((label): label is string => Boolean(label)))
    const visibleFields = section.fields.filter((field) => !pairedLabels.has(field.label) && !options.excludeField?.(section, field))
    const cellValue = (values: Record<string, unknown>, field: FormField): string => {
      const content = markdownFieldValue(values, field, origin)
      const paired = pairedFieldValue(values, section, field, origin)
      return [content, paired].filter(Boolean).join('\n\n')
    }
    if (section.multiple) {
      const value = data[section.title]
      const rows = (Array.isArray(value) ? value : value ? [value] : [])
        .filter((row) => hasMeaningfulValue(row))
      if (rows.length === 0) {
        lines.splice(lines.length - 2, 2)
        continue
      }
      const headers = ['No.', ...visibleFields.map((field) => escapeText(field.label).replace(/\n/g, ' '))]
      lines.push(`| ${headers.join(' | ')} |`, `| ${headers.map(() => '---').join(' | ')} |`)
      rows.forEach((row, index) => {
        const values = visibleFields.map((field) => tableCellValue(cellValue(record(row), field)))
        lines.push(`| ${[String(index + 1), ...values].join(' | ')} |`)
      })
      lines.push('')
      if (['작업자정보', '작업자'].includes(section.title.replace(/\s/g, '')) && movedExtraBlocks.length) {
        for (const block of movedExtraBlocks) {
          lines.push(`## ${escapeText(block.title).replace(/\n/g, ' ')}`, '')
          if (block.content) lines.push(block.content, '')
        }
      }
      continue
    }

    const values = record(data[section.title])
    lines.push('| 항목 | 내용 |', '| --- | --- |')
    for (const field of visibleFields) {
      const content = cellValue(values, field)
      lines.push(`| ${escapeText(field.label).replace(/\n/g, ' ')} | ${tableCellValue(content)} |`)
    }
    lines.push('')
  }
  if (remainingExtraBlocks.length) {
    lines.push('## 가져온 추가 내용', '')
    for (const block of remainingExtraBlocks) {
      if (block.title) lines.push(`### ${escapeText(block.title).replace(/\n/g, ' ')}`, '')
      if (block.content) lines.push(block.content, '')
    }
  }
  return `${lines.join('\n').trimEnd()}\n`
}

export function markdownFileName(title: string, id: string): string {
  const safeTitle = Array.from(title, (char) => char.charCodeAt(0) < 32 ? '_' : char).join('')
    .replace(/[<>:"/\\|?*]/g, '_').trim().slice(0, 100).replace(/[. ]+$/, '')
  return `${safeTitle || '문서'}_${id.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`
}
