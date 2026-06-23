<template>
  <q-page class="q-pa-md">
    <div class="text-h6 q-mb-md">팀 캘린더</div>

    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner color="primary" size="40px" />
    </div>

    <div v-else-if="error" class="text-negative q-pa-md">
      캘린더를 불러오지 못했습니다: {{ error }}
    </div>

    <div v-else class="calendar-wrap">
      <FullCalendar :options="calendarOptions" />
    </div>

    <!-- 이벤트 상세 다이얼로그 -->
    <q-dialog v-model="detailOpen">
      <q-card style="min-width: 320px; max-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ selected?.title }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="q-mb-sm text-caption text-grey">
            {{ fmtRange(selected) }}
          </div>
          <div v-if="selected?.location" class="q-mb-sm">
            <q-icon name="place" size="xs" class="q-mr-xs" />{{ selected.location }}
          </div>
          <div v-if="selected?.description" style="white-space: pre-wrap">
            {{ selected.description }}
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import type { CalendarOptions, EventClickArg } from '@fullcalendar/core'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import koLocale from '@fullcalendar/core/locales/ko'
import { api } from 'boot/axios'

interface CalEvent {
  title: string
  start: string
  end: string
  description: string
  location: string
  allDay: boolean
}

const loading = ref(true)
const error = ref('')
const detailOpen = ref(false)
const selected = ref<CalEvent | null>(null)
const events = ref<CalEvent[]>([])

const calendarOptions = ref<CalendarOptions>({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  locale: koLocale,
  height: 'auto',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,dayGridWeek',
  },
  events: [],
  eventClick: (info: EventClickArg) => {
    selected.value = {
      title: info.event.title,
      start: info.event.startStr,
      end: info.event.endStr,
      description: (info.event.extendedProps['description'] as string) || '',
      location: (info.event.extendedProps['location'] as string) || '',
      allDay: info.event.allDay,
    }
    detailOpen.value = true
  },
  eventColor: '#1976d2',
})

function fmtRange(ev: CalEvent | null): string {
  if (!ev) return ''
  const s = new Date(ev.start)
  const e = new Date(ev.end)
  const fmt = (d: Date) =>
    `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
  if (ev.allDay) {
    const eDay = new Date(e)
    eDay.setDate(eDay.getDate() - 1)
    return fmt(s) === fmt(eDay) ? fmt(s) : `${fmt(s)} ~ ${fmt(eDay)}`
  }
  const fmtTime = (d: Date) =>
    `${fmt(d)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return `${fmtTime(s)} ~ ${fmtTime(e)}`
}

onMounted(async () => {
  try {
    const res = await api.get<CalEvent[]>('/calendar/events')
    events.value = res.data
    calendarOptions.value = {
      ...calendarOptions.value,
      events: res.data.map((ev) => ({
        title: ev.title,
        start: ev.start,
        end: ev.end,
        allDay: ev.allDay,
        extendedProps: { description: ev.description, location: ev.location },
      })),
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.calendar-wrap {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}
</style>
