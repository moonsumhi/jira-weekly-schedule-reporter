<template>
  <q-dialog :model-value="modelValue" maximized transition-show="slide-up" transition-hide="slide-down"
    @update:model-value="handleDialogUpdate">
    <q-card class="work-document">
      <header class="document-topbar">
        <q-btn flat round dense icon="arrow_back" :aria-label="backLabel || '목록으로 돌아가기'" :disable="saving" @click="close" />
        <div class="document-breadcrumb"><span>작업 관리</span><q-icon name="chevron_right" size="16px" /><strong>{{ title }}</strong></div>
        <q-space />
        <span class="reading-badge"><span />{{ editing ? (creating ? '작성 모드' : '수정 모드') : '읽기 모드' }}</span>
        <q-btn flat round dense icon="close" aria-label="상세 닫기" :disable="saving" @click="close" />
      </header>

      <div v-if="loading" class="document-loading"><q-spinner size="36px" color="primary" /><span>문서를 불러오고 있습니다</span></div>
      <div v-else-if="error" class="document-loading" role="alert">
        <span>{{ error }}</span><q-btn outline color="primary" label="다시 불러오기" @click="emit('retry')" />
      </div>
      <div v-else-if="entry" :class="['document-layout', { 'is-editing': editing }]">
        <aside class="document-sidebar">
          <div class="sidebar-label">문서 목차 <span>{{ sections.length }}</span></div>
          <nav class="document-nav" aria-label="문서 목차">
            <button v-for="(section, index) in sections" :key="index" type="button"
              :class="['document-nav-item', { active: activeSection === index }]"
              :aria-current="activeSection === index ? 'location' : undefined" @click="goToSection(index)">
              <span class="nav-number">{{ String(index + 1).padStart(2, '0') }}</span><span>{{ displaySectionTitle(section) }}</span>
            </button>
          </nav>
          <div class="sidebar-metadata">
            <q-icon name="description" size="22px" />
            <div class="sidebar-meta-title">문서 정보</div>
            <dl><dt>작성자</dt><dd>{{ entry.createdBy || '—' }}</dd><dt>작성일</dt><dd>{{ formatDate(entry.createdAt) }}</dd>
              <dt>최종 수정</dt><dd>{{ formatDate(entry.updatedAt) }}</dd><dt>버전</dt><dd>v{{ entry.version }}</dd></dl>
          </div>
        </aside>

        <main ref="scrollArea" class="document-scroll" @scroll="updateActiveSection">
          <article class="document-paper">
            <header class="document-hero">
              <div class="document-kind"><q-icon name="article" size="16px" />{{ title }}</div>
              <h1>{{ documentTitle }}</h1>
              <div class="document-byline">
                <span><q-icon name="person_outline" />{{ entry.createdBy || '작성자 미등록' }}</span>
                <span v-if="workDate"><q-icon name="event" />{{ workDate }}</span>
                <span v-else><q-icon name="schedule" />{{ formatDate(entry.createdAt) }}</span>
              </div>
            </header>

            <div v-if="(inspectionLinks || resultInspectionLinks) && !creating && canViewInspection" class="document-inspection-link">
              <InspectionLinks :key="`${entry.id}:${entry.version}`" :work-plan-id="inspectionLinks ? entry.id : undefined" :work-result-id="resultInspectionLinks ? entry.id : undefined" :allow-add="false" @navigate="closeImmediately" />
            </div>
            <WorkDocumentAssets v-if="linkAssets" v-model="editableAssets" :editing="editing" :disable="!!saving" @navigate="closeImmediately" />

            <template v-if="editing">
              <div v-if="saveWarning" class="document-save-warning" role="alert"><q-icon name="info" size="19px" /><span>{{ saveWarning }}</span></div>
              <WorkDocumentInspectionOptions v-if="inspectionLinks && canViewInspection" v-model="inspection"
                :entry-id="creating ? undefined : entry.id" :assets="editableAssets" :data="editableData" :disable="!!saving" />
              <InlineDocumentEditor v-model="editableData" :sections="sections" />
            </template>
            <template v-else-if="view === 'markdown'">
              <WorkResultContent :content="markdown" :section-titles="markdownSectionTitles" />
            </template>
            <template v-else>
            <section v-for="(section, index) in sections" :key="index" :data-section-index="index" class="document-section">
              <div class="section-heading"><span class="section-number">{{ String(index + 1).padStart(2, '0') }}</span>
                <h2>{{ displaySectionTitle(section) }}</h2><span v-if="section.multiple" class="section-count">{{ sectionRows(section).length }}개 항목</span></div>

              <div v-if="isWorkTable(section)" class="document-table-scroll" tabindex="0" role="region" :aria-label="`${displaySectionTitle(section)} 표, 가로 스크롤 가능`">
                <table class="document-work-table">
                  <thead><tr><th scope="col" class="row-number">No.</th><th v-for="field in tableFields(section)" :key="field.label" scope="col" :class="fieldColumnClass(field)">{{ field.label }}</th></tr></thead>
                  <tbody>
                    <template v-for="(row, rowIndex) in sectionRows(section)" :key="rowIndex">
                    <tr>
                      <th scope="row" class="row-number">{{ rowIndex + 1 }}</th>
                      <td v-for="field in tableFields(section)" :key="field.label" :class="fieldColumnClass(field)">
                        <template v-if="field.type === 'image'">
                          <div v-if="images(row[field.label]).length" class="document-images">
                            <button v-for="(src, imageIndex) in images(row[field.label])" :key="imageIndex" type="button" class="document-image"
                              :aria-label="`${field.label} ${imageIndex + 1} 확대`" @click="previewSource = src">
                              <img :src="src" :alt="`${field.label} ${imageIndex + 1}`" loading="lazy" /><span><q-icon name="zoom_in" />확대</span>
                            </button>
                          </div><div v-else class="field-empty">—</div>
                        </template>
                        <WorkResultContent v-else-if="developmentImages(section, field).length" :content="comparisonMarkdown(row, [field, ...developmentImages(section, field)])" />
                        <WorkResultContent v-else-if="isMarkdownValue(row[field.label], row[`${field.label}__format`])" :content="String(row[field.label] ?? '')" />
                        <div v-else :class="['field-value', { 'field-empty': isEmpty(row[field.label]) }]">{{ displayValue(row[field.label]) }}</div>
                      </td>
                    </tr>
                    </template>
                    <tr v-if="!sectionRows(section).length"><td :colspan="tableFields(section).length + 1" class="field-empty">등록된 항목이 없습니다.</td></tr>
                  </tbody>
                </table>
              </div>
              <div v-else-if="section.multiple" class="document-steps">
                <div v-for="(row, rowIndex) in sectionRows(section)" :key="rowIndex" class="document-step">
                  <div class="step-rail"><span>{{ String(rowIndex + 1).padStart(2, '0') }}</span></div>
                  <div class="step-card"><div class="document-field-groups">
                    <div v-for="group in workResultFieldGroups(section)" :key="group.label" :class="['document-field-group', { 'comparison-side': group.label, 'whole-document': section.title === '문서 본문' }]">
                      <div v-if="group.label" class="comparison-heading">{{ group.label }}</div>
                      <template v-if="group.label">
                        <WorkResultContent v-if="comparisonMarkdown(row, group.fields)" :content="comparisonMarkdown(row, group.fields)" />
                        <div v-else class="field-empty">작성된 내용이 없습니다.</div>
                      </template>
                      <div v-else class="document-fields">
                    <div v-for="field in group.fields" :key="field.label" :class="['document-field', { wide: isWide(field, row[field.label]) }]">
                      <div class="field-label">{{ field.label }}</div>
                      <template v-if="field.type === 'image'">
                        <div v-if="images(row[field.label]).length" class="document-images">
                          <button v-for="(src, imageIndex) in images(row[field.label])" :key="imageIndex" type="button" class="document-image"
                            :aria-label="`${field.label} ${imageIndex + 1} 확대`" @click="previewSource = src">
                            <img :src="src" :alt="`${field.label} ${imageIndex + 1}`" loading="lazy" /><span><q-icon name="zoom_in" />확대</span>
                          </button>
                        </div><div v-else class="field-empty">등록된 이미지가 없습니다</div>
                      </template>
                      <WorkResultContent v-else-if="isMarkdownValue(row[field.label], row[`${field.label}__format`])" :content="String(row[field.label] ?? '')" />
                      <div v-else :class="['field-value', { 'field-empty': isEmpty(row[field.label]) }]">{{ displayValue(row[field.label]) }}</div>
                    </div>
                      </div>
                    </div>
                  </div></div>
                </div>
                <div v-if="!sectionRows(section).length" class="section-empty">등록된 항목이 없습니다.</div>
              </div>

              <div v-else class="document-fields single-fields">
                <div v-for="field in section.fields" :key="field.label" :class="['document-field', { wide: isWide(field, sectionRecord(section)[field.label]) }]">
                  <div class="field-label">{{ field.label }}</div>
                  <template v-if="field.type === 'image'">
                    <div v-if="images(sectionRecord(section)[field.label]).length" class="document-images">
                      <button v-for="(src, imageIndex) in images(sectionRecord(section)[field.label])" :key="imageIndex" type="button" class="document-image"
                        :aria-label="`${field.label} ${imageIndex + 1} 확대`" @click="previewSource = src">
                        <img :src="src" :alt="`${field.label} ${imageIndex + 1}`" loading="lazy" /><span><q-icon name="zoom_in" />확대</span>
                      </button>
                    </div><div v-else class="field-empty">등록된 이미지가 없습니다</div>
                  </template>
                  <WorkResultContent v-else-if="isMarkdownValue(sectionRecord(section)[field.label], sectionRecord(section)[`${field.label}__format`])" :content="String(sectionRecord(section)[field.label] ?? '')" />
                  <div v-else :class="['field-value', { 'field-empty': isEmpty(sectionRecord(section)[field.label]) }]">{{ displayValue(sectionRecord(section)[field.label]) }}</div>
                </div>
              </div>
            </section>
            <div v-if="!sections.length" class="section-empty">표시할 문서 항목이 없습니다.</div>
            </template>
            <div class="document-end"><span />문서 끝<span /></div>
          </article>
        </main>
      </div>
      <div v-else class="document-loading">표시할 문서가 없습니다.</div>

      <footer class="document-footer">
        <span class="footer-note"><q-icon name="description" />{{ title }}</span><q-space />
        <q-btn flat no-caps :label="editing ? (creating ? '작성 취소' : '수정 취소') : '닫기'" :disable="saving" @click="editing ? cancelEdit() : close()" />
        <q-btn v-if="editing" color="primary" no-caps icon="save" label="저장" :loading="saving" @click="emit('save', editableData, linkAssets ? editableAssets.map(a => a.id) : undefined, inspection)" />
        <q-btn v-else-if="!creating" outline no-caps icon="edit_note" label="수정" :disable="loading || !entry || entry.isDeleted" @click="startEdit" />
        <q-btn-dropdown v-if="!editing" outline no-caps icon="download" label="내보내기" :loading="exporting" :disable="loading || !entry || exporting">
          <q-list>
            <q-item clickable v-close-popup @click="emit('export')"><q-item-section>Markdown (.md)</q-item-section></q-item>
            <q-item clickable v-close-popup :disable="!entry?.originalFile" @click="emit('download-original')"><q-item-section>{{ originalDownloadLabel }}</q-item-section></q-item>
            <q-item clickable v-close-popup @click="emit('export-file', 'hwp')"><q-item-section>HWP 내보내기</q-item-section></q-item>
            <q-item clickable v-close-popup @click="emit('export-file', 'docx')"><q-item-section>Word (.docx)</q-item-section></q-item>
          </q-list>
        </q-btn-dropdown>
      </footer>

      <q-dialog :model-value="!!previewSource" @update:model-value="previewSource = ''">
        <q-card class="document-preview"><q-btn flat round icon="close" class="preview-close" aria-label="이미지 닫기" v-close-popup />
          <img :src="previewSource" alt="문서 이미지 확대" /></q-card>
      </q-dialog>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import type { FormEntry, WorkDocumentAsset } from 'src/services/formEntries'
