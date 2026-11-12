<template>
  <q-page class="dashboard-page q-pa-md">
    <draggable
      :list="cardOrder"
      tag="div"
      :item-key="(id: string) => id"
      class="dashboard-grid"
      handle=".card-drag-handle"
      ghost-class="drag-ghost"
      @end="saveCardOrder"
    >
      <template #item="{ element: cardId }">

      <FavoriteProjectBacklogs v-if="cardId === 'favorites'" class="dash-card favorites-card" :class="cardSizeClasses(cardId)">
        <template #drag-handle>
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
        </template>
        <template #actions>
          <q-btn flat round dense size="sm" icon="open_in_full" color="grey-5" class="card-resize-btn" aria-label="즐겨찾는 프로젝트 크기 조절">
            <q-tooltip>카드 크기 조절</q-tooltip>
            <q-menu anchor="bottom right" self="top right">
              <CardSizePicker :w="sizeOf(cardId).w" :h="sizeOf(cardId).h" @select="(w, h) => setCardSize(cardId, w, h)" />
            </q-menu>
          </q-btn>
        </template>
      </FavoriteProjectBacklogs>

      <section v-else-if="cardId === 'weeklyReport'" class="dash-card shortcuts-card" :class="cardSizeClasses(cardId)" aria-labelledby="shortcuts-title">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="shortcut" size="18px" color="primary" aria-hidden="true" />
          <h2 id="shortcuts-title" class="card-title">업무 바로가기</h2>
          <q-space />
          <q-btn flat round dense size="sm" icon="open_in_full" color="grey-5" class="card-resize-btn" aria-label="업무 바로가기 크기 조절">
            <q-tooltip>카드 크기 조절</q-tooltip>
            <q-menu anchor="bottom right" self="top right">
              <CardSizePicker :w="sizeOf(cardId).w" :h="sizeOf(cardId).h" @select="(w, h) => setCardSize(cardId, w, h)" />
            </q-menu>
          </q-btn>
        </div>
        <nav class="dash-card-body shortcuts-body" aria-label="이번 주·이번 달 업무">
          <q-btn v-if="hasPmPerm" flat no-caps class="shortcut-row" aria-label="이번 주 주간보고 열기"
            :loading="openingReport === 'weekly'" :disable="openingReport !== null && openingReport !== 'weekly'" @click="openCurrentReport('weekly')">
            <q-icon name="view_week" size="20px" class="shortcut-icon" aria-hidden="true" />
            <span class="shortcut-copy">
              <span class="shortcut-title">주간보고</span>
              <span class="shortcut-period">이번 주<span class="shortcut-dates"> · {{ thisWeekReportPeriod.startDate.slice(5).replace('-', '.') }} ~ {{ thisWeekReportPeriod.endDate.slice(5).replace('-', '.') }}</span></span>
            </span>
            <q-icon name="arrow_forward" size="18px" class="shortcut-arrow" aria-hidden="true" />
          </q-btn>
          <q-btn v-if="hasPmPerm" flat no-caps class="shortcut-row" aria-label="이번 달 월간보고 열기"
            :loading="openingReport === 'monthly'" :disable="openingReport !== null && openingReport !== 'monthly'" @click="openCurrentReport('monthly')">
            <q-icon name="calendar_month" size="20px" class="shortcut-icon" aria-hidden="true" />
            <span class="shortcut-copy">
              <span class="shortcut-title">월간보고</span>
              <span class="shortcut-period">이번 달<span class="shortcut-dates"> · {{ thisMonthReportPeriod.year }}년 {{ thisMonthReportPeriod.month }}월</span></span>
            </span>
            <q-icon name="arrow_forward" size="18px" class="shortcut-arrow" aria-hidden="true" />
          </q-btn>
          <q-btn v-if="canInspect" flat no-caps class="shortcut-row" aria-label="이번 달 서버점검 작업 목록 열기"
            :disable="openingReport !== null" @click="openCurrentInspection">
            <q-icon name="fact_check" size="20px" class="shortcut-icon" aria-hidden="true" />
            <span class="shortcut-copy">
              <span class="shortcut-title">서버점검</span>
              <span class="shortcut-period">이번 달<span class="shortcut-dates"> · {{ thisMonthReportPeriod.year }}년 {{ thisMonthReportPeriod.month }}월 점검 작업</span></span>
            </span>
            <q-icon name="arrow_forward" size="18px" class="shortcut-arrow" aria-hidden="true" />
          </q-btn>
        </nav>
      </section>

      <div v-else-if="cardId === 'calendar'" class="dash-card calendar-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="calendar_month" size="18px" color="primary" />
          <span class="card-title">달력</span>
          <q-space />
          <q-btn flat dense no-caps color="primary" icon="add" label="D-Day 추가" aria-label="D-Day 추가" @click="openDDayCreate()" />
          <q-btn flat round dense size="sm" icon="open_in_full" color="grey-5" class="card-resize-btn" aria-label="달력 크기 조절">
            <q-tooltip>카드 크기 조절</q-tooltip>
            <q-menu anchor="bottom right" self="top right">
              <CardSizePicker :w="sizeOf(cardId).w" :h="sizeOf(cardId).h" @select="(w, h) => setCardSize(cardId, w, h)" />
            </q-menu>
          </q-btn>
        </div>
        <div class="dash-card-body">
          <DDayCalendar :events="calendarDDays" :today="todayISO" :loading="ddaysLoading || pmLoading || watchLoading"
            :load-failed="ddaysLoadFailed || watchLoadFailed" :error-message="calendarLoadError" @retry="retryCalendar" @create="openDDayCreate">
            <template #actions="{ event }">
              <template v-if="editableCalendarDDay(event.id)">
                <q-btn v-close-popup flat dense no-caps color="primary" icon="edit" label="수정" @click="editCalendarDDay(event.id)" />
                <q-btn v-close-popup flat dense no-caps color="negative" icon="delete_outline" label="삭제" @click="deleteCalendarDDay(event.id)" />
              </template>
              <template v-else-if="event.id === 'inspection'">
                <q-btn v-if="canInspect" v-close-popup flat dense no-caps color="primary" label="내 점검 작업" :to="{ path: '/inspection/tasks', query: { mine: '1' } }" />
                <q-btn v-if="auth.me?.isAdmin" v-close-popup flat dense no-caps color="primary" icon="edit" label="점검일 수정" @click="openInspectionEdit" />
                <q-btn v-if="auth.me?.isAdmin && inspectionOverridden" v-close-popup flat dense no-caps color="primary" label="자동 계산으로 초기화" @click="resetInspection" />
              </template>
              <q-btn v-else-if="event.id.startsWith('issue-')" v-close-popup flat dense no-caps color="primary" icon="open_in_new" label="일감 보기" @click="openCalendarIssue(event.id)" />
            </template>
          </DDayCalendar>
        </div>
      </div>

      <div v-else-if="cardId === 'pm'" class="dash-card pm-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="fa-solid fa-diagram-project" size="18px" color="indigo-7" />
          <span class="card-title">내 일감 보기</span>
          <q-space />
          <q-btn v-if="hasPmPerm || hasSrWorkPerm" flat dense round icon="open_in_new" size="sm" color="grey-6" aria-label="내 담당 일감 목록 열기"
            :to="hasPmPerm ? { path: '/pm/dashboard', query: { group: 'assigned' } } : { path: '/pm/sr/manage', query: { mine: '1', tab: MY_WORK_SR_STATUSES.join(',') } }" />
          <q-btn flat round dense size="sm" icon="open_in_full" color="grey-5" class="card-resize-btn">
            <q-tooltip>카드 크기 조절</q-tooltip>
            <q-menu anchor="bottom right" self="top right">
              <CardSizePicker
                :w="sizeOf(cardId).w"
                :h="sizeOf(cardId).h"
                @select="(w, h) => setCardSize(cardId, w, h)"
              />
            </q-menu>
          </q-btn>
        </div>

        <div class="dash-card-body">
          <MyWorkList :items="myWorkItems" :loading="pmLoading || srLoading" :errors="myWorkErrors"
            @open="openMyWork" @retry="retryMyWork" />
        </div>
      </div>

      </template>
    </draggable>

    <!-- D-Day 추가/수정 다이얼로그 -->
    <q-dialog
      v-model="ddayDialog"
      :persistent="ddaySaving || (ddayForm.id !== '' && ddayCompletingId === ddayForm.id)"
    >
      <q-card class="dday-edit-card">
        <q-card-section>
          <div class="text-h6">{{ ddayForm.id ? 'D-Day 수정' : 'D-Day 추가' }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="ddayForm.title" outlined dense label="이름 *" placeholder="예: ISMS-P 심사" />
          <q-input v-model="ddayForm.date" outlined dense label="날짜 *" type="date" />
          <q-select
            v-model="ddayForm.color"
            outlined dense label="색상"
            :options="ddayColorOptions"
            emit-value map-options
          />
          <q-checkbox v-if="auth.me?.isAdmin" v-model="ddayForm.visibleToAll" label="전체 표시" />
          <q-select
            v-if="!ddayForm.visibleToAll"
            v-model="ddayForm.visibleTeams"
            outlined dense multiple use-chips clearable
            label="표시할 팀"
            :options="ddayTeamOptions"
            emit-value map-options
            :loading="ddayUsersLoading"
          />
          <q-select
            v-if="!ddayForm.visibleToAll"
            v-model="ddayForm.visibleUserIds"
            outlined dense multiple use-chips clearable
            label="표시할 사람"
            class="dday-visible-people-select"
            :options="ddayUserOptions"
            emit-value map-options
            :hint="'※팀과 사람을 모두 비우면 나에게만 표시됩니다.\n선택한 팀원과 사람에게 표시됩니다.'"
            :loading="ddayUsersLoading"
          />
          <q-input v-model="ddayForm.note" outlined dense label="메모" type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            v-if="canCompleteEditedDDay"
            flat color="positive" icon="check_circle" label="완료"
            :loading="ddayCompletingId === ddayForm.id"
            @click="completeEditedDDay"
          />
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="ddaySaving" @click="saveDDay" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <IssueDetailDialog
      v-if="pmDetailDialog.issue"
      v-model="pmDetailDialog.open"
      :project-id="pmDetailDialog.issue.projectId"
      :project-key="pmDetailDialog.issue.projectKey ?? ''"
      :issue="pmDetailDialog.issue"
      @updated="refreshMyWork"
      @deleted="refreshMyWork"
    />

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import draggable from 'vuedraggable'
import { useAuthStore } from 'stores/auth'
import { api } from 'boot/axios'
import { fetchDDays, fetchDDayAudience, createDDay, patchDDay, deleteDDay, completeDDay as completeDDayRequest, type DDay, type DDayAudienceUser } from 'src/services/ddays'
import { type Issue } from 'src/services/pm/issue'
import { listAllSRs, type SRListItem } from 'src/services/sr'
import { getPrefs, savePrefs, type ColPreset, type CardSize } from 'src/services/prefs'
import { getInspectionTasks, thisMonth } from 'src/services/inspection'
import { listWeeklyReports, listMonthlyReports } from 'src/services/pm/reports'
import { getIsoWeekKst, getIsoWeekPeriodKst, getCalendarMonthKst, fmtDateKst, fmtDatetimeKst } from 'src/utils/time/kst'
import { getErrorMessage } from 'src/utils/http/error'
import CardSizePicker from 'src/components/CardSizePicker.vue'
import FavoriteProjectBacklogs from 'src/components/dashboard/FavoriteProjectBacklogs.vue'
import DDayCalendar, { type CalendarDDay } from 'src/components/dashboard/DDayCalendar.vue'
import MyWorkList from 'src/components/dashboard/MyWorkList.vue'
import { buildMyWork, MY_WORK_SR_STATUSES, type MyWorkItem } from 'src/utils/myWork'
import { DUTY_RANGE_DAYS, groupDutyPeriods, loadDashboardDuties, nextDutyPeriod, type DutyAssignment } from 'src/utils/dutyPeriods'
import { resolveDashboardLayout } from 'src/utils/dashboardLayout'
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue'

const auth = useAuthStore()
const $q = useQuasar()
const router = useRouter()
const openingReport = ref<'weekly' | 'monthly' | null>(null)
const thisWeekReportPeriod = computed(() => getIsoWeekPeriodKst(new Date(clockNow.value)))
const thisMonthReportPeriod = computed(() => getCalendarMonthKst(new Date(clockNow.value)))
let disposed = false

async function openCurrentReport(kind: 'weekly' | 'monthly') {
  if (openingReport.value || !hasPmPerm.value) return
  openingReport.value = kind
  const label = kind === 'weekly' ? '이번 주 주간보고' : '이번 달 월간보고'
  try {
    // Calculate on click as well as on the clock tick, including month/year rollover.
    const period = kind === 'weekly' ? getIsoWeekKst() : getCalendarMonthKst()
    const reports = kind === 'weekly' ? await listWeeklyReports(period) : await listMonthlyReports(period)
    if (disposed) return
    const report = reports.length === 1 ? reports[0] : undefined
    await router.push(report
      ? { path: `/pm/${kind}-report/${report.id}` }
      : { path: `/pm/${kind}-report`, query: period })
    if (!reports.length) $q.notify({ type: 'info', message: `${label}가 아직 없습니다.` })
  } catch (e) {
    if (!disposed) $q.notify({ type: 'negative', message: getErrorMessage(e, `${label}를 불러오지 못했습니다. 다시 시도해 주세요.`) })
  } finally {
    openingReport.value = null
  }
}

function openCurrentInspection() {
  if (!canInspect.value || openingReport.value) return
  const { year, month } = getCalendarMonthKst()
  void router.push({ path: '/inspection/tasks', query: { month: `${year}-${String(month).padStart(2, '0')}` } })
}

const DAY_MS = 24 * 60 * 60 * 1000
const clockNow = ref(Date.now())
const todayDayKey = ref(calendarDayKey(new Date()))
const todayISO = computed(() => new Date(todayDayKey.value).toISOString().slice(0, 10))
let dayRefreshInterval: number | undefined

function calendarDayKey(date: Date): number {
  return Date.parse(`${fmtDateKst(date.toISOString())}T00:00:00Z`)
}

function dateStringDayKey(dateStr: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateStr.trim())
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const key = Date.UTC(year, month - 1, day)
  const parsed = new Date(key)
  if (parsed.getUTCFullYear() !== year || parsed.getUTCMonth() !== month - 1 || parsed.getUTCDate() !== day) return null
  return key
}

