<template>
  <q-page class="dashboard-page q-pa-md">

    <draggable
      v-model="cardOrder"
      :item-key="(id: string) => id"
      class="dashboard-grid"
      handle=".card-drag-handle"
      ghost-class="drag-ghost"
      @end="saveCardOrder"
    >
      <template #item="{ element: cardId }">

      <!-- D-Day -->
      <div v-if="cardId === 'dday'" class="dash-card dday-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="event" size="18px" color="red-7" />
          <span class="card-title">D-Day</span>
          <q-space />
          <q-btn v-if="auth.me?.isAdmin" flat dense round icon="add" size="sm" color="grey-7" @click="openDDayCreate" />
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

        <!-- 서버 점검일 (정기: 3번째 목요일) — D-Day 지나면 숨김 -->
        <div v-if="showInspectionDay" class="dday-item dday-item--inspection q-mb-sm">
          <div class="dday-count" style="background: #00897b">
            <span class="dday-label">{{ calcDDay(inspectionDate) }}</span>
          </div>
          <div class="dday-info">
            <div class="dday-title">
              서버 점검일
              <q-badge outline color="teal" label="정기" class="q-ml-xs" style="font-size:10px" />
            </div>
            <div class="dday-date text-grey-6">{{ inspectionDate }}{{ inspectionOverridden ? ' (수정됨)' : ' (3번째 목요일)' }}</div>
          </div>
          <div v-if="auth.me?.isAdmin" class="dday-actions">
            <q-btn flat dense round icon="edit" size="xs" color="grey" @click="openInspectionEdit" />
            <q-btn v-if="inspectionOverridden" flat dense round icon="refresh" size="xs" color="grey" title="자동 계산으로 초기화" @click="resetInspection" />
          </div>
        </div>

        <!-- 다음 당직일 — 14일 이내로 다가왔을 때만 표시 -->
        <div v-if="showDutyDDay && nextDutyDay" class="dday-item dday-item--inspection q-mb-sm">
          <div class="dday-count" style="background: #7b1fa2">
            <span class="dday-label">{{ calcDDay(nextDutyDay.date) }}</span>
          </div>
          <div class="dday-info">
            <div class="dday-title">
              당직일
              <q-badge outline color="purple" label="당직" class="q-ml-xs" style="font-size:10px" />
            </div>
            <div class="dday-date text-grey-6">{{ nextDutyDay.date }}</div>
          </div>
        </div>

        <div v-if="ddaysLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
        <div v-if="!ddaysLoading && visibleDDays.length > 0" class="dday-list">
          <div
            v-for="d in visibleDDays"
            :key="d.id"
            class="dday-item"
          >
            <div class="dday-count" :style="{ background: ddayColorMap[d.color] ?? '#1e88e5' }">
              <span class="dday-label">{{ calcDDay(d.date) }}</span>
            </div>
            <div class="dday-info">
              <div class="dday-title">{{ d.title }}</div>
              <div class="dday-date text-grey-6">{{ d.date }}</div>
              <div v-if="d.note" class="dday-note text-grey-5">{{ d.note }}</div>
            </div>
            <div v-if="auth.me?.isAdmin" class="dday-actions">
              <q-btn flat dense round icon="edit" size="xs" color="grey" @click="openDDayEdit(d)" />
              <q-btn flat dense round icon="delete" size="xs" color="negative" @click="confirmDeleteDDay(d)" />
            </div>
          </div>
        </div>
      </div>

      <!-- EoS 현황 -->
      <div v-else-if="cardId === 'eos'" class="dash-card eos-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="warning" size="18px" color="deep-orange-7" />
          <span class="card-title">서버 EoS 현황</span>
          <q-space />
          <q-btn flat dense round icon="open_in_new" size="sm" color="grey-6" @click="$router.push('/asset/list')" />
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

        <div v-if="eosLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
        <div v-else class="eos-summary">
          <!-- 카운트 요약 -->
          <div class="eos-counts">
            <div class="eos-count-item eos-count--danger" @click="eosTab = 'eos'">
              <div class="eos-count-num">{{ eosSummary.eosCount }}</div>
              <div class="eos-count-label">EoS된 장비</div>
            </div>
            <div class="eos-count-item eos-count--warn" @click="eosTab = 'soon'">
              <div class="eos-count-num">{{ eosSummary.soonCount }}</div>
              <div class="eos-count-label">1년 내 EoS 예정</div>
            </div>
          </div>

          <!-- 탭 목록 -->
          <div class="eos-tab-btns q-mt-sm">
            <q-btn flat dense :color="eosTab === 'eos' ? 'negative' : 'grey'" size="sm" label="EoS 목록" @click="eosTab = 'eos'" />
            <q-btn flat dense :color="eosTab === 'soon' ? 'orange' : 'grey'" size="sm" label="예정 목록" @click="eosTab = 'soon'" />
          </div>

          <div class="eos-list q-mt-xs">
            <div v-if="currentEosList.length === 0" class="text-grey text-caption text-center q-pa-sm">해당 장비가 없습니다.</div>
            <div v-for="a in currentEosList" :key="a.id" class="eos-item">
              <q-icon :name="eosTab === 'eos' ? 'cancel' : 'schedule'" :color="eosTab === 'eos' ? 'negative' : 'orange'" size="16px" />
              <div class="eos-item-info">
                <span class="eos-item-name">{{ a.name }}</span>
                <span class="eos-item-os text-grey-6">{{ a.os }}{{ a.version ? ` ${a.version}` : '' }}</span>
              </div>
              <span class="eos-item-date" :class="eosTab === 'eos' ? 'text-negative' : 'text-orange'">{{ a.eosDate }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 서버 리소스 위험 현황 -->
      <div v-else-if="cardId === 'resource'" class="dash-card resource-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="memory" size="18px" color="red-7" />
          <span class="card-title">서버 리소스 위험 현황</span>
          <q-space />
          <span v-if="dangerReport.reportDate" class="text-caption text-grey-6">{{ dangerReport.reportDate }} 기준</span>
          <q-btn flat dense round icon="open_in_new" size="sm" color="grey-6" @click="$router.push('/inspection/health-summary')" />
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
        <div v-if="dangerLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
        <div v-else-if="dangerReport.servers.length === 0" class="text-center text-grey text-caption q-pa-md">위험 수치 서버가 없습니다.</div>
        <div v-else class="resource-list">
          <div v-for="s in dangerReport.servers" :key="s.ip" class="resource-item">
            <div class="resource-name">{{ s.hostName || s.ip }}</div>
            <div class="resource-badges">
              <q-badge
                :color="s.ramPct >= 90 ? 'negative' : 'orange'"
                class="q-mr-xs"
              >RAM {{ s.ram }}</q-badge>
              <q-badge
                :color="s.diskPct >= 90 ? 'negative' : 'orange'"
              >Disk {{ s.diskMax }}</q-badge>
            </div>
          </div>
        </div>
      </div>

      <!-- 스케줄 관리: 담당 중 -->
      <div v-else-if="cardId === 'pm'" class="dash-card pm-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="fa-solid fa-diagram-project" size="18px" color="indigo-7" />
          <span class="card-title">스케줄 관리 — 담당 중</span>
          <q-space />
          <q-btn flat dense round icon="open_in_new" size="sm" color="grey-6" @click="$router.push(hasPmPerm ? '/pm/dashboard' : '/pm/sr/my')" />
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

        <div v-if="hasPmPerm" class="pm-subsection">
          <div class="pm-subheader">담당 이슈</div>
          <div v-if="pmLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
          <div v-else-if="pmMyIssues.length === 0" class="text-center text-grey text-caption q-pa-md">담당 중인 이슈가 없습니다.</div>
          <div v-else class="pm-issue-list">
            <div
              v-for="issue in pmMyIssues"
              :key="issue.id"
              class="pm-issue-item"
              @click="$router.push('/pm/dashboard')"
            >
              <span class="pm-issue-key">{{ issue.projectKey }}-{{ issue.number }}</span>
              <span class="pm-issue-title">{{ issue.title }}</span>
              <q-badge :color="STATUS_COLOR[issue.status]" :label="STATUS_LABEL[issue.status]" />
            </div>
          </div>
        </div>

        <div v-if="hasSrPerm" class="pm-subsection" :class="{ 'q-mt-md': hasPmPerm }">
          <div class="pm-subheader">내 SR 목록</div>
          <div v-if="srLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
          <div v-else-if="mySrList.length === 0" class="text-center text-grey text-caption q-pa-md">접수한 SR이 없습니다.</div>
          <div v-else class="pm-issue-list">
            <div
              v-for="sr in mySrList"
              :key="sr.id"
              class="pm-issue-item"
              @click="$router.push(`/pm/sr/${sr.id}`)"
            >
              <span class="pm-issue-key">{{ sr.srNo }}</span>
              <span class="pm-issue-title">{{ sr.title }}</span>
              <q-badge :color="SR_STATUS_COLOR[sr.status]" :label="SR_STATUS_LABEL[sr.status]" />
            </div>
          </div>
        </div>
      </div>

      <!-- 이번 달 당직 일정 -->
      <div v-else-if="cardId === 'watch'" class="dash-card watch-card" :class="cardSizeClasses(cardId)">
        <div class="card-header">
          <q-icon name="drag_indicator" class="card-drag-handle cursor-grab" color="grey-4" size="16px" />
          <q-icon name="schedule" size="18px" color="orange-7" />
          <span class="card-title">이번 달 당직 일정</span>
          <q-space />
          <span class="text-caption text-grey-6">{{ currentMonthLabel }}</span>
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

        <div v-if="watchLoading" class="text-center text-grey q-pa-md">불러오는 중...</div>
        <div v-else-if="myWatchList.length === 0" class="text-center text-grey text-caption q-pa-md">이번 달 당직 일정이 없습니다.</div>
        <div v-else class="watch-cards">
          <div v-for="w in myWatchList" :key="w.id" class="watch-card-item">
            <div class="watch-card-date" :style="{ background: watchShiftColor(w.start) }">
              <div class="watch-card-month">{{ new Date(w.start).getMonth() + 1 }}월</div>
              <div class="watch-card-day">{{ new Date(w.start).getDate() }}</div>
              <div class="watch-card-dow">{{ ['일','월','화','수','목','금','토'][new Date(w.start).getDay()] }}</div>
            </div>
            <div class="watch-card-body" :style="{ background: watchShiftColor(w.start) + '18' }">
              <div class="watch-card-name">{{ w.assignee }}</div>
              <div class="watch-card-time" :style="{ color: watchShiftColor(w.start) }">
                <q-icon name="schedule" size="12px" />
                {{ watchTime(w.start, w.end) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      </template>
    </draggable>

    <!-- D-Day 추가/수정 다이얼로그 -->
    <q-dialog v-model="ddayDialog" persistent>
      <q-card style="min-width: 340px">
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
          <q-input v-model="ddayForm.note" outlined dense label="메모" type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="ddaySaving" @click="saveDDay" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import draggable from 'vuedraggable'
import { useAuthStore } from 'stores/auth'
import { api } from 'boot/axios'
import { fetchDDays, createDDay, patchDDay, deleteDDay, type DDay } from 'src/services/ddays'
import { STATUS_LABEL, STATUS_COLOR, type Issue } from 'src/services/pm/issue'
import { listMySRs, SR_STATUS_LABEL, SR_STATUS_COLOR, type SRListItem } from 'src/services/sr'
import { getPrefs, savePrefs, type ColPreset, type CardSize } from 'src/services/prefs'
import CardSizePicker from 'src/components/CardSizePicker.vue'

const auth = useAuthStore()
const $q = useQuasar()

// ── 당직 일정 ──────────────────────────────────────────────────────────────
interface WatchItem { id: string; assignee: string; start: string; end: string }
const watchLoading = ref(false)
const watchList = ref<WatchItem[]>([])

const now = new Date()
const currentMonthLabel = `${now.getFullYear()}년 ${now.getMonth() + 1}월`

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
  if (!auth.me?.fullName && !auth.me?.email) return []
  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0)
  return watchList.value.filter((w) => {
    // 이미 종료된 당직 제외 (end가 오늘 자정 이전이면 제외)
    if (new Date(w.end) < todayStart) return false
    return isMyWatchAssignee(w.assignee)
  })
})

