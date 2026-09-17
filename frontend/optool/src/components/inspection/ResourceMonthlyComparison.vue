<template>
  <section class="resource-comparison" aria-label="월별 비교">
    <div class="comparison-toolbar">
      <div class="comparison-description">
        <h2>월별 자원 사용량 비교</h2>
        <p>선택한 점검 데이터와 이전 데이터를 비교합니다.</p>
      </div>
      <q-select
        v-model="baseId"
        :options="[{ label: '비교 안 함', value: null }, ...reportOptions]"
        emit-value
        map-options
        dense
        outlined
        label="비교할 이전 데이터"
        class="comparison-base"
        :disable="loading"
        @update:model-value="loadComparison()"
      />
      <q-btn
        v-if="baseId !== (resource.comparison?.id ?? null)"
        flat
        no-caps
        color="primary"
        label="전월과 비교"
        :disable="loading"
        @click="resetBaseline"
      />
    </div>
    <q-banner v-if="error" rounded class="bg-red-1 text-negative q-mb-md" role="alert">
      {{ error }}
      <template #action
        ><q-btn flat label="다시 불러오기" @click="loadComparison(true)"
      /></template>
    </q-banner>
    <div v-else-if="loading" class="text-center q-pa-xl" role="status">
      <q-spinner color="primary" size="32px" />
      <p class="q-mt-sm">비교 결과를 불러오고 있습니다.</p>
    </div>
    <template v-else-if="rows.length">
      <p v-if="!baseReport" class="comparison-notice">
        {{
          resource.comparison
            ? '이전 점검 데이터를 선택하면 사용량 변화를 확인할 수 있습니다.'
            : '전월 점검 데이터가 없습니다. 비교할 다른 데이터를 선택해 주세요.'
        }}
      </p>
      <div class="comparison-results-heading">
        <div class="text-caption text-grey-6">
          {{ baseReport?.reportDate ?? '비교 데이터 없음' }} → {{ compareReport?.reportDate }} 변화
          <span class="q-ml-md">
            <q-badge color="positive" class="q-mr-xs">▼ 사용량 감소</q-badge>
            <q-badge color="negative" class="q-mr-xs">▲ 사용량 증가</q-badge>
            <q-badge color="grey-5">= ±0.5%p 이내 · - 비교할 값 없음</q-badge>
          </span>
        </div>

        <q-input
          v-model="search"
          outlined
          dense
          clearable
          placeholder="호스트명 / IP 검색"
          class="comparison-search"
        >
          <template #prepend><q-icon name="search" size="19px" /></template>
        </q-input>
      </div>
      <div v-if="!filteredRows.length" class="comparison-empty">
        검색 조건에 맞는 서버가 없습니다.
        <q-btn flat color="primary" label="검색 초기화" @click="search = ''" />
      </div>
      <q-card v-else-if="!$q.screen.lt.md" flat bordered class="comparison-table">
        <q-markup-table flat dense separator="horizontal">
          <thead>
            <tr class="text-left bg-grey-2">
              <th style="min-width: 140px">호스트명</th>
              <th style="min-width: 120px">IP</th>
              <th colspan="3" class="text-center border-left" style="width: 210px">CPU (%)</th>
              <th colspan="3" class="text-center border-left" style="width: 210px">RAM (%)</th>
              <th colspan="3" class="text-center border-left" style="width: 210px">
                디스크 전체 (%)
              </th>
            </tr>
            <tr class="text-center bg-grey-1 text-caption text-grey-7">
              <th></th>
              <th></th>
              <th class="border-left sortable-th" @click="setSort('cpu.base')">
                이전 <q-icon :name="sortIcon('cpu.base')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('cpu.cmp')">
                현재 <q-icon :name="sortIcon('cpu.cmp')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('cpu.delta')">
                변화 <q-icon :name="sortIcon('cpu.delta')" size="12px" />
              </th>
              <th class="border-left sortable-th" @click="setSort('ram.base')">
                이전 <q-icon :name="sortIcon('ram.base')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('ram.cmp')">
                현재 <q-icon :name="sortIcon('ram.cmp')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('ram.delta')">
                변화 <q-icon :name="sortIcon('ram.delta')" size="12px" />
              </th>
              <th class="border-left sortable-th" @click="setSort('disk.base')">
                이전 <q-icon :name="sortIcon('disk.base')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('disk.cmp')">
                현재 <q-icon :name="sortIcon('disk.cmp')" size="12px" />
              </th>
              <th class="sortable-th" @click="setSort('disk.delta')">
                변화 <q-icon :name="sortIcon('disk.delta')" size="12px" />
              </th>
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
                <q-badge
                  v-if="baseReport && r.isNew"
                  color="blue"
                  dense
                  class="q-ml-xs"
                  style="font-size: 9px"
                  >이전 기록 없음</q-badge
                >
                <q-badge
                  v-if="r.isRemoved"
                  color="grey"
                  dense
                  class="q-ml-xs"
                  style="font-size: 9px"
                  >현재 기록 없음</q-badge
                >
              </td>
              <td class="text-caption text-grey-7" style="font-size: 11px">{{ formatIp(r.ip) }}</td>

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
      <div v-else class="comparison-cards">
        <article v-for="r in filteredRows" :key="r.hostName" class="comparison-server-card">
          <div class="comparison-card-title">
            <div>
              <strong>{{ r.hostName }}</strong>
              <p>{{ formatIp(r.ip) }}</p>
            </div>
            <q-badge v-if="baseReport && r.isNew" color="blue">이전 기록 없음</q-badge>
            <q-badge v-else-if="r.isRemoved" color="grey">현재 기록 없음</q-badge>
          </div>
          <div class="comparison-card-labels">
            <span>사용량</span><span>이전 → 현재</span><span>변화</span>
          </div>
          <div v-for="metric in metricKinds" :key="metric.key" class="comparison-card-metric">
            <span>{{ metric.label }}</span>
            <span
              >{{ r[metric.key].base || '-' }} <span class="text-grey-5">→</span>
              <strong :class="metricClass(r[metric.key].cmp)">{{
                r[metric.key].cmp || '-'
              }}</strong></span
            >
            <DeltaChip :delta="r[metric.key].delta" />
          </div>
          <div class="text-right">
            <q-btn flat dense no-caps color="primary" label="상세" @click="openDetail(r)" />
          </div>
        </article>
      </div>
    </template>
    <div v-else-if="!error && !loading" class="comparison-empty">
      비교할 서버 측정값이 없습니다.
    </div>

    <!-- 상세 다이얼로그 (비교 보고서 기준) -->
    <q-dialog v-model="detailDialog" maximized>
      <q-card v-if="detailRow" class="comparison-detail-card">
        <q-card-section class="row items-center q-pb-none sticky-header">
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ detailRow.hostName }}</div>
            <div class="text-caption text-grey-6">{{ detailRow.ip }}</div>
          </div>
          <q-space />
          <q-btn
            flat
            dense
            no-caps
            icon="show_chart"
            label="사용량 추이"
            color="primary"
            class="q-mr-sm"
            @click="openTrend(detailRow.hostName)"
          />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="section-title q-mb-sm">자원 사용량 변화</div>
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
                <td class="text-center">
                  <span :class="metricClass(detailRow.cpu.cmp)">{{
                    detailRow.cpu.cmp || '-'
                  }}</span>
                </td>
                <td class="text-center"><DeltaChip :delta="detailRow.cpu.delta" /></td>
              </tr>
              <tr>
                <td class="label-cell">RAM</td>
                <td class="text-center">{{ detailRow.ram.base || '-' }}</td>
                <td class="text-center">
                  <span :class="metricClass(detailRow.ram.cmp)">{{
                    detailRow.ram.cmp || '-'
                  }}</span>
                </td>
                <td class="text-center"><DeltaChip :delta="detailRow.ram.delta" /></td>
              </tr>
              <tr>
                <td class="label-cell">디스크 전체</td>
                <td class="text-center">{{ detailRow.disk.base || '-' }}</td>
                <td class="text-center">
                  <span :class="metricClass(detailRow.disk.cmp)">{{
                    detailRow.disk.cmp || '-'
                  }}</span>
                </td>
                <td class="text-center"><DeltaChip :delta="detailRow.disk.delta" /></td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- 사용량 추이 다이얼로그 -->
    <q-dialog v-model="trendDialog" :maximized="trendMaximized">
      <q-card :style="trendMaximized ? '' : 'width:960px; max-width:calc(100vw - 32px)'">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold">월별 자원 사용량 — {{ trendHostName }}</div>
          <q-space />
          <q-btn
            flat
            round
            dense
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
          <p v-else-if="trendError" class="text-negative" role="alert">{{ trendError }}</p>
          <HealthTrendChart v-else :points="trendPoints" :large="trendMaximized" />
        </q-card-section>
      </q-card>
    </q-dialog>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, defineComponent, h } from 'vue';
