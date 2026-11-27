<template>
  <q-page class="q-pa-md bo-page work-status-page">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="row items-center bo-page-heading">
          <div class="col">
            <div role="heading" aria-level="1" class="text-h5 text-weight-bold bo-page-title">업무 현황</div>
            <div class="text-caption text-grey-6 bo-page-description">담당자별 업무 일정 현황</div>
          </div>
          <HelpButton feature="work-status" guide-path="/pm/schedule/guide" />
        </div>
      </div>

      <!-- 캘린더와 필터 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section class="work-status-filters">
            <ProjectFilter v-model="selectedProjectId" :issues="allIssues" class="work-status-select" />
            <div class="work-status-assignees" role="group" aria-label="담당자 필터">
              <button type="button" class="assignee-toggle" :class="{ 'assignee-toggle--active': selectedIds.size === 0 }"
                :aria-pressed="selectedIds.size === 0" @click="clearAssignees">
                <span class="assignee-name">전체 담당자</span>
                <q-icon name="check" size="14px" class="assignee-check" aria-hidden="true" />
              </button>
              <button v-for="assignee in assigneeFilters" :key="assignee.id" type="button" class="assignee-toggle"
                :class="{ 'assignee-toggle--active': selectedIds.has(assignee.id) }"
                :aria-pressed="selectedIds.has(assignee.id)" @click="toggleAssignee(assignee.id)">
                <span class="assignee-color" :style="{ backgroundColor: getAssigneeColor(assignee.id) }" aria-hidden="true" />
                <span class="assignee-name">{{ assignee.name }}</span>
                <q-icon name="check" size="14px" class="assignee-check" aria-hidden="true" />
              </button>
            </div>
            <q-btn v-if="hasFilters" flat dense no-caps icon="restart_alt" label="초기화" aria-label="프로젝트와 담당자 필터 초기화"
              class="work-status-reset" @click="resetFilters" />
          </q-card-section>
          <q-separator />
          <q-card-section>
            <div v-if="loading || loadFailed || (hasFilters && !filteredEvents.length)" class="work-status-notice" role="status">
              <span>{{ loading ? '일정을 불러오는 중입니다.' : loadFailed ? '일정을 불러오지 못했습니다.' : '선택한 조건에 표시할 일정이 없습니다.' }}</span>
              <q-btn v-if="loadFailed && !loading" flat dense no-caps label="다시 시도" @click="retryIssues" />
            </div>
            <FullCalendar ref="calendarRef" :options="calendarOptions" />
          </q-card-section>
        </q-card>
      </div>

    </div>

    <!-- 이슈 상세/편집 다이얼로그 -->
    <IssueDetailDialog
      v-if="detailIssue"
      v-model="detailOpen"
      :project-id="detailIssue.projectId"
      :project-key="detailIssue.projectKey ?? ''"
      :issue="detailIssue"
      @updated="onIssueUpdated"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Notify } from 'quasar'
import { DateTime } from 'luxon'

import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { CalendarOptions, EventContentArg, EventInput, EventSourceFuncArg } from '@fullcalendar/core'
import type FullCalendarComponent from '@fullcalendar/vue3'

import IssueDetailDialog from './components/IssueDetailDialog.vue'
import ProjectFilter from 'src/components/ProjectFilter.vue'
import {
  getWorkStatus,
  TYPE_ICON,
  type Issue,
} from 'src/services/pm/issue'
import { getErrorMessage } from 'src/utils/http/error'

