<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width:560px; max-width:96vw">
      <q-card-section class="row items-center q-pb-none">
        <div>
          <div class="text-h6">{{ isEdit ? '항목 수정' : '항목 추가' }}</div>
          <div class="text-caption text-grey-6">{{ SECTION_LABEL[section] }}</div>
        </div>
        <q-space />
        <q-btn flat round dense icon="close" @click="close" />
      </q-card-section>
      <q-separator class="q-mt-sm" />

      <q-card-section class="q-gutter-sm">
        <!-- 공통 -->
        <q-input v-model="form.title" label="제목 *" outlined dense autofocus />
        <q-input v-model="form.owner" label="담당자" outlined dense />

        <!-- MAIN_AGENDA -->
        <template v-if="section === 'MAIN_AGENDA'">
          <q-select v-model="form.category" :options="AGENDA_CATEGORIES" label="카테고리" outlined dense clearable emit-value map-options />
          <q-input v-model="form.content" label="주요 내용" type="textarea" outlined dense rows="3" />
          <q-select v-model="form.agenda_status" :options="AGENDA_STATUSES" label="진행 상태" outlined dense clearable emit-value map-options />
        </template>

        <!-- ISSUE_RISK -->
        <template v-if="section === 'ISSUE_RISK'">
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-select v-model="form.item_type" :options="RISK_TYPES" label="유형" outlined dense clearable emit-value map-options />
            </div>
            <div class="col-6">
              <q-select v-model="form.impact" :options="IMPACT_LEVELS" label="영향도" outlined dense clearable emit-value map-options />
            </div>
          </div>
          <q-input v-model="form.content" label="상세 내용" type="textarea" outlined dense rows="3" />
          <q-input v-model="form.action_plan" label="대응 방안" type="textarea" outlined dense rows="2" />
        </template>

        <!-- DECISION_REQUIRED -->
        <template v-if="section === 'DECISION_REQUIRED'">
          <q-input v-model="form.background" label="배경" type="textarea" outlined dense rows="2" />
          <q-input v-model="form.options" label="선택지" type="textarea" outlined dense rows="2" placeholder="① 안, ② 안 ..." />
          <q-input v-model="form.requested_decision" label="요청 결정 내용" type="textarea" outlined dense rows="2" />
          <q-input v-model="form.desired_date" label="희망 결정일" outlined dense>
            <template #append>
              <q-icon name="event" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-date v-model="form.desired_date" mask="YYYY-MM-DD">
                    <div class="row items-center justify-end"><q-btn v-close-popup label="닫기" color="primary" flat /></div>
                  </q-date>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>
        </template>

        <q-toggle v-model="form.include_in_report" label="보고서에 포함" color="primary" />
      </q-card-section>

      <q-separator />
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="취소" no-caps @click="close" />
        <q-btn color="primary" :label="isEdit ? '수정' : '추가'" :loading="saving" no-caps @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Notify } from 'quasar'
import { addManualItem, updateManualItem, type ManualItem, type ManualItemCreate, type ManualItemSection } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{
  modelValue: boolean
  reportId: string
  section: ManualItemSection
  item: ManualItem | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved', report: Awaited<ReturnType<typeof addManualItem>>): void
}>()

const SECTION_LABEL: Record<ManualItemSection, string> = {
  MAIN_AGENDA: '주요 안건',
  ISSUE_RISK: '특이사항 및 리스크',
  DECISION_REQUIRED: '결정 필요 사항',
}

const AGENDA_CATEGORIES = ['운영', '보안', '개발', '인프라', '장애', '대외협력', '기타'].map(v => ({ label: v, value: v }))
const AGENDA_STATUSES   = ['예정', '진행중', '완료', '지연', '보류'].map(v => ({ label: v, value: v }))
const RISK_TYPES        = ['특이사항', '리스크', '장애', '일정지연', '협조필요'].map(v => ({ label: v, value: v }))
const IMPACT_LEVELS     = ['높음', '보통', '낮음'].map(v => ({ label: v, value: v }))

const saving = ref(false)
const isEdit = ref(false)

type FormType = {
  title: string
  owner: string | null
  include_in_report: boolean
  category: string | null
  content: string | null
  agenda_status: string | null
  item_type: string | null
  impact: string | null
  action_plan: string | null
  background: string | null
  options: string | null
  requested_decision: string | null
  desired_date: string | null
}

const form = ref<FormType>({
  title: '',
  owner: null,
  include_in_report: true,
  category: null,
  content: null,
  agenda_status: null,
  item_type: null,
  impact: null,
  action_plan: null,
  background: null,
  options: null,
  requested_decision: null,
  desired_date: null,
})

watch(() => props.modelValue, (open) => {
  if (!open) return
  isEdit.value = !!props.item
  if (props.item) {
    form.value = {
      title: props.item.title,
      owner: props.item.owner,
      include_in_report: props.item.includeInReport,
      category: props.item.category,
      content: props.item.content,
      agenda_status: props.item.agendaStatus,
      item_type: props.item.itemType,
      impact: props.item.impact,
      action_plan: props.item.actionPlan,
      background: props.item.background,
      options: props.item.options,
      requested_decision: props.item.requestedDecision,
      desired_date: props.item.desiredDate,
    }
  } else {
    form.value = {
      title: '', owner: null, include_in_report: true,
      category: null, content: null, agenda_status: null,
      item_type: null, impact: null, action_plan: null,
      background: null, options: null, requested_decision: null, desired_date: null,
    }
  }
}, { immediate: true })

function close() {
  emit('update:modelValue', false)
}

async function save() {
  if (!form.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }

  const payload: ManualItemCreate = {
    section: props.section,
    title: form.value.title.trim(),
  }
  if (form.value.owner)              payload.owner = form.value.owner
  if (!form.value.include_in_report) payload.include_in_report = false
  if (form.value.category)           payload.category = form.value.category
  if (form.value.content)            payload.content = form.value.content
  if (form.value.agenda_status)      payload.agenda_status = form.value.agenda_status
  if (form.value.item_type)          payload.item_type = form.value.item_type
  if (form.value.impact)             payload.impact = form.value.impact
  if (form.value.action_plan)        payload.action_plan = form.value.action_plan
  if (form.value.background)         payload.background = form.value.background
  if (form.value.options)            payload.options = form.value.options
  if (form.value.requested_decision) payload.requested_decision = form.value.requested_decision
  if (form.value.desired_date)       payload.desired_date = form.value.desired_date

  saving.value = true
  try {
    let result
    if (isEdit.value && props.item) {
      result = await updateManualItem(props.reportId, props.item.id, payload)
    } else {
      result = await addManualItem(props.reportId, payload)
    }
    emit('saved', result)
    close()
    Notify.create({ type: 'positive', message: isEdit.value ? '수정되었습니다.' : '추가되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    saving.value = false
  }
}
</script>
