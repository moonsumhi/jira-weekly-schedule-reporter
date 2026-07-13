<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6">서버 점검 서버리스트</div>
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
    </div>

    <div v-if="!reports.length && !loading" class="text-center text-grey-5 q-pa-xl">
      <q-icon name="description" size="48px" class="q-mb-sm" /><br />
      업로드된 보고서가 없습니다.<br />
      요약 페이지에서 Excel 파일을 업로드하세요.
    </div>

    <div v-else-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" />
    </div>

    <template v-else-if="report">
      <div class="text-caption text-grey-6 q-mb-md">
        {{ report.reportTitle }} · {{ report.servers.length }}대
      </div>

      <div class="row q-gutter-md">
        <q-card
          v-for="s in filteredServers"
          :key="s.hostName"
          flat bordered
          class="server-card cursor-pointer"
          @click="openDetail(s)"
        >
          <q-card-section class="q-pb-xs">
            <div class="text-subtitle2 text-weight-bold">{{ s.hostName }}</div>
            <div class="text-caption text-grey-6">{{ s.ip }}</div>
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <div class="row q-gutter-xs">
              <q-chip dense :color="metricColor(validPct(s.cpu.afterPct) || validPct(s.cpu.beforePct))" text-color="white" size="sm">
                CPU {{ validPct(s.cpu.afterPct) || validPct(s.cpu.beforePct) || '-' }}
              </q-chip>
              <q-chip dense :color="metricColor(validPct(s.ram.afterPct) || validPct(s.ram.beforePct))" text-color="white" size="sm">
                RAM {{ validPct(s.ram.afterPct) || validPct(s.ram.beforePct) || '-' }}
              </q-chip>
              <template v-if="totalDisk(s) && validPct(totalDisk(s)!.pct)">
                <q-chip dense :color="metricColor(validPct(totalDisk(s)!.pct))" text-color="white" size="sm">
                  Disk {{ validPct(totalDisk(s)!.pct) }}
                </q-chip>
              </template>
            </div>
          </q-card-section>
        </q-card>
      </div>
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
          <q-btn flat dense no-caps icon="show_chart" label="추이 현황" color="primary" class="q-mr-sm" @click="openTrend(detailServer.hostName)" />
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

    <!-- 추이 현황 다이얼로그 -->
    <q-dialog v-model="trendDialog" :maximized="trendMaximized">
      <q-card :style="trendMaximized ? '' : 'min-width:640px; max-width:90vw'">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold">RAM / Disk 월별 추이 — {{ trendHostName }}</div>
          <q-space />
          <q-btn
            flat round dense
            :icon="trendMaximized ? 'fullscreen_exit' : 'fullscreen'"
            @click="trendMaximized = !trendMaximized"
          >
            <q-tooltip>{{ trendMaximized ? '원래 크기로' : '전체 보기' }}</q-tooltip>
          </q-btn>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <div v-if="trendLoading" class="text-center q-pa-lg">
            <q-spinner size="32px" />
          </div>
          <HealthTrendChart v-else :points="trendPoints" :large="trendMaximized" />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from 'boot/axios'
import HealthActionPanel from './HealthActionPanel.vue'
import HealthTrendChart, { type TrendPoint } from './HealthTrendChart.vue'

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
  servers: ServerDetail[]
}

const loading = ref(false)
const search = ref('')
const reports = ref<HealthReportListItem[]>([])
const selectedId = ref<string | null>(null)  // 현재 선택된 report id
const report = ref<HealthReport | null>(null)

const reportOptions = computed(() =>
  reports.value.map((r) => ({
    label: `${r.reportDate} (${r.serverCount}대)`,
    value: r.id,
  }))
)

const filteredServers = computed(() => {
  if (!report.value) return []
  const q = search.value.trim().toLowerCase()
  if (!q) return report.value.servers
  return report.value.servers.filter(
    (s) => s.hostName.toLowerCase().includes(q) || s.ip.toLowerCase().includes(q)
  )
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

const detailDialog = ref(false)
const detailServer = ref<ServerDetail | null>(null)

function openDetail(s: ServerDetail) {
  detailServer.value = s
  detailDialog.value = true
}

// ── 추이 현황 다이얼로그 ────────────────────────────────────────────────────────

interface HistoryPointRes {
  reportDate: string
  cpuPct: number
  ramPct: number
  diskPct: number
}

const trendDialog = ref(false)
const trendMaximized = ref(false)
const trendLoading = ref(false)
const trendHostName = ref('')
const trendPoints = ref<TrendPoint[]>([])

async function openTrend(hostName: string) {
  trendHostName.value = hostName
  trendDialog.value = true
  trendMaximized.value = false
  trendLoading.value = true
  try {
    const res = await api.get<HistoryPointRes[]>(`/health-reports/history/${encodeURIComponent(hostName)}`)
    trendPoints.value = res.data.map((p) => ({ label: p.reportDate, cpu: p.cpuPct, ram: p.ramPct, disk: p.diskPct }))
  } catch {
    trendPoints.value = []
  } finally {
    trendLoading.value = false
  }
}

function parsePercent(val: string): number {
  const m = val.match(/([\d.]+)%/)
  return m ? parseFloat(m[1]!) : 0
}

function metricClass(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'text-negative text-weight-bold'
  if (pct >= 80) return 'text-orange text-weight-medium'
  return ''
}

function cleanTime(val: string): string {
  if (!val) return ''
  const v = val.trim()
  if (!/\d/.test(v) && /(시간|종료|재기동|재가동|점검)/.test(v)) return ''
  return v
}

function validPct(val: string): string {
  return val && val !== '-' ? val : ''
}

function totalDisk(s: ServerDetail): DiskEntry | undefined {
  return s.disks.find((d) => d.filesystem === 'Total')
}

function metricColor(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'negative'
  if (pct >= 80) return 'orange'
  return 'positive'
}

onMounted(() => {
  void loadList()
})
</script>

<style scoped>
.server-card {
  width: 200px;
  transition: box-shadow 0.2s;
}
.server-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
  padding-left: 2px;
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
