<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <div class="col-12">
        <div class="row items-start">
          <div>
            <div class="text-h5">당직 근무 일정표</div>
            <div class="text-caption text-grey-7">
              드래그/리사이즈로 수정할 수 있습니다.
              빈 시간대를 클릭하면 생성할 수 있고,
              이벤트를 클릭하면 수정/삭제할 수 있습니다.
            </div>
          </div>
          <q-space />
          <div class="row items-center q-gutter-sm">
            <q-btn flat dense icon="download" label="템플릿 다운로드" @click="downloadTemplate" />
            <q-btn color="teal" icon="upload" label="Import" :loading="importing" @click="triggerImport" />
            <input ref="importInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onImportFile" />
          </div>
        </div>
      </div>

      <!-- 일괄 생성 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">일괄 생성</div>
            <div class="row q-col-gutter-sm">

              <!-- A타임 -->
              <div class="col-12">
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-badge color="blue" label="A타임" />
                    <span class="text-caption text-grey-7">11:00 ~ 12:00</span>
                  </div>
                  <div class="row items-center q-col-gutter-sm">
                    <div class="col-12 col-sm-4">
                      <q-input dense v-model="bulkA.assignee" label="담당자" />
                    </div>
                    <div class="col-6 col-sm-3">
                      <q-input dense v-model="bulkA.fromDate" label="시작일" type="date" />
                    </div>
                    <div class="col-6 col-sm-3">
                      <q-input dense v-model="bulkA.toDate" label="종료일" type="date" />
                    </div>
                    <div class="col-12 col-sm-2">
                      <q-btn color="blue" class="full-width" label="생성" :loading="busy" @click="createBulkA" />
                    </div>
                  </div>
                </q-card>
              </div>

              <!-- B타임 -->
              <div class="col-12">
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-badge color="purple" label="B타임" />
                    <span class="text-caption text-grey-7">12:00 ~ 13:00</span>
                  </div>
                  <div class="row items-center q-col-gutter-sm">
                    <div class="col-12 col-sm-4">
                      <q-input dense v-model="bulkB.assignee" label="담당자" />
                    </div>
                    <div class="col-6 col-sm-3">
                      <q-input dense v-model="bulkB.fromDate" label="시작일" type="date" />
                    </div>
                    <div class="col-6 col-sm-3">
                      <q-input dense v-model="bulkB.toDate" label="종료일" type="date" />
                    </div>
                    <div class="col-12 col-sm-2">
                      <q-btn color="purple" class="full-width" label="생성" :loading="busy" @click="createBulkB" />
                    </div>
                  </div>
                </q-card>
              </div>

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
      <q-card style="width:min(480px, 92vw);">
        <q-card-section>
          <div class="text-h6">
            {{ dialog.mode === 'create' ? '근무 일정 생성' : '근무 일정 수정' }}
          </div>
          <div v-if="dialog.mode === 'create'" class="text-caption text-grey-7 q-mt-xs">
            {{ dialog.date }}
          </div>
        </q-card-section>

        <q-separator />

        <!-- 생성 모드: A/B타임 담당자 -->
        <q-card-section v-if="dialog.mode === 'create'" class="q-gutter-md">
          <div class="row items-center q-col-gutter-sm">
            <div class="col-auto">
              <q-badge color="blue" label="A타임" style="font-size:13px;padding:4px 8px;" />
            </div>
            <div class="col">
              <q-input v-model="dialog.assigneeA" label="담당자" dense />
            </div>
          </div>
          <div class="row items-center q-col-gutter-sm">
            <div class="col-auto">
              <q-badge color="purple" label="B타임" style="font-size:13px;padding:4px 8px;" />
            </div>
            <div class="col">
              <q-input v-model="dialog.assigneeB" label="담당자" dense />
            </div>
          </div>
          <q-input v-model="dialog.note" label="메모 (선택)" dense />
          <div v-if="dialog.error" class="text-negative text-caption">{{ dialog.error }}</div>
        </q-card-section>

        <!-- 수정 모드: 단일 담당자 -->
        <q-card-section v-else class="q-gutter-md">
          <q-input v-model="dialog.assignee" label="담당자" />
          <q-input v-model="dialog.note" label="메모 (선택)" />
          <div v-if="dialog.error" class="text-negative text-caption">{{ dialog.error }}</div>
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
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { Notify } from 'quasar'
import { DateTime } from 'luxon'
import * as XLSX from 'xlsx'

