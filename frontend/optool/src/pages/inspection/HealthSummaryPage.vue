<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6">서버 점검 요약</div>
      <q-space />

      <q-input
        v-if="report"
        v-model="search"
        dense outlined clearable
        placeholder="호스트명 / IP 검색"
        style="min-width: 200px"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>

      <q-select
        v-if="reports.length"
        v-model="selectedId"
        :options="reportOptions"
        emit-value map-options
        dense outlined
        label="보고서 선택"
        style="min-width: 240px"
        @update:model-value="loadReport"
      />

      <q-btn v-if="isInternal" color="primary" icon="upload_file" label="Excel 업로드" dense @click="triggerUpload" :loading="uploading" />
      <input ref="fileInput" type="file" accept=".xlsx" class="hidden" @change="onFileChange" />

      <q-btn
        v-if="isInternal && selectedId"
        flat dense round icon="delete"
        color="negative"
        @click="confirmDelete"
        :loading="deleting"
      >
        <q-tooltip>보고서 삭제</q-tooltip>
      </q-btn>
    </div>

    <div v-if="!reports.length && !loading" class="text-center text-grey-5 q-pa-xl">
      <q-icon name="description" size="48px" class="q-mb-sm" /><br />
      업로드된 보고서가 없습니다.<br />
      health_report_*.xlsx 파일을 업로드하세요.
    </div>

    <div v-else-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" />
    </div>

    <template v-else-if="report">
      <div class="row items-center q-mb-sm text-caption text-grey-6">
        <span>{{ report.reportTitle }}</span>
        <q-space />
        <span>{{ report.serverCount ?? report.summary.length }}대 점검</span>
        <span class="q-ml-md">업로드: {{ report.uploadedBy }} · {{ report.uploadedAt }}</span>
      </div>

      <q-card flat bordered>
        <q-markup-table flat dense separator="horizontal">
          <thead>
            <tr class="text-left bg-grey-2">
              <th style="width:40px" class="sortable-th" @click="setSort('no')">
                No. <q-icon :name="sortIcon('no')" size="14px" />
              </th>
              <th style="min-width:140px" class="sortable-th" @click="setSort('hostName')">
                Host Name <q-icon :name="sortIcon('hostName')" size="14px" />
              </th>
              <th style="min-width:140px">IP</th>
              <th style="width:80px" class="sortable-th" @click="setSort('cpu')">
                CPU <q-icon :name="sortIcon('cpu')" size="14px" />
              </th>
              <th style="width:80px" class="sortable-th" @click="setSort('ram')">
                RAM <q-icon :name="sortIcon('ram')" size="14px" />
              </th>
              <th style="width:80px" class="sortable-th" @click="setSort('disk')">
                Disk <q-icon :name="sortIcon('disk')" size="14px" />
              </th>
              <th style="width:70px" class="sortable-th" @click="setSort('logErrors')">
                로그에러 <q-icon :name="sortIcon('logErrors')" size="14px" />
              </th>
              <th>조치 필요 항목</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in sortedSummary"
              :key="s.hostName"
              class="cursor-pointer row-hover"
              @click="openDetail(s.hostName)"
            >
              <td class="text-caption text-grey-6">{{ s.no }}</td>
              <td class="text-caption text-weight-medium">{{ s.hostName }}</td>
              <td class="text-caption text-grey-7" style="font-size:11px">
                <span>{{ formatIp(s.ip) }}</span>
                <q-tooltip v-if="ipCount(s.ip) > 3" style="font-size:12px; white-space:pre">{{ s.ip }}</q-tooltip>
              </td>
              <td>
                <q-chip dense :color="metricColor(detailCpu(s.hostName) || s.cpu)" text-color="white" size="sm" class="q-ma-none">
                  {{ formatPct(detailCpu(s.hostName) || s.cpu) }}
                </q-chip>
              </td>
              <td>
                <q-chip dense :color="metricColor(detailRam(s.hostName) || s.ram)" text-color="white" size="sm" class="q-ma-none">
                  {{ formatPct(detailRam(s.hostName) || s.ram) }}
                </q-chip>
              </td>
              <td>
                <q-chip dense :color="metricColor(detailDisk(s.hostName) || s.diskMax)" text-color="white" size="sm" class="q-ma-none">
                  {{ formatPct(detailDisk(s.hostName) || s.diskMax) }}
                </q-chip>
              </td>
              <td>
                <q-badge v-if="s.logErrors !== '-' && s.logErrors" :color="logErrorColor(s.logErrors)" outline>
                  {{ s.logErrors }}건
                </q-badge>
                <span v-else class="text-caption text-grey-5">-</span>
              </td>
              <td>
                <span :class="actionClass(s.actionItems)" class="text-caption action-preview">
                  {{ actionPreview(s.actionItems) }}
                </span>
              </td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card>
    </template>

    <!-- 상세 다이얼로그 -->
    <q-dialog v-model="detailDialog" maximized>
      <q-card v-if="detailServer" style="max-width:800px; margin:auto; height:fit-content; max-height:92vh; overflow-y:auto">
        <q-card-section class="row items-center q-pb-none sticky-header">
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ detailServer.hostName }}</div>
            <div class="text-caption text-grey-6">{{ detailServer.serverOs }} · {{ detailServer.ip }}</div>
          </div>
          <q-space />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section>

          <!-- 기본 정보 -->
          <div class="section-title">기본 정보</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <tbody>
              <tr><td class="label-cell">호스트명</td><td>{{ detailServer.hostName }}</td><td class="label-cell">서버명</td><td>{{ detailServer.serverName }}</td></tr>
              <tr><td class="label-cell">OS</td><td>{{ detailServer.serverOs }}</td><td class="label-cell">IP</td><td>{{ detailServer.ip }}</td></tr>
              <tr><td class="label-cell">점검자</td><td>{{ detailServer.inspector }}</td><td class="label-cell">서버 종료</td><td>{{ cleanTime(detailServer.serverShutdown) }}</td></tr>
              <tr><td class="label-cell">점검 시작</td><td>{{ cleanTime(detailServer.inspectionStart) }}</td><td class="label-cell">서버 재기동</td><td>{{ cleanTime(detailServer.serverRestart) }}</td></tr>
              <tr><td class="label-cell">점검 종료</td><td>{{ cleanTime(detailServer.inspectionEnd) }}</td><td></td><td></td></tr>
            </tbody>
          </q-markup-table>

          <!-- H/W 육안 점검 -->
          <div class="section-title">H/W 육안 점검</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <thead>
              <tr class="bg-grey-2"><th>항목</th><th style="width:60px">OK</th><th style="width:60px">NG</th><th style="width:60px">N/A</th></tr>
            </thead>
            <tbody>
              <tr v-for="hw in detailServer.hwChecks" :key="hw.item">
                <td>{{ hw.item }}</td>
                <td class="text-center">{{ hw.ok }}</td>
                <td class="text-center" :class="hw.ng ? 'text-negative text-weight-bold' : ''">{{ hw.ng }}</td>
                <td class="text-center text-grey-5">{{ hw.na }}</td>
              </tr>
            </tbody>
          </q-markup-table>

          <!-- 성능 상태 -->
          <div class="section-title">성능 상태</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <thead>
              <tr class="bg-grey-2">
                <th>항목</th>
                <th>점검 전 (값)</th><th>점검 전 (%)</th>
                <th>점검 후 (값)</th><th>점검 후 (%)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="label-cell">CPU</td>
                <td>{{ detailServer.cpu.beforeVal }}</td>
                <td><span :class="metricClass(detailServer.cpu.beforePct)">{{ detailServer.cpu.beforePct }}</span></td>
                <td>{{ detailServer.cpu.afterVal }}</td>
                <td><span :class="metricClass(detailServer.cpu.afterPct)">{{ detailServer.cpu.afterPct }}</span></td>
              </tr>
              <tr>
                <td class="label-cell">RAM</td>
                <td>{{ detailServer.ram.beforeVal }}</td>
                <td><span :class="metricClass(detailServer.ram.beforePct)">{{ detailServer.ram.beforePct }}</span></td>
                <td>{{ detailServer.ram.afterVal }}</td>
                <td><span :class="metricClass(detailServer.ram.afterPct)">{{ detailServer.ram.afterPct }}</span></td>
              </tr>
              <tr>
                <td class="label-cell">Swap</td>
                <td>{{ detailServer.swap.beforeVal }}</td>
                <td><span :class="metricClass(detailServer.swap.beforePct)">{{ detailServer.swap.beforePct }}</span></td>
                <td>{{ detailServer.swap.afterVal }}</td>
                <td><span :class="metricClass(detailServer.swap.afterPct)">{{ detailServer.swap.afterPct }}</span></td>
              </tr>
              <tr>
                <td class="label-cell">Network (전)</td>
                <td colspan="4">{{ detailServer.networkBefore }}</td>
              </tr>
              <tr>
                <td class="label-cell">Network (후)</td>
                <td colspan="4">{{ detailServer.networkAfter }}</td>
              </tr>
            </tbody>
          </q-markup-table>

          <!-- 디스크 -->
          <div class="section-title">디스크 현황</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <thead>
              <tr class="bg-grey-2"><th>Filesystem</th><th>Used</th><th>Total</th><th>%</th></tr>
            </thead>
            <tbody>
              <tr v-for="d in detailServer.disks" :key="d.filesystem">
                <td>{{ d.filesystem }}</td>
                <td>{{ d.used }}</td>
                <td>{{ d.total }}</td>
                <td><span :class="metricClass(d.pct)">{{ d.pct }}</span></td>
              </tr>
            </tbody>
          </q-markup-table>

          <!-- 시스템 보안 -->
          <div class="section-title">시스템 보안 점검</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <thead>
              <tr class="bg-grey-2"><th>항목</th><th style="width:80px">결과</th></tr>
            </thead>
            <tbody>
              <tr v-for="sc in detailServer.securityChecks" :key="sc.item">
                <td>{{ sc.item }}</td>
                <td class="text-center">{{ sc.result }}</td>
              </tr>
            </tbody>
          </q-markup-table>

          <!-- 서비스 상태 -->
          <div v-if="detailServer.services.length" class="section-title">서비스 상태</div>
          <q-card v-if="detailServer.services.length" flat bordered class="q-mb-md">
            <q-list dense>
              <q-item v-for="svc in detailServer.services" :key="svc" dense>
                <q-item-section avatar>
                  <q-icon name="circle" size="8px" color="positive" />
                </q-item-section>
                <q-item-section class="text-caption">{{ svc }}</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- 접근 가능 IP -->
          <div v-if="detailServer.allowedIps" class="section-title">접근 가능 IP</div>
          <pre v-if="detailServer.allowedIps" class="pre-block q-mb-md">{{ detailServer.allowedIps }}</pre>

          <!-- 종합의견 -->
          <div class="section-title">종합의견</div>
          <pre class="pre-block q-mb-md">{{ detailServer.overallComment || '이상 없음' }}</pre>

          <!-- 조치 현황 -->
          <HealthActionPanel
            v-if="selectedId"
            :report-id="selectedId"
            :host-name="detailServer.hostName"
          />

        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import HealthActionPanel from './HealthActionPanel.vue'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const auth = useAuthStore()
