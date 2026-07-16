<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-start q-mb-md q-gutter-sm">
      <q-btn flat round icon="arrow_back" @click="$router.back()" />
      <div class="col">
        <div class="row items-center q-gutter-sm">
          <div class="text-h5 text-weight-bold">{{ report?.title }}</div>
          <q-badge v-if="report" :color="STATUS_COLOR[report.status] ?? 'grey-6'"
            :label="STATUS_KO[report.status] ?? report.status" class="q-px-sm" style="font-size:12px" />
        </div>
        <div class="text-caption text-grey-6 q-mt-xs">
          스케줄 관리 › 주간 보고 › 상세
          <span v-if="report">
            · {{ report.reportYear }}년 {{ report.reportWeek }}주차
            · {{ report.startDate?.slice(0,10) }} ~ {{ report.endDate?.slice(0,10) }}
            <template v-if="report.department"> · {{ report.department }}</template>
          </span>
        </div>
      </div>
      <HelpButton feature="weekly-report-detail" guide-path="/pm/schedule/guide" />
      <!-- 액션 버튼 -->
      <template v-if="report">
        <q-btn v-if="report.status === 'DRAFT'" flat icon="refresh" label="재집계" color="teal" no-caps
          :loading="refreshing" @click="doRefresh" />
        <q-btn v-if="report.status === 'DRAFT'" flat icon="rate_review" label="검토 완료" color="orange" no-caps
          @click="changeStatus('REVIEWING')" />
        <q-btn v-if="report.status === 'REVIEWING'" flat icon="check_circle" label="보고 확정" color="positive" no-caps
          @click="changeStatus('CONFIRMED')" />
        <q-btn v-if="report.status === 'CONFIRMED'" flat icon="lock_open" label="확정 해제" color="grey-7" no-caps
          @click="changeStatus('REVIEWING')" />
        <q-btn flat icon="preview" label="미리보기" color="primary" no-caps @click="openPreview" />
        <q-btn flat icon="picture_as_pdf" label="PDF 출력" color="deep-orange" no-caps @click="openPrint" />
        <q-btn flat icon="download" label="Excel" color="positive" no-caps @click="downloadExcel" />
      </template>
    </div>

    <q-inner-loading :showing="loading" />

    <div v-if="report && !loading" class="column q-gutter-md">

      <!-- 통계 카드 -->
      <div class="row q-col-gutter-sm">
        <div v-for="card in statsCards" :key="card.label" class="col-auto">
          <q-card flat bordered class="text-center q-pa-sm" style="min-width:80px">
            <div class="text-h5 text-weight-bold" :class="card.color">{{ card.value }}</div>
            <div class="text-caption text-grey-6">{{ card.label }}</div>
          </q-card>
        </div>
        <div v-if="report.adminComment" class="col-12 col-sm-auto">
          <q-card flat bordered class="q-pa-sm bg-grey-1">
            <div class="text-caption text-weight-bold text-grey-7 q-mb-xs">관리자 코멘트</div>
            <div class="content-text pre-wrap">{{ report.adminComment }}</div>
          </q-card>
        </div>
      </div>

      <!-- 자동 집계 섹션 -->
      <q-card flat bordered>
        <q-card-section class="q-py-sm q-px-md">
          <div class="row items-center">
            <div class="text-subtitle1 text-weight-bold">자동 집계 업무</div>
            <q-badge color="grey-5" :label="`총 ${report.stats.total}건`" class="q-ml-sm" />
            <q-space />
            <q-btn v-if="report.status === 'DRAFT'" flat dense icon="refresh" label="재집계" size="sm" color="teal" no-caps
              :loading="refreshing" @click="doRefresh" />
          </div>
        </q-card-section>
        <q-separator />
        <q-tabs v-model="tab" dense align="left" class="q-px-md">
          <q-tab name="project" label="프로젝트별" />
          <q-tab name="person"  label="개인별" />
          <q-tab name="all"     label="전체 업무" />
          <q-tab v-if="report.upcomingItems.length" name="upcoming" label="차주 계획" />
        </q-tabs>
        <q-separator />
        <q-card-section style="max-height:60vh;overflow-y:auto" class="q-pa-md">
          <q-tab-panels v-model="tab" animated>

            <!-- 프로젝트별 -->
            <q-tab-panel name="project" class="q-pa-none">
              <div v-if="!report.byProject.length" class="text-grey-5 text-center q-pa-lg">집계된 업무가 없습니다.</div>
              <q-expansion-item v-for="(pb, i) in report.byProject" :key="pb.projectId"
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
                          <q-badge :color="item.isDelayed ? 'negative' : 'grey-5'" :label="ISSUE_STATUS_KO[item.status] ?? item.status" />
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
              <div v-if="!report.byPerson.length" class="text-grey-5 text-center q-pa-lg">집계된 업무가 없습니다.</div>
              <q-expansion-item v-for="(pb, i) in report.byPerson" :key="pb.userId"
                default-opened :label="pb.userName"
                :caption="pb.stats.total ? `완료 ${pb.stats.completed}/${pb.stats.total} · ${pb.stats.completionRate}%` : '이번 주 업무 없음'"
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
                            <q-badge :color="item.isDelayed ? 'negative' : 'grey-5'" :label="ISSUE_STATUS_KO[item.status] ?? item.status" />
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
              <div v-if="!report.allItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="report.allItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">{{ props.row.projectName }}-{{ props.row.issueNumber }}</q-td>
                </template>
                <template #body-cell-priority="props">
                  <q-td :props="props"><q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" /></q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge :color="props.row.isDelayed ? 'negative' : 'grey-5'" :label="ISSUE_STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

            <!-- 차주 계획 -->
            <q-tab-panel name="upcoming" class="q-pa-none">
              <div v-if="!report.upcomingItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="report.upcomingItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">{{ props.row.projectName }}-{{ props.row.issueNumber }}</q-td>
                </template>
                <template #body-cell-priority="props">
                  <q-td :props="props"><q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" /></q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge :color="props.row.isDelayed ? 'negative' : 'grey-5'" :label="ISSUE_STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

          </q-tab-panels>
        </q-card-section>
      </q-card>

      <!-- 수기 항목 섹션 (주요 안건 / 특이사항 및 리스크 / 결정 필요 사항) -->
      <q-card v-for="sec in MANUAL_SECTIONS" :key="sec.section" flat bordered>
        <q-card-section class="q-py-sm q-px-md">
          <div class="row items-center">
            <q-icon :name="sec.icon" :color="sec.color" size="sm" class="q-mr-sm" />
            <div class="text-subtitle1 text-weight-bold">{{ sec.label }}</div>
            <q-badge :color="sec.color" :label="sectionItems(sec.section).length" class="q-ml-sm" />
            <q-space />
            <q-btn v-if="report.status !== 'CONFIRMED'" flat dense icon="add" label="추가" size="sm"
              :color="sec.color" no-caps @click="openAdd(sec.section)" />
          </div>
        </q-card-section>
        <q-separator />

        <!-- 항목 없음 -->
        <div v-if="!sectionItems(sec.section).length" class="text-grey-5 text-body2 text-center q-pa-md">
          항목이 없습니다.
        </div>

        <!-- 복무 현황: 테이블 뷰 -->
        <template v-else-if="sec.section === 'ATTENDANCE'">
          <q-markup-table flat dense separator="cell" class="q-ma-sm">
            <thead>
              <tr class="bg-grey-2">
                <th class="text-left">이름</th>
                <th class="text-center">발생일수</th>
                <th class="text-center">총사용일수</th>
                <th class="text-center">잔여일수</th>
                <th class="text-left">비고</th>
                <th v-if="report.status !== 'CONFIRMED'" style="width:64px" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sectionItems('ATTENDANCE')" :key="item.id"
                :class="{ 'excluded-item': !item.includeInReport }">
                <td class="text-weight-medium">{{ item.title }}</td>
                <td class="text-center text-caption">{{ item.category ?? '-' }}</td>
                <td class="text-center text-caption">{{ item.itemType ?? '-' }}</td>
                <td class="text-center text-caption">{{ item.actionPlan ?? '-' }}</td>
                <td class="text-caption text-grey-7">{{ item.content ?? '-' }}</td>
                <td v-if="report.status !== 'CONFIRMED'" class="text-center">
                  <q-btn flat dense icon="edit" size="xs" color="grey-6" @click="openEdit(item)" />
                  <q-btn flat dense icon="delete" size="xs" color="negative" @click="removeItem(item)" />
                </td>
              </tr>
            </tbody>
          </q-markup-table>
        </template>

        <!-- 일반 섹션: 항목 목록 -->
        <template v-else>
          <div v-for="item in sectionItems(sec.section)" :key="item.id"
            class="manual-item-row q-px-md q-py-sm"
            :class="{ 'excluded-item': !item.includeInReport }">
            <div class="row items-start q-gutter-sm no-wrap">
              <!-- 포함 여부 아이콘 -->
              <q-icon :name="item.includeInReport ? 'check_circle' : 'radio_button_unchecked'"
                :color="item.includeInReport ? 'positive' : 'grey-4'" size="xs" class="q-mt-xs flex-shrink-0"
                style="cursor:pointer" @click="report.status !== 'CONFIRMED' && toggleInclude(item)" />

              <div class="col">
                <!-- 태그 행 -->
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <q-badge v-if="item.category" color="blue-2" text-color="blue-9" :label="item.category" />
                  <q-badge v-if="item.agendaStatus" :color="agendaStatusColor(item.agendaStatus)" :label="item.agendaStatus" />
                  <q-badge v-if="item.itemType" color="purple-2" text-color="purple-9" :label="item.itemType" />
                  <q-badge v-if="item.impact" :color="impactColor(item.impact)" :label="item.impact" />
                  <span class="text-body2 text-weight-medium">{{ item.title }}</span>
                </div>

                <!-- 상세 내용 -->
                <template v-if="item.section === 'MAIN_AGENDA'">
                  <div v-if="item.content" class="text-body2 text-grey-8 q-mb-xs" style="white-space:pre-wrap">{{ item.content }}</div>
                </template>
                <template v-if="item.section === 'ISSUE_RISK'">
                  <div v-if="item.content" class="text-body2 text-grey-8 q-mb-xs"><span class="text-caption text-grey-6">내용:</span> {{ item.content }}</div>
                  <div v-if="item.actionPlan" class="text-body2 text-grey-8"><span class="text-caption text-grey-6">대응:</span> {{ item.actionPlan }}</div>
                </template>
                <template v-if="item.section === 'DECISION_REQUIRED'">
                  <div v-if="item.background" class="text-body2 text-grey-8 q-mb-xs"><span class="text-caption text-grey-6">배경:</span> {{ item.background }}</div>
                  <div v-if="item.options" class="text-body2 text-grey-8 q-mb-xs"><span class="text-caption text-grey-6">선택지:</span> {{ item.options }}</div>
                  <div v-if="item.requestedDecision" class="text-body2 text-grey-8 q-mb-xs"><span class="text-caption text-grey-6">요청:</span> {{ item.requestedDecision }}</div>
                  <div v-if="item.desiredDate" class="text-caption text-grey-6">희망 결정일: {{ item.desiredDate.slice(0,10) }}</div>
                </template>
                <template v-if="item.section === 'NETWORK'">
                  <div v-if="item.content" class="text-body2 text-grey-8 q-mb-xs" style="white-space:pre-wrap">{{ item.content }}</div>
                </template>
                <template v-if="item.section === 'ANNOUNCEMENT'">
                  <div v-if="item.content" class="text-body2 text-grey-8 q-mb-xs" style="white-space:pre-wrap">{{ item.content }}</div>
                </template>

                <div v-if="item.owner" class="text-caption text-grey-6 q-mt-xs">담당자: {{ item.owner }}</div>
              </div>

              <!-- 수정/삭제 버튼 -->
              <div v-if="report.status !== 'CONFIRMED'" class="row q-gutter-xs flex-shrink-0">
                <q-btn flat dense icon="edit" size="xs" color="grey-6" @click="openEdit(item)" />
                <q-btn flat dense icon="delete" size="xs" color="negative" @click="removeItem(item)" />
              </div>
            </div>
          </div>
        </template>
      </q-card>

    </div>

    <!-- 수기 항목 다이얼로그 -->
    <WrItemDialog
      v-if="itemDialog.open"
      v-model="itemDialog.open"
      :report-id="reportId"
      :section="itemDialog.section"
      :item="itemDialog.item"
      @saved="onItemSaved"
    />


  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { api } from 'boot/axios'