import FullCalendar from '@fullcalendar/vue3'
import timeGridPlugin from '@fullcalendar/timegrid'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import luxonPlugin from '@fullcalendar/luxon'
import type { CalendarOptions, EventInput, EventSourceFuncArg } from '@fullcalendar/core'
import type FullCalendarComponent from '@fullcalendar/vue3'

import { listWatch, createWatch, patchWatch, deleteWatch, type WatchRow } from 'src/services/watch'
import { dateToKstDateTimeLocal, kstDateTimeLocalToUtcIso } from 'src/utils/time/kst'
import { isRecord, getErrorMessage } from 'src/utils/http/error'

const busy = ref(false)


const bulkA = ref({ assignee: '', fromDate: '', toDate: '' })
const bulkB = ref({ assignee: '', fromDate: '', toDate: '' })

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

function slotColor(startIso: string): string {
  const hour = DateTime.fromISO(startIso, { zone: 'Asia/Seoul' }).hour
  if (hour === 11) return '#1976d2' // A타임 파란색
  if (hour === 12) return '#7b1fa2' // B타임 보라색
  return '#1976d2'
}

function mapRowsToEvents(rows: WatchRow[]): EventInput[] {
  return rows.map(r => {
    const note = (isRecord(r.fields) && typeof r.fields.note === 'string') ? r.fields.note : ''
    const ext: ExtendedProps = { assignee: r.assignee, note, version: r.version ?? 1 }
    const color = slotColor(r.start)
    return {
      id: r.id,
      title: note ? `${r.assignee} — ${note}` : r.assignee,
      start: r.start,
      end: r.end,
      backgroundColor: color,
      borderColor: color,
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
  mode: 'create',
  id: '',
  assignee: '',     // edit 모드 전용
  assigneeA: '',    // create 모드 A타임
  assigneeB: '',    // create 모드 B타임
  date: '',         // create 모드 선택 날짜 (YYYY-MM-DD)
  startLocal: '',   // edit 모드 전용
  endLocal: '',     // edit 모드 전용
  note: '',
  version: 1,
  error: ''
})

function openCreate(start: Date) {
  const dateStr = DateTime.fromJSDate(start, { zone: 'Asia/Seoul' }).toISODate() ?? ''
  dialog.value = {
    open: true,
    mode: 'create',
    id: '',
    assignee: '',
    assigneeA: '',
    assigneeB: '',
    date: dateStr,
    startLocal: '',
    endLocal: '',
    note: '',
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
    assigneeA: '',
    assigneeB: '',
    date: '',
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
    const note = dialog.value.note?.trim() || ''

    if (dialog.value.mode === 'create') {
      const assigneeA = dialog.value.assigneeA.trim()
      const assigneeB = dialog.value.assigneeB.trim()
      if (!assigneeA && !assigneeB) throw new Error('A타임 또는 B타임 담당자를 입력해 주세요.')

      const dt = DateTime.fromISO(dialog.value.date, { zone: 'Asia/Seoul' })
      if (!dt.isValid) throw new Error('날짜가 올바르지 않습니다.')

      if (assigneeA) {
        const startIso = dt.set({ hour: 11, minute: 0, second: 0, millisecond: 0 }).toUTC().toISO()
        const endIso   = dt.set({ hour: 12, minute: 0, second: 0, millisecond: 0 }).toUTC().toISO()
        if (startIso && endIso) await createWatch({ assignee: assigneeA, start: startIso, end: endIso, fields: { note } })
      }
      if (assigneeB) {
        const startIso = dt.set({ hour: 12, minute: 0, second: 0, millisecond: 0 }).toUTC().toISO()
        const endIso   = dt.set({ hour: 13, minute: 0, second: 0, millisecond: 0 }).toUTC().toISO()
        if (startIso && endIso) await createWatch({ assignee: assigneeB, start: startIso, end: endIso, fields: { note } })
      }
    } else {
      const assignee = dialog.value.assignee.trim()
      if (!assignee) throw new Error('담당자를 입력해 주세요.')

      const startIso = kstDateTimeLocalToUtcIso(dialog.value.startLocal)
      const endIso   = kstDateTimeLocalToUtcIso(dialog.value.endLocal)
      const start = DateTime.fromISO(startIso)
      const end   = DateTime.fromISO(endIso)
      if (!start.isValid || !end.isValid) throw new Error('날짜/시간이 올바르지 않습니다.')
      if (end <= start) throw new Error('종료 시각은 시작 시각 이후여야 합니다.')

      await patchWatch(dialog.value.id, { assignee, start: startIso, end: endIso, fields: { note }, version: dialog.value.version })
    }

    closeDialog()
    refetchCalendar()
    Notify.create({ type: 'positive', message: '저장되었습니다.' })
  } catch (e: unknown) {
    dialog.value.error = getErrorMessage(e, '처리에 실패했습니다.')
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
    Notify.create({ type: 'positive', message: '삭제되었습니다.' })
  } catch (e: unknown) {
    dialog.value.error = getErrorMessage(e, '처리에 실패했습니다.')
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

    const startIso = DateTime.fromJSDate(ev.start, { zone: 'utc' }).toISO()
    const endIso = DateTime.fromJSDate(ev.end, { zone: 'utc' }).toISO()
    if (!startIso || !endIso) return

    const ext = isRecord(ev.extendedProps) ? ev.extendedProps : {}
    const version = (isRecord(ext) && typeof ext.version === 'number') ? ext.version : undefined

    await patchWatch(ev.id, { start: startIso, end: endIso, ...(version !== undefined ? { version } : {}) })
    refetchCalendar()
  } catch {
    info.revert?.()
    Notify.create({ type: 'negative', message: '수정에 실패하여 되돌렸습니다.' })
  }
}

async function createBulkForSlot(assignee: string, fromDate: string, toDate: string, sh: number, sm: number, eh: number, em: number) {
  if (!assignee.trim()) throw new Error('담당자를 입력해 주세요.')
  if (!fromDate || !toDate) throw new Error('시작일과 종료일을 입력해 주세요.')

  let cursor = DateTime.fromISO(fromDate, { zone: 'Asia/Seoul' })
  const end = DateTime.fromISO(toDate, { zone: 'Asia/Seoul' })

  if (cursor > end) throw new Error('종료일이 시작일보다 앞습니다.')

  // 해당 범위의 기존 일정을 미리 조회하여 startIso → id 맵 구성 (덮어쓰기용)
  const rangeStart = cursor.set({ hour: sh, minute: sm, second: 0, millisecond: 0 }).toUTC().toISO()
  const rangeEnd = end.set({ hour: eh, minute: em, second: 0, millisecond: 0 }).toUTC().toISO()
  const existing = rangeStart && rangeEnd
    ? await listWatch({ start: rangeStart, end: rangeEnd, include_deleted: false })
    : []
  const existingByStart = new Map(existing.map(r => [r.start, r]))

  while ((cursor.toISODate() ?? '') <= (end.toISODate() ?? '')) {
    // 평일(월~금)만 생성
    if (cursor.weekday <= 5) {
      const startKst = cursor.set({ hour: sh, minute: sm, second: 0, millisecond: 0 })
      const endKst = cursor.set({ hour: eh, minute: em, second: 0, millisecond: 0 })
      const startIso = startKst.toUTC().toISO()
      const endIso = endKst.toUTC().toISO()
      if (!startIso || !endIso) throw new Error('날짜/시간이 올바르지 않습니다.')
      const found = existingByStart.get(startIso)
      if (found) {
        await patchWatch(found.id, { assignee: assignee.trim(), version: found.version })
      } else {
        await createWatch({ assignee: assignee.trim(), start: startIso, end: endIso, fields: { note: '' } })
      }
    }
    cursor = cursor.plus({ days: 1 })
  }
}

async function createBulkA() {
  try {
    busy.value = true
    await createBulkForSlot(bulkA.value.assignee, bulkA.value.fromDate, bulkA.value.toDate, 11, 0, 12, 0)
    refetchCalendar()
    Notify.create({ type: 'positive', message: 'A타임 생성 완료' })
  } catch (e: unknown) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '처리에 실패했습니다.') })
  } finally {
    busy.value = false
  }
}