// ── 색상 팔레트 ────────────────────────────────────────────────────────
// 골든 앵글(137.508°)로 색상환을 순회하며 명도/채도를 3단계로 번갈아
// 인접한 색끼리 최대한 구분되도록 생성한 50색 팔레트.
const PALETTE = [
  '#ae5529', '#4dcb9c', '#8d1b98', '#92ae29', '#4d8ccb',
  '#981b35', '#29ae34', '#7d4dcb', '#986e1b', '#29aea8',
  '#cb4dac', '#54981b', '#293fae', '#cb5d4d', '#1b984f',
  '#8729ae', '#cbcb4d', '#1b7398', '#ae2960', '#5dcb4d',
  '#301b98', '#ae6629', '#4dcbac', '#981b92', '#81ae29',
  '#4d7ccb', '#981b25', '#29ae45', '#8d4dcb', '#987e1b',
  '#29a2ae', '#cb4d9c', '#44981b', '#292eae', '#cb6d4d',
  '#1b985f', '#9829ae', '#bbcb4d', '#1b6398', '#ae294f',
  '#4dcb4e', '#401b98', '#ae7729', '#4dcbbc', '#981b82',
  '#70ae29', '#4d6ccb', '#98211b', '#29ae56', '#9d4dcb',
]
// 미배정은 팔레트에 없는 고정 회색을 써서 실제 담당자 색과 절대 겹치지 않게 한다.
// STATUS_COLOR.BACKLOG(grey-5)와 동일한 회색으로 맞춰 "백로그"와 시각적으로 통일.
const UNASSIGNED_COLOR = '#bdbdbd'
const NO_ASSIGNEE_KEY = '__unassigned__'
const colorMap = new Map<string, string>()

function getAssigneeColor(assigneeId: string | null): string {
  if (!assigneeId || assigneeId === NO_ASSIGNEE_KEY) return UNASSIGNED_COLOR
  if (!colorMap.has(assigneeId)) colorMap.set(assigneeId, PALETTE[colorMap.size % PALETTE.length]!)
  return colorMap.get(assigneeId)!
}

function lightenSubTaskColor(color: string): string {
  return `#${[1, 3, 5].map((offset) => {
    const channel = Number.parseInt(color.slice(offset, offset + 2), 16)
    return Math.round(channel + (255 - channel) * 0.18).toString(16).padStart(2, '0')
  }).join('')}`
}

function getContrastingTextColor(color: string): string {
  const channels = [1, 3, 5].map((offset) => Number.parseInt(color.slice(offset, offset + 2), 16) / 255)
  const luminance = channels
    .map(channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
    .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index]!, 0)
  const whiteContrast = 1.05 / (luminance + 0.05)
  const darkContrast = (luminance + 0.05) / 0.05
  return darkContrast >= whiteContrast ? '#111827' : '#ffffff'
}

// ── 상태 ─────────────────────────────────────────────────────────────
const calendarRef = ref<InstanceType<typeof FullCalendarComponent> | null>(null)
const allIssues   = ref<Issue[]>([])
const selectedIds = ref(new Set<string>())
const selectedProjectId = ref<string | null>(null)
const loading = ref(false)
const loadFailed = ref(false)
const hasFilters = computed(() => !!selectedProjectId.value || selectedIds.value.size > 0)

const detailOpen  = ref(false)
const detailIssue = ref<Issue | null>(null)

function isWorkStatusIssue(issue: Issue): boolean {
  // API에서 하위 Task가 없는 Epic만 반환한다.
  return issue.type === 'EPIC' || issue.type === 'TASK' || issue.type === 'SUB_TASK'
}

function workStatusAssigneeId(issue: Issue): string {
  return issue.assigneeId && !issue.assigneeName?.includes('삭제된 회원')
    ? issue.assigneeId
    : NO_ASSIGNEE_KEY
}

// ── 담당자 목록 (이슈 로드 후 자동 추출) ──────────────────────────────
const allAssignees = computed(() => {
  const map = new Map<string, string>()
  for (const i of allIssues.value) {
    if (!isWorkStatusIssue(i)) continue
    const id = workStatusAssigneeId(i)
    map.set(id, id === NO_ASSIGNEE_KEY ? '담당자없음' : i.assigneeName || '담당자없음')
  }
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => Number(a.id === NO_ASSIGNEE_KEY) - Number(b.id === NO_ASSIGNEE_KEY))
})

// ── 담당자 다중 선택 ────────────────────────────────────────────────────
const knownAssigneeNames = ref(new Map<string, string>())
watch(allAssignees, assignees => {
  for (const assignee of assignees) knownAssigneeNames.value.set(assignee.id, assignee.name)
}, { immediate: true })

