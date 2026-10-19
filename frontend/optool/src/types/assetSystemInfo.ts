export type SystemInfoValue = string | number | null
export type SystemInfoValues = Record<string, SystemInfoValue>
export type SystemInformation = {
  cpu: SystemInfoValues
  memory: SystemInfoValues
  memoryModules: SystemInfoValues[]
  disks: SystemInfoValues[]
  hardware: SystemInfoValues
  networkInterfaces: SystemInfoValues[]
  notes: string
}

export type SystemInfoField = {
  key: string
  label: string
  type?: 'number' | 'date' | 'textarea'
  options?: string[]
  placeholder?: string
  min?: number
  max?: number
  decimal?: boolean
  maxLength?: number
  wide?: boolean
}
type SingleKey = 'cpu' | 'memory' | 'hardware'
type ListKey = 'memoryModules' | 'disks' | 'networkInterfaces'
export type SystemInfoSection = { title: string; fields: SystemInfoField[] } & (
  { key: SingleKey; multiple?: false } |
  { key: ListKey; multiple: true; itemLabel: string; limit: number }
)
const count = (key: string, label: string, min = 1): SystemInfoField => ({ key, label, type: 'number', min, max: 1048576 })
const gb = (key: string, label: string): SystemInfoField => ({ key, label, type: 'number', min: 0, max: 1073741824, decimal: true })

export const systemInfoSections: SystemInfoSection[] = [
  { key: 'cpu', title: 'CPU', fields: [
    { key: 'manufacturer', label: '제조사' }, { key: 'model', label: '모델명' },
    { key: 'architecture', label: '아키텍처', placeholder: '예: x86_64' }, count('sockets', '소켓 수'),
    count('coreCount', '전체 코어 수'), count('logicalCpus', '논리 CPU 수'),
    count('threadsPerCore', '코어당 스레드 수'), { key: 'frequency', label: '동작 주파수', placeholder: '예: 3.60 GHz' },
    { key: 'virtualization', label: '가상화 지원', placeholder: '예: VT-x' }, { key: 'cache', label: '캐시', placeholder: '예: L3 12 MB' },
  ] },
  { key: 'memory', title: '메모리', fields: [
    gb('totalGb', '총 용량 (GB)'), { ...count('totalSlots', '전체 슬롯 수', 0), max: 65536 },
    gb('maxCapacityGb', '최대 지원 용량 (GB)'), { key: 'ecc', label: '오류 정정 방식', placeholder: '예: ECC' },
  ] },
  { key: 'memoryModules', title: '메모리 슬롯', multiple: true, itemLabel: '슬롯', limit: 128, fields: [
    { key: 'slot', label: '슬롯명', placeholder: '예: DIMM A1' }, { key: 'status', label: '장착 상태', options: ['장착', '미장착', '확인 필요'] },
    gb('capacityGb', '용량 (GB)'), { key: 'type', label: '메모리 종류', placeholder: '예: DDR4' },
    { key: 'speed', label: '동작 속도', placeholder: '예: 2667 MT/s' }, { key: 'manufacturer', label: '제조사' },
    { key: 'model', label: '모델명' }, { key: 'serial', label: '일련번호' },
  ] },
  { key: 'disks', title: '디스크', multiple: true, itemLabel: '디스크', limit: 256, fields: [
    { key: 'name', label: '장치명', placeholder: '예: sda, vg-root' }, { key: 'type', label: '종류', options: ['디스크', '파티션', '논리 볼륨', '광학 장치', '기타'] },
    { key: 'capacity', label: '용량', placeholder: '예: 500 GB' }, { key: 'filesystem', label: '파일시스템', placeholder: '예: ext4, xfs' },
    { key: 'mountPoint', label: '마운트 경로', placeholder: '예: /data' }, { key: 'parent', label: '상위 장치', placeholder: '예: sda2' },
    { key: 'model', label: '모델명' }, { key: 'serial', label: '일련번호' },
  ] },
  { key: 'hardware', title: '하드웨어', fields: [
    { key: 'boardManufacturer', label: '메인보드 제조사' }, { key: 'boardModel', label: '메인보드 모델' },
    { key: 'boardSerial', label: '메인보드 일련번호' }, { key: 'chassis', label: '장비 형태', placeholder: '예: 랙마운트' },
    { key: 'biosManufacturer', label: 'BIOS 제조사' }, { key: 'biosVersion', label: 'BIOS 버전' },
    { key: 'biosDate', label: 'BIOS 날짜', type: 'date' },
  ] },
  { key: 'networkInterfaces', title: '네트워크', multiple: true, itemLabel: '인터페이스', limit: 128, fields: [
    { key: 'name', label: '인터페이스명', placeholder: '예: eth0, bond0' }, { key: 'type', label: '종류', options: ['물리', '본딩', '브리지', 'VLAN', '가상', '루프백', '기타'] },
    { key: 'state', label: '동작 상태', options: ['활성', '비활성', '확인 필요'] }, count('mtu', 'MTU'),
    { key: 'ipv4', label: 'IPv4 주소', type: 'textarea', placeholder: '예: 192.0.2.10/24', maxLength: 1024 },
    { key: 'ipv6', label: 'IPv6 주소', type: 'textarea', placeholder: '예: fe80::1/64', maxLength: 1024 },
    { key: 'mac', label: 'MAC 주소' }, { key: 'permanentMac', label: '원래 MAC 주소' },
    { key: 'parent', label: '상위 인터페이스', placeholder: '예: bond0' }, { key: 'speed', label: '링크 속도', placeholder: '예: 1 Gbps' },
  ] },
]