import {
  getWeeklyReport, refreshWeeklyReport, changeWeeklyReportStatus, deleteManualItem,
  updateManualItem,
  type WeeklyReport, type ManualItem, type ManualItemSection, type ReportStatus,
  type ProjectBreakdown, type PersonBreakdown,
} from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'
import WrItemDialog from './components/WrItemDialog.vue'


const route  = useRoute()
const router = useRouter()

const reportId = route.params.id as string
const loading   = ref(false)
const refreshing = ref(false)
const report    = ref<WeeklyReport | null>(null)
const tab       = ref('project')

const itemDialog = ref<{ open: boolean; section: ManualItemSection; item: ManualItem | null }>({
  open: false, section: 'MAIN_AGENDA', item: null,
})

// ── 상수 ──────────────────────────────────────────────────────────────
const STATUS_KO: Record<string, string>    = { DRAFT: '초안', REVIEWING: '검토중', CONFIRMED: '확정' }
const STATUS_COLOR: Record<string, string> = { DRAFT: 'grey-6', REVIEWING: 'orange', CONFIRMED: 'positive' }

const ISSUE_STATUS_KO: Record<string, string> = {
  BACKLOG: '백로그', TODO: '할 일', IN_PROGRESS: '진행 중', IN_REVIEW: '검토 중', DONE: '완료',
}
const PRIORITY_KO: Record<string, string>    = { LOWEST: '최하', LOW: '낮음', MEDIUM: '중간', HIGH: '높음', HIGHEST: '최고' }
const PRIORITY_COLOR: Record<string, string> = { LOWEST: 'grey', LOW: 'blue-grey', MEDIUM: 'orange', HIGH: 'deep-orange', HIGHEST: 'red' }

