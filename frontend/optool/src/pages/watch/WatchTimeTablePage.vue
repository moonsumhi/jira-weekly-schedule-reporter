<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <div class="col-12">
        <div class="text-h5">당직 근무 일정표</div>
        <div class="text-caption text-grey-7">
          드래그/리사이즈로 수정할 수 있습니다.
          빈 시간대를 클릭하면 생성할 수 있고,
          이벤트를 클릭하면 수정/삭제할 수 있습니다.
        </div>
      </div>

      <!-- 일괄 생성 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section class="row items-center q-col-gutter-sm">
            <div class="col-12 col-md-3">
              <q-input dense v-model="bulk.assignee" label="담당자" />
            </div>

            <div class="col-6 col-md-2">
              <q-input
                dense
                v-model="bulk.startTime"
                label="시작 시간 (HH:MM)"
                placeholder="12:00"
              />
            </div>

            <div class="col-6 col-md-2">
              <q-input
                dense
                v-model="bulk.endTime"
                label="종료 시간 (HH:MM)"
                placeholder="12:30"
              />
            </div>

            <div class="col-12 col-md-3 row items-center q-gutter-sm">
              <q-checkbox
                v-for="d in days"
                :key="d.key"
                dense
                v-model="bulk.dayKeys"
                :val="d.key"
                :label="d.label"
              />
            </div>

            <div class="col-12 col-md-2">
              <q-btn
                color="primary"
                class="full-width"
                label="일괄 생성"
                :loading="busy"
                @click="createBulk"
              />
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

    <!-- 생성 / 수정 다이얼로그 -->
    <q-dialog v-model="dialog.open" persistent>
      <q-card style="width:min(560px, 92vw);">
        <q-card-section>
          <div class="text-h6">
            {{ dialog.mode === 'create' ? '근무 일정 생성' : '근무 일정 수정' }}
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section class="q-gutter-md">
          <q-input v-model="dialog.assignee" label="담당자" />
          <q-input v-model="dialog.startLocal" label="시작 시간" type="datetime-local" />
          <q-input v-model="dialog.endLocal" label="종료 시간" type="datetime-local" />
          <q-input v-model="dialog.note" label="메모 (선택)" />

          <div v-if="dialog.error" class="text-negative text-caption">
            {{ dialog.error }}
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right" class="q-gutter-sm">
          <q-btn flat label="취소" @click="closeDialog" />
          <q-btn
            v-if="dialog.mode === 'edit'"
            color="negative"
            flat
            label="삭제"
            @click="removeDialog"
          />
          <q-btn
            color="primary"
            label="저장"
            :loading="busy"
            @click="saveDialog"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Notify } from 'quasar'
import { DateTime } from 'luxon'

import FullCalendar from '@fullcalendar/vue3'
import timeGridPlugin from '@fullcalendar/timegrid'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { CalendarOptions, EventInput, EventSourceFuncArg } from '@fullcalendar/core'
import type FullCalendarComponent from '@fullcalendar/vue3'

import { listWatch, createWatch, patchWatch, deleteWatch, type WatchRow } from 'src/services/watch'
import { dateToKstDateTimeLocal, kstDateTimeLocalToUtcIso } from 'src/utils/time/kst'
import { isRecord, getErrorMessage } from 'src/utils/http/error'

const busy = ref(false)

const days = [
  { key: 'mon', label: 'Mon' },
  { key: 'tue', label: 'Tue' },
  { key: 'wed', label: 'Wed' },
  { key: 'thu', label: 'Thu' },
  { key: 'fri', label: 'Fri' },
  { key: 'sat', label: 'Sat' },
  { key: 'sun', label: 'Sun' }
] as const

const bulk = ref({
  assignee: '문수미',
  startTime: '12:00',
  endTime: '12:30',
  dayKeys: ['mon', 'tue', 'wed', 'thu'] as string[],
  note: ''
})

const events = ref<EventInput[]>([])

type ExtendedProps = {
  assignee: string
  note: string
  version: number
}

type ClickArg = {
  event: {
    id: string
    title: string
    start: Date | null
    end: Date | null
    extendedProps?: unknown
  }
}

