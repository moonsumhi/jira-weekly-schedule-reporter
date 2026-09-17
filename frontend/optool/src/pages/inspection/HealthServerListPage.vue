<template>
  <q-page class="resource-page">
    <header class="resource-header">
      <div>
        <h1>자원 점검</h1>
        <p>CPU·메모리·디스크 사용량과 점검 결과를 확인합니다.</p>
      </div>
      <div class="resource-actions">
        <q-btn
          v-if="canWrite"
          flat
          no-caps
          color="grey-8"
          icon="tune"
          label="정기 점검 서버 설정"
          :disable="busy"
          @click="targetsOpen = true"
        />
        <q-btn
          v-if="canWrite"
          unelevated
          no-caps
          color="primary"
          icon="upload_file"
          label="Excel 업로드"
          :loading="uploading"
          :disable="deleting || mappingBusy"
          @click="fileInput?.click()"
        />
      </div>
    </header>
    <input ref="fileInput" type="file" accept=".xlsx" class="hidden" @change="uploadFile" />
    <q-tabs
      v-model="view"
      dense
      align="left"
      no-caps
      active-color="primary"
      indicator-color="primary"
      class="resource-views"
      aria-label="자원 점검 보기"
    >
      <q-tab name="data" label="점검 결과" />
      <q-tab name="compare" label="월별 비교" />
    </q-tabs>
    <div class="period-toolbar">
      <InspectionMonthPicker v-model="month" class="month-field" :disable="uploading || deleting" />
      <q-select
        v-if="data?.source"
        :model-value="data.source.id"
        :options="sourceOptions"
        emit-value
        map-options
        outlined
        dense
        label="점검 데이터"
        class="resource-source-select"
        :hint="`${data.source.uploadedBy || ''} · ${reportTime(data.source.uploadedAt)}`"
        :disable="busy"
        @update:model-value="selectSource"
      />
      <q-btn
        v-if="canWrite && data?.source"
        flat
        round
        dense
        icon="more_horiz"
        aria-label="점검 데이터 관리"
        :disable="busy"
        :loading="deleting"
      >
        <q-menu
          ><q-list
            ><q-item clickable v-close-popup @click="confirmDeleteSource"
              ><q-item-section avatar
                ><q-icon name="delete_outline" color="negative" /></q-item-section
              ><q-item-section class="text-negative">점검 데이터 삭제</q-item-section></q-item
            ></q-list
          ></q-menu
        >
      </q-btn>
      <q-btn
        flat
        round
        dense
        icon="refresh"
        aria-label="점검 결과 새로고침"
        :loading="refreshing"
        :disable="busy"
        @click="load(true)"
        ><q-tooltip>새로고침</q-tooltip></q-btn
      >
    </div>
    <q-banner
      v-if="error && !mappingOpen"
      rounded
      class="resource-error bg-red-1 text-negative"
      role="alert"
      >{{ error }}
      <template #action
        ><q-btn flat label="다시 불러오기" @click="load()" /><q-btn
          v-if="sourceId"
          flat
          label="최신 데이터 보기"
          @click="selectSource()"
      /></template>
    </q-banner>
    <div v-if="loading" class="resource-loading" role="status">
      <q-spinner color="primary" size="32px" /><span>점검 결과를 불러오고 있습니다.</span>
    </div>
    <template v-else-if="data">
      <section v-if="!data.source" class="resource-empty">
        <div class="empty-icon"><q-icon name="upload_file" size="28px" /></div>
        <div>
          <h2>선택한 월의 점검 데이터가 없습니다.</h2>
          <p>점검 Excel 파일을 업로드하면 서버별 사용량과 전월 대비 변화를 확인할 수 있습니다.</p>
        </div>
        <q-btn
          v-if="canWrite"
          outline
          no-caps
          color="primary"
          label="Excel 업로드"
          :loading="uploading"
          @click="fileInput?.click()"
        />
      </section>
      <ResourceMonthlyComparison
        v-if="data.source"
        v-show="view === 'compare'"
        :resource="data"
        :active="view === 'compare'"
      />
      <div v-show="view === 'data'">
        <div class="target-coverage">
          <q-icon name="event_repeat" size="17px" />
          <template v-if="data.items.length"
            ><span
              >정기 점검 서버 <strong>{{ data.items.length }}대</strong></span
            ><span class="coverage-divider">·</span
            ><span
              >점검 결과 있음 <strong>{{ coveredTargets }}대</strong></span
            ></template
          >
          <span v-else>정기 점검 서버를 등록하면 점검 결과가 없는 서버도 확인할 수 있습니다.</span>
          <span v-if="data.source" class="comparison-note">{{
            data.comparison ? `전월 ${data.comparison.reportDate} 대비` : '전월 점검 데이터 없음'
          }}</span>
        </div>
        <template v-if="rows.length || data.source">
          <div class="resource-stats" aria-label="확인할 항목 선택">
            <button
              v-for="stat in stats"
              :key="stat.key"
              type="button"
              :class="['stat-card', stat.tone, { active: filter === stat.key }]"
              :aria-pressed="filter === stat.key"
              @click="selectFilter(stat.key)"
            >
              <div class="stat-label">
                <span>{{ stat.label }}</span
                ><q-icon :name="stat.icon" size="18px" />
              </div>
              <div class="stat-value">
                {{ stat.count }}<small>{{ stat.unit }}</small>
              </div>
              <p>{{ stat.hint }}</p>
            </button>
          </div>
          <section class="results-panel">
            <div class="results-heading">
              <div>
                <h2>
                  서버별 점검 결과 <span>{{ filtered.length }}건</span>
                </h2>
              </div>
              <q-input
                v-model="search"
                outlined
                dense
                clearable
                placeholder="호스트명 / IP / 조치 내용 검색"
                class="resource-search"
                ><template #prepend><q-icon name="search" size="19px" /></template
              ></q-input>
            </div>
            <div v-if="filter !== 'all' || search" class="active-filters">
              <span v-if="filter !== 'all'">{{ activeFilterLabel }}</span
              ><span v-if="search">검색: {{ search }}</span
              ><q-btn
                flat
                dense
                no-caps
                color="primary"
                label="필터 초기화"
                @click="resetFilters"
              />
            </div>
            <ResourceResultsTable
              :key="`${data.month}:${data.source?.id}`"
              :rows="filtered"
              :can-view-asset="canViewAsset"
              :can-write="canWrite"
              :busy="busy"
              @detail="openDetail"
              @mapping="openMapping"
              @reset="resetFilters"
            />
          </section>
          <p v-if="data.source" class="threshold-note">
            사용량 80% 이상은 주의, 90% 이상은 위험으로 표시합니다. 전월과 같은 항목을 측정한
            경우에만 증감을 표시합니다.
          </p>
        </template>
      </div>
    </template>
    <ResourceTargetsDialog v-if="targetsOpen" v-model="targetsOpen" @saved="targetsSaved" />
    <HealthResourceDetailDialog
      v-model="detailOpen"
      :record="detailRecord"
      :source-id="detailSourceId"
    />
    <q-dialog v-model="mappingOpen" :persistent="mappingBusy">
      <q-card class="resource-mapping-dialog">
        <q-card-section class="mapping-heading"
          ><div>
            <h2>자산 연결</h2>
            <p v-if="mappingRecord">
              {{ mappingRecord.hostName }} · {{ mappingRecord.ip || 'IP 없음' }}
            </p>
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="자산 연결 닫기"
            :disable="mappingBusy"
            v-close-popup
        /></q-card-section>
        <q-card-section class="q-pt-none"
          ><p v-if="canWrite" class="mapping-help">
            점검한 서버를 자산 목록에서 찾아 선택해 주세요.<br />
            여기서 선택한 자산은 이번 점검 데이터에만 연결됩니다.
          </p>
          <p v-else class="mapping-help">이 서버와 연결된 자산을 확인할 수 있습니다.</p>
          <p
            v-if="canWrite && mappingRecord?.mappingIssue === 'hostname_mismatch'"
            class="mapping-help"
          >
            자산의 호스트명이 바뀌었다면 자산 정보를 먼저 수정해 주세요.
          </p>
          <q-banner v-if="error" rounded class="bg-red-1 text-negative q-mb-md" role="alert">{{
            error
          }}</q-banner>
          <ResourceExceptionMapping
            v-if="mappingRecord"
            :record="mappingRecord"
            :disable="busy"
            @select="(asset) => applyMapping(mappingRecord!.key, asset)"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'src/stores/auth';