// ── 당직 일정 ──────────────────────────────────────────────────────────────
const watchLoading = ref(false)
const watchLoadFailed = ref(false)
const watchList = ref<DutyAssignment[]>([])

const now = new Date()

function isMyWatchAssignee(assignee: string): boolean {
  const fullName = (auth.me?.fullName || '').trim()
  const email = (auth.me?.email || '').trim()
  const a = (assignee || '').trim()
  if (!a || (!fullName && !email)) return false
  if (email && a === email) return true
  if (fullName && (a.includes(fullName) || fullName.includes(a))) return true
  return false
}

const myWatchList = computed(() => {
  const lastDay = todayDayKey.value + DUTY_RANGE_DAYS * DAY_MS
  return watchList.value.filter((w) => {
    const startDay = dateStringDayKey(fmtDateKst(w.start))
    const endDay = dateStringDayKey(fmtDateKst(w.end))
    return startDay !== null && endDay !== null && endDay >= todayDayKey.value
      && startDay <= lastDay && isMyWatchAssignee(w.assignee)
  }).sort((a, b) => fmtDatetimeKst(a.start).localeCompare(fmtDatetimeKst(b.start)))
})

const dutyPeriods = computed(() => groupDutyPeriods(watchList.value.filter(w => isMyWatchAssignee(w.assignee))))
const upcomingDutyPeriod = computed(() => nextDutyPeriod(dutyPeriods.value, clockNow.value))

