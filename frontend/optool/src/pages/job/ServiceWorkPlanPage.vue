<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">작업계획서 (서비스)</div>
      <q-space />
      <q-toggle v-model="includeDeleted" label="삭제 포함" dense />
      <q-btn outline icon="refresh" label="새로고침" :loading="loading" @click="load" />
      <q-btn color="primary" icon="add" label="작업계획서 추가" @click="openCreate" />
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
          v-model="statusFilter"
          :options="statusOptions"
          dense
          outlined
          clearable
          label="상태 필터"
          style="min-width: 120px"
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
          <!-- 상태 badge -->
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row.status)" outline>
                {{ props.row.status }}
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
      <q-card style="width: 800px; max-width: 95vw; max-height: 90vh" class="column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ isEdit ? '작업계획서 수정' : '작업계획서 추가' }}</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="col scroll">
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

          <!-- 작업 내용 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">작업 내용</div>
          <q-input
            v-model="form.purpose"
            outlined
            dense
            type="textarea"
            autogrow
            label="작업 목적 *"
            class="q-mb-sm"
          />
          <q-input
            v-model="form.scope"
            outlined
            dense
            type="textarea"
            autogrow
            label="작업 범위 *"
            class="q-mb-sm"
          />
          <q-input
            v-model="form.detail"
            outlined
            dense
            type="textarea"
            autogrow
            label="작업 상세 내용 *"
          />

          <q-separator class="q-my-md" />

          <!-- 영향도 분석 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">영향도 분석</div>
          <q-toggle v-model="form.service_affected" label="서비스 영향 여부" class="q-mb-sm" />
          <div class="row q-gutter-sm">
            <q-input
              v-model="form.downtime"
              outlined
              dense
              label="서비스 중단 시간"
              class="col-12 col-sm-5"
            />
            <q-input
              v-model="form.impact_scope"
              outlined
              dense
              label="영향 범위"
              class="col-12 col-sm-6"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- 사전 준비 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">사전 준비</div>
          <q-toggle v-model="form.backup_done" label="백업 완료" class="q-mb-sm" />
          <q-input
            v-model="form.backup_details"
            outlined
            dense
            type="textarea"
            autogrow
            label="백업 내용"
          />

          <q-separator class="q-my-md" />

          <!-- 작업 절차 -->
          <div class="row items-center q-mb-xs">
            <div class="text-subtitle1 text-weight-bold">세부 절차</div>
            <q-space />
            <q-btn flat dense icon="add" label="단계 추가" @click="addStep" />
          </div>
          <q-list bordered separator>
            <q-item v-for="(step, i) in form.steps" :key="i">
              <q-item-section>
                <div class="row items-center q-mb-xs">
                  <div class="col text-caption text-grey-7 text-weight-medium">세부 절차 {{ i + 1 }}</div>
                  <q-btn flat dense icon="delete" color="negative" @click="removeStep(i)" />
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
                  <q-input
                    v-model="step.duration"
                    outlined
                    dense
                    label="소요 시간"
                    style="width: 100px"
                  />
                </div>
              </q-item-section>
            </q-item>
            <q-item v-if="form.steps.length === 0">
              <q-item-section class="text-grey-6 text-caption q-pa-sm">
                세부 절차가 없습니다. 단계를 추가하세요.
              </q-item-section>
            </q-item>
          </q-list>

          <q-separator class="q-my-md" />

          <!-- 롤백 계획 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">롤백 계획</div>
          <q-toggle v-model="form.rollback_possible" label="롤백 가능" class="q-mb-sm" />
          <div class="row q-gutter-sm">
            <q-input
              v-model="form.rollback_steps"
              outlined
              dense
              type="textarea"
              autogrow
              label="롤백 절차"
              class="col-12 col-sm-7"
            />
            <q-input
              v-model="form.rollback_duration"
              outlined
              dense
              label="롤백 소요 시간"
              class="col-12 col-sm-4"
            />
          </div>

          <!-- Status (edit only) -->
          <template v-if="isEdit">
            <q-separator class="q-my-md" />
            <div class="text-subtitle1 text-weight-bold q-mb-xs">상태</div>
            <div class="row q-gutter-sm">
              <q-select
                v-model="form.status"
                :options="statusOptions"
                outlined
                dense
                label="작업 상태"
                class="col-12 col-sm-5"
              />
              <q-input
                v-model="form.result_notes"
                outlined
                dense
                type="textarea"
                autogrow
                label="작업 결과 특이 사항"
                class="col-12 col-sm-6"
              />
            </div>
          </template>
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
      <q-card v-if="detailRow" style="width: 700px; max-width: 95vw; max-height: 90vh" class="column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">작업계획서 상세</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="col scroll">
          <div class="row q-gutter-x-md q-mb-sm">
            <div class="col">
              <div class="text-caption text-grey-7">작업명</div>
              <div class="text-body1 text-weight-medium">{{ detailRow.title }}</div>
            </div>
            <div class="col-auto">
              <q-badge :color="statusColor(detailRow.status)" outline>
                {{ detailRow.status }}
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
          <div class="text-subtitle2 text-weight-bold q-mb-xs">작업 내용</div>
          <div class="q-mb-xs">
            <span class="text-caption text-grey-7">목적: </span>{{ detailRow.purpose }}
          </div>
          <div class="q-mb-xs">
            <span class="text-caption text-grey-7">범위: </span>{{ detailRow.scope }}
          </div>
          <div>
            <span class="text-caption text-grey-7">상세: </span>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.detail }}</div>
          </div>

          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 text-weight-bold q-mb-xs">영향도 분석</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12">
              <q-badge :color="detailRow.service_affected ? 'negative' : 'positive'" outline>
                {{ detailRow.service_affected ? '서비스 영향 있음' : '서비스 영향 없음' }}
              </q-badge>
            </div>
            <div v-if="detailRow.downtime" class="col-6">
              <div class="text-caption text-grey-7">중단 시간</div>
              <div>{{ detailRow.downtime }}</div>
            </div>
            <div v-if="detailRow.impact_scope" class="col-6">
              <div class="text-caption text-grey-7">영향 범위</div>
              <div>{{ detailRow.impact_scope }}</div>
            </div>
          </div>

          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 text-weight-bold q-mb-xs">사전 준비</div>
          <q-badge :color="detailRow.backup_done ? 'positive' : 'warning'" outline>
            {{ detailRow.backup_done ? '백업 완료' : '백업 미완료' }}
          </q-badge>
          <div v-if="detailRow.backup_details" class="q-mt-xs text-body2">
            {{ detailRow.backup_details }}
          </div>

          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 text-weight-bold q-mb-xs">세부 절차</div>
          <q-list bordered separator dense>
            <q-item v-for="(step, i) in detailRow.steps" :key="i">
              <q-item-section avatar>
                <q-avatar size="24px" color="grey-4" text-color="grey-9" font-size="12px">
                  {{ step.order }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ step.task }}</q-item-label>
                <q-item-label caption>
                  담당: {{ step.person }}
                  <span v-if="step.duration"> / {{ step.duration }}</span>
                </q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!detailRow.steps?.length">
              <q-item-section class="text-grey-6 text-caption">세부 절차 없음</q-item-section>
            </q-item>
          </q-list>

          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 text-weight-bold q-mb-xs">롤백 계획</div>
          <q-badge :color="detailRow.rollback_possible ? 'positive' : 'negative'" outline>
            {{ detailRow.rollback_possible ? '롤백 가능' : '롤백 불가' }}
          </q-badge>
          <div v-if="detailRow.rollback_steps" class="q-mt-xs text-body2">
            {{ detailRow.rollback_steps }}
          </div>
          <div v-if="detailRow.rollback_duration" class="text-caption text-grey-7">
            소요 시간: {{ detailRow.rollback_duration }}
          </div>

          <template v-if="detailRow.result_notes">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">작업 결과</div>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.result_notes }}</div>
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
  ServiceWorkPlan,
  ServiceWorkPlanCreate,
  JobCategory,
  JobStatus,
  JobWorkStep,
} from 'src/types/job'

