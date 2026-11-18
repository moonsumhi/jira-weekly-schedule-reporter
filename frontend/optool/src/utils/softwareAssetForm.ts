import type { AssetFormField } from './assetFormFields'
export type SoftwareField = AssetFormField
// Keep existing category values stable while using clearer names in the UI.
export const SOFTWARE_CATEGORIES = [
  { value: 'WEB', label: '웹 서버 (WEB)', description: 'Nginx, Apache HTTP Server, WebtoB' },
  { value: 'WAS', label: '애플리케이션 서버 (WAS)', description: 'Tomcat, JEUS, WebLogic' },
  { value: 'DBMS', label: '데이터베이스 (DBMS)', description: 'Oracle Database, PostgreSQL, SQL Server' },
  { value: 'OS', label: '운영체제 (OS)', description: 'Windows Server, RHEL' },
  { value: '가상화·컨테이너', label: '가상화·컨테이너', description: 'VMware vSphere, Docker, Kubernetes' },
  { value: '보안·인증', label: '보안·인증', description: '백신, EDR, 접근제어, SSO' },
  { value: '백업·복구', label: '백업·복구', description: 'NetBackup, Veeam' },
  { value: '모니터링', label: '모니터링·로그', description: 'Zabbix, Prometheus, Splunk' },
  { value: '데이터 처리·연계', label: '데이터 처리·연계', description: 'ETL, CDC, Kafka' },
  { value: '운영·자동화', label: '운영·자동화', description: 'Ansible, 배치 스케줄러' },
  { value: '개발·배포', label: '개발·배포', description: 'GitLab, Jenkins, Nexus' },
  { value: '업무용', label: '업무·협업', description: 'Microsoft 365, 한글, Jira' },
  { value: '기타', label: '기타', description: '위 분류에 해당하지 않는 제품' },
]
export function softwareCategoryLabel(value: string): string {
  return SOFTWARE_CATEGORIES.find(category => category.value === value)?.label ?? value
}
export const SOFTWARE_PRODUCT: SoftwareField[] = [
  { key: '운영체제', label: '제품명', required: true, placeholder: '예: Nginx, Apache Tomcat, Microsoft 365' },
  { key: '구분', label: '분류', required: true,
    options: SOFTWARE_CATEGORIES.map(category => category.value),
    optionLabels: Object.fromEntries(SOFTWARE_CATEGORIES.map(category => [category.value, category.label])),
    optionDescriptions: Object.fromEntries(SOFTWARE_CATEGORIES.map(category => [category.value, category.description])),
  },
  { key: 'version', label: '버전', placeholder: '예: 1.26.2', hint: 'SaaS처럼 버전을 관리하지 않으면 비워두세요.' },
  { key: '자산번호', label: '자산번호', required: true, placeholder: '예: SW-001', hint: '조직에서 사용하는 자산 관리 번호' },
  { key: '설명', label: '용도·설명', required: true, type: 'textarea', wide: true, placeholder: '예: ATOM 서비스의 웹 요청을 처리하는 웹 서버' },
]
export const SOFTWARE_EXTRA_PRODUCT: SoftwareField[] = [
  { key: '__name__', label: '관리명', wide: true, placeholder: '예: 운영 웹 서버 · Nginx', hint: '목록에 표시되는 관리명입니다. 미입력 시 제품명으로 자동 설정됩니다.' },
  { key: '에디션', label: '에디션', placeholder: '예: Community, Enterprise' },
  { key: '제조사', label: '제조사·공급사', placeholder: '예: Microsoft, Red Hat' },
  { key: '도입형태', label: '제공 방식', options: ['설치형', 'SaaS'] },
  { key: '상태', label: '관리 상태', options: ['운영', '점검', '미사용', '폐기예정', '폐기'] },
]
export const SOFTWARE_LICENSE: SoftwareField[] = [
  { key: '사용권형태', label: '사용권 형태', options: ['영구', '구독', '기간제', '평가판', '무상', '오픈소스', '기타'] },
  { key: '라이선스식별번호', label: '계약·라이선스 번호', placeholder: '계약서 또는 구매 내역의 관리 번호' },
  { key: '라이선스기준', label: '수량 기준', options: ['사용자', '장치', '서버', '코어', '프로세서', '동시접속', '사이트', '기타'] },
  { key: '라이선스수량', label: '보유 수량', type: 'number', hint: '예: 사용자 기준 50 → 50명이 사용할 수 있는 사용권' },
  { key: '사용시작일', label: '사용 시작일', type: 'date' },
  { key: '사용권만료일', label: '사용권 만료일', type: 'date', hint: '구독·기간제·평가판의 사용 종료일' },
]
export const SOFTWARE_USAGE: SoftwareField[] = [
  { key: '사용부서', label: '사용 부서', placeholder: '예: 데이터운영팀' },
  { key: '사용서비스', label: '사용 서비스', placeholder: '예: ATOM, 통합 모니터링' },
]
export const SOFTWARE_PURCHASE: SoftwareField[] = [
  { key: '도입사업', label: '도입 사업', placeholder: '예: 2026년 운영 환경 개선' },
  { key: '납품회사', label: '구매·납품 업체' },
  { key: '담당자', label: '담당자' },
  { key: '도입가격', label: '도입 가격 (원)', type: 'number' },
  { key: '도입일자', label: '도입일', type: 'date' },
  { key: '유지보수계약구분', label: '유지보수 계약 구분', options: ['유상', '무상', '해당 없음'] },
  { key: '유지보수종료일자', label: '유지보수 종료일', type: 'date', hint: '사용권 만료일과 별도로 관리합니다.' },
  { key: '유지보수업체', label: '유지보수 업체' },
  { key: '유지보수연락처', label: '유지보수 연락처' },
  { key: '유지보수특이사항', label: '유지보수 메모', type: 'textarea', wide: true },
  { key: '비고', label: '비고', type: 'textarea', wide: true },
]
export const SOFTWARE_FORM_FIELDS = [...SOFTWARE_PRODUCT, ...SOFTWARE_EXTRA_PRODUCT, ...SOFTWARE_LICENSE, ...SOFTWARE_USAGE, ...SOFTWARE_PURCHASE]
export function softwareErrors(values: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const field of SOFTWARE_FORM_FIELDS) {
    const value = values[field.key]?.trim() || ''
    if (field.required && !value) errors[field.key] = `${field.label}${field.options ? '를 선택하세요.' : field.key === '자산번호' ? '를 입력하세요.' : '을 입력하세요.'}`
    if (value && field.type === 'number' && (!Number.isFinite(Number(value)) || Number(value) < 0)) errors[field.key] = '0 이상의 숫자를 입력하세요.'
    if (value && field.type === 'date') {
      const date = new Date(value)
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value) errors[field.key] = '올바른 날짜를 입력하세요. 예: 2026-11-13'
    }
  }
  if (values['라이선스수량']?.trim() && !values['라이선스기준']?.trim()) errors['라이선스기준'] = '보유 수량의 기준을 선택하세요. 예: 사용자, 서버'
  if (values['사용시작일'] && values['사용권만료일'] && values['사용시작일'] > values['사용권만료일']) errors['사용권만료일'] = '사용 시작일 이후의 날짜를 선택하세요.'
  return errors
}
// Keep text identifiers and versions intact; the shared detail serializer handles license numbers and relations.
export function softwareTextFields(values: Record<string, string>): Record<string, string | null> {
  const fields: Record<string, string | null> = {}
  for (const field of SOFTWARE_FORM_FIELDS) {
    if (!field.key.startsWith('__') && field.key !== '자산번호' && field.type !== 'number') fields[field.key] = values[field.key]?.trim() || null
  }
  fields['서버명'] = values['서버명']?.trim() || values['__name__']?.trim() || values['운영체제']?.trim() || ''
  return fields
}