import { useQuasar } from 'quasar';
import type { ResourceMonth } from 'src/services/inspectionResources';
import { inspectionError } from 'src/services/inspection';
import { api } from 'boot/axios';
import HealthTrendChart, { type TrendPoint } from 'src/pages/inspection/HealthTrendChart.vue';

const props = defineProps<{ resource: ResourceMonth; active: boolean }>();
const $q = useQuasar();
const metricKinds = [
  { key: 'cpu', label: 'CPU' },
  { key: 'ram', label: 'RAM' },
  { key: 'disk', label: '디스크 전체' },
] as const;

// ── DeltaChip 인라인 컴포넌트 ────────────────────────────────────────────────
const DeltaChip = defineComponent({
  props: { delta: { type: Number, default: null } },
  setup(props) {
    return () => {
      const d = props.delta;
      if (d === null || isNaN(d)) return h('span', { class: 'text-caption text-grey-5' }, '-');
      const abs = Math.abs(d).toFixed(1);
      if (d > 0.5)
        return h('span', { class: 'text-negative text-weight-bold text-caption' }, `▲ +${abs}%p`);
      if (d < -0.5)
        return h('span', { class: 'text-positive text-weight-bold text-caption' }, `▼ -${abs}%p`);
      return h(
        'span',
        { class: 'text-caption text-grey-6' },
        `= ${d >= 0 ? '+' : ''}${d.toFixed(1)}%p`,
      );
    };
  },
});