// 다음 당직일 D-Day (월 경계와 무관하게 가장 가까운 미래 당직을 찾기 위해 별도 조회)
const nextDutyDay = ref<{ date: string } | null>(null)

const showDutyDDay = computed(() => {
  if (!nextDutyDay.value) return false
  const target = new Date(nextDutyDay.value.date); target.setHours(0, 0, 0, 0)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  return diff >= 0 && diff <= 14
})

async function loadNextDutyDay() {
  try {
    const start = new Date(); start.setHours(0, 0, 0, 0)
    const end = new Date(start); end.setDate(end.getDate() + 45)
    const { data } = await api.get<WatchItem[]>('/watch', { params: { start: start.toISOString(), end: end.toISOString() } })
    const mine = data
      .filter((w) => new Date(w.end) >= start && isMyWatchAssignee(w.assignee))
      .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
    nextDutyDay.value = mine.length ? { date: mine[0]!.start.substring(0, 10) } : null
  } catch {
    nextDutyDay.value = null
  }
}


function watchShiftColor(startIso: string): string {
  const hour = (new Date(startIso).getUTCHours() + 9) % 24
  if (hour === 11) return '#1976d2' // A타임
  if (hour === 12) return '#7b1fa2' // B타임
  return '#1976d2'
}

function watchTime(startIso: string, endIso: string): string {
  const toKSTHour = (iso: string) => (new Date(iso).getUTCHours() + 9) % 24
  const fmt = (iso: string) => {
    const h = toKSTHour(iso)
    return `${String(h).padStart(2, '0')}:00`
  }
  return `${fmt(startIso)}~${fmt(endIso)}`
}