const isInternal = computed(() => auth.me?.isInternal !== false)

interface SummaryRow {
  no: number | null
  hostName: string
  ip: string
  cpu: string
  ram: string
  swap: string
  diskMax: string
  logErrors: string
  actionItems: string
}

interface PerfItem {
  beforeVal: string
  beforePct: string
  afterVal: string
  afterPct: string
}

interface DiskEntry {
  filesystem: string
  used: string
  total: string
  pct: string
}

interface HwCheck {
  item: string
  ok: string
  ng: string
  na: string
}

interface SecurityCheck {
  item: string
  result: string
}

interface ServerDetail {
  hostName: string
  serverName: string
  serverOs: string
  ip: string
  inspector: string
  inspectionStart: string
  inspectionEnd: string
  serverShutdown: string
  serverRestart: string
  hwChecks: HwCheck[]
  cpu: PerfItem
  ram: PerfItem
  swap: PerfItem
  networkBefore: string
  networkAfter: string
  disks: DiskEntry[]
  securityChecks: SecurityCheck[]
  services: string[]
  allowedIps: string
  overallComment: string
}

interface HealthReportListItem {
  id: string
  reportDate: string
  reportTitle: string
  serverCount: number
  uploadedAt: string | null
  uploadedBy: string
}

interface HealthReport extends HealthReportListItem {
  summary: SummaryRow[]
  servers: ServerDetail[]
}

