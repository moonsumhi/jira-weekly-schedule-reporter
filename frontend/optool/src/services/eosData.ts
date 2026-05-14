import { api } from 'boot/axios'

// endoflife.date에 없는 제품 — 하드코딩 폴백
// Rocky Linux / RHEL / CentOS 는 endoflife.date가 마이너 버전 단위로만 사이클을 제공하며
// 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 추가한다.
const STATIC_FALLBACK: Record<string, string> = {
  // Rocky Linux (https://rockylinux.org/news/rocky-linux-eol)
  'Rocky Linux|8': '2029-05',
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
  } catch (e) {
    console.warn('[eos] fetch failed, using static fallback only', e)
    _cache = { ...STATIC_FALLBACK }
  }
  return _cache
}

export function getEosMap(): Record<string, string> {
  return _cache ?? STATIC_FALLBACK
}
