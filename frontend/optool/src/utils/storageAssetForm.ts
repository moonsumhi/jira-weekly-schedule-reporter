import type { AssetFormField } from './assetFormFields'

export const STORAGE_IDENTITY: AssetFormField[] = [
  { key: '서버명', label: '자산명', required: true, placeholder: '예: 운영 파일 스토리지' },
  { key: '__name__', label: '호스트명', placeholder: '선택 · 장비에 설정된 호스트명이 있을 때 입력' },
  { key: '구분', label: '스토리지 유형', required: true, options: ['SAN', 'NAS', 'DAS', '통합형', '기타'] },
  { key: '자산번호', label: '자산번호', required: true, placeholder: '예: ST-001' },
  { key: '운영체제', label: '모델·기종', required: true, placeholder: '장비에 표기된 모델명' },
  { key: '__ip__', label: 'IP', placeholder: '예: 192.0.2.10', hint: 'IP가 없는 장비는 비워두세요.' },
  { key: '상태', label: '관리 상태', options: ['운영', '점검', '미사용', '폐기예정', '폐기'] },
  { key: '설명', label: '용도·설명', type: 'textarea', wide: true, required: true, placeholder: '예: 운영 서버의 공용 파일과 백업 데이터 저장' },
]
export const STORAGE_CAPACITY: AssetFormField[] = [
  { key: '총물리용량', label: '전체 디스크 용량', type: 'number', unitKey: '총물리용량단위', placeholder: '예: 24', hint: '장착된 디스크의 물리 용량 합계' },
  { key: '사용가능용량', label: '사용 가능 용량', type: 'number', unitKey: '사용가능용량단위', placeholder: '예: 18', hint: 'RAID 등을 적용한 후 저장할 수 있는 전체 용량' },
]
export const STORAGE_CONNECTION: AssetFormField[] = [
  { key: '연결방식', label: '연결 방식', type: 'multi', options: ['FC', 'iSCSI', 'NFS', 'SMB', 'SAS', 'NVMe-oF', '기타'], hint: '장비에서 사용하는 방식을 모두 선택하세요.' },
]
export const STORAGE_HARDWARE: AssetFormField[] = [
  { key: '제조사', label: '제조사', placeholder: '장비 제조사' },
  { key: 'version', label: '펌웨어 버전', placeholder: '예: 1.10' },
  { key: 'SN', label: '시리얼 번호' },
  { key: '자산관리번호', label: '추가 관리번호' },
  { key: '디스크유형', label: '디스크 유형', options: ['SSD', 'HDD', '혼합', '기타'] },
  { key: '디스크수량', label: '디스크 수량', type: 'number', integer: true, placeholder: '예: 12' },
  { key: '디스크개별용량', label: '디스크 1개 용량', type: 'number', unitKey: '디스크개별용량단위', hint: '용량이 서로 다르면 아래 구성 메모에 기록하세요.' },
  { key: 'RAID구성', label: 'RAID 구성', options: ['RAID 0', 'RAID 1', 'RAID 5', 'RAID 6', 'RAID 10', 'RAID 50', 'RAID 60', '기타'] },
  { key: '컨트롤러이중화', label: '컨트롤러 구성', options: ['이중화', '단일', '해당 없음'] },
  { key: '스토리지구성메모', label: '구성 메모', type: 'textarea', wide: true, placeholder: '예: SSD 2 TB × 12개, 예비 디스크 1개 포함' },
]
export const STORAGE_PURCHASE: AssetFormField[] = [
  { key: '도입사업', label: '도입 사업' }, { key: '납품회사', label: '구매·납품 업체' },
  { key: '담당자', label: '담당자' }, { key: '도입가격', label: '도입 가격 (원)', type: 'number' },
  { key: '도입일자', label: '도입일', type: 'date' },
  { key: '유지보수계약구분', label: '유지보수 계약 구분', options: ['유상', '무상', '해당 없음'] },
  { key: '유지보수종료일자', label: '유지보수 종료일', type: 'date' },
  { key: '유지보수업체', label: '유지보수 업체' }, { key: '유지보수연락처', label: '유지보수 연락처' },
  { key: '유지보수특이사항', label: '유지보수 메모', type: 'textarea', wide: true },
  { key: '비고', label: '비고', type: 'textarea', wide: true },
]
export const STORAGE_FORM_FIELDS = [...STORAGE_IDENTITY, ...STORAGE_CAPACITY, ...STORAGE_CONNECTION, ...STORAGE_HARDWARE, ...STORAGE_PURCHASE]
const units: Record<string, number> = { GB: 1e9, TB: 1e12, PB: 1e15, GiB: 2 ** 30, TiB: 2 ** 40, PiB: 2 ** 50 }
export function storageErrors(values: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const field of STORAGE_FORM_FIELDS) {
    const value = values[field.key]?.trim() || ''
    if (field.required && !value) errors[field.key] = `${field.label} 항목을 ${field.options ? '선택' : '입력'}하세요.`
    if (value && field.type === 'number') {
      const number = Number(value)
      if (!Number.isFinite(number) || number < 0) errors[field.key] = '0 이상의 숫자를 입력하세요.'
      else if (field.integer && !Number.isInteger(number)) errors[field.key] = '디스크 수량은 정수로 입력하세요.'
      if (field.unitKey && !units[values[field.unitKey] || 'TB']) errors[field.unitKey] = '단위를 선택하세요.'
    }
    if (value && field.type === 'date') {
      const date = new Date(value)
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value) errors[field.key] = '올바른 날짜를 입력하세요.'
    }
  }
  if (values['총물리용량']?.trim() && values['사용가능용량']?.trim()) {
    const raw = Number(values['총물리용량']) * (units[values['총물리용량단위'] || 'TB'] || 0)
    const usable = Number(values['사용가능용량']) * (units[values['사용가능용량단위'] || 'TB'] || 0)
    if (usable > raw) errors['사용가능용량'] = '전체 디스크 용량보다 큽니다. 값과 단위를 확인하세요.'
  }
  return errors
}
export function storageTextFields(values: Record<string, string>): Record<string, string | null> {
  const fields: Record<string, string | null> = {}
  for (const field of STORAGE_FORM_FIELDS) {
    if (!field.key.startsWith('__') && field.key !== '자산번호' && !['number', 'multi'].includes(field.type || '')) fields[field.key] = values[field.key]?.trim() || null
  }
  fields['서버명'] = values['서버명']?.trim() || ''
  fields['호스트명'] = values['__name__']?.trim() || null
  return fields
}
export function storageCapacityText(values: Record<string, string>, key: string): string {
  const value = values[key]?.trim()
  return value ? `${value} ${values[key + '단위'] || 'TB'}` : '미등록'
}

// Keep an absent hostname distinct from the asset name used as the display fallback.
export function storageRecordName(values: Record<string, string>): string {
  return values['__name__']?.trim() || values['서버명']?.trim() || ''
}
export function storageFormIdentity(row: { name: string; fields?: Record<string, unknown> | null }): Record<string, string> {
  const fields = row.fields || {}
  return {
    __name__: Object.hasOwn(fields, '호스트명') ? (typeof fields['호스트명'] === 'string' ? fields['호스트명'] : '') : row.name,
    서버명: (typeof fields['서버명'] === 'string' ? fields['서버명'].trim() : '') || row.name,
  }
}
