<template>
  <div class="monthly-highlights" :class="{ 'monthly-highlights--dark': $q.dark.isActive }">
    <q-card v-for="section in visibleSections" :id="section.id" :key="section.kind" flat bordered class="highlight-card">
      <q-card-section class="row items-center q-py-sm q-px-md">
        <q-icon :name="section.icon" :color="section.color" size="sm" class="q-mr-sm" />
        <div class="text-subtitle1 text-weight-bold">{{ section.label }}</div>
        <q-badge :color="section.color" :label="sectionItems(section.kind).length" class="q-ml-sm" />
        <q-space />
        <template v-if="editable && section.kind !== 'MILESTONE'">
          <q-btn flat dense no-caps icon="add" label="추가" size="sm" :color="section.color" @click="openInsight(section.kind)" />
        </template>
      </q-card-section>
      <q-separator />
      <div v-if="!sectionItems(section.kind).length" class="text-grey-5 text-body2 text-center q-pa-md">항목이 없습니다.</div>
      <q-list v-else separator class="highlight-list">
        <q-item v-for="item in sectionItems(section.kind)" :key="item.id" class="highlight-item">
          <q-item-section>
            <q-item-label><strong>{{ item.title }}</strong></q-item-label>
            <WorkResultContent v-if="item.content" :content="item.content" />
            <div v-if="item.impact" class="text-caption">영향: {{ item.impact }}</div>
            <div v-if="item.actionPlan" class="text-caption">대응 / 요청: {{ item.actionPlan }}</div>
            <div v-if="item.owner || item.dueDate" class="text-caption text-grey-7">{{ item.owner ? '담당: ' + item.owner : '' }}{{ item.dueDate ? ' · 기한: ' + item.dueDate : '' }}</div>
            <div v-if="item.kind === 'MILESTONE'" class="text-caption text-grey-7">{{ item.status || '상태 미지정' }} · 계획일 {{ item.plannedDate || '-' }} · 예상일 {{ item.expectedDate || '-' }}</div>
            <router-link v-if="item.sourceReportId" class="text-caption" :to="`/pm/weekly-report/${item.sourceReportId}`">출처: {{ item.sourceLabel || '주간 보고' }}</router-link>
          </q-item-section>
          <q-item-section v-if="editable" side top>
            <div class="row no-wrap"><q-btn flat dense icon="edit" aria-label="항목 수정" @click="openInsight(section.kind, item)" /><q-btn flat dense icon="delete" aria-label="항목 삭제" @click="removeInsight(item)" /></div>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <q-dialog v-model="insightOpen" persistent><q-card :class="{ 'highlight-dialog--dark': $q.dark.isActive }" style="width:700px;max-width:95vw">
      <q-card-section class="text-h6">{{ kindLabels[draft.kind] }} {{ editing ? '수정' : '추가' }}</q-card-section>
      <q-card-section class="q-gutter-sm" style="max-height:70vh;overflow:auto">
        <q-input v-model="draft.title" outlined dense label="제목 *" maxlength="300" />
        <MarkdownEditor v-model="draft.content" label="내용" :rows="3" @uploading="uploading.content = $event" />
        <q-input v-if="draft.kind !== 'MILESTONE'" v-model="draft.impact" outlined dense label="영향" />
        <q-input v-if="draft.kind !== 'MILESTONE'" v-model="draft.actionPlan" outlined autogrow type="textarea" label="대응 방안 / 요청 사항" />
        <q-input v-model="draft.owner" outlined dense label="담당자" />
        <q-input v-if="draft.kind !== 'MILESTONE'" v-model="draft.dueDate" outlined dense type="date" label="기한" stack-label />
        <template v-else><q-input v-model="draft.plannedDate" outlined dense type="date" label="기존 계획일" stack-label /><q-input v-model="draft.expectedDate" outlined dense type="date" label="현재 예상일" stack-label /><q-input v-model="draft.status" outlined dense label="상태 / 변경 사유" /></template>
      </q-card-section><q-card-actions align="right"><q-btn flat label="취소" :disable="isUploading" v-close-popup /><q-btn color="primary" label="저장" :disable="isUploading" :loading="saving" @click="saveInsight" /></q-card-actions>
    </q-card></q-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, Notify, useQuasar } from 'quasar'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import WorkResultContent from 'src/components/WorkResultContent.vue'
