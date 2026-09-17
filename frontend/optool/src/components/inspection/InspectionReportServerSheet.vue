<template>
  <article class="appendix-server" :aria-labelledby="`${sheetId}-title`" :id="sheetId">
    <header class="sheet-header">
      <div class="sheet-heading">
        <span class="sheet-number">{{ String(index + 1).padStart(2, '0') }}</span>
        <div>
          <h3 :id="`${sheetId}-title`">{{ server.hostName }}</h3>
          <p
            v-if="server.serverName && server.serverName !== server.hostName"
            class="sheet-server-name"
          >
            {{ server.serverName }}
          </p>
        </div>
      </div>
      <dl class="sheet-meta">
        <div>
          <dt>IP 주소</dt>
          <dd class="monospace">{{ server.ip || '미기록' }}</dd>
        </div>
        <div>
          <dt>운영체제</dt>
          <dd>{{ server.detail.serverOs || '미기록' }}</dd>
        </div>
        <div>
          <dt>점검자</dt>
          <dd>{{ server.detail.inspector || '미기록' }}</dd>
        </div>
        <div>
          <dt>점검 시간</dt>
          <dd>
            {{ server.detail.inspectionStart || '미기록' }} ~
            {{ server.detail.inspectionEnd || '미기록' }}
          </dd>
        </div>
      </dl>
    </header>

    <div class="sheet-body">
      <section class="sheet-section">
        <h4>자원 사용량</h4>
        <div class="appendix-resource-metrics">
          <div
            v-for="item in measurements"
            :key="item.kind"
            class="sheet-metric"
            :class="item.level"
          >
            <div class="sheet-metric-heading">
              <b>{{ item.label }}</b>
              <span class="sheet-result" :class="item.level">{{ item.status }}</span>
            </div>
            <strong class="sheet-metric-value">{{ percent(item.metric.value) }}</strong>
            <span class="sheet-metric-delta">{{ delta(item.metric.delta) }}</span>
            <span class="sheet-metric-basis"
              >{{ measurementBasis(item.metric)
              }}{{ item.metric.path ? ` · ${item.metric.path}` : '' }}</span
            >
          </div>
        </div>
      </section>

      <section v-if="server.detail.disks?.length" class="sheet-section">
        <h4>디스크 사용량</h4>
        <table
          class="sheet-table sheet-disk-table"
          :aria-label="`${server.hostName} 디스크 사용량`"
        >
          <thead>
            <tr>
              <th scope="col">파일시스템</th>
              <th scope="col">사용 중</th>
              <th scope="col">전체 용량</th>
              <th scope="col">사용률</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(disk, i) in server.detail.disks"
              :key="i"
              :class="{ 'disk-total': disk.filesystem.trim().toLowerCase() === 'total' }"
            >
              <th scope="row" class="monospace">{{ disk.filesystem }}</th>
              <td>{{ disk.used || '—' }}</td>
              <td>{{ disk.total || '—' }}</td>
              <td class="numeric-emphasis">{{ disk.pct || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section
        v-if="server.detail.swap || server.detail.networkBefore || server.detail.networkAfter"
        class="sheet-section"
      >
        <h4>Swap · 네트워크</h4>
        <table
          class="sheet-table sheet-extra-table"
          :aria-label="`${server.hostName} Swap 및 네트워크 측정값`"
        >
          <thead>
            <tr>
              <th scope="col">항목</th>
              <th scope="col">측정값</th>
              <th scope="col">사용률</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="server.detail.swap">
              <th scope="row">Swap</th>
              <td>{{ swap.value || '—' }}</td>
              <td class="numeric-emphasis">{{ percent(swap.pct) }}</td>
            </tr>
            <tr v-if="server.detail.networkBefore || server.detail.networkAfter">
              <th scope="row">네트워크</th>
              <td colspan="2">{{ networkMeasurement(server.detail) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <div
        v-if="hardwareChecks.length || server.detail.securityChecks?.length"
        class="sheet-checks"
      >
        <section v-if="hardwareChecks.length" class="sheet-section">
          <h4>하드웨어 점검</h4>
          <table
            class="sheet-table sheet-check-table"
            :aria-label="`${server.hostName} 하드웨어 점검`"
          >
            <thead>
              <tr>
                <th scope="col">항목</th>
                <th scope="col">결과</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(check, i) in hardwareChecks" :key="i">
                <th scope="row">{{ check.item }}</th>
                <td>
                  <span class="sheet-result" :class="check.tone">{{ check.label }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
        <section v-if="server.detail.securityChecks?.length" class="sheet-section">
          <h4>보안 점검</h4>
          <table class="sheet-table sheet-check-table" :aria-label="`${server.hostName} 보안 점검`">
            <thead>
              <tr>
                <th scope="col">항목</th>
                <th scope="col">결과</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(check, i) in server.detail.securityChecks" :key="i">
                <th scope="row">{{ check.item }}</th>
                <td>{{ check.result || '미기록' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <section v-if="server.detail.services?.length" class="sheet-section">
        <h4>서비스 확인</h4>
        <ul class="sheet-services">
          <li v-for="(service, i) in server.detail.services" :key="i">{{ service }}</li>
        </ul>
      </section>

      <section
        v-if="
          server.detail.allowedIps || server.detail.serverShutdown || server.detail.serverRestart
        "
        class="sheet-section"
      >
        <h4>접근 설정 · 작업 시각</h4>
        <dl class="sheet-settings">
          <div v-if="server.detail.allowedIps">
            <dt>접근 허용 IP</dt>
            <dd class="monospace">{{ server.detail.allowedIps }}</dd>
          </div>
          <div v-if="server.detail.serverShutdown">
            <dt>서버 종료</dt>
            <dd>{{ server.detail.serverShutdown }}</dd>
          </div>
          <div v-if="server.detail.serverRestart">
            <dt>서버 재시작</dt>
            <dd>{{ server.detail.serverRestart }}</dd>
          </div>
        </dl>
      </section>

      <section v-if="server.detail.overallComment" class="sheet-section sheet-opinion">
        <h4>점검 의견</h4>
        <p>{{ server.detail.overallComment }}</p>
      </section>

      <section
        v-if="editable || server.action || inspectionActionNote(server.actionItems)"
        class="sheet-section sheet-action"
        :class="{ 'screen-only': !server.action && !inspectionActionNote(server.actionItems) }"
      >
        <h4>조치 내역</h4>
        <InspectionReportAction
          :action="server.action"
          :action-items="server.actionItems"
          :host-name="server.hostName"
          :editable="!!editable"
          @edit="emit('action')"
        />
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { percent, type ResourceServer, type ReportSnapshot } from 'src/services/inspectionReports';
import {
  importedMeasurement,
  measurementBasis,
  networkMeasurement,
} from 'src/utils/inspectionMeasurements';
import { resourceMetricLevel, inspectionActionNote } from 'src/utils/inspectionReportResources';
import InspectionReportAction from './InspectionReportAction.vue';

const props = defineProps<{
  server: ResourceServer;
  thresholds: ReportSnapshot['thresholds'];
  index: number;
  editable?: boolean;
}>();
const emit = defineEmits<{ action: [] }>();
const sheetId = computed(() => `appendix-server-${props.server.key}`);
const metricStatus = (level: ReturnType<typeof resourceMetricLevel>) =>
  ({ danger: '위험', warning: '주의', missing: '측정값 없음', neutral: '기준 이내' })[level];
const measurements = computed(() =>
  (['cpu', 'ram', 'disk'] as const).map((kind) => {
    const level = resourceMetricLevel(props.server[kind].value, props.thresholds);
    return {
      kind,
      label: kind === 'disk' ? '디스크 최대' : kind.toUpperCase(),
      metric: props.server[kind],
      level,
      status: metricStatus(level),
    };
  }),
);
const swap = computed(() => importedMeasurement(props.server.detail.swap));
const delta = (value: number | null) =>
  value == null
    ? '전월 비교값 없음'
    : value === 0
      ? '전월과 동일'
      : `전월 대비 ${value > 0 ? '+' : ''}${value}%p`;
const checked = (value: string | boolean) =>
  !['', '-', 'false', '0', 'no', 'none', 'n/a', 'na', '☐', '□'].includes(
    String(value || '')
      .toLowerCase()
      .trim(),
  );
const hardwareChecks = computed(() =>
  (props.server.detail.hwChecks || []).map((check) => ({
    item: check.item,
    label: checked(check.ng)
      ? 'NG'
      : checked(check.ok)
        ? 'OK'
        : checked(check.na)
          ? 'N/A'
          : '미확인',
    tone: checked(check.ng)
      ? 'danger'
      : checked(check.ok)
        ? 'positive'
        : checked(check.na)
          ? 'muted'
          : 'missing',
  })),
);
</script>

<style scoped>
.appendix-server {
  margin-top: 28px;
  border: 1px solid #dbe3ec;
  border-radius: 10px;
  scroll-margin-top: 170px;
  color: #34475c;
}
.sheet-header {
  padding: 22px 24px 20px;
  background: #f3f6fa;
  border-bottom: 1px solid #dbe3ec;
  border-radius: 10px 10px 0 0;
}
.sheet-heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.sheet-heading > div {
  min-width: 0;
}
.sheet-number {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  background: #e3ebf4;
  color: #4b6685;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
.sheet-heading h3 {
  margin: 1px 0 0;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.45;
  overflow-wrap: anywhere;
  color: #243b55;
}
.sheet-server-name {
  margin: 5px 0 0;
  font-size: 12px;
  color: #617389;
  overflow-wrap: anywhere;
}
.sheet-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 20px 0 0;
}
.sheet-meta dt {
  color: #63768b;
  font-size: 11px;
  margin-bottom: 5px;
}
.sheet-meta dd {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.monospace {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
.sheet-body {
  padding: 0 24px 24px;
}
.sheet-section {
  margin-top: 24px;
  min-width: 0;
}
.sheet-section h4 {
  margin: 0 0 12px;
  color: #334c67;
  font-size: 13px;
  line-height: 1.5;
  font-weight: 650;
}
.appendix-resource-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.sheet-metric {
  padding: 14px;
  border: 1px solid #e0e6ee;
  border-radius: 7px;
  min-width: 0;
}
.sheet-metric.warning {
  border-color: #e8d5b1;
  background: #fffcf6;
}
.sheet-metric.danger {
  border-color: #ebc9c6;
  background: #fffafa;
}
.sheet-metric.missing {
  background: #f8f9fb;
  border-style: dashed;
}
.sheet-metric-heading {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 5px;
}
.sheet-metric-heading b {
  font-size: 12px;
  font-weight: 600;
}
.sheet-metric-value {
  display: block;
  margin: 12px 0 7px;
  color: #2b4662;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
}
.sheet-metric.warning .sheet-metric-value {
  color: #966211;
}
.sheet-metric.danger .sheet-metric-value {
  color: #b64d43;
}
.sheet-metric.missing .sheet-metric-value {
  color: #8793a2;
}
.sheet-metric-delta,
.sheet-metric-basis {
  display: block;
  color: #596d82;
  font-size: 11px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.sheet-metric-basis {
  margin-top: 3px;
  color: #718194;
  font-size: 10px;
}
.sheet-result {
  display: inline-block;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.4;
}
.sheet-result.danger {
  color: #ad433c;
  background: #fae9e7;
}
.sheet-result.warning,
.sheet-result.missing {
  color: #8c6429;
  background: #f8eedc;
}
.sheet-result.positive {
  color: #3a7259;
  background: #eaf4ed;
}
.sheet-result.neutral,
.sheet-result.muted {
  color: #637487;
  background: #eef2f6;
}
.sheet-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 12px;
  line-height: 1.65;
}
.sheet-table th,
.sheet-table td {
  padding: 9px 10px;
  text-align: left;
  border-bottom: 1px solid #e3e9ef;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.sheet-table thead th {
  background: #f1f5f9;
  color: #4a6179;
  font-size: 11px;
  font-weight: 600;
}
.sheet-table tbody th {
  font-weight: 500;
}
.sheet-table tbody tr:nth-child(even) {
  background: #fafbfd;
}
.sheet-disk-table th:first-child {
  width: 40%;
}
.sheet-disk-table td,
.sheet-disk-table thead th:not(:first-child) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.sheet-table .disk-total {
  border-top: 2px solid #dbe3ec;
  background: #f4f7fa;
}
.numeric-emphasis {
  font-weight: 650;
}
.sheet-extra-table th:first-child {
  width: 25%;
}
.sheet-extra-table th:last-child {
  width: 22%;
}
.sheet-checks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.sheet-check-table th:first-child {
  width: 52%;
}
.sheet-check-table td {
  white-space: pre-wrap;
}
.sheet-services {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  line-height: 1.8;
}
.sheet-services li {
  position: relative;
  padding: 7px 12px 7px 24px;
  border-bottom: 1px solid #e6ebf1;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.sheet-services li::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 16px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #8496a9;
}
.sheet-settings {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
}
.sheet-settings > div {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 12px;
  padding: 8px 10px;
  border-bottom: 1px solid #e6ebf1;
}
.sheet-settings dt {
  color: #60748a;
}
.sheet-settings dd {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.sheet-opinion {
  background: #f5f8fb;
  border-left: 3px solid #a6bbd1;
  padding: 14px 16px;
}
.sheet-opinion h4 {
  margin-bottom: 7px;
}
.sheet-opinion p {
  margin: 0;
  font-size: 12px;
  line-height: 1.9;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.sheet-action {
  border-top: 1px solid #dbe3ec;
  padding-top: 20px;
}
@media (max-width: 700px) {
  .sheet-header {
    padding: 18px 16px;
  }
  .sheet-heading h3 {
    font-size: 18px;
  }
  .sheet-body {
    padding: 0 16px 20px;
  }
  .sheet-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 12px;
  }
  .sheet-checks {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }
  .sheet-table th,
  .sheet-table td {
    padding: 8px 6px;
    font-size: 11px;
  }
}
@media (max-width: 500px) {
  .appendix-resource-metrics {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }
  .sheet-metric {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: 10px;
    padding: 12px;
  }
  .sheet-metric-heading {
    justify-content: flex-start;
    align-self: center;
  }
  .sheet-metric-value {
    margin: 0;
    font-size: 24px;
  }
  .sheet-metric-delta {
    margin-top: 7px;
    grid-column: 1 / -1;
  }
  .sheet-metric-basis {
    grid-column: 1 / -1;
  }
  .sheet-settings > div {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }
}
@media print {
  .appendix-server {
    margin-top: 18px;
    border: 0;
    border-radius: 0;
    break-inside: auto;
  }
  .appendix-server + .appendix-server {
    break-before: page;
    margin-top: 0;
  }
  .sheet-header {
    padding: 16px 18px;
    border-radius: 0;
    border-top: 3px solid #486987;
    break-inside: avoid;
    break-after: avoid;
    print-color-adjust: exact;
  }
  .sheet-heading h3 {
    font-size: 18px;
  }
  .sheet-meta {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 14px;
  }
  .sheet-body {
    padding: 0;
  }
  .sheet-section {
    margin-top: 18px;
  }
  .sheet-section h4 {
    break-after: avoid;
  }
  .appendix-resource-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    break-inside: avoid;
  }
  .sheet-metric {
    display: block;
    padding: 12px;
    print-color-adjust: exact;
  }
  .sheet-metric-heading {
    justify-content: space-between;
  }
  .sheet-metric-value {
    margin: 10px 0 6px;
    font-size: 23px;
  }
  .sheet-result {
    print-color-adjust: exact;
  }
  .sheet-table {
    font-size: 11px;
  }
  .sheet-table th,
  .sheet-table td {
    padding: 7px 9px;
  }
  .sheet-table thead {
    display: table-header-group;
  }
  .sheet-table thead th,
  .sheet-table tbody tr {
    print-color-adjust: exact;
  }
  .sheet-table tr {
    break-inside: avoid;
  }
  .sheet-checks {
    display: block;
  }
  .sheet-check-table th:first-child {
    width: 52%;
  }
  .sheet-services li,
  .sheet-settings > div {
    break-inside: avoid;
  }
  .sheet-settings > div {
    grid-template-columns: 110px minmax(0, 1fr);
    gap: 12px;
  }
  .sheet-opinion {
    print-color-adjust: exact;
  }
  .sheet-opinion p {
    orphans: 3;
    widows: 3;
  }
  .sheet-action {
    padding-top: 14px;
  }
}
</style>