const assigneeFilters = computed(() => {
  const choices = new Map(allAssignees.value.map(assignee => [assignee.id, assignee]))
  // Keep selected people available for deselection when moving to an empty period.
  for (const id of selectedIds.value) {
    if (!choices.has(id)) choices.set(id, { id, name: knownAssigneeNames.value.get(id) ?? '선택한 담당자' })
  }
  return [...choices.values()]
    .sort((a, b) => Number(a.id === NO_ASSIGNEE_KEY) - Number(b.id === NO_ASSIGNEE_KEY)
      || a.name.localeCompare(b.name, 'ko'))
})

function toggleAssignee(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function clearAssignees() {
  selectedIds.value = new Set()
}

function resetFilters() {
  selectedProjectId.value = null
  clearAssignees()
}

function calendarIssueTitle(issue: Issue): string {
  if (issue.type === 'SUB_TASK' && issue.parentIssueTitle) {
    return `${issue.parentIssueTitle} - ${issue.title}`
  }
  return issue.title
}

const ISSUE_TYPE_LABEL: Partial<Record<Issue['type'], string>> = { EPIC: 'Epic', TASK: 'Task', SUB_TASK: 'Sub-task' }

function calendarEventContent(arg: EventContentArg): { domNodes: Node[] } {
  const issue = (arg.event.extendedProps as { issue?: Issue }).issue
  if (!issue) return { domNodes: [document.createTextNode(arg.event.title)] }

  const content = document.createElement('span')
  content.className = 'work-status-event-content'
  const icon = document.createElement('i')
  icon.className = TYPE_ICON[issue.type]
  icon.setAttribute('role', 'img')
  icon.setAttribute('aria-label', ISSUE_TYPE_LABEL[issue.type] ?? issue.type)
  const title = document.createElement('span')
  title.className = 'work-status-event-title'
  title.textContent = arg.event.title
  content.append(icon, title)
  return { domNodes: [content] }
}

// ── 필터된 이벤트 ─────────────────────────────────────────────────────
const filteredEvents = computed<EventInput[]>(() => {
  const base = selectedIds.value.size === 0
    ? allIssues.value
    : allIssues.value.filter(i => selectedIds.value.has(workStatusAssigneeId(i)))

  return base
    .filter(i => (!selectedProjectId.value || i.projectId === selectedProjectId.value)
      && isWorkStatusIssue(i) && (i.dueDate ?? i.startDate))
    .map(i => {
      const assigneeId = workStatusAssigneeId(i)
      const color = getAssigneeColor(assigneeId)
      const eventColor = i.type === 'SUB_TASK' ? lightenSubTaskColor(color) : color
      const start = (i.startDate ?? i.dueDate)!.slice(0, 10)
      const rawEnd = i.dueDate ? i.dueDate.slice(0, 10) : null
      const end = rawEnd
        ? DateTime.fromISO(rawEnd).plus({ days: 1 }).toFormat('yyyy-MM-dd')
        : null
      return {
        id: i.id,
        title: assigneeId === NO_ASSIGNEE_KEY
          ? `[담당자없음] ${i.projectName || i.projectKey || calendarIssueTitle(i)}`
          : `[${i.assigneeName}] ${calendarIssueTitle(i)}`,
        start,
        ...(end && end !== start ? { end } : {}),
        allDay: true,
        backgroundColor: eventColor,
        borderColor: eventColor,
        textColor: getContrastingTextColor(eventColor),
        extendedProps: { issue: i },
      }
    })
})

// ── 이슈 로드 ─────────────────────────────────────────────────────────
let lastFetchKey = ''
let fetchSequence = 0

function retryIssues() {
  lastFetchKey = ''
  calendarRef.value?.getApi()?.refetchEvents()
}

async function loadIssues(startDate: string, endDate: string): Promise<void> {
  const sequence = ++fetchSequence
  loading.value = true
  loadFailed.value = false
  try {
    const issues = await getWorkStatus({ start_date: startDate, end_date: endDate })
    if (sequence === fetchSequence) allIssues.value = issues
  } catch (e) {
    if (sequence !== fetchSequence) return
    loadFailed.value = true
    Notify.create({ type: 'negative', message: getErrorMessage(e, '이슈 로드 실패') })
    allIssues.value = []
  } finally {
    if (sequence === fetchSequence) loading.value = false
  }
}

// ── 캘린더 옵션 ────────────────────────────────────────────────────────
const calendarOptions = ref<CalendarOptions>({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,dayGridWeek',
  },
  buttonText: { today: '오늘', month: '월', week: '주' },
  weekends: true,
  height: 'auto',
  dayMaxEvents: true,
  eventDisplay: 'block',
  eventContent: calendarEventContent,
  eventDidMount: (arg) => {
    arg.el.title = arg.event.title
  },

  events: (
    fetchInfo: EventSourceFuncArg,
    successCallback: (events: EventInput[]) => void,
    failureCallback: (error: Error) => void
  ) => {
    const start = DateTime.fromJSDate(fetchInfo.start).toFormat('yyyy-MM-dd')
    const end   = DateTime.fromJSDate(fetchInfo.end).toFormat('yyyy-MM-dd')
    const fetchKey = `${start}|${end}`

    if (fetchKey === lastFetchKey) {
      successCallback(filteredEvents.value)
      return
    }
    lastFetchKey = fetchKey

    loadIssues(start, end)
      .then(() => successCallback(filteredEvents.value))
      .catch((err: unknown) => failureCallback(err instanceof Error ? err : new Error('fetch failed')))
  },

  eventClick: (arg) => {
    const ext = arg.event.extendedProps as { issue?: Issue }
    if (ext.issue) {
      detailIssue.value = ext.issue
      detailOpen.value = true
    }
  },
})

