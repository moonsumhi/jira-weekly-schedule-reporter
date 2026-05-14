import type { EosActionStatus } from 'src/types/assets'
import { OS_TREE } from 'src/constants/osVersions'
import { NETWORK_EOS_LIST, NETWORK_MANUAL_LIST } from 'src/constants/networkEos'
import { getEosMap } from 'src/services/eosData'

// ── OS 탐지 ──────────────────────────────────────────────────────────────────

export function detectOsFamily(osName: string): string {
  for (const [family, dists] of Object.entries(OS_TREE)) {
    if (osName in dists) return family
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

export function getAutoEos(dist: string, version: string): { status: EosActionStatus; date: string } | null {
  if (!dist || !version) return null
  let eosDate = lookupEosDate(`${dist}|${version}`)
  if (!eosDate) {
    const parent = version.includes('.') ? version.slice(0, version.lastIndexOf('.')) : null
    if (parent) eosDate = lookupEosDate(`${dist}|${parent}`)
  }
  if (!eosDate) return null
  const today = new Date().toISOString().slice(0, 7)
  return { status: eosDate <= today ? 'EOS' : 'ACTIVE', date: eosDate }
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
