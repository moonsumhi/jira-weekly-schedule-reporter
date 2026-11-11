export type SystemInfoValue = string | number | null
export type SystemInfoValues = Record<string, SystemInfoValue>
export type SystemInformation = {
  cpu: SystemInfoValues
  memory: SystemInfoValues
  memoryModules: SystemInfoValues[]
  disks: SystemInfoValues[]
  partitions: SystemInfoValues[]
  hardware: SystemInfoValues
  networkInterfaces: SystemInfoValues[]
  gpus: SystemInfoValues[]
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
  stacked?: boolean
  bytes?: boolean
}
export type SystemInfoSingleKey = 'cpu' | 'memory' | 'hardware'
export type SystemInfoListKey = 'memoryModules' | 'disks' | 'partitions' | 'networkInterfaces' | 'gpus'
export type SystemInfoSection = { title: string; fields: SystemInfoField[]; rows: string[][] } & (
  { key: SystemInfoSingleKey; multiple?: false } |
  { key: SystemInfoListKey; multiple: true; itemLabel: string; limit: number; columns: string[] }
)
const count = (key: string, label: string, min = 1): SystemInfoField => ({ key, label, type: 'number', min, max: 1048576 })
const gb = (key: string, label: string): SystemInfoField => ({ key, label, type: 'number', min: 0, max: 1073741824, decimal: true })
const bytes = (key: string, label: string): SystemInfoField => ({ key, label, type: 'number', min: 0, max: Number.MAX_SAFE_INTEGER, bytes: true })