// ── 타입 ──────────────────────────────────────────────────────────────────────
interface PerfItem {
  beforeVal: string;
  beforePct: string;
  afterVal: string;
  afterPct: string;
}
interface DiskEntry {
  filesystem: string;
  used: string;
  total: string;
  pct: string;
}
interface ServerDetail {
  hostName: string;
  ip: string;
  cpu: PerfItem;
  ram: PerfItem;
  swap: PerfItem;
  disks: DiskEntry[];
}
interface HealthReport {
  id: string;
  reportDate: string;
  reportTitle: string;
  serverCount: number;
  summary: { hostName: string; ip: string }[];
  servers: ServerDetail[];
}
interface MetricPair {
  base: string;
  cmp: string;
  delta: number;
}
interface CompareRow {
  hostName: string;
  ip: string;
  cpu: MetricPair;
  ram: MetricPair;
  disk: MetricPair;
  isNew: boolean;
  isRemoved: boolean;
}

// ── state ──────────────────────────────────────────────────────────────────────
const loading = ref(false);
const reports = ref<{ id: string; reportDate: string; reportTitle: string; serverCount: number }[]>(
  [],
);
const baseId = ref<string | null>(null);
const error = ref('');
let generation = 0;
let loadedResource: ResourceMonth | null = null;
let selectedSource = '';
let defaultBaseline: string | null = null;
const baseReport = ref<HealthReport | null>(null);
const compareReport = ref<HealthReport | null>(null);
const rows = ref<CompareRow[]>([]);
const search = ref('');

const detailDialog = ref(false);
const detailRow = ref<CompareRow | null>(null);

const reportOptions = computed(() =>
  reports.value
    .filter((r) => r.id !== props.resource.source?.id)
    .map((r) => ({
      label: `${r.reportDate} · ${r.reportTitle || '점검 데이터'} (${r.serverCount}대)`,
      value: r.id,
    })),
);

const sortKey = ref('');
const sortDir = ref<1 | -1>(1);

function setSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 1 ? -1 : 1;
  } else {
    sortKey.value = key;
    sortDir.value = 1;
  }
}

function sortIcon(key: string): string {
  if (sortKey.value !== key) return 'unfold_more';
  return sortDir.value === 1 ? 'arrow_upward' : 'arrow_downward';
}

function getVal(r: CompareRow, key: string): number {
  const [metric, field] = key.split('.') as [
    keyof Pick<CompareRow, 'cpu' | 'ram' | 'disk'>,
    'base' | 'cmp' | 'delta',
  ];
  const pair = r[metric];
  if (field === 'delta') return isNaN(pair.delta) ? -Infinity : pair.delta;
  return parsePct(field === 'base' ? pair.base : pair.cmp);
}

const filteredRows = computed(() => {
  const q = (search.value || '').trim().toLowerCase();
  const base = q
    ? rows.value.filter(
        (r) => r.hostName.toLowerCase().includes(q) || r.ip.toLowerCase().includes(q),
      )
    : rows.value;
  if (!sortKey.value) return base;
  return [...base].sort((a, b) => {
    const av = getVal(a, sortKey.value);
    const bv = getVal(b, sortKey.value);
    if (av < bv) return -1 * sortDir.value;
    if (av > bv) return 1 * sortDir.value;
    return 0;
  });
});

