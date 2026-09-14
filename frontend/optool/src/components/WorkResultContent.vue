<template>
  <div class="work-result-content" @click="openImage" @keydown.enter="openImage" @keydown.space="openImage" v-html="rendered" />
  <q-dialog v-model="previewOpen" @hide="previewSource = ''">
    <q-card class="image-preview-card">
      <q-bar><span>이미지 크게 보기</span><q-space /><q-btn flat round dense icon="close" aria-label="이미지 닫기" v-close-popup /></q-bar>
      <img :src="previewSource" :alt="previewAlt" class="image-preview-full" />
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked, Renderer } from 'marked'
const props = defineProps<{ content: string; sectionTitles?: string[] }>()
const previewOpen = ref(false)
const previewSource = ref('')
const previewAlt = ref('')
function openImage(event: MouseEvent | KeyboardEvent) {
  if (!(event.target instanceof HTMLImageElement)) return
  event.preventDefault()
  event.stopPropagation()
  previewSource.value = event.target.currentSrc || event.target.src
  previewAlt.value = event.target.alt || '문서 이미지 확대'
  previewOpen.value = true
}
function escapeHtml(text: string) { return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') }
function normalizeHeading(text: string) {
  return text.replace(/<[^>]+>/g, '').replace(/\s/g, '').trim()
}
function safeUrl(href: string, image: boolean): boolean {
  if (image && /^data:image\/(png|jpeg|gif|webp);base64,/i.test(href)) return true
  try { return (image ? ['http:', 'https:'] : ['http:', 'https:', 'mailto:']).includes(new URL(href, window.location.origin).protocol) }
  catch { return false }
}
function lineText(line: string): string {
  const template = document.createElement('template')
  template.innerHTML = line
  return (template.content.textContent ?? '').replace(/\\\|/g, '|').trim()
}
function pipeRow(line: string): string[] | null {
  const text = lineText(line)
  if (!text.startsWith('|') || !text.endsWith('|')) return null
  return text.slice(1, -1).split('|').map(cell => cell.trim())
}
function isPipeSeparator(cells: string[] | null): cells is string[] {
  return cells !== null && cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell))
}
function nestedTableHtml(rows: string[][]): string {
  const columns = Math.max(...rows.map(row => row.length))
  const normalize = (row: string[]) => {
    if (row.length > columns) {
      return [...row.slice(0, columns - 1), row.slice(columns - 1).join(' | ')]
    }
    return [...row, ...Array.from({ length: columns - row.length }, () => '')]
  }
  const renderRow = (row: string[], tag: 'th' | 'td') => `<tr>${normalize(row).map(value => `<${tag}>${escapeHtml(value)}</${tag}>`).join('')}</tr>`
  return `<div class="work-table-scroll work-table-scroll--nested" tabindex="0" role="region" aria-label="상세 내용 표, 가로 스크롤 가능"><table><thead>${renderRow(rows[0] ?? [], 'th')}</thead><tbody>${rows.slice(1).map(row => renderRow(row, 'td')).join('')}</tbody></table></div>`
}
function renderNestedTables(body: string): string {
  if (!body.includes('<br')) return body
  const root = document.createElement('tbody')
  root.innerHTML = body
  root.querySelectorAll<HTMLElement>('td, th').forEach(cell => {
    let lines = cell.innerHTML.split(/<br\s*\/?\s*>/i)
    let offset = 0
    while (offset < lines.length - 1) {
      const header = pipeRow(lines[offset] ?? '')
      const separator = pipeRow(lines[offset + 1] ?? '')
      if (!header || !isPipeSeparator(separator)) {
        offset += 1
        continue
      }
      const tableLines: string[] = [lines[offset] ?? '']
      let end = offset + 2
      while (end < lines.length) {
        const row = pipeRow(lines[end] ?? '')
        if (!row) break
        tableLines.push(lines[end] ?? '')
        end += 1
      }
      if (tableLines.length < 2) {
        offset += 1
        continue
      }
      const parsedRows = tableLines.map(line => pipeRow(line)).filter((row): row is string[] => Boolean(row))
      const before = lines.slice(0, offset).filter(line => line.trim())
      const after = lines.slice(end).filter(line => line.trim())
      const nested = nestedTableHtml(parsedRows)
      cell.innerHTML = [...before, nested, ...after].join('<br>')
      lines = cell.innerHTML.split(/<br\s*\/?\s*>/i)
      offset = before.length + 1
    }
  })
  return root.innerHTML
}
const renderer = new Renderer()
renderer.heading = (text, level) => {
  const sectionIndex = level === 2
    ? (props.sectionTitles ?? []).findIndex(title => normalizeHeading(title) === normalizeHeading(text))
    : -1
  const attributes = sectionIndex >= 0
    ? ` id="document-section-${sectionIndex}" data-section-index="${sectionIndex}"`
    : ''
  return `<h${level}${attributes}>${text}</h${level}>\n`
}
renderer.table = (header, body) => `<div class="work-table-scroll" tabindex="0" role="region" aria-label="문서 표, 가로 스크롤 가능"><table><thead>${header}</thead><tbody>${renderNestedTables(body)}</tbody></table></div>`
renderer.html = (html) => /^<br\s*\/?\s*>$/i.test(html.trim()) ? '<br>' : escapeHtml(html)
renderer.link = (href, _title, text) => href && safeUrl(href, false) ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${text}</a>` : text
renderer.image = (href, _title, text) => href && safeUrl(href, true) ? `<img src="${escapeHtml(href)}" alt="${escapeHtml(text)}" loading="lazy" role="button" tabindex="0" aria-label="${escapeHtml(text || '문서 이미지')} 크게 보기" title="클릭하여 크게 보기">` : escapeHtml(text)
const rendered = computed(() => marked(props.content, { renderer, breaks: true }))
</script>
<style scoped>
.work-result-content { overflow-wrap: anywhere; font-size: 14px; line-height: 1.8; min-width: 0; max-width: 100%; }
.work-result-content :deep(img) { display: block; max-width: 100%; height: auto; margin: 12px 0; border-radius: 6px; cursor: zoom-in; }
.work-result-content :deep(img:focus-visible) { outline: 2px solid var(--q-primary); outline-offset: 4px; }
.image-preview-card { width: 94vw; max-width: 94vw; max-height: 94vh; }
.image-preview-full { display: block; width: 100%; height: calc(90vh - 40px); object-fit: contain; }
.work-result-content :deep(p) { margin: 0 0 14px; white-space: pre-wrap; }
.work-result-content :deep(pre) { overflow: auto; padding: 12px; background: #f1f5f9; color: #1e293b; border-radius: 6px; }
.work-result-content :deep(h1) { font-size: 18px; line-height: 1.5; margin: 16px 0 8px; text-align: center; }
.work-result-content :deep(h2) { font-size: 24px; line-height: 1.45; margin: 32px 0 14px; text-align: center; font-weight: 700; }
.work-result-content :deep(h3) { font-size: 18px; line-height: 1.5; margin: 20px 0 10px; text-align: center; }
.work-result-content :deep(h4), .work-result-content :deep(h5), .work-result-content :deep(h6) { text-align: center; }
.work-result-content :deep(.work-table-scroll) { display: block; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; overflow-x: auto; overflow-y: hidden; margin: 16px 0; border: 1px solid #cbd5e1; border-radius: 8px; }
.work-result-content :deep(.work-table-scroll--nested) { margin: 10px 0; border-color: #94a3b8; }
.work-result-content :deep(.work-table-scroll:focus-visible) { outline: 2px solid var(--q-primary); outline-offset: 3px; }
.work-result-content :deep(table) { width: 100%; max-width: 100%; min-width: 100%; border-collapse: collapse; table-layout: auto; }
.work-result-content :deep(td), .work-result-content :deep(th) { min-width: 0; border: 1px solid #cbd5e1; padding: 12px 16px; vertical-align: top; white-space: normal; word-break: normal; overflow-wrap: anywhere; }
.work-result-content :deep(th) { background: #64748b0d; font-weight: 600; text-align: center; }
</style>
