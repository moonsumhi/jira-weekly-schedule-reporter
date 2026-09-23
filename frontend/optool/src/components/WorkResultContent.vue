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
const tableHtmlTags = new Set(['table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'br', 'p', 'div', 'span', 'strong', 'em', 'b', 'i', 'u', 'code', 'pre', 'a', 'img'])
const dangerousHtmlTags = new Set(['script', 'style', 'iframe', 'object', 'embed', 'svg', 'math'])

function sanitizeTableHtml(html: string): string {
  const template = document.createElement('template')
  template.innerHTML = html

  const clean = (parent: ParentNode) => {
    Array.from(parent.childNodes).forEach((node) => {
      if (node.nodeType !== Node.ELEMENT_NODE) return
      const element = node as HTMLElement
      const tag = element.tagName.toLowerCase()
      if (dangerousHtmlTags.has(tag)) {
        element.remove()
        return
      }
      if (!tableHtmlTags.has(tag)) {
        clean(element)
        const fragment = document.createDocumentFragment()
        while (element.firstChild) fragment.append(element.firstChild)
        element.replaceWith(fragment)
        return
      }

      const allowedAttributes = tag === 'img'
        ? new Set(['src', 'alt', 'title'])
        : tag === 'a'
          ? new Set(['href', 'title'])
          : new Set(['colspan', 'rowspan', 'align'])
      Array.from(element.attributes).forEach((attribute) => {
        if (!allowedAttributes.has(attribute.name)) element.removeAttribute(attribute.name)
      })
      if (tag === 'img') {
        const source = element.getAttribute('src') ?? ''
        if (!source || !safeUrl(source, true)) {
          element.remove()
          return
        }
      }
      if (tag === 'a') {
        const href = element.getAttribute('href') ?? ''
        if (!href || !safeUrl(href, false)) {
          element.removeAttribute('href')
        } else {
          element.setAttribute('target', '_blank')
          element.setAttribute('rel', 'noopener noreferrer')
        }
      }
      for (const attribute of ['colspan', 'rowspan']) {
        const value = element.getAttribute(attribute)
        if (value !== null && !/^\d+$/.test(value)) element.removeAttribute(attribute)
      }
      clean(element)
    })
  }

  clean(template.content)
  const renderedHtml = template.innerHTML.trim()
  if (!renderedHtml) return ''

  // Toast UI stores a table inserted into a Markdown field as raw HTML. Keep
  // it as a styled nested table instead of escaping the tags as plain text.
  const hasDirectTable = Array.from(template.content.childNodes).some((node) =>
    node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName.toLowerCase() === 'table',
  )
  return hasDirectTable
    ? `<div class="work-table-scroll work-table-scroll--nested" tabindex="0" role="region" aria-label="상세 내용 표, 가로 스크롤 가능">${renderedHtml}</div>`
    : renderedHtml
}

function isTableHtml(html: string): boolean {
  return /<\/?(?:table|thead|tbody|tfoot|tr|th|td)\b/i.test(html)
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
  return `<div class="work-table-scroll work-table-scroll--nested" tabindex="0" role="region" aria-label="상세 내용 표, 가로 스크롤 가능"><table><thead>${renderRow(rows[0] ?? [], 'th')}</thead><tbody>${rows.slice(2).map(row => renderRow(row, 'td')).join('')}</tbody></table></div>`
}
function splitMarkdownRow(line: string): string[] | null {
  const trimmed = line.trim()
  // Nested rows are escaped before they are placed in the outer table cell.
  const normalized = trimmed.replace(/^\\\|/, '|').replace(/\\\|$/, '|')
  if (!normalized.startsWith('|') || !normalized.endsWith('|')) return null
  const cells: string[] = []
  let current = ''
  let escaped = false
  for (const char of normalized.slice(1, -1)) {
    if (char === '|' && !escaped) {
      cells.push(current.trim())
      current = ''
      continue
    }
    current += char
    escaped = char === '\\' && !escaped
    if (char !== '\\') escaped = false
  }
  cells.push(current.trim())
  return cells
}

function splitNestedMarkdownRow(line: string): string[] | null {
  const trimmed = line.trim()
  const normalized = trimmed.replace(/^\\\|/, '|').replace(/\\\|$/, '|')
  if (!normalized.startsWith('|') || !normalized.endsWith('|')) return null
  // The outer table escapes nested separators. Once isolated, those escaped
  // pipes are the nested table's own column delimiters.
  return normalized.slice(1, -1).split(/\\\||\|/).map(cell => cell.trim())
}

function isNestedSeparator(cells: string[] | null): cells is string[] {
  return cells !== null && cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell))
}

