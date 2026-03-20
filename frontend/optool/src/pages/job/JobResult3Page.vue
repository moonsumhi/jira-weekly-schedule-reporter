<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">작업결과서3</div>
      <q-space />
      <q-toggle v-model="includeDeleted" label="삭제 포함" dense />
      <q-btn outline icon="refresh" label="새로고침" :loading="loading" @click="load" />
      <q-btn color="primary" icon="add" label="결과서 추가" @click="openCreate" />
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
          placeholder="제목 / 작업자 / 시스템명 검색"
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
        <q-select
          v-model="outcomeFilter"
          :options="outcomeOptions"
          dense
          outlined
          clearable
          label="결과 필터"
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

          <!-- 결과 badge -->
          <template #body-cell-outcome="props">
            <q-td :props="props">
              <q-badge :color="outcomeColor(props.row.outcome)" outline>
                {{ props.row.outcome }}
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
          <div class="text-h6">{{ isEdit ? '작업결과서3 수정' : '작업결과서3 추가' }}</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="col scroll">
          <!-- 첨부파일 인식 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">첨부파일 인식</div>
          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-file
              v-model="attachmentFile"
              outlined
              dense
              label="파일 선택 (HWP / txt / md)"
              accept=".hwp,.txt,.md"
              class="col"
              clearable
            >
              <template #prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>
            <q-btn
              color="secondary"
              icon="search"
              label="텍스트 추출"
              :loading="extracting"
              :disable="!attachmentFile"
              @click="doExtract"
            />
          </div>
          <div v-if="extractedFilename" class="text-caption text-grey-7 q-mb-sm">
            추출 완료: {{ extractedFilename }}
          </div>

          <q-separator class="q-my-md" />

          <!-- 기본 정보 -->
          <div class="text-subtitle1 text-weight-bold q-mt-sm q-mb-xs">기본 정보</div>
          <div class="row q-gutter-sm">
            <q-input
              v-model="form.title"
              outlined
              dense
              label="결과서 제목 *"
              class="col-12"
            />
            <q-input
              v-model="form.work_date"
              outlined
              dense
              label="작업 일시 * (YYYY-MM-DD HH:MM)"
              mask="####-##-## ##:##"
              class="col-12 col-sm-6"
            />
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
          <div class="row q-gutter-sm q-mt-xs">
            <q-input
              v-model="form.related_plan_id"
              outlined
              dense
              label="관련 작업계획서 ID (선택)"
              class="col-12"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- 작업 결과 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">작업 결과</div>
          <div class="row q-gutter-sm q-mb-sm">
            <q-select
              v-model="form.outcome"
              :options="outcomeOptions"
              outlined
              dense
              label="결과 *"
              class="col-12 col-sm-5"
            />
          </div>
          <q-input
            v-model="form.work_summary"
            outlined
            dense
            type="textarea"
            autogrow
            label="수행 작업 요약 *"
            class="q-mb-sm"
          />
          <q-input
            v-model="form.service_impact_actual"
            outlined
            dense
            type="textarea"
            autogrow
            label="실제 서비스 영향"
            class="q-mb-sm"
          />

          <q-separator class="q-my-md" />

          <!-- 문제 및 조치 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">발생 문제 및 조치</div>
          <q-input
            v-model="form.issues_found"
            outlined
            dense
            type="textarea"
            autogrow
            label="발생 문제"
            class="q-mb-sm"
          />
          <q-input
            v-model="form.resolution"
            outlined
            dense
            type="textarea"
            autogrow
            label="조치 내용"
          />

          <q-separator class="q-my-md" />

          <!-- 후속 조치 -->
          <div class="text-subtitle1 text-weight-bold q-mb-xs">후속 조치</div>
          <q-input
            v-model="form.next_steps"
            outlined
            dense
            type="textarea"
            autogrow
            label="후속 조치 사항"
          />

          <!-- Status (edit only) -->
          <template v-if="isEdit">
            <q-separator class="q-my-md" />
            <div class="text-subtitle1 text-weight-bold q-mb-xs">상태</div>
            <q-select
              v-model="form.status"
              :options="statusOptions"
              outlined
              dense
              label="작업 상태"
              class="col-12 col-sm-5"
            />
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
          <div class="text-h6">작업결과서3 상세</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section class="col scroll">
          <div class="row q-gutter-x-md q-mb-sm">
            <div class="col">
              <div class="text-caption text-grey-7">결과서 제목</div>
              <div class="text-body1 text-weight-medium">{{ detailRow.title }}</div>
            </div>
            <div class="col-auto column q-gutter-xs">
              <q-badge :color="statusColor(detailRow.status)" outline>
                {{ detailRow.status }}
              </q-badge>
              <q-badge :color="outcomeColor(detailRow.outcome)" outline>
                {{ detailRow.outcome }}
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
            <div v-if="detailRow.related_plan_id" class="col-12">
              <div class="text-caption text-grey-7">관련 작업계획서 ID</div>
              <div>{{ detailRow.related_plan_id }}</div>
            </div>
          </div>

          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 text-weight-bold q-mb-xs">수행 작업 요약</div>
          <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.work_summary }}</div>

          <template v-if="detailRow.service_impact_actual">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">실제 서비스 영향</div>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.service_impact_actual }}</div>
          </template>

          <template v-if="detailRow.issues_found || detailRow.resolution">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">발생 문제 및 조치</div>
            <div v-if="detailRow.issues_found" class="q-mb-xs">
              <span class="text-caption text-grey-7">발생 문제: </span>
              <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.issues_found }}</div>
            </div>
            <div v-if="detailRow.resolution">
              <span class="text-caption text-grey-7">조치 내용: </span>
              <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.resolution }}</div>
            </div>
          </template>

          <template v-if="detailRow.next_steps">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">후속 조치</div>
            <div class="text-body2" style="white-space: pre-wrap">{{ detailRow.next_steps }}</div>
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
  JobResult,
  JobResultCreate,
  JobCategory,
  JobStatus,
  JobOutcome,
} from 'src/types/job'

