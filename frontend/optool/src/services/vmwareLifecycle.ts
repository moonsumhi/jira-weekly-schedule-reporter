import { getEosMap } from 'src/services/eosData'

/** 기존 엑셀/직접 입력 표기를 수집 API의 제품명과 지원 주기로 변환한다. */
export function normalizeVmware(dist: string, version = ''): { dist: string; version: string } | null {
  const match = dist.trim().match(/^(?:VMware\s+)?(ESXi|ESX|vCenter(?:\s+Server)?)(?:\s+(.+))?$/i)
  if (!match) return null
  const product = /^esx/i.test(match[1] ?? '') ? 'ESXi' : 'vCenter'
  const rawVersion = (version.trim() || match[2] || '').trim()
  // 7.0 U3, 7.0.3 등의 패치는 7.0 지원 주기에 속한다.
  // 메이저만 선택한 7, 7.x는 특정 마이너(7.0)로 추정하지 않는다.
  const cycle = rawVersion.match(/^v?(\d+)(?:\.(\d+|x))?(?=$|[\s.uU(-])/i)
  const normalized = cycle ? (!cycle[2] || cycle[2].toLowerCase() === 'x' ? cycle[1]! : `${cycle[1]}.${cycle[2]}`) : rawVersion
  return { dist: product, version: normalized }
}

export const VMWARE_GUIDANCE_NOTE = '기술 가이드는 유효한 기존 VMware 계약에만 적용되며 Broadcom 계약에는 적용되지 않습니다. 보안 패치 제공 기간을 의미하지 않습니다.'
export const VMWARE_GUIDANCE_SOURCE = 'https://ftpdocs.broadcom.com/cadocs/0/contentimages/Product_EOTG_Dates.pdf'

export function getVmwareGuidanceDate(dist: string, version = ''): string | null {
  const product = normalizeVmware(dist, version)
  return product ? getEosMap()[`${product.dist}|${product.version}|technicalGuidance`] ?? null : null
}

export function getVmwareGeneralSupportDate(dist: string, version: string, fallback = ''): string {
  const product = normalizeVmware(dist, version)
  return product ? getEosMap()[`${product.dist}|${product.version}|generalSupport`] ?? fallback : fallback
}

/** 날짜가 남아 있어도 계약 적용 여부를 알 수 없어 지원 중으로 단정하지 않는다. */
export function getVmwareGuidanceStatus(date: string | null): { label: string; color: string } {
  if (!date) return { label: '확인 불가', color: 'grey' }
  return date <= new Date().toISOString().slice(0, 10)
    ? { label: '기술 가이드 종료', color: 'negative' }
    : { label: '계약 확인 필요', color: 'warning' }
}
