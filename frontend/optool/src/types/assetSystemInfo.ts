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
  allowCustom?: boolean
  placeholder?: string
  hint?: string
  min?: number
  max?: number
  decimal?: boolean
  maxLength?: number
  wide?: boolean
  stacked?: boolean
  bytes?: boolean
  capacityTextKey?: string
  widthWeight?: number
  columnWidth?: number
}
export type SystemInfoSingleKey = 'cpu' | 'memory' | 'hardware'
export type SystemInfoListKey = 'memoryModules' | 'disks' | 'partitions' | 'networkInterfaces' | 'gpus'
export type SystemInfoSection = { title: string; fields: SystemInfoField[]; rows: string[][] } & (
  { key: SystemInfoSingleKey; multiple?: false } |
  { key: SystemInfoListKey; multiple: true; itemLabel: string; limit: number; columns: string[] }
)
const count = (key: string, label: string, min = 1): SystemInfoField => ({ key, label, type: 'number', min, max: 1048576, columnWidth: 112 })
const gb = (key: string, label: string): SystemInfoField => ({ key, label, type: 'number', min: 0, max: 1073741824, decimal: true, columnWidth: 120 })
const bytes = (key: string, label: string): SystemInfoField => ({ key, label, type: 'number', min: 0, max: Number.MAX_SAFE_INTEGER, bytes: true, columnWidth: 168 })

