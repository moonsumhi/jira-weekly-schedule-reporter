<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6">월별 비교</div>
      <q-space />

      <q-select
        v-model="baseId"
        :options="[{ label: '없음 (이전 데이터 없음)', value: null }, ...reportOptions]"
        emit-value map-options
        dense outlined
        label="기준 (이전)"
        style="min-width:220px"
        @update:model-value="buildCompare"
      />
      <q-icon name="arrow_forward" color="grey-5" />
      <q-select
        v-model="compareId"
        :options="reportOptions"
        emit-value map-options
        dense outlined
        label="비교 (최근)"
        style="min-width:200px"
        @update:model-value="buildCompare"
      />
    </div>

    <div v-if="!reports.length && !loading" class="text-center text-grey-5 q-pa-xl">
      <q-icon name="compare" size="48px" class="q-mb-sm" /><br />
      업로드된 보고서가 없습니다.<br />
      요약 페이지에서 Excel 파일을 업로드하세요.
    </div>

    <div v-else-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" />
    </div>

    <template v-else-if="rows.length">
      <div class="text-caption text-grey-6 q-mb-sm">
        {{ baseReport?.reportDate ?? '이전 없음' }} → {{ compareReport?.reportDate }} 변화
        <span class="q-ml-md">
          <q-badge color="positive" class="q-mr-xs">▼ 개선</q-badge>
          <q-badge color="negative" class="q-mr-xs">▲ 악화</q-badge>
          <q-badge color="grey-5">- 동일/신규</q-badge>
        </span>
      </div>

      <q-card flat bordered>
        <q-markup-table flat dense separator="horizontal">
          <thead>
            <tr class="text-left bg-grey-2">
              <th style="min-width:140px">Host Name</th>
              <th style="min-width:120px">IP</th>
              <th colspan="3" class="text-center border-left" style="width:210px">CPU (%)</th>
              <th colspan="3" class="text-center border-left" style="width:210px">RAM (%)</th>
              <th colspan="3" class="text-center border-left" style="width:210px">Disk Total (%)</th>
            </tr>
            <tr class="text-center bg-grey-1 text-caption text-grey-7">
              <th></th><th></th>
              <th class="border-left sortable-th" @click="setSort('cpu.base')">이전 <q-icon :name="sortIcon('cpu.base')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('cpu.cmp')">현재 <q-icon :name="sortIcon('cpu.cmp')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('cpu.delta')">변화 <q-icon :name="sortIcon('cpu.delta')" size="12px" /></th>
              <th class="border-left sortable-th" @click="setSort('ram.base')">이전 <q-icon :name="sortIcon('ram.base')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('ram.cmp')">현재 <q-icon :name="sortIcon('ram.cmp')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('ram.delta')">변화 <q-icon :name="sortIcon('ram.delta')" size="12px" /></th>
              <th class="border-left sortable-th" @click="setSort('disk.base')">이전 <q-icon :name="sortIcon('disk.base')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('disk.cmp')">현재 <q-icon :name="sortIcon('disk.cmp')" size="12px" /></th>
              <th class="sortable-th" @click="setSort('disk.delta')">변화 <q-icon :name="sortIcon('disk.delta')" size="12px" /></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in filteredRows"
              :key="r.hostName"
              class="cursor-pointer row-hover"
              @click="openDetail(r)"
            >
              <td class="text-caption text-weight-medium">
                {{ r.hostName }}
                <q-badge v-if="r.isNew" color="blue" dense class="q-ml-xs" style="font-size:9px">NEW</q-badge>
                <q-badge v-if="r.isRemoved" color="grey" dense class="q-ml-xs" style="font-size:9px">이전만</q-badge>
              </td>
              <td class="text-caption text-grey-7" style="font-size:11px">{{ formatIp(r.ip) }}</td>

              <!-- CPU -->
              <td class="text-center border-left text-caption">{{ r.cpu.base || '-' }}</td>
              <td class="text-center text-caption">{{ r.cpu.cmp || '-' }}</td>
              <td class="text-center"><DeltaChip :delta="r.cpu.delta" /></td>

              <!-- RAM -->
              <td class="text-center border-left text-caption">{{ r.ram.base || '-' }}</td>
              <td class="text-center text-caption">{{ r.ram.cmp || '-' }}</td>
              <td class="text-center"><DeltaChip :delta="r.ram.delta" /></td>

              <!-- Disk -->
              <td class="text-center border-left text-caption">{{ r.disk.base || '-' }}</td>
              <td class="text-center text-caption">{{ r.disk.cmp || '-' }}</td>
              <td class="text-center"><DeltaChip :delta="r.disk.delta" /></td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card>
    </template>

    <!-- 상세 다이얼로그 (비교 보고서 기준) -->
    <q-dialog v-model="detailDialog" maximized>
      <q-card v-if="detailRow" style="max-width:960px; margin:auto; height:fit-content; max-height:92vh; overflow-y:auto">
        <q-card-section class="row items-center q-pb-none sticky-header">
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ detailRow.hostName }}</div>
            <div class="text-caption text-grey-6">{{ detailRow.ip }}</div>
          </div>
          <q-space />
          <q-btn flat dense no-caps icon="show_chart" label="추이 현황" color="primary" class="q-mr-sm" @click="openTrend(detailRow.hostName)" />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="section-title q-mb-sm">지표 변화</div>
          <q-markup-table flat dense bordered class="q-mb-md">
            <thead>
              <tr class="bg-grey-2 text-center">
                <th>항목</th>
                <th>{{ baseReport?.reportDate ?? '-' }} (이전)</th>
                <th>{{ compareReport?.reportDate }} (현재)</th>
                <th>변화</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="label-cell">CPU</td>
                <td class="text-center">{{ detailRow.cpu.base || '-' }}</td>
                <td class="text-center"><span :class="metricClass(detailRow.cpu.cmp)">{{ detailRow.cpu.cmp || '-' }}</span></td>
                <td class="text-center"><DeltaChip :delta="detailRow.cpu.delta" /></td>
              </tr>
              <tr>
                <td class="label-cell">RAM</td>
                <td class="text-center">{{ detailRow.ram.base || '-' }}</td>
                <td class="text-center"><span :class="metricClass(detailRow.ram.cmp)">{{ detailRow.ram.cmp || '-' }}</span></td>
                <td class="text-center"><DeltaChip :delta="detailRow.ram.delta" /></td>
              </tr>
              <tr>
                <td class="label-cell">Disk Total</td>
                <td class="text-center">{{ detailRow.disk.base || '-' }}</td>
                <td class="text-center"><span :class="metricClass(detailRow.disk.cmp)">{{ detailRow.disk.cmp || '-' }}</span></td>
                <td class="text-center"><DeltaChip :delta="detailRow.disk.delta" /></td>
              </tr>
            </tbody>
          </q-markup-table>
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
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { api } from 'boot/axios'
import HealthTrendChart, { type TrendPoint } from './HealthTrendChart.vue'

