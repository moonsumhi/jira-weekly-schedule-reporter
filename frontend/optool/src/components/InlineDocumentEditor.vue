<template>
  <div ref="editorRoot" class="inline-editor" @keydown.capture="handleKeydown">
  <section v-for="(section, sectionIndex) in sections" :key="section.title" :data-section-index="sectionIndex" class="inline-section">
    <h2>{{ displaySectionTitle(section) }}</h2>

    <div v-if="isImportedExtraSection(section)" class="imported-extra-editor-columns">
      <article class="imported-extra-editor-panel">
        <h3>원본 확인</h3>
        <MarkdownEditor
          :model-value="importedExtraPanels(section).original"
          placeholder="원본 내용"
          @uploading="setImportedExtraUploading('original', $event)"
          @update:model-value="updateImportedExtraPanel(section, 'original', $event)"
        />
      </article>
    </div>
    <div v-else class="inline-table-scroll">
      <table v-if="section.multiple">
        <thead>
          <tr><th class="number-cell">No.</th><th v-for="field in visibleFields(section)" :key="field.label">{{ field.label }}</th><th class="action-cell" /></tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows(section)" :key="rowIndex">
            <td class="number-cell">{{ rowIndex + 1 }}</td>
            <td v-for="field in visibleFields(section)" :key="field.label"
              :class="{ 'editor-cell': row[`${field.label}__format`] === 'markdown' }"
              tabindex="0" @paste="pasteCellImage(section, rowIndex, field, $event)">
              <q-select v-if="field.type === 'select'" :model-value="row[field.label]" :options="field.options ?? []" borderless dense options-dense @update:model-value="updateField(row, field.label, $event)" />
              <q-checkbox v-else-if="field.type === 'boolean'" :model-value="Boolean(row[field.label])" dense @update:model-value="updateField(row, field.label, $event)" />
              <div v-else-if="field.type === 'image'" class="image-cell">
                <img v-for="(src, imageIndex) in imageValues(row[field.label])" :key="imageIndex" :src="src" :alt="field.label" />
                <span v-if="!imageValues(row[field.label]).length" class="paste-hint">이미지를 붙여넣을 수 있습니다.</span>
              </div>
              <MarkdownEditor v-else-if="isMarkdownEditor(field, row)"
                :model-value="scalarValue(row[field.label])?.toString() ?? ''"
                :placeholder="`${field.label}`"
                @update:model-value="updateField(row, field.label, $event)" />
              <div v-else class="content-cell">
                <q-btn
                  v-if="canUseRichEditor(field)"
                  flat dense no-caps color="primary" icon="table_chart"
                  label="표/이미지 입력" class="rich-editor-button"
                  @click="enableMarkdownEditor(row, field.label)"
                />
                <q-input :model-value="scalarValue(row[field.label])" borderless dense autogrow :type="inputType(field)" :placeholder="`${field.label} 입력`" @update:model-value="updateField(row, field.label, $event ?? '')" />
              </div>
            </td>
            <td class="action-cell"><q-btn flat round dense icon="delete_outline" color="grey-7" :aria-label="`${rowIndex + 1}행 삭제`" @click="removeRow(section, rowIndex)" /></td>
          </tr>
          <tr v-if="!rows(section).length"><td :colspan="visibleFields(section).length + 2" class="empty-cell">등록된 항목이 없습니다.</td></tr>
        </tbody>
      </table>

      <table v-else>
        <thead><tr><th class="label-column">항목</th><th>내용</th></tr></thead>
        <tbody>
          <tr v-for="field in visibleFields(section)" :key="field.label">
            <th class="field-label">{{ field.label }}</th>
            <td :class="{ 'editor-cell': record(section)[`${field.label}__format`] === 'markdown' }"
              tabindex="0" @paste="pasteCellImage(section, 0, field, $event)">
              <q-select v-if="field.type === 'select'" :model-value="record(section)[field.label]" :options="field.options ?? []" borderless dense options-dense @update:model-value="updateField(record(section), field.label, $event)" />
              <q-checkbox v-else-if="field.type === 'boolean'" :model-value="Boolean(record(section)[field.label])" dense @update:model-value="updateField(record(section), field.label, $event)" />
              <div v-else-if="field.type === 'image'" class="image-cell">
                <img v-for="(src, imageIndex) in imageValues(record(section)[field.label])" :key="imageIndex" :src="src" :alt="field.label" />
                <span v-if="!imageValues(record(section)[field.label]).length" class="paste-hint">이미지를 붙여넣을 수 있습니다.</span>
              </div>
              <MarkdownEditor v-else-if="isMarkdownEditor(field, record(section))"
                :model-value="scalarValue(record(section)[field.label])?.toString() ?? ''"
                :placeholder="`${field.label}`"
                @update:model-value="updateField(record(section), field.label, $event)" />
              <div v-else class="content-cell">
                <q-btn
                  v-if="canUseRichEditor(field)"
                  flat dense no-caps color="primary" icon="table_chart"
                  label="표/이미지 입력" class="rich-editor-button"
                  @click="enableMarkdownEditor(record(section), field.label)"
                />
                <q-input :model-value="scalarValue(record(section)[field.label])" borderless dense autogrow :type="inputType(field)" :placeholder="`${field.label} 입력`" @update:model-value="updateField(record(section), field.label, $event ?? '')" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <q-btn v-if="section.multiple" outline dense no-caps color="primary" icon="add" :label="`${displaySectionTitle(section)} 항목 추가`" class="add-row" @click="addRow(section)" />
  </section>
  </div>
