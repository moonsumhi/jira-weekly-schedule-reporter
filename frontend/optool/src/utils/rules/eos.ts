import { eosStatusOptions, type EosActionStatus } from 'src/types/assets'

function toUpperString(v: unknown): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'string') return v.toUpperCase()
  if (typeof v === 'number' || typeof v === 'boolean') return String(v).toUpperCase()
  // object/array는 string으로 만들지 않음 (eslint no-base-to-string 회피)
  return ''
}

export function eosStatusLabel(v: unknown): string {
  const s = toUpperString(v)
  if (s === 'NONE') return '미조치'
  if (s === 'PLAN') return '계획'
  if (s === 'DOING') return '진행'
  if (s === 'DONE') return '완료'
  if (s === 'EXCEPTION') return '예외'
  return '-'
}

export function eosStatusColor(v: unknown): string {
  const s = toUpperString(v)
  if (s === 'DONE') return 'positive'
  if (s === 'DOING' || s === 'PLAN') return 'warning'
  if (s === 'EXCEPTION') return 'grey'
  if (s === 'NONE') return 'negative'
  return 'grey'
}

export function normalizeEosStatus(v: unknown): EosActionStatus | null {
  const s = toUpperString(v)
  const allowed = new Set<EosActionStatus>(eosStatusOptions.map((x) => x.value))
  return allowed.has(s as EosActionStatus) ? (s as EosActionStatus) : null
}
