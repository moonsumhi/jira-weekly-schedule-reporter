<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-md q-gutter-sm">
      <div>
        <div class="text-h5 text-weight-bold">주간 보고</div>
        <div class="text-caption text-grey-6">스케줄 관리 › 주간 보고</div>
      </div>
      <q-space />
      <HelpButton feature="weekly-report" guide-path="/pm/schedule/guide" />
      <q-btn flat icon="download" label="목록 Excel" color="positive" no-caps @click="downloadList" />
      <q-btn color="primary" icon="add" label="새 보고서 생성" no-caps @click="openCreate" />
    </div>

    <!-- 필터 -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section class="q-py-sm">
        <div class="row q-col-gutter-sm items-center">
          <div class="col-auto">
            <q-select v-model="filter.year" :options="yearOptions" label="연도" dense outlined
              emit-value map-options clearable style="min-width:100px" @update:model-value="load" />
          </div>
          <div class="col-auto">
            <q-input v-model.number="filter.week" label="주차" type="number" dense outlined clearable
              style="min-width:80px" @update:model-value="load" />
          </div>
          <div class="col-auto">
            <q-btn flat dense icon="refresh" @click="load" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- 목록 -->
    <q-card flat bordered>
      <q-table :rows="reports" :columns="columns" row-key="id" flat :loading="loading"
        no-data-label="보고서가 없습니다." :pagination="{ rowsPerPage: 15 }">
        <template #body-cell-period="props">
          <q-td :props="props" class="text-caption text-grey-7">
            {{ props.row.startDate?.slice(0,10) }} ~ {{ props.row.endDate?.slice(0,10) }}
          </q-td>
        </template>
        <template #body-cell-stats="props">
          <q-td :props="props">
            <div class="row q-gutter-xs no-wrap">
              <q-badge color="grey-6"   :label="`전체 ${props.row.stats.total}`" />
              <q-badge color="positive" :label="`완료 ${props.row.stats.completed}`" />
              <q-badge color="primary"  :label="`진행 ${props.row.stats.inProgress}`" />
              <q-badge v-if="props.row.stats.delayed" color="negative" :label="`지연 ${props.row.stats.delayed}`" />
            </div>
          </q-td>
        </template>
        <template #body-cell-rate="props">
          <q-td :props="props">
            <div class="row items-center q-gutter-xs">
              <q-linear-progress :value="props.row.stats.completionRate / 100"
                color="positive" track-color="grey-3" style="width:60px;height:6px;border-radius:4px" />
              <span class="text-caption text-weight-bold">{{ props.row.stats.completionRate }}%</span>
            </div>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-badge :color="REPORT_STATUS_COLOR[props.row.status] ?? 'grey'" :label="REPORT_STATUS_KO[props.row.status] ?? props.row.status" />
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" class="q-gutter-xs">
            <q-btn flat dense icon="open_in_new" size="sm" color="primary" title="상세 보기" @click="openDetail(props.row)" />
            <q-btn flat dense icon="edit" size="sm" color="grey-7" @click="openEdit(props.row)" />
            <q-btn flat dense icon="refresh" size="sm" color="teal" title="이슈 재집계"
              :loading="refreshingId === props.row.id" @click="doRefresh(props.row)" />
            <q-btn flat dense icon="download" size="sm" color="positive" @click="downloadDetail(props.row.id)" />
            <q-btn flat dense icon="delete" size="sm" color="negative" @click="confirmDelete(props.row)" />
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- 생성 다이얼로그 -->
    <q-dialog v-model="createDialog.open" persistent>
      <q-card style="width:480px; max-width:96vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">주간 보고 생성</div>
          <q-space /><q-btn flat round dense icon="close" @click="createDialog.open = false" />
        </q-card-section>
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-gutter-sm">
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input v-model.number="createForm.report_year" label="연도 *" type="number" outlined dense
                @update:model-value="createForm.title = defaultTitle(createForm.report_year, createForm.report_week)" />
            </div>
            <div class="col-6">
              <q-input v-model.number="createForm.report_week" label="주차 *" type="number" outlined dense
                @update:model-value="createForm.title = defaultTitle(createForm.report_year, createForm.report_week)" />
            </div>
            <div class="col-12">
              <div class="text-caption text-grey-6">기간: {{ createDateRange }}</div>
            </div>
            <div class="col-12">
              <q-input v-model="createForm.title" label="제목 *" outlined dense />
            </div>
            <div class="col-12">
              <q-input v-model="createForm.department" label="부서" outlined dense />
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="createDialog.open = false" />
          <q-btn color="primary" label="생성 (자동 집계)" :loading="createDialog.loading" no-caps @click="submitCreate" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 수정 다이얼로그 -->
    <q-dialog v-model="editDialog.open" persistent>
      <q-card style="width:480px; max-width:96vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">보고서 수정</div>
          <q-space /><q-btn flat round dense icon="close" @click="editDialog.open = false" />
        </q-card-section>
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="editForm.title" label="제목" outlined dense />
          <q-input v-model="editForm.department" label="부서" outlined dense />
          <q-input v-model="editForm.admin_comment" label="관리자 코멘트" outlined dense
            type="textarea" :rows="4"
            hint="이슈 집계 외에 관리자가 추가할 내용을 입력하세요." />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="editDialog.open = false" />
          <q-btn color="primary" label="저장" :loading="editDialog.loading" no-caps @click="submitEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Notify, Dialog } from 'quasar'
