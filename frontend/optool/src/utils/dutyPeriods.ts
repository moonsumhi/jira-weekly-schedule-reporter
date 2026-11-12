export interface DutyAssignment { id: string; assignee: string; start: string; end: string }

export interface DutyShift extends DutyAssignment {
  startMs: number
  endMs: number
  startDay: number
  endDay: number
}

export interface DutyPeriod {
  id: string
  startMs: number
  endMs: number
  startDay: number
  endDay: number
  days: number
  shifts: DutyShift[]
}

const DAY_MS = 86_400_000
const KST_OFFSET = 9 * 60 * 60 * 1000
export const DUTY_RANGE_DAYS = 30

export function dutyDayKey(timestamp: number): number {
  return Math.floor((timestamp + KST_OFFSET) / DAY_MS) * DAY_MS
}

function timestamp(iso: string): number {
  // The API also returns naive UTC timestamps.
  return Date.parse(/Z|[+-]\d{2}:?\d{2}$/i.test(iso) ? iso : `${iso}Z`)
}

export function groupDutyPeriods(assignments: DutyAssignment[]): DutyPeriod[] {
  const shifts = [...new Map(assignments.map(item => [item.id, item])).values()]
    .map(item => {
      const startMs = timestamp(item.start)
      const endMs = timestamp(item.end)
      return { ...item, startMs, endMs, startDay: dutyDayKey(startMs), endDay: dutyDayKey(endMs - 1) }
    })
    .filter(item => Number.isFinite(item.startMs) && Number.isFinite(item.endMs) && item.endMs > item.startMs)
    .sort((a, b) => a.startMs - b.startMs || a.id.localeCompare(b.id))

  const periods: DutyPeriod[] = []
  for (const shift of shifts) {
    const last = periods[periods.length - 1]
    if (last && shift.startDay <= last.endDay + DAY_MS) {
      last.shifts.push(shift)
      last.endMs = Math.max(last.endMs, shift.endMs)
      last.endDay = Math.max(last.endDay, shift.endDay)
      last.days = (last.endDay - last.startDay) / DAY_MS + 1
    } else {
      periods.push({
        id: shift.id, startMs: shift.startMs, endMs: shift.endMs,
        startDay: shift.startDay, endDay: shift.endDay,
        days: (shift.endDay - shift.startDay) / DAY_MS + 1, shifts: [shift],
      })
    }
  }
  return periods
}

export function nextDutyPeriod(periods: DutyPeriod[], now: number): DutyPeriod | undefined {
  const lastDay = dutyDayKey(now) + DUTY_RANGE_DAYS * DAY_MS
  return periods.find(period => period.endMs > now && period.startDay <= lastDay)
}

export function dutyPeriodStatus(period: DutyPeriod, now: number): string {
  if (now >= period.endMs) return '종료'
  if (now >= period.startMs) return '당직 중'
  const days = (period.startDay - dutyDayKey(now)) / DAY_MS
  return days === 0 ? 'D-Day' : `D-${days}`
}

type FetchDutyRange = (params: { start: string; end: string }) => Promise<DutyAssignment[]>

/** Keep the nearest period whole, even when it crosses the dashboard's date window. */
export async function loadDashboardDuties(fetchRange: FetchDutyRange, isMine: (assignee: string) => boolean, now: number): Promise<DutyAssignment[]> {
  const today = dutyDayKey(now)
  let from = today - DUTY_RANGE_DAYS * DAY_MS
  let through = today + DUTY_RANGE_DAYS * DAY_MS
  const records = new Map<string, DutyAssignment>()
  async function load(firstDay: number, lastDay: number) {
    const items = await fetchRange({
      start: new Date(firstDay - KST_OFFSET).toISOString(),
      end: new Date(lastDay + DAY_MS - KST_OFFSET - 1).toISOString(),
    })
    for (const item of items) records.set(item.id, item)
  }
  await load(from, through)
  while (true) {
    const own = [...records.values()].filter(item => isMine(item.assignee))
    const period = nextDutyPeriod(groupDutyPeriods(own), now)
    if (!period) break
    if (period.startDay <= from) {
      const earlier = Math.min(from, period.startDay) - DUTY_RANGE_DAYS * DAY_MS
      await load(earlier, from - DAY_MS)
      from = earlier
    } else if (period.endDay >= through) {
      const later = Math.max(through, period.endDay) + DUTY_RANGE_DAYS * DAY_MS
      await load(through + DAY_MS, later)
      through = later
    } else {
      break
    }
  }
  return [...records.values()]
}