// ── 유틸 ──────────────────────────────────────────────────────────────────────
function parsePct(val: string): number {
  if (!val || val === '-') return NaN;
  const m = val.match(/([\d.]+)%/);
  if (m) return parseFloat(m[1]!);
  const n = parseFloat(val);
  if (!isNaN(n) && n >= 0 && n <= 1) return n * 100;
  if (!isNaN(n)) return n;
  return NaN;
}

function validPct(val: string): string {
  return val && val !== '-' ? val : '';
}

function bestPct(s: PerfItem): string {
  return validPct(s.afterPct) || validPct(s.beforePct);
}

function diskTotalPct(s: ServerDetail): string {
  const t = s.disks.find((d) => d.filesystem === 'Total');
  return validPct(t?.pct ?? '');
}

function buildPair(base: string, cmp: string): MetricPair {
  const bv = parsePct(base);
  const cv = parsePct(cmp);
  const delta = !isNaN(bv) && !isNaN(cv) ? cv - bv : NaN;
  return { base, cmp, delta };
}

function serverMap(report: HealthReport): Map<string, ServerDetail> {
  const m = new Map<string, ServerDetail>();
  for (const s of report.servers) m.set(s.hostName.trim().toLowerCase(), s);
  return m;
}

function metricClass(val: string): string {
  const p = parsePct(val);
  if (p >= 90) return 'text-negative text-weight-bold';
  if (p >= 80) return 'text-orange text-weight-medium';
  return '';
}

function formatIp(val: string): string {
  const ips = val
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (ips.length <= 2) return ips.join(', ');
  return ips.slice(0, 2).join(', ') + ' ...';
}

// ── 비교 빌드 ─────────────────────────────────────────────────────────────────
async function loadComparison(refreshOptions = false) {
  const resource = props.resource;
  const currentSource = resource.source?.id;
  if (!currentSource) return;
  const request = ++generation;
  loading.value = true;
  error.value = '';
  detailDialog.value = false;
  trendDialog.value = false;
  trendGeneration++;
  try {
    if (refreshOptions) {
      const res = await api.get<typeof reports.value>('/health-reports');
      if (request !== generation) return;
      reports.value = res.data;
      if (selectedSource !== currentSource) search.value = '';
      if (
        selectedSource !== currentSource ||
        baseId.value === defaultBaseline ||
        (baseId.value && !reports.value.some((r) => r.id === baseId.value))
      ) {
        baseId.value = resource.comparison?.id ?? null;
        selectedSource = currentSource;
      }
      defaultBaseline = resource.comparison?.id ?? null;
    }
    const baseline = baseId.value;
    const [resCmp, resBase] = await Promise.all([
      api.get<HealthReport>(`/health-reports/${currentSource}`),
      baseline && baseline !== currentSource
        ? api.get<HealthReport>(`/health-reports/${baseline}`)
        : null,
    ]);
    if (request !== generation) return;
    compareReport.value = resCmp.data;
    baseReport.value = resBase?.data ?? null;
    const bMap = resBase ? serverMap(resBase.data) : new Map<string, ServerDetail>();

    const cMap = serverMap(resCmp.data);
    const allKeys = new Set([...bMap.keys(), ...cMap.keys()]);
    const result: CompareRow[] = [];

    for (const key of allKeys) {
      const bs = bMap.get(key);
      const cs = cMap.get(key);
      const hostName = cs?.hostName ?? bs?.hostName ?? key;
      const ip = cs?.ip ?? bs?.ip ?? '';

      result.push({
        hostName,
        ip,
        cpu: buildPair(bs ? bestPct(bs.cpu) : '', cs ? bestPct(cs.cpu) : ''),
        ram: buildPair(bs ? bestPct(bs.ram) : '', cs ? bestPct(cs.ram) : ''),
        disk: buildPair(bs ? diskTotalPct(bs) : '', cs ? diskTotalPct(cs) : ''),
        isNew: !bs && !!cs,
        isRemoved: !!bs && !cs,
      });
    }

    result.sort((a, b) => {
      const ad =
        (isNaN(a.cpu.delta) ? 0 : a.cpu.delta) +
        (isNaN(a.ram.delta) ? 0 : a.ram.delta) +
        (isNaN(a.disk.delta) ? 0 : a.disk.delta);
      const bd =
        (isNaN(b.cpu.delta) ? 0 : b.cpu.delta) +
        (isNaN(b.ram.delta) ? 0 : b.ram.delta) +
        (isNaN(b.disk.delta) ? 0 : b.disk.delta);
      return bd - ad;
    });

    rows.value = result;
    loadedResource = resource;
  } catch (e) {
    if (request === generation) {
      error.value = inspectionError(e);
      rows.value = [];
      loadedResource = null;
    }
  } finally {
    if (request === generation) loading.value = false;
  }
}
function resetBaseline() {
  baseId.value = props.resource.comparison?.id ?? null;
  void loadComparison();
}

