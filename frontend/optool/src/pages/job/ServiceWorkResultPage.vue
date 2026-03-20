<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">작업 결과서</div>
      <q-space />
      <q-toggle v-model="includeDeleted" label="삭제 포함" dense />
      <q-btn outline icon="refresh" label="새로고침" :loading="loading" @click="load" />
      <q-btn color="primary" icon="add" label="작업 결과서 추가" @click="openCreate" />
    </div>

    <q-card bordered>
      <!-- Filters -->
      <q-card-section class="row items-center q-gutter-sm">
        <q-input
          v-model="filter"
          dense
          outlined
          clearable
          debounce="200"
          placeholder="작업명 / 작업자 / 시스템명 검색"
          class="col"
        />
        <q-select
          v-model="resultFilter"
          :options="resultOptions"
          dense
          outlined
          clearable
          label="결과 필터"
          style="min-width: 130px"
        />
      </q-card-section>

      <q-separator />

      <!-- Table -->
      <q-card-section class="q-pa-none">
        <q-table
          :rows="filteredRows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="pagination"
          @update:pagination="onPagination"
          flat
          bordered
        >
          <!-- 작업 결과 badge -->
          <template #body-cell-result="props">
            <q-td :props="props">
              <q-badge :color="resultColor(props.row.result)" outline>
                {{ props.row.result }}
              </q-badge>
            </q-td>
          </template>

          <!-- 서비스 영향 -->
          <template #body-cell-service_affected="props">
            <q-td :props="props">
              <q-badge :color="props.row.service_affected ? 'negative' : 'positive'" outline>
                {{ props.row.service_affected ? '영향있음' : '영향없음' }}
              </q-badge>
            </q-td>
          </template>

          <!-- Actions -->
          <template #body-cell-actions="props">
            <q-td :props="props">
              <div class="row items-center justify-end q-gutter-xs">
                <q-btn
                  dense
                  outline
                  icon="visibility"
                  label="상세"
                  @click="openDetail(props.row)"
                />
                <q-btn
                  dense
                  outline
                  icon="edit"
                  label="수정"
                  :disable="Boolean(props.row.is_deleted)"
                  @click="openEdit(props.row)"
                />
                <q-btn
                  dense
                  color="negative"
                  icon="delete"
                  label="삭제"
                  :disable="Boolean(props.row.is_deleted)"
                  :loading="actingId === String(props.row.id) && actingType === 'delete'"
                  @click="confirmDelete(props.row)"
                />
              </div>
            </q-td>
          </template>

          <template #no-data>
            <div class="full-width row flex-center q-pa-lg text-grey-6">
              표시할 데이터가 없습니다.
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create / Edit Dialog -->
    <q-dialog v-model="formDialog" persistent>
      <q-card style="width: 800px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ isEdit ? '작업 결과서 수정' : '작업 결과서 추가' }}</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-separator />

        <q-card-section class="col scroll" style="min-height: 0;">
          <!-- 기본 정보 -->
          <div class="text-subtitle1 text-weight-bold q-mt-sm q-mb-xs">기본 정보</div>
          <div class="row q-gutter-sm">
            <q-input
              v-model="form.title"
              outlined
              dense
              label="작업명 *"
              class="col-12"
            />
            <q-input
              v-model="form.work_date"
              outlined
              dense
              label="작업 일시 * (YYYY-MM-DD HH:MM)"
              mask="####-##-## ##:##"
              class="col-12 col-sm-6"
            >
              <template #append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <q-date
                      :model-value="form.work_date ? form.work_date.slice(0, 10) : ''"
                      @update:model-value="(val: string) => { const time = form.work_date && form.work_date.length > 10 ? form.work_date.slice(10) : ' 00:00'; form.work_date = val + time }"
                      mask="YYYY-MM-DD"
                    >
                      <div class="row items-center justify-end">
                        <q-btn v-close-popup label="닫기" color="primary" flat />
                      </div>
                    </q-date>
                  </q-popup-proxy>
                </q-icon>
              </template>
            </q-input>
            <q-select
              v-model="form.category"
              :options="categoryOptions"
              outlined
              dense
              label="작업 구분 *"
              class="col-12 col-sm-5"
            />
          </div>
          <div class="row q-gutter-sm q-mt-xs">
            <q-input v-model="form.worker" outlined dense label="작업자 *" class="col-12 col-sm-5" />
            <q-input v-model="form.requester" outlined dense label="신청자 *" class="col-12 col-sm-5" />
            <q-input v-model="form.system_name" outlined dense label="시스템명 *" class="col-12" />
          </div>

          <q-separator class="q-my-md" />

          <!-- 작업 결과 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">작업 결과</div>
          <div class="row q-gutter-sm">
            <q-select
              v-model="form.result"
              :options="resultOptions"
              outlined
              dense
              label="작업 최종 결과 *"
              class="col-12 col-sm-5"
            />
            <q-input
              v-model="form.actual_start_time"
              outlined
              dense
              label="실제 시작 시간 (HH:MM)"
              mask="##:##"
              class="col-12 col-sm-3"
            />
            <q-input
              v-model="form.actual_end_time"
              outlined
              dense
              label="실제 종료 시간 (HH:MM)"
              mask="##:##"
              class="col-12 col-sm-3"
            />
          </div>
          <q-input
            v-model="form.summary"
            outlined
            dense
            type="textarea"
            autogrow
            label="작업 결과 요약 *"
            class="q-mt-sm"
          />

          <q-separator class="q-my-md" />

          <!-- 서비스 영향 결과 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">서비스 영향 결과</div>
          <q-toggle v-model="form.service_affected" label="서비스 영향 여부" class="q-mb-sm" />
          <q-input
            v-model="form.actual_downtime"
            outlined
            dense
            label="실제 서비스 중단 시간"
            class="col-12 col-sm-5"
          />

          <q-separator class="q-my-md" />

          <!-- 작업 절차 결과 -->
          <div class="row items-center q-mb-xs">
            <div class="text-subtitle1 text-weight-bold">세부 절차 결과</div>
            <q-space />
            <q-btn flat dense icon="add" label="단계 추가" @click="addStepResult" />
          </div>
          <q-list bordered separator>
            <q-item v-for="(step, i) in form.step_results" :key="i">
              <q-item-section>
                <div class="row items-center q-mb-xs">
                  <div class="col text-caption text-grey-7 text-weight-medium">세부 절차 {{ i + 1 }}</div>
                  <q-btn flat dense icon="delete" color="negative" @click="removeStepResult(i)" />
                </div>
                <q-input
                  v-model="step.task"
                  outlined
                  dense
                  type="textarea"
                  autogrow
                  label="세부 작업 내용 *"
                  class="q-mb-xs"
                />
                <div class="row q-gutter-xs items-center">
                  <q-input
                    v-model="step.person"
                    outlined
                    dense
                    label="담당자 *"
                    class="col"
                  />
                  <q-toggle v-model="step.completed" label="완료" dense />
                  <q-input
                    v-model="step.notes"
                    outlined
                    dense
                    label="비고"
                    class="col"
                  />
                </div>
              </q-item-section>
            </q-item>
            <q-item v-if="form.step_results.length === 0">
              <q-item-section class="text-grey-6 text-caption q-pa-sm">
                작업 절차 결과가 없습니다. 단계를 추가하세요.
              </q-item-section>
            </q-item>
          </q-list>

          <q-separator class="q-my-md" />

          <!-- 이슈 및 특이 사항 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">이슈 및 특이 사항</div>
          <q-toggle v-model="form.issues_occurred" label="이슈 발생 여부" class="q-mb-sm" />
          <div v-if="form.issues_occurred" class="q-gutter-sm">
            <q-input
              v-model="form.issue_details"
              outlined
              dense
              type="textarea"
              autogrow
              label="이슈 내용"
              class="q-mb-sm"
            />
            <q-input
              v-model="form.action_taken"
              outlined
              dense
              type="textarea"
              autogrow
              label="이슈 조치 내용"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- 사후 확인 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">사후 확인</div>
          <q-toggle v-model="form.post_check_done" label="사후 확인 완료" class="q-mb-sm" />
          <q-input
            v-model="form.post_check_details"
            outlined
            dense
            type="textarea"
            autogrow
            label="사후 확인 내용"
          />

          <q-separator class="q-my-md" />

          <!-- 기타 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">기타</div>
          <q-input
            v-model="form.notes"
            outlined
            dense
            type="textarea"
            autogrow
            label="기타 특이 사항"
            class="q-mb-sm"
          />
          <q-input
            v-model="form.plan_id"
            outlined
            dense
            label="참조 작업계획서 ID (선택)"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            :label="isEdit ? '저장' : '생성'"
            :loading="actingType === 'create' || actingType === 'edit'"
            @click="isEdit ? doEdit() : doCreate()"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Detail Dialog -->
    <q-dialog v-model="detailDialog">
      <q-card v-if="detailRow" style="width: 720px; max-width: 95vw; max-height: 90vh" class="column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">작업 결과서 상세</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-separator />

        <q-card-section class="col scroll">
          <!-- 기본 정보 -->
          <div class="row q-gutter-x-md q-mb-sm">
            <div class="col">
              <div class="text-caption text-grey-7">작업명</div>
              <div class="text-body1 text-weight-medium">{{ detailRow.title }}</div>
            </div>
            <div class="col-auto">
              <q-badge :color="resultColor(detailRow.result)" outline>
                {{ detailRow.result }}
              </q-badge>
            </div>
          </div>

          <q-separator class="q-my-sm" />

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <div class="text-caption text-grey-7">작업 일시</div>
              <div>{{ detailRow.work_date }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">작업 구분</div>
              <div>{{ detailRow.category }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">작업자</div>
              <div>{{ detailRow.worker }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">신청자</div>
              <div>{{ detailRow.requester }}</div>
            </div>
            <div class="col-12">
              <div class="text-caption text-grey-7">시스템명</div>
              <div>{{ detailRow.system_name }}</div>
            </div>
          </div>

          <q-separator class="q-my-sm" />

          <!-- 작업 결과 -->
          <div class="text-subtitle2 text-weight-bold q-mb-xs">작업 결과</div>
          <div class="row q-col-gutter-sm q-mb-xs">
            <div v-if="detailRow.actual_start_time" class="col-6">
              <div class="text-caption text-grey-7">실제 시작 시간</div>
              <div>{{ detailRow.actual_start_time }}</div>
            </div>
            <div v-if="detailRow.actual_end_time" class="col-6">
              <div class="text-caption text-grey-7">실제 종료 시간</div>
              <div>{{ detailRow.actual_end_time }}</div>
            </div>
          </div>
          <div class="q-mb-xs">
            <div class="text-caption text-grey-7">결과 요약</div>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.summary }}</div>
          </div>

          <q-separator class="q-my-sm" />

          <!-- 서비스 영향 결과 -->
          <div class="text-subtitle2 text-weight-bold q-mb-xs">서비스 영향 결과</div>
          <div class="row q-col-gutter-sm q-mb-xs">
            <div class="col-12">
              <q-badge :color="detailRow.service_affected ? 'negative' : 'positive'" outline>
                {{ detailRow.service_affected ? '서비스 영향 있음' : '서비스 영향 없음' }}
              </q-badge>
            </div>
            <div v-if="detailRow.actual_downtime" class="col-6">
              <div class="text-caption text-grey-7">실제 중단 시간</div>
              <div>{{ detailRow.actual_downtime }}</div>
            </div>
          </div>

          <q-separator class="q-my-sm" />

          <!-- 작업 절차 결과 -->
          <div class="text-subtitle2 text-weight-bold q-mb-xs">세부 절차 결과</div>
          <q-list bordered separator dense>
            <q-item v-for="(step, i) in detailRow.step_results" :key="i">
              <q-item-section avatar>
                <q-avatar size="24px" color="grey-4" text-color="grey-9" font-size="12px">
                  {{ step.order }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ step.task }}</q-item-label>
                <q-item-label caption>담당: {{ step.person }}</q-item-label>
                <q-item-label v-if="step.notes" caption>비고: {{ step.notes }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="step.completed ? 'positive' : 'negative'" outline>
                  {{ step.completed ? '완료' : '미완료' }}
                </q-badge>
              </q-item-section>
            </q-item>
            <q-item v-if="!detailRow.step_results?.length">
              <q-item-section class="text-grey-6 text-caption">세부 절차 결과 없음</q-item-section>
            </q-item>
          </q-list>

          <q-separator class="q-my-sm" />

          <!-- 이슈 -->
          <div class="text-subtitle2 text-weight-bold q-mb-xs">이슈 및 특이 사항</div>
          <q-badge :color="detailRow.issues_occurred ? 'negative' : 'positive'" outline>
            {{ detailRow.issues_occurred ? '이슈 발생' : '이슈 없음' }}
          </q-badge>
          <template v-if="detailRow.issues_occurred">
            <div v-if="detailRow.issue_details" class="q-mt-xs">
              <div class="text-caption text-grey-7">이슈 내용</div>
              <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.issue_details }}</div>
            </div>
            <div v-if="detailRow.action_taken" class="q-mt-xs">
              <div class="text-caption text-grey-7">조치 내용</div>
              <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.action_taken }}</div>
            </div>
          </template>

          <q-separator class="q-my-sm" />

          <!-- 사후 확인 -->
          <div class="text-subtitle2 text-weight-bold q-mb-xs">사후 확인</div>
          <q-badge :color="detailRow.post_check_done ? 'positive' : 'warning'" outline>
            {{ detailRow.post_check_done ? '사후 확인 완료' : '사후 확인 미완료' }}
          </q-badge>
          <div v-if="detailRow.post_check_details" class="q-mt-xs text-body2">
            {{ detailRow.post_check_details }}
          </div>

          <template v-if="detailRow.notes">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">기타 특이 사항</div>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.notes }}</div>
          </template>

          <template v-if="detailRow.plan_id">
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey-6">참조 작업계획서 ID: {{ detailRow.plan_id }}</div>
          </template>

          <q-separator class="q-my-sm" />
          <div class="text-caption text-grey-6">
            생성: {{ detailRow.created_by }} / {{ formatKst(detailRow.created_at ?? '') }}
            <span v-if="detailRow.updated_at">
              &nbsp;|&nbsp; 수정: {{ detailRow.updated_by }} / {{ formatKst(detailRow.updated_at) }}
            </span>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive } from 'vue'
