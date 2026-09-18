<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    :maximized="$q.screen.lt.sm"
    @update:model-value="close"
  >
    <q-card class="source-dialog">
      <header class="source-header">
        <div>
          <div class="eyebrow">
            {{ formatInspectionMonth(month) }} ·
            {{ report ? '최신 내용 불러오기' : `${documentLabel} 작성` }}
          </div>
          <h2>{{ report ? '최신 내용 확인' : `점검 ${documentLabel} 작성` }}</h2>
          <p>
            {{
              isPlan
                ? '정기 점검 대상 서버와 예정된 월간 작업을 불러옵니다.'
                : '점검 데이터와 월간 작업 결과를 불러옵니다.'
            }}
          </p>
        </div>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="보고서 작성창 닫기"
          :disable="busy || saving"
          @click="close"
        />
      </header>
      <q-linear-progress v-if="busy" indeterminate color="primary" />
      <div v-if="loading" class="source-loading" role="status">
        <q-spinner color="primary" size="30px" />
        <p>선택한 월의 점검 내용을 불러오는 중입니다.</p>
      </div>
      <div v-else class="source-body">
        <section v-if="isPlan" class="source-config">
          <h3>자원 점검 계획</h3>
          <p class="field-help">자원 점검에 등록된 정기 점검 대상입니다.</p>
          <div v-if="preview" class="source-record">
            <strong>대상 서버 {{ preview.snapshot.resourceTargets?.length || 0 }}대</strong>
            <div
              v-for="asset in preview.snapshot.resourceTargets"
              :key="asset.id"
              class="plan-target"
            >
              <b>{{ asset.name }}</b
              ><span>{{ asset.ip || 'IP 미등록' }}</span>
            </div>
            <p v-if="!preview.snapshot.resourceTargets?.length">
              등록된 정기 점검 대상이 없습니다.
            </p>
          </div>
        </section>
        <section v-else class="source-config">
          <h3>자원 점검 데이터</h3>
          <template v-if="preview">
            <p class="field-help">선택한 월과 전월의 최신 점검 데이터를 비교합니다.</p>
            <div class="source-record">
              <span class="source-period">선택한 월 · {{ formatInspectionMonth(month) }}</span>
              <template v-if="preview?.snapshot.source">
                <strong>{{ preview.snapshot.source.title }}</strong>
                <span>점검일 {{ preview.snapshot.source.reportDate }}</span>
                <small>업로드 {{ reportTime(preview.snapshot.source.uploadedAt) }}</small>
              </template>
              <p v-else>
                자원 점검 데이터가 없습니다. 월간 작업만으로도 보고서를 작성할 수 있습니다.
              </p>
              <router-link
                v-if="preview && !preview.snapshot.source"
                :to="{ path: '/inspection/health-servers', query: { month, tab: 'data' } }"
                target="_blank"
                >Excel 업로드</router-link
              >
            </div>
            <div class="source-record">
              <span class="source-period">전월 · {{ formatInspectionMonth(previousMonth) }}</span>
              <template v-if="preview?.snapshot.comparison">
                <strong>{{ preview.snapshot.comparison.title }}</strong>
                <span>점검일 {{ preview.snapshot.comparison.reportDate }}</span>
                <small>업로드 {{ reportTime(preview.snapshot.comparison.uploadedAt) }}</small>
              </template>
              <p v-else>
                {{
                  preview?.snapshot.source
                    ? '전월 점검 데이터가 없습니다.'
                    : '선택한 월의 점검 데이터가 없어 비교할 수 없습니다.'
                }}
              </p>
            </div>
            <div v-if="preview.snapshot.plan" class="source-record">
              <span class="source-period">비교할 점검 계획서</span
              ><strong>{{ preview.snapshot.plan.title }}</strong
              ><span
                >{{ preview.snapshot.plan.revision }}차 확정본 ·
                {{ preview.snapshot.plan.tasks.length }}건</span
              >
            </div>
          </template>
          <p v-else class="field-help">점검 데이터를 불러오지 못했습니다. 다시 시도해 주세요.</p>
        </section>
        <section class="source-preview" aria-live="polite">
          <div class="preview-heading">
            <h3>보고서에 포함할 내용</h3>
            <span v-if="busy" class="ready-label" role="status">불러오는 중</span>
            <span v-else-if="preview && !stale" class="ready-label"
              ><q-icon name="check_circle" /> 불러옴</span
            >
          </div>
          <p class="field-help">
            {{
              isPlan
                ? '선택한 월에 진행할 작업을 포함합니다. 이월하거나 제외한 작업은 포함하지 않습니다.'
                : '선택한 월의 점검 작업 전체가 포함됩니다. 목록에서 설정한 검색·필터와 관계없이 불러옵니다.'
            }}
          </p>
          <template v-if="preview">
            <div class="preview-counts">
              <div>
                <strong>{{ preview.snapshot.stats.servers }}</strong
                ><span>자원 점검 서버</span>
              </div>
              <div>
                <strong>{{ preview.snapshot.stats.planned }}</strong
                ><span>월간 작업</span>
              </div>
              <div>
                <strong>{{ isPlan ? assignedCount : preview.snapshot.stats.done }}</strong
                ><span>{{ isPlan ? '작업 담당자' : '완료 작업' }}</span>
              </div>
            </div>
            <p v-if="report" class="field-help">
              기존 {{ report.snapshot.stats.servers }}대 · {{ report.snapshot.stats.planned }}건 →
              변경 후 {{ preview.snapshot.stats.servers }}대 ·
              {{ preview.snapshot.stats.planned }}건. 직접 작성한 내용은 유지됩니다.
            </p>
            <div v-if="preview.snapshot.warnings.length" class="review-notes">
              <h4>확인이 필요한 항목</h4>
              <div v-for="w in preview.snapshot.warnings" :key="w.code">
                <span>{{ w.label }}</span
                ><b>{{ w.count }}{{ w.code === 'no_source' ? '' : '건' }}</b>
              </div>
              <p>
                누락된 항목이 있어도 초안은 만들 수 있습니다. 보고서 확정 전에는 내용을 확인해
                주세요.
              </p>
            </div>
            <q-expansion-item
              v-if="exceptionServers.length"
              label="자산 연결 확인"
              icon="dns"
              class="mapping-box"
              :caption="`${exceptionServers.length}대`"
            >
              <div class="q-pa-md q-pt-sm">
                <div class="row items-center justify-between q-mb-sm">
                  <span class="field-help"
                    >자동으로 연결되지 않은 서버입니다. 자산을 직접 선택하면 이번 점검에만
                    연결됩니다.</span
                  ><q-btn
                    flat
                    dense
                    color="primary"
                    icon="refresh"
                    label="다시 확인"
                    :disable="busy || saving"
                    @click="buildPreview"
                  />
                </div>
                <div v-for="row in exceptionServers" :key="row.key" class="mapping-row">
                  <div class="mapping-host">
                    <b>{{ row.hostName }}</b
                    ><span>{{ row.ip || 'IP 없음' }}</span>
                  </div>
                  <ResourceExceptionMapping
                    :record="row"
                    :disable="busy || saving"
                    @select="(asset) => applyMapping(row.key, asset)"
                  />
                </div>
              </div>
            </q-expansion-item>
            <p v-if="preview.snapshot.historicalReconstruction" class="field-help q-mt-md">
              과거 월의 보고서입니다. 현재 등록된 데이터로 작성되므로 당시 내용과 다를 수 있습니다.
            </p>
          </template>
          <div v-else class="preview-empty">
            <q-icon name="description" size="38px" />
            <p>점검 데이터를 불러오면 보고서에 포함할 내용을 확인할 수 있습니다.</p>
          </div>
        </section>
      </div>
      <q-banner
        v-if="error"
        class="bg-red-1 text-negative q-mx-lg q-mb-md rounded-borders"
        role="alert"
        >{{ error }}
        <template #action>
          <q-btn
            flat
            label="다시 불러오기"
            :disable="busy || saving"
            @click="loadPreview"
          /> </template
      ></q-banner>
      <footer class="source-footer">
        <span>{{
          report ? '직접 작성한 내용은 유지됩니다.' : '보고서는 확정 전까지 수정할 수 있습니다.'
        }}</span>
        <div>
          <q-btn flat label="취소" :disable="busy || saving" @click="close" /><q-btn
            unelevated
            color="primary"
            :label="report ? '보고서에 반영' : '초안 만들기'"
            :disable="!preview || stale || busy || loading"
            :loading="saving"
            @click="apply"
          />
        </div>
      </footer>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { uid, useQuasar } from 'quasar';
