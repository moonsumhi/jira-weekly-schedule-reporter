<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">반복 업무</div>
      <q-chip dense square color="grey-2" text-color="grey-8" icon="repeat">
        규칙을 정해두면 매일 09시에 도래한 회차 이슈가 자동 생성됩니다
      </q-chip>
      <q-space />
      <q-select
        v-model="filterProjectId"
        :options="projectOptions"
        emit-value
        map-options
        clearable
        dense
        outlined
        label="프로젝트 필터"
        style="min-width: 200px"
        @update:model-value="load"
      />
      <q-btn color="primary" icon="add" label="반복 업무 추가" @click="openCreate" />
    </div>

    <q-card bordered flat>
      <q-table
        :rows="filteredRows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        flat
        :pagination="{ rowsPerPage: 10 }"
      >
        <template #body-cell-name="props">
          <q-td :props="props">
            <div class="text-weight-medium">{{ props.row.name }}</div>
            <div class="text-caption text-grey-6">{{ props.row.blueprint.title }}</div>
          </q-td>
        </template>

        <template #body-cell-project="props">
          <q-td :props="props">
            {{ projectName(props.row.projectId) }}
          </q-td>
        </template>

        <template #body-cell-rule="props">
          <q-td :props="props">
            <span>매월 {{ ruleSummary(props.row.rule) }} {{ props.row.rule.time }}</span>
            <div v-if="props.row.leadDays" class="text-caption text-grey-6">
              {{ props.row.leadDays }}일 전 생성
            </div>
          </q-td>
        </template>

        <template #body-cell-state="props">
          <q-td :props="props">
            <q-badge :color="props.row.active ? 'positive' : 'grey-5'" outline class="q-mr-xs">
              {{ props.row.active ? '활성' : '비활성' }}
            </q-badge>
            <q-badge :color="props.row.autoEnabled ? 'primary' : 'grey-5'" outline>
              {{ props.row.autoEnabled ? '자동' : '수동만' }}
            </q-badge>
          </q-td>
        </template>

        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn dense flat icon="playlist_add" color="teal-7" @click="openGenerate(props.row)">
              <q-tooltip>회차 생성</q-tooltip>
            </q-btn>
            <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)">
              <q-tooltip>수정</q-tooltip>
            </q-btn>
            <q-btn dense flat icon="delete" color="negative" @click="confirmDelete(props.row)">
              <q-tooltip>삭제</q-tooltip>
            </q-btn>
          </q-td>
        </template>

        <template #no-data>
          <div class="full-width text-center q-pa-lg text-grey-6">
            등록된 반복 업무가 없습니다. "반복 업무 추가"로 규칙을 만들어 보세요.
          </div>
        </template>
      </q-table>
    </q-card>

    <!-- 생성/수정 다이얼로그 -->
    <q-dialog v-model="editDialog">
      <q-card class="ri-dialog">
        <q-card-section class="q-px-lg q-pt-md q-pb-none">
          <div class="text-h6 text-weight-bold">{{ editingId ? '반복 업무 수정' : '반복 업무 추가' }}</div>
          <div class="text-caption text-grey-6">
            규칙을 저장하면 매월 지정한 날에 이슈가 자동 생성됩니다
          </div>
        </q-card-section>
        <q-separator class="q-mt-md" />

        <q-card-section class="q-px-lg q-pt-md q-pb-md ri-body">
          <!-- 기본 정보 -->
          <div class="section-label q-mb-sm">기본 정보</div>
          <div class="ri-fields">
            <q-input v-model="form.name" label="반복 업무 이름 *" outlined dense placeholder="예: 월간 정기배포" />
            <q-select
              v-model="form.projectId"
              :options="projectOptions"
              emit-value map-options
              label="프로젝트 *"
              outlined dense :disable="!!editingId"
              @update:model-value="onProjectChange"
            />
          </div>

          <q-separator class="q-my-lg" />

          <!-- 이슈 내용 -->
          <div class="section-label q-mb-sm">생성될 이슈 내용</div>
          <div class="ri-fields">
            <q-input v-model="form.title" label="제목 베이스 *" outlined dense placeholder="예: 정기배포"
              hint="생성 시 뒤에 회차가 붙습니다 → '정기배포 - 8월 1차'" />
            <div class="ri-row">
              <q-select v-model="form.type" :options="TYPE_OPTIONS" emit-value map-options
                label="유형" outlined dense class="col" />
              <q-select v-model="form.priority" :options="PRIORITY_OPTIONS" emit-value map-options
                label="우선순위" outlined dense class="col" />
            </div>
            <q-select
              v-model="form.assigneeId"
              :options="memberOptions"
              emit-value map-options clearable
              :label="form.showOnDashboard ? '담당자 *' : '담당자'"
              outlined dense />
            <q-input v-model="form.description" label="설명" type="textarea"
              outlined dense autogrow input-style="min-height: 60px" />
            <div class="ri-check">
              <q-checkbox v-model="form.showOnDashboard" dense label="대시보드 D-Day 표시" />
              <div v-if="form.showOnDashboard" class="ri-check-note text-caption text-grey-6">
                D-Day는 담당자 대시보드에만 표시됩니다. 담당자를 지정해 주세요.
              </div>
            </div>
          </div>

          <q-separator class="q-my-lg" />

          <!-- 반복 규칙 -->
          <div class="section-label q-mb-sm">반복 규칙</div>
          <div class="ri-fields">
            <q-btn-toggle
              v-model="form.mode"
              :options="MODE_OPTIONS"
              spread no-caps unelevated
              toggle-color="primary" color="grey-3" text-color="grey-8"
            />

            <!-- 날짜 지정 -->
            <q-select
              v-if="form.mode === 'day_of_month'"
              v-model="form.daysOfMonth"
              :options="dayOptions"
              multiple use-chips
              label="매월 회차일 *"
              outlined dense
              hint="매달 이슈를 만들 날짜 (예: 5, 19 → 매월 5일·19일)"
            />

            <!-- 요일 지정 -->
            <template v-else>
              <div class="ri-row">
                <q-select v-model="form.weeks" :options="WEEK_OPTIONS" emit-value map-options
                  multiple use-chips label="몇 번째 *" outlined dense class="col" />
                <q-select v-model="form.weekdaysSel" :options="WEEKDAY_OPTIONS" emit-value map-options
                  multiple use-chips label="요일 *" outlined dense class="col" />
              </div>
              <div class="text-caption text-grey-6" style="margin-top:-2px">
                <span v-if="weekdaySummary">→ 매월 {{ weekdaySummary }}</span>
                <span v-else>몇 번째와 요일을 고르면 조합됩니다 (예: 1번째 + 목 → 매월 첫 목요일)</span>
              </div>
            </template>

            <div class="ri-row">
              <q-input v-model="form.time" label="시각" outlined dense mask="##:##" placeholder="09:00" class="col">
                <template #prepend><q-icon name="schedule" size="18px" color="grey-6" /></template>
              </q-input>
              <q-input v-model.number="form.leadDays" type="number" min="0"
                label="며칠 전 생성" outlined dense class="col"
                suffix="일 전" hint="0 = 당일 생성" />
            </div>
          </div>

          <q-separator class="q-my-lg" />

          <!-- 옵션 -->
          <div class="section-label q-mb-sm">옵션</div>
          <div class="column q-gutter-y-md">
            <q-toggle v-model="form.autoEnabled" color="primary"
              label="자동 생성 (매일 스케줄러가 도래한 회차를 자동으로 만듭니다)" />
            <q-toggle v-model="form.active" color="positive"
              label="활성 (끄면 자동·수동 생성 모두 중단)" />
          </div>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right" class="q-px-lg q-py-md">
          <q-btn flat label="취소" color="grey-7" v-close-popup />
          <q-btn unelevated color="primary" label="저장" :loading="saving" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 회차 생성 다이얼로그 -->
    <q-dialog v-model="genDialog">
      <q-card class="ri-dialog">
        <q-card-section class="q-px-lg q-pt-md q-pb-none">
          <div class="text-h6 text-weight-bold">회차 생성</div>
          <div class="text-caption text-grey-6">{{ genTarget?.name }} · 선택한 월의 회차를 만듭니다</div>
        </q-card-section>
        <q-separator class="q-mt-md" />

        <q-card-section class="q-px-lg q-pt-md q-pb-md">
          <!-- 대상 월 -->
          <div class="section-label q-mb-sm">대상 월</div>
          <div class="ri-row">
            <q-input v-model.number="genYear" type="number" label="연도" outlined dense
              class="col" @update:model-value="loadPreview" />
            <q-select v-model="genMonth" :options="monthOptions" emit-value map-options label="월"
              outlined dense class="col" @update:model-value="loadPreview" />
          </div>

          <!-- 미리보기 -->
          <div class="row items-center q-mt-md q-mb-sm">
            <div class="section-label">회차 미리보기</div>
            <q-space />
            <span v-if="preview.length" class="text-caption text-grey-6">
              생성 {{ newCount }} · 기존 {{ preview.length - newCount }}
            </span>
          </div>
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="occ in preview" :key="occ.occurrenceDate">
              <q-item-section>
                <q-item-label>{{ occ.title }}</q-item-label>
                <q-item-label caption>{{ occ.occurrenceDate }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge v-if="occ.alreadyExists" color="grey-5" outline>이미 있음</q-badge>
                <q-badge v-else color="teal" outline>생성 예정</q-badge>
              </q-item-section>
            </q-item>
            <q-item v-if="!preview.length">
              <q-item-section class="text-grey-6 text-center q-py-sm">해당 월에 회차가 없습니다.</q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right" class="q-px-lg q-py-md">
          <q-btn flat label="닫기" color="grey-7" v-close-popup />
          <q-btn unelevated color="teal-7" :label="`생성 (${newCount})`"
            :loading="generating" :disable="!newCount" @click="doGenerate" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import type { QTableProps } from 'quasar'
import { getErrorMessage } from 'src/utils/http/error'
import { listProjects, listProjectMembers } from 'src/services/pm/project'
import type { Project, ProjectMember } from 'src/services/pm/project'
import type { IssueType, IssuePriority } from 'src/services/pm/issue'
import {
  listRecurringTemplates,
  createRecurringTemplate,
  updateRecurringTemplate,
  deleteRecurringTemplate,
  previewOccurrences,
  generateOccurrences,
} from 'src/services/pm/recurringIssue'
import type { RecurringIssueTemplate, Occurrence, TemplatePayload } from 'src/services/pm/recurringIssue'

const $q = useQuasar()

const TYPE_OPTIONS = [
  { label: '작업', value: 'TASK' },
  { label: '스토리', value: 'STORY' },
  { label: '버그', value: 'BUG' },
  { label: '하위작업', value: 'SUB_TASK' },
  { label: '에픽', value: 'EPIC' },
]
const PRIORITY_OPTIONS = [
  { label: '최고', value: 'HIGHEST' },
  { label: '높음', value: 'HIGH' },
  { label: '보통', value: 'MEDIUM' },
  { label: '낮음', value: 'LOW' },
  { label: '최저', value: 'LOWEST' },
]
const dayOptions = Array.from({ length: 31 }, (_, i) => i + 1)
const monthOptions = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}월`, value: i + 1 }))
const MODE_OPTIONS = [
  { label: '날짜 지정', value: 'day_of_month' },
  { label: '요일 지정', value: 'weekday' },
]
// "N번째 요일" = 그 달에 해당 요일이 N번째로 등장하는 날 (달력 줄 수가 아님).
// iCal/Google 캘린더 등과 동일한 표준 방식이라 라벨도 "1번째 …"로 표기한다.
const WEEK_OPTIONS = [
  { label: '1번째', value: 1 },
  { label: '2번째', value: 2 },
  { label: '3번째', value: 3 },
  { label: '4번째', value: 4 },
  { label: '5번째', value: 5 },
  { label: '마지막', value: -1 },
]
const WEEKDAY_OPTIONS = [
  { label: '월', value: 0 },
  { label: '화', value: 1 },
  { label: '수', value: 2 },
  { label: '목', value: 3 },
  { label: '금', value: 4 },
  { label: '토', value: 5 },
  { label: '일', value: 6 },
]
const WEEK_LABEL: Record<number, string> = { 1: '1번째', 2: '2번째', 3: '3번째', 4: '4번째', 5: '5번째', [-1]: '마지막' }
const WEEKDAY_LABEL = ['월', '화', '수', '목', '금', '토', '일']

const loading = ref(false)
const saving = ref(false)
const rows = ref<RecurringIssueTemplate[]>([])
const projects = ref<Project[]>([])
const members = ref<ProjectMember[]>([])
const filterProjectId = ref<string | null>(null)

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'name', label: '반복 업무', field: 'name', align: 'left' },
  { name: 'project', label: '프로젝트', field: 'projectId', align: 'left' },
  { name: 'rule', label: '반복 규칙', field: 'rule', align: 'left' },
  { name: 'state', label: '상태', field: 'active', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
]

const projectOptions = computed(() => projects.value.map((p) => ({ label: `${p.key} · ${p.name}`, value: p.id })))
const memberOptions = computed(() =>
  members.value.map((m) => ({ label: `${m.userName} (${m.userEmail})`, value: m.userId })),
)
const filteredRows = computed(() => rows.value)

function projectName(id: string): string {
  const p = projects.value.find((x) => x.id === id)
  return p ? `${p.key} · ${p.name}` : '-'
}

function ruleSummary(rule: RecurringIssueTemplate['rule']): string {
  if (rule.mode === 'weekday') {
    return (rule.weekdays ?? [])
      .map((w) => `${WEEK_LABEL[w.week]} ${WEEKDAY_LABEL[w.weekday]}요일`)
      .join(' · ') || '-'
  }
  return `${(rule.daysOfMonth ?? []).join('·')}일`
}

async function load() {
  loading.value = true
  try {
    rows.value = await listRecurringTemplates(filterProjectId.value ?? undefined)
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '목록 조회 실패') })
  } finally {
    loading.value = false
  }
}

// ── 생성/수정 폼 ──────────────────────────────────────────────
const editDialog = ref(false)
const editingId = ref<string | null>(null)
type RuleMode = 'day_of_month' | 'weekday'
type FormState = {
  name: string
  projectId: string
  title: string
  type: IssueType
  priority: IssuePriority
  assigneeId: string | null
  description: string
  showOnDashboard: boolean
  mode: RuleMode
  daysOfMonth: number[]
  weeks: number[]
  weekdaysSel: number[]
  time: string
  leadDays: number
  autoEnabled: boolean
  active: boolean
}

const form = ref<FormState>({
  name: '',
  projectId: '',
  title: '',
  type: 'TASK',
  priority: 'MEDIUM',
  assigneeId: null,
  description: '',
  showOnDashboard: false,
  mode: 'day_of_month',
  daysOfMonth: [],
  weeks: [],
  weekdaysSel: [],
  time: '09:00',
  leadDays: 0,
  autoEnabled: true,
  active: true,
})

function resetForm() {
  form.value = {
    name: '', projectId: '', title: '', type: 'TASK', priority: 'MEDIUM',
    assigneeId: null, description: '', showOnDashboard: false,
    mode: 'day_of_month', daysOfMonth: [],
    weeks: [], weekdaysSel: [], time: '09:00',
    leadDays: 0, autoEnabled: true, active: true,
  }
}

// 요일 지정 조합 미리보기 ("1번째 월요일 · 3번째 월요일")
const weekdaySummary = computed(() => {
  const parts: string[] = []
  for (const w of form.value.weeks) {
    for (const d of form.value.weekdaysSel) {
      parts.push(`${WEEK_LABEL[w]} ${WEEKDAY_LABEL[d]}요일`)
    }
  }
  return parts.join(' · ')
})

async function onProjectChange(pid: string | null) {
  members.value = []
  form.value.assigneeId = null
  if (pid) {
    try {
      members.value = await listProjectMembers(pid)
    } catch { /* 멤버 조회 실패는 무시 (담당자 선택만 비게 됨) */ }
  }
}

function openCreate() {
  resetForm()
  editingId.value = null
  editDialog.value = true
}

async function openEdit(row: RecurringIssueTemplate) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    projectId: row.projectId,
    title: row.blueprint.title,
    type: row.blueprint.type,
    priority: row.blueprint.priority,
    assigneeId: row.blueprint.assigneeId,
    description: row.blueprint.description ?? '',
    showOnDashboard: row.blueprint.showOnDashboard,
    mode: row.rule.mode ?? 'day_of_month',
    daysOfMonth: [...(row.rule.daysOfMonth ?? [])],
    weeks: [...new Set((row.rule.weekdays ?? []).map(w => w.week))],
    weekdaysSel: [...new Set((row.rule.weekdays ?? []).map(w => w.weekday))],
    time: row.rule.time,
    leadDays: row.leadDays,
    autoEnabled: row.autoEnabled,
    active: row.active,
  }
  await onProjectChange(row.projectId)
  form.value.assigneeId = row.blueprint.assigneeId
  editDialog.value = true
}

function buildPayload(): TemplatePayload {
  return {
    name: form.value.name.trim(),
    project_id: form.value.projectId,
    blueprint: {
      title: form.value.title.trim(),
      description: form.value.description || null,
      type: form.value.type,
      priority: form.value.priority,
      assignee_id: form.value.assigneeId,
      label_ids: [],
      show_on_dashboard: form.value.showOnDashboard,
    },
    rule: {
      freq: 'monthly',
      mode: form.value.mode,
      days_of_month: form.value.mode === 'day_of_month'
        ? [...form.value.daysOfMonth].sort((a, b) => a - b)
        : [],
      weekdays: form.value.mode === 'weekday'
        ? form.value.weeks.flatMap(w => form.value.weekdaysSel.map(d => ({ week: w, weekday: d })))
        : [],
      time: form.value.time,
    },
    lead_days: form.value.leadDays || 0,
    auto_enabled: form.value.autoEnabled,
    active: form.value.active,
  }
}

async function save() {
  const ruleSet = form.value.mode === 'day_of_month'
    ? form.value.daysOfMonth.length > 0
    : form.value.weeks.length > 0 && form.value.weekdaysSel.length > 0
  if (!form.value.name.trim() || !form.value.projectId || !form.value.title.trim() || !ruleSet) {
    $q.notify({
      type: 'warning',
      message: form.value.mode === 'weekday'
        ? '이름·프로젝트·제목과 몇 번째·요일은 필수입니다.'
        : '이름·프로젝트·제목·회차일은 필수입니다.',
    })
    return
  }
  if (form.value.showOnDashboard && !form.value.assigneeId) {
    $q.notify({
      type: 'warning',
      message: 'D-Day 표시는 담당자 대시보드에만 노출됩니다. 담당자를 지정해 주세요.',
    })
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (editingId.value) {
      await updateRecurringTemplate(editingId.value, {
        name: payload.name,
        blueprint: payload.blueprint,
        rule: payload.rule,
        lead_days: payload.lead_days,
        auto_enabled: payload.auto_enabled,
        active: payload.active,
      })
    } else {
      await createRecurringTemplate(payload)
    }
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
    editDialog.value = false
    await load()
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: RecurringIssueTemplate) {
  $q.dialog({
    title: '삭제 확인',
    message: `"${row.name}" 반복 업무를 삭제할까요? (이미 생성된 이슈는 그대로 유지됩니다)`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void doDelete(row.id)
  })
}

async function doDelete(id: string) {
  try {
    await deleteRecurringTemplate(id)
    $q.notify({ type: 'positive', message: '삭제되었습니다.' })
    await load()
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
  }
}

// ── 회차 생성 ──────────────────────────────────────────────
const genDialog = ref(false)
const genTarget = ref<RecurringIssueTemplate | null>(null)
const genYear = ref(new Date().getFullYear())
const genMonth = ref(new Date().getMonth() + 1)
const preview = ref<Occurrence[]>([])
const generating = ref(false)

const newCount = computed(() => preview.value.filter((o) => !o.alreadyExists).length)

function openGenerate(row: RecurringIssueTemplate) {
  genTarget.value = row
  genYear.value = new Date().getFullYear()
  genMonth.value = new Date().getMonth() + 1
  preview.value = []
  genDialog.value = true
  void loadPreview()
}

async function loadPreview() {
  if (!genTarget.value || !genYear.value || !genMonth.value) return
  try {
    preview.value = await previewOccurrences(genTarget.value.id, genYear.value, genMonth.value)
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '미리보기 실패') })
  }
}

async function doGenerate() {
  if (!genTarget.value) return
  generating.value = true
  try {
    const res = await generateOccurrences(genTarget.value.id, genYear.value, genMonth.value)
    $q.notify({
      type: 'positive',
      message: `${res.created.length}건 생성, ${res.skipped.length}건 건너뜀`,
    })
    await loadPreview()
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '생성 실패') })
  } finally {
    generating.value = false
  }
}

onMounted(async () => {
  try {
    projects.value = await listProjects()
  } catch { /* ignore */ }
  await load()
})
</script>

<style scoped>
.ri-dialog {
  width: 560px;
  max-width: 95vw;
}
.ri-body {
  max-height: 72vh;
  overflow-y: auto;
}
/* 섹션 내 필드들 세로 간격 — 필드가 자체 하단 메시지 공간(~20px)을
   가지므로 gap 은 소폭만. (과하면 hint 없는 필드 사이가 텅 비어 보임) */
.ri-fields {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* 2컬럼 한 줄 (필드 폭·시작 위치 일치) */
.ri-row {
  display: flex;
  gap: 16px;
}
.ri-row > .col {
  flex: 1 1 0;
  min-width: 0;
}
/* D-Day 체크박스 — 위 필드와 구분되도록 얇은 구분선 + 여백 */
.ri-check {
  margin-top: 2px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}
/* 체크박스 밑 주의사항 — 체크박스 라벨 글자와 시작선 맞춤 */
.ri-check-note {
  margin-top: 4px;
  padding-left: 34px;
}
.section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9e9e9e;
}
</style>