import { useQuasar, type QTableProps } from 'quasar'

import type {
  ServiceWorkResult,
  ServiceWorkResultCreate,
  JobCategory,
  JobOutcome,
  JobWorkStepResult,
} from 'src/types/job'

import {
  listServiceWorkResults,
  createServiceWorkResult,
  patchServiceWorkResult,
  deleteServiceWorkResult,
} from 'src/services/job'

import { getErrorMessage } from 'src/utils/http/error'
import { formatKst } from 'src/utils/time/kst'

const $q = useQuasar()

const loading = ref(false)
const rows = ref<ServiceWorkResult[]>([])
const includeDeleted = ref(false)
const filter = ref('')
const resultFilter = ref<string | null>(null)

const categoryOptions: JobCategory[] = ['정기', '긴급', '임시']
const resultOptions: JobOutcome[] = ['성공', '부분성공', '실패']

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  page: 1,
  rowsPerPage: 10,
  sortBy: 'work_date',
  descending: true,
})

function onPagination(p: NonNullable<QTableProps['pagination']>) {
  pagination.value = p
}

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'title', label: '작업명', field: 'title', align: 'left', sortable: true },
  { name: 'work_date', label: '작업 일시', field: 'work_date', align: 'left', sortable: true },
  { name: 'worker', label: '작업자', field: 'worker', align: 'left', sortable: true },
  { name: 'system_name', label: '시스템명', field: 'system_name', align: 'left', sortable: true },
  { name: 'category', label: '구분', field: 'category', align: 'center', sortable: true },
  { name: 'service_affected', label: '서비스 영향', field: 'service_affected', align: 'center', sortable: true },
  { name: 'result', label: '결과', field: 'result', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredRows = computed(() => {
  let result = rows.value
  if (resultFilter.value) {
    result = result.filter((r) => r.result === resultFilter.value)
  }
  const q = filter.value.trim().toLowerCase()
  if (!q) return result
  return result.filter((r) => {
    if (r.title.toLowerCase().includes(q)) return true
    if (r.worker.toLowerCase().includes(q)) return true
    if (r.system_name.toLowerCase().includes(q)) return true
    if (r.requester.toLowerCase().includes(q)) return true
    return false
  })
})

function resultColor(r: JobOutcome): string {
  const map: Record<JobOutcome, string> = {
    '성공': 'positive',
    '부분성공': 'orange',
    '실패': 'negative',
  }
  return map[r] ?? 'grey'
}

async function load() {
  loading.value = true
  try {
    rows.value = await listServiceWorkResults(includeDeleted.value)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

// ─── Form state ────────────────────────────────────────────────────────────
const formDialog = ref(false)
const isEdit = ref(false)
const selectedRow = ref<ServiceWorkResult | null>(null)
const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'edit' | 'delete' | null>(null)

function emptyForm(): ServiceWorkResultCreate & { version?: number } {
  return {
    title: '',
    work_date: '',
    worker: '',
    requester: '',
    system_name: '',
    category: '정기' as JobCategory,
    result: '성공' as JobOutcome,
    actual_start_time: null,
    actual_end_time: null,
    summary: '',
    service_affected: false,
    actual_downtime: null,
    step_results: [] as JobWorkStepResult[],
    issues_occurred: false,
    issue_details: null,
    action_taken: null,
    post_check_done: false,
    post_check_details: null,
    plan_id: null,
    notes: null,
  }
}

const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

function openCreate() {
  Object.assign(form, emptyForm())
  isEdit.value = false
  formDialog.value = true
}

function openEdit(row: ServiceWorkResult) {
  isEdit.value = true
  selectedRow.value = row
  Object.assign(form, {
    title: row.title,
    work_date: row.work_date,
    worker: row.worker,
    requester: row.requester,
    system_name: row.system_name,
    category: row.category,
    result: row.result,
    actual_start_time: row.actual_start_time ?? null,
    actual_end_time: row.actual_end_time ?? null,
    summary: row.summary,
    service_affected: row.service_affected,
    actual_downtime: row.actual_downtime ?? null,
    step_results: row.step_results.map((s) => ({ ...s })),
    issues_occurred: row.issues_occurred,
    issue_details: row.issue_details ?? null,
    action_taken: row.action_taken ?? null,
    post_check_done: row.post_check_done,
    post_check_details: row.post_check_details ?? null,
    plan_id: row.plan_id ?? null,
    notes: row.notes ?? null,
    version: row.version ?? undefined,
  })
  formDialog.value = true
}

function addStepResult() {
  form.step_results.push({
    order: form.step_results.length + 1,
    task: '',
    person: '',
    completed: true,
    notes: null,
  })
}

function removeStepResult(i: number) {
  form.step_results.splice(i, 1)
  form.step_results.forEach((s, idx) => { s.order = idx + 1 })
}

function validateForm(): boolean {
  const required = [
    form.title.trim(),
    form.work_date.trim(),
    form.worker.trim(),
    form.requester.trim(),
    form.system_name.trim(),
    form.summary.trim(),
  ]
  if (required.some((v) => !v)) {
    $q.notify({ type: 'warning', message: '필수 항목을 모두 입력해주세요.' })
    return false
  }
  for (const step of form.step_results) {
    if (!step.task.trim() || !step.person.trim()) {
      $q.notify({ type: 'warning', message: '세부 절차 결과의 세부 작업 내용과 담당자를 모두 입력해주세요.' })
      return false
    }
  }
  return true
}

async function doCreate() {
  if (!validateForm()) return
  actingType.value = 'create'
  try {
    const payload: ServiceWorkResultCreate = {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      result: form.result,
      actual_start_time: form.actual_start_time || null,
      actual_end_time: form.actual_end_time || null,
      summary: form.summary.trim(),
      service_affected: form.service_affected,
      actual_downtime: form.actual_downtime || null,
      step_results: form.step_results.map((s, i) => ({
        order: i + 1,
        task: s.task.trim(),
        person: s.person.trim(),
        completed: s.completed,
        notes: s.notes || null,
      } as JobWorkStepResult)),
      issues_occurred: form.issues_occurred,
      issue_details: form.issue_details || null,
      action_taken: form.action_taken || null,
      post_check_done: form.post_check_done,
      post_check_details: form.post_check_details || null,
      plan_id: form.plan_id || null,
      notes: form.notes || null,
    }
    const created = await createServiceWorkResult(payload)
    rows.value = [created, ...rows.value]
    formDialog.value = false
    $q.notify({ type: 'positive', message: '작업 결과서가 생성되었습니다.' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '생성 실패') })
  } finally {
    actingType.value = null
  }
}

async function doEdit() {
  if (!selectedRow.value || !validateForm()) return
  actingId.value = selectedRow.value.id
  actingType.value = 'edit'
  try {
    const updated = await patchServiceWorkResult(selectedRow.value.id, {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      result: form.result,
      actual_start_time: form.actual_start_time || null,
      actual_end_time: form.actual_end_time || null,
      summary: form.summary.trim(),
      service_affected: form.service_affected,
      actual_downtime: form.actual_downtime || null,
      step_results: form.step_results.map((s, i) => ({
        order: i + 1,
        task: s.task.trim(),
        person: s.person.trim(),
        completed: s.completed,
        notes: s.notes || null,
      } as JobWorkStepResult)),
      issues_occurred: form.issues_occurred,
      issue_details: form.issue_details || null,
      action_taken: form.action_taken || null,
      post_check_done: form.post_check_done,
      post_check_details: form.post_check_details || null,
      plan_id: form.plan_id || null,
      notes: form.notes || null,
      version: 'version' in form ? (form as { version?: number }).version : undefined,
    })
    rows.value = rows.value.map((r) =>
      r.id === selectedRow.value!.id ? updated : r
    )
    formDialog.value = false
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

function confirmDelete(row: ServiceWorkResult) {
  $q.dialog({
    title: '삭제',
    message: `정말 삭제하시겠습니까?\n${row.title}`,
    cancel: true,
    persistent: true,
  }).onOk(() => void doDelete(row))
}

async function doDelete(row: ServiceWorkResult) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    await deleteServiceWorkResult(row.id)
    rows.value = rows.value.map((r) =>
      r.id === row.id ? { ...r, is_deleted: true } : r
    )
    $q.notify({ type: 'info', message: '삭제됨(soft delete)' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '삭제 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

const detailDialog = ref(false)
const detailRow = ref<ServiceWorkResult | null>(null)

function openDetail(row: ServiceWorkResult) {
  detailRow.value = row
  detailDialog.value = true
}

onMounted(() => void load())
</script>
