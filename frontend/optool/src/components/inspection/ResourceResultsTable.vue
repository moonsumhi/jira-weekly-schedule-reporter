<template>
  <q-table
    flat
    class="resource-results"
    row-key="key"
    :rows="rows"
    :columns="columns"
    v-model:pagination="pagination"
    :grid="$q.screen.lt.md"
    :rows-per-page-options="[25, 50, 0]"
    rows-per-page-label="페이지당 항목"
    :pagination-label="(first, last, total) => `${first}–${last} / ${total}건`"
  >
    <template #body-cell-name="props">
      <q-td :props="props" class="identity-cell">
        <ResourceResultIdentity
          :row="props.row"
          :can-view-asset="canViewAsset"
          :can-write="canWrite"
          :busy="busy"
          @mapping="emit('mapping', $event)"
        />
      </q-td>
    </template>
    <template #body-cell-status="props">
      <q-td :props="props"
        ><span class="result-status" :class="props.row.status.tone"
          ><i />{{ props.row.status.label }}</span
        ></q-td
      >
    </template>
    <template v-for="kind in metricKinds" :key="kind" v-slot:[`body-cell-${kind}`]="props">
      <q-td :props="props" class="metric-cell">
        <ResourceUsageMetric v-if="props.row.record" :metric="props.row.record[kind]" />
        <span v-else class="text-grey-5">—</span>
      </q-td>
    </template>
    <template #body-cell-notes="props">
      <q-td :props="props" class="notes-cell">
        <div v-if="props.row.notes.length" class="result-notes">
          <span v-for="note in props.row.notes.slice(0, 2)" :key="note">{{ note }}</span>
          <small v-if="props.row.notes.length > 2"
            >외 {{ props.row.notes.length - 2 }}건 · 상세 보기</small
          >
          <q-tooltip class="notes-tooltip">{{ props.row.notes.join('\n') }}</q-tooltip>
        </div>
        <span v-else class="text-grey-5">—</span>
      </q-td>
    </template>
    <template #body-cell-detail="props">
      <q-td :props="props"
        ><q-btn
          v-if="props.row.record"
          flat
          dense
          no-caps
          color="primary"
          label="상세"
          :aria-label="`${props.row.name} 점검 상세`"
          @click="emit('detail', props.row.record)"
      /></q-td>
    </template>
    <template #item="props">
      <article class="result-card">
        <div class="result-card-heading">
          <ResourceResultIdentity
            :row="props.row"
            :can-view-asset="canViewAsset"
            :can-write="canWrite"
            :busy="busy"
            @mapping="emit('mapping', $event)"
          />
          <span class="result-status" :class="props.row.status.tone"
            ><i />{{ props.row.status.label }}</span
          >
        </div>
        <div v-if="props.row.record" class="result-card-metrics">
          <div v-for="kind in metricKinds" :key="kind">
            <label>{{ metricLabels[kind] }}</label
            ><ResourceUsageMetric :metric="props.row.record[kind]" />
          </div>
        </div>
        <div v-if="props.row.notes.length" class="result-notes result-card-notes">
          <span v-for="note in props.row.notes.slice(0, 2)" :key="note">{{ note }}</span>
          <small v-if="props.row.notes.length > 2">외 {{ props.row.notes.length - 2 }}건</small>
        </div>
        <div v-if="props.row.record" class="result-card-footer">
          <q-btn
            flat
            dense
            no-caps
            color="primary"
            label="상세 점검 · 조치 내역"
            @click="emit('detail', props.row.record)"
          />
        </div>
      </article>
    </template>
    <template #no-data>
      <div class="result-no-match">
        <q-icon name="search_off" size="28px" /><strong>조건에 맞는 항목이 없습니다</strong
        ><q-btn flat color="primary" label="전체 결과 보기" @click="emit('reset')" />
      </div>
    </template>
  </q-table>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
