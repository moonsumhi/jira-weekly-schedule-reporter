<template>
  <div ref="container" class="dday-calendar" :aria-busy="loading">
    <div class="calendar-toolbar">
      <h3 aria-live="polite">{{ monthTitle }}</h3>
      <div class="calendar-navigation">
        <q-btn flat dense no-caps color="primary" label="오늘" @click="calendar?.getApi().today()" />
        <q-btn flat dense round icon="chevron_left" aria-label="이전 달" @click="calendar?.getApi().prev()" />
        <q-btn flat dense round icon="chevron_right" aria-label="다음 달" @click="calendar?.getApi().next()" />
      </div>
    </div>
    <div v-if="loadFailed" class="calendar-notice" role="status">
      <span>{{ errorMessage || '일정을 불러오지 못했습니다.' }}</span>
      <q-btn flat dense no-caps color="primary" label="다시 불러오기" @click="emit('retry')" />
    </div>
    <div v-else-if="loading" class="calendar-notice" role="status">일정을 불러오는 중입니다.</div>
    <div v-else-if="!monthEventCount" class="calendar-notice">이번 달에 표시할 일정이 없습니다.</div>
    <div class="calendar-month">
      <FullCalendar ref="calendar" :options="options">
        <template #eventContent="{ event }">
          <span class="calendar-event">
            <strong class="calendar-event-dday">{{ event.extendedProps.daysLabel }}</strong>
            <span class="calendar-event-title">{{ event.title }}</span>
          </span>
        </template>
      </FullCalendar>
    </div>
    <q-menu v-model="overflowOpen" :target="overflowTarget" no-parent-event
      class="calendar-overflow" anchor="bottom left" self="top left" :offset="[0, 4]"
      max-width="300px" max-height="360px" role="dialog" aria-labelledby="calendar-overflow-title"
      @hide="closeOverflow">
      <div class="calendar-overflow-heading">
        <strong id="calendar-overflow-title">{{ overflowTitle }}</strong>
        <q-btn v-close-popup flat dense round size="sm" icon="close" aria-label="날짜별 일정 닫기" />
      </div>
      <ul class="calendar-overflow-list">
        <li v-for="event in overflowEvents" :key="event.id">
          <span class="calendar-overflow-count" :style="{ background: event.color }">{{ event.daysLabel }}</span>
          <div class="calendar-overflow-info">
            <strong>{{ event.title }}</strong>
            <p v-if="event.note">{{ event.note }}</p>
            <div class="calendar-event-actions"><slot name="actions" :event="event" /></div>
          </div>
        </li>
      </ul>
    </q-menu>
  </div>
</template>

<script lang="ts">
export interface CalendarDDay {
  id: string
  title: string
  date: string
  color: string
  daysLabel: string
  note?: string | null
}
</script>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import koLocale from '@fullcalendar/core/locales/ko'
import type { CalendarOptions } from '@fullcalendar/core'

const props = defineProps<{ events: CalendarDDay[]; today: string; loading: boolean; loadFailed: boolean; errorMessage?: string }>()
const emit = defineEmits<{ retry: []; create: [date: string] }>()
const calendar = ref<InstanceType<typeof FullCalendar>>()
const container = ref<HTMLElement>()
const monthTitle = ref('')
const displayedMonth = ref(props.today.slice(0, 7))
const monthEventCount = computed(() => props.events.filter(event => event.date.startsWith(displayedMonth.value)).length)
const initialDate = props.today
const overflowOpen = ref(false)
const overflowTarget = ref<HTMLElement | false>(false)
const overflowDate = ref('')
const overflowEvents = computed(() => props.events.filter(event => event.date === overflowDate.value))
const overflowTitle = computed(() => overflowDate.value ? new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC',
}).format(new Date(`${overflowDate.value}T00:00:00Z`)) : '')

// Show event details and actions outside the card's clipped scroll area.
function showDay(target: HTMLElement, date: string) {
  closeOverflow()
  overflowTarget.value = target
  overflowDate.value = date
  target.setAttribute('aria-expanded', 'true')
  void nextTick(() => { overflowOpen.value = true })
}