function protectRawTableHtml(markdown: string): { source: string; replacements: NestedTableReplacement[] } {
  const replacements: NestedTableReplacement[] = []
  let tokenIndex = 0
  const source = markdown.replace(/<table\b[^>]*>[\s\S]*?<\/table\s*>/gi, (table) => {
    const token = `workrawtabletoken${tokenIndex++}`
    replacements.push({ token, html: sanitizeTableHtml(table) })
    return token
  })
  return { source, replacements }
}

function nestedMarkdownTableHtml(rows: string[][]): string {
  const columns = Math.max(...rows.map(row => row.length))
  const normalize = (row: string[]) => row.length > columns
    ? [...row.slice(0, columns - 1), row.slice(columns - 1).join(' | ')]
    : [...row, ...Array.from({ length: columns - row.length }, () => '')]
  const renderInline = (value: string) => marked.parseInline(value.replace(/\\\|/g, '|'), { renderer, breaks: true })
  const renderRow = (row: string[], tag: 'th' | 'td') => `<tr>${normalize(row).map(value => `<${tag}>${renderInline(value)}</${tag}>`).join('')}</tr>`
  return `<div class="work-table-scroll work-table-scroll--nested" tabindex="0" role="region" aria-label="Nested table"><table><thead>${renderRow(rows[0] ?? [], 'th')}</thead><tbody>${rows.slice(2).map(row => renderRow(row, 'td')).join('')}</tbody></table></div>`
}

interface NestedTableReplacement { token: string; html: string }

function nestedMarkdownRowEnd(parts: string[], start: number): number | null {
  for (let end = start + 1; end <= parts.length; end += 1) {
    // tableCellValue converts each row-ending pipe to `\\|`. A cell may
    // contain <br> followed by an image or text, so the row can span several
    // parts and cannot be split at every <br>.
    if (/\\\|\s*$/.test(parts[end - 1] ?? '')) return end
  }
  return null
}

