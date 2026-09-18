<template>
  <q-dialog :model-value="modelValue" :persistent="saving" @update:model-value="emit('update:modelValue', $event)">
    <q-card class="hostname-dialog">
      <q-card-section class="hostname-heading">
        <div>
          <h2>자산 호스트명 일괄 변경</h2>
          <p>점검 데이터의 IP와 일치하는 서버 자산을 찾아 호스트명을 변경합니다.</p>
        </div>
        <q-btn flat round dense icon="close" aria-label="닫기" :disable="saving" v-close-popup />
      </q-card-section>
      <q-separator />
      <div class="hostname-body">
        <div v-if="loading" class="hostname-loading" role="status">
          <q-spinner size="30px" color="primary" /> 자산 IP를 비교하고 있습니다.
        </div>
        <q-banner v-if="error" rounded class="bg-red-1 text-negative q-ma-md" role="alert">
          {{ error }}
          <template #action><q-btn flat label="다시 불러오기" :disable="saving || loading" @click="load" /></template>
        </q-banner>
        <template v-if="data && !loading">
          <div class="hostname-context">
            <div class="hostname-source"><q-icon name="description" size="18px" /> {{ data.source.reportDate }} · {{ data.source.title }}</div>
            <p>여러 IP를 각각 비교합니다. 여러 서버에 공통으로 나타나는 IP는 매칭에서 제외합니다.</p>
          </div>
          <q-banner v-if="result" rounded class="hostname-result bg-green-1 text-green-9" role="status">
            <strong>{{ result.updatedIds.length }}대의 호스트명을 변경했습니다.</strong>
            <div v-if="result.skipped.length">적용 중 자산 정보가 바뀐 {{ result.skipped.length }}대는 제외했습니다. 다시 불러와 확인해 주세요.</div>
            <div>자산의 변경 이력에서 이전 호스트명과 변경한 관리자를 확인할 수 있습니다.</div>
          </q-banner>
          <template v-else>
            <q-tabs v-model="tab" dense no-caps align="left" active-color="primary" indicator-color="primary" class="hostname-tabs">
              <q-tab name="ready" :label="`변경 가능 ${counts.ready}`" />
              <q-tab name="review" :label="`확인 필요 ${counts.review}`" />
              <q-tab name="unchanged" :label="`이미 일치 ${counts.unchanged}`" />
            </q-tabs>
            <div class="hostname-toolbar">
              <q-checkbox v-if="tab === 'ready'" :model-value="allSelected" :disable="saving || stale || !shownRows.length" label="검색 결과 전체 선택" @update:model-value="toggleAll" />
              <span v-else class="hostname-hint">{{ tab === 'review' ? '이 항목들은 일괄 변경에서 제외됩니다.' : '호스트명이 같아 변경할 필요가 없습니다.' }}</span>
              <q-input v-model="search" outlined dense clearable placeholder="호스트명 / IP 검색" aria-label="호스트명 또는 IP 검색" :disable="saving">
                <template #prepend><q-icon name="search" size="19px" /></template>
              </q-input>
            </div>
            <q-table
              flat wrap-cells class="hostname-table" row-key="key"
              :rows="shownRows" :columns="columns" :grid="$q.screen.lt.sm"
              :rows-per-page-options="[25, 50, 100]" :pagination="{ rowsPerPage: 25 }"
              rows-per-page-label="페이지당 항목"
              :pagination-label="(first, last, total) => `${first}–${last} / ${total}건`"
              :no-data-label="search ? '검색 결과가 없습니다.' : '해당 항목이 없습니다.'"
            >
              <template #body-cell-select="scope"><q-td :props="scope">
                <q-checkbox :model-value="selected.includes(scope.row.assetId)" :disable="saving || stale" :aria-label="`${scope.row.hostname} 변경 선택`" @update:model-value="toggle(scope.row.assetId)" />
              </q-td></template>
              <template #body-cell-current="scope"><q-td :props="scope">
                <div class="hostname-current">{{ scope.row.currentHostname || '—' }}</div><div class="hostname-hint">{{ scope.row.assetName }}</div>
              </q-td></template>
              <template #body-cell-hostname="scope"><q-td :props="scope">
                <strong :class="{ 'text-primary': tab === 'ready' }">{{ scope.row.hostname || '호스트명 없음' }}</strong>
              </q-td></template>
              <template #body-cell-ip="scope"><q-td :props="scope">
                <div>{{ scope.row.matchedIps.join(', ') || scope.row.sourceIp || 'IP 없음' }}</div>
                <div v-if="scope.row.ignoredIps.length" class="hostname-hint">비교 제외: {{ scope.row.ignoredIps.join(', ') }}</div>
              </q-td></template>
              <template #item="scope">
                <div class="hostname-mobile-row col-12">
                  <div class="row items-center no-wrap">
                    <q-checkbox v-if="tab === 'ready'" :model-value="selected.includes(scope.row.assetId)" :disable="saving || stale" :aria-label="`${scope.row.hostname} 변경 선택`" @update:model-value="toggle(scope.row.assetId)" />
                    <strong>{{ scope.row.hostname || '호스트명 없음' }}</strong>
                  </div>
                  <dl>
                    <dt>현재 호스트명</dt><dd>{{ scope.row.currentHostname || '—' }}</dd>
                    <dt>일치한 IP</dt><dd>{{ scope.row.matchedIps.join(', ') || '—' }}</dd>
                    <dt>점검 IP</dt><dd>{{ scope.row.sourceIp || '—' }}</dd>
                  </dl>
                  <p v-if="scope.row.reason" class="hostname-hint">{{ scope.row.reason }}</p>
                  <p v-if="scope.row.ignoredIps.length" class="hostname-hint">비교 제외: {{ scope.row.ignoredIps.join(', ') }}</p>
                </div>
              </template>
            </q-table>
          </template>
        </template>
      </div>
      <q-separator />
      <q-card-actions class="hostname-footer">
        <span class="hostname-hint">{{ result ? '변경 내역은 자산에 반영되었습니다.' : `변경할 자산 ${selected.length}대 선택` }}</span>
        <q-space />
        <q-btn flat :label="result ? '닫기' : '취소'" :disable="saving" v-close-popup />
        <q-btn v-if="result?.skipped.length" outline color="primary" label="다시 불러오기" @click="load" />
        <q-btn v-else-if="!result" unelevated color="primary" :label="`선택한 ${selected.length}대 변경`" :loading="saving" :disable="loading || stale || !selected.length" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { QTableColumn } from 'quasar';
