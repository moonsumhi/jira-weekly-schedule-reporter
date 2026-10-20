import audit from 'src/data/lifecycle_audit.json'
import type { EosActionStatus } from 'src/types/assets'

export type LifecycleEvidence = { date: string; source: string; basis: string; note: string; dateKind?: string; scope?: string; milestone?: { date: string; basis: string; source: string; note: string } }
export const softwareEvidence: Record<string, LifecycleEvidence> = audit.software
export const softwareAliases: Record<string, string> = audit.softwareAliases
export const REVIEW_NOTE = '정확한 모델·버전·지원 종류와 제조사 공지를 확인해야 합니다.'

export function supportStatus(end: string, today = new Date().toISOString().slice(0, 10)): EosActionStatus {
  if (!end || (end.length === 7 && end === today.slice(0, 7))) return 'REVIEW_REQUIRED'
  return end < today.slice(0, end.length) ? 'EOS' : 'ACTIVE'
}

export function reviewedEosMap(_candidate: Record<string, string>): Record<string, string> {
  void _candidate // Keep the existing API; external values are deliberately ignored.
  const result: Record<string, string> = Object.fromEntries(
    Object.entries(audit.technicalGuidance).filter(([, entry]) => entry.date && entry.source)
      .map(([key, entry]) => [key, entry.date]),
  )
  for (const [key, entry] of Object.entries(softwareEvidence)) {
    if (entry.dateKind === 'service_end' && entry.date && entry.source) {
      result[key] = entry.date.slice(0, 7)

    }
    if (/^(ESXi|vCenter)\|/.test(key) && entry.milestone?.date) result[`${key}|generalSupport`] = entry.milestone.date
  }
  return result
}