function protectNestedMarkdownTables(markdown: string): { source: string; replacements: NestedTableReplacement[] } {
  const replacements: NestedTableReplacement[] = []
  let tokenIndex = 0
  const source = markdown.split(/\r?\n/).map(line => {
    const outerCells = splitMarkdownRow(line)
    if (!outerCells) return line
    const cells = outerCells.map(cell => {
      const parts = cell.split(/<br\s*\/?\s*>/i)
      let index = 0
      while (index < parts.length) {
        const headerEnd = nestedMarkdownRowEnd(parts, index)
        if (headerEnd === null) {
          index += 1
          continue
        }
        const header = splitNestedMarkdownRow(parts.slice(index, headerEnd).join('<br>'))
        const separatorEnd = nestedMarkdownRowEnd(parts, headerEnd)
        if (separatorEnd === null) {
          index += 1
          continue
        }
        const separator = splitNestedMarkdownRow(parts.slice(headerEnd, separatorEnd).join('<br>'))
        if (!header || !isNestedSeparator(separator)) {
          index += 1
          continue
        }
        const rows: string[][] = [header, separator]
        let end = separatorEnd
        while (end < parts.length) {
          const rowEnd = nestedMarkdownRowEnd(parts, end)
          if (rowEnd === null) break
          const row = splitNestedMarkdownRow(parts.slice(end, rowEnd).join('<br>'))
          if (!row) break
          rows.push(row)
          end = rowEnd
        }
        const token = `worknestedtabletoken${tokenIndex++}`
        replacements.push({ token, html: nestedMarkdownTableHtml(rows) })
        parts.splice(index, end - index, token)
        index += 1
      }
      return parts.join('<br>')
    })
    return `| ${cells.join(' | ')} |`
  }).join('\n')
  return { source, replacements }
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
renderer.table = (header, body) => {
  const headerText = header.replace(/<[^>]+>/g, ' ')
  const normalizedHeaderText = headerText.replace(/\s+/g, '')
  const tableClasses = [
    /제목/.test(normalizedHeaderText) && /리스크/.test(normalizedHeaderText) ? 'work-table-scroll--development' : '',
    /시작시간/.test(normalizedHeaderText) && /종료시간/.test(normalizedHeaderText) && /세부작업내용/.test(normalizedHeaderText)
      ? 'work-table-scroll--work-schedule'
      : '',
    /사전점검사항/.test(normalizedHeaderText) && /점검결과/.test(normalizedHeaderText) && /비고/.test(normalizedHeaderText)
      ? 'work-table-scroll--precheck'
      : '',
    /설명/.test(normalizedHeaderText) && /테스트데이터/.test(normalizedHeaderText) && /예상결과/.test(normalizedHeaderText)
      ? 'work-table-scroll--test-case'
      : '',
  ].filter(Boolean)
  const tableClass = tableClasses.length ? ` ${tableClasses.join(' ')}` : ''
  return `<div class="work-table-scroll${tableClass}" tabindex="0" role="region" aria-label="문서 표, 가로 스크롤 가능"><table><thead>${header}</thead><tbody>${renderNestedTables(body)}</tbody></table></div>`
}
renderer.html = (html) => {
  const trimmed = html.trim()
  if (/^<br\s*\/?\s*>$/i.test(trimmed)) return '<br>'
  return isTableHtml(trimmed) ? sanitizeTableHtml(html) : escapeHtml(html)
}
renderer.link = (href, _title, text) => href && safeUrl(href, false) ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${text}</a>` : text
renderer.image = (href, _title, text) => href && safeUrl(href, true) ? `<img src="${escapeHtml(href)}" alt="${escapeHtml(text)}" loading="lazy" role="button" tabindex="0" aria-label="${escapeHtml(text || '문서 이미지')} 크게 보기" title="클릭하여 크게 보기">` : escapeHtml(text)
const rendered = computed(() => {
  const rawTables = protectRawTableHtml(props.content ?? '')
  const prepared = protectNestedMarkdownTables(rawTables.source)
  let html = marked(prepared.source, { renderer, breaks: true })
  for (const replacement of [...rawTables.replacements, ...prepared.replacements]) {
    html = html.split(replacement.token).join(replacement.html)
  }
  return html
})
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
.work-result-content :deep(.work-table-scroll--nested) { margin: 10px 0; border-color: #94a3b8; overflow-x: hidden; }
.work-result-content :deep(.work-table-scroll:focus-visible) { outline: 2px solid var(--q-primary); outline-offset: 3px; }
.work-result-content :deep(table) { width: 100%; max-width: 100%; min-width: 100%; border-collapse: collapse; table-layout: auto; }
.work-result-content :deep(.work-table-scroll--development table) { table-layout: fixed; }
.work-result-content :deep(.work-table-scroll--development th:first-child), .work-result-content :deep(.work-table-scroll--development td:first-child) { width: 5%; }
.work-result-content :deep(.work-table-scroll--development th:nth-child(2)), .work-result-content :deep(.work-table-scroll--development td:nth-child(2)) { width: 15%; }
.work-result-content :deep(.work-table-scroll--development th:nth-child(3)), .work-result-content :deep(.work-table-scroll--development td:nth-child(3)) { width: 6%; }
.work-result-content :deep(.work-table-scroll--work-schedule table) { table-layout: fixed; }
.work-result-content :deep(.work-table-scroll--work-schedule th:first-child), .work-result-content :deep(.work-table-scroll--work-schedule td:first-child) { width: 8%; }
.work-result-content :deep(.work-table-scroll--work-schedule th:nth-child(2)), .work-result-content :deep(.work-table-scroll--work-schedule td:nth-child(2)) { width: 9%; }
.work-result-content :deep(.work-table-scroll--work-schedule th:nth-child(3)), .work-result-content :deep(.work-table-scroll--work-schedule td:nth-child(3)) { width: 9%; }
.work-result-content :deep(.work-table-scroll--work-schedule th:nth-child(4)), .work-result-content :deep(.work-table-scroll--work-schedule td:nth-child(4)) { width: 62%; }
.work-result-content :deep(.work-table-scroll--work-schedule th:nth-child(5)), .work-result-content :deep(.work-table-scroll--work-schedule td:nth-child(5)) { width: 12%; }
.work-result-content :deep(.work-table-scroll--precheck table) { table-layout: fixed; }
.work-result-content :deep(.work-table-scroll--precheck th:first-child), .work-result-content :deep(.work-table-scroll--precheck td:first-child) { width: 6%; }
.work-result-content :deep(.work-table-scroll--precheck th:nth-child(2)), .work-result-content :deep(.work-table-scroll--precheck td:nth-child(2)) { width: 47%; }
.work-result-content :deep(.work-table-scroll--precheck th:nth-child(3)), .work-result-content :deep(.work-table-scroll--precheck td:nth-child(3)) { width: 41%; }
.work-result-content :deep(.work-table-scroll--precheck th:nth-child(4)), .work-result-content :deep(.work-table-scroll--precheck td:nth-child(4)) { width: 6%; }
.work-result-content :deep(.work-table-scroll--test-case table) { table-layout: fixed; }
.work-result-content :deep(.work-table-scroll--test-case th:first-child), .work-result-content :deep(.work-table-scroll--test-case td:first-child) { width: 6%; }
.work-result-content :deep(.work-table-scroll--test-case th:nth-child(2)), .work-result-content :deep(.work-table-scroll--test-case td:nth-child(2)) { width: 24%; }
.work-result-content :deep(.work-table-scroll--test-case th:nth-child(3)), .work-result-content :deep(.work-table-scroll--test-case td:nth-child(3)) { width: 18%; }
.work-result-content :deep(.work-table-scroll--test-case th:nth-child(4)), .work-result-content :deep(.work-table-scroll--test-case td:nth-child(4)) { width: 24%; }
.work-result-content :deep(.work-table-scroll--test-case th:nth-child(5)), .work-result-content :deep(.work-table-scroll--test-case td:nth-child(5)) { width: 28%; }
.work-result-content :deep(.work-table-scroll--nested table) { width: 100%; max-width: 100%; min-width: 0; table-layout: fixed; }
.work-result-content :deep(td), .work-result-content :deep(th) { min-width: 0; border: 1px solid #cbd5e1; padding: 12px 16px; vertical-align: top; white-space: normal; word-break: normal; overflow-wrap: anywhere; }
.work-result-content :deep(.work-table-scroll--nested td), .work-result-content :deep(.work-table-scroll--nested th) { width: auto; max-width: 100%; overflow: hidden; }
.work-result-content :deep(.work-table-scroll--nested th:first-child), .work-result-content :deep(.work-table-scroll--nested td:first-child) { width: 8%; }
.work-result-content :deep(.work-table-scroll--nested th:nth-child(3)), .work-result-content :deep(.work-table-scroll--nested td:nth-child(3)) { width: 24.5%; }
.work-result-content :deep(.work-table-scroll--nested img) { display: block; width: auto !important; max-width: 100% !important; min-width: 0 !important; height: auto !important; object-fit: contain; }
.work-result-content :deep(th) { background: #64748b0d; font-weight: 600; text-align: center; }
</style>
