<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="wr-dialog">
      <!-- 헤더 -->
      <div class="wr-header row items-center no-wrap q-px-lg q-py-md">
        <div class="row items-center q-gutter-sm">
          <q-icon :name="SECTION_ICON[section]" :color="SECTION_COLOR[section]" size="22px" />
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ SECTION_LABEL[section] }}</div>
            <div class="text-caption text-grey-6">{{ isEdit ? '항목 수정' : '새 항목 추가' }}</div>
          </div>
        </div>
        <q-space />
        <q-btn flat round dense icon="close" color="grey-6" @click="close" />
      </div>
      <q-separator />

      <!-- 폼 바디 (스크롤) -->
      <q-scroll-area style="height: min(65vh, 520px)">
        <div class="q-px-lg q-py-md column q-gutter-y-md">

          <!-- ① 제목 -->
          <div>
            <div class="field-label">제목 <span class="text-negative">*</span></div>
            <q-input
              v-model="form.title"
              outlined
              autofocus
              placeholder="안건 제목을 간결하게 입력하세요"
              :rules="[v => !!v.trim() || '제목을 입력해주세요.']"
              hide-bottom-space
            />
          </div>

          <!-- ② 담당자 -->
          <div>
            <div class="field-label">담당자</div>
            <q-select
              v-model="form.owner"
              :options="ownerOptions"
              outlined clearable
              emit-value map-options
              option-value="value"
              option-label="label"
              :loading="loadingUsers"
              placeholder="담당자를 선택하세요"
              popup-content-style="font-size: 14px"
            >
              <template #no-option>
                <q-item><q-item-section class="text-grey-6 text-center">팀원 없음</q-item-section></q-item>
              </template>
              <template #selected-item="scope">
                <div class="row items-center q-gutter-xs">
                  <q-avatar size="22px" color="primary" text-color="white" style="font-size:11px">
                    {{ (scope.opt.label as string).charAt(0) }}
                  </q-avatar>
                  <span>{{ scope.opt.label }}</span>
                </div>
              </template>
              <template #option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-avatar size="28px" color="primary" text-color="white" style="font-size:12px">
                      {{ (scope.opt.label as string).charAt(0) }}
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>{{ scope.opt.label }}</q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- ③ MAIN_AGENDA 전용 -->
          <template v-if="section === 'MAIN_AGENDA'">
            <div class="row q-col-gutter-md">
              <div class="col-6">
                <div class="field-label">카테고리</div>
                <q-select
                  v-model="form.category"
                  :options="AGENDA_CATEGORIES"
                  outlined clearable
                  emit-value map-options
                  placeholder="선택"
                >
                  <template #option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section avatar>
                        <q-icon :name="CATEGORY_ICON[scope.opt.value] ?? 'label'" size="18px" color="grey-6" />
                      </q-item-section>
                      <q-item-section>{{ scope.opt.label }}</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </div>
              <div class="col-6">
                <div class="field-label">진행 상태</div>
                <q-select
                  v-model="form.agenda_status"
                  :options="AGENDA_STATUSES"
                  outlined clearable
                  emit-value map-options
                  placeholder="선택"
                >
                  <template #option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section avatar>
                        <q-badge :color="AGENDA_STATUS_COLOR[scope.opt.value] ?? 'grey'" :label="scope.opt.label" />
                      </q-item-section>
                    </q-item>
                  </template>
                  <template #selected-item="scope">
                    <q-badge :color="AGENDA_STATUS_COLOR[scope.opt.value] ?? 'grey-5'" :label="scope.opt.label" />
                  </template>
                </q-select>
              </div>
            </div>
            <div>
              <div class="field-label">주요 내용</div>
              <q-input
                v-model="form.content"
                outlined autogrow
                type="textarea"
                placeholder="안건의 배경, 현황, 핵심 내용을 입력하세요"
                input-style="min-height: 80px; resize: vertical"
              />
            </div>
          </template>

          <!-- ④ ISSUE_RISK 전용 -->
          <template v-if="section === 'ISSUE_RISK'">
            <div class="row q-col-gutter-md">
              <div class="col-6">
                <div class="field-label">유형</div>
                <q-select
                  v-model="form.item_type"
                  :options="RISK_TYPES"
                  outlined clearable
                  emit-value map-options
                  placeholder="선택"
                />
              </div>
              <div class="col-6">
                <div class="field-label">영향도</div>
                <q-select
                  v-model="form.impact"
                  :options="IMPACT_LEVELS"
                  outlined clearable
                  emit-value map-options
                  placeholder="선택"
                >
                  <template #option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section avatar>
                        <q-icon :name="IMPACT_ICON[scope.opt.value] ?? 'remove'" :color="IMPACT_COLOR[scope.opt.value] ?? 'grey'" size="18px" />
                      </q-item-section>
                      <q-item-section>{{ scope.opt.label }}</q-item-section>
                    </q-item>
                  </template>
                  <template #selected-item="scope">
                    <div class="row items-center q-gutter-xs">
                      <q-icon :name="IMPACT_ICON[scope.opt.value] ?? 'remove'" :color="IMPACT_COLOR[scope.opt.value] ?? 'grey'" size="16px" />
                      <span>{{ scope.opt.label }}</span>
                    </div>
                  </template>
                </q-select>
              </div>
            </div>
            <div>
              <div class="field-label">상세 내용</div>
              <q-input
                v-model="form.content"
                outlined autogrow
                type="textarea"
                placeholder="특이사항 또는 리스크의 상세 내용을 입력하세요"
                input-style="min-height: 72px; resize: vertical"
              />
            </div>
            <div>
              <div class="field-label">대응 방안</div>
              <q-input
                v-model="form.action_plan"
                outlined autogrow
                type="textarea"
                placeholder="조치 계획 또는 대응 방안을 입력하세요"
                input-style="min-height: 60px; resize: vertical"
              />
            </div>
          </template>

          <!-- ⑤ DECISION_REQUIRED 전용 -->
          <template v-if="section === 'DECISION_REQUIRED'">
            <div>
              <div class="field-label">배경</div>
              <q-input
                v-model="form.background"
                outlined autogrow
                type="textarea"
                placeholder="결정이 필요한 배경 및 이유를 입력하세요"
                input-style="min-height: 64px; resize: vertical"
              />
            </div>
            <div>
              <div class="field-label">선택지</div>
              <q-input
                v-model="form.options"
                outlined autogrow
                type="textarea"
                placeholder="① 1안 설명&#10;② 2안 설명"
                input-style="min-height: 64px; resize: vertical"
              />
            </div>
            <div>
              <div class="field-label">요청 결정 내용</div>
              <q-input
                v-model="form.requested_decision"
                outlined autogrow
                type="textarea"
                placeholder="최종적으로 어떤 결정을 요청하는지 명확하게 작성하세요"
                input-style="min-height: 60px; resize: vertical"
              />
            </div>
            <div>
              <div class="field-label">희망 결정일</div>
              <q-input v-model="form.desired_date" outlined placeholder="YYYY-MM-DD">
                <template #append>
                  <q-icon name="event" class="cursor-pointer" color="grey-6">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="form.desired_date" mask="YYYY-MM-DD" minimal>
                        <div class="row items-center justify-end q-pa-sm">
                          <q-btn v-close-popup label="닫기" color="primary" flat no-caps dense />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
          </template>

          <!-- ⑥ 보고서 포함 여부 -->
          <q-separator />
          <div class="row items-center justify-between q-py-xs">
            <div>
              <div class="text-body2 text-weight-medium">보고서에 포함</div>
              <div class="text-caption text-grey-6">미리보기 및 출력 시 이 항목의 포함 여부</div>
            </div>
            <q-toggle v-model="form.include_in_report" color="primary" size="md" />
          </div>

        </div>
      </q-scroll-area>

      <q-separator />
      <div class="row items-center justify-end q-px-lg q-py-sm q-gutter-sm">
        <q-btn flat label="취소" no-caps color="grey-7" @click="close" />
        <q-btn
          color="primary"
          :label="isEdit ? '수정 저장' : '추가'"
          :loading="saving"
          no-caps
          icon-right="check"
          @click="save"
        />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { Notify } from 'quasar'