</template>

<script setup lang="ts">
import type { FormField, FormSection } from 'src/services/formTemplates'
import MarkdownEditor from './MarkdownEditor.vue'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type Row = Record<string, unknown>
type FormData = Record<string, Row | Row[]>
defineProps<{ sections: FormSection[] }>()
const model = defineModel<FormData>({ required: true })
const emit = defineEmits<{ uploading: [value: boolean] }>()
const editorRoot = ref<HTMLElement | null>(null)
const undoHistory: FormData[] = []
const redoHistory: FormData[] = []
let editorHeightFrame: number | null = null
let layoutObserver: ResizeObserver | null = null
let contentObserver: MutationObserver | null = null

function syncEditorHeights() {
  const root = editorRoot.value
  if (!root) return

  const rows = Array.from(root.querySelectorAll<HTMLTableRowElement>('tbody tr'))
  for (const row of rows) {
    const cells = Array.from(row.querySelectorAll<HTMLElement>('td'))
      .filter(cell => cell.querySelector('.toastui-editor-defaultUI'))
    if (cells.length < 2) continue

    const editors = cells
      .map(cell => cell.querySelector<HTMLElement>('.toastui-editor-defaultUI'))
      .filter((editor): editor is HTMLElement => editor !== null)
    if (editors.length < 2) continue

    cells.forEach(cell => cell.style.removeProperty('--editor-row-height'))
    editors.forEach(editor => editor.style.setProperty('height', 'auto', 'important'))
    // Toast UI updates the contenteditable DOM after its Vue model event. Measure
    // the content area as well as the editor shell so the longer side wins even
    // when the editor was previously constrained to the shorter row height.
    const editorHeights = editors.map((editor) => {
      const content = editor.querySelector<HTMLElement>('.toastui-editor-contents, .ProseMirror')
      const contentHeight = content?.scrollHeight ?? 0
      return Math.max(editor.getBoundingClientRect().height, editor.scrollHeight, contentHeight)
    })
    const maxHeight = Math.max(...editorHeights)
    if (!Number.isFinite(maxHeight) || maxHeight <= 0) continue
    const rowHeight = `${Math.ceil(maxHeight)}px`
    cells.forEach(cell => cell.style.setProperty('--editor-row-height', rowHeight))
    editors.forEach(editor => editor.style.setProperty('height', rowHeight, 'important'))
  }
}