function openOverflow(event: Event) {
  if (event instanceof KeyboardEvent && event.key !== 'Enter' && event.key !== ' ') return
  const target = event.currentTarget as HTMLElement
  const date = target.closest<HTMLElement>('[data-date]')?.dataset.date
  if (!date) return
  event.preventDefault()
  event.stopImmediatePropagation()
  showDay(target, date)
}

function closeOverflow() {
  if (overflowTarget.value) overflowTarget.value.setAttribute('aria-expanded', 'false')
}

function createOnDate(date: string) {
  overflowOpen.value = false
  emit('create', date)
}

function createFromDateKey(event: KeyboardEvent) {
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  if (event.repeat) return
  const date = (event.currentTarget as HTMLElement).closest<HTMLElement>('[data-date]')?.dataset.date
  if (date) createOnDate(date)
}

const options = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  initialDate,
  now: props.today,
  timeZone: 'UTC', // All-day calendar dates must not shift with the browser's time zone.
  locale: koLocale,
  headerToolbar: false,
  height: '100%',
  fixedWeekCount: false,
  firstDay: 0,
  dayMaxEvents: 1,
  moreLinkText: count => `+${count}개`,
  moreLinkDidMount: ({ el }) => {
    el.setAttribute('aria-haspopup', 'dialog')
    el.addEventListener('click', openOverflow, true)
    el.addEventListener('keydown', openOverflow, true)
  },
  moreLinkWillUnmount: ({ el }) => {
    el.removeEventListener('click', openOverflow, true)
    el.removeEventListener('keydown', openOverflow, true)
    if (el === overflowTarget.value) overflowOpen.value = false
  },
  eventInteractive: true,
  eventClick: info => {
    info.jsEvent.preventDefault()
    showDay(info.el, info.event.startStr)
  },
  eventDisplay: 'block',
  displayEventTime: false,
  dateClick: info => createOnDate(info.dateStr),
  dayCellContent: info => info.dayNumberText.replace('일', ''),
  dayCellDidMount: ({ el }) => {
    const dayNumber = el.querySelector<HTMLElement>('.fc-daygrid-day-number')
    if (!dayNumber) return
    dayNumber.setAttribute('role', 'button')
    dayNumber.setAttribute('tabindex', '0')
    dayNumber.setAttribute('aria-label', `${el.dataset.date} D-Day 추가`)
    dayNumber.setAttribute('aria-haspopup', 'dialog')
    dayNumber.addEventListener('keydown', createFromDateKey)
  },
  dayCellWillUnmount: ({ el }) => {
    el.querySelector<HTMLElement>('.fc-daygrid-day-number')?.removeEventListener('keydown', createFromDateKey)
  },
  datesSet: info => {
    monthTitle.value = info.view.title
    displayedMonth.value = info.view.currentStart.toISOString().slice(0, 7)
  },
  events: props.events.map(event => ({
    id: event.id,
    title: event.title,
    start: event.date,
    allDay: true,
    backgroundColor: event.color,
    borderColor: event.color,
    textColor: '#ffffff',
    extendedProps: { daysLabel: event.daysLabel, note: event.note },
  })),
  eventDidMount: info => {
    const description = `${info.event.startStr} · ${info.event.extendedProps.daysLabel} · ${info.event.title}${info.event.extendedProps.note ? `\n${info.event.extendedProps.note}` : ''}`
    info.el.title = description
    info.el.setAttribute('aria-label', description)
    info.el.setAttribute('aria-haspopup', 'dialog')
    info.el.setAttribute('aria-expanded', 'false')
  },
  eventWillUnmount: info => {
    if (info.el === overflowTarget.value) overflowOpen.value = false
  },
}))

let observer: ResizeObserver | undefined
let resizeFrame = 0
onMounted(() => {
  observer = new ResizeObserver(() => {
    window.cancelAnimationFrame(resizeFrame)
    resizeFrame = window.requestAnimationFrame(() => calendar.value?.getApi().updateSize())
  })
  if (container.value) observer.observe(container.value)
})
onUnmounted(() => {
  observer?.disconnect()
  window.cancelAnimationFrame(resizeFrame)
})
</script>