import WorkDocumentAssets from './WorkDocumentAssets.vue'
import type { FormField, FormSection } from 'src/services/formTemplates'
import { comparisonMarkdown, workResultFieldGroups } from 'src/utils/workResultFields'
import WorkResultContent from './WorkResultContent.vue'
import InlineDocumentEditor from './InlineDocumentEditor.vue'
import { formEntryMarkdown } from 'src/utils/formEntryMarkdown'
import { useAuthStore } from 'stores/auth'
import InspectionLinks from './inspection/InspectionLinks.vue'
import WorkDocumentInspectionOptions from './inspection/WorkDocumentInspectionOptions.vue'
import type { WorkDocumentInspection } from 'src/services/workDocumentInspection'

type EditableData = Record<string, Record<string, unknown> | Record<string, unknown>[]>
const props = defineProps<{ modelValue: boolean; loading: boolean; entry: FormEntry | null; title: string; sections: FormSection[]; creating?: boolean; exporting?: boolean; saving?: boolean; linkAssets?: boolean; inspectionLinks?: boolean; resultInspectionLinks?: boolean; saveWarning?: string; error?: string; backLabel?: string }>()
const auth = useAuthStore()
const canViewInspection = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('server_check'))
const view = ref<'markdown'>('markdown')
const editing = ref(false)
const inspection = ref<WorkDocumentInspection | null>(null)
const editableData = ref<EditableData>({})
const editableAssets = ref<WorkDocumentAsset[]>([])
const editSnapshot = ref('')
const $q = useQuasar()
function cloneEntryData(): EditableData { return JSON.parse(JSON.stringify(props.entry?.data ?? {})) as EditableData }
function cloneEntryAssets() { return (props.entry?.linkedAssets ?? []).map(asset => ({ ...asset })) }
function snapshot(value: EditableData): string { return JSON.stringify({ data: value, assets: editableAssets.value.map(a => a.id) }) }
const isEditDirty = computed(() => editing.value && (!!inspection.value || snapshot(editableData.value) !== editSnapshot.value))
function startEdit() {
  inspection.value = null
  editableData.value = cloneEntryData()
  editableAssets.value = cloneEntryAssets()
  editSnapshot.value = snapshot(editableData.value)
  editing.value = true
}
function discardEdit() {
  inspection.value = null
  editableData.value = cloneEntryData()
  editableAssets.value = cloneEntryAssets()
  editSnapshot.value = snapshot(editableData.value)
  editing.value = false
}
function confirmDiscard(onOk: () => void): void {
  if (!isEditDirty.value) {
    onOk()
    return
  }
  $q.dialog({
    title: '저장하지 않은 변경사항이 있습니다',
    message: '저장하지 않고 닫으시겠습니까?',
    cancel: { label: '취소', flat: true },
    ok: { label: '닫기', color: 'negative' },
  }).onOk(onOk)
}
function cancelEdit() {
  confirmDiscard(() => {
    discardEdit()
    if (props.creating) closeImmediately()
  })
}
function withoutDocumentTitle(source: string): string {
  const lines = source.split('\n')
  if (/^\s*#\s+/.test(lines[0] ?? '')) {
    lines.shift()
    while (lines[0]?.trim() === '') lines.shift()
  }
  return lines.join('\n')
}
const markdown = computed(() => withoutDocumentTitle(formEntryMarkdown(
  props.title,
  props.sections,
  props.entry?.data ?? {},
  window.location.origin,
)))
function displaySectionTitle(section: FormSection): string {
  const normalized = section.title.replace(/\s/g, '')
  if (normalized === '기본정보') return '작업 개요'
  if (normalized === '작업시간표') return '세부 작업 절차'
  const fields = section.fields.map((field) => field.label.replace(/\s/g, ''))
  if (normalized === '담당자' && fields.some((label) => ['검토의견', '서명', '검토내용'].includes(label))) return '검토/서명'
  return section.title
}
const markdownSectionTitles = computed(() => props.sections.map(displaySectionTitle))
const originalDownloadLabel = '원본 파일 다운로드'
watch(() => [props.modelValue, props.entry?.id, props.entry?.version, props.loading, props.creating], () => {
  if (props.modelValue && editing.value && props.saveWarning) return
  inspection.value = null
  view.value = 'markdown'
  editing.value = Boolean(props.creating && props.modelValue && props.entry)
  editableData.value = cloneEntryData()
  editableAssets.value = cloneEntryAssets()
  editSnapshot.value = snapshot(editableData.value)
})
function isWorkTable(section: FormSection): boolean {
  const title = section.title.replace(/\s/g, '')
  return isWorkTarget(section) || (['작업내용', '개발내용', '세부작업내용'].includes(title) && section.fields.length > 1)
}
function isWorkTarget(section: FormSection): boolean { return section.title.replace(/\s/g, '') === '작업대상' }
function isDevelopmentImage(field: FormField): boolean {
  return field.type === 'image' && field.label.replace(/\s/g, '') === '개발이미지'
}
function fieldColumnClass(field: FormField): string | undefined {
  return field.label.replace(/\s/g, '') === '제목' ? 'title-column' : undefined
}
function developmentImages(section: FormSection, field: FormField): FormField[] {
  const target = section.fields.find(item => item.label === '세부 작업 내용')
    ?? section.fields.find(item => item.type === 'textarea')
  return field === target ? section.fields.filter(isDevelopmentImage) : []
}
function tableFields(section: FormSection): FormField[] {
  const fields = section.fields.filter(field => !isDevelopmentImage(field))
  if (!isWorkTarget(section)) return fields
  const note = fields.find(field => field.label.trim() === '비고')
  const ordered = fields.filter(field => field.label.trim() !== '비고')
  if (!note) return ordered
  const hostnameIndex = ordered.findIndex(field => field.label.replace(/\s/g, '').toUpperCase() === 'HOSTNAME')
  ordered.splice(hostnameIndex >= 0 ? hostnameIndex + 1 : ordered.length, 0, note)
  return ordered
}
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; save: [value: EditableData, assetIds?: string[], inspection?: WorkDocumentInspection | null]; export: []; 'export-file': [format: 'hwp' | 'docx']; 'download-original': []; retry: [] }>()
const scrollArea = ref<HTMLElement | null>(null)
const activeSection = ref(0)
const previewSource = ref('')
type DocumentRow = Record<string, unknown>
function asRecord(value: unknown): DocumentRow { return value && typeof value === 'object' && !Array.isArray(value) ? value as DocumentRow : {} }
function sectionRecord(section: FormSection): DocumentRow { return asRecord(props.entry?.data[section.title]) }
function sectionRows(section: FormSection): DocumentRow[] {
  const value = props.entry?.data[section.title]
  return Array.isArray(value) ? value.map(asRecord) : value ? [asRecord(value)] : []
}
function displayValue(value: unknown): string {
  if (value == null || value === '') return '—'
  if (typeof value === 'boolean') return value ? '예' : '아니오'
  if (typeof value === 'number' || typeof value === 'string') return String(value)
  return Array.isArray(value) ? value.map(displayValue).join('\n') : JSON.stringify(value)
}
function isEmpty(value: unknown) { return value == null || value === '' || (Array.isArray(value) && !value.length) }
function images(value: unknown): string[] { return (Array.isArray(value) ? value : [value]).filter((item): item is string => typeof item === 'string' && !!item.trim()) }
function isMarkdownValue(value: unknown, format?: unknown): boolean {
  if (typeof value !== 'string' || !value.trim()) return false
  if (format === 'markdown') return true
  const lines = value.split(/\r?\n/)
  return lines.some((line, index) => {
    const separator = lines[index + 1] ?? ''
    return /^\s*\|.*\|\s*$/.test(line)
      && /^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$/.test(separator)
  })
}
function isWide(field: FormField, value: unknown) { return field.fullWidth || field.type === 'textarea' || field.type === 'image' || displayValue(value).length > 90 || displayValue(value).includes('\n') }
function findField(labels: string[]): string {
  for (const section of props.sections.filter((item) => !item.multiple)) {
    const record = sectionRecord(section)
    for (const label of labels) { if (!isEmpty(record[label])) return displayValue(record[label]) }
  }
  return ''
}
const documentTitle = computed(() => findField(['작업명', '작업 제목', '제목', '작업 명', '문서명', '신청명', '처리 목적']) || props.title)
const workDate = computed(() => findField(['작업 일시', '작업 기간 (시작)', '작업일', '신청일자', '신청일', '작성일']).replace('T', ' '))
function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('sv-SE', { timeZone: 'Asia/Seoul' }).slice(0, 16)
}
function closeImmediately() { emit('update:modelValue', false) }
function close() { if (!props.saving) confirmDiscard(closeImmediately) }
function handleDialogUpdate(open: boolean) {
  if (open) emit('update:modelValue', true)
  else close()
}
function goToSection(index: number) {
  const element = scrollArea.value?.querySelector<HTMLElement>(`[data-section-index="${index}"]`)
  element?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
  activeSection.value = index
}
function updateActiveSection() {
  const area = scrollArea.value
  if (!area) return
  const top = area.getBoundingClientRect().top + 90
  let current = 0
  area.querySelectorAll<HTMLElement>('[data-section-index]').forEach((element, index) => {
    if (element.getBoundingClientRect().top <= top) current = index
  })
  activeSection.value = current
}
watch(() => [props.modelValue, props.entry?.id, props.loading], async () => {
  activeSection.value = 0
  previewSource.value = ''
  await nextTick()
  if (scrollArea.value) scrollArea.value.scrollTop = 0
})
</script>

<style scoped src="./workDocument.css"></style>
<style scoped>
.document-save-warning { display: flex; gap: 8px; padding: 12px; margin-bottom: 16px; border-radius: 8px; background: #fff4de; color: #775521; font-size: 13px; line-height: 1.7; }
.document-save-warning .q-icon { flex-shrink: 0; margin-top: 2px; }
.document-inspection-link { display: flex; justify-content: flex-end; margin: 0 0 12px; }
</style>