const PALETTE = ['blue', 'teal', 'purple', 'orange', 'green', 'deep-orange', 'indigo', 'cyan', 'pink', 'amber']
function headerBg(i: number)   { return `bg-${PALETTE[i % PALETTE.length]}-1` }
function headerText(i: number) { return `text-${PALETTE[i % PALETTE.length]}-9` }

const MANUAL_SECTIONS = [
  { section: 'MAIN_AGENDA'      as ManualItemSection, label: '주요 안건',           icon: 'task_alt',       color: 'blue'   },
  { section: 'ISSUE_RISK'       as ManualItemSection, label: '특이사항 및 리스크',   icon: 'warning_amber',  color: 'orange' },
  { section: 'DECISION_REQUIRED'as ManualItemSection, label: '결정 필요 사항',       icon: 'gavel',          color: 'purple' },
  { section: 'NETWORK'          as ManualItemSection, label: '네트워크',             icon: 'hub',             color: 'cyan'   },
  { section: 'ANNOUNCEMENT'     as ManualItemSection, label: '공지사항',             icon: 'campaign',       color: 'teal'   },
  { section: 'ATTENDANCE'       as ManualItemSection, label: '복무 현황',            icon: 'event_available',color: 'indigo' },
]

const workItemCols = [
  { name: 'num',      label: '번호',    field: 'issueNumber', align: 'left'   as const },
  { name: 'title',    label: '업무명',  field: 'title',       align: 'left'   as const },
  { name: 'assignee', label: '담당자',  field: 'assigneeName',align: 'left'   as const },
  { name: 'priority', label: '우선순위',field: 'priority',    align: 'center' as const },
  { name: 'status',   label: '상태',    field: 'status',      align: 'center' as const },
  { name: 'due',      label: '마감일',  field: (r: { dueDate: string | null }) => r.dueDate?.slice(0,10) ?? '', align: 'center' as const },
]