import { thisMonth, inspectionError, type InspectionAsset } from 'src/services/inspection';
import {
  getResourceMonth,
  previewResourceMonth,
  changedMappings,
  rememberMappings,
  forgetMappings,
  type ResourceMonth,
} from 'src/services/inspectionResources';
import { reportTime, type ResourceServer } from 'src/services/inspectionReports';
import InspectionMonthPicker from 'src/components/inspection/InspectionMonthPicker.vue';
import ResourceTargetsDialog from 'src/components/inspection/ResourceTargetsDialog.vue';
import ResourceExceptionMapping from 'src/components/inspection/ResourceExceptionMapping.vue';
import ResourceResultsTable from 'src/components/inspection/ResourceResultsTable.vue';
import ResourceMonthlyComparison from 'src/components/inspection/ResourceMonthlyComparison.vue';
import {
  buildResourceResults,
  matchesResourceResult,
  type ResourceFilter,
} from 'src/utils/inspectionResources';
import HealthResourceDetailDialog from './HealthResourceDetailDialog.vue';
const route = useRoute(),
  router = useRouter(),
  auth = useAuthStore(),
  $q = useQuasar();
const canWrite = computed(() => auth.me?.isInternal !== false);
const canViewAsset = computed(
  () => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('asset')),
);
const month = computed({
  get: () =>
    typeof route.query.month === 'string' && /^20\d{2}-(0[1-9]|1[0-2])$/.test(route.query.month)
      ? route.query.month
      : thisMonth(),
  set: (value: string) => {
    void router.replace({ query: { ...route.query, month: value, source: undefined } });
  },
});
const view = computed({
  get: () => (route.query.tab === 'compare' ? 'compare' : 'data'),
  set: (value: string) => {
    void router.replace({
      query: { ...route.query, tab: value === 'compare' ? 'compare' : undefined },
    });
  },
});
const sourceId = computed(() =>
  typeof route.query.source === 'string' ? route.query.source : undefined,
);
const sourceOptions = computed(() =>
  (data.value?.sources || []).map((source, index) => ({
    value: source.id,
    label: `${source.reportDate} · ${source.title}${index === 0 ? ' (최신)' : ''}`,
  })),
);
const uploading = ref(false),
  deleting = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
