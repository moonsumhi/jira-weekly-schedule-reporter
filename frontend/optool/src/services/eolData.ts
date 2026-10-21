import { NETWORK_EOS_LIST } from 'src/constants/networkEos'
import audit from 'src/data/lifecycle_audit.json'
import { softwareAliases, supportStatus, REVIEW_NOTE, type LifecycleEvidence } from 'src/services/lifecycleAudit'
import { requiresMinorVersion, resolveDistName } from 'src/services/eosDetection'
import { normalizeCiscoSoftware } from 'src/services/ciscoLifecycle'
import { normalizeVmware } from 'src/services/vmwareLifecycle'

// EoL requires an explicit vendor life-end milestone; intermediate support phases are not EoL.
const EOL_EVIDENCE: Record<string, LifecycleEvidence> = audit.eol

export interface EolResult {
  /** 'O' = EoL 도달, 'X' = 미도달, VERSION_REQUIRED = 세부 버전 확인 필요 */
  status: 'O' | 'X' | 'VERSION_REQUIRED' | 'REVIEW_REQUIRED'
  source?: string
  basis?: string
  note?: string
  date: string
}

export function eolStatusLabel(v: unknown): string {
  const s = typeof v === 'string' ? v.toUpperCase() : ''
  if (s === 'O') return 'EoL 지남'
  if (s === 'X') return '지원 기간 중'
  if (s === 'VERSION_REQUIRED') return '세부 버전 확인 필요'
  if (s === 'REVIEW_REQUIRED') return '근거 확인 필요'
  return '확인 불가'
}

export function eolStatusColor(v: unknown): string {
  const s = typeof v === 'string' ? v.toUpperCase() : ''
  if (s === 'O') return 'negative'
  if (s === 'X') return 'positive'
  if (s === 'VERSION_REQUIRED' || s === 'REVIEW_REQUIRED') return 'warning'
  return 'grey'
}

export function getAutoEol(dist: string, version: string): EolResult | null {
  // fields는 느슨한 타입이라 실제로는 문자열이 아닌 값(숫자 등)이 들어올 수 있음
  dist = String(dist ?? '')
  version = String(version ?? '')
  if (!dist) return null

  // VMware는 일반 지원과 계약 조건부 기술 가이드를 별도로 표시한다.
  if (normalizeVmware(dist, version)) return null

  const cisco = normalizeCiscoSoftware(dist, version)
  if (cisco) ({ dist, version } = cisco)
  dist = resolveDistName(dist)
  const evidence = EOL_EVIDENCE[`${dist}|${version}`]
    ?? EOL_EVIDENCE[softwareAliases[`${dist}|${version}`] ?? '']
  if (!evidence) {
    const normalized = dist.toLowerCase().replace(/[^a-z0-9]/g, '').replace(/^cisco/, '').replace(/^nexus/, '')
    const hardware = NETWORK_EOS_LIST.find(row => row.aliases.includes(normalized))
    if (hardware && 'eolNote' in hardware) return { status: 'REVIEW_REQUIRED', date: '', source: hardware.source, note: hardware.eolNote }
    return Object.keys(EOL_EVIDENCE).some(key => key.startsWith(`${dist}|`))
      ? { status: 'REVIEW_REQUIRED', date: '', note: REVIEW_NOTE } : null
  }
  const end = evidence.dateKind === 'life_end' ? evidence.date : ''
  const status = supportStatus(end)
  const resultStatus = status === 'EOS' ? 'O' : status === 'REVIEW_REQUIRED' ? 'REVIEW_REQUIRED'
    : requiresMinorVersion(dist, version) ? 'VERSION_REQUIRED' : 'X'
  return { ...evidence, date: end.slice(0, 7), status: resultStatus }
}