// ── computed ───────────────────────────────────────────────────────────
const statsCards = computed(() => {
  if (!report.value) return []
  const s = report.value.stats
  return [
    { label: '총 업무', value: s.total,          color: 'text-grey-8'   },
    { label: '완료',    value: s.completed,      color: 'text-positive' },
    { label: '진행 중', value: s.inProgress,     color: 'text-primary'  },
    { label: '지연',    value: s.delayed,        color: 'text-negative' },
    { label: '완료율',  value: `${s.completionRate}%`, color: 'text-teal' },
  ]
})

function sectionItems(section: ManualItemSection) {
  if (!report.value) return []
  return report.value.manualItems
    .filter(i => i.section === section)
    .sort((a, b) => a.sortOrder - b.sortOrder)
}

function breakdown(pb: ProjectBreakdown | PersonBreakdown) {
  return [
    { label: '✅ 완료',     items: pb.completed,  color: 'positive' },
    { label: '🔄 진행 중',  items: pb.inProgress, color: 'primary'  },
    { label: '⚠ 지연',      items: pb.delayed,    color: 'negative' },
    { label: '📌 차주 계획', items: pb.upcoming,   color: 'grey-7'   },
  ]
}

function agendaStatusColor(s: string) {
  const map: Record<string, string> = { 예정: 'blue-2', 진행중: 'orange-2', 완료: 'green-2', 지연: 'red-2', 보류: 'grey-3' }
  return map[s] ?? 'grey-2'
}

