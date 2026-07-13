<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5 text-weight-bold">업무 현황</div>
        <div class="text-caption text-grey-6">담당자별 업무 일정 현황</div>
      </div>

      <!-- 담당자 필터 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section class="q-py-sm">
            <div class="row items-center wrap q-gutter-xs">
              <span class="text-caption text-grey-5 q-mr-xs" style="line-height: 28px">담당자</span>

              <!-- 전체 칩 -->
              <q-chip
                clickable
                dense
                :color="selectedIds.size === 0 ? 'primary' : undefined"
                :text-color="selectedIds.size === 0 ? 'white' : 'grey-7'"
                :outline="selectedIds.size > 0"
                size="sm"
                @click="clearSelection"
              >전체</q-chip>

              <!-- 담당자 칩 (다중 선택) -->
              <q-chip
                v-for="a in allAssignees"
                :key="a.id"
                clickable
                dense
                size="sm"
                :outline="!selectedIds.has(a.id)"
                :text-color="selectedIds.has(a.id) ? 'white' : 'grey-8'"
                :style="selectedIds.has(a.id)
                  ? `background:${getAssigneeColor(a.id)};border-color:${getAssigneeColor(a.id)}`
                  : `border-color:${getAssigneeColor(a.id)}`"
                @click="toggleAssignee(a.id)"
              >
                <q-avatar
                  :style="`background:${getAssigneeColor(a.id)};color:#fff;font-size:10px`"
                  size="18px"
                >{{ a.name.charAt(0).toUpperCase() }}</q-avatar>
                {{ a.name }}
              </q-chip>

              <!-- 선택 수 표시 -->
              <span
                v-if="selectedIds.size > 0"
                class="text-caption text-grey-5 q-ml-xs"
                style="line-height: 28px"
              >{{ selectedIds.size }}명 선택</span>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 캘린더 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <FullCalendar ref="calendarRef" :options="calendarOptions" />
          </q-card-section>
        </q-card>
      </div>

    </div>

    <!-- 이슈 상세 팝업 -->
    <q-dialog v-model="detailOpen">
      <q-card style="min-width: 360px; max-width: 500px">
        <q-card-section class="row items-start no-wrap">
          <div class="col">
            <div class="row items-center q-gutter-xs q-mb-xs">
              <q-icon
                :name="detailIssue ? TYPE_ICON[detailIssue.type] : ''"
                :color="detailIssue ? TYPE_COLOR[detailIssue.type] : ''"
                size="16px"
              />
              <span class="text-caption text-grey-5">
                {{ detailIssue?.projectKey }}-{{ detailIssue?.number }}
              </span>
              <q-badge
                v-if="detailIssue"
                :color="STATUS_COLOR[detailIssue.status]"
                :label="STATUS_LABEL[detailIssue.status]"
              />
            </div>
            <div class="text-subtitle1 text-weight-bold">{{ detailIssue?.title }}</div>
          </div>
          <q-btn flat round dense icon="close" class="q-ml-sm" @click="detailOpen = false" />
        </q-card-section>

        <q-separator />

        <q-card-section v-if="detailIssue" class="q-gutter-xs">
          <div class="row items-center q-gutter-xs">
            <q-icon
              :name="PRIORITY_ICON[detailIssue.priority]"
              :color="PRIORITY_COLOR[detailIssue.priority]"
              size="16px"
            />
            <span class="text-caption text-grey-7">{{ PRIORITY_LABEL[detailIssue.priority] }}</span>
          </div>
          <div class="row q-gutter-md q-mt-xs">
            <div>
              <div class="text-caption text-grey-5">프로젝트</div>
              <div class="text-body2">{{ detailIssue.projectName ?? detailIssue.projectKey }}</div>
            </div>
            <div>
              <div class="text-caption text-grey-5">담당자</div>
              <div class="text-body2 row items-center">
                <q-avatar
                  v-if="detailIssue.assigneeId"
                  :style="`background:${getAssigneeColor(detailIssue.assigneeId)};color:#fff;font-size:10px`"
                  size="20px"
                  class="q-mr-xs"
                >{{ (detailIssue.assigneeName ?? '?').charAt(0).toUpperCase() }}</q-avatar>
                {{ detailIssue.assigneeName ?? '미배정' }}
              </div>
            </div>
          </div>
          <div class="row q-gutter-md q-mt-xs">
            <div v-if="detailIssue.startDate">
              <div class="text-caption text-grey-5">시작일</div>
              <div class="text-body2">{{ detailIssue.startDate.slice(0, 10) }}</div>
            </div>
            <div v-if="detailIssue.dueDate">
              <div class="text-caption text-grey-5">마감일</div>
              <div
                class="text-body2"
                :class="isOverdue(detailIssue) ? 'text-negative text-weight-bold' : ''"
              >
                {{ detailIssue.dueDate.slice(0, 10) }}
                <q-icon v-if="isOverdue(detailIssue)" name="warning" size="14px" class="q-ml-xs" />
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Notify } from 'quasar'
import { DateTime } from 'luxon'