import { formatInspectionMonth, inspectionError } from 'src/services/inspection';
import {
  createReport,
  previewReport,
  refreshReport,
  reportTime,
  type InspectionReport,
  type ReportPreview,
  type ReportKind,
  type ResourceMapping,
} from 'src/services/inspectionReports';
import ResourceExceptionMapping from './ResourceExceptionMapping.vue';
import {
  getSessionMappings,
  changedMappings,
  manualMappings,
  rememberMappings,
  forgetMappings,
} from 'src/services/inspectionResources';
import type { InspectionAsset } from 'src/services/inspection';
const props = defineProps<{
  modelValue: boolean;
  kind?: ReportKind;
  month: string;
  report?: InspectionReport | null;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  saved: [report: InspectionReport];
}>();
const $q = useQuasar();
const isPlan = computed(() => (props.report?.kind || props.kind) === 'PLAN');
const documentLabel = computed(() => (isPlan.value ? '계획서' : '결과서'));
const assignedCount = computed(
  () =>
    new Set((preview.value?.snapshot.tasks || []).map((t) => t.issue.assigneeId).filter(Boolean))
      .size,
);
const preview = ref<ReportPreview | null>(null),
  loading = ref(false),
  busy = ref(false),
  saving = ref(false),
  stale = ref(true),
  error = ref('');