import { api } from 'boot/axios'
import {
  listWeeklyReports, createWeeklyReport, updateWeeklyReport,
  deleteWeeklyReport, refreshWeeklyReport,
  type WeeklyReport, type WeeklyReportCreate,
} from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const router = useRouter()

// ── 보고서 상태 ────────────────────────────────────────────────────────
const REPORT_STATUS_KO: Record<string, string> = { DRAFT: '초안', REVIEWING: '검토중', CONFIRMED: '확정' }
const REPORT_STATUS_COLOR: Record<string, string> = { DRAFT: 'grey-6', REVIEWING: 'orange', CONFIRMED: 'positive' }

// ── 상태 ──────────────────────────────────────────────────────────────
const now = new Date()
const reports = ref<WeeklyReport[]>([])
const loading = ref(false)
const refreshingId = ref<string | null>(null)

const filter = ref<{ year: number | null; week: number | null }>({
  year: now.getFullYear(), week: null,
})

const yearOptions = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)
  .map(y => ({ label: `${y}년`, value: y }))

// ── 테이블 컬럼 ───────────────────────────────────────────────────────
const columns = [
  { name: 'week',    label: '주차',      field: (r: WeeklyReport) => `${r.reportYear}년 ${r.reportWeek}주차`, align: 'left'   as const, sortable: true },
  { name: 'period',  label: '기간',      field: 'startDate',  align: 'left'   as const },
  { name: 'title',   label: '제목',      field: 'title',      align: 'left'   as const, sortable: true },
  { name: 'status',  label: '상태',      field: 'status',     align: 'center' as const },
  { name: 'stats',   label: '업무 현황', field: 'stats',      align: 'left'   as const },
  { name: 'rate',    label: '완료율',    field: (r: WeeklyReport) => r.stats.completionRate, align: 'left' as const, sortable: true },
  { name: 'createdByName', label: '작성자', field: 'createdByName', align: 'left' as const },
  { name: 'actions', label: '',          field: 'id',         align: 'center' as const },
]

// ── 주차 → 날짜 범위 계산 (ISO 8601) ─────────────────────────────────
function weekToDateRange(year: number, week: number): { start: string; end: string } {
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const jan4 = new Date(year, 0, 4)
  const dayOfWeek = jan4.getDay() || 7
  const week1Mon = new Date(jan4)
  week1Mon.setDate(jan4.getDate() - (dayOfWeek - 1))
  const monday = new Date(week1Mon)
  monday.setDate(week1Mon.getDate() + (week - 1) * 7)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { start: fmt(monday), end: fmt(sunday) }
}

function getCurrentWeekInfo() {
  const d = new Date()
  const day = d.getDay() || 7
  d.setDate(d.getDate() + 4 - day)
  const yearStart = new Date(d.getFullYear(), 0, 1)
  const weekNum = Math.ceil(((d.valueOf() - yearStart.valueOf()) / 86400000 + 1) / 7)
  const { start, end } = weekToDateRange(d.getFullYear(), weekNum)
  return { year: d.getFullYear(), week: weekNum, start, end }
}