async function loadWatch() {
  watchLoading.value = true
  try {
    const y = now.getFullYear()
    const m = now.getMonth()
    const start = new Date(y, m, 1).toISOString()
    const end = new Date(y, m + 1, 0, 23, 59, 59).toISOString()
    const { data } = await api.get<WatchItem[]>('/watch', { params: { start, end } })
    watchList.value = data
  } catch {
    watchList.value = []
  } finally {
    watchLoading.value = false
  }
}

// ── 서버 점검일 ────────────────────────────────────────────────────────────
const INSPECTION_KEY_PREFIX = '서버 점검일'

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
  }
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
const ddayDialog = ref(false)
const ddaySaving = ref(false)
const ddayForm = ref({ id: '', title: '', date: '', color: 'blue', note: '' })

const ddayColorMap: Record<string, string> = {
  red: '#e53935', orange: '#fb8c00', yellow: '#f9a825',
  green: '#43a047', blue: '#1e88e5', purple: '#8e24aa',
  teal: '#00897b', grey: '#757575',
}
const ddayColorOptions = Object.entries(ddayColorMap).map(([value]) => ({
  value,
  label: { red: '빨강', orange: '주황', yellow: '노랑', green: '초록', blue: '파랑', purple: '보라', teal: '청록', grey: '회색' }[value] ?? value,
}))

