<template>
  <section class="asset-work-documents" :aria-busy="loading">
    <div class="row items-center q-gutter-y-sm q-mb-md">
      <div><strong>운영 이력</strong><div class="text-caption text-grey-7">전체 {{ total }}건 · 최근 등록순</div></div>
      <q-space />
      <q-btn v-if="!assetDeleted" flat dense no-caps color="primary" icon="add" label="메모 추가" @click="openNote(null)" />
      <q-btn flat round dense icon="refresh" :loading="loading" aria-label="운영 이력 새로고침" @click="load(false)" />
    </div>
    <div v-if="error" class="text-negative text-caption q-mb-md" role="alert">
      {{ error }} <q-btn flat dense label="다시 불러오기" @click="load(false)" />
    </div>
    <div v-if="loading && !items.length" class="q-pa-lg text-center"><q-spinner color="primary" size="24px" /></div>
    <div v-else-if="!items.length && !error" class="work-document-empty">
      <q-icon name="description" size="30px" />
      <strong>등록된 운영 이력이 없습니다.</strong>
      <span>{{ assetDeleted ? '이 자산에 남겨진 이력이 없습니다.' : '작업 문서·이슈·서버 점검과 직접 남긴 운영 메모를 함께 확인할 수 있습니다.' }}</span>
      <q-btn v-if="canViewDocuments" flat no-caps color="primary" label="작업 관리 열기" @click="navigate" />
    </div>
    <button v-for="item in items" :key="`${item.type}:${item.id}`" class="work-document-row" :class="{ 'asset-note-row': item.type === 'note', 'asset-inspection-row': item.type === 'inspection', 'asset-issue-row': item.type === 'issue' }"
      type="button" aria-haspopup="dialog" @click="openItem(item)">
      <template v-if="item.type === 'note'">
        <span class="work-document-kind">운영 메모</span>
        <strong class="note-preview">{{ item.content }}</strong>
        <span>일자 {{ item.occurredOn }}</span>
        <small>{{ item.createdBy }} · {{ fmtDateKst(item.createdAt) }} 등록{{ item.version > 1 ? ' · 수정됨' : '' }}</small>
      </template>
      <template v-else-if="item.type === 'inspection'">
        <span class="inspection-row-heading"><span class="work-document-kind">서버 점검</span><span class="inspection-row-status" :class="{ 'is-done': item.state === 'ACTIVE' && item.issue.status === 'DONE', 'is-active': item.state === 'ACTIVE' && item.issue.status !== 'DONE' && !item.issueDeleted }">{{ inspectionStatusLabel(item) }}</span></span>
        <strong>{{ item.issue.title }}</strong>
        <span>{{ formatInspectionMonth(item.month) }} 점검 · {{ item.issue.key }}</span>
        <small>담당 {{ item.issue.assigneeName || '미배정' }}{{ item.toMonth ? ` · ${formatInspectionMonth(item.toMonth)}로 이월` : '' }}{{ item.issueDeleted ? item.sourceType === 'WORK_PLAN' ? ' · 작업계획서 삭제됨' : ' · 이슈 삭제됨' : '' }}</small>
      </template>
      <template v-else-if="item.type === 'issue'">
        <span class="inspection-row-heading"><span class="work-document-kind">스케줄 이슈</span><span class="inspection-row-status" :class="{ 'is-done': item.issue.status === 'DONE', 'is-active': item.issue.status !== 'DONE' }">{{ STATUS_LABEL[item.issue.status] }}</span></span>
        <strong>{{ item.issue.title }}</strong>
        <span>{{ item.issue.key }} · {{ issueSchedule(item) }}</span>
        <small>담당 {{ item.issue.assigneeName || '미배정' }}</small>
      </template>
      <template v-else>
        <span class="work-document-kind">{{ item.templateTitle }}</span>
        <strong>{{ item.title }}</strong>
        <span>{{ item.dateLabel || '작업일' }} {{ item.workDate ? item.workDate.replace('T', ' ') : '미입력' }}</span>
        <small>{{ item.createdBy || '작성자 미등록' }} · {{ fmtDateKst(item.createdAt) }} 등록{{ item.assetCount > 1 ? ` · 자산 ${item.assetCount}개` : '' }}</small>
      </template>
    </button>
    <q-btn v-if="items.length < total" flat color="primary" class="full-width q-mt-sm" :loading="loading" label="더 보기" @click="load(true)" />
    <WorkDocumentEntryDialog v-if="selectedDocument" v-model="documentOpen" :entry-id="selectedDocument.id"
      :title="selectedDocument.templateTitle" @saved="load(false)" />
    <AssetNoteDialog v-model="noteOpen" :asset-id="assetId" :note-id="selectedNoteId" :asset-deleted="!!assetDeleted"
      @saved="noteSaved" @removed="noteRemoved" />
    <AssetInspectionDialog v-model="inspectionOpen" :asset-id="assetId" :selected="selectedInspection"
      @changed="load(false)" @navigate="emit('navigate')" />
    <AssetIssueDialog v-model="issueOpen" :asset-id="assetId" :selected="selectedIssue" @changed="load(false)" />
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { AssetWorkDocument } from 'src/services/formEntries'
import { listAssetWorkHistory, type AssetWorkHistoryItem, type AssetNote, type AssetIssueHistory } from 'src/services/assetWorkHistory'
import { STATUS_LABEL } from 'src/services/pm/issue'
import { useAuthStore } from 'src/stores/auth'
import { fmtDateKst } from 'src/utils/time/kst'
import { getErrorMessage } from 'src/utils/http/error'
import { formatInspectionMonth, inspectionStatusLabel, type InspectionTask } from 'src/services/inspection'
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue'
import AssetNoteDialog from './AssetNoteDialog.vue'
import AssetInspectionDialog from './AssetInspectionDialog.vue'
import AssetIssueDialog from './AssetIssueDialog.vue'
const props = defineProps<{ assetId: string; assetDeleted?: boolean }>()
const emit = defineEmits<{ navigate: [] }>()
const router = useRouter()
const auth = useAuthStore()
const canViewDocuments = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('job'))
const items = ref<AssetWorkHistoryItem[]>([]), total = ref(0), loading = ref(false), error = ref('')
const documentOpen = ref(false), selectedDocument = ref<AssetWorkDocument | null>(null)
const noteOpen = ref(false), selectedNoteId = ref<string | null>(null)
const inspectionOpen = ref(false), selectedInspection = ref<InspectionTask | null>(null)
const issueOpen = ref(false), selectedIssue = ref<{ id: string; projectId: string } | null>(null)
let request = 0
async function load(append = false) {
  const token = ++request, id = props.assetId
  loading.value = true; error.value = ''
  try {
    const offsets = append ? [items.value.length] : Array.from({ length: Math.max(1, Math.ceil(items.value.length / 20)) }, (_, page) => page * 20)
    const results = await Promise.all(offsets.map(offset => listAssetWorkHistory(id, offset)))
    if (token !== request) return
    const refreshed = results.flatMap(result => result.items)
    items.value = [...new Map([...(append ? items.value : []), ...refreshed].map(item => [`${item.type}:${item.id}`, item])).values()]
    total.value = results[0]?.total ?? 0
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '운영 이력을 불러오지 못했습니다.')
  } finally { if (token === request) loading.value = false }
}
function openItem(item: AssetWorkHistoryItem) {
  if (item.type === 'note') openNote(item.id)
  else if (item.type === 'inspection') { selectedInspection.value = item; inspectionOpen.value = true }
  else if (item.type === 'issue') { selectedIssue.value = item.issue; issueOpen.value = true }
  else { selectedDocument.value = item; documentOpen.value = true }
}
function issueSchedule(item: AssetIssueHistory) {
  const start = item.startDate ? fmtDateKst(item.startDate) : '', end = item.dueDate ? fmtDateKst(item.dueDate) : ''
  if (start && end) return start === end ? start : `${start} ~ ${end}`
  return start ? `${start} 시작` : end ? `${end} 마감` : '일정 미정'
}
function openNote(id: string | null) {
  selectedNoteId.value = id
  noteOpen.value = true
}
function noteSaved(note: AssetNote) {
  const index = items.value.findIndex(item => item.type === 'note' && item.id === note.id)
  if (index >= 0) items.value[index] = note
  else { items.value.unshift(note); total.value += 1 }
  void load(false)
}
function noteRemoved(id: string) {
  items.value = items.value.filter(item => item.type !== 'note' || item.id !== id)
  total.value = Math.max(0, total.value - 1)
  void load(false)
}
function navigate() {
  emit('navigate')
  void router.push('/job/forms')
}
watch(() => props.assetId, () => { documentOpen.value = false; noteOpen.value = false; inspectionOpen.value = false; issueOpen.value = false; selectedIssue.value = null; selectedInspection.value = null; selectedDocument.value = null; items.value = []; total.value = 0; void load() }, { immediate: true })
onBeforeUnmount(() => { ++request })
</script>
<style scoped>
.work-document-empty { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 28px 10px; text-align: center; font-size: 12px; line-height: 1.8; color: #7a8798; }
.work-document-empty strong { color: #4f6279; font-size: 13px; }
.work-document-row { display: flex; width: 100%; flex-direction: column; gap: 7px; text-align: left; padding: 16px 2px; background: transparent; border: 0; border-bottom: 1px solid #e8edf3; cursor: pointer; color: #65758a; font: inherit; font-size: 12px; overflow-wrap: anywhere; }
.work-document-row:hover { background: #f5f8fb; }
.work-document-row strong { color: #33485f; font-size: 14px; font-weight: 500; }
.work-document-kind { font-size: 11px; color: #7188a3; }
.work-document-row small { font-size: 11px; }
.note-preview { white-space: pre-wrap; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; line-height: 1.7; }
.inspection-row-heading { display: flex; align-items: center; gap: 8px; }
.inspection-row-status { font-size: 11px; padding: 1px 6px; border-radius: 4px; color: #738091; background: #f1f3f6; }
.inspection-row-status.is-active { color: #476d9a; background: #edf3fa; }
.inspection-row-status.is-done { color: #3b7960; background: #edf6f1; }
</style>