let generation = 0,
  previewGeneration = 0,
  clientId = '';
const previousMonth = computed(() => {
  const [year, month] = props.month.split('-').map(Number);
  return month === 1 ? `${year! - 1}-12` : `${year}-${String(month! - 1).padStart(2, '0')}`;
});
const pendingMappings = ref<ResourceMapping[] | null>(null);
const exceptionServers = computed(
  () =>
    preview.value?.snapshot.servers.filter((s) => !s.asset || s.mappingState === 'manual') || [],
);
watch(
  () => props.modelValue,
  async (open) => {
    ++generation;
    ++previewGeneration;
    if (!open) return;
    // Internal HTTP deployments also need a stable request ID for creation retries.
    clientId = uid();
    await loadPreview();
  },
);
function refreshAfterAssetEdit() {
  if (
    props.modelValue &&
    document.visibilityState === 'visible' &&
    !busy.value &&
    !saving.value &&
    !loading.value
  )
    void buildPreview();
}
onMounted(() => {
  window.addEventListener('focus', refreshAfterAssetEdit);
});
onBeforeUnmount(() => {
  window.removeEventListener('focus', refreshAfterAssetEdit);
  ++generation;
  ++previewGeneration;
});
async function loadPreview() {
  const token = generation;
  loading.value = true;
  preview.value = null;
  pendingMappings.value = null;
  await buildPreview();
  if (token === generation) loading.value = false;
}
async function applyMapping(rowKey: string, asset: InspectionAsset | null) {
  if (!preview.value) return;
  pendingMappings.value = changedMappings(preview.value.snapshot.servers, rowKey, asset);
  await buildPreview();
}
async function buildPreview() {
  busy.value = true;
  stale.value = true;
  error.value = '';
  const token = generation;
  const request = ++previewGeneration;
  try {
    const body = {
      month: props.month,
      kind: props.report?.kind || props.kind || 'RESULT',
      // Keep displayed sources while rechecking live asset names.
      ...(preview.value
        ? {
            source_id: preview.value.snapshot.source?.id || null,
            comparison_id: preview.value.snapshot.comparison?.id || null,
          }
        : {}),
      include_images: true,
      ...(preview.value
        ? { mappings: pendingMappings.value ?? manualMappings(preview.value.snapshot.servers) }
        : {}),
      // New reports include all projects; refresh keeps the saved report's scope.
      ...(props.report
        ? {
            report_id: props.report.id,
            version: props.report.version,
            project_ids: props.report.projectIds,
          }
        : {}),
    };
    let data = await previewReport(body);
    if (token !== generation || request !== previewGeneration) return;
    const source = data.snapshot.source;
    const cached =
      !preview.value && !props.report && source
        ? getSessionMappings(props.month, source.id)
        : undefined;
    if (source && cached?.length) {
      try {
        data = await previewReport({
          ...body,
          source_id: source.id,
          comparison_id: data.snapshot.comparison?.id || null,
          mappings: cached.filter((m) => data.snapshot.servers.some((r) => r.key === m.row_key)),
        });
      } catch (e) {
        if ((e as { response?: { status: number } }).response?.status !== 422) throw e;
        forgetMappings(props.month, source.id);
      }
    }
    if (token !== generation || request !== previewGeneration) return;
    preview.value = data;
    pendingMappings.value = null;
    if (source) rememberMappings(props.month, source.id, data.snapshot.servers);
    stale.value = false;
  } catch (e) {
    if (token === generation && request === previewGeneration) {
      error.value = inspectionError(e);
      stale.value = true;
    }
  } finally {
    if (token === generation && request === previewGeneration) busy.value = false;
  }
}
function close() {
  if (!busy.value && !saving.value && !loading.value) emit('update:modelValue', false);
}
async function apply() {
  if (!preview.value || stale.value || busy.value || saving.value) return;
  saving.value = true;
  error.value = '';
  try {
    const doc = props.report
      ? await refreshReport(props.report, preview.value.id)
      : await createReport(preview.value.id, clientId);
    emit('saved', doc);
    emit('update:modelValue', false);
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    saving.value = false;
  }
}
</script>
<style scoped>
.plan-target {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 6px;
  padding-top: 10px;
  font-size: 12px;
}
.plan-target span {
  color: #8796a8;
}
.source-dialog {
  width: 1040px;
  max-width: calc(100vw - 48px);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  max-height: 92vh;
  color: #27364a;
}
.source-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 26px 28px 22px;
  border-bottom: 1px solid #e7ecf1;
}
.eyebrow {
  color: #667c90;
  font-size: 12px;
  font-weight: 600;
}
h2 {
  font-size: 23px;
  line-height: 1.45;
  margin: 7px 0;
  font-weight: 700;
  letter-spacing: -0.7px;
}
h3 {
  font-size: 14px;
  line-height: 1.5;
  margin: 0 0 14px;
  font-weight: 700;
}
h4 {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.4;
  font-weight: 700;
}
.source-header p {
  font-size: 13px;
  margin: 0;
  color: #748294;
}
.source-body {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  overflow: auto;
  min-height: 340px;
}
.source-config {
  padding: 26px;
  border-right: 1px solid #e7ecf1;
}
.source-loading {
  padding: 70px 28px;
  text-align: center;
  color: #667c90;
  font-size: 13px;
}
.source-record {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 16px 0;
  border-bottom: 1px solid #e7ecf1;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.source-record strong {
  line-height: 1.6;
}
.source-period {
  color: #536b82;
  font-size: 12px;
  font-weight: 600;
}
.source-record small {
  color: #758395;
  font-size: 11px;
}
.source-record p {
  margin: 0;
  color: #758395;
  line-height: 1.7;
}
.source-preview {
  padding: 26px;
  background: #f7f9fb;
  min-width: 0;
}
.field-help {
  color: #758395;
  font-size: 12px;
  line-height: 1.75;
  margin: 10px 0 18px;
}
.preview-heading {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.ready-label {
  color: #26816b;
  font-size: 12px;
}
.preview-counts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: white;
  border: 1px solid #e4eaf0;
  border-radius: 12px;
  padding: 22px 10px;
}
.preview-counts div {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  border-right: 1px solid #e9edf2;
}
.preview-counts div:last-child {
  border: none;
}
.preview-counts strong {
  font-size: 28px;
  line-height: 1.2;
  font-weight: 700;
}
.preview-counts span {
  font-size: 12px;
  color: #758395;
}
.review-notes {
  margin: 20px 0;
  padding: 18px;
  border: 1px solid #e9e0ca;
  border-radius: 10px;
  background: #fffcf5;
}
.review-notes > div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 9px;
  font-size: 12px;
  color: #786849;
}
.review-notes p {
  font-size: 12px;
  color: #8c7d64;
  margin: 14px 0 0;
  line-height: 1.7;
}
.preview-notice {
  padding: 12px;
  margin-top: 15px;
  background: #eaf2fc;
  color: #3e668c;
  border-radius: 8px;
  font-size: 12px;
}
.mapping-box {
  background: white;
  border: 1px solid #e4eaf0;
  border-radius: 10px;
  margin-top: 20px;
}
.mapping-row {
  padding: 14px 0;
  border-bottom: 1px solid #edf0f4;
}
.mapping-row:last-child {
  border: none;
}
.mapping-host {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.mapping-host span {
  color: #748294;
}
.preview-empty {
  text-align: center;
  padding: 70px 12px;
  color: #7a8a9c;
  font-size: 13px;
}
.source-footer {
  padding: 18px 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-top: 1px solid #e4eaf0;
}
.source-footer > span {
  font-size: 12px;
  color: #758395;
}
.source-footer > div {
  display: flex;
  gap: 8px;
}
@media (max-width: 700px) {
  .source-dialog {
    max-height: 100%;
    max-width: 100%;
    border-radius: 0;
  }
  .source-body {
    grid-template-columns: 1fr;
  }
  .source-config {
    border-right: 0;
    border-bottom: 1px solid #e7ecf1;
  }
  .source-footer > span {
    display: none;
  }
  .source-footer {
    justify-content: flex-end;
  }
  .source-header,
  .source-preview,
  .source-config {
    padding: 20px;
  }
  h2 {
    font-size: 20px;
  }
}
</style>
