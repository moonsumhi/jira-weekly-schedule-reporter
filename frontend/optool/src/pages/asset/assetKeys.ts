// 자산 fields 키 상수 — 컴포넌트와 설정 모듈이 공유한다.
export const VADA_KEY = 'vada_installed' as const
export const ELASTIC_KEY = 'elastic_installed' as const
export const ANTIVIRUS_KEY = 'antivirus_installed' as const
export const ISMS_P_KEY = 'isms_p_target' as const
export const TAGS_KEY = 'tags' as const
export const EOL_STATUS_KEY = 'eol_status' as const
export const EOL_DATE_KEY = 'eol_date' as const

export function isExtendedAssetCategory(category: unknown): boolean {
  return category === '스토리지' || category === '소프트웨어'
}

export function isFreeformAssetProduct(category: unknown): boolean {
  return category === '네트워크' || category === '정보보호시스템' || isExtendedAssetCategory(category)
}

export function assetProductLabel(category: unknown): string {
  if (category === '소프트웨어') return '제품명'
  if (isFreeformAssetProduct(category)) return '기종'
  return category === 'DBMS' ? 'DBMS' : '운영체제'
}