function watchShiftColor(startIso: string): string {
  return fmtDatetimeKst(startIso).slice(11, 13) === '12' ? '#7b1fa2' : '#1976d2'
}

function watchTime(startIso: string, endIso: string): string {
  const start = fmtDatetimeKst(startIso)
  const end = fmtDatetimeKst(endIso)
  const endDate = start.slice(0, 10) === end.slice(0, 10) ? '' : `${end.slice(5, 10).replace('-', '.')} `
  return `${start.slice(11)} ~ ${endDate}${end.slice(11)}`
}

const dutyCalendarItems = computed<CalendarDDay[]>(() => myWatchList.value.map(w => {
  const date = fmtDateKst(w.start)
  return {
    id: `duty-${w.id}`, date, title: `당직 ${watchTime(w.start, w.end)}`,
    color: watchShiftColor(w.start), daysLabel: calcDDay(date), note: w.assignee,
  }
}))

const calendarLoadError = computed(() => ddaysLoadFailed.value && watchLoadFailed.value
  ? '일부 일정을 불러오지 못했습니다.'
  : watchLoadFailed.value ? '당직 일정을 불러오지 못했습니다.' : 'D-Day를 불러오지 못했습니다.')

function retryCalendar() {
  if (ddaysLoadFailed.value) void loadDDays()
  if (watchLoadFailed.value) void loadWatch()
}