import {
  listServiceWorkPlans,
  createServiceWorkPlan,
  patchServiceWorkPlan,
  deleteServiceWorkPlan,
} from 'src/services/job'

import { getErrorMessage } from 'src/utils/http/error'
import { formatKst } from 'src/utils/time/kst'

const $q = useQuasar()

const loading = ref(false)
const rows = ref<ServiceWorkPlan[]>([])
const includeDeleted = ref(false)
const filter = ref('')
const statusFilter = ref<string | null>(null)

const categoryOptions: JobCategory[] = ['정기', '긴급', '임시']
const statusOptions: JobStatus[] = ['초안', '승인대기', '승인됨', '완료', '취소']

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
  { name: 'status', label: '상태', field: 'status', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredRows = computed(() => {
  let result = rows.value
  if (statusFilter.value) {
    result = result.filter((r) => r.status === statusFilter.value)
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

function statusColor(s: JobStatus): string {
  const map: Record<JobStatus, string> = {
    '초안': 'grey',
    '승인대기': 'orange',
    '승인됨': 'blue',
    '완료': 'positive',
    '취소': 'negative',
  }
  return map[s] ?? 'grey'
}

async function load() {
  loading.value = true
  try {
    rows.value = await listServiceWorkPlans(includeDeleted.value)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

// ─── Form state ────────────────────────────────────────────────────────────
const formDialog = ref(false)
const isEdit = ref(false)
const selectedRow = ref<ServiceWorkPlan | null>(null)
const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'edit' | 'delete' | null>(null)

function emptyForm(): ServiceWorkPlanCreate & { status: JobStatus; result_notes: string | null; version?: number } {
  return {
    title: '',
    work_date: '',
    worker: '',
    requester: '',
    system_name: '',
    category: '정기',
    purpose: '',
    scope: '',
    detail: '',
    service_affected: false,
    downtime: null,
    impact_scope: null,
    backup_done: false,
    backup_details: null,
    steps: [],
    rollback_possible: true,
    rollback_steps: null,
    rollback_duration: null,
    result_notes: null,
    status: '초안',
  }
}

const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

function openCreate() {
  Object.assign(form, emptyForm())
  isEdit.value = false
  formDialog.value = true
}

function openEdit(row: ServiceWorkPlan) {
  isEdit.value = true
  selectedRow.value = row
  Object.assign(form, {
    title: row.title,
    work_date: row.work_date,
    worker: row.worker,
    requester: row.requester,
    system_name: row.system_name,
    category: row.category,
    purpose: row.purpose,
    scope: row.scope,
    detail: row.detail,
    service_affected: row.service_affected,
    downtime: row.downtime ?? null,
    impact_scope: row.impact_scope ?? null,
    backup_done: row.backup_done,
    backup_details: row.backup_details ?? null,
    steps: row.steps.map((s) => ({ ...s })),
    rollback_possible: row.rollback_possible,
    rollback_steps: row.rollback_steps ?? null,
    rollback_duration: row.rollback_duration ?? null,
    status: row.status,
    result_notes: row.result_notes ?? null,
    version: row.version ?? undefined,
  })
  formDialog.value = true
}

// Step management
function addStep() {
  form.steps.push({ order: form.steps.length + 1, task: '', person: '', duration: null })
}

function removeStep(i: number) {
  form.steps.splice(i, 1)
  form.steps.forEach((s, idx) => { s.order = idx + 1 })
}

function validateForm(): boolean {
  const required = [
    form.title.trim(),
    form.work_date.trim(),
    form.worker.trim(),
    form.requester.trim(),
    form.system_name.trim(),
    form.purpose.trim(),
    form.scope.trim(),
    form.detail.trim(),
  ]
  if (required.some((v) => !v)) {
    $q.notify({ type: 'warning', message: '필수 항목을 모두 입력해주세요.' })
    return false
  }
  for (const step of form.steps) {
    if (!step.task.trim() || !step.person.trim()) {
      $q.notify({ type: 'warning', message: '세부 절차의 세부 작업 내용과 담당자를 모두 입력해주세요.' })
      return false
    }
  }
  return true
}

async function doCreate() {
  if (!validateForm()) return
  actingType.value = 'create'
  try {
    const payload: ServiceWorkPlanCreate = {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      purpose: form.purpose.trim(),
      scope: form.scope.trim(),
      detail: form.detail.trim(),
      service_affected: form.service_affected,
      downtime: form.downtime || null,
      impact_scope: form.impact_scope || null,
      backup_done: form.backup_done,
      backup_details: form.backup_details || null,
      steps: form.steps.map((s, i) => ({
        order: i + 1,
        task: s.task.trim(),
        person: s.person.trim(),
        duration: s.duration || null,
      } as JobWorkStep)),
      rollback_possible: form.rollback_possible,
      rollback_steps: form.rollback_steps || null,
      rollback_duration: form.rollback_duration || null,
      result_notes: form.result_notes || null,
    }
    const created = await createServiceWorkPlan(payload)
    rows.value = [created, ...rows.value]
    formDialog.value = false
    $q.notify({ type: 'positive', message: '작업계획서가 생성되었습니다.' })
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
    const updated = await patchServiceWorkPlan(selectedRow.value.id, {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      purpose: form.purpose.trim(),
      scope: form.scope.trim(),
      detail: form.detail.trim(),
      service_affected: form.service_affected,
      downtime: form.downtime || null,
      impact_scope: form.impact_scope || null,
      backup_done: form.backup_done,
      backup_details: form.backup_details || null,
      steps: form.steps.map((s, i) => ({
        order: i + 1,
        task: s.task.trim(),
        person: s.person.trim(),
        duration: s.duration || null,
      } as JobWorkStep)),
      rollback_possible: form.rollback_possible,
      rollback_steps: form.rollback_steps || null,
      rollback_duration: form.rollback_duration || null,
      status: form.status,
      result_notes: form.result_notes || null,
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

/** Delete */
function confirmDelete(row: ServiceWorkPlan) {
  $q.dialog({
    title: '삭제',
    message: `정말 삭제하시겠습니까?\n${row.title}`,
    cancel: true,
    persistent: true,
  }).onOk(() => void doDelete(row))
}

async function doDelete(row: ServiceWorkPlan) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    await deleteServiceWorkPlan(row.id)
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

/** Detail */
const detailDialog = ref(false)
const detailRow = ref<ServiceWorkPlan | null>(null)

function openDetail(row: ServiceWorkPlan) {
  detailRow.value = row
  detailDialog.value = true
}

onMounted(() => void load())
</script>