async function createBulkB() {
  try {
    busy.value = true
    await createBulkForSlot(bulkB.value.assignee, bulkB.value.fromDate, bulkB.value.toDate, 12, 0, 13, 0)
    refetchCalendar()
    Notify.create({ type: 'positive', message: 'B타임 생성 완료' })
  } catch (e: unknown) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '처리에 실패했습니다.') })
  } finally {
    busy.value = false
  }
}

/** Import */
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

function triggerImport() {
  importInput.value?.click()
}

function downloadTemplate() {
  const ws = XLSX.utils.aoa_to_sheet([
    ['구분 (A/B)', '담당자', '시작일', '종료일', '※ 날짜는 YYYY-MM-DD 형식으로 입력 / 구분은 A 또는 B만 허용'],
    ['A', '홍길동', '2026-05-01', '2026-05-31', ''],
    ['B', '김철수', '2026-05-01', '2026-05-31', ''],
  ])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '점심당직')
  XLSX.writeFile(wb, '점심당직_포맷.xlsx')
}

async function onImportFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  ;(e.target as HTMLInputElement).value = ''

  importing.value = true
  try {
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array', cellDates: false })
    const ws = wb.Sheets[wb.SheetNames[0]!]
    if (!ws) throw new Error('시트를 찾을 수 없습니다.')

    // raw: true → 날짜 셀은 Excel 시리얼 숫자로 받음 (타임존 없이 직접 변환)
    const allRows = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, defval: '' })
    const dataRows = allRows.slice(1) // 첫 행(헤더) 제거

    function toStr(val: unknown): string {
      if (val === null || val === undefined) return ''
      if (typeof val === 'string') return val
      if (typeof val === 'number') return String(val)
      return ''
    }

    function parseDateCell(val: unknown): string {
      // Excel 시리얼 숫자 → YYYY-MM-DD (타임존 변환 없이)
      if (typeof val === 'number') {
        const d = XLSX.SSF.parse_date_code(val)
        return `${d.y}-${String(d.m).padStart(2, '0')}-${String(d.d).padStart(2, '0')}`
      }
      // 문자열인 경우 YYYY-MM-DD 추출
      const s = toStr(val).trim().replace(/\//g, '-')
      const m = s.match(/(\d{4}-\d{2}-\d{2})/)
      return m ? m[1] ?? '' : ''
    }

    // 전체 기간의 기존 데이터를 미리 로드
    const allDates = dataRows
      .map(r => { const row = Array.isArray(r) ? r : []; return [parseDateCell(row[2]), parseDateCell(row[3])] })
      .filter(([f, t]) => f && t)
    const minDate = allDates.map(([f]) => f).sort()[0]
    const maxDate = allDates.map(([, t]) => t).sort().slice(-1)[0]

    const startParam = minDate ? (DateTime.fromISO(minDate, { zone: 'Asia/Seoul' }).startOf('day').toUTC().toISO() ?? undefined) : undefined
    const endParam = maxDate ? (DateTime.fromISO(maxDate, { zone: 'Asia/Seoul' }).endOf('day').toUTC().toISO() ?? undefined) : undefined
    const existingRows = startParam && endParam
      ? await listWatch({ start: startParam, end: endParam })
      : []

    // startISO → id 맵 (덮어쓰기 대상 찾기용)
    // ISO 형식 정규화 (Z vs +00:00, 밀리초 유무 차이 제거)
    function normalizeIso(iso: string): string {
      return DateTime.fromISO(iso, { zone: 'utc' }).toFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
    }
    const existingByStart = new Map(existingRows.map(r => [normalizeIso(r.start), r.id]))

    let created = 0
    let skipped = 0

    for (const rawRow of dataRows) {
      const row = Array.isArray(rawRow) ? rawRow : []
      const slot = toStr(row[0]).trim().toUpperCase()
      const assignee = toStr(row[1]).trim()
      const fromDate = parseDateCell(row[2])
      const toDate = parseDateCell(row[3])

      if (!slot || !assignee || !fromDate || !toDate) { skipped++; continue }
      if (slot !== 'A' && slot !== 'B') { skipped++; continue }

      const [sh, sm, eh, em] = slot === 'A' ? [11, 0, 12, 0] : [12, 0, 13, 0]

      let cursor = DateTime.fromISO(fromDate, { zone: 'Asia/Seoul' })
      const end = DateTime.fromISO(toDate, { zone: 'Asia/Seoul' })
      if (!cursor.isValid || !end.isValid || cursor > end) { skipped++; continue }

      while ((cursor.toISODate() ?? '') <= (end.toISODate() ?? '')) {
        if (cursor.weekday <= 5) {
          const startIso = cursor.set({ hour: sh, minute: sm, second: 0, millisecond: 0 }).toUTC().toISO()
          const endIso = cursor.set({ hour: eh, minute: em, second: 0, millisecond: 0 }).toUTC().toISO()
          if (startIso && endIso) {
            const key = normalizeIso(startIso)
            const existingId = existingByStart.get(key)
            if (existingId) {
              // 기존 항목이 있으면 담당자만 업데이트
              const updated = await patchWatch(existingId, { assignee })
              existingByStart.set(key, updated.id)
            } else {
              // 없으면 새로 생성
              const created_ = await createWatch({ assignee, start: startIso, end: endIso, fields: { note: '' } })
              existingByStart.set(key, created_.id)
            }
            created++
          }
        }
        cursor = cursor.plus({ days: 1 })
      }
    }

    refetchCalendar()
    Notify.create({ type: 'positive', message: `Import 완료: ${created}건 생성${skipped ? `, ${skipped}행 건너뜀` : ''}` })
  } catch (e: unknown) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Import 실패') })
  } finally {
    importing.value = false
  }
}

// 드로어 토글 시 캘린더 크기 재계산
let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  const el = document.querySelector('.q-page')
  if (!el) return
  resizeObserver = new ResizeObserver(() => {
    calendarRef.value?.getApi?.()?.updateSize()
  })
  resizeObserver.observe(el)
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

const calendarOptions = ref<CalendarOptions>({
  plugins: [timeGridPlugin, dayGridPlugin, interactionPlugin, luxonPlugin],
  timeZone: 'Asia/Seoul',
  initialView: 'timeGridWeek',
  selectable: true,
  editable: true,
  nowIndicator: true,
  height: 'auto',
  weekends: false,
  slotMinTime: '11:00:00',
  slotMaxTime: '13:00:00',

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
          err instanceof Error ? err : new Error('일정을 불러오지 못했습니다.')
        )
      })
  },

  select: (arg) => openCreate(arg.start),
  eventClick: (arg) => openEdit(arg),
  eventDrop: (info) => { void onMoveOrResize(info) },
  eventResize: (info) => { void onMoveOrResize(info)}
})
</script>