// ── 필터·조회 결과 변경 → 캘린더 재렌더 (API 재호출 없음) ────────────────
watch(filteredEvents, () => {
  calendarRef.value?.getApi()?.refetchEvents()
})

// ── 이슈 업데이트 반영 ────────────────────────────────────────────────
function onIssueUpdated(updated: Issue) {
  const idx = allIssues.value.findIndex(i => i.id === updated.id)
  if (idx !== -1) allIssues.value[idx] = updated
  calendarRef.value?.getApi()?.refetchEvents()
}

// ── ResizeObserver ────────────────────────────────────────────────────
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  const el = document.querySelector('.q-page')
  if (!el) return
  resizeObserver = new ResizeObserver(() => calendarRef.value?.getApi()?.updateSize())
  resizeObserver.observe(el)
})

onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<style scoped>
.work-status-filters { display: grid; grid-template-columns: 220px minmax(0, 1fr) auto; align-items: start; gap: 12px 16px; padding: 12px 16px; }
.work-status-select { width: 220px; min-width: 0; max-width: 100%; }
.work-status-select :deep(.q-field__control), .work-status-select :deep(.q-field__marginal) { min-height: 38px; height: 38px; }
.work-status-assignees { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; min-width: 0; padding: 2px 0; }
.work-status-reset { grid-column: 3; grid-row: 1; min-height: 38px; color: var(--bo-muted); }
.assignee-toggle { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 34px; max-width: 100%; padding: 6px 10px; border: 1px solid var(--bo-border-strong); border-radius: var(--bo-radius-control, 8px); background: var(--bo-surface); color: var(--bo-secondary); font: inherit; font-size: 13px; line-height: 20px; cursor: pointer; }
.assignee-toggle:hover { background: var(--bo-accent-soft); }
.assignee-toggle:focus-visible { outline: 2px solid var(--bo-accent-ink); outline-offset: 2px; }
.assignee-toggle--active { border-color: var(--bo-accent-ink); background: var(--bo-accent-soft); color: var(--bo-accent-ink); }
.assignee-name { min-width: 0; overflow-wrap: anywhere; }
.assignee-check { flex-shrink: 0; visibility: hidden; }
.assignee-toggle--active .assignee-check { visibility: visible; }
.assignee-color { flex-shrink: 0; width: 8px; height: 8px; border-radius: 50%; }
.work-status-notice { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; color: var(--bo-muted); font-size: 13px; }
:deep(.work-status-event-content) { display: inline-flex; align-items: center; gap: 5px; min-width: 0; max-width: 100%; }
:deep(.work-status-event-content i) { flex: none; width: 14px; font-size: 11px; text-align: center; }
:deep(.work-status-event-title) { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 899px) {
  .work-status-filters { grid-template-columns: minmax(0, 1fr) auto; }
  .work-status-assignees { grid-column: 1 / -1; grid-row: 2; }
  .work-status-reset { grid-column: 2; }
}
</style>
