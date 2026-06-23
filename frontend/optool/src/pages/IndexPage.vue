<template>
  <q-page class="dashboard-page q-pa-md">

    <div class="dashboard-grid">

      <!-- 내 정보 -->
      <div class="dash-card profile-card">
        <div class="card-header">
          <q-icon name="person" size="18px" color="blue-7" />
          <span class="card-title">내 정보</span>
        </div>
        <div class="profile-body">
          <div class="profile-avatar">
            <q-icon name="account_circle" size="56px" color="blue-3" />
          </div>
          <div class="profile-info">
            <div class="profile-name">{{ auth.me?.fullName || auth.me?.email }}</div>
            <div class="profile-email text-grey-6">{{ auth.me?.email }}</div>
            <div class="profile-badges q-mt-sm">
              <q-badge v-if="auth.me?.isAdmin" color="deep-purple" label="관리자" class="q-mr-xs" />
              <q-badge
                v-for="perm in (auth.me?.permissions ?? [])"
                :key="perm"
                color="blue-grey"
                :label="perm"
                class="q-mr-xs q-mb-xs"
                outline
              />
            </div>
          </div>
        </div>
      </div>

      <!-- D-Day -->
      <div class="dash-card dday-card">
        <div class="card-header">
          <q-icon name="event" size="18px" color="red-7" />
          <span class="card-title">D-Day</span>
          <q-space />
          <q-btn v-if="auth.me?.isAdmin" flat dense round icon="add" size="sm" color="grey-7" @click="openDDayCreate" />
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
      <div class="dash-card eos-card">
        <div class="card-header">
          <q-icon name="warning" size="18px" color="deep-orange-7" />
          <span class="card-title">서버 EoS 현황</span>
          <q-space />
          <q-btn flat dense round icon="open_in_new" size="sm" color="grey-6" @click="$router.push('/asset/list')" />
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

      <!-- 이번 달 당직 일정 -->
      <div class="dash-card watch-card">
        <div class="card-header">
          <q-icon name="schedule" size="18px" color="orange-7" />
          <span class="card-title">이번 달 당직 일정</span>
          <q-space />
          <span class="text-caption text-grey-6">{{ currentMonthLabel }}</span>
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

    </div>

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
import { useAuthStore } from 'stores/auth'
import { api } from 'boot/axios'
import { fetchDDays, createDDay, patchDDay, deleteDDay, type DDay } from 'src/services/ddays'

const auth = useAuthStore()
const $q = useQuasar()

// ── 당직 일정 ──────────────────────────────────────────────────────────────
interface WatchItem { id: string; assignee: string; start: string; end: string }
const watchLoading = ref(false)
const watchList = ref<WatchItem[]>([])

const now = new Date()
const currentMonthLabel = `${now.getFullYear()}년 ${now.getMonth() + 1}월`

const myWatchList = computed(() => {
  const fullName = (auth.me?.fullName || '').trim()
  const email = (auth.me?.email || '').trim()
  if (!fullName && !email) return []
  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0)
  return watchList.value.filter((w) => {
    const assignee = (w.assignee || '').trim()
    if (!assignee) return false
    // 이미 종료된 당직 제외 (end가 오늘 자정 이전이면 제외)
    if (new Date(w.end) < todayStart) return false
    // 이메일 일치
    if (email && assignee === email) return true
    // 이름 포함 여부 (양방향)
    if (fullName) {
      if (assignee.includes(fullName) || fullName.includes(assignee)) return true
    }
    return false
  })
})


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

onMounted(() => {
  void loadDDays()
  void loadWatch()
  void loadEosSummary()
})
</script>

<style scoped>
.dashboard-page {
  background: #f4f6f9;
  min-height: 100vh;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 1000px;
  margin: 0 auto;
}

.dash-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8edf5;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a237e;
}

/* 내 정보 */
.profile-body {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.profile-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a237e;
}

.profile-email {
  font-size: 13px;
  margin-top: 2px;
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

/* 당직 */
.watch-card {
  grid-column: 1 / -1;
}

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

@media (max-width: 600px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .watch-card,
  .eos-card {
    grid-column: 1;
  }
}
</style>