function queueEditorHeightSync() {
  if (editorHeightFrame !== null) cancelAnimationFrame(editorHeightFrame)
  editorHeightFrame = requestAnimationFrame(() => {
    // The editor emits its change event before ProseMirror has painted the new
    // paragraph/image. A second frame makes the measurement deterministic.
    editorHeightFrame = requestAnimationFrame(() => {
      editorHeightFrame = null
      syncEditorHeights()
    })
  })
}
function snapshot(): FormData { return JSON.parse(JSON.stringify(model.value)) as FormData }
function checkpoint() {
  undoHistory.push(snapshot())
  if (undoHistory.length > 100) undoHistory.shift()
  redoHistory.length = 0
}
function updateField(target: Row, field: string, value: unknown) {
  if (target[field] === value) return
  checkpoint()
  target[field] = value
}
function undo() {
  const previous = undoHistory.pop()
  if (!previous) return
  redoHistory.push(snapshot())
  model.value = previous
}
function redo() {
  const next = redoHistory.pop()
  if (!next) return
  undoHistory.push(snapshot())
  model.value = next
}
function handleKeydown(event: KeyboardEvent) {
  if (!event.ctrlKey || event.key.toLowerCase() !== 'z') return
  event.preventDefault()
  event.stopPropagation()
  if (event.shiftKey) redo()
  else undo()
}

