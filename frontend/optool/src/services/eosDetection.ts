import type { EosActionStatus } from 'src/types/assets'
import { OS_TREE } from 'src/constants/osVersions'
import { NETWORK_EOS_LIST } from 'src/constants/networkEos'
import { softwareEvidence, softwareAliases, supportStatus, REVIEW_NOTE, type LifecycleEvidence } from 'src/services/lifecycleAudit'
import { normalizeCiscoSoftware } from 'src/services/ciscoLifecycle'
import { normalizeVmware } from 'src/services/vmwareLifecycle'

// ── OS 탐지 ──────────────────────────────────────────────────────────────────

/** 공백·하이픈 제거 + 소문자 정규화 (예: "Rocky Linux" → "rockylinux") */
function norm(s: string): string {
  return s.replace(/[\s\-_]/g, '').toLowerCase()
}

/** 정규화된 이름으로 OS_TREE 배포판 키를 찾아 정확한 키 반환 */
export function resolveDistName(osName: string): string {
  const vmware = normalizeVmware(osName)
  if (vmware) return vmware.dist
  const n = norm(osName)
  for (const dists of Object.values(OS_TREE)) {
    for (const key of Object.keys(dists)) {
      if (norm(key) === n) return key
    }
  }
  return osName
}

export function detectOsFamily(osName: string): string {
  const n = norm(resolveDistName(osName))
  for (const [family, dists] of Object.entries(OS_TREE)) {
    for (const key of Object.keys(dists)) {
      if (norm(key) === n) return family
    }
  }
  return ''
}

export function osDistOptions(family: string): string[] {
  return Object.keys(OS_TREE[family] ?? {})
}

export function osMajorOptions(dist: string): string[] {
  for (const dists of Object.values(OS_TREE)) {
    if (dist in dists) return Object.keys(dists[dist] ?? {})
  }
  return []
}

export function osMinorOptions(dist: string, major: string): string[] {
  for (const dists of Object.values(OS_TREE)) {
    if (dist in dists) return (dists[dist] ?? {})[major] ?? []
  }
  return []
}

export function detectOsMajor(dist: string, version: string): string {
  const vmware = normalizeCiscoSoftware(dist, version) ?? normalizeVmware(dist, version)
  if (vmware) ({ dist, version } = vmware)
  const majors = osMajorOptions(dist)
  if (majors.includes(version)) return version
  for (const major of majors) {
    if (osMinorOptions(dist, major).includes(version)) return major
  }
  return ''
}

// ── EoS 날짜 조회 ─────────────────────────────────────────────────────────────

/**
 * 마이너 버전 목록이 있는 제품에서 메이저 버전만 고른 경우에는 실제 설치된
 * 마이너 버전의 지원 여부를 확정할 수 없다. 계열 종료일은 보여주되 지원 중으로
 * 단정하지 않는다.
 */
export function requiresMinorVersion(dist: string, version: string): boolean {
  return osMajorOptions(dist).includes(version) && osMinorOptions(dist, version).length > 0
}

/** Rocky Linux 8은 8.10부터 계열 종료일까지 보안 유지보수 단계다. */
function isMaintenancePhase(dist: string, version: string, today: string): boolean {
  return resolveDistName(dist) === 'Rocky Linux'
    && version === '8.10'
    && today >= '2024-05'
}

export function getAutoEos(dist: string, version: string): (LifecycleEvidence & { status: EosActionStatus }) | null {
  dist = String(dist ?? '')
  version = String(version ?? '')
  const vmware = normalizeCiscoSoftware(dist, version) ?? normalizeVmware(dist, version)
  if (vmware) ({ dist, version } = vmware)
  dist = resolveDistName(dist)
  if (!dist) return null
  // Only explicitly enumerated versions may inherit a series policy.
  const evidence = softwareEvidence[`${dist}|${version}`] ?? softwareEvidence[softwareAliases[`${dist}|${version}`] ?? '']
  if (!evidence) {
    const known = Object.keys(softwareEvidence).some(key => key.startsWith(`${dist}|`))
    return known ? { status: 'REVIEW_REQUIRED', date: '', source: '', basis: '', note: REVIEW_NOTE }
      : NETWORK_EOS_LIST.some(e => e.aliases.includes(normalizeModel(dist).replace(/^cisco/, '').replace(/^nexus/, ''))) ? getNetworkEos(dist) : null
  }
  const today = new Date().toISOString().slice(0, 10)
  const end = evidence.dateKind === 'service_end' ? evidence.date : ''
  let status = supportStatus(end, today)
  if (status === 'ACTIVE' && requiresMinorVersion(dist, version)) status = 'VERSION_REQUIRED'
  if (status === 'ACTIVE' && isMaintenancePhase(dist, version, today)) status = 'MAINTENANCE'
  return { ...evidence, date: end.slice(0, 7), status }
}

// ── 네트워크 장비 EoS 탐지 ────────────────────────────────────────────────────

export function normalizeModel(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export function getNetworkEos(model: string): {
  status: EosActionStatus; date: string; matchedLabel: string; source: string; basis: string; note: string; milestones?: Array<{date: string; basis: string; source: string}>
} | null {
  if (!model.trim()) return null
  const normalized = normalizeModel(model).replace(/^cisco/, '').replace(/^nexus/, '')
  const entry = NETWORK_EOS_LIST.find(e => e.aliases.includes(normalized))
  if (!entry) return { status: 'REVIEW_REQUIRED', date: '', matchedLabel: model, source: '', basis: '', note: REVIEW_NOTE }
  const end = entry.dateKind === 'service_end' ? entry.date : ''
  return { ...entry, status: supportStatus(end), date: end.slice(0, 7), matchedLabel: entry.label,
    source: entry.source, basis: entry.basis, note: entry.note }
}
