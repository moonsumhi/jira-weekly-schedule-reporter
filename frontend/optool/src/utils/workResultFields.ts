import type { FormField, FormSection } from '../services/formTemplates'

export function comparisonFormatKey(label: string): string { return `${label}__format` }

export function comparisonMarkdown(row: Record<string, unknown>, fields: FormField[]): string {
  const textField = fields.find((field) => field.type !== 'image')
  if (!textField) return ''
  const value = row[textField.label]
  const text = typeof value === 'string' ? value : ''
  const markdown = row[comparisonFormatKey(textField.label)] === 'markdown' ? text
    : text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/([\\`*_{}[\]()#+.!|~-])/g, '\\$1')
  const photos = fields.filter((field) => field.type === 'image').flatMap((field) => {
    const images = row[field.label]
    return (Array.isArray(images) ? images : [images])
      .filter((src): src is string => typeof src === 'string' && !!src)
      .map((src) => `![${field.label}](<${src.replace(/[<>\s]/g, (char) => encodeURIComponent(char))}>)`)
  })
  return [markdown, ...photos].filter(Boolean).join('\n\n')
}

export function workResultFieldGroups(section: FormSection): { label: string; fields: FormField[] }[] {
  if (section.title === '문서 본문') {
    return [
      { label: '', fields: section.fields.filter((field) => field.label !== '내용') },
      { label: '내용', fields: section.fields.filter((field) => field.label === '내용') },
    ]
  }
  const before = section.fields.find((field) => field.label === '작업 전')
  const after = section.fields.find((field) => field.label === '작업 후')
  if (section.title !== '작업 결과' || !before || !after) return [{ label: '', fields: section.fields }]
  const groups = [before, after].map((field) => ({
    label: field.label,
    fields: [field, ...section.fields.filter((image) => image.type === 'image'
      && image.label === (field.pairedImage || `${field.label} 사진`))],
  }))
  const grouped = new Set(groups.flatMap((group) => group.fields))
  const remaining = section.fields.filter((field) => !grouped.has(field))
  if (remaining.length) groups.push({ label: '', fields: remaining })
  return groups
}