function normalized(value: string) { return value.replace(/\s/g, '') }
function displaySectionTitle(section: FormSection) {
  if (normalized(section.title) === '기본정보') return '작업 개요'
  if (normalized(section.title) === '작업시간표') return '세부 작업 절차'
  const labels = section.fields.map(field => normalized(field.label))
  if (normalized(section.title) === '담당자' && labels.some(label => ['검토의견', '서명', '검토내용'].includes(label))) return '검토/서명'
  return section.title
}
function visibleFields(section: FormSection) {
  const hiddenFields = new Set(['개발이미지', '작업전사진', '작업후사진'])
  return section.fields.filter(field => !hiddenFields.has(normalized(field.label)))
}
function canUseRichEditor(field: FormField): boolean {
  return field.type === 'textarea' || field.type === 'markdown' || field.fullWidth === true
}
function isMarkdownEditor(field: FormField, target: Row): boolean {
  return field.type === 'markdown' || target[`${field.label}__format`] === 'markdown'
}
function enableMarkdownEditor(target: Row, field: string): void {
  if (target[`${field}__format`] === 'markdown') return
  checkpoint()
  target[field] = scalarValue(target[field]) ?? ''
  target[`${field}__format`] = 'markdown'
}
function isImportedExtraSection(section: FormSection): boolean {
  return normalized(section.title) === '가져온추가내용'
}
type ImportedExtraPanel = 'original' | 'mapping'
const pendingImportedUploads = ref(new Set<ImportedExtraPanel>())
function setImportedExtraUploading(panel: ImportedExtraPanel, uploading: boolean): void {
  const next = new Set(pendingImportedUploads.value)
  if (uploading) next.add(panel)
  else next.delete(panel)
  pendingImportedUploads.value = next
  emit('uploading', next.size > 0)
}
function importedExtraField(section: FormSection): string {
  return section.fields.find(field => normalized(field.label) === '내용')?.label ?? section.fields[0]?.label ?? '내용'
}
function importedExtraRaw(section: FormSection): string {
  const value = model.value[section.title]
  const rowsArr = Array.isArray(value) ? value : value ? [value] : []
  const field = importedExtraField(section)
  return rowsArr.map(row => scalarValue(row[field]) ?? '').filter(Boolean).join('\n\n')
}
function importedExtraPanels(section: FormSection): { original: string; mapping: string } {
  const source = importedExtraRaw(section)
  const headings = [...source.matchAll(/^##\s+([^\n]+?)\s*$/gm)]
  const normalizedHeading = (value: string) => value.replace(/[\s*_`~]/g, '').toLocaleLowerCase()
  const body = (index: number) => {
    const current = headings[index]
    if (!current || current.index == null) return ''
    const end = headings[index + 1]?.index ?? source.length
    return source.slice(current.index + current[0].length, end).trim()
  }
  const originalIndex = headings.findIndex(heading => normalizedHeading(heading[1] ?? '') === '원본내용')
  const mappingIndex = headings.findIndex(heading => normalizedHeading(heading[1] ?? '') === '매핑확인')
  if (originalIndex < 0 && mappingIndex < 0) return { original: source, mapping: '' }
  return {
    original: originalIndex >= 0 ? body(originalIndex) : '',
    mapping: mappingIndex >= 0 ? body(mappingIndex) : '',
  }
}
function updateImportedExtraPanel(section: FormSection, panel: ImportedExtraPanel, value: string): void {
  const rowsArr = rows(section)
  const target = rowsArr[0] ?? {}
  if (!rowsArr.length) rowsArr.push(target)
  const original = panel === 'original' ? value : importedExtraPanels(section).original
  checkpoint()
  if (!original.trim()) {
    delete model.value[section.title]
    return
  }
  if (rowsArr.length > 1) rowsArr.splice(1)
  target[importedExtraField(section)] = '## 원본 내용\n\n' + original.trim()
  target[importedExtraField(section) + '__format'] = 'markdown'
}
function record(section: FormSection): Row {
  const value = model.value[section.title]
  if (value && !Array.isArray(value)) return value
  const created: Row = {}
  model.value[section.title] = created
  return created
}
function rows(section: FormSection): Row[] {
  const value = model.value[section.title]
  if (Array.isArray(value)) return value
  const created: Row[] = value ? [value] : []
  model.value[section.title] = created
  return created
}
function inputType(field: FormField): 'text' | 'textarea' {
  return ['textarea', 'markdown'].includes(field.type) || field.fullWidth ? 'textarea' : 'text'
}
function addRow(section: FormSection) {
  checkpoint()
  rows(section).push(Object.fromEntries(section.fields.map(field => [field.label, field.type === 'image' ? [] : ''])))
}
function removeRow(section: FormSection, index: number) { checkpoint(); rows(section).splice(index, 1) }
function imageValues(value: unknown): string[] {
  return (Array.isArray(value) ? value : value ? [value] : []).filter((item): item is string => typeof item === 'string')
}
function scalarValue(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number' ? value : null
}
function appendImageField(target: Row, field: string, files: File[]) {
  const current = imageValues(target[field])
  for (const file of files) {
    const reader = new FileReader()
    reader.onload = () => { if (typeof reader.result === 'string') { checkpoint(); current.push(reader.result); target[field] = [...current] } }
    reader.readAsDataURL(file)
  }
}
function appendContentImages(target: Row, field: string, files: File[]) {
  for (const file of files) {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') return
      const current = scalarValue(target[field]) ?? ''
      checkpoint()
      target[field] = `${current}${current ? '\n\n' : ''}![사진](<${reader.result}>)`
      target[`${field}__format`] = 'markdown'
    }
    reader.readAsDataURL(file)
  }
}
function isUsableImageSource(source: string): boolean {
  try {
    const url = new URL(source, window.location.origin)
    return ['http:', 'https:'].includes(url.protocol)
      || /^data:image\/[a-z0-9.+-]+;base64,/i.test(source)
  } catch {
    return false
  }
}
function clipboardImageSources(event: ClipboardEvent): string[] {
  const html = event.clipboardData?.getData('text/html') ?? ''
  if (!html || !/<img\b/i.test(html)) return []
  const parsed = new DOMParser().parseFromString(html, 'text/html')
  return Array.from(parsed.images)
    .map(image => image.getAttribute('src')?.trim() ?? '')
    .filter((source, index, sources) => isUsableImageSource(source) && sources.indexOf(source) === index)
}
function appendContentImageSources(target: Row, field: string, sources: string[]) {
  const current = scalarValue(target[field]) ?? ''
  const images = sources.map(source => `![붙여넣은 이미지](<${source}>)`).join('\n\n')
  checkpoint()
  target[field] = `${current}${current ? '\n\n' : ''}${images}`
  target[`${field}__format`] = 'markdown'
}
function appendImageSources(target: Row, field: string, sources: string[]) {
  const current = imageValues(target[field])
  checkpoint()
  target[field] = [...current, ...sources]
}
function pasteCellImage(section: FormSection, rowIndex: number, field: FormField, event: ClipboardEvent) {
  const files = Array.from(event.clipboardData?.items ?? [])
    .filter(item => item.kind === 'file' && item.type.startsWith('image/'))
    .map(item => item.getAsFile())
    .filter((file): file is File => file !== null)
  const target = section.multiple ? rows(section)[rowIndex] : record(section)
  if (!target) return
  if (files.length) {
    event.preventDefault()
    if (field.type === 'image') appendImageField(target, field.label, files)
    else appendContentImages(target, field.label, files)
    return
  }

  // Browsers often copy an image element as HTML instead of a File item.
  // Handle its <img src> so the input does not receive only the image URL.
  const sources = clipboardImageSources(event)
  if (!sources.length) return
  event.preventDefault()
  if (field.type === 'image') appendImageSources(target, field.label, sources)
  else appendContentImageSources(target, field.label, sources)
}

watch(model, async () => {
  await nextTick()
  queueEditorHeightSync()
}, { deep: true })

onMounted(async () => {
  await nextTick()
  queueEditorHeightSync()
  window.addEventListener('resize', queueEditorHeightSync)
  if (editorRoot.value) {
    layoutObserver = new ResizeObserver(queueEditorHeightSync)
    layoutObserver.observe(editorRoot.value)
    contentObserver = new MutationObserver(queueEditorHeightSync)
    contentObserver.observe(editorRoot.value, { childList: true, characterData: true, subtree: true })
  }
})

onBeforeUnmount(() => {
  pendingImportedUploads.value = new Set()
  emit('uploading', false)
  window.removeEventListener('resize', queueEditorHeightSync)
  layoutObserver?.disconnect()
  layoutObserver = null
  contentObserver?.disconnect()
  contentObserver = null
  if (editorHeightFrame !== null) cancelAnimationFrame(editorHeightFrame)
  editorHeightFrame = null
})
</script>

<style scoped>
.inline-section { margin: 0 0 32px; scroll-margin-top: 28px; }
.inline-editor { width: 100%; max-width: 100%; min-width: 0; overflow-x: hidden; }
.inline-section h2 { margin: 32px 0 14px; font-size: 24px; line-height: 1.45; text-align: center; font-weight: 700; }
.inline-editor { width: 100%; max-width: 100%; min-width: 0; overflow-x: hidden; }
.inline-section h2 { margin: 32px 0 14px; font-size: 24px; line-height: 1.45; text-align: center; font-weight: 700; }
.inline-table-scroll { width: 100%; max-width: 100%; overflow-x: hidden; overflow-y: visible; margin: 16px 0 10px; border: 1px solid #cbd5e1; border-radius: 8px; }
.imported-extra-editor-columns { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; margin: 16px 0 10px; }
.imported-extra-editor-panel { min-width: 0; padding: 14px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; }
.imported-extra-editor-panel h3 { margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid #94a3b8; font-size: 15px; text-align: center; }
.imported-extra-editor-panel:last-child h3 { border-bottom-color: var(--q-primary); color: var(--q-primary); }
table { width: 100%; max-width: 100%; min-width: 0; border-collapse: collapse; table-layout: auto; }
th, td { min-width: 0; max-width: 100%; border: 1px solid #cbd5e1; padding: 6px 10px; vertical-align: top; overflow-wrap: anywhere; }
thead th { background: #64748b0d; font-weight: 600; text-align: center; padding: 12px 16px; }
.label-column { width: 36%; }.field-label { width: 36%; text-align: left; font-weight: 400; }
.number-cell { width: 6%; text-align: center; }.action-cell { width: 42px; padding: 4px; text-align: center; }
.empty-cell { padding: 20px; text-align: center; color: #94a3b8; }
.add-row { margin-top: 4px; }
:deep(.q-field__control), :deep(.q-field__native) { min-height: 28px; padding: 0; font-size: 14px; line-height: 1.6; }
:deep(textarea.q-field__native) { resize: vertical; }
.image-cell { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.image-cell img { display: block; max-width: 240px; max-height: 180px; object-fit: contain; border-radius: 6px; }
.inline-editor { width: 100%; max-width: 100%; min-width: 0; overflow-x: hidden; }
.inline-section h2 { margin: 32px 0 14px; font-size: 24px; line-height: 1.45; text-align: center; font-weight: 700; }
.inline-table-scroll { width: 100%; max-width: 100%; overflow-x: hidden; overflow-y: visible; margin: 16px 0 10px; border: 1px solid #cbd5e1; border-radius: 8px; }
.imported-extra-editor-columns { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; margin: 16px 0 10px; }
.imported-extra-editor-panel { min-width: 0; padding: 14px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; }
.imported-extra-editor-panel h3 { margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid #94a3b8; font-size: 15px; text-align: center; }
.imported-extra-editor-panel:last-child h3 { border-bottom-color: var(--q-primary); color: var(--q-primary); }
table { width: 100%; max-width: 100%; min-width: 0; border-collapse: collapse; table-layout: auto; }
th, td { min-width: 0; max-width: 100%; border: 1px solid #cbd5e1; padding: 6px 10px; vertical-align: top; overflow-wrap: anywhere; }
.paste-hint { color: #94a3b8; font-size: 12px; }
td:focus-visible { outline: 2px solid var(--q-primary); outline-offset: -2px; }

/* Keep the Toast UI editor inside its table cell so the document sidebar stays visible. */
.inline-table-scroll :deep(.toastui-editor-defaultUI),
.inline-table-scroll :deep(.toastui-editor-main),
.inline-table-scroll :deep(.toastui-editor-main-container),
.inline-table-scroll :deep(.toastui-editor-ww-container),
.inline-table-scroll :deep(.toastui-editor-contents) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}
.inline-table-scroll :deep(.toastui-editor-main),
.inline-table-scroll :deep(.toastui-editor-main-container),
.inline-table-scroll :deep(.toastui-editor-ww-container),
.inline-table-scroll :deep(.toastui-editor-contents) {
  height: auto;
  overflow: visible;
}
.inline-table-scroll :deep(.toastui-editor-defaultUI-toolbar) {
  display: flex;
  flex-wrap: wrap;
  height: auto;
  min-height: 45px;
  max-width: 100%;
  padding: 0 8px;
  overflow: hidden;
}
.inline-table-scroll :deep(.toastui-editor-toolbar) { height: auto; max-width: 100%; }
.inline-table-scroll :deep(.toastui-editor-toolbar-group) { flex-shrink: 0; }
.inline-table-scroll :deep(.toastui-editor .ProseMirror) {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: pre-wrap;
}
.inline-table-scroll :deep(.toastui-editor-contents table) {
  width: 100%;
  max-width: 100%;
  table-layout: fixed;
}
.inline-table-scroll :deep(.toastui-editor-contents th),
.inline-table-scroll :deep(.toastui-editor-contents td) {
  min-width: 0;
  max-width: 100%;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.inline-table-scroll td.editor-cell { vertical-align: stretch; }
.inline-table-scroll td.editor-cell > div {
  height: var(--editor-row-height, auto);
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.inline-table-scroll td.editor-cell :deep(.toastui-editor-defaultUI) {
  height: 100% !important;
  min-height: 160px;
  display: flex;
  flex-direction: column;
}
.inline-table-scroll td.editor-cell :deep(.toastui-editor-main) {
  flex: 1 1 auto;
}
</style>