// dateStr 기준으로 오늘보다 daysAfter일 이상 지났으면 true
function isDatePast(dateStr: string, daysAfter: number): boolean {
  if (!dateStr) return false
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((today.getTime() - target.getTime()) / 86400000)
  return diff > daysAfter
}

// 서버 점검일 override key가 아닌 것만, 2주 초과 지난 것 제외
const visibleDDays = computed(() =>
  ddays.value.filter((d) => {
    if (d.title.startsWith(INSPECTION_KEY_PREFIX)) return false  // 서버 점검일 override는 목록에서 숨김
    return !isDatePast(d.date, 14)
  })
)

function calcDDay(dateStr: string): string {
  const target = new Date(dateStr)
  target.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return 'D-Day'
  if (diff > 0) return `D-${diff}`
  return `D+${Math.abs(diff)}`
}

async function loadDDays() {
  ddaysLoading.value = true
  try {
    ddays.value = await fetchDDays()
  } finally {
    ddaysLoading.value = false
  }
}

function openDDayCreate() {
  ddayForm.value = { id: '', title: '', date: '', color: 'blue', note: '' }
  ddayDialog.value = true
}

function openDDayEdit(d: DDay) {
  ddayForm.value = { id: d.id, title: d.title, date: d.date, color: d.color, note: d.note ?? '' }
  ddayDialog.value = true
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

function confirmDeleteDDay(d: DDay) {
  $q.dialog({
    title: 'D-Day 삭제',
    message: `"${d.title}"을(를) 삭제하시겠습니까?`,
    cancel: true,
    persistent: true,
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

// ── EoS 현황 ───────────────────────────────────────────────────────────────
interface EosAsset { id: string; name: string; ip: string; category: string; os: string; version: string; eosDate: string }
interface EosSummary { eosCount: number; soonCount: number; eosAssets: EosAsset[]; soonAssets: EosAsset[] }
const eosLoading = ref(false)
const eosTab = ref<'eos' | 'soon'>('eos')
const eosSummary = ref<EosSummary>({ eosCount: 0, soonCount: 0, eosAssets: [], soonAssets: [] })

const currentEosList = computed(() =>
  eosTab.value === 'eos' ? eosSummary.value.eosAssets : eosSummary.value.soonAssets
)

async function loadEosSummary() {
  eosLoading.value = true
  try {
    const { data } = await api.get<{ eosCount: number; soonCount: number; eosAssets: Record<string, string>[]; soonAssets: Record<string, string>[] }>('/assets/eos-summary')
    const toAsset = (a: Record<string, string>): EosAsset => ({
      id: a['id'] ?? '', name: a['name'] ?? '', ip: a['ip'] ?? '',
      category: a['category'] ?? '', os: a['os'] ?? '', version: a['version'] ?? '',
      eosDate: a['eosDate'] ?? '',
    })
    eosSummary.value = {
      eosCount: data.eosCount,
      soonCount: data.soonCount,
      eosAssets: data.eosAssets.map(toAsset),
      soonAssets: data.soonAssets.map(toAsset),
    }
  } catch {
    // ignore
  } finally {
    eosLoading.value = false
  }
}

// ── 서버 리소스 위험 현황 ────────────────────────────────────────────────────
interface DangerServer { hostName: string; ip: string; ram: string; diskMax: string; ramPct: number; diskPct: number }
interface DangerReport { reportDate: string | null; servers: DangerServer[] }
const dangerLoading = ref(false)
const dangerReport = ref<DangerReport>({ reportDate: null, servers: [] })

async function loadDangerSummary() {
  dangerLoading.value = true
  try {
    const { data } = await api.get<DangerReport>('/health-reports/danger')
    dangerReport.value = data
  } catch {
    // ignore
  } finally {
    dangerLoading.value = false
  }
}

// ── 스케줄 관리(PM) 담당 중 ──────────────────────────────────────────────────
const pmLoading = ref(false)
const pmMyIssues = ref<Issue[]>([])
const hasPmPerm = computed(() => auth.me?.isAdmin || (auth.me?.permissions ?? []).includes('pm'))

async function loadPmDashboard() {
  pmLoading.value = true
  try {
    const { data } = await api.get<{ myIssues: Issue[] }>('/pm/dashboard')
    pmMyIssues.value = data.myIssues
  } catch {
    pmMyIssues.value = []
  } finally {
    pmLoading.value = false
  }
}

// ── 내 SR 목록 ───────────────────────────────────────────────────────────
const srLoading = ref(false)
const mySrList = ref<SRListItem[]>([])
const hasSrPerm = computed(() => auth.me?.isAdmin || (auth.me?.permissions ?? []).includes('sr'))

// 대시보드 "내 SR 목록"은 처리 완료/최종 완료 건은 노출하지 않음
// (담당 이슈 목록은 백엔드에서 DONE 제외 후 내려오므로 여기서 SR만 별도 필터)
const DASHBOARD_HIDDEN_SR_STATUSES = new Set(['COMPLETED', 'CLOSED'])

async function loadMySrList() {
  srLoading.value = true
  try {
    const list = await listMySRs()
    mySrList.value = list.filter((sr) => !DASHBOARD_HIDDEN_SR_STATUSES.has(sr.status))
  } catch {
    mySrList.value = []
  } finally {
    srLoading.value = false
  }
}

// ── 대시보드 카드 순서 (드래그로 배치 변경, 계정에 저장) ──────────────────────
const cardOrder = ref<string[]>([])
let savedAssetColPresets: ColPreset[] = []

const baseCardOrder = computed(() => {
  const order = ['watch', 'dday', 'eos', 'resource']
  if (hasPmPerm.value || hasSrPerm.value) order.push('pm')
  return order
})

// 저장된 순서에서 더 이상 존재/노출되지 않는 카드는 제거하고, 새로 생긴 카드는 뒤에 추가
function reconcileCardOrder(saved: string[], base: string[]): string[] {
  const kept = saved.filter((id) => base.includes(id))
  const missing = base.filter((id) => !kept.includes(id))
  return [...kept, ...missing]
}

async function loadCardOrder() {
  try {
    const prefs = await getPrefs()
    savedAssetColPresets = prefs.assetColPresets ?? []
    cardSizes.value = prefs.dashboardCardSizes ?? {}
    cardOrder.value = prefs.dashboardCardOrder?.length
      ? reconcileCardOrder(prefs.dashboardCardOrder, baseCardOrder.value)
      : baseCardOrder.value
  } catch {
    cardOrder.value = baseCardOrder.value
  }
}

async function saveCardOrder() {
  try {
    await savePrefs({ assetColPresets: savedAssetColPresets, dashboardCardOrder: cardOrder.value, dashboardCardSizes: cardSizes.value })
  } catch {
    // 저장 실패해도 화면 배치는 유지되므로 조용히 무시
  }
}

// ── 카드 크기 조절 (오른쪽 위 버튼으로 너비x높이를 3x3 그리드에서 선택, 계정에 저장) ──
// w, h는 각각 1~3 단계 (예: 2x2, 3x1 등 그리드 피커의 표기와 그대로 대응)
const DEFAULT_CARD_SIZE: Record<string, CardSize> = {
  dday: { w: 1, h: 2 },
  eos: { w: 1, h: 2 },
  resource: { w: 1, h: 2 },
  pm: { w: 3, h: 2 },
  watch: { w: 3, h: 2 },
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
  void loadDDays()
  void loadWatch()
  void loadNextDutyDay()
  void loadEosSummary()
  void loadDangerSummary()
  if (hasPmPerm.value) void loadPmDashboard()
  if (hasSrPerm.value) void loadMySrList()
  void loadCardOrder()
})
</script>

<style scoped>
.dashboard-page {
  background: #f4f6f9;
  min-height: 100vh;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  border: 1px solid #e8edf5;
  padding: 20px;
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
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a237e;
}

/* D-Day */
.dday-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dday-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8f9fc;
}

.dday-count {
  min-width: 64px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.dday-label {
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.dday-title {
  font-size: 14px;
  font-weight: 600;
  color: #263238;
}

.dday-date {
  font-size: 12px;
  margin-top: 2px;
}

.dday-note {
  font-size: 11px;
  margin-top: 2px;
}

.dday-info {
  flex: 1;
}

.dday-actions {
  display: flex;
  gap: 2px;
}

/* EoS */
.eos-counts {
  display: flex;
  gap: 12px;
}

.eos-count-item {
  flex: 1;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  cursor: pointer;
  transition: opacity 0.15s;
}

.eos-count-item:hover { opacity: 0.85; }

.eos-count--danger { background: #fff3f3; border: 1px solid #ffcdd2; }
.eos-count--warn   { background: #fff8f0; border: 1px solid #ffe0b2; }

.eos-count-num {
  font-size: 28px;
  font-weight: 800;
}

.eos-count--danger .eos-count-num { color: #c62828; }
.eos-count--warn   .eos-count-num { color: #e65100; }

.eos-count-label {
  font-size: 11px;
  color: #78909c;
  margin-top: 2px;
}

.eos-tab-btns {
  display: flex;
  gap: 4px;
}

.eos-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.eos-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #f8f9fc;
  font-size: 13px;
}

.eos-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.eos-item-name { font-weight: 600; color: #263238; }
.eos-item-os   { font-size: 11px; }
.eos-item-date { font-size: 12px; font-weight: 600; white-space: nowrap; }

/* 리소스 위험 */
.resource-card {
  display: flex;
  flex-direction: column;
}

.resource-list {
  max-height: 310px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  min-height: 0;
}

.resource-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: 7px;
  background: #fff8f8;
  border: 1px solid #ffcdd2;
}

.resource-name {
  font-size: 13px;
  font-weight: 600;
  color: #263238;
}

.resource-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* 스케줄 관리 */
.pm-subheader {
  font-size: 12px;
  font-weight: 700;
  color: #78909c;
  margin-bottom: 6px;
}

.pm-issue-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pm-issue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 7px;
  background: #f8f9fc;
  cursor: pointer;
  transition: background 0.15s;
}

.pm-issue-item:hover {
  background: #eef1f8;
}

.pm-issue-key {
  font-size: 12px;
  font-weight: 700;
  color: #3949ab;
  flex-shrink: 0;
}

.pm-issue-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 당직 */
.watch-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  max-height: 260px;
  overflow-y: auto;
}

.watch-card-item {
  display: flex;
  align-items: stretch;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
  min-width: 160px;
  flex: 1 1 160px;
  max-width: 220px;
}

.watch-card-date {
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 10px 14px;
  min-width: 52px;
}

.watch-card-month {
  font-size: 10px;
  font-weight: 600;
  opacity: 0.85;
  line-height: 1;
}

.watch-card-day {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
}

.watch-card-dow {
  font-size: 11px;
  opacity: 0.85;
  line-height: 1;
}

.watch-card-body {
  flex: 1;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.watch-card-name {
  font-size: 14px;
  font-weight: 700;
  color: #263238;
}

.watch-card-time {
  font-size: 12px;
  color: #e65100;
  display: flex;
  align-items: center;
  gap: 3px;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .card-w-1,
  .card-w-2,
  .card-w-3 {
    grid-column: span 2;
  }
}

@media (max-width: 600px) {
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