import { useQuasar, type QTableColumn } from 'quasar';
import type { ResourceServer } from 'src/services/inspectionReports';
import type { ResourceResultRow } from 'src/utils/inspectionResources';
import ResourceUsageMetric from './ResourceUsageMetric.vue';
import ResourceResultIdentity from './ResourceResultIdentity.vue';
const props = defineProps<{
  rows: ResourceResultRow[];
  canViewAsset: boolean;
  canWrite: boolean;
  busy: boolean;
}>();
const emit = defineEmits<{
  detail: [record: ResourceServer];
  mapping: [record: ResourceServer];
  reset: [];
}>();
const $q = useQuasar();
const pagination = ref({ sortBy: 'status', descending: false, page: 1, rowsPerPage: 25 });
const metricKinds = ['cpu', 'ram', 'disk'] as const;
const metricLabels = { cpu: 'CPU', ram: 'RAM', disk: '디스크 최대' };
const columns: QTableColumn<ResourceResultRow>[] = [
  { name: 'name', label: '서버', field: 'name', align: 'left', sortable: true },
  { name: 'status', label: '상태', field: (row) => row.status.rank, align: 'left', sortable: true },
  ...metricKinds.map((kind) => ({
    name: kind,
    label: metricLabels[kind],
    field: (row: ResourceResultRow) => row.record?.[kind].value ?? null,
    align: 'right' as const,
    sortable: true,
  })),
  { name: 'notes', label: '확인할 내용', field: (row) => row.notes.join(' · '), align: 'left' },
  { name: 'detail', label: '', field: 'key', align: 'right' },
];
watch(
  () => props.rows.map((row) => row.key).join('|'),
  () => {
    pagination.value.page = 1;
  },
);
</script>
<style scoped>
.resource-results {
  border-radius: 0 0 14px 14px;
  background: transparent;
}
.resource-results :deep(th) {
  background: #f8fafc;
  color: #66768b;
  font-size: 12px;
  height: 46px;
  border-color: #e8edf3;
}
.resource-results :deep(td) {
  padding: 18px 16px;
  border-color: #edf1f5;
}
.resource-results :deep(tbody tr:hover) {
  background: #fbfdff;
}
.identity-cell {
  min-width: 210px;
  max-width: 300px;
  white-space: normal;
}
.metric-cell {
  min-width: 88px;
}
.notes-cell {
  width: 26%;
  min-width: 190px;
  max-width: 300px;
  white-space: normal;
}
.result-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 600;
  border-radius: 5px;
  padding: 4px 7px;
}
.result-status i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.danger {
  color: #b42318;
  background: #fff0ed;
}
.warning {
  color: #9a6014;
  background: #fff8e8;
}
.normal {
  color: #27715b;
  background: #f0f8f4;
}
.muted {
  color: #637083;
  background: #f0f3f7;
}
.result-notes {
  color: #566477;
  font-size: 12px;
  line-height: 1.65;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.result-notes span {
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow-wrap: anywhere;
}
.result-notes small {
  color: #8994a4;
}
.notes-tooltip {
  white-space: pre-line;
  max-width: 420px;
  line-height: 1.6;
}
.result-no-match {
  width: 100%;
  padding: 36px 16px;
  text-align: center;
  color: #7b8798;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 10px;
}
.result-no-match strong {
  font-weight: 500;
}
.result-card {
  width: 100%;
  padding: 18px;
  border-bottom: 1px solid #e8edf3;
}
.result-card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.result-card-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 14px 0;
  margin-top: 14px;
  border-top: 1px solid #edf1f5;
  gap: 12px;
}
.result-card-metrics label {
  display: block;
  font-size: 11px;
  color: #7c8899;
  margin-bottom: 7px;
}
.result-card-notes {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f7f9fb;
}
.result-card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.resource-results :deep(.q-table__bottom) {
  padding: 12px 18px;
  color: #718096;
}
.resource-results :deep(.q-table__grid-content) {
  display: block;
}
</style>