function defaultTitle(year: number, week: number) {
  return `${year}년 ${week}주차 주간 보고`
}

// ── 생성 ──────────────────────────────────────────────────────────────
const createDialog = ref({ open: false, loading: false })
const createForm = ref({ report_year: now.getFullYear(), report_week: 1, title: '', department: '' })

const createDateRange = computed(() => {
  const { start, end } = weekToDateRange(createForm.value.report_year, createForm.value.report_week)
  return `${start} ~ ${end}`
})

function openCreate() {
  const { year, week } = getCurrentWeekInfo()
  createForm.value = { report_year: year, report_week: week, title: defaultTitle(year, week), department: '' }
  createDialog.value = { open: true, loading: false }
}

async function submitCreate() {
  if (!createForm.value.title) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }
  createDialog.value.loading = true
  const { start, end } = weekToDateRange(createForm.value.report_year, createForm.value.report_week)
  const payload: WeeklyReportCreate = {
    report_year: createForm.value.report_year,
    report_week: createForm.value.report_week,
    start_date: start,
    end_date: end,
    title: createForm.value.title,
    ...(createForm.value.department ? { department: createForm.value.department } : {}),
  }
  try {
    await createWeeklyReport(payload)
    Notify.create({ type: 'positive', message: '보고서가 생성되었습니다.' })
    createDialog.value.open = false
    await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '생성 실패') })
  } finally {
    createDialog.value.loading = false
  }
}

// ── 수정 ──────────────────────────────────────────────────────────────
const editDialog = ref({ open: false, loading: false, editId: '' })
const editForm = ref({ title: '', department: '', admin_comment: '' })

function openEdit(r: WeeklyReport) {
  editForm.value = {
    title: r.title, department: r.department ?? '',
    admin_comment: r.adminComment ?? '',
  }
  editDialog.value = { open: true, loading: false, editId: r.id }
}

async function submitEdit() {
  editDialog.value.loading = true
  try {
    await updateWeeklyReport(editDialog.value.editId, {
      title: editForm.value.title,
      ...(editForm.value.department    ? { department:    editForm.value.department    } : {}),
      ...(editForm.value.admin_comment ? { admin_comment: editForm.value.admin_comment } : {}),
    })
    Notify.create({ type: 'positive', message: '저장되었습니다.' })
    editDialog.value.open = false
    await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    editDialog.value.loading = false
  }
}

// ── 재집계 ────────────────────────────────────────────────────────────
async function doRefresh(r: WeeklyReport) {
  refreshingId.value = r.id
  try {
    await refreshWeeklyReport(r.id)
    Notify.create({ type: 'positive', message: '이슈 데이터를 재집계했습니다.' })
    await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '재집계 실패') })
  } finally {
    refreshingId.value = null
  }
}

// ── 상세 ──────────────────────────────────────────────────────────────
function openDetail(r: WeeklyReport) {
  void router.push(`/pm/weekly-report/${r.id}`)
}

// ── 삭제 ──────────────────────────────────────────────────────────────
function confirmDelete(r: WeeklyReport) {
  Dialog.create({
    title: '삭제 확인', message: `"${r.title}"을(를) 삭제하시겠습니까?`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteWeeklyReport(r.id)
        Notify.create({ type: 'positive', message: '삭제되었습니다.' })
        await load()
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

// ── Excel ──────────────────────────────────────────────────────────────
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function downloadList() {
  try {
    const params: Record<string, number> = {}
    if (filter.value.year) params.year = filter.value.year
    if (filter.value.week) params.week = filter.value.week
    const res = await api.get('/pm/weekly-reports/export/list', { params, responseType: 'blob' })
    triggerDownload(res.data as Blob, `주간보고목록_${filter.value.year ?? '전체'}년.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

async function downloadDetail(id: string) {
  try {
    const res = await api.get(`/pm/weekly-reports/${id}/export`, { responseType: 'blob' })
    triggerDownload(res.data as Blob, `주간보고_${id}.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

// ── 로드 ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    reports.value = await listWeeklyReports({
      ...(filter.value.year ? { year: filter.value.year } : {}),
      ...(filter.value.week ? { week: filter.value.week } : {}),
    })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