let disposed = false;
const data = ref<ResourceMonth | null>(null),
  loading = ref(false),
  error = ref(''),
  search = ref('');
const mappingBusy = ref(false);
const refreshing = ref(false);
const busy = computed(
  () => refreshing.value || uploading.value || deleting.value || mappingBusy.value,
);
const filter = ref<ResourceFilter>('all');
const targetsOpen = ref(false),
  detailOpen = ref(false),
  mappingOpen = ref(false);
const detailRecord = ref<ResourceServer | null>(null),
  detailSourceId = ref('');
const mappingKey = ref('');
const mappingRecord = computed(() =>
  data.value?.records.find((record) => record.key === mappingKey.value),
);
const rows = computed(() => (data.value ? buildResourceResults(data.value) : []));
const filtered = computed(() =>
  rows.value.filter((row) => matchesResourceResult(row, filter.value, search.value || '')),
);
const coveredTargets = computed(
  () => data.value?.items.filter((item) => item.records.length).length || 0,
);
const stats = computed(() => [
  {
    key: 'measured' as const,
    label: '전체 측정 결과',
    count: rows.value.filter((row) => row.record).length,
    unit: '건',
    hint: '업로드한 데이터 기준',
    icon: 'dns',
    tone: 'measured',
  },
  {
    key: 'attention' as const,
    label: '확인 필요',
    count: rows.value.filter((row) => row.attention).length,
    unit: '건',
    hint: '사용량 · 오류 · 조치 항목',
    icon: 'error_outline',
    tone: 'attention',
  },
  {
    key: 'missing' as const,
    label: '결과 없는 서버',
    count: rows.value.filter((row) => !row.record).length,
    unit: '대',
    hint: '정기 점검 대상 중',
    icon: 'playlist_add_check',
    tone: 'missing',
  },
  {
    key: 'unlinked' as const,
    label: '자산 미연결',
    count: rows.value.filter((row) => row.record && !row.asset).length,
    unit: '건',
    hint: '등록 자산과 연결되지 않은 서버',
    icon: 'link_off',
    tone: 'unlinked',
  },
]);
const activeFilterLabel = computed(
  () => stats.value.find((stat) => stat.key === filter.value)?.label,
);
function resetFilters() {
  filter.value = 'all';
  search.value = '';
}
function selectFilter(value: ResourceFilter) {
  filter.value = filter.value === value ? 'all' : value;
  search.value = '';
}
function openMapping(record: ResourceServer) {
  if (busy.value) return;
  mappingKey.value = record.key;
  error.value = '';
  mappingOpen.value = true;
}
let generation = 0;
async function load(background = false) {
  const request = ++generation;
  mappingBusy.value = false;
  refreshing.value = true;
  if (!background) {
    resetFilters();
    loading.value = true;
    data.value = null;
  }
  error.value = '';
  try {
    const result = await getResourceMonth(month.value, sourceId.value);
    if (request === generation) {
      data.value = result;
      if (result.source) rememberMappings(result.month, result.source.id, result.records);
      const linked = result.records.find((record) => record.key === mappingKey.value);
      if (mappingOpen.value && linked?.asset && linked.mappingState === 'automatic')
        mappingOpen.value = false;
    }
  } catch (e) {
    if (request === generation) error.value = inspectionError(e);
  } finally {
    if (request === generation) {
      loading.value = false;
      refreshing.value = false;
    }
  }
}
function selectSource(id?: string) {
  void router.replace({ query: { ...route.query, source: id || undefined } });
}
async function uploadFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || uploading.value || !canWrite.value) return;
  if (!file.name.endsWith('.xlsx')) {
    $q.notify({ type: 'negative', message: '.xlsx 파일을 선택해 주세요.' });
    return;
  }
  uploading.value = true;
  const startingMonth = month.value;
  try {
    const form = new FormData();
    form.append('file', file);
    const { data: uploaded } = await api.post<{ id: string; reportDate: string }>(
      '/health-reports',
      form,
    );
    if (disposed) return;
    const uploadedMonth = uploaded.reportDate.slice(0, 7);
    forgetMappings(uploadedMonth, uploaded.id);
    $q.notify({ type: 'positive', message: `${uploaded.reportDate} 점검 자료를 업로드했습니다.` });
    if (month.value === startingMonth) {
      const sameSelection = month.value === uploadedMonth && sourceId.value === uploaded.id;
      await router.replace({
        query: { ...route.query, month: uploadedMonth, source: uploaded.id, tab: 'data' },
      });
      if (sameSelection) await load();
    }
  } catch (e) {
    if (!disposed) $q.notify({ type: 'negative', message: inspectionError(e) });
  } finally {
    uploading.value = false;
  }
}
function confirmDeleteSource() {
  const source = data.value?.source;
  if (!source || !canWrite.value) return;
  const selectedMonth = month.value;
  $q.dialog({
    title: '점검 데이터 삭제',
    message: `${source.reportDate} · ${source.title} 데이터를 삭제하시겠습니까?`,
    cancel: { label: '취소', flat: true },
    ok: { label: '삭제', color: 'negative', unelevated: true },
  }).onOk(() => {
    void (async () => {
      deleting.value = true;
      try {
        await api.delete(`/health-reports/${source.id}`);
        forgetMappings(selectedMonth, source.id);
        if (disposed) return;
        $q.notify({ type: 'positive', message: '점검 데이터를 삭제했습니다.' });
        if (month.value === selectedMonth) {
          if (sourceId.value === source.id) {
            await router.replace({ query: { ...route.query, source: undefined } });
          } else {
            await load();
          }
        }
      } catch (e) {
        if (!disposed) $q.notify({ type: 'negative', message: inspectionError(e) });
      } finally {
        deleting.value = false;
      }
    })();
  });
}
async function applyMapping(rowKey: string, asset: InspectionAsset | null) {
  if (!data.value?.source || uploading.value || deleting.value) return;
  const current = data.value;
  const sourceId = current.source!.id;
  const request = ++generation;
  mappingBusy.value = true;
  error.value = '';
  try {
    const result = await previewResourceMonth(
      current.month,
      sourceId,
      changedMappings(current.records, rowKey, asset),
    );
    if (request !== generation) return;
    data.value = result;
    rememberMappings(current.month, sourceId, result.records);
    mappingOpen.value = false;
  } catch (e) {
    if (request === generation) error.value = inspectionError(e);
  } finally {
    if (request === generation) mappingBusy.value = false;
  }
}
function targetsSaved() {
  $q.notify({ type: 'positive', message: '정기 점검 서버를 저장했습니다.' });
  void load(true);
}
function openDetail(record: ResourceServer) {
  detailRecord.value = record;
  detailSourceId.value = data.value?.source?.id || '';
  detailOpen.value = true;
}
watch(
  [month, sourceId],
  () => {
    resetFilters();
    mappingOpen.value = false;
    detailOpen.value = false;
    void load();
  },
  { immediate: true },
);
function refreshAfterAssetEdit() {
  if (
    document.visibilityState === 'visible' &&
    !loading.value &&
    !refreshing.value &&
    !mappingBusy.value &&
    !uploading.value &&
    !deleting.value &&
    !targetsOpen.value &&
    !detailOpen.value
  )
    void load(true);
}
onMounted(() => {
  window.addEventListener('focus', refreshAfterAssetEdit);
});
onBeforeUnmount(() => {
  disposed = true;
  window.removeEventListener('focus', refreshAfterAssetEdit);
  generation++;
});
</script>
<style scoped>
.resource-page {
  max-width: 1480px;
  margin: auto;
  padding: 26px 32px;
  color: #26344a;
}
.resource-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 22px;
  flex-wrap: wrap;
}
h1 {
  font-size: 28px;
  line-height: 1.3;
  font-weight: 750;
  letter-spacing: -0.7px;
  margin: 0 0 8px;
}
h2 {
  font-size: 16px;
  line-height: 1.5;
  font-weight: 650;
  margin: 0;
}
p {
  color: #748195;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}
.resource-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.resource-actions :deep(.q-btn) {
  min-height: 38px;
  border-radius: 7px;
}
.resource-views {
  margin-bottom: 18px;
  border-bottom: 1px solid #e5ebf2;
}
.period-toolbar {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5ebf2;
}
.period-toolbar > .q-btn {
  margin-top: 4px;
}
.month-field {
  width: 182px;
}
.resource-error {
  margin-bottom: 20px;
}
.resource-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 300px;
  color: #8190a3;
}
.resource-source-select {
  flex: 1;
  min-width: 0;
}
.target-coverage {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  font-size: 12px;
  color: #7b8798;
  margin: 12px 2px 18px;
}
.target-coverage strong {
  font-weight: 600;
  color: #53657d;
}
.comparison-note {
  margin-left: auto;
  font-size: 11px;
}
.coverage-divider {
  color: #c4cedb;
}
.resource-empty {
  display: flex;
  align-items: center;
  gap: 18px;
  border: 1px dashed #cad8e7;
  border-radius: 12px;
  background: #f8fbff;
  padding: 26px;
}
.resource-empty h2 {
  margin-bottom: 6px;
}
.resource-empty .q-btn {
  margin-left: auto;
  white-space: nowrap;
}
.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 12px;
  color: var(--q-primary);
  background: #eaf2fd;
}
.resource-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}
.stat-card {
  font: inherit;
  text-align: left;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  padding: 14px 17px;
  cursor: pointer;
  color: #516178;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.stat-card:hover {
  border-color: #b0c5df;
  background: #fafcff;
}
.stat-card.active {
  border-color: var(--q-primary);
  background: #f2f7ff;
  box-shadow: inset 0 0 0 1px var(--q-primary);
}
.stat-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
}
.stat-label .q-icon {
  color: #a6b4c6;
}
.stat-value {
  font-size: 27px;
  line-height: 1.25;
  font-weight: 700;
  color: #24364d;
  margin-top: 8px;
}
.stat-value small {
  font-size: 12px;
  font-weight: 400;
  margin-left: 5px;
  color: #8a97a8;
}
.stat-card p {
  font-size: 11px;
  margin-top: 5px;
}
.stat-card.attention .stat-value {
  color: #b35b37;
}
.stat-card.unlinked .stat-value {
  color: #977239;
}
.results-panel {
  background: white;
  border: 1px solid #e1e8f0;
  border-radius: 14px;
  overflow: hidden;
}
.results-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 18px 20px;
}
.results-heading h2 span {
  color: #8591a1;
  font-size: 13px;
  font-weight: 400;
  margin-left: 6px;
}
.results-heading p {
  font-size: 12px;
  margin-top: 4px;
}
.resource-search {
  width: 300px;
}
.active-filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 22px 14px;
  font-size: 12px;
}
.active-filters > span {
  background: #eef4fd;
  color: #4973a6;
  padding: 4px 9px;
  border-radius: 5px;
}
.threshold-note {
  margin-top: 8px;
  padding-left: 2px;
  font-size: 11px;
  color: #8c97a7;
}
.resource-mapping-dialog {
  width: 540px;
  max-width: calc(100vw - 32px);
  border-radius: 12px;
}
.mapping-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.mapping-heading p {
  margin-top: 4px;
  overflow-wrap: anywhere;
}
.mapping-help {
  margin-bottom: 16px;
}
@media (max-width: 1100px) {
  .resource-page {
    padding: 24px;
  }
  .stat-card {
    padding: 16px;
  }
}
@media (max-width: 599px) {
  .resource-page {
    padding: 20px 16px;
  }
  .resource-header {
    gap: 18px;
    margin-bottom: 24px;
  }
  h1 {
    font-size: 26px;
  }
  .resource-actions {
    width: 100%;
    justify-content: space-between;
  }
  .period-toolbar {
    gap: 10px;
    flex-wrap: wrap;
    padding-bottom: 8px;
  }
  .month-field {
    width: calc(100% - 88px);
  }
  .resource-source-select {
    order: 4;
    flex-basis: 100%;
  }
  .resource-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 20px;
  }
  .stat-card {
    padding: 12px 14px;
  }
  .stat-label {
    font-size: 12px;
  }
  .stat-value {
    margin-top: 6px;
    font-size: 25px;
  }
  .stat-card p {
    display: none;
  }
  .results-heading {
    padding: 18px;
    gap: 14px;
  }
  .resource-search {
    width: 100%;
  }
  .active-filters {
    padding: 0 18px 12px;
  }
  .resource-empty {
    padding: 20px;
    flex-wrap: wrap;
  }
  .resource-empty > div:nth-child(2) {
    flex: 1;
    min-width: 180px;
  }
  .resource-empty .q-btn {
    margin-left: 0;
  }
  .resource-empty h2 {
    font-size: 15px;
  }
  .target-coverage {
    font-size: 11px;
    margin-bottom: 16px;
  }
  .comparison-note {
    margin-left: 0;
  }
}
</style>