import { addManualItem, updateManualItem, type ManualItem, type ManualItemCreate, type ManualItemSection } from 'src/services/pm/reports'
import { listPmUsers } from 'src/services/pm/users'
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
const SECTION_ICON: Record<ManualItemSection, string> = {
  MAIN_AGENDA: 'task_alt',
  ISSUE_RISK: 'warning_amber',
  DECISION_REQUIRED: 'gavel',
}
const SECTION_COLOR: Record<ManualItemSection, string> = {
  MAIN_AGENDA: 'blue',
  ISSUE_RISK: 'orange',
  DECISION_REQUIRED: 'purple',
}

const AGENDA_CATEGORIES = ['운영', '보안', '개발', '인프라', '장애', '대외협력', '기타'].map(v => ({ label: v, value: v }))
const AGENDA_STATUSES   = ['예정', '진행중', '완료', '지연', '보류'].map(v => ({ label: v, value: v }))
const AGENDA_STATUS_COLOR: Record<string, string> = {
  예정: 'blue-5', 진행중: 'orange', 완료: 'positive', 지연: 'negative', 보류: 'grey-5',
}
const RISK_TYPES    = ['특이사항', '리스크', '장애', '일정지연', '협조필요'].map(v => ({ label: v, value: v }))
const IMPACT_LEVELS = ['높음', '보통', '낮음'].map(v => ({ label: v, value: v }))
const IMPACT_ICON:  Record<string, string> = { 높음: 'keyboard_double_arrow_up', 보통: 'remove', 낮음: 'keyboard_double_arrow_down' }
const IMPACT_COLOR: Record<string, string> = { 높음: 'negative', 보통: 'orange', 낮음: 'positive' }
const CATEGORY_ICON: Record<string, string> = {
  운영: 'settings', 보안: 'security', 개발: 'code', 인프라: 'dns',
  장애: 'report_problem', 대외협력: 'handshake', 기타: 'more_horiz',
}

