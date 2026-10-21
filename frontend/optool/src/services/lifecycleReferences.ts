import manifest from 'src/data/lifecycle_references.json'
import { getAutoEos, getNetworkEos } from 'src/services/eosDetection'
import { getAutoEol } from 'src/services/eolData'
import { DBMS_TREE } from 'src/constants/dbmsVersions'
import type { LifecycleEvidence } from 'src/services/lifecycleAudit'

export type ReferenceDocument = {
  path: string
  title: string
  kind: 'original_pdf' | 'web_capture' | 'data_extract'
  capturedAt: string
  sha256: string
  archiveNote?: string
}
const references = manifest as Record<string, ReferenceDocument | { unavailableReason: string }>

/** 외부 URL은 출처 식별용으로만 사용한다. 화면에서는 배포본에 포함된 PDF만 연다. */
export function localLifecycleDocument(source?: string): ReferenceDocument | null {
  const document = source ? references[source] : undefined
  return document && 'path' in document && /^\/reference\/[a-zA-Z0-9_/-]+\.pdf$/.test(document.path) ? document : null
}

export function lifecycleDocumentNotice(source?: string): string {
  const document = source ? references[source] : undefined
  return document && 'unavailableReason' in document ? document.unavailableReason : ''
}

export function assetLifecycleEvidence(fields: Record<string, unknown> | undefined, kind: 'eos' | 'eol'): Partial<LifecycleEvidence> | null {
  const text = (value: unknown) => typeof value === 'string' || typeof value === 'number' ? String(value) : ''
  const product = text(fields?.['운영체제'])
  const version = text(fields?.['version'])
  if (!product) return null
  const series = Object.keys(DBMS_TREE[product] ?? {}).find(key => DBMS_TREE[product]?.[key]?.includes(version))
  if (kind === 'eol') return getAutoEol(product, version) ?? (series ? getAutoEol(product, series) : null)
  return getAutoEos(product, version) ?? (series ? getAutoEos(product, series) : null) ?? getNetworkEos(product)
}