export const systemInfoSections: SystemInfoSection[] = [
  { key: 'hardware', title: '메인보드 상세', rows: [['boardManufacturer', 'boardModel'], ['boardVersion', 'boardSerial'], ['boardFeatures']], fields: [
    { key: 'boardManufacturer', label: '제조사', placeholder: '예: FUJITSU' }, { key: 'boardModel', label: '제품명', widthWeight: 1.4, placeholder: '예: D3289-B1' },
    { key: 'boardVersion', label: '버전', type: 'textarea', widthWeight: 1.6, placeholder: '예: S26361-D3289-B13 WGS04 GS02' }, { key: 'boardSerial', label: '시리얼', placeholder: '예: 53520357' },
    { key: 'boardFeatures', label: '특징', type: 'textarea', wide: true, stacked: true, maxLength: 4000 },
  ] },
  { key: 'hardware', title: 'BIOS 상세', rows: [['biosManufacturer', 'biosRevision'], ['biosVersion', 'biosDate'], ['biosFeatures']], fields: [
    { key: 'biosManufacturer', label: '제조사', type: 'textarea', widthWeight: 1.8, placeholder: '예: FUJITSU / American Megatrends Inc.' }, { key: 'biosRevision', label: 'BIOS 리비전', placeholder: '예: 1.15' },
    { key: 'biosVersion', label: '버전', type: 'textarea', widthWeight: 1.8, placeholder: '예: V5.0.0.11 R1.15.0 for D3289-B1x' }, { key: 'biosDate', label: '릴리즈 일자', type: 'date' },
    { key: 'biosFeatures', label: '특징', type: 'textarea', wide: true, stacked: true, maxLength: 4000 },
  ] },
  { key: 'cpu', title: 'CPU 상세', rows: [
    ['manufacturer', 'model'], ['architecture', 'frequencyMhz', 'virtualization'],
    ['sockets', 'coresPerSocket', 'threadsPerCore'], ['logicalCpus', 'threadList', 'numaNodes'],
  ], fields: [
    { key: 'manufacturer', label: '제조사', placeholder: '예: GenuineIntel' }, { key: 'model', label: '모델명', type: 'textarea', widthWeight: 2.4, placeholder: '예: Intel(R) Xeon(R) Gold 5217 CPU @ 3.00GHz' },
    { key: 'architecture', label: '아키텍처', placeholder: '예: x86_64' },
    gb('frequencyMhz', '동작 주파수 (MHz)'),
    { key: 'virtualization', label: '가상화 기술 지원', widthWeight: 1.3, placeholder: '예: VT-x, AMD-V, 미지원' },
    count('sockets', '소켓 수'), count('coresPerSocket', '소켓당 코어 수'),
    count('threadsPerCore', '코어당 스레드 수'), count('logicalCpus', '논리 CPU 수'),
    { key: 'threadList', label: '스레드 목록', type: 'textarea', widthWeight: 1.8, maxLength: 4000, placeholder: '예: 0-31 또는 0-15,32-47' },
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
    { key: 'slot', label: '메모리 슬롯', columnWidth: 144, placeholder: '예: DIMM 21' }, { key: 'manufacturer', label: '제조사', type: 'textarea', columnWidth: 180, placeholder: '예: Micron Technology' },
    { key: 'model', label: '모델명', type: 'textarea', widthWeight: 1.3, placeholder: '예: 36ASF4G72PZ-2G9E2' }, { key: 'type', label: '메모리 타입', placeholder: '예: DDR4' },
    bytes('sizeBytes', 'Size (byte)'),
    { key: 'status', label: '장착 상태', options: ['장착', '미장착', '확인 필요'] },
    { key: 'partNumber', label: 'Part Number', type: 'textarea', placeholder: '예: HMA42GR7AFR4N-UH' }, { key: 'specification', label: '사양', type: 'textarea', widthWeight: 2, columnWidth: 320, placeholder: '예: DIMM DDR4 Synchronous 2933 MHz (0.3 ns)' },
    { key: 'formFactor', label: 'Form Factor', placeholder: '예: DIMM, SODIMM' },
    gb('capacityGb', 'Size (GB)'), { key: 'speed', label: 'Speed', widthWeight: 1.2, placeholder: '예: 2400 MT/s' },
    { key: 'serial', label: 'Serial', columnWidth: 160, placeholder: '예: 2D2254AF' },
  ] },
  { key: 'disks', title: '디스크 목록', multiple: true, itemLabel: '디스크', limit: 256,
    rows: [['name', 'kernelName', 'parent'], ['type', 'filesystem', 'uuid'], ['mountPoint', 'sizeBytes'],
      ['partitionLabel', 'filesystemLabel', 'revision'], ['manufacturer', 'model', 'serial']],
    columns: ['name', 'mountPoint', 'type', 'parent', 'filesystem', 'sizeBytes', 'manufacturer', 'model'], fields: [
    { key: 'name', label: '장치명', placeholder: '예: sda, nvme0n1' },
    { key: 'type', label: '장치 종류', allowCustom: true, options: ['disk', 'part', 'lvm', 'rom', 'raid1', 'crypt', '디스크', '파티션', '논리 볼륨', '광학 장치', '기타'], hint: '목록에서 선택하거나 장치 종류를 직접 입력' },
    { key: 'mountPoint', label: '마운트 경로', type: 'textarea', widthWeight: 1.5, columnWidth: 200, placeholder: '예: /boot/efi' }, { key: 'partitionLabel', label: '파티션 라벨', type: 'textarea', widthWeight: 1.5, placeholder: '예: EFI System Partition' },
    { key: 'manufacturer', label: '제조사', columnWidth: 160 }, { key: 'kernelName', label: '커널명', placeholder: '예: sda' },
    { key: 'filesystem', label: '파일시스템 종류', placeholder: '예: vfat, ext4, xfs' },
    { ...bytes('sizeBytes', 'Size'), capacityTextKey: 'capacity', widthWeight: 1.4, placeholder: '예: 446.1G 또는 바이트 수', hint: '바이트는 정수로, 단위가 있는 용량은 원문 그대로 저장합니다.' },
    { key: 'filesystemLabel', label: '파일시스템 라벨', type: 'textarea', widthWeight: 1.5 }, { key: 'model', label: '모델명', type: 'textarea', widthWeight: 2, columnWidth: 240, placeholder: '예: RAID 930-8i-2GB' },
    { key: 'parent', label: '부모 커널명', placeholder: '예: sda' }, { key: 'uuid', label: 'UUID', type: 'textarea', widthWeight: 2, placeholder: '예: 8974-2C4B' },
    { key: 'revision', label: 'REV' }, { key: 'serial', label: 'Serial', type: 'textarea' },
  ] },
  { key: 'partitions', title: '파티션 목록', multiple: true, itemLabel: '파티션', limit: 512,
    rows: [['mountPoint', 'source'], ['sizeBytes', 'usedBytes', 'availableBytes'], ['usedPercent', 'filesystem']],
    columns: ['mountPoint', 'source', 'sizeBytes', 'usedBytes', 'availableBytes', 'usedPercent', 'filesystem'], fields: [
    { key: 'mountPoint', label: '마운트 경로', type: 'textarea', columnWidth: 200, placeholder: '예: /boot/efi' }, bytes('sizeBytes', 'Size (byte)'),
    { key: 'usedPercent', label: 'Used (%)', type: 'number', min: 0, max: 100, decimal: true },
    { key: 'source', label: '마운트 소스', type: 'textarea', columnWidth: 220, placeholder: '예: /dev/sda1' }, bytes('usedBytes', 'Used (byte)'),
    { key: 'filesystem', label: '파일시스템 타입' }, bytes('availableBytes', 'Avail (byte)'),
  ] },
  { key: 'networkInterfaces', title: '네트워크 목록', multiple: true, itemLabel: '네트워크', limit: 128,
    rows: [['name', 'bondingOptions'], ['ipv4', 'netmask', 'gateway']],
    columns: ['name', 'ipv4', 'netmask', 'gateway', 'bondingOptions'], fields: [
    { key: 'name', label: '네트워크\n인터페이스', columnWidth: 180, placeholder: '예: bond0' },
    { key: 'ipv4', label: 'IP', type: 'textarea', maxLength: 1024, columnWidth: 200, placeholder: '예: 10.10.10.222', hint: '여러 IP는 줄바꿈으로 구분' },
    { key: 'bondingOptions', label: 'bonding 옵션', type: 'textarea', widthWeight: 2.2, columnWidth: 300, wide: true, maxLength: 4000, placeholder: '예: active-backup miimon=100' },
    { key: 'netmask', label: 'netmask', columnWidth: 160, placeholder: '예: 255.255.255.0' }, { key: 'gateway', label: 'gateway', columnWidth: 160, placeholder: '예: 10.10.10.1' },
  ] },
  { key: 'gpus', title: 'GPU 목록', multiple: true, itemLabel: 'GPU', limit: 128,
    rows: [['manufacturer', 'productName', 'coreCodename']],
    columns: ['manufacturer', 'productName', 'coreCodename'], fields: [
    { key: 'manufacturer', label: 'GPU 제조사', type: 'textarea', widthWeight: 1.6, columnWidth: 220, placeholder: '예: NVIDIA Corporation' }, { key: 'productName', label: 'GPU 제품명', columnWidth: 160, placeholder: '예: L40S' },
    { key: 'coreCodename', label: 'GPU 코어\n코드네임', columnWidth: 180, placeholder: '예: AD102GL' },
  ] },
]

