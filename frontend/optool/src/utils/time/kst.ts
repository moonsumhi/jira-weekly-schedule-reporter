import {DateTime} from 'luxon'

export function toKSTPlusOneDay(utcString: string): string {
  return DateTime.fromISO(utcString, {zone: 'utc'})
    .setZone('Asia/Seoul')
    .plus({days: 1})
    .toFormat('yyyy-MM-dd')
}

export function toKSTDay(utcString: string): string {
  return DateTime.fromISO(utcString, {zone: 'utc'})
    .setZone('Asia/Seoul')
    .toFormat('yyyy-MM-dd')
}

export function formatKst(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR')
}

export function isDateSoon(dateVal: unknown, days: number): boolean {
  const s = typeof dateVal === 'string' ? dateVal : ''
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false

  const d = new Date(`${s}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return false

  const leftDays = (d.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  return leftDays <= days
}

/**
 * Convert JS Date -> datetime-local string in Asia/Seoul
 * Output: "YYYY-MM-DDTHH:mm"
 */
export function dateToKstDateTimeLocal(d: Date): string {
  return DateTime.fromJSDate(d)
    .setZone('Asia/Seoul')
    .toFormat("yyyy-LL-dd'T'HH:mm")
}

/**
 * Convert datetime-local string (interpreted as KST) -> ISO UTC string
 */
export function kstDateTimeLocalToUtcIso(local: string): string {
  // local: "YYYY-MM-DDTHH:mm"
  const dt = DateTime.fromFormat(local, "yyyy-LL-dd'T'HH:mm", { zone: 'Asia/Seoul' })
  if (!dt.isValid) throw new Error('Invalid date/time')
  return dt.toUTC().toISO()
}