import { inspectionError } from 'src/services/inspection';
import { applyHostnames, previewHostnames, type HostnameApplyResult, type HostnameChange, type HostnamePreview } from 'src/services/inspectionResources';

const props = defineProps<{ modelValue: boolean; sourceId: string }>();
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>();
const data = ref<HostnamePreview | null>(null);
const result = ref<HostnameApplyResult | null>(null);
const loading = ref(false), saving = ref(false), stale = ref(false), error = ref('');
const selected = ref<string[]>([]), search = ref('');
const tab = ref<HostnameChange['status']>('ready');
let generation = 0;
const counts = computed(() => ({
  ready: data.value?.rows.filter(r => r.status === 'ready').length || 0,
  review: data.value?.rows.filter(r => r.status === 'review').length || 0,
  unchanged: data.value?.rows.filter(r => r.status === 'unchanged').length || 0,
}));
const shownRows = computed(() => {
  const term = (search.value || '').trim().toLowerCase();
  return (data.value?.rows || []).filter(r => r.status === tab.value &&
    `${r.hostname} ${r.currentHostname} ${r.assetName} ${r.sourceIp} ${r.assetIp}`.toLowerCase().includes(term));
});
const allSelected = computed(() => {
  const count = shownRows.value.filter(r => r.assetId && selected.value.includes(r.assetId)).length;
  return count === 0 ? false : count === shownRows.value.length ? true : null;
});
const columns = computed<QTableColumn[]>(() => [
  ...(tab.value === 'ready' ? [{ name: 'select', label: '', field: 'assetId', align: 'left' as const, style: 'width: 48px' }] : []),
  { name: 'current', label: '현재 자산 호스트명', field: 'currentHostname', align: 'left', style: 'width: 24%' },
  { name: 'hostname', label: tab.value === 'ready' ? '변경할 호스트명' : '점검 호스트명', field: 'hostname', align: 'left', style: 'width: 24%' },
  { name: 'ip', label: tab.value === 'review' ? '일치한 IP / 점검 IP' : '일치한 IP', field: 'matchedIps', align: 'left' },
  ...(tab.value === 'review' ? [{ name: 'reason', label: '제외 사유', field: 'reason', align: 'left' as const }] : []),
]);
function toggle(id: string) {
  if (saving.value || stale.value) return;
  selected.value = selected.value.includes(id) ? selected.value.filter(value => value !== id) : [...selected.value, id];
}
function toggleAll(value: boolean) {
  const ids = shownRows.value.flatMap(r => r.status === 'ready' && r.assetId ? [r.assetId] : []);
  selected.value = value ? [...new Set([...selected.value, ...ids])] : selected.value.filter(id => !ids.includes(id));
}
async function load() {
  const request = ++generation;
  loading.value = true;
  selected.value = [];
  data.value = null;
  result.value = null;
  error.value = '';
  stale.value = false;
  search.value = '';
  try {
    const response = await previewHostnames(props.sourceId);
    if (request !== generation) return;
    data.value = response;
    selected.value = response.rows.flatMap(r => r.status === 'ready' && r.assetId ? [r.assetId] : []);
    tab.value = selected.value.length ? 'ready' : counts.value.review ? 'review' : 'unchanged';
  } catch (e) {
    if (request === generation) error.value = inspectionError(e);
  } finally {
    if (request === generation) loading.value = false;
  }
}
async function save() {
  if (!data.value || !selected.value.length || saving.value || stale.value) return;
  saving.value = true;
  error.value = '';
  try {
    result.value = await applyHostnames(data.value.source.id, data.value.revision, selected.value);
    emit('saved');
  } catch (e) {
    error.value = inspectionError(e);
    // A failed bulk request may have applied some rows before losing connection.
    // Require a fresh preview before another write.
    stale.value = true;
    emit('saved');
  } finally {
    saving.value = false;
  }
}
watch(() => props.sourceId, () => { void load(); });
watch(tab, () => { search.value = ''; });
onMounted(() => { void load(); });
onBeforeUnmount(() => { generation++; });
</script>