async function loadWatch() {
  if (watchLoading.value) return
  watchLoading.value = true
  watchLoadFailed.value = false
  try {
    const data = await loadDashboardDuties(async (params) => {
      const response = await api.get<DutyAssignment[]>('/watch', { params })
      return response.data
    }, isMyWatchAssignee, clockNow.value)
    if (!disposed) watchList.value = data
  } catch {
    if (!disposed) watchLoadFailed.value = true
  } finally {
    watchLoading.value = false
  }
}

// ── 서버 점검일 ────────────────────────────────────────────────────────────
const INSPECTION_KEY_PREFIX = '서버 점검일'
const inspectionPending = ref(0)
const inspectionLoadFailed = ref(false)
const canInspect = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('server_check'))
async function loadInspectionPending() {
  if (!canInspect.value) return
  try {
    const result = await getInspectionTasks(thisMonth())
    inspectionPending.value = result.items.filter(t => t.state === 'ACTIVE' && t.issue.status !== 'DONE' && t.issue.assigneeId === auth.me?.id).length
    inspectionLoadFailed.value = false
  } catch { inspectionLoadFailed.value = true }
}


function thirdThursdayOf(year: number, month: number): string {
  // month: 0-based
  let count = 0
  for (let d = 1; d <= 31; d++) {
    const dt = new Date(year, month, d)
    if (dt.getMonth() !== month) break
    if (dt.getDay() === 4) { // 4 = Thursday
      count++
      if (count === 3) {
        const mm = String(month + 1).padStart(2, '0')
        const dd = String(d).padStart(2, '0')
        return `${year}-${mm}-${dd}`
      }
    }
  }
  return ''
}

