<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-md q-gutter-sm">
      <div>
        <div class="text-h5 text-weight-bold">월간 보고</div>
        <div class="text-caption text-grey-6">스케줄 관리 › 월간 보고</div>
      </div>
      <q-space />
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
            <q-select v-model="filter.month" :options="monthOptions" label="월" dense outlined
              emit-value map-options clearable style="min-width:90px" @update:model-value="load" />
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
            {{ props.row.reportYear }}년 {{ props.row.reportMonth }}월
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
        <template #body-cell-actions="props">
          <q-td :props="props" class="q-gutter-xs">
            <q-btn flat dense icon="visibility" size="sm" color="primary" @click="openDetail(props.row)" />
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
          <div class="text-h6">월간 보고 생성</div>
          <q-space /><q-btn flat round dense icon="close" @click="createDialog.open = false" />
        </q-card-section>
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-gutter-sm">
          <div class="text-caption text-grey-7 q-mb-sm">
            연월을 입력하면 해당 월의 이슈 데이터가 자동으로 집계됩니다.
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input v-model.number="createForm.report_year" label="연도 *" type="number" outlined dense />
            </div>
            <div class="col-6">
              <q-select v-model="createForm.report_month" :options="monthOptions" label="월 *"
                outlined dense emit-value map-options />
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
            type="textarea" rows="4" hint="이슈 집계 외에 관리자가 추가할 내용을 입력하세요." />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="editDialog.open = false" />
          <q-btn color="primary" label="저장" :loading="editDialog.loading" no-caps @click="submitEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 상세 다이얼로그 -->
    <q-dialog v-model="detailDialog.open" full-width>
      <q-card v-if="detailDialog.report" style="max-width:1100px;width:100%">
        <q-card-section class="row items-start no-wrap q-pb-none">
          <div class="col">
            <div class="text-h6 text-weight-bold">{{ detailDialog.report.title }}</div>
            <div class="text-caption text-grey-6">
              {{ detailDialog.report.reportYear }}년 {{ detailDialog.report.reportMonth }}월
              <span v-if="detailDialog.report.department"> · {{ detailDialog.report.department }}</span>
            </div>
          </div>
          <q-btn flat round dense icon="close" @click="detailDialog.open = false" />
        </q-card-section>

        <!-- 전체 통계 -->
        <q-card-section class="q-pt-sm q-pb-none">
          <div class="row q-col-gutter-sm">
            <div v-for="card in overallCards(detailDialog.report.stats)" :key="card.label" class="col-auto">
              <q-card flat bordered class="text-center q-pa-sm" style="min-width:88px">
                <div class="text-h5 text-weight-bold" :class="card.color">{{ card.value }}</div>
                <div class="text-caption text-grey-6">{{ card.label }}</div>
              </q-card>
            </div>
          </div>
        </q-card-section>

        <q-separator class="q-mt-md" />

        <q-tabs v-model="detailTab" dense align="left" class="q-px-md">
          <q-tab name="project" label="프로젝트별" />
          <q-tab name="person"  label="개인별" />
          <q-tab name="all"     label="전체 업무" />
          <q-tab v-if="detailDialog.report.upcomingItems.length" name="upcoming" label="차월 계획" />
        </q-tabs>
        <q-separator />

        <q-card-section style="max-height:55vh;overflow-y:auto" class="q-pa-md">
          <q-tab-panels v-model="detailTab" animated>

            <!-- 프로젝트별 -->
            <q-tab-panel name="project" class="q-pa-none">
              <div v-if="!detailDialog.report.byProject.length" class="text-grey-5 text-center q-pa-lg">
                집계된 업무가 없습니다.
              </div>
              <q-expansion-item v-for="(pb, i) in detailDialog.report.byProject" :key="pb.projectId"
                default-opened :label="pb.projectName"
                :caption="`${pb.orgName ?? ''} · 완료 ${pb.stats.completed}/${pb.stats.total} · ${pb.stats.completionRate}%`"
                class="q-mb-sm" :header-class="`${headerBg(i)} ${headerText(i)} text-weight-bold`">
                <q-card flat>
                  <q-card-section class="q-pa-sm">
                    <template v-for="sec in breakdown(pb)" :key="sec.label">
                      <div v-if="sec.items.length" class="q-mb-sm">
                        <div class="text-caption text-weight-bold q-mb-xs" :class="`text-${sec.color}`">{{ sec.label }}</div>
                        <div v-for="item in sec.items" :key="item.issueId"
                          class="row items-center q-gutter-xs q-mb-xs q-pa-xs bg-grey-1 rounded-borders">
                          <span class="text-caption text-grey-6" style="min-width:90px">{{ item.projectName }}-{{ item.issueNumber }}</span>
                          <span class="text-body2 col ellipsis">{{ item.title }}</span>
                          <span v-if="item.assigneeName" class="text-caption text-grey-7">{{ item.assigneeName }}</span>
                          <q-badge :color="PRIORITY_COLOR[item.priority]" :label="PRIORITY_KO[item.priority]" />
                          <q-badge :color="item.isDelayed ? 'negative' : 'grey-5'" :label="STATUS_KO[item.status] ?? item.status" />
                          <span v-if="item.dueDate" class="text-caption text-grey-6">{{ item.dueDate.slice(0,10) }}</span>
                        </div>
                      </div>
                    </template>
                    <div v-if="!pb.completed.length && !pb.inProgress.length && !pb.delayed.length"
                      class="text-grey-5 text-caption">업무 없음</div>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-tab-panel>

            <!-- 개인별 -->
            <q-tab-panel name="person" class="q-pa-none">
              <div v-if="!detailDialog.report.byPerson.length" class="text-grey-5 text-center q-pa-lg">
                집계된 업무가 없습니다.
              </div>
              <q-expansion-item v-for="(pb, i) in detailDialog.report.byPerson" :key="pb.userId"
                default-opened :label="pb.userName"
                :caption="pb.stats.total ? `완료 ${pb.stats.completed}/${pb.stats.total} · ${pb.stats.completionRate}%` : '이번 달 업무 없음'"
                class="q-mb-sm" :header-class="`${headerBg(i)} ${headerText(i)} text-weight-bold`">
                <q-card flat>
                  <q-card-section class="q-pa-sm">
                    <template v-for="sec in breakdown(pb)" :key="sec.label">
                      <div class="q-mb-sm">
                        <div class="text-caption text-weight-bold q-mb-xs" :class="`text-${sec.color}`">{{ sec.label }}</div>
                        <div v-if="sec.items.length">
                          <div v-for="item in sec.items" :key="item.issueId"
                            class="row items-center q-gutter-xs q-mb-xs q-pa-xs bg-grey-1 rounded-borders">
                            <span class="text-caption text-grey-6" style="min-width:90px">{{ item.projectName }}-{{ item.issueNumber }}</span>
                            <span class="text-body2 col ellipsis">{{ item.title }}</span>
                            <q-badge :color="PRIORITY_COLOR[item.priority]" :label="PRIORITY_KO[item.priority]" />
                            <q-badge :color="item.isDelayed ? 'negative' : 'grey-5'" :label="STATUS_KO[item.status] ?? item.status" />
                            <span v-if="item.dueDate" class="text-caption text-grey-6">{{ item.dueDate.slice(0,10) }}</span>
                          </div>
                        </div>
                        <div v-else class="text-caption text-grey-5 q-pl-sm">없음</div>
                      </div>
                    </template>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-tab-panel>

            <!-- 전체 업무 -->
            <q-tab-panel name="all" class="q-pa-none">
              <div v-if="!detailDialog.report.allItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="detailDialog.report.allItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">
                    {{ props.row.projectName }}-{{ props.row.issueNumber }}
                  </q-td>
                </template>
                <template #body-cell-priority="props">
                  <q-td :props="props">
                    <q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" />
                  </q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge :color="props.row.isDelayed ? 'negative' : 'grey-5'"
                      :label="STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

            <!-- 차월 계획 -->
            <q-tab-panel name="upcoming" class="q-pa-none">
              <div v-if="!detailDialog.report.upcomingItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="detailDialog.report.upcomingItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">
                    {{ props.row.projectName }}-{{ props.row.issueNumber }}
                  </q-td>
                </template>
                <template #body-cell-priority="props">
                  <q-td :props="props">
                    <q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" />
                  </q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge :color="props.row.isDelayed ? 'negative' : 'grey-5'"
                      :label="STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

          </q-tab-panels>

          <!-- 관리자 코멘트 -->
          <div v-if="detailDialog.report.adminComment" class="q-mt-md">
            <q-separator class="q-mb-md" />
            <div class="text-subtitle2 text-weight-bold q-mb-xs">관리자 코멘트</div>
            <div class="text-body2 q-pa-sm bg-grey-1 rounded-borders" style="white-space:pre-wrap">
              {{ detailDialog.report.adminComment }}
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat icon="download" label="Excel" color="positive" no-caps @click="downloadDetail(detailDialog.report!.id)" />
          <q-btn flat label="닫기" no-caps @click="detailDialog.open = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Notify, Dialog } from 'quasar'
