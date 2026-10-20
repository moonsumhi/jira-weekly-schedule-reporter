import { api } from 'boot/axios'
import vmwareLifecycleSnapshot from 'src/data/vmware_lifecycle_snapshot.json'

import { reviewedEosMap } from 'src/services/lifecycleAudit'

const STATIC_FALLBACK = reviewedEosMap(vmwareLifecycleSnapshot)

let _cache: Record<string, string> | null = null

export async function fetchEosMap(): Promise<Record<string, string>> {
  if (_cache) return _cache
  try {
    const { data } = await api.get<Record<string, string>>('/assets/eos-map')
    _cache = reviewedEosMap({ ...STATIC_FALLBACK, ...data })
    return _cache
  } catch (e) {
    // 실패를 _cache에 영구 저장하지 않는다 — 그러면 이후 호출이 전부
    // if (_cache) return _cache 로 걸려서 API가 복구돼도 재시도조차 안 됨.
    // 폴백 목록만 반환하고, 다음 호출에서 다시 API를 시도한다.
    console.warn('[eos] fetch failed, using static fallback only (will retry next call)', e)
    return { ...STATIC_FALLBACK }
  }
}

export function getEosMap(): Record<string, string> {
  return _cache ?? STATIC_FALLBACK
}