const saving      = ref(false)
const isEdit      = ref(false)
const loadingUsers = ref(false)
const ownerOptions = ref<{ label: string; value: string }[]>([])

onMounted(async () => {
  loadingUsers.value = true
  try {
    const users = await listPmUsers('데이터운영팀')
    ownerOptions.value = users.map(u => ({ label: u.name || u.email, value: u.name || u.email }))
  } catch {
    // 실패 시 빈 목록
  } finally {
    loadingUsers.value = false
  }
})

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

const EMPTY_FORM: FormType = {
  title: '', owner: null, include_in_report: true,
  category: null, content: null, agenda_status: null,
  item_type: null, impact: null, action_plan: null,
  background: null, options: null, requested_decision: null, desired_date: null,
}

const form = ref<FormType>({ ...EMPTY_FORM })

watch(() => props.modelValue, (open) => {
  if (!open) return
  isEdit.value = !!props.item
  form.value = props.item ? {
    title:               props.item.title,
    owner:               props.item.owner,
    include_in_report:   props.item.includeInReport,
    category:            props.item.category,
    content:             props.item.content,
    agenda_status:       props.item.agendaStatus,
    item_type:           props.item.itemType,
    impact:              props.item.impact,
    action_plan:         props.item.actionPlan,
    background:          props.item.background,
    options:             props.item.options,
    requested_decision:  props.item.requestedDecision,
    desired_date:        props.item.desiredDate,
  } : { ...EMPTY_FORM }
}, { immediate: true })

function close() {
  emit('update:modelValue', false)
}

async function save() {
  if (!form.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }

  const payload: ManualItemCreate = { section: props.section, title: form.value.title.trim() }
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
    const result = isEdit.value && props.item
      ? await updateManualItem(props.reportId, props.item.id, payload)
      : await addManualItem(props.reportId, payload)
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

<style scoped>
.wr-dialog {
  width: 620px;
  max-width: 96vw;
  border-radius: 12px !important;
}

.wr-header {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}
</style>