<style scoped>
.dday-calendar { display: flex; flex-direction: column; min-height: 0; height: 100%; color: var(--bo-text); }
.calendar-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 12px; }
.calendar-toolbar h3 { margin: 0; font-size: 18px; line-height: 1.45; font-weight: 650; }
.calendar-navigation { display: flex; align-items: center; gap: 4px; }
.calendar-notice { display: flex; align-items: center; flex-wrap: wrap; justify-content: space-between; gap: 4px; margin-bottom: 8px; color: var(--bo-muted); font-size: 12px; }
.calendar-month { flex: 1; min-height: 230px; }
.calendar-month :deep(.fc) { --fc-border-color: var(--bo-border); --fc-today-bg-color: var(--bo-accent-soft); --fc-neutral-bg-color: var(--bo-surface-subtle); --fc-page-bg-color: var(--bo-surface); font-size: 12px; }
.calendar-month :deep(.fc-col-header-cell) { padding: 4px 0; background: var(--bo-surface-subtle); color: var(--bo-secondary); font-weight: 600; }
.calendar-month :deep(.fc-daygrid-day-number) { padding: 4px 6px; color: var(--bo-secondary); font-variant-numeric: tabular-nums; text-decoration: none; }
.calendar-month :deep(.fc-daygrid-day-frame) { cursor: pointer; }
.calendar-month :deep(.fc-daygrid-day-number:focus-visible) { outline: 2px solid var(--bo-accent-ink); outline-offset: -2px; }
.calendar-month :deep(.fc-daygrid-day-events) { min-height: 0; }
.calendar-month :deep(.fc-day-today .fc-daygrid-day-number) { color: var(--bo-accent-ink); font-weight: 750; }
.calendar-month :deep(.fc-day-sun .fc-col-header-cell-cushion),
.calendar-month :deep(.fc-day-sun .fc-daygrid-day-number) { color: #b42318; }
.calendar-month :deep(.fc-day-sat .fc-col-header-cell-cushion),
.calendar-month :deep(.fc-day-sat .fc-daygrid-day-number) { color: var(--bo-accent-ink); }
.calendar-month :deep(.fc-daygrid-event) { border-radius: 4px; padding: 2px 3px; margin: 1px 3px; cursor: pointer; }
.calendar-month :deep(.fc-daygrid-event:focus-visible) { outline: 2px solid var(--bo-accent-ink); outline-offset: 2px; }
.calendar-event { display: flex; flex-direction: column; min-width: 0; font-size: 11px; line-height: 1.4; }
.calendar-event-dday { font-weight: 700; font-variant-numeric: tabular-nums; }
.calendar-event-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.calendar-month :deep(.fc-daygrid-more-link) { color: var(--bo-accent-ink); padding: 2px 4px; font-weight: 600; }
.calendar-overflow { width: 300px; color: var(--bo-text); background: var(--bo-surface); }
.calendar-overflow-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--bo-border); font-size: 13px; }
.calendar-overflow-list { margin: 0; padding: 4px 12px; list-style: none; }
.calendar-overflow-list li { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; }
.calendar-overflow-list li + li { border-top: 1px solid var(--bo-border); }
.calendar-overflow-count { flex-shrink: 0; min-width: 48px; padding: 4px 6px; border-radius: 4px; color: #fff; text-align: center; font-size: 12px; font-weight: 650; }
.calendar-overflow-info { min-width: 0; overflow-wrap: anywhere; font-size: 13px; }
.calendar-overflow-info strong { font-weight: 600; }
.calendar-overflow-info p { margin: 4px 0 0; color: var(--bo-muted); font-size: 12px; white-space: pre-wrap; }
.calendar-event-actions { display: flex; flex-wrap: wrap; gap: 4px 8px; }
.calendar-event-actions:not(:empty) { margin-top: 8px; }
@media (max-width: 600px) {
  .calendar-toolbar h3 { font-size: 16px; }
  .calendar-month :deep(.fc-daygrid-event) { margin-inline: 1px; padding-inline: 2px; }
}
</style>