const calendarRef = ref<InstanceType<typeof FullCalendarComponent> | null>(null)

function refetchCalendar() {
  const api = calendarRef.value?.getApi?.()
  api?.refetchEvents()
}

function mapRowsToEvents(rows: WatchRow[]): EventInput[] {
  return rows.map(r => {
    const note = (isRecord(r.fields) && typeof r.fields.note === 'string') ? r.fields.note : ''
    const ext: ExtendedProps = { assignee: r.assignee, note, version: r.version ?? 1 }
    return {
      id: r.id,
      title: note ? `${r.assignee} — ${note}` : r.assignee,
      start: r.start,
      end: r.end,
      extendedProps: ext
    }
  })
}

async function loadRange(startISO?: string, endISO?: string) {
  const params: { start?: string; end?: string; include_deleted?: boolean } = {
    include_deleted: false
  }

  if (startISO) params.start = startISO
  if (endISO) params.end = endISO

  const rows = await listWatch(params)
  events.value = mapRowsToEvents(rows)
}

// Dialog
const dialog = ref({
  open: false,
  mode: 'create' as 'create' | 'edit',
  id: '' as string,
  assignee: '',
  startLocal: '',
  endLocal: '',
  note: '',
  version: 1 as number,
  error: ''
})

function openCreate(start: Date, end: Date) {
  dialog.value = {
    open: true,
    mode: 'create',
    id: '',
    assignee: bulk.value.assignee,
    startLocal: dateToKstDateTimeLocal(start),
    endLocal: dateToKstDateTimeLocal(end),
    note: bulk.value.note,
    version: 1,
    error: ''
  }
}

function openEdit(arg: ClickArg) {
  const ev = arg.event
  const start = ev.start ?? new Date()
  const end = ev.end ?? new Date(start.getTime() + 30 * 60 * 1000)

  const ext = (ev.extendedProps ?? {}) as Partial<ExtendedProps>

  dialog.value = {
    open: true,
    mode: 'edit',
    id: String(ev.id),
    assignee: typeof ext.assignee === 'string' ? ext.assignee : (ev.title ?? ''),
    startLocal: dateToKstDateTimeLocal(start),
    endLocal: dateToKstDateTimeLocal(end),
    note: typeof ext.note === 'string' ? ext.note : '',
    version: typeof ext.version === 'number' ? ext.version : 1,
    error: ''
  }
}

function closeDialog() {
  dialog.value.open = false
  dialog.value.error = ''
}

async function saveDialog() {
  try {
    busy.value = true
    dialog.value.error = ''

    const assignee = dialog.value.assignee.trim()
    if (!assignee) throw new Error('Assignee is required.')

    const startIso = kstDateTimeLocalToUtcIso(dialog.value.startLocal)
    const endIso = kstDateTimeLocalToUtcIso(dialog.value.endLocal)

    const start = DateTime.fromISO(startIso)
    const end = DateTime.fromISO(endIso)
    if (!start.isValid || !end.isValid) throw new Error('Invalid date/time.')
    if (end <= start) throw new Error('End must be after start.')

    const payload = {
      assignee,
      start: startIso,
      end: endIso,
      fields: { note: dialog.value.note?.trim() || '' }
    }

    if (dialog.value.mode === 'create') {
      await createWatch(payload)
    } else {
      await patchWatch(dialog.value.id, { ...payload, version: dialog.value.version })
    }

    closeDialog()
    refetchCalendar()
    Notify.create({ type: 'positive', message: 'Saved' })
  } catch (e: unknown) {
    dialog.value.error = getErrorMessage(e, 'Failed')
    Notify.create({ type: 'negative', message: dialog.value.error })
  } finally {
    busy.value = false
  }
}

async function removeDialog() {
  try {
    busy.value = true
    dialog.value.error = ''
    await deleteWatch(dialog.value.id)
    closeDialog()
    refetchCalendar()
    Notify.create({ type: 'positive', message: 'Deleted' })
  } catch (e: unknown) {
    dialog.value.error = getErrorMessage(e, 'Failed')
    Notify.create({ type: 'negative', message: dialog.value.error })
  } finally {
    busy.value = false
  }
}