import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { CalendarOptions, EventInput, EventSourceFuncArg } from '@fullcalendar/core'
import type FullCalendarComponent from '@fullcalendar/vue3'

import {
  getWorkStatus,
  STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR, PRIORITY_ICON, PRIORITY_COLOR, PRIORITY_LABEL,
  type Issue,
} from 'src/services/pm/issue'
import { getErrorMessage } from 'src/utils/http/error'

// ── 색상 팔레트 ────────────────────────────────────────────────────────
const PALETTE = [
  '#1976d2', '#388e3c', '#7b1fa2', '#c62828',
  '#f57c00', '#0097a7', '#5d4037', '#455a64',
  '#e91e63', '#00897b',
]
// 미배정은 팔레트에 없는 고정 회색을 써서 실제 담당자 색과 절대 겹치지 않게 한다.
// STATUS_COLOR.BACKLOG(grey-5)와 동일한 회색으로 맞춰 "백로그"와 시각적으로 통일.
const UNASSIGNED_COLOR = '#bdbdbd'
const colorMap = new Map<string, string>()

function getAssigneeColor(assigneeId: string | null): string {
  if (!assigneeId) return UNASSIGNED_COLOR
  if (!colorMap.has(assigneeId)) colorMap.set(assigneeId, PALETTE[colorMap.size % PALETTE.length]!)
  return colorMap.get(assigneeId)!
}

// ── 상태 ─────────────────────────────────────────────────────────────
const calendarRef = ref<InstanceType<typeof FullCalendarComponent> | null>(null)
const allIssues   = ref<Issue[]>([])
const selectedIds = ref(new Set<string>())

const detailOpen  = ref(false)
const detailIssue = ref<Issue | null>(null)

// ── 담당자 목록 (이슈 로드 후 자동 추출) ──────────────────────────────
const allAssignees = computed(() => {
  const map = new Map<string, string>()
  for (const i of allIssues.value) {
    if (i.assigneeId && i.assigneeName) map.set(i.assigneeId, i.assigneeName)
  }
  return [...map.entries()].map(([id, name]) => ({ id, name }))
})

// ── 다중 선택 토글 ────────────────────────────────────────────────────
function toggleAssignee(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

// ── 필터된 이벤트 ─────────────────────────────────────────────────────
const filteredEvents = computed<EventInput[]>(() => {
  const base = selectedIds.value.size === 0
    ? allIssues.value
    : allIssues.value.filter(i => i.assigneeId !== null && selectedIds.value.has(i.assigneeId))

  return base
    .filter(i => i.type === 'TASK' && (i.dueDate ?? i.startDate))
    .map(i => {
      const color = getAssigneeColor(i.assigneeId)
      const start = (i.startDate ?? i.dueDate)!.slice(0, 10)
      const rawEnd = i.dueDate ? i.dueDate.slice(0, 10) : null
      const end = rawEnd
        ? DateTime.fromISO(rawEnd).plus({ days: 1 }).toFormat('yyyy-MM-dd')
        : null
      return {
        id: i.id,
        title: `[${i.assigneeName ?? '미배정'}] ${i.title}`,
        start,
        ...(end && end !== start ? { end } : {}),
        allDay: true,
        backgroundColor: color,
        borderColor: color,
        extendedProps: { issue: i } as Record<string, unknown>,
      }
    })
})

// ── 이슈 로드 ─────────────────────────────────────────────────────────
let lastFetchKey = ''

async function loadIssues(startDate: string, endDate: string): Promise<void> {
  try {
    allIssues.value = await getWorkStatus({ start_date: startDate, end_date: endDate })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '이슈 로드 실패') })
    allIssues.value = []
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

// ── 담당자 선택 변경 → 캘린더 재렌더 (API 재호출 없음) ────────────────
watch(selectedIds, () => {
  calendarRef.value?.getApi()?.refetchEvents()
})

// ── 헬퍼 ─────────────────────────────────────────────────────────────
function isOverdue(issue: Issue): boolean {
  if (!issue.dueDate || issue.status === 'DONE') return false
  const due = DateTime.fromISO(issue.dueDate, { zone: 'Asia/Seoul' })
  const today = DateTime.now().setZone('Asia/Seoul').startOf('day')
  return due < today
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
