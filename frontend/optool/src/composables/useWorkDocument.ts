import { ref, type Ref } from 'vue'
import { exportFile, useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import type { FormEntry } from 'src/services/formEntries'
import type { FormTemplate, FormSection } from 'src/services/formTemplates'
import { downloadAttachment } from 'src/utils/attachment'
import { formEntryMarkdown, markdownFileName, hasOriginalForm, synchronizedDocument } from 'src/utils/formEntryMarkdown'

export type WorkDocumentData = Record<string, Record<string, unknown> | Record<string, unknown>[]>

const documentSections: FormSection[] = [{ title: '문서 본문', multiple: true, fields: [
  { label: '제목', type: 'text', required: true, fullWidth: true },
  { label: '내용', type: 'textarea', required: true, fullWidth: true },
] }]
export function originalWorkDocumentSections(template: FormTemplate | null, data: Record<string, unknown>): FormSection[] {
  const base = template?.sections ?? []
  return data['가져온 추가 내용'] ? [...base, { title: '가져온 추가 내용', multiple: true, fields: [{ label: '내용', type: 'textarea', fullWidth: true }] }] : base
}
function hasMarkdownOverride(data: Record<string, unknown>): boolean {
  const rows = data['문서 본문']
  const row = Array.isArray(rows) && rows.length === 1 ? rows[0] : undefined
  return !!row && typeof row === 'object' && !Array.isArray(row) && (row as Record<string, unknown>)['__markdown_override'] === 'true'
}

export function workDocumentSections(template: FormTemplate | null, data: Record<string, unknown>): FormSection[] {
  return data['문서 본문'] && !hasOriginalForm(template?.sections ?? [], data)
    ? documentSections : originalWorkDocumentSections(template, data)
}

export async function resultImageUrl(src: string): Promise<string> {
  if (!src.startsWith('data:image/')) return src
  const response = await fetch(src)
  const blob = await response.blob()
  const file = new FormData()
  file.append('file', blob, `image.${blob.type.split('/')[1] || 'png'}`)
  const { data } = await api.post<{ url: string }>('/pm/uploads', file)
  return data.url
}

async function uploadEmbeddedDataImages(value: string): Promise<string> {
  const sources = [...new Set(value.match(/data:image\/[a-zA-Z0-9.+-]+;base64,[a-zA-Z0-9+/=]+/g) ?? [])]
  let result = value
  for (const source of sources) result = result.replaceAll(source, await resultImageUrl(source))
  return result
}

export async function prepareWorkDocumentData(template: FormTemplate, values: WorkDocumentData): Promise<FormEntry['data']> {
  const data = JSON.parse(JSON.stringify(values)) as FormEntry['data']
  for (const section of workDocumentSections(template, data)) {
    const stored = data[section.title]
    const items = Array.isArray(stored) ? stored : stored ? [stored] : []
    for (let rowIndex = 0; rowIndex < items.length; rowIndex += 1) {
      const row = items[rowIndex]
      if (!row) continue
      for (const field of section.fields) {
        const value = row[field.label]
        if (field.required && (!value || (Array.isArray(value) && value.length === 0))) {
          const position = section.multiple ? ` ${rowIndex + 1}번째 행의` : ''
          throw new Error(`[${section.title}]${position} "${field.label}"은(는) 필수 입력입니다.`)
        }
        if (field.type === 'image') row[field.label] = await Promise.all((Array.isArray(value) ? value : value ? [value] : []).map(resultImageUrl))
        else if (typeof value === 'string') row[field.label] = await uploadEmbeddedDataImages(value)
      }
    }
  }
  const original = originalWorkDocumentSections(template, data)
  return hasOriginalForm(original, data)
    ? synchronizedDocument(template.title, original, data, window.location.origin)
    : data
}

export function useWorkDocumentExport(
  detailRow: Ref<FormEntry | null>, template: Ref<FormTemplate | null>,
  sections: Readonly<Ref<FormSection[]>>, detailLoading: Readonly<Ref<boolean>>,
) {
  const $q = useQuasar()
  function normalizedFileLabel(value: string): string {
    return value.replace(/[\s_*/\\()]/g, '').toLocaleLowerCase()
  }

  function detailValueForLabels(labels: string[]): string {
    const wanted = new Set(labels.map(normalizedFileLabel))
    for (const sectionData of Object.values(detailRow.value?.data ?? {})) {
      const records = Array.isArray(sectionData) ? sectionData : [sectionData]
      for (const record of records) {
        if (!record || typeof record !== 'object' || Array.isArray(record)) continue
        for (const [label, value] of Object.entries(record as Record<string, unknown>)) {
          if (label.endsWith('__format') || !wanted.has(normalizedFileLabel(label))) continue
          if (typeof value === 'string' || typeof value === 'number') {
            if (String(value).trim()) return String(value).trim()
          }
        }
      }
    }
    return ''
  }

  function exportDatePart(value: string): string {
    const numeric = value.match(/(20\d{2})[./-](\d{1,2})[./-](\d{1,2})/)
    const korean = value.match(/(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일/)
    const [, year, month, day] = numeric ?? korean ?? []
    if (year && month && day) return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return ''
    const parts = new Intl.DateTimeFormat('en', {
      timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(parsed)
    const dateYear = parts.find(part => part.type === 'year')?.value
    const dateMonth = parts.find(part => part.type === 'month')?.value
    const dateDay = parts.find(part => part.type === 'day')?.value
    return dateYear && dateMonth && dateDay ? `${dateYear}-${dateMonth}-${dateDay}` : ''
  }

  function exportDocumentFileName(format: 'hwp' | 'docx'): string {
    const templateName = template.value?.title || '작업템플릿'
    const serviceName = detailValueForLabels(['서비스 명', '서비스명']) || '서비스'
    const workDate = detailValueForLabels(['작업 일시', '작업 기간 (시작)', '작업기간 시작'])
    const date = exportDatePart(workDate || detailRow.value?.createdAt || '') || '날짜미상'
    const safePart = (value: string, fallback: string) => value
      .replace(/[<>:"|?*]/g, '_')
      .replaceAll('/', '_')
      .replaceAll('\\', '_')
      .split('').map(character => character.charCodeAt(0) < 32 ? '_' : character).join('')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 100)
      .replace(/[. ]+$/, '') || fallback
    return `${safePart(templateName, '작업템플릿')}_${safePart(serviceName, '서비스')}_${date}.${format}`
  }

  const exportingDocument = ref(false)
  async function exportDetailFile(format: 'hwp' | 'docx') {
    if (detailLoading.value || !detailRow.value || !template.value || exportingDocument.value) return
    const title = template.value.title
    const filename = exportDocumentFileName(format)
    const markdown = formEntryMarkdown(title, sections.value, detailRow.value.data, window.location.origin)
    const originalName = detailRow.value.originalFile?.originalName ?? ''
    const sourceExtension = originalName.includes('.') ? originalName.slice(originalName.lastIndexOf('.')).toLowerCase() : ''
    if (format === 'hwp' && sourceExtension === '.pdf') {
      $q.notify({ type: 'info', timeout: 4500, message: 'PDF 원본은 원본 PDF로 다운로드할 수 있으며, HWP는 수정된 항목을 기준으로 재생성됩니다.' })
    }
    exportingDocument.value = true
    try {
      const original = originalWorkDocumentSections(template.value, detailRow.value.data)
      const original_form = !hasMarkdownOverride(detailRow.value.data) && hasOriginalForm(original, detailRow.value.data)
        ? { title, sections: original, data: detailRow.value.data } : undefined
      const { data } = await api.post<Blob>('/form-entries/export-document', { markdown, format, original_form }, { responseType: 'blob', timeout: 120000 })
      if (exportFile(filename, data) !== true) throw new Error('download failed')
    } catch {
      $q.notify({ type: 'negative', message: '파일 내보내기에 실패했습니다. 사진이 정상적으로 표시되는지 확인한 뒤 다시 시도해 주세요.' })
    } finally { exportingDocument.value = false }
  }

  async function downloadOriginalFile() {
    const originalFile = detailRow.value?.originalFile
    if (!originalFile || exportingDocument.value) return
    exportingDocument.value = true
    try {
      await downloadAttachment(originalFile.url, originalFile.originalName)
    } catch {
      $q.notify({ type: 'negative', message: '원본 파일 다운로드에 실패했습니다.' })
    } finally {
      exportingDocument.value = false
    }
  }

  function exportDetailMarkdown() {
    if (detailLoading.value || !detailRow.value || !template.value) return
    const title = template.value.title
    const markdown = formEntryMarkdown(title, sections.value, detailRow.value.data, window.location.origin)
    const result = exportFile(markdownFileName(title, detailRow.value.id), markdown, 'text/markdown;charset=utf-8')
    if (result !== true) {
      $q.notify({ type: 'negative', message: '파일을 내려받지 못했습니다. 브라우저의 다운로드 설정을 확인해 주세요.' })
    }
  }

  return { exportingDocument, exportDetailFile, downloadOriginalFile, exportDetailMarkdown }
}