// ── DeltaChip 인라인 컴포넌트 ────────────────────────────────────────────────
const DeltaChip = defineComponent({
  props: { delta: { type: Number, default: null } },
  setup(props) {
    return () => {
      const d = props.delta
      if (d === null || isNaN(d)) return h('span', { class: 'text-caption text-grey-5' }, '-')
      const abs = Math.abs(d).toFixed(1)
      if (d > 0.5) return h('span', { class: 'text-negative text-weight-bold text-caption' }, `▲ +${abs}%`)
      if (d < -0.5) return h('span', { class: 'text-positive text-weight-bold text-caption' }, `▼ -${abs}%`)
      return h('span', { class: 'text-caption text-grey-6' }, `= ${d >= 0 ? '+' : ''}${d.toFixed(1)}%`)
    }
  },
})

// ── 타입 ──────────────────────────────────────────────────────────────────────
interface PerfItem { beforeVal: string; beforePct: string; afterVal: string; afterPct: string }
interface DiskEntry { filesystem: string; used: string; total: string; pct: string }
interface ServerDetail {
  hostName: string; ip: string
  cpu: PerfItem; ram: PerfItem; swap: PerfItem
  disks: DiskEntry[]
}
interface HealthReport {
  id: string; reportDate: string; reportTitle: string; serverCount: number
  summary: { hostName: string; ip: string }[]
  servers: ServerDetail[]
}
interface MetricPair { base: string; cmp: string; delta: number }
interface CompareRow {
  hostName: string; ip: string
  cpu: MetricPair; ram: MetricPair; disk: MetricPair
  isNew: boolean; isRemoved: boolean
}

// ── state ──────────────────────────────────────────────────────────────────────
const loading = ref(false)
const reports = ref<{ id: string; reportDate: string; serverCount: number }[]>([])
const baseId = ref<string | null>(null)
const compareId = ref<string | null>(null)
const baseReport = ref<HealthReport | null>(null)
const compareReport = ref<HealthReport | null>(null)
const rows = ref<CompareRow[]>([])
const search = ref('')

const detailDialog = ref(false)
const detailRow = ref<CompareRow | null>(null)

const reportOptions = computed(() =>
  reports.value.map((r) => ({ label: `${r.reportDate} (${r.serverCount}대)`, value: r.id }))
)

const sortKey = ref('')
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

function getVal(r: CompareRow, key: string): number {
  const [metric, field] = key.split('.') as [keyof Pick<CompareRow, 'cpu' | 'ram' | 'disk'>, 'base' | 'cmp' | 'delta']
  const pair = r[metric]
  if (field === 'delta') return isNaN(pair.delta) ? -Infinity : pair.delta
  return parsePct(field === 'base' ? pair.base : pair.cmp)
}

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase()
  const base = q
    ? rows.value.filter((r) => r.hostName.toLowerCase().includes(q) || r.ip.toLowerCase().includes(q))
    : rows.value
  if (!sortKey.value) return base
  return [...base].sort((a, b) => {
    const av = getVal(a, sortKey.value)
    const bv = getVal(b, sortKey.value)
    if (av < bv) return -1 * sortDir.value
    if (av > bv) return 1 * sortDir.value
    return 0
  })
})