<style scoped>
.hostname-dialog { width: 1040px; max-width: calc(100vw - 32px); max-height: calc(100dvh - 48px); display: flex; flex-direction: column; }
.hostname-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 22px 24px 18px; }
.hostname-heading h2 { margin: 0; color: #263d56; font-size: 19px; font-weight: 700; line-height: 1.5; }
.hostname-heading p, .hostname-context p { margin: 6px 0 0; color: #708095; font-size: 12px; line-height: 1.7; }
.hostname-body { overflow: auto; flex: 1; min-height: 0; }
.hostname-context { padding: 18px 24px; background: #f6f8fb; }
.hostname-source { display: flex; align-items: center; gap: 8px; color: #3e526c; font-size: 13px; font-weight: 600; }
.hostname-tabs { padding: 10px 16px 0; border-bottom: 1px solid #e3e9f1; }
.hostname-toolbar { padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.hostname-toolbar .q-input { width: 280px; }
.hostname-hint { color: #708095; font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; }
.hostname-current { color: #526479; }
.hostname-table :deep(th) { background: #f6f8fb; color: #63758b; }
.hostname-table :deep(td) { padding-top: 14px; padding-bottom: 14px; overflow-wrap: anywhere; }
.hostname-footer { padding: 16px 24px; flex-shrink: 0; }
.hostname-loading { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 48px 16px; color: #63758b; }
.hostname-result { margin: 24px; }
.hostname-mobile-row { padding: 14px 20px; border-bottom: 1px solid #e3e9f1; }
.hostname-mobile-row strong { overflow-wrap: anywhere; }
.hostname-mobile-row dl { display: grid; grid-template-columns: 90px 1fr; gap: 6px 12px; font-size: 12px; margin: 10px 0; }
.hostname-mobile-row dt { color: #708095; }
.hostname-mobile-row dd { margin: 0; overflow-wrap: anywhere; }
@media (max-width: 599px) {
  .hostname-heading { padding: 18px 16px; }
  .hostname-context { padding: 14px 16px; }
  .hostname-toolbar { flex-direction: column; align-items: stretch; padding: 12px 16px; gap: 8px; }
  .hostname-toolbar .q-input { width: 100%; }
  .hostname-footer { padding: 12px 16px; }
  .hostname-footer > .hostname-hint { width: 100%; margin-bottom: 8px; }
}
</style>