import {
  listJobResults,
  createJobResult,
  patchJobResult,
  deleteJobResult,
  extractAttachmentText,
} from 'src/services/job'

import { getErrorMessage } from 'src/utils/http/error'
import { formatKst } from 'src/utils/time/kst'

const $q = useQuasar()

const loading = ref(false)
const rows = ref<JobResult[]>([])
const includeDeleted = ref(false)
const filter = ref('')
const statusFilter = ref<string | null>(null)
const outcomeFilter = ref<string | null>(null)

const categoryOptions: JobCategory[] = ['정기', '긴급', '임시']
const statusOptions: JobStatus[] = ['초안', '승인대기', '승인됨', '완료', '취소']
const outcomeOptions: JobOutcome[] = ['성공', '부분성공', '실패']

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
  { name: 'title', label: '결과서 제목', field: 'title', align: 'left', sortable: true },
  { name: 'work_date', label: '작업 일시', field: 'work_date', align: 'left', sortable: true },
  { name: 'worker', label: '작업자', field: 'worker', align: 'left', sortable: true },
  { name: 'system_name', label: '시스템명', field: 'system_name', align: 'left', sortable: true },
  { name: 'category', label: '구분', field: 'category', align: 'center', sortable: true },
  { name: 'outcome', label: '결과', field: 'outcome', align: 'center', sortable: true },
  { name: 'status', label: '상태', field: 'status', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredRows = computed(() => {
  let result = rows.value
  if (statusFilter.value) {
    result = result.filter((r) => r.status === statusFilter.value)
  }
  if (outcomeFilter.value) {
    result = result.filter((r) => r.outcome === outcomeFilter.value)
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

function outcomeColor(o: JobOutcome): string {
  const map: Record<JobOutcome, string> = {
    '성공': 'positive',
    '부분성공': 'orange',
    '실패': 'negative',
  }
  return map[o] ?? 'grey'
}

async function load() {
  loading.value = true
  try {
    rows.value = await listJobResults(includeDeleted.value)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

// ─── Attachment extraction ──────────────────────────────────────────────────
const attachmentFile = ref<File | null>(null)
const extracting = ref(false)
const extractedFilename = ref('')

async function doExtract() {
  if (!attachmentFile.value) return
  extracting.value = true
  try {
    const result = await extractAttachmentText(attachmentFile.value)
    extractedFilename.value = result.filename
    if (result.text) {
      form.work_summary = result.text
      $q.notify({ type: 'positive', message: `첨부파일 텍스트를 '수행 작업 요약'에 적용했습니다.` })
    } else {
      $q.notify({ type: 'warning', message: '텍스트를 추출할 수 없었습니다.' })
    }
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '텍스트 추출 실패') })
  } finally {
    extracting.value = false
  }
}

// ─── Form state ────────────────────────────────────────────────────────────
const formDialog = ref(false)
const isEdit = ref(false)
const selectedRow = ref<JobResult | null>(null)
const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'edit' | 'delete' | null>(null)

function emptyForm(): JobResultCreate & { status: JobStatus; version?: number } {
  return {
    title: '',
    work_date: '',
    worker: '',
    requester: '',
    system_name: '',
    category: '정기',
    work_summary: '',
    issues_found: null,
    resolution: null,
    service_impact_actual: null,
    outcome: '성공',
    next_steps: null,
    related_plan_id: null,
    status: '초안',
  }
}

const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

function openCreate() {
  Object.assign(form, emptyForm())
  attachmentFile.value = null
  extractedFilename.value = ''
  isEdit.value = false
  formDialog.value = true
}

function openEdit(row: JobResult) {
  isEdit.value = true
  selectedRow.value = row
  attachmentFile.value = null
  extractedFilename.value = ''
  Object.assign(form, {
    title: row.title,
    work_date: row.work_date,
    worker: row.worker,
    requester: row.requester,
    system_name: row.system_name,
    category: row.category,
    work_summary: row.work_summary,
    issues_found: row.issues_found ?? null,
    resolution: row.resolution ?? null,
    service_impact_actual: row.service_impact_actual ?? null,
    outcome: row.outcome,
    next_steps: row.next_steps ?? null,
    related_plan_id: row.related_plan_id ?? null,
    status: row.status,
    version: row.version ?? undefined,
  })
  formDialog.value = true
}

function validateForm(): boolean {
  const required = [
    form.title.trim(),
    form.work_date.trim(),
    form.worker.trim(),
    form.requester.trim(),
    form.system_name.trim(),
    form.work_summary.trim(),
  ]
  if (required.some((v) => !v)) {
    $q.notify({ type: 'warning', message: '필수 항목을 모두 입력해주세요.' })
    return false
  }
  return true
}

async function doCreate() {
  if (!validateForm()) return
  actingType.value = 'create'
  try {
    const payload: JobResultCreate = {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      work_summary: form.work_summary.trim(),
      issues_found: form.issues_found || null,
      resolution: form.resolution || null,
      service_impact_actual: form.service_impact_actual || null,
      outcome: form.outcome,
      next_steps: form.next_steps || null,
      related_plan_id: form.related_plan_id || null,
    }
    const created = await createJobResult(payload)
    rows.value = [created, ...rows.value]
    formDialog.value = false
    $q.notify({ type: 'positive', message: '작업결과서3이 생성되었습니다.' })
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
    const updated = await patchJobResult(selectedRow.value.id, {
      title: form.title.trim(),
      work_date: form.work_date.trim(),
      worker: form.worker.trim(),
      requester: form.requester.trim(),
      system_name: form.system_name.trim(),
      category: form.category,
      work_summary: form.work_summary.trim(),
      issues_found: form.issues_found || null,
      resolution: form.resolution || null,
      service_impact_actual: form.service_impact_actual || null,
      outcome: form.outcome,
      next_steps: form.next_steps || null,
      related_plan_id: form.related_plan_id || null,
      status: form.status,
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

function confirmDelete(row: JobResult) {
  $q.dialog({
    title: '삭제',
    message: `정말 삭제하시겠습니까?\n${row.title}`,
    cancel: true,
    persistent: true,
  }).onOk(() => void doDelete(row))
}

async function doDelete(row: JobResult) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    await deleteJobResult(row.id)
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
const detailRow = ref<JobResult | null>(null)

function openDetail(row: JobResult) {
  detailRow.value = row
  detailDialog.value = true
}

onMounted(() => void load())
</script>