const loading = ref(false)
const uploading = ref(false)
const deleting = ref(false)
const search = ref('')

const reports = ref<HealthReportListItem[]>([])
const selectedId = ref<string | null>(null)
const report = ref<HealthReport | null>(null)

const fileInput = ref<HTMLInputElement | null>(null)

const reportOptions = computed(() =>
  reports.value.map((r) => ({
    label: `${r.reportDate} (${r.serverCount}대)`,
    value: r.id,
  }))
)

const sortKey = ref<string>('')
const sortDir = ref<1 | -1>(1)

function setSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 1 ? -1 : 1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

function sortIcon(key: string): string {
  if (sortKey.value !== key) return 'unfold_more'
  return sortDir.value === 1 ? 'arrow_upward' : 'arrow_downward'
}

const filteredSummary = computed(() => {
  if (!report.value) return []
  const q = search.value.trim().toLowerCase()
  if (!q) return report.value.summary
  return report.value.summary.filter(
    (s) => s.hostName.toLowerCase().includes(q) || s.ip.toLowerCase().includes(q)
  )
})

const sortedSummary = computed(() => {
  const rows = filteredSummary.value
  if (!sortKey.value) return rows

  return [...rows].sort((a, b) => {
    let av: string | number = 0
    let bv: string | number = 0

    if (sortKey.value === 'no') {
      av = a.no ?? 0; bv = b.no ?? 0
    } else if (sortKey.value === 'hostName') {
      av = a.hostName; bv = b.hostName
    } else if (sortKey.value === 'cpu') {
      av = parsePercent(detailCpu(a.hostName) || a.cpu)
      bv = parsePercent(detailCpu(b.hostName) || b.cpu)
    } else if (sortKey.value === 'ram') {
      av = parsePercent(detailRam(a.hostName) || a.ram)
      bv = parsePercent(detailRam(b.hostName) || b.ram)
    } else if (sortKey.value === 'disk') {
      av = parsePercent(detailDisk(a.hostName) || a.diskMax)
      bv = parsePercent(detailDisk(b.hostName) || b.diskMax)
    } else if (sortKey.value === 'logErrors') {
      av = parseInt(a.logErrors) || 0
      bv = parseInt(b.logErrors) || 0
    }

    if (av < bv) return -1 * sortDir.value
    if (av > bv) return 1 * sortDir.value
    return 0
  })
})