import { updateMonthlyReport, type MonthlyReport, type MonthlyInsight, type MonthlyReportPatch } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{ report: MonthlyReport }>()
const $q = useQuasar()
const emit = defineEmits<{ saved: [report: MonthlyReport] }>()
const editable = computed(() => props.report.status !== 'CONFIRMED')
const kindLabels: Record<string, string> = { MAIN_AGENDA: '주요 안건', ISSUE_RISK: '특이사항 및 리스크', DECISION_REQUIRED: '결정 필요 사항', MILESTONE: '주요 일정' }
const sections = [
  { kind: 'MAIN_AGENDA', id: 'monthly-agenda', label: '주요 안건', icon: 'task_alt', color: 'blue' },
  { kind: 'ISSUE_RISK', id: 'monthly-risks', label: '특이사항 및 리스크', icon: 'warning_amber', color: 'orange' },
  { kind: 'DECISION_REQUIRED', id: 'monthly-decisions', label: '결정 필요 사항', icon: 'gavel', color: 'purple' },
  { kind: 'MILESTONE', id: 'monthly-milestones', label: '주요 일정', icon: 'event', color: 'teal' },
] as const
const visibleSections = computed(() => sections.filter(section => section.kind !== 'MILESTONE' || props.report.insights.some(item => item.kind === 'MILESTONE')))
function sectionItems(kind: MonthlyInsight['kind']) { return props.report.insights.filter(item => item.kind === kind) }
const saving = ref(false)
const uploading = ref({ content: false })
const isUploading = computed(() => Object.values(uploading.value).some(Boolean))
const editBase = ref('')
async function persist(payload: MonthlyReportPatch): Promise<boolean> {
  saving.value = true
  try { emit('saved', await updateMonthlyReport(props.report.id, { ...payload, expected_updated_at: editBase.value })); return true }
  catch (e) { Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') }); return false }
  finally { saving.value = false }
}
const blank = (): MonthlyInsight => ({ id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`, kind: 'MAIN_AGENDA', title: '', content: '', impact: '', actionPlan: '', owner: '', dueDate: '', plannedDate: '', expectedDate: '', status: '', sourceReportId: null, sourceItemId: null, sourceLabel: null })
const insightOpen = ref(false)
const editing = ref(false)
const draft = ref<MonthlyInsight>(blank())
function openInsight(kind: MonthlyInsight['kind'], item?: MonthlyInsight) { editBase.value = props.report.updatedAt; editing.value = !!item; draft.value = item ? { ...item } : { ...blank(), kind }; insightOpen.value = true }
function payload(items: MonthlyInsight[]): NonNullable<MonthlyReportPatch['insights']> {
  return items.map(i => ({ id: i.id, kind: i.kind, title: i.title, content: i.content, impact: i.impact, action_plan: i.actionPlan, owner: i.owner, due_date: i.dueDate, planned_date: i.plannedDate, expected_date: i.expectedDate, status: i.status, source_report_id: i.sourceReportId, source_item_id: i.sourceItemId, source_label: i.sourceLabel }))
}
async function saveInsight() {
  if (!draft.value.title.trim()) { Notify.create({ type: 'warning', message: '제목을 입력해 주세요.' }); return }
  const item = { ...draft.value, title: draft.value.title.trim() }
  const items = editing.value ? props.report.insights.map(i => i.id === item.id ? item : i) : [...props.report.insights, item]
  if (await persist({ insights: payload(items) })) insightOpen.value = false
}
function removeInsight(item: MonthlyInsight) {
  editBase.value = props.report.updatedAt
  Dialog.create({ title: '항목 삭제', message: `“${item.title}” 항목을 삭제하시겠습니까?`, cancel: true }).onOk(() => { void persist({ insights: payload(props.report.insights.filter(i => i.id !== item.id)) }) })
}
</script>

<style scoped>
.monthly-highlights { display: grid; gap: 16px; margin-bottom: 16px; }
.highlight-card { scroll-margin-top: 20px; background: #fff; }
.highlight-item { overflow-wrap: anywhere; }
.monthly-highlights--dark .highlight-card,
.highlight-dialog--dark { background: #182334; color: #e2e8f0; border-color: #334155; color-scheme: dark; }
.monthly-highlights--dark :deep(.text-grey-5),
.monthly-highlights--dark :deep(.text-grey-7) { color: #aebbd0 !important; }
.monthly-highlights--dark .highlight-item a,
.monthly-highlights--dark :deep(.work-result-content a) { color: #93c5fd; }
.monthly-highlights--dark :deep(.work-result-content pre) { background: #111b2a; color: #e2e8f0; }
.monthly-highlights--dark :deep(.work-result-content .work-table-scroll),
.monthly-highlights--dark :deep(.work-result-content td),
.monthly-highlights--dark :deep(.work-result-content th) { border-color: #475569; }
.monthly-highlights--dark :deep(.work-result-content th) { background: #223047; }
</style>
