import type { EosActionStatus } from 'src/types/assets'
import { DBMS_TREE } from 'src/constants/dbmsVersions'
import { OS_TREE } from 'src/constants/osVersions'
import { NETWORK_EOS_LIST, NETWORK_MANUAL_LIST } from 'src/constants/networkEos'
import { getEosMap } from 'src/services/eosData'

// ── OS 탐지 ──────────────────────────────────────────────────────────────────

/** 공백·하이픈 제거 + 소문자 정규화 (예: "Rocky Linux" → "rockylinux") */
function norm(s: string): string {
  return s.replace(/[\s\-_]/g, '').toLowerCase()
}

/** 정규화된 이름으로 OS_TREE 배포판 키를 찾아 정확한 키 반환 */
export function resolveDistName(osName: string): string {
  const n = norm(osName)
  for (const dists of Object.values(OS_TREE)) {
    for (const key of Object.keys(dists)) {
      if (norm(key) === n) return key
    }
  }
  return osName
}

export function detectOsFamily(osName: string): string {
  const n = norm(osName)
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
  const majors = osMajorOptions(dist)
  if (majors.includes(version)) return version
  for (const major of majors) {
    if (osMinorOptions(dist, major).includes(version)) return major
  }
  return ''
}

// ── EoS 날짜 조회 ─────────────────────────────────────────────────────────────

function lookupEosDate(key: string): string | undefined {
  return getEosMap()[key]
}

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

export function getAutoEos(dist: string, version: string): { status: EosActionStatus; date: string } | null {
  // fields는 느슨한 타입이라 실제로는 문자열이 아닌 값(숫자 등)이 들어올 수 있음
  dist = String(dist ?? '')
  version = String(version ?? '')
  if (!dist || !version) return null
  let eosDate = lookupEosDate(`${dist}|${version}`)
  if (!eosDate) {
    const parent = version.includes('.') ? version.slice(0, version.lastIndexOf('.')) : null
    if (parent) eosDate = lookupEosDate(`${dist}|${parent}`)
  }
  // Oracle/SAP HANA처럼 실제 패치 버전과 지원주기 이름의 형식이 다른 DBMS는
  // 드롭다운 트리에서 소속 시리즈를 찾아 다시 조회한다.
  if (!eosDate) {
    const series = Object.entries(DBMS_TREE[dist] ?? {}).find(([, patches]) => patches.includes(version))?.[0]
    if (series) eosDate = lookupEosDate(`${dist}|${series}`)
  }
  if (!eosDate) return null
  const today = new Date().toISOString().slice(0, 7)
  // 계열 자체의 종료일이 지났다면 마이너 버전을 몰라도 EoS로 확정할 수 있다.
  if (eosDate <= today) return { status: 'EOS', date: eosDate }
  if (requiresMinorVersion(resolveDistName(dist), version)) {
    return { status: 'VERSION_REQUIRED', date: eosDate }
  }
  if (isMaintenancePhase(dist, version, today)) {
    return { status: 'MAINTENANCE', date: eosDate }
  }
  return { status: 'ACTIVE', date: eosDate }
}

// ── 네트워크 장비 EoS 탐지 ────────────────────────────────────────────────────

export function normalizeModel(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, '')
}

export function getNetworkEos(
  model: string
): { status: EosActionStatus; date: string; matchedLabel: string } | null {
  if (!model.trim()) return null
  const normalized = normalizeModel(model)
  const today = new Date().toISOString().slice(0, 7)

  // 날짜 기반 목록 (긴 패턴 우선)
  const sorted = [...NETWORK_EOS_LIST].sort((a, b) => b.pattern.length - a.pattern.length)
  const entry = sorted.find(e => normalized.includes(e.pattern))
  if (entry) {
    return { status: entry.date <= today ? 'EOS' : 'ACTIVE', date: entry.date, matchedLabel: entry.label }
  }

  // 날짜 없이 상태만 알려진 목록 (긴 패턴 우선)
  const sortedManual = [...NETWORK_MANUAL_LIST].sort((a, b) => b.pattern.length - a.pattern.length)
  const manual = sortedManual.find(e => normalized.includes(e.pattern))
  if (manual) {
    return { status: manual.status, date: '', matchedLabel: manual.label }
  }

  return null
}