function impactColor(impact: string) {
  return impact === '높음' ? 'red-2' : impact === '보통' ? 'orange-2' : 'grey-2'
}

// ── 로드 ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    report.value = await getWeeklyReport(reportId)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
    void router.back()
  } finally {
    loading.value = false
  }
}

// ── 재집계 ────────────────────────────────────────────────────────────
async function doRefresh() {
  refreshing.value = true
  try {
    report.value = await refreshWeeklyReport(reportId)
    Notify.create({ type: 'positive', message: '이슈 데이터를 재집계했습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '재집계 실패') })
  } finally {
    refreshing.value = false
  }
}

// ── 상태 변경 ─────────────────────────────────────────────────────────
async function changeStatus(status: ReportStatus) {
  try {
    report.value = await changeWeeklyReportStatus(reportId, status)
    Notify.create({ type: 'positive', message: `상태가 '${STATUS_KO[status]}'로 변경되었습니다.` })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '상태 변경 실패') })
  }
}

// ── 수기 항목 ─────────────────────────────────────────────────────────
function openAdd(section: ManualItemSection) {
  itemDialog.value = { open: true, section, item: null }
}

function openEdit(item: ManualItem) {
  itemDialog.value = { open: true, section: item.section, item }
}

function onItemSaved(updated: WeeklyReport) {
  report.value = updated
}

async function toggleInclude(item: ManualItem) {
  try {
    report.value = await updateManualItem(reportId, item.id, {
      include_in_report: !item.includeInReport,
    })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '수정 실패') })
  }
}

async function removeItem(item: ManualItem) {
  try {
    report.value = await deleteManualItem(reportId, item.id)
    Notify.create({ type: 'positive', message: '삭제되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
  }
}

// ── 미리보기 / PDF 출력 ───────────────────────────────────────────────
function openPreview() {
  void router.push(`/pm/weekly-report/${reportId}/print?preview=true`)
}

function openPrint() {
  void router.push(`/pm/weekly-report/${reportId}/print`)
}

// ── Excel ──────────────────────────────────────────────────────────────
async function downloadExcel() {
  try {
    const res = await api.get(`/pm/weekly-reports/${reportId}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url; a.download = `주간보고_${reportId}.xlsx`
    document.body.appendChild(a); a.click()
    document.body.removeChild(a); URL.revokeObjectURL(url)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

onMounted(load)
</script>

<style scoped>
.manual-item-row {
  border-top: 1px solid rgba(0,0,0,0.06);
}
.manual-item-row:hover {
  background: rgba(0,0,0,0.02);
}
.excluded-item {
  opacity: 0.45;
}
</style>