async function loadList() {
  const res = await api.get<HealthReportListItem[]>('/health-reports')
  reports.value = res.data
  if (reports.value.length && !selectedId.value) {
    selectedId.value = reports.value[0]!.id
    await loadReport(selectedId.value)
  }
}

async function loadReport(id: string) {
  loading.value = true
  try {
    const res = await api.get<HealthReport>(`/health-reports/${id}`)
    report.value = res.data
  } finally {
    loading.value = false
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''

  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await api.post<HealthReport>('/health-reports', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const uploaded = res.data
    await loadList()
    selectedId.value = uploaded.id
    await loadReport(uploaded.id)
    $q.notify({ type: 'positive', message: `${uploaded.reportDate} 보고서 업로드 완료 (${uploaded.summary.length}대)` })
  } catch {
    $q.notify({ type: 'negative', message: '업로드 실패' })
  } finally {
    uploading.value = false
  }
}

function confirmDelete() {
  if (!selectedId.value || !report.value) return
  $q.dialog({
    title: '보고서 삭제',
    message: `${report.value.reportDate} 보고서를 삭제하시겠습니까?`,
    cancel: true,
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      deleting.value = true
      try {
        await api.delete(`/health-reports/${selectedId.value}`)
        selectedId.value = null
        report.value = null
        await loadList()
        $q.notify({ type: 'positive', message: '삭제되었습니다.' })
      } finally {
        deleting.value = false
      }
    })()
  })
}

// ── 서버 상세 데이터 매핑 ──────────────────────────────────────────────────────

const serverDetailMap = computed<Map<string, ServerDetail>>(() => {
  const map = new Map<string, ServerDetail>()
  for (const s of report.value?.servers ?? []) {
    map.set(s.hostName.trim().toLowerCase(), s)
  }
  return map
})