export const systemInfoSections: SystemInfoSection[] = [
  { key: 'hardware', title: '메인보드 상세', rows: [['boardManufacturer', 'boardModel'], ['boardVersion', 'boardSerial'], ['boardFeatures']], fields: [
    { key: 'boardManufacturer', label: '제조사' }, { key: 'boardModel', label: '제품명' },
    { key: 'boardVersion', label: '버전' }, { key: 'boardSerial', label: '시리얼' },
    { key: 'boardFeatures', label: '특징', type: 'textarea', wide: true, stacked: true, maxLength: 4000 },
  ] },
  { key: 'hardware', title: 'BIOS 상세', rows: [['biosManufacturer', 'biosRevision'], ['biosVersion', 'biosDate'], ['biosFeatures']], fields: [
    { key: 'biosManufacturer', label: '제조사' }, { key: 'biosRevision', label: 'BIOS 리비전' },
    { key: 'biosVersion', label: '버전' }, { key: 'biosDate', label: '릴리즈 일자', type: 'date' },
    { key: 'biosFeatures', label: '특징', type: 'textarea', wide: true, stacked: true, maxLength: 4000 },
  ] },
  { key: 'cpu', title: 'CPU 상세', rows: [
    ['manufacturer', 'model'], ['architecture', 'frequencyMhz', 'virtualization'],
    ['sockets', 'coresPerSocket', 'threadsPerCore'], ['logicalCpus', 'threadList', 'numaNodes'],
  ], fields: [
    { key: 'manufacturer', label: '제조사' }, { key: 'model', label: '모델명' },
    { key: 'architecture', label: '아키텍처', placeholder: '예: x86_64' },
    gb('frequencyMhz', '동작 주파수 (MHz)'),
    { key: 'virtualization', label: '가상화 기술 지원', placeholder: '예: VT-x, AMD-V, 미지원' },
    count('sockets', '소켓 수'), count('coresPerSocket', '소켓당 코어 수'),
    count('threadsPerCore', '코어당 스레드 수'), count('logicalCpus', '논리 CPU 수'),
    { key: 'threadList', label: '스레드 목록', type: 'textarea', maxLength: 4000, placeholder: '예: 0-31' },
    count('numaNodes', 'NUMA 노드 수'),
  ] },
  { key: 'memory', title: '메모리 정보', rows: [['totalGb', 'maxCapacityGb', 'installedSlots', 'totalSlots']], fields: [
    gb('totalGb', '총 용량 (GB)'), gb('maxCapacityGb', '최대 지원 용량 (GB)'),
    { ...count('installedSlots', '장착 슬롯 수', 0), max: 65536 },
    { ...count('totalSlots', '전체 슬롯 수', 0), max: 65536 },
  ] },
  { key: 'memoryModules', title: '메모리 슬롯 목록', multiple: true, itemLabel: '메모리 슬롯', limit: 128,
    rows: [['slot', 'status'], ['manufacturer', 'partNumber'], ['model', 'specification'],
      ['type', 'formFactor', 'speed'], ['sizeBytes', 'capacityGb', 'serial']],
    columns: ['slot', 'manufacturer', 'capacityGb', 'specification', 'serial'], fields: [
    { key: 'slot', label: '메모리 슬롯', placeholder: '예: DIMM A1' }, { key: 'manufacturer', label: '제조사' },
    { key: 'model', label: '모델명' }, { key: 'type', label: '메모리 타입', placeholder: '예: DDR4' },
    bytes('sizeBytes', 'Size (byte)'),
    { key: 'status', label: '장착 상태', options: ['장착', '미장착', '확인 필요'] },
    { key: 'partNumber', label: 'Part Number' }, { key: 'specification', label: '사양' },
    { key: 'formFactor', label: 'Form Factor', placeholder: '예: DIMM, SODIMM' },
    gb('capacityGb', 'Size (GB)'), { key: 'speed', label: 'Speed', placeholder: '예: 3200 MT/s' },
    { key: 'serial', label: 'Serial' },
  ] },
  { key: 'disks', title: '디스크 목록', multiple: true, itemLabel: '디스크', limit: 256,
    rows: [['name', 'kernelName', 'parent'], ['type', 'filesystem', 'uuid'], ['mountPoint', 'sizeBytes'],
      ['partitionLabel', 'filesystemLabel', 'revision'], ['manufacturer', 'model', 'serial']],
    columns: ['name', 'mountPoint', 'type', 'parent', 'filesystem', 'sizeBytes', 'manufacturer', 'model'], fields: [
    { key: 'name', label: '장치명', placeholder: '예: sda, nvme0n1' },
    { key: 'type', label: '장치 종류', options: ['디스크', '파티션', '논리 볼륨', '광학 장치', '기타'] },
    { key: 'mountPoint', label: '마운트 경로' }, { key: 'partitionLabel', label: '파티션 라벨' },
    { key: 'manufacturer', label: '제조사' }, { key: 'kernelName', label: '커널명' },
    { key: 'filesystem', label: '파일시스템 종류' }, bytes('sizeBytes', 'Size (byte)'),
    { key: 'filesystemLabel', label: '파일시스템 라벨' }, { key: 'model', label: '모델명' },
    { key: 'parent', label: '부모 커널명' }, { key: 'uuid', label: 'UUID' },
    { key: 'revision', label: 'REV' }, { key: 'serial', label: 'Serial' },
  ] },
  { key: 'partitions', title: '파티션 목록', multiple: true, itemLabel: '파티션', limit: 512,
    rows: [['mountPoint', 'source'], ['sizeBytes', 'usedBytes', 'availableBytes'], ['usedPercent', 'filesystem']],
    columns: ['mountPoint', 'source', 'sizeBytes', 'usedBytes', 'availableBytes', 'usedPercent', 'filesystem'], fields: [
    { key: 'mountPoint', label: '마운트 경로' }, bytes('sizeBytes', 'Size (byte)'),
    { key: 'usedPercent', label: 'Used (%)', type: 'number', min: 0, max: 100, decimal: true },
    { key: 'source', label: '마운트 소스' }, bytes('usedBytes', 'Used (byte)'),
    { key: 'filesystem', label: '파일시스템 타입' }, bytes('availableBytes', 'Avail (byte)'),
  ] },
  { key: 'networkInterfaces', title: '네트워크 목록', multiple: true, itemLabel: '네트워크', limit: 128,
    rows: [['name', 'bondingOptions'], ['ipv4', 'netmask', 'gateway']],
    columns: ['name', 'ipv4', 'netmask', 'gateway', 'bondingOptions'], fields: [
    { key: 'name', label: '네트워크\n인터페이스' },
    { key: 'ipv4', label: 'IP', type: 'textarea', maxLength: 1024 },
    { key: 'bondingOptions', label: 'bonding 옵션', type: 'textarea', wide: true, maxLength: 4000 },
    { key: 'netmask', label: 'netmask' }, { key: 'gateway', label: 'gateway' },
  ] },
  { key: 'gpus', title: 'GPU 목록', multiple: true, itemLabel: 'GPU', limit: 128,
    rows: [['manufacturer', 'productName', 'coreCodename']],
    columns: ['manufacturer', 'productName', 'coreCodename'], fields: [
    { key: 'manufacturer', label: 'GPU 제조사' }, { key: 'productName', label: 'GPU 제품명' },
    { key: 'coreCodename', label: 'GPU 코어\n코드네임' },
  ] },
]

export function formatHardwareBytes(value: SystemInfoValue | undefined): string {
  if (value === null || value === undefined || value === '') return '-'
  const size = Number(value)
  if (!Number.isFinite(size) || size < 0) return '-'
  if (size < 1024) return `${size} B`
  const units = ['KB', 'MB', 'GB', 'TB', 'PB']
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)) - 1, units.length - 1)
  return `${Number((size / 1024 ** (index + 1)).toFixed(2))} ${units[index]}`
}
export function emptySystemInfoEntry(fields: SystemInfoField[]): SystemInfoValues {
  return Object.fromEntries(fields.map(field => [field.key, field.type === 'number' || field.type === 'date' ? null : '']))
}

/** A fresh editable copy; absent data stays empty rather than being guessed. */
export function copySystemInformation(value?: SystemInformation | null): SystemInformation {
  const data: SystemInformation = { cpu: {}, memory: {}, memoryModules: [], disks: [], partitions: [], hardware: {}, networkInterfaces: [], gpus: [], notes: value?.notes || '' }
  for (const section of systemInfoSections) {
    if (section.multiple) {
      data[section.key] = (value?.[section.key] || []).map(row => ({ ...emptySystemInfoEntry(section.fields), ...row }))
    } else {
      data[section.key] = { ...data[section.key], ...emptySystemInfoEntry(section.fields), ...value?.[section.key] }
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
