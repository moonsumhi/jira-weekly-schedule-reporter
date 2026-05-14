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
  // 타임존 표기가 없으면 UTC로 강제 처리 (백엔드가 naive UTC 반환)
  const normalized = /Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z'
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })
}

export function isDateSoon(dateVal: unknown, days: number): boolean {
  const s = typeof dateVal === 'string' ? dateVal : ''
  // YYYY-MM-DD 또는 YYYY-MM 포맷 모두 허용
  let iso: string
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    iso = `${s}T00:00:00Z`
  } else if (/^\d{4}-\d{2}$/.test(s)) {
    iso = `${s}-01T00:00:00Z`
  } else {
    return false
  }

  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false

  const leftDays = (d.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  return leftDays <= days
}

/**
 * Convert JS Date -> datetime-local string in Asia/Seoul timezone
 * Output: "YYYY-MM-DDTHH:mm"
 *
 * FullCalendar passes Date objects representing actual UTC moments.
 * We convert from UTC to KST to display the correct wall-clock time.
 */
export function dateToKstDateTimeLocal(d: Date): string {
  return DateTime.fromJSDate(d, { zone: 'utc' })
    .setZone('Asia/Seoul')
    .toFormat("yyyy-LL-dd'T'HH:mm")
}

/**
 * Convert datetime-local string (interpreted as KST) -> ISO UTC string with 'Z' suffix.
 *
 * The datetime-local input always represents KST wall-clock time in this app.
 * This ensures the value is correctly stored as UTC on the backend.
 *
 * Bug reference (NCDC-490): Without explicit KST→UTC conversion, entering
 * "2026-01-12 00:00 KST" would register as "2026-01-11 15:00" (UTC leaked through).
 */
export function kstDateTimeLocalToUtcIso(local: string): string {
  // local: "YYYY-MM-DDTHH:mm" — always treated as KST regardless of browser locale
  const dt = DateTime.fromFormat(local, "yyyy-LL-dd'T'HH:mm", { zone: 'Asia/Seoul' })
  if (!dt.isValid) throw new Error('Invalid date/time')
  const iso = dt.toUTC().toISO({ suppressMilliseconds: true })
  if (!iso) throw new Error('Failed to serialize datetime')
  return iso
}
