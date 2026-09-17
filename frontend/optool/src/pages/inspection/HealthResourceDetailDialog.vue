<template>
  <q-dialog
    :model-value="modelValue"
    :maximized="$q.screen.lt.sm"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card v-if="record" class="resource-detail">
      <header class="resource-detail-header">
        <div class="detail-heading">
          <span class="detail-eyebrow">자원 점검 상세</span>
          <h2>{{ record.hostName }}</h2>
          <div class="detail-server-meta">
            <span v-if="record.serverName">{{ record.serverName }}</span>
            <span v-if="record.ip" class="server-ip">{{ record.ip }}</span>
            <span v-if="record.detail.serverOs">{{ record.detail.serverOs }}</span>
          </div>
        </div>
        <div class="detail-header-actions">
          <q-btn
            outline
            no-caps
            icon="show_chart"
            label="사용량 추이"
            color="primary"
            @click="openTrend(record.hostName)"
          />
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="자원 점검 상세 닫기"
            @click="emit('update:modelValue', false)"
          />
        </div>
      </header>
      <q-tabs
        v-model="tab"
        dense
        no-caps
        align="left"
        active-color="primary"
        indicator-color="primary"
        class="resource-detail-tabs"
        aria-label="자원 점검 상세 메뉴"
      >
        <q-tab name="resources" label="자원 사용량" />
        <q-tab name="checks" label="점검 항목" />
        <q-tab name="actions" label="조치 내역" />
      </q-tabs>
      <div ref="body" class="resource-detail-body">
        <div class="detail-main">
          <section v-show="tab === 'resources'" class="detail-tab-panel" aria-label="자원 사용량">
            <div class="detail-resource-metrics">
              <article
                v-for="kind in metricKinds"
                :key="kind"
                class="detail-metric"
                :class="metricTone(record[kind].value)"
              >
                <div class="metric-heading">
                  <h3>{{ metricLabels[kind] }}</h3>
                  <span class="metric-status">{{ metricStatus(record[kind].value) }}</span>
                </div>
                <div class="metric-value">
                  {{ record[kind].value === null ? '—' : record[kind].value
                  }}<small v-if="record[kind].value !== null">%</small>
                </div>
                <div class="usage-track" aria-hidden="true">
                  <span :style="{ width: `${record[kind].value ?? 0}%` }" />
                </div>
                <p class="metric-delta">{{ deltaLabel(record[kind].delta) }}</p>
                <p v-if="metricDetail(kind)" class="metric-measurement">{{ metricDetail(kind) }}</p>
              </article>
            </div>
            <p class="detail-threshold">사용률 80% 이상은 주의, 90% 이상은 위험으로 표시합니다.</p>
            <div v-if="record.findings.length" class="detail-findings">
              <div>
                <q-icon name="info_outline" size="20px" /><strong>확인이 필요한 항목</strong>
              </div>
              <ul>
                <li v-for="(finding, index) in record.findings" :key="index">
                  {{ finding.label }}
                </li>
              </ul>
              <q-btn
                flat
                dense
                no-caps
                color="primary"
                label="조치 내역 보기"
                icon-right="arrow_forward"
                @click="tab = 'actions'"
              />
            </div>
            <section class="detail-section">
              <div class="detail-section-heading">
                <h3>디스크 사용량</h3>
                <span>{{ (record.detail.disks || []).length }}개 파일시스템</span>
              </div>
              <div v-if="record.detail.disks?.length" class="detail-table-wrap">
                <table class="detail-table disk-table">
                  <thead>
                    <tr>
                      <th scope="col">파일시스템</th>
                      <th scope="col">사용 / 전체 용량</th>
                      <th scope="col">사용률</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(disk, index) in record.detail.disks" :key="index">
                      <th scope="row" class="filesystem">{{ disk.filesystem || '—' }}</th>
                      <td class="disk-capacity">
                        {{ disk.used || '—' }}<span> / {{ disk.total || '—' }}</span>
                      </td>
                      <td class="disk-usage" :class="metricTone(diskPercent(disk.pct))">
                        <div>
                          <strong>{{ percent(diskPercent(disk.pct)) }}</strong
                          ><span
                            v-if="diskPercent(disk.pct) !== null && diskPercent(disk.pct)! >= 80"
                            class="metric-status"
                            >{{ metricStatus(diskPercent(disk.pct)) }}</span
                          >
                        </div>
                        <div class="usage-track" aria-hidden="true">
                          <span :style="{ width: `${diskPercent(disk.pct) ?? 0}%` }" />
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-else class="detail-empty">등록된 디스크 측정값이 없습니다.</p>
            </section>
            <section
              v-if="
                swap.value ||
                swap.pct !== null ||
                record.detail.networkBefore ||
                record.detail.networkAfter
              "
              class="detail-section"
            >
              <div class="detail-section-heading"><h3>기타 측정값</h3></div>
              <dl class="detail-extra-values">
                <div v-if="swap.value || swap.pct !== null">
                  <dt>Swap</dt>
                  <dd>
                    {{ swap.value || '—'
                    }}<span v-if="swap.pct !== null"> · {{ percent(swap.pct) }}</span>
                  </dd>
                </div>
                <div v-if="record.detail.networkBefore || record.detail.networkAfter">
                  <dt>네트워크</dt>
                  <dd>{{ networkMeasurement(record.detail) }}</dd>
                </div>
              </dl>
            </section>
          </section>
          <section v-show="tab === 'checks'" class="detail-tab-panel" aria-label="점검 항목">
            <section v-if="hardwareChecks.length" class="detail-section">
              <div class="detail-section-heading">
                <h3>하드웨어 육안 점검</h3>
                <span>{{ hardwareChecks.length }}개 항목</span>
              </div>
              <table class="detail-table check-table">
                <thead>
                  <tr>
                    <th scope="col">점검 항목</th>
                    <th scope="col">결과</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(check, index) in hardwareChecks" :key="index">
                    <th scope="row">{{ check.item }}</th>
                    <td>
                      <span class="check-result" :class="check.tone">{{ check.label }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>
            <section v-if="record.detail.securityChecks?.length" class="detail-section">
              <div class="detail-section-heading">
                <h3>시스템 보안 점검</h3>
                <span>{{ record.detail.securityChecks.length }}개 항목</span>
              </div>
              <table class="detail-table check-table">
                <thead>
                  <tr>
                    <th scope="col">점검 항목</th>
                    <th scope="col">결과</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(check, index) in record.detail.securityChecks" :key="index">
                    <th scope="row">{{ check.item }}</th>
                    <td>
                      <span class="check-result" :class="securityTone(check.result)">{{
                        check.result || '미기록'
                      }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </section>
            <section v-if="record.detail.services?.length" class="detail-section">
              <div class="detail-section-heading"><h3>서비스 상태</h3></div>
              <ul class="service-list">
                <li v-for="(service, index) in record.detail.services" :key="index">
                  <q-icon name="terminal" size="18px" /><span>{{ service }}</span>
                </li>
              </ul>
            </section>
            <section v-if="record.detail.allowedIps" class="detail-section">
              <div class="detail-section-heading"><h3>접근 가능 IP</h3></div>
              <pre class="detail-code">{{ record.detail.allowedIps }}</pre>
            </section>
            <p v-if="!hasChecks" class="detail-empty">
              등록된 하드웨어·보안·서비스 점검 항목이 없습니다.
            </p>
          </section>
          <section v-show="tab === 'actions'" class="detail-tab-panel" aria-label="조치 내역">
            <section v-if="importedNotes.length" class="detail-section">
              <div class="detail-section-heading"><h3>점검표 기록</h3></div>
              <div class="inspection-notes">
                <article v-for="note in importedNotes" :key="note.label">
                  <h4>{{ note.label }}</h4>
                  <p>{{ note.content }}</p>
                </article>
              </div>
            </section>
            <section class="detail-section">
              <HealthActionPanel
                v-if="sourceId"
                :key="`${sourceId}:${record.hostName}`"
                :report-id="sourceId"
                :host-name="record.hostName"
              />
              <p v-else class="detail-empty">점검 데이터가 없어 조치 내역을 불러올 수 없습니다.</p>
            </section>
          </section>
        </div>
        <aside class="detail-inspection-info" aria-label="점검 정보">
          <h3>점검 정보</h3>
          <dl>
            <div v-for="item in inspectionInfo" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd :class="{ 'is-empty': !item.value }">{{ item.value || '미기록' }}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </q-card>
  </q-dialog>
  <q-dialog v-model="trendDialog" :maximized="trendMaximized || $q.screen.lt.sm">
    <q-card
      class="resource-trend-dialog"
      :class="{ 'is-maximized': trendMaximized || $q.screen.lt.sm }"
    >
      <header class="resource-detail-header">
        <div class="detail-heading">
          <span class="detail-eyebrow">월별 자원 사용량</span>
          <h2>{{ trendHostName }}</h2>
        </div>
        <div class="detail-header-actions">
          <q-btn
            v-if="!$q.screen.lt.sm"
            flat
            round
            dense
            :icon="trendMaximized ? 'fullscreen_exit' : 'fullscreen'"
            :aria-label="trendMaximized ? '원래 크기로' : '전체 보기'"
            @click="trendMaximized = !trendMaximized"
          />
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="사용량 추이 닫기"
            @click="trendDialog = false"
          />
        </div>
      </header>
      <div class="resource-trend-body">
        <div v-if="trendLoading" class="detail-empty" role="status">
          <q-spinner size="28px" color="primary" />
          <p>사용량 기록을 불러오는 중입니다.</p>
        </div>
        <div v-else-if="trendError" class="detail-empty" role="alert">
          <p>사용량 기록을 불러오지 못했습니다.</p>
          <q-btn outline no-caps color="primary" label="다시 불러오기" @click="loadTrend" />
        </div>
        <HealthTrendChart v-else :points="trendPoints" :large="trendMaximized" />
      </div>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { ref, computed, nextTick, onBeforeUnmount, watch } from 'vue';
import { api } from 'boot/axios';
import type { ResourceServer } from 'src/services/inspectionReports';
import { percent } from 'src/services/inspectionReports';
import { importedMeasurement, networkMeasurement } from 'src/utils/inspectionMeasurements';
import HealthActionPanel from './HealthActionPanel.vue';
import HealthTrendChart, { type TrendPoint } from './HealthTrendChart.vue';
const props = defineProps<{
  modelValue: boolean;
  record: ResourceServer | null;
  sourceId: string;
}>();
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>();
const tab = ref('resources'),
  body = ref<HTMLElement | null>(null);
const metricKinds = ['cpu', 'ram', 'disk'] as const;
const metricLabels = { cpu: 'CPU', ram: '메모리 (RAM)', disk: '디스크 최대 사용률' };
const metricTone = (value: number | null) =>
  value === null ? 'missing' : value >= 90 ? 'danger' : value >= 80 ? 'warning' : 'normal';
const metricStatus = (value: number | null) =>
  value === null ? '측정값 없음' : value >= 90 ? '위험' : value >= 80 ? '주의' : '양호';
const deltaLabel = (value: number | null) =>
  value === null
    ? '전월 비교값 없음'
    : value === 0
      ? '전월과 동일'
      : `전월 대비 ${value > 0 ? '+' : ''}${value}%p`;
function metricDetail(kind: (typeof metricKinds)[number]) {
  if (!props.record) return '';
  return kind === 'disk'
    ? props.record.disk.path || ''
    : importedMeasurement(props.record.detail[kind]).value;
}
const diskPercent = (text: string) => importedMeasurement({ beforePct: text }).pct;
const swap = computed(() => importedMeasurement(props.record?.detail.swap));
const checked = (value: string | boolean) =>
  !['', '-', 'false', '0', 'no', 'none', 'n/a', 'na', '☐', '□'].includes(
    String(value || '')
      .toLowerCase()
      .trim(),
  );
const hardwareChecks = computed(() =>
  (props.record?.detail.hwChecks || []).map((check) => ({
    item: check.item,
    label: checked(check.ng)
      ? '이상 (NG)'
      : checked(check.ok)
        ? '정상 (OK)'
        : checked(check.na)
          ? '해당 없음'
          : '미기록',
    tone: checked(check.ng) ? 'danger' : checked(check.ok) ? 'normal' : 'missing',
  })),
);
const securityTone = (value: string) =>
  /^(ng|fail|false|불량|비정상|이상)$/i.test(value.trim())
    ? 'danger'
    : /^(ok|pass|true|정상|양호)$/i.test(value.trim())
      ? 'normal'
      : 'missing';
const hasChecks = computed(
  () =>
    !!(
      hardwareChecks.value.length ||
      props.record?.detail.securityChecks?.length ||
      props.record?.detail.services?.length ||
      props.record?.detail.allowedIps
    ),
);
const importedNotes = computed(() =>
  [
    { label: '로그 확인', content: props.record?.logErrors },
    { label: '조치 사항', content: props.record?.actionItems },
    { label: '종합 의견', content: props.record?.detail.overallComment },
  ].filter((note) => note.content?.trim()),
);
function cleanTime(value = '') {
  const text = value.trim();
  return !/\d/.test(text) && /(시간|종료|재기동|재가동|점검)/.test(text) ? '' : text;
}
const inspectionInfo = computed(() => [
  { label: '점검자', value: props.record?.detail.inspector },
  { label: '점검 시작', value: cleanTime(props.record?.detail.inspectionStart) },
  { label: '점검 종료', value: cleanTime(props.record?.detail.inspectionEnd) },
  { label: '서버 종료', value: cleanTime(props.record?.detail.serverShutdown) },
  { label: '서버 재기동', value: cleanTime(props.record?.detail.serverRestart) },
]);
const trendDialog = ref(false),
  trendMaximized = ref(false),
  trendLoading = ref(false),
  trendError = ref(false);
const trendHostName = ref(''),
  trendPoints = ref<TrendPoint[]>([]);
let trendRequest = 0;
async function loadTrend() {
  const token = ++trendRequest;
  trendLoading.value = true;
  trendError.value = false;
  trendPoints.value = [];
  try {
    const res = await api.get<
      { reportDate: string; cpuPct: number; ramPct: number; diskPct: number }[]
    >(`/health-reports/history/${encodeURIComponent(trendHostName.value)}`);
    if (token === trendRequest)
      trendPoints.value = res.data.map((p) => ({
        label: p.reportDate,
        cpu: p.cpuPct,
        ram: p.ramPct,
        disk: p.diskPct,
      }));
  } catch {
    if (token === trendRequest) trendError.value = true;
  } finally {
    if (token === trendRequest) trendLoading.value = false;
  }
}
function openTrend(hostName: string) {
  trendHostName.value = hostName;
  trendDialog.value = true;
  trendMaximized.value = false;
  void loadTrend();
}
watch(tab, async () => {
  await nextTick();
  if (body.value) body.value.scrollTop = 0;
});
watch(
  () => [props.modelValue, props.record?.key, props.sourceId],
  async () => {
    tab.value = 'resources';
    trendDialog.value = false;
    ++trendRequest;
    await nextTick();
    if (body.value) body.value.scrollTop = 0;
  },
);
onBeforeUnmount(() => {
  ++trendRequest;
});
</script>
<style scoped>
.resource-detail {
  width: 1080px;
  max-width: calc(100vw - 48px);
  height: min(880px, calc(100dvh - 48px));
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px;
  color: #25364a;
}
.resource-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px 22px;
  background: #fff;
  flex-shrink: 0;
}
.detail-heading {
  min-width: 0;
}
.detail-eyebrow {
  display: block;
  margin-bottom: 7px;
  font-size: 12px;
  color: #61758e;
}
.detail-heading h2 {
  font-size: 23px;
  font-weight: 650;
  line-height: 1.35;
  letter-spacing: -0.4px;
  margin: 0;
  overflow-wrap: anywhere;
}
.detail-server-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-top: 10px;
  font-size: 13px;
  color: #62748a;
}
.server-ip {
  font-variant-numeric: tabular-nums;
}
.detail-header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.detail-header-actions .q-btn {
  font-size: 12px;
}
.resource-detail-tabs {
  flex-shrink: 0;
  padding: 0 16px;
  border-top: 1px solid #eef1f5;
  border-bottom: 1px solid #e1e7ef;
}
.resource-detail-tabs :deep(.q-tab) {
  min-height: 48px;
  padding: 0 20px;
}
.resource-detail-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 204px;
  gap: 26px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  padding: 26px 28px;
  background: #f6f8fb;
  align-content: start;
}
.detail-main {
  min-width: 0;
}
.detail-tab-panel > * + * {
  margin-top: 22px;
}
.detail-resource-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.detail-metric {
  border: 1px solid #dfe6ef;
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  min-width: 0;
}
.normal {
  --metric-color: #347166;
  --metric-bg: #edf6f2;
}
.warning {
  --metric-color: #995517;
  --metric-bg: #fff4de;
}
.danger {
  --metric-color: #b63a43;
  --metric-bg: #fff0f1;
}
.missing {
  --metric-color: #768398;
  --metric-bg: #f0f2f5;
}
.detail-metric.warning,
.detail-metric.danger {
  border-color: color-mix(in srgb, var(--metric-color) 30%, #fff);
}
.metric-heading {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
}
.metric-heading h3 {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  margin: 0;
}
.metric-status {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--metric-color);
  background: var(--metric-bg);
  white-space: nowrap;
}
.metric-value {
  font-size: 34px;
  font-weight: 650;
  line-height: 1.2;
  margin: 16px 0 12px;
  color: var(--metric-color);
  font-variant-numeric: tabular-nums;
}
.metric-value small {
  font-size: 17px;
  font-weight: 500;
  margin-left: 3px;
}
.usage-track {
  height: 5px;
  background: #edf0f4;
  border-radius: 4px;
  overflow: hidden;
}
.usage-track > span {
  display: block;
  height: 100%;
  background: var(--metric-color);
  border-radius: inherit;
}
.metric-delta {
  color: #62748a;
  font-size: 12px;
  margin: 12px 0 0;
}
.metric-measurement {
  font-size: 12px;
  color: #52667e;
  margin: 7px 0 0;
  overflow-wrap: anywhere;
}
.detail-threshold {
  color: #718299;
  font-size: 12px;
  margin: 10px 0 0 !important;
}
.detail-findings {
  padding: 16px 18px;
  border: 1px solid #e5d6b8;
  border-radius: 10px;
  background: #fffbf3;
  font-size: 13px;
}
.detail-findings > div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #806126;
}
.detail-findings ul {
  margin: 10px 0;
  padding-left: 28px;
  color: #5b5243;
  line-height: 1.8;
  overflow-wrap: anywhere;
}
.detail-findings .q-btn {
  font-size: 12px;
  margin-left: 20px;
}
.detail-section {
  background: #fff;
  border: 1px solid #e0e7ef;
  border-radius: 12px;
  overflow: hidden;
}
.detail-section-heading {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #edf0f4;
}
.detail-section-heading h3,
.detail-inspection-info h3 {
  margin: 0;
  font-size: 15px;
  line-height: 1.5;
  font-weight: 650;
}
.detail-section-heading > span {
  font-size: 12px;
  color: #78899b;
}
.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}
.detail-table th,
.detail-table td {
  text-align: left;
  padding: 14px 20px;
  border-bottom: 1px solid #edf0f4;
  overflow-wrap: anywhere;
  line-height: 1.6;
}
.detail-table thead th {
  font-weight: 500;
  font-size: 12px;
  color: #687b90;
  background: #fafbfd;
}
.detail-table tbody th {
  font-weight: 500;
}
.detail-table tbody tr:last-child > * {
  border-bottom: 0;
}
.disk-table th:first-child {
  width: 34%;
}
.disk-capacity {
  font-variant-numeric: tabular-nums;
}
.disk-capacity span {
  color: #7c8b9b;
}
.disk-usage > div:first-child {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 5px;
  margin-bottom: 7px;
}
.disk-usage strong {
  font-size: 14px;
  color: var(--metric-color);
  font-variant-numeric: tabular-nums;
}
.check-table th:first-child {
  width: 65%;
}
.check-result {
  display: inline-block;
  border-radius: 5px;
  padding: 4px 9px;
  color: var(--metric-color);
  background: var(--metric-bg);
  font-size: 12px;
}
.detail-extra-values {
  margin: 0;
  padding: 4px 20px;
}
.detail-extra-values > div {
  display: flex;
  align-items: baseline;
  gap: 18px;
  padding: 12px 0;
}
.detail-extra-values dt {
  color: #718299;
  width: 65px;
  flex-shrink: 0;
  font-size: 12px;
}
.detail-extra-values dd {
  margin: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.service-list {
  list-style: none;
  padding: 0 20px;
  margin: 0;
}
.service-list li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 13px 0;
  border-bottom: 1px solid #edf0f4;
  font-size: 13px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.service-list li:last-child {
  border-bottom: 0;
}
.service-list .q-icon {
  color: #8090a3;
  flex-shrink: 0;
}
.detail-code {
  margin: 16px 20px;
  background: #f5f7fa;
  padding: 14px;
  border-radius: 7px;
  font-size: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.inspection-notes {
  padding: 0 20px;
}
.inspection-notes article {
  padding: 18px 0;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 16px;
}
.inspection-notes article + article {
  border-top: 1px solid #edf0f4;
}
.inspection-notes h4 {
  margin: 2px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: #697b91;
  font-weight: 500;
}
.inspection-notes p {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 14px;
  line-height: 1.85;
}
.detail-inspection-info {
  align-self: start;
  padding: 4px 0 4px 22px;
  border-left: 1px solid #dfe6ee;
}
.detail-inspection-info dl {
  margin: 20px 0 0;
  display: grid;
  gap: 22px;
}
.detail-inspection-info dt {
  color: #75869b;
  font-size: 12px;
  margin-bottom: 6px;
}
.detail-inspection-info dd {
  font-size: 13px;
  margin: 0;
  line-height: 1.7;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
.detail-inspection-info dd.is-empty {
  color: #9aa6b5;
}
.detail-empty {
  margin: 0;
  padding: 30px 20px;
  text-align: center;
  color: #7a8b9d;
  font-size: 13px;
  line-height: 1.8;
}
.resource-trend-dialog {
  width: 820px;
  max-width: calc(100vw - 48px);
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
  border-radius: 14px;
}
.resource-trend-body {
  padding: 24px;
  overflow: auto;
}
.resource-trend-dialog.is-maximized {
  width: 100%;
  max-width: 100%;
  max-height: 100%;
  border-radius: 0;
}
@media (max-width: 950px) {
  .resource-detail-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .detail-inspection-info {
    border-left: 0;
    border-top: 1px solid #dfe6ee;
    padding: 20px 0 0;
  }
  .detail-inspection-info dl {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
  }
}
@media (max-width: 599px) {
  .inspection-notes article {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }
  .resource-detail {
    width: 100%;
    max-width: 100%;
    height: 100dvh;
    max-height: 100dvh;
    border-radius: 0;
  }
  .resource-detail-header {
    gap: 12px;
    padding: 18px 16px;
  }
  .detail-heading h2 {
    font-size: 20px;
  }
  .detail-header-actions {
    flex-direction: column-reverse;
    align-items: flex-end;
    gap: 10px;
  }
  .detail-header-actions .q-btn {
    font-size: 11px;
  }
  .detail-server-meta {
    gap: 4px 10px;
    font-size: 12px;
  }
  .resource-detail-tabs {
    padding: 0 4px;
  }
  .resource-detail-tabs :deep(.q-tab) {
    padding: 0 12px;
  }
  .resource-detail-body {
    padding: 18px 16px;
    gap: 24px;
  }
  .detail-resource-metrics {
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }
  .detail-metric {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 16px;
    padding: 14px 16px;
  }
  .metric-heading {
    justify-content: flex-start;
    align-items: center;
  }
  .metric-value {
    grid-column: 2;
    grid-row: 1 / span 2;
    margin: 0;
    align-self: center;
    font-size: 30px;
  }
  .detail-metric .usage-track {
    grid-column: 1;
    grid-row: 2;
    align-self: center;
  }
  .metric-delta,
  .metric-measurement {
    grid-column: 1 / -1;
    margin: 0;
  }
  .detail-section-heading {
    padding: 16px;
  }
  .detail-table th,
  .detail-table td {
    padding: 12px;
  }
  .disk-table thead {
    display: none;
  }
  .disk-table tbody tr {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 105px;
    padding: 14px 16px;
    gap: 4px 16px;
    border-bottom: 1px solid #edf0f4;
  }
  .disk-table tbody tr:last-child {
    border-bottom: 0;
  }
  .disk-table tbody th,
  .disk-table tbody td {
    padding: 0;
    border: 0;
    width: auto;
  }
  .disk-table .disk-capacity {
    grid-column: 1;
    font-size: 12px;
  }
  .disk-table .disk-usage {
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: center;
  }
  .detail-inspection-info dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .resource-trend-body {
    padding: 16px;
  }
}
</style>