export function emptySystemInfoEntry(fields: SystemInfoField[]): SystemInfoValues {
  return Object.fromEntries(fields.map(field => [field.key, field.type === 'number' || field.type === 'date' ? null : '']))
}

/** A fresh editable copy; absent data stays empty rather than being guessed. */
export function copySystemInformation(value?: SystemInformation | null): SystemInformation {
  const data: SystemInformation = { cpu: {}, memory: {}, memoryModules: [], disks: [], hardware: {}, networkInterfaces: [], notes: value?.notes || '' }
  for (const section of systemInfoSections) {
    if (section.multiple) {
      data[section.key] = (value?.[section.key] || []).map(row => ({ ...emptySystemInfoEntry(section.fields), ...row }))
    } else {
      data[section.key] = { ...emptySystemInfoEntry(section.fields), ...value?.[section.key] }
    }
  }
  return data
}

export function systemInfoFieldError(field: SystemInfoField, value: SystemInfoValue | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  if (field.type === 'number') {
    const num = Number(value)
    if (!Number.isFinite(num) || num < (field.min ?? 0) || num > (field.max ?? 1048576) || (!field.decimal && !Number.isInteger(num))) {
      return `${field.label}: ${field.min ?? 0}~${field.max ?? 1048576} 범위의 ${field.decimal ? '숫자' : '정수'}를 입력해 주세요.`
    }
  }
  if (String(value).length > (field.maxLength ?? 256)) return `${field.label}: ${field.maxLength ?? 256}자 이하로 입력해 주세요.`
  return ''
}

export function systemInformationError(data: SystemInformation): string {
  for (const section of systemInfoSections) {
    const rows = section.multiple ? data[section.key] : [data[section.key]]
    for (const row of rows) {
      for (const field of section.fields) {
        const error = systemInfoFieldError(field, row[field.key])
        if (error) return `${section.title} · ${error}`
      }
    }
  }
  return ''
}

export function systemInformationPayload(value: SystemInformation): SystemInformation {
  const data = copySystemInformation(value)
  for (const section of systemInfoSections) {
    if (section.multiple) data[section.key] = data[section.key].filter(row => Object.values(row).some(v => v !== null && String(v).trim() !== ''))
  }
  return data
}