// ── 유틸 ──────────────────────────────────────────────────────────────────────
function parsePct(val: string): number {
  if (!val || val === '-') return NaN
  const m = val.match(/([\d.]+)%/)
  if (m) return parseFloat(m[1]!)
  const n = parseFloat(val)
  if (!isNaN(n) && n >= 0 && n <= 1) return n * 100
  if (!isNaN(n)) return n
  return NaN
}

function validPct(val: string): string {
  return val && val !== '-' ? val : ''
}

function bestPct(s: PerfItem): string {
  return validPct(s.afterPct) || validPct(s.beforePct)
}

function diskTotalPct(s: ServerDetail): string {
  const t = s.disks.find((d) => d.filesystem === 'Total')
  return validPct(t?.pct ?? '')
}

function buildPair(base: string, cmp: string): MetricPair {
  const bv = parsePct(base)
  const cv = parsePct(cmp)
  const delta = !isNaN(bv) && !isNaN(cv) ? cv - bv : NaN
  return { base, cmp, delta }
}

function serverMap(report: HealthReport): Map<string, ServerDetail> {
  const m = new Map<string, ServerDetail>()
  for (const s of report.servers) m.set(s.hostName.trim().toLowerCase(), s)
  return m
}

function metricClass(val: string): string {
  const p = parsePct(val)
  if (p >= 90) return 'text-negative text-weight-bold'
  if (p >= 80) return 'text-orange text-weight-medium'
  return ''
}

function formatIp(val: string): string {
  const ips = val.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean)
  if (ips.length <= 2) return ips.join(', ')
  return ips.slice(0, 2).join(', ') + ' ...'
}

// ── 비교 빌드 ─────────────────────────────────────────────────────────────────
async function buildCompare() {
  if (!compareId.value) return
  loading.value = true
  try {
    const resCmp = await api.get<HealthReport>(`/health-reports/${compareId.value}`)
    compareReport.value = resCmp.data

    let bMap = new Map<string, ServerDetail>()
    if (baseId.value && baseId.value !== compareId.value) {
      const resBase = await api.get<HealthReport>(`/health-reports/${baseId.value}`)
      baseReport.value = resBase.data
      bMap = serverMap(resBase.data)
    } else {
      baseReport.value = null
    }

    const cMap = serverMap(resCmp.data)
    const allKeys = new Set([...bMap.keys(), ...cMap.keys()])
    const result: CompareRow[] = []

    for (const key of allKeys) {
      const bs = bMap.get(key)
      const cs = cMap.get(key)
      const hostName = cs?.hostName ?? bs?.hostName ?? key
      const ip = cs?.ip ?? bs?.ip ?? ''

      result.push({
        hostName, ip,
        cpu: buildPair(bs ? bestPct(bs.cpu) : '', cs ? bestPct(cs.cpu) : ''),
        ram: buildPair(bs ? bestPct(bs.ram) : '', cs ? bestPct(cs.ram) : ''),
        disk: buildPair(bs ? diskTotalPct(bs) : '', cs ? diskTotalPct(cs) : ''),
        isNew: !bs && !!cs,
        isRemoved: !!bs && !cs,
      })
    }

    result.sort((a, b) => {
      const ad = (isNaN(a.cpu.delta) ? 0 : a.cpu.delta) + (isNaN(a.ram.delta) ? 0 : a.ram.delta) + (isNaN(a.disk.delta) ? 0 : a.disk.delta)
      const bd = (isNaN(b.cpu.delta) ? 0 : b.cpu.delta) + (isNaN(b.ram.delta) ? 0 : b.ram.delta) + (isNaN(b.disk.delta) ? 0 : b.disk.delta)
      return bd - ad
    })

    rows.value = result
  } finally {
    loading.value = false
  }
}

function openDetail(r: CompareRow) {
  detailRow.value = r
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

// ── init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  const res = await api.get<{ id: string; reportDate: string; serverCount: number }[]>('/health-reports')
  reports.value = res.data
  if (reports.value.length >= 2) {
    compareId.value = reports.value[0]!.id
    baseId.value = reports.value[1]!.id
  } else if (reports.value.length === 1) {
    compareId.value = reports.value[0]!.id
    baseId.value = null                      // 이전 데이터 없음
  }
  if (compareId.value) await buildCompare()
})
</script>

<style scoped>
.row-hover:hover { background: #f5f5f5; cursor: pointer; }
.border-left { border-left: 1px solid #e0e0e0; }
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
  border-left: 3px solid #1976d2;
  padding-left: 8px;
}
.label-cell {
  background: #f5f5f5;
  font-weight: 500;
  width: 100px;
  color: #555;
}
.sticky-header {
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
  border-bottom: 1px solid #e0e0e0;
}
</style>
