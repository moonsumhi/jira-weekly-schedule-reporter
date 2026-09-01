import { api } from 'boot/axios'

// endoflife.date에 없는 제품 — 하드코딩 폴백
// Rocky Linux / RHEL / CentOS 는 endoflife.date가 마이너 버전 단위로만 사이클을 제공하며
// 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 추가한다.
const STATIC_FALLBACK: Record<string, string> = {
  // Rocky Linux (https://wiki.rockylinux.org/rocky/version/)
  'Rocky Linux|8':    '2029-05',
  'Rocky Linux|8.3':  '2021-06',
  'Rocky Linux|8.4':  '2021-11',
  'Rocky Linux|8.5':  '2022-05',
  'Rocky Linux|8.6':  '2022-11',
  'Rocky Linux|8.7':  '2023-05',
  'Rocky Linux|8.8':  '2023-11',
  'Rocky Linux|8.9':  '2024-05',
  'Rocky Linux|8.10': '2029-05',
  'Rocky Linux|9': '2032-05',
  // RHEL (Red Hat Maintenance Support 2 end date)
  'RHEL|7': '2024-06',
  'RHEL|8': '2029-05',
  'RHEL|9': '2032-05',
  // CentOS
  'CentOS|6': '2020-11',
  'CentOS|7': '2024-06',
  'CentOS|8': '2021-12',
  // Oracle DB (endoflife.date 미수록)
  'Oracle|12c R1': '2022-07',
  'Oracle|12c R2': '2022-03',
  'Oracle|19c':    '2027-04',
  'Oracle|21c':    '2024-04',
  'Oracle|23c':    '2030-04',
  // SAP HANA
  'SAP HANA|1.0':  '2023-12',
  'SAP HANA|2.0':  '2030-12',
}

let _cache: Record<string, string> | null = null

export async function fetchEosMap(): Promise<Record<string, string>> {
  if (_cache) return _cache
  try {
    const { data } = await api.get<Record<string, string>>('/assets/eos-map')
    _cache = { ...STATIC_FALLBACK, ...data }
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