import { api } from 'boot/axios'
import {
  listMonthlyReports, createMonthlyReport, updateMonthlyReport,
  deleteMonthlyReport, refreshMonthlyReport,
  type MonthlyReport, type MonthlyReportCreate,
  type ReportStats, type WorkItem, type ProjectBreakdown, type PersonBreakdown,
} from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

// ── 색상 팔레트 ───────────────────────────────────────────────────────
const PALETTE = ['blue', 'teal', 'purple', 'orange', 'green', 'deep-orange', 'indigo', 'cyan', 'pink', 'amber']
function headerBg(index: number) { return `bg-${PALETTE[index % PALETTE.length]}-1` }
function headerText(index: number) { return `text-${PALETTE[index % PALETTE.length]}-9` }

// ── 레이블 맵 ─────────────────────────────────────────────────────────
const STATUS_KO: Record<string, string> = {
  BACKLOG: '백로그', TODO: '할 일', IN_PROGRESS: '진행 중', IN_REVIEW: '검토 중', DONE: '완료',
}
const PRIORITY_KO: Record<string, string> = {
  LOWEST: '최하', LOW: '낮음', MEDIUM: '중간', HIGH: '높음', HIGHEST: '최고',
}
const PRIORITY_COLOR: Record<string, string> = {
  LOWEST: 'grey', LOW: 'blue-grey', MEDIUM: 'orange', HIGH: 'deep-orange', HIGHEST: 'red',
}