export function formatHardwareBytes(value: SystemInfoValue | undefined): string {
  if (value === null || value === undefined || value === '') return '-'
  const size = Number(value)
  if (!Number.isFinite(size) || size < 0) return '-'
  if (size < 1024) return `${size} B`
  const units = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)) - 1, units.length - 1)
  return `${Number((size / 1024 ** (index + 1)).toFixed(2))} ${units[index]}`
}
export function emptySystemInfoEntry(fields: SystemInfoField[]): SystemInfoValues {
  return Object.fromEntries(fields.map(field => [field.key, field.type === 'number' || field.type === 'date' ? null : '']))
}

/** A source capacity such as 446.1G is distinct from an exact byte count. */
export function systemInfoFieldValue(field: SystemInfoField, values: SystemInfoValues): SystemInfoValue | undefined {
  const value = values[field.key]
  return value !== null && value !== undefined && value !== '' ? value
    : field.capacityTextKey ? values[field.capacityTextKey] : value
}

export function updateSystemInfoField(field: SystemInfoField, values: SystemInfoValues, value: SystemInfoValue): SystemInfoValues {
  if (field.capacityTextKey) {
    const text = String(value ?? '').trim()
    const numericInput = /^[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(text)
    return { ...values, [field.key]: numericInput ? Number(text) : null, [field.capacityTextKey]: numericInput ? '' : text }
  }
  const next = field.type === 'number' ? (value === null || String(value).trim() === '' ? null : Number(value))
    : field.type === 'date' ? value || null : value ?? ''
  return { ...values, [field.key]: next }
}

export function systemInfoRowColumns(fields: SystemInfoField[]): string {
  return fields.map(field => `minmax(0, ${field.widthWeight ?? 1}fr)`).join(' ')
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
  if (field.capacityTextKey && typeof value === 'string') {
    // Older inventory can contain descriptions such as "1 TB (SSD)" or "N/A".
    // Keep source text separate; only the numeric byte field implies exact bytes.
    return value.length > 256 ? `${field.label}: 256자 이하로 입력해 주세요.` : ''
  }
  if (field.type === 'number') {
    const num = Number(value)
    if (!Number.isFinite(num) || num < (field.min ?? 0) || num > (field.max ?? 1048576) || (!field.decimal && !Number.isInteger(num))) {
      return `${field.label}: ${field.min ?? 0}~${field.max ?? 1048576} 범위의 ${field.decimal ? '숫자' : '정수'}를 입력해 주세요.`
    }
  }
  if (field.type === 'date') {
    const text = String(value)
    const date = new Date(`${text}T00:00:00Z`)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text) || text.startsWith('0000-') || !Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== text) {
      return `${field.label}: 올바른 날짜를 입력해 주세요.`
    }
  }
  if (field.options && !field.allowCustom && !field.options.includes(String(value))) {
    return `${field.label}: 목록에서 값을 선택해 주세요.`
  }
  if (String(value).length > (field.maxLength ?? 256)) return `${field.label}: ${field.maxLength ?? 256}자 이하로 입력해 주세요.`
  return ''
}

export function systemInformationError(data: SystemInformation): string {
  for (const section of systemInfoSections) {
    const rows = section.multiple ? data[section.key] : [data[section.key]]
    for (const row of rows) {
      for (const field of section.fields) {
        const error = systemInfoFieldError(field, systemInfoFieldValue(field, row))
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
