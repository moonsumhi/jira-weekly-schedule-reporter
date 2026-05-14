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
  if (s === 'ACTIVE') return '지원 기간 중'
  if (s === 'EOS') return 'EoS 지남'
  return '확인 불가'
}

export function eosStatusColor(v: unknown): string {
  const s = toUpperString(v)
  if (s === 'ACTIVE') return 'positive'
  if (s === 'EOS') return 'negative'
  return 'grey'
}

export function normalizeEosStatus(v: unknown): EosActionStatus | null {
  const s = toUpperString(v)
  const allowed = new Set<EosActionStatus>(eosStatusOptions.map((x) => x.value))
  return allowed.has(s as EosActionStatus) ? (s as EosActionStatus) : null
}