const inspectionOverrideKey = computed(() => {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${INSPECTION_KEY_PREFIX} ${y}-${m}`
})

const inspectionOverrideDDay = computed(() =>
  ddays.value.find((d) => d.title === inspectionOverrideKey.value)
)

const inspectionOverridden = computed(() => !!inspectionOverrideDDay.value)

const inspectionDate = computed(() =>
  inspectionOverrideDDay.value?.date ?? thirdThursdayOf(now.getFullYear(), now.getMonth())
)

const showInspectionDay = computed(() => {
  const date = inspectionDate.value
  if (!date) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const parts = date.split('-')
  const target = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return target >= today
})

function openInspectionEdit() {
  const existing = inspectionOverrideDDay.value
  ddayForm.value = {
    id: existing?.id ?? '',
    title: inspectionOverrideKey.value,
    date: inspectionDate.value,
    color: 'teal',
    note: existing?.note ?? '',
    visibleUserIds: existing?.visibleUserIds ?? [],
    visibleTeams: existing?.visibleTeams ?? [],
    visibleToAll: existing?.visibleToAll ?? true,
  }
  void loadDDayUsers()
  ddayDialog.value = true
}

function resetInspection() {
  const existing = inspectionOverrideDDay.value
  if (!existing) return
  confirmDeleteDDay(existing)
}

// ── D-Day ──────────────────────────────────────────────────────────────────
const ddays = ref<DDay[]>([])
const ddaysLoading = ref(false)
const ddaysLoadFailed = ref(false)
const ddayDialog = ref(false)
const ddaySaving = ref(false)
const ddayUsersLoading = ref(false)
const ddayCompletingId = ref<string | null>(null)
const ddayUsers = ref<DDayAudienceUser[]>([])
const ddayForm = ref({ id: '', title: '', date: '', color: 'blue', note: '', visibleUserIds: [] as string[], visibleTeams: [] as string[], visibleToAll: false })
const ddayTeamOptions = computed(() =>
  [...new Set(ddayUsers.value
    .map((user) => user.team?.trim())
    .filter((team): team is string => Boolean(team) && (auth.me?.isAdmin || team === auth.me?.team?.trim())))]
    .sort((left, right) => left.localeCompare(right, 'ko'))
    .map((team) => ({ value: team, label: team }))
)
const ddayUserOptions = computed(() =>
  ddayUsers.value
    .filter((user) => auth.me?.isAdmin || (auth.me?.team && user.team?.trim() === auth.me.team.trim()) || String(user.id) === String(auth.me?.id))
    .map((user) => ({
      value: user.id,
      label: `${user.fullName || user.email}${user.team ? ` (${user.team})` : ''}`,
    }))
)

const ddayColorMap: Record<string, string> = {
  red: '#b42318', orange: '#b54708', yellow: '#936000',
  green: '#067647', blue: '#175cd3', purple: '#6941c6',
  teal: '#067a6f', grey: '#475467',
}
const ddayColorOptions = Object.entries(ddayColorMap).map(([value]) => ({
  value,
  label: { red: '빨강', orange: '주황', yellow: '노랑', green: '초록', blue: '파랑', purple: '보라', teal: '청록', grey: '회색' }[value] ?? value,
}))

// dateStr 기준으로 오늘보다 daysAfter일 이상 지났으면 true
function isDatePast(dateStr: string, daysAfter: number): boolean {
  if (!dateStr) return false
  const targetDay = dateStringDayKey(dateStr)
  if (targetDay === null) return false
  return todayDayKey.value > targetDay + daysAfter * DAY_MS
}

// 서버 점검일 override key와 완료된 D-Day만 일반 목록에서 제외한다.
const visibleDDays = computed(() =>
  ddays.value.filter((d) => {
    if (d.title.startsWith(INSPECTION_KEY_PREFIX)) return false  // 서버 점검일 override는 목록에서 숨김
    return !d.completed
  })
)

// 이슈 추가 시 'D-Day 표시'를 체크한 내 담당 이슈 — 기한 당일까지 개인별로만 노출
// (/pm/dashboard/my-issues는 이미 미완료, assignee = 나로 필터링되어 옴)
const issueDDayItems = computed(() =>
  pmMyIssues.value
    .filter((i) => i.showOnDashboard && i.dueDate && !isDatePast(i.dueDate.slice(0, 10), 0))
    .map((i) => ({
      id: `issue-${i.id}`,
      title: `${i.projectKey ?? ''}-${i.number} ${i.title}`,
      date: (i.dueDate as string).slice(0, 10),
      issue: i,
    }))
)

const calendarDDays = computed<CalendarDDay[]>(() => {
  const events: CalendarDDay[] = visibleDDays.value.map(day => ({
    id: `dday-${day.id}`, title: day.title, date: day.date,
    color: ddayColorMap[day.color] ?? '#175cd3', daysLabel: calcDDay(day.date), note: day.note ?? null,
  }))
  if (showInspectionDay.value || inspectionPending.value > 0 || inspectionLoadFailed.value) {
    events.push({ id: 'inspection', title: '서버 점검일', date: inspectionDate.value, color: '#067a6f', daysLabel: calcDDay(inspectionDate.value),
      note: canInspect.value ? (inspectionLoadFailed.value ? '점검 작업을 확인해 주세요.' : `내 미완료 작업 ${inspectionPending.value}건`) : null })
  }
  events.push(...dutyCalendarItems.value)
  events.push(...issueDDayItems.value.map(day => ({
    id: day.id, title: day.title, date: day.date, color: '#3949ab', daysLabel: calcDDay(day.date),
  })))
  return events.filter(event => dateStringDayKey(event.date) !== null)
})

// Calendar popovers retain the actions previously available on the D-Day card.
function editableCalendarDDay(id: string): DDay | undefined {
  return visibleDDays.value.find(day => `dday-${day.id}` === id && (auth.me?.isAdmin || isDDayCreator(day)))
}

function editCalendarDDay(id: string) {
  const day = editableCalendarDDay(id)
  if (day) openDDayEdit(day)
}

function deleteCalendarDDay(id: string) {
  const day = editableCalendarDDay(id)
  if (day) confirmDeleteDDay(day)
}

function openCalendarIssue(id: string) {
  const item = issueDDayItems.value.find(day => day.id === id)
  if (item) openPmIssueDetail(item.issue)
}

function calcDDay(dateStr: string): string {
  const targetDay = dateStringDayKey(dateStr)
  if (targetDay === null) return ''
  const diff = Math.trunc((targetDay - todayDayKey.value) / DAY_MS)
  if (diff === 0) return 'D-Day'
  if (diff > 0) return `D-${diff}`
  return `D+${Math.abs(diff)}`
}

async function loadDDays() {
  ddaysLoading.value = true
  ddaysLoadFailed.value = false
  try {
    ddays.value = await fetchDDays()
  } catch {
    ddaysLoadFailed.value = true
  } finally {
    ddaysLoading.value = false
  }
}

function openDDayCreate(date = '') {
  ddayForm.value = { id: '', title: '', date, color: 'blue', note: '', visibleUserIds: [], visibleTeams: [], visibleToAll: false }
  void loadDDayUsers()
  ddayDialog.value = true
}

function openDDayEdit(d: DDay) {
  ddayForm.value = {
    id: d.id,
    title: d.title,
    date: d.date,
    color: d.color,
    note: d.note ?? '',
    visibleUserIds: d.visibleUserIds ?? [],
    visibleTeams: d.visibleTeams ?? [],
    visibleToAll: d.visibleToAll ?? false,
  }
  void loadDDayUsers()
  ddayDialog.value = true
}

async function loadDDayUsers() {
  if (ddayUsers.value.length > 0) {
    restrictDDayAudience()
    return
  }
  ddayUsersLoading.value = true
  try {
    ddayUsers.value = await fetchDDayAudience()
    restrictDDayAudience()
  } catch {
    $q.notify({ type: 'negative', message: '사용자 목록을 불러오지 못했습니다.' })
  } finally {
    ddayUsersLoading.value = false
  }
}

function restrictDDayAudience() {
  if (auth.me?.isAdmin) return
  const allowedTeams = new Set(ddayTeamOptions.value.map((option) => option.value))
  const allowedUsers = new Set(ddayUserOptions.value.map((option) => option.value))
  ddayForm.value.visibleTeams = ddayForm.value.visibleTeams.filter((team) => allowedTeams.has(team))
  ddayForm.value.visibleUserIds = ddayForm.value.visibleUserIds.filter((id) => allowedUsers.has(id))
}

async function saveDDay() {
  if (!ddayForm.value.title || !ddayForm.value.date) {
    $q.notify({ type: 'warning', message: '이름과 날짜는 필수입니다.' })
    return
  }
  ddaySaving.value = true
  try {
    const payload = {
      title: ddayForm.value.title,
      date: ddayForm.value.date,
      color: ddayForm.value.color,
      note: ddayForm.value.note || null,
      visible_user_ids: ddayForm.value.visibleUserIds,
      visible_teams: ddayForm.value.visibleTeams,
      visible_to_all: auth.me?.isAdmin === true && ddayForm.value.visibleToAll,
    }
    if (ddayForm.value.id) {
      await patchDDay(ddayForm.value.id, payload)
    } else {
      await createDDay(payload)
    }
    ddayDialog.value = false
    await loadDDays()
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장 실패' })
  } finally {
    ddaySaving.value = false
  }
}

function isDDayCreator(d: DDay): boolean {
  return !!auth.me?.id && String(auth.me.id) === d.createdBy
}

const canCompleteEditedDDay = computed(() => {
  if (!ddayForm.value.id || ddayForm.value.title.startsWith(INSPECTION_KEY_PREFIX)) return false
  const dday = ddays.value.find((item) => item.id === ddayForm.value.id)
  return !!dday && isDDayCreator(dday)
})

async function completeEditedDDay() {
  const dday = ddays.value.find((item) => item.id === ddayForm.value.id)
  if (dday) await completeDDay(dday)
}

async function completeDDay(d: DDay) {
  ddayCompletingId.value = d.id
  try {
    await completeDDayRequest(d.id)
    ddays.value = ddays.value.filter((item) => item.id !== d.id)
    if (ddayForm.value.id === d.id) ddayDialog.value = false
    $q.notify({ type: 'positive', message: 'D-Day를 완료 처리했습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: 'D-Day 완료 처리에 실패했습니다.' })
  } finally {
    ddayCompletingId.value = null
  }
}

function confirmDeleteDDay(d: DDay) {
  $q.dialog({
    title: 'D-Day 삭제',
    message: `"${d.title}"을(를) 삭제하시겠습니까?`,
    cancel: true,
    noBackdropDismiss: true, noRouteDismiss: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteDDay(d.id)
        ddays.value = ddays.value.filter((x) => x.id !== d.id)
        $q.notify({ type: 'positive', message: '삭제되었습니다.' })
      } catch {
        $q.notify({ type: 'negative', message: '삭제 실패' })
      }
    })()
  })
}

// ── 내 담당 미완료 일감 ──────────────────────────────────────────────────
const pmLoading = ref(false)
const pmLoadFailed = ref(false)
const pmMyIssues = ref<Issue[]>([])
const hasPmPerm = computed(() => auth.me?.isAdmin || (auth.me?.permissions ?? []).includes('pm'))
const pmDetailDialog = ref({ open: false, issue: null as Issue | null })

function openPmIssueDetail(issue: Issue) {
  pmDetailDialog.value = { open: true, issue }
}

async function loadPmDashboard() {
  if (pmLoading.value) return
  pmLoading.value = true
  pmLoadFailed.value = false
  try {
    const { data } = await api.get<Issue[]>('/pm/dashboard/my-issues')
    if (!disposed) pmMyIssues.value = data
  } catch {
    if (!disposed) pmLoadFailed.value = true
  } finally {
    pmLoading.value = false
  }
}

// ── 내 담당 SR ───────────────────────────────────────────────────────────
const srLoading = ref(false)
const srLoadFailed = ref(false)
const mySrList = ref<SRListItem[]>([])
const hasSrPerm = computed(() => auth.me?.isAdmin || (auth.me?.permissions ?? []).includes('sr'))
const hasSrWorkPerm = computed(() => hasSrPerm.value && (auth.me?.isAdmin
  || (auth.me?.permissions ?? []).some(permission => permission === 'sr_operator' || permission === 'sr_manager')))
const myWorkItems = computed(() => buildMyWork(pmMyIssues.value, mySrList.value, auth.me?.id?.toString(), todayISO.value))
const myWorkErrors = computed(() => [pmLoadFailed.value ? '담당 이슈' : '', srLoadFailed.value ? '담당 SR' : ''].filter(Boolean))

function openMyWork(item: MyWorkItem) {
  if (item.kind === 'issue') openPmIssueDetail(item.issue)
  else void router.push(`/pm/sr/${item.sr.id}`)
}

function retryMyWork() {
  if (pmLoadFailed.value) void loadPmDashboard()
  if (srLoadFailed.value) void loadAssignedSrs()
}

function refreshMyWork() {
  if (hasPmPerm.value) void loadPmDashboard()
  if (hasSrWorkPerm.value) void loadAssignedSrs()
}

async function loadAssignedSrs() {
  if (!hasSrWorkPerm.value || srLoading.value) return
  srLoading.value = true
  srLoadFailed.value = false
  try {
    const rows: SRListItem[] = []
    let skip = 0
    while (!disposed) {
      const page = await listAllSRs({ my_assigned: true, status: MY_WORK_SR_STATUSES.join(','), skip, limit: 200 })
      rows.push(...page.items)
      skip += page.items.length
      if (!page.items.length || skip >= page.total) break
    }
    if (!disposed) mySrList.value = rows
  } catch {
    if (!disposed) srLoadFailed.value = true
  } finally {
    srLoading.value = false
  }
}

// ── 대시보드 카드 순서 (드래그로 배치 변경, 계정에 저장) ──────────────────────
// 기본 카드는 설정을 읽기 전에도 바로 그려 빈 대시보드가 노출되지 않게 한다.
const cardOrder = ref<string[]>(['watch', 'dday', 'eos', 'resource'])
let savedAssetColPresets: ColPreset[] = []

const baseCardOrder = computed(() => {
  const order: string[] = []
  if (hasPmPerm.value || hasSrPerm.value) order.push('pm')
  // Keep the saved weeklyReport key so the expanded card retains its position and size.
  if (hasPmPerm.value || canInspect.value) order.push('weeklyReport')
  order.push('calendar')
  if (hasPmPerm.value) order.push('favorites')
  return order
})

async function loadCardOrder() {
  try {
    const prefs = await getPrefs()
    savedAssetColPresets = prefs.assetColPresets ?? []
    const layout = resolveDashboardLayout(prefs.dashboardCardOrder ?? [], prefs.dashboardCardSizes ?? {}, baseCardOrder.value)
    cardSizes.value = layout.sizes
    cardOrder.value = layout.order
  } catch {
    cardOrder.value = baseCardOrder.value
  }
}

async function saveCardOrder() {
  try {
    await savePrefs({ assetColPresets: savedAssetColPresets, dashboardCardOrder: cardOrder.value, dashboardCardSizes: cardSizes.value })
  } catch {
    $q.notify({ type: 'negative', message: '카드 배치를 저장하지 못했습니다. 다시 시도해 주세요.' })
  }
}

// ── 카드 크기 조절 (오른쪽 위 버튼으로 너비x높이를 3x3 그리드에서 선택, 계정에 저장) ──
// w, h는 각각 1~3 단계 (예: 2x2, 3x1 등 그리드 피커의 표기와 그대로 대응)
const DEFAULT_CARD_SIZE: Record<string, CardSize> = {
  calendar: { w: 2, h: 3 },
  favorites: { w: 1, h: 3 },
  weeklyReport: { w: 1, h: 2 },
  pm: { w: 2, h: 2 },
}
const cardSizes = ref<Record<string, CardSize>>({})

function sizeOf(id: string): CardSize {
  return cardSizes.value[id] ?? DEFAULT_CARD_SIZE[id] ?? { w: 1, h: 2 }
}

function cardSizeClasses(id: string): string[] {
  const s = sizeOf(id)
  return [`card-w-${s.w}`, `card-h-${s.h}`]
}

function setCardSize(id: string, w: number, h: number) {
  cardSizes.value = { ...cardSizes.value, [id]: { w, h } }
  void saveCardOrder()
}

onMounted(() => {
  dayRefreshInterval = window.setInterval(() => {
    const previousDutyId = upcomingDutyPeriod.value?.id
    clockNow.value = Date.now()
    const currentDay = calendarDayKey(new Date())
    if (currentDay !== todayDayKey.value) {
      todayDayKey.value = currentDay
      void loadWatch()
    } else if (previousDutyId !== upcomingDutyPeriod.value?.id) void loadWatch()
  }, 30_000)
  void loadDDays()
  void loadInspectionPending()
  void loadWatch()
  if (hasPmPerm.value) void loadPmDashboard()
  if (hasSrWorkPerm.value) void loadAssignedSrs()
  void loadCardOrder()
})

onUnmounted(() => {
  disposed = true
  if (dayRefreshInterval !== undefined) window.clearInterval(dayRefreshInterval)
})
</script>

<style scoped>
.dashboard-page {
  background: var(--bo-canvas);
}
.shortcuts-card .card-title { margin: 0; }
.shortcuts-body { display: flex; flex-direction: column; }
.shortcut-row { width: 100%; min-height: 64px; flex-shrink: 0; padding: 10px 8px; color: var(--bo-text); border-radius: 0; }
.shortcut-row + .shortcut-row { border-top: 1px solid var(--bo-border); }
.shortcut-row :deep(.q-btn__content) { width: 100%; display: flex; flex-wrap: nowrap; gap: 12px; text-align: left; }
.shortcut-copy { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 4px; }
.shortcut-title { font-size: 14px; line-height: 1.5; font-weight: 600; }
.shortcut-period { color: var(--bo-muted); font-size: 12px; line-height: 1.5; font-weight: 400; font-variant-numeric: tabular-nums; }
.shortcut-icon { flex-shrink: 0; color: var(--bo-accent-ink); }
.shortcut-arrow { flex-shrink: 0; color: var(--bo-muted); }
.shortcut-row:focus-visible { outline: 2px solid var(--bo-accent-ink) !important; outline-offset: -2px; }
/* The smallest saved size keeps all destinations visible as three compact links. */
.shortcuts-card.card-h-1 .card-header { margin-bottom: 8px; }
.shortcuts-card.card-h-1 .shortcuts-body { flex-direction: row; }
.shortcuts-card.card-h-1 .shortcut-row { flex: 1; min-width: 0; width: auto; min-height: 44px; padding: 4px; }
.shortcuts-card.card-h-1 .shortcut-row + .shortcut-row { border-top: 0; border-left: 1px solid var(--bo-border); }
.shortcuts-card.card-h-1 .shortcut-row :deep(.q-btn__content) { text-align: center; }
.shortcuts-card.card-h-1 .shortcut-icon,
.shortcuts-card.card-h-1 .shortcut-arrow,
.shortcuts-card.card-h-1 .shortcut-dates { display: none; }
.shortcuts-card.card-h-1 .shortcut-copy { gap: 2px; }
.dday-edit-card { width: min(420px, calc(100vw - 32px)); }

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: 140px;
  grid-auto-flow: dense;
  gap: 16px;
  max-width: 1600px;
  margin: 0 auto;
}

.card-drag-handle {
  cursor: grab;
}

.drag-ghost {
  opacity: 0.4;
  background: #eef1f8;
}

/* 카드 크기 조절 (헤더 오른쪽 위 버튼 → 3x3 그리드에서 너비x높이 선택) */
.card-w-1 { grid-column: span 1; }
.card-w-2 { grid-column: span 2; }
.card-w-3 { grid-column: span 3; }

/* 모든 카드가 높이 단계별로 동일한 고정 높이를 갖도록 통일 (grid-auto-rows: 140px 기준) */
.card-h-1 {
  grid-row: span 1;
  height: 140px;
  overflow-y: auto;
}

.card-h-2 {
  grid-row: span 2;
  height: 296px;
  overflow-y: auto;
}

.card-h-3 {
  grid-row: span 3;
  height: 452px;
  overflow-y: auto;
}

.dash-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--bo-border);
  padding: 20px;
  position: relative;
  isolation: isolate;
  min-width: 0;
}

.card-resize-btn {
  opacity: 0.55;
  transition: opacity 0.15s;
}

.card-resize-btn:hover {
  opacity: 1;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

/* 모든 대시보드 카드: sticky 대신 헤더를 스크롤 영역 밖으로 분리해서
   스크롤 시 내용이 헤더에 겹쳐 보이던 문제를 근본적으로 제거 */
.dash-card {
  display: flex;
  flex-direction: column;
}

.dash-card.card-h-1,
.dash-card.card-h-2,
.dash-card.card-h-3 {
  overflow: hidden;
}

.dash-card-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--bo-text);
  line-height: 1.45;
}
.dashboard-page :deep(.q-badge.bg-blue-4),
.dashboard-page :deep(.q-badge.bg-blue-5),
.dashboard-page :deep(.q-badge.bg-cyan-7) { background: #eff8ff !important; color: #175cd3 !important; }
.dashboard-page :deep(.q-badge.bg-orange),
.dashboard-page :deep(.q-badge.bg-orange-5),
.dashboard-page :deep(.q-badge.bg-orange-6),
.dashboard-page :deep(.q-badge.bg-amber-7) { background: #fffaeb !important; color: #93370d !important; }
.dashboard-page :deep(.q-badge.bg-green-6),
.dashboard-page :deep(.q-badge.bg-teal-6) { background: #ecfdf3 !important; color: #027a48 !important; }
.dashboard-page :deep(.q-badge.bg-grey-5) { background: #f2f4f7 !important; color: #475467 !important; }
.dashboard-page :deep(.q-badge.bg-red-6) { background: #fef3f2 !important; color: #b42318 !important; }
.dashboard-page :deep(.text-orange) { color: #93370d !important; }

.dday-visible-people-select {
  margin-bottom: 16px;
}

.dday-visible-people-select :deep(.q-field__messages) {
  white-space: pre-line;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .card-w-1 { grid-column: span 1; }
  .card-w-2,
  .card-w-3 {
    grid-column: span 2;
  }
}

@media (max-width: 600px) {
  .dash-card { padding: 16px; }
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .card-w-1,
  .card-w-2,
  .card-w-3 {
    grid-column: span 1;
  }
}
</style>