// ── 상태 ──────────────────────────────────────────────────────────────
const now = new Date()
const reports = ref<MonthlyReport[]>([])
const loading = ref(false)
const refreshingId = ref<string | null>(null)
const detailTab = ref('project')

const filter = ref<{ year: number | null; month: number | null }>({
  year: now.getFullYear(), month: null,
})

const yearOptions = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)
  .map(y => ({ label: `${y}년`, value: y }))
const monthOptions = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}월`, value: i + 1 }))

// ── 테이블 컬럼 ───────────────────────────────────────────────────────
const columns = [
  { name: 'period',  label: '기간',      field: 'reportMonth', align: 'left'   as const, sortable: true },
  { name: 'title',   label: '제목',      field: 'title',       align: 'left'   as const, sortable: true },
  { name: 'stats',   label: '업무 현황', field: 'stats',       align: 'left'   as const },
  { name: 'rate',    label: '완료율',    field: (r: MonthlyReport) => r.stats.completionRate, align: 'left' as const, sortable: true },
  { name: 'createdByName', label: '작성자', field: 'createdByName', align: 'left' as const },
  { name: 'actions', label: '',          field: 'id',          align: 'center' as const },
]

const workItemCols = [
  { name: 'num',      label: '번호',    field: 'issueNumber',  align: 'left'   as const },
  { name: 'title',    label: '업무명',  field: 'title',        align: 'left'   as const },
  { name: 'epic',     label: '에픽',    field: 'epicTitle',    align: 'left'   as const },
  { name: 'sprint',   label: '스프린트',field: 'sprintName',   align: 'left'   as const },
  { name: 'assignee', label: '담당자',  field: 'assigneeName', align: 'left'   as const },
  { name: 'priority', label: '우선순위',field: 'priority',     align: 'center' as const },
  { name: 'status',   label: '상태',    field: 'status',       align: 'center' as const },
  { name: 'due',      label: '마감일',  field: (r: WorkItem) => r.dueDate?.slice(0,10) ?? '', align: 'center' as const },
  { name: 'sp',       label: 'SP',      field: 'storyPoints',  align: 'center' as const },
]

function overallCards(stats: ReportStats) {
  return [
    { label: '총 업무', value: stats.total,          color: 'text-grey-8'   },
    { label: '완료',    value: stats.completed,      color: 'text-positive' },
    { label: '진행 중', value: stats.inProgress,     color: 'text-primary'  },
    { label: '지연',    value: stats.delayed,        color: 'text-negative' },
    { label: '완료율',  value: `${stats.completionRate}%`, color: 'text-teal' },
  ]
}

function breakdown(pb: ProjectBreakdown | PersonBreakdown) {
  return [
    { label: '✅ 완료',     items: pb.completed,  color: 'positive' },
    { label: '🔄 진행 중',  items: pb.inProgress, color: 'primary'  },
    { label: '⚠ 지연',      items: pb.delayed,    color: 'negative' },
    { label: '📌 차월 계획', items: pb.upcoming,   color: 'grey-7'   },
  ]
}

// ── 생성 ──────────────────────────────────────────────────────────────
const createDialog = ref({ open: false, loading: false })
const createForm = ref<MonthlyReportCreate>({
  report_year: now.getFullYear(), report_month: now.getMonth() + 1,
  title: '', department: '',
})

function openCreate() {
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  createForm.value = {
    report_year: year, report_month: month,
    title: `${year}년 ${month}월 월간 보고`,
    department: '',
  }
  createDialog.value = { open: true, loading: false }
}

async function submitCreate() {
  if (!createForm.value.title) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }
  createDialog.value.loading = true
  try {
    await createMonthlyReport(createForm.value)
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

function openEdit(r: MonthlyReport) {
  editForm.value = {
    title: r.title, department: r.department ?? '',
    admin_comment: r.adminComment ?? '',
  }
  editDialog.value = { open: true, loading: false, editId: r.id }
}

async function submitEdit() {
  editDialog.value.loading = true
  try {
    await updateMonthlyReport(editDialog.value.editId, {
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
async function doRefresh(r: MonthlyReport) {
  refreshingId.value = r.id
  try {
    await refreshMonthlyReport(r.id)
    Notify.create({ type: 'positive', message: '이슈 데이터를 재집계했습니다.' })
    await load()
    if (detailDialog.value.open && detailDialog.value.report?.id === r.id) {
      const updated = reports.value.find(x => x.id === r.id)
      if (updated) detailDialog.value.report = updated
    }
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '재집계 실패') })
  } finally {
    refreshingId.value = null
  }
}

// ── 상세 ──────────────────────────────────────────────────────────────
const detailDialog = ref<{ open: boolean; report: MonthlyReport | null }>({ open: false, report: null })

function openDetail(r: MonthlyReport) {
  detailTab.value = 'project'
  detailDialog.value = { open: true, report: r }
}

// ── 삭제 ──────────────────────────────────────────────────────────────
function confirmDelete(r: MonthlyReport) {
  Dialog.create({
    title: '삭제 확인', message: `"${r.title}"을(를) 삭제하시겠습니까?`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteMonthlyReport(r.id)
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
    if (filter.value.year)  params.year  = filter.value.year
    if (filter.value.month) params.month = filter.value.month
    const res = await api.get('/pm/monthly-reports/export/list', { params, responseType: 'blob' })
    triggerDownload(res.data as Blob, `월간보고목록_${filter.value.year ?? '전체'}년.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

async function downloadDetail(id: string) {
  try {
    const res = await api.get(`/pm/monthly-reports/${id}/export`, { responseType: 'blob' })
    triggerDownload(res.data as Blob, `월간보고_${id}.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

// ── 로드 ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    reports.value = await listMonthlyReports({
      ...(filter.value.year  ? { year:  filter.value.year  } : {}),
      ...(filter.value.month ? { month: filter.value.month } : {}),
    })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
