// Registration, editing and Excel use the same field names and value types.
export type AssetDetailField = {
  key: string; label: string; options?: string[]; type?: 'number' | 'date' | 'multi';
  hint?: string; unitKey?: string; integer?: boolean; periodOnly?: boolean
}
export const STORAGE_TYPES = ['SAN', 'NAS', 'DAS', '통합형', '기타']
export const CAPACITY_UNITS = ['GB', 'TB', 'PB', 'GiB', 'TiB', 'PiB']
export const PERIOD_LICENSES = ['구독', '기간제', '평가판']
export const LINKED_ASSET_KEY = '연결자산'
export const STORAGE_FIELDS: AssetDetailField[] = [
  { key: '총물리용량', label: '총 물리 용량', type: 'number', unitKey: '총물리용량단위' },
  { key: '사용가능용량', label: '사용 가능 용량', type: 'number', unitKey: '사용가능용량단위', hint: 'RAID 등을 적용한 후 데이터를 저장할 수 있는 용량' },
  { key: '연결방식', label: '연결 방식', type: 'multi', options: ['FC', 'iSCSI', 'NFS', 'SMB', 'SAS', 'NVMe-oF', '기타'] },
  { key: '디스크유형', label: '디스크 유형', options: ['SSD', 'HDD', '혼합', '기타'] },
  { key: '디스크수량', label: '디스크 수량', type: 'number', integer: true },
  { key: '디스크개별용량', label: '디스크 개별 용량', type: 'number', unitKey: '디스크개별용량단위', hint: '용량이 서로 다르면 아래 구성 메모에 기록하세요.' },
  { key: 'RAID구성', label: 'RAID 구성', options: ['RAID 0', 'RAID 1', 'RAID 5', 'RAID 6', 'RAID 10', 'RAID 50', 'RAID 60', '기타'] },
  { key: '컨트롤러이중화', label: '컨트롤러 이중화', options: ['이중화', '단일', '해당 없음'] },
  { key: '스토리지구성메모', label: '구성 메모' },
]
export const SOFTWARE_FIELDS: AssetDetailField[] = [
  { key: '에디션', label: '에디션', hint: '예: Standard, Enterprise' },
  { key: '도입형태', label: '도입 형태', options: ['설치형', 'SaaS'] },
  { key: '사용권형태', label: '사용권 형태', options: ['영구', '구독', '기간제', '평가판', '무상', '오픈소스', '기타'] },
  { key: '라이선스기준', label: '라이선스 기준', options: ['사용자', '장치', '서버', '코어', '프로세서', '동시접속', '사이트', '기타'] },
  { key: '라이선스수량', label: '보유 수량', type: 'number', hint: '선택한 라이선스 기준에 따른 수량' },
  { key: '사용시작일', label: '사용 시작일', type: 'date' },
  { key: '사용권만료일', label: '사용권 만료일', type: 'date', periodOnly: true, hint: '유지보수 종료일과 별도로 관리합니다.' },
  { key: '라이선스식별번호', label: '계약·라이선스 식별번호' },
]
export const SOFTWARE_USAGE_FIELDS: AssetDetailField[] = [
  { key: '사용부서', label: '사용 부서' }, { key: '사용서비스', label: '사용 서비스' },
]
export const ALL_DETAIL_FIELDS = [...STORAGE_FIELDS, ...SOFTWARE_FIELDS, ...SOFTWARE_USAGE_FIELDS]
export const DETAIL_FIELD_KEYS = new Set([...ALL_DETAIL_FIELDS.flatMap(f => [f.key, ...(f.unitKey ? [f.unitKey] : [])]), LINKED_ASSET_KEY])
export function detailFieldsFor(category: unknown): AssetDetailField[] {
  return category === '스토리지' ? STORAGE_FIELDS : category === '소프트웨어' ? SOFTWARE_FIELDS : []
}
export function detailList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).filter(Boolean)
  if (typeof value !== 'string' || !value.trim()) return []
  try { const parsed: unknown = JSON.parse(value); if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean) } catch { /* Excel also accepts comma-separated values. */ }
  return value.split(/[,;\n]/).map(v => v.trim()).filter(Boolean)
}
export function detailEditValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return value == null ? '' : JSON.stringify(value) ?? ''
}
export function detailPayload(values: Record<string, string>, category: unknown): Record<string, string | number | string[] | null> {
  if (category !== '스토리지' && category !== '소프트웨어') return {}
  const result: Record<string, string | number | string[] | null> = {}
  const specs = [...detailFieldsFor(category), ...(category === '소프트웨어' ? SOFTWARE_USAGE_FIELDS : [])]
  for (const f of specs) {
    const value = (values[f.key] ?? '').trim()
    result[f.key] = f.type === 'multi' ? detailList(value) : value || null
    if (f.type === 'number' && value && Number.isFinite(Number(value))) result[f.key] = Number(value)
    if (f.unitKey) result[f.unitKey] = values[f.unitKey] || (value ? 'TB' : null)
  }
  if (category === '소프트웨어' && values['사용권형태'] && !PERIOD_LICENSES.includes(values['사용권형태'])) result['사용권만료일'] = null
  result[LINKED_ASSET_KEY] = detailList(values[LINKED_ASSET_KEY])
  return result
}