// Minimal typing for move/resize compatibility across FullCalendar versions
type MutableEventApi = {
  id: string
  start: Date | null
  end: Date | null
  extendedProps?: unknown
}
type MoveResizeArg = { event: MutableEventApi; revert?: () => void }

async function onMoveOrResize(info: MoveResizeArg) {
  try {
    const ev = info.event
    if (!ev.start || !ev.end) return

    const startIso = DateTime.fromJSDate(ev.start).toUTC().toISO()
    const endIso = DateTime.fromJSDate(ev.end).toUTC().toISO()
    if (!startIso || !endIso) return

    const ext = isRecord(ev.extendedProps) ? ev.extendedProps : {}
    const version = (isRecord(ext) && typeof ext.version === 'number') ? ext.version : undefined

    await patchWatch(ev.id, { start: startIso, end: endIso, ...(version !== undefined ? { version } : {}) })
    refetchCalendar()
  } catch {
    info.revert?.()
    Notify.create({ type: 'negative', message: 'Update failed. Reverted.' })
  }
}

// Bulk create using Luxon in KST (no JS Date weekday math headaches)
async function createBulk() {
  try {
    busy.value = true

    const [sh, sm] = bulk.value.startTime.split(':').map(Number)
    const [eh, em] = bulk.value.endTime.split(':').map(Number)
    if ([sh, sm, eh, em].some(n => Number.isNaN(n))) {
      Notify.create({ type: 'negative', message: 'Invalid time format. Use HH:MM' })
      return
    }

    // Start of this week in KST (Monday 00:00)
    const nowKst = DateTime.now().setZone('Asia/Seoul')
    const mondayKst = nowKst.startOf('day').minus({ days: nowKst.weekday - 1 })
    const keyToOffset: Record<string, number> = { mon: 0, tue: 1, wed: 2, thu: 3, fri: 4, sat: 5, sun: 6 }

    for (const key of bulk.value.dayKeys) {
      const offset = keyToOffset[key]
      if (offset === undefined) continue

      const startKst = mondayKst.plus({ days: offset }).set({ hour: sh, minute: sm, second: 0, millisecond: 0 })
      const endKst = mondayKst.plus({ days: offset }).set({ hour: eh, minute: em, second: 0, millisecond: 0 })

      if (endKst <= startKst) {
        Notify.create({ type: 'negative', message: 'End must be after start.' })
        return
      }

      const startIso = startKst.toUTC().toISO()
      const endIso = endKst.toUTC().toISO()

      if (!startIso || !endIso) {
        throw new Error('Invalid datetime')
      }

      await createWatch({
        assignee: bulk.value.assignee.trim(),
        start: startIso,
        end: endIso,
        fields: { note: bulk.value.note?.trim() || '' }
      })
    }

    refetchCalendar()
    Notify.create({ type: 'positive', message: 'Bulk created' })
  } catch (e: unknown) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Failed') })
  } finally {
    busy.value = false
  }
}

const calendarOptions = ref<CalendarOptions>({
  plugins: [timeGridPlugin, dayGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  selectable: true,
  editable: true,
  nowIndicator: true,
  height: 'auto',

  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'timeGridWeek,dayGridMonth'
  },

  events: (
    fetchInfo: EventSourceFuncArg,
    successCallback: (events: EventInput[]) => void,
    failureCallback: (error: Error) => void
  ) => {
    loadRange(fetchInfo.startStr, fetchInfo.endStr)
      .then(() => successCallback(events.value))
      .catch((err: unknown) => {
        failureCallback(
          err instanceof Error ? err : new Error('Failed to load events')
        )
      })
  },

  select: (arg) => openCreate(arg.start, arg.end),
  eventClick: (arg) => openEdit(arg),
  eventDrop: (info) => { void onMoveOrResize(info as MoveResizeArg) },
  eventResize: (info) => { void onMoveOrResize(info as MoveResizeArg)}
})
</script>