function openDetail(r: CompareRow) {
  detailRow.value = r;
  detailDialog.value = true;
}

// ── 사용량 추이 다이얼로그 ────────────────────────────────────────────────────────

interface HistoryPointRes {
  reportDate: string;
  cpuPct: number;
  ramPct: number;
  diskPct: number;
}

let trendGeneration = 0;
const trendError = ref('');
const trendDialog = ref(false);
const trendMaximized = ref(false);
const trendLoading = ref(false);
const trendHostName = ref('');
const trendPoints = ref<TrendPoint[]>([]);

async function openTrend(hostName: string) {
  const request = ++trendGeneration;
  trendError.value = '';
  trendPoints.value = [];
  trendHostName.value = hostName;
  trendDialog.value = true;
  trendMaximized.value = false;
  trendLoading.value = true;
  try {
    const res = await api.get<HistoryPointRes[]>(
      `/health-reports/history/${encodeURIComponent(hostName)}`,
    );
    if (request !== trendGeneration) return;
    trendPoints.value = res.data.map((p) => ({
      label: p.reportDate,
      cpu: p.cpuPct,
      ram: p.ramPct,
      disk: p.diskPct,
    }));
  } catch (e) {
    if (request === trendGeneration) trendError.value = inspectionError(e);
  } finally {
    if (request === trendGeneration) trendLoading.value = false;
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
watch(
  () => [props.resource, props.active],
  () => {
    if (props.active && loadedResource !== props.resource) void loadComparison(true);
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  generation++;
  trendGeneration++;
});
</script>

<style scoped>
.resource-comparison {
  margin-top: 24px;
  min-width: 0;
}
h2 {
  margin: 0 0 5px;
  font-size: 16px;
  line-height: 1.5;
  font-weight: 650;
}
p {
  margin: 0;
  color: #748195;
  font-size: 12px;
  line-height: 1.6;
}
.comparison-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.comparison-description {
  flex: 1;
  min-width: 240px;
}
.comparison-base {
  width: 330px;
  max-width: 100%;
}
.comparison-results-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.comparison-results-heading .q-badge {
  margin-top: 4px;
}
.comparison-search {
  width: 260px;
}
.comparison-notice {
  padding: 12px 16px;
  background: #f3f6fa;
  border-radius: 8px;
  margin-bottom: 16px;
}
.comparison-empty {
  padding: 40px 16px;
  text-align: center;
  color: #748195;
}
.comparison-table {
  border-radius: 12px;
  overflow: hidden;
}
.comparison-detail-card {
  width: 960px;
  max-width: calc(100vw - 32px);
  margin: auto;
  height: fit-content;
  max-height: 92vh;
  overflow-y: auto;
}
.comparison-cards {
  background: white;
  border: 1px solid #e1e8f0;
  border-radius: 12px;
  overflow: hidden;
}
.comparison-server-card {
  padding: 16px;
  border-bottom: 1px solid #edf1f5;
}
.comparison-server-card:last-child {
  border-bottom: 0;
}
.comparison-card-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.comparison-card-title strong {
  overflow-wrap: anywhere;
}
.comparison-card-labels,
.comparison-card-metric {
  display: grid;
  grid-template-columns: 76px 1fr 78px;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 8px 0;
}
.comparison-card-labels {
  color: #8c97a7;
  font-size: 11px;
  border-bottom: 1px solid #edf1f5;
}
.comparison-card-labels > :last-child,
.comparison-card-metric > :last-child {
  text-align: right;
}
@media (max-width: 599px) {
  .comparison-toolbar {
    gap: 12px;
  }
  .comparison-base,
  .comparison-search {
    width: 100%;
  }
  .comparison-results-heading .q-ml-md {
    display: block;
    margin-left: 0;
  }
}

.row-hover:hover {
  background: #f5f5f5;
  cursor: pointer;
}
.border-left {
  border-left: 1px solid #e0e0e0;
}
.sortable-th {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.sortable-th:hover {
  background: #e8e8e8;
}
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