function findDetail(hostName: string): ServerDetail | undefined {
  return serverDetailMap.value.get(hostName.trim().toLowerCase())
}

function cleanTime(val: string): string {
  if (!val) return ''
  const v = val.trim()
  // 숫자가 없고 "시간"이나 "종료"/"재기동"/"재가동" 등 라벨 패턴이면 제거
  if (!/\d/.test(v) && /(시간|종료|재기동|재가동|점검)/.test(v)) return ''
  return v
}

function validPct(val: string): string {
  return val && val !== '-' ? val : ''
}

function detailCpu(hostName: string): string {
  const s = findDetail(hostName)
  if (!s) return ''
  return validPct(s.cpu.afterPct) || validPct(s.cpu.beforePct)
}

function detailRam(hostName: string): string {
  const s = findDetail(hostName)
  if (!s) return ''
  return validPct(s.ram.afterPct) || validPct(s.ram.beforePct)
}

function detailDisk(hostName: string): string {
  const s = findDetail(hostName)
  if (!s) return ''
  const total = s.disks.find((d) => d.filesystem === 'Total')
  return validPct(total?.pct ?? '')
}

// ── 상세 다이얼로그 ────────────────────────────────────────────────────────────

const detailDialog = ref(false)
const detailServer = ref<ServerDetail | null>(null)

function openDetail(hostName: string) {
  const server = findDetail(hostName)
  if (!server) return
  detailServer.value = server
  detailDialog.value = true
}

// ── 색상/포맷 유틸 ─────────────────────────────────────────────────────────────

function parsePercent(val: string): number {
  if (!val) return 0
  const withSign = val.match(/([\d.]+)%/)
  if (withSign) return parseFloat(withSign[1]!)
  // openpyxl이 percentage 셀을 0.45 같은 소수로 반환하는 경우
  const n = parseFloat(val)
  if (!isNaN(n) && n >= 0 && n <= 1) return n * 100
  if (!isNaN(n)) return n
  return 0
}

function formatPct(val: string): string {
  if (!val) return '-'
  if (val.includes('%')) return val
  const n = parseFloat(val)
  if (!isNaN(n) && n > 0 && n <= 1) return `${(n * 100).toFixed(1)}%`
  if (!isNaN(n) && n > 0) return `${n.toFixed(1)}%`
  return val || '-'
}

function metricColor(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'negative'
  if (pct >= 80) return 'orange'
  return 'teal'
}

function metricClass(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'text-negative text-weight-bold'
  if (pct >= 80) return 'text-orange text-weight-medium'
  return ''
}

function splitIps(val: string): string[] {
  return val.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean)
}

function ipCount(val: string): number {
  return splitIps(val).length
}

function formatIp(val: string): string {
  const ips = splitIps(val)
  if (ips.length <= 3) return ips.join(', ')
  return ips.slice(0, 3).join(', ') + ' ...'
}

function logErrorColor(val: string): string {
  const n = parseInt(val)
  if (isNaN(n) || n === 0) return 'grey'
  if (n >= 100) return 'negative'
  return 'orange'
}

function actionClass(val: string): string {
  if (val.includes('⚠')) return 'text-negative'
  if (val.includes('△')) return 'text-orange'
  if (val.includes('이상 없음')) return 'text-positive'
  return 'text-grey-7'
}

function actionPreview(val: string): string {
  if (!val) return '-'
  const firstLine = val.split('\n')[0] ?? val
  return firstLine.length > 30 ? firstLine.slice(0, 30) + '…' : firstLine
}

onMounted(() => {
  void loadList()
})
</script>

<style scoped>
.hidden { display: none; }
.row-hover:hover { background: #f5f5f5; }
.action-preview { white-space: nowrap; }
.sortable-th {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.sortable-th:hover { background: #e8e8e8; }
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
  border-left: 3px solid #1976d2;
  padding-left: 8px;
}
.label-cell {
  background: #f5f5f5;
  font-weight: 500;
  width: 110px;
  color: #555;
}
.pre-block {
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.6;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  font-family: monospace;
  margin: 0;
}
.sticky-header {
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
  border-bottom: 1px solid #e0e0e0;
}
</style>
