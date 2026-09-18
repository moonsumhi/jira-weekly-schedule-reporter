<template>
  <div class="inspection-links">
    <q-btn
      flat
      dense
      no-caps
      class="inspection-link-trigger"
      :class="{ 'has-links': tasks.length }"
      :aria-label="triggerLabel"
      aria-haspopup="dialog"
      :aria-expanded="expanded"
    >
      <q-icon name="event_available" size="17px" />
      <span>서버 점검</span>
      <span class="inspection-link-count">
        <q-spinner v-if="loading && !hasLoaded" size="13px" />
        <q-icon
          v-else-if="error && !hasLoaded"
          name="error_outline"
          size="15px"
          class="text-warning"
        />
        <template v-else>{{ tasks.length > 99 ? '99+' : tasks.length }}</template>
      </span>
      <q-icon name="expand_more" size="16px" class="inspection-link-chevron" />
      <q-tooltip v-if="!expanded">{{ triggerLabel }}</q-tooltip>
      <q-menu
        v-model="expanded"
        :anchor="$q.screen.lt.sm ? 'bottom middle' : 'bottom right'"
        :self="$q.screen.lt.sm ? 'top middle' : 'top right'"
        :offset="[0, 8]"
        class="inspection-links-menu"
        role="dialog"
        aria-label="서버 점검 연결"
        @before-show="load()"
      >
        <section class="inspection-link-panel" :aria-busy="loading">
          <header class="inspection-link-header">
            <div>
              <h3>
                서버 점검
                <q-spinner
                  v-if="loading && hasLoaded"
                  size="13px"
                  class="q-ml-xs"
                  aria-label="최신 정보 확인 중"
                />
              </h3>
              <p>
                {{ issueId ? '이 이슈' : workPlanId ? '이 작업계획서' : workResultId ? '이 작업결과서' : '이 자산' }}에 연결된
                작업<span v-if="hasLoaded" class="inspection-link-total">
                  {{ tasks.length }}건</span
                >
              </p>
            </div>
            <q-btn
              flat
              round
              dense
              icon="close"
              size="sm"
              aria-label="점검 작업 목록 닫기"
              @click="expanded = false"
            />
          </header>

          <div v-if="error && hasLoaded" class="inspection-link-refresh-error" role="alert">
            <span>새로고침하지 못해 이전에 조회한 내용을 표시합니다.</span>
            <q-btn flat dense no-caps color="primary" label="다시 불러오기" @click="load()" />
          </div>
          <div v-if="loading && !hasLoaded" class="inspection-link-feedback" aria-live="polite">
            <q-spinner size="20px" color="primary" /><span>점검 작업을 불러오는 중입니다.</span>
          </div>
          <div v-else-if="error && !hasLoaded" class="inspection-link-feedback" role="alert">
            <q-icon name="error_outline" size="23px" color="grey-7" />
            <span>연결 정보를 불러오지 못했습니다.</span>
            <q-btn flat no-caps color="primary" label="다시 불러오기" @click="load()" />
          </div>
          <template v-else-if="tasks.length">
            <div class="inspection-link-summary">
              <span>{{ pendingCount ? `미완료 ${pendingCount}건` : '미완료 작업 없음' }}</span>
              <span v-if="tasks.length > previewTasks.length"
                >{{ previewTasks.length }}건 미리보기</span
              >
            </div>
            <div class="inspection-link-list">
              <button
                v-for="task in previewTasks"
                :key="`${task.issueId}:${task.month}`"
                type="button"
                class="inspection-link-row"
                @click="navigate(task)"
              >
                <div class="inspection-link-row-top">
                  <span>{{ formatMonth(task.month) }}</span>
                  <span class="inspection-link-status" :class="statusClass(task)">{{
                    statusLabel(task)
                  }}</span>
                </div>
                <div class="inspection-link-title">
                  {{ issueId ? targetLabel(task) : task.issue.title }}
                </div>
                <div v-if="!issueId" class="inspection-link-meta">
                  {{ task.issue.key }} · {{ task.issue.assigneeName || '미배정' }}
                </div>
                <div v-else-if="task.toMonth" class="inspection-link-meta">
                  {{ formatMonth(task.toMonth) }}로 이월
                </div>
                <q-icon name="chevron_right" size="18px" class="inspection-link-row-arrow" />
              </button>
            </div>
          </template>
          <div v-else class="inspection-link-feedback">
            <q-icon name="event_note" size="27px" color="grey-5" />
            <strong>연결된 점검 작업이 없습니다.</strong>
            <span>{{
              workResultId ? '월간 작업의 결과 작성에서 이 작업결과서를 연결할 수 있습니다.' : workPlanId
                ? '월간 작업에서 이 작업계획서를 연결할 수 있습니다.'
                : '‘작업 추가’에서 이슈를 점검 작업에 등록할 수 있습니다.'
            }}</span>
          </div>

          <footer class="inspection-link-footer">
            <q-btn
              flat
              dense
              no-caps
              color="grey-8"
              label="월간 작업 열기"
              icon-right="arrow_forward"
              @click="navigate()"
            />
            <q-btn
              v-if="allowAdd"
              unelevated
              dense
              no-caps
              color="primary"
              label="작업 추가"
              icon="add"
              @click="startAdd"
            />
          </footer>
        </section>
      </q-menu>
    </q-btn>
    <InspectionTaskDialog
      v-if="allowAdd"
      v-model="open"
      :issue-id="issueId"
      :issue-title="issueTitle"
      :asset-id="assetId"
      @saved="load(true)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter, type LocationQueryRaw } from 'vue-router';
import { getInspectionTasks, thisMonth, type InspectionTask } from 'src/services/inspection';
import { STATUS_LABEL } from 'src/services/pm/issue';
import InspectionTaskDialog from './InspectionTaskDialog.vue';

const props = withDefaults(
  defineProps<{
    issueId?: string;
    issueTitle?: string;
    assetId?: string;
    workPlanId?: string | undefined;
    workResultId?: string | undefined;
    allowAdd?: boolean;
  }>(),
  { allowAdd: true },
);
const emit = defineEmits<{ navigate: [] }>();
const router = useRouter();
const expanded = ref(false),
  open = ref(false);
const tasks = ref<InspectionTask[]>([]),
  loading = ref(false),
  error = ref(false),
  hasLoaded = ref(false);
const isPending = (task: InspectionTask) => task.state === 'ACTIVE' && task.issue.status !== 'DONE';
const pendingCount = computed(() => tasks.value.filter(isPending).length);
const previewTasks = computed(() =>
  [...tasks.value]
    .sort((a, b) => {
      if (isPending(a) !== isPending(b)) return isPending(a) ? -1 : 1;
      const byMonth = isPending(a)
        ? a.month.localeCompare(b.month)
        : b.month.localeCompare(a.month);
      return byMonth || a.issue.key.localeCompare(b.issue.key, 'ko', { numeric: true });
    })
    .slice(0, props.workPlanId || props.workResultId ? tasks.value.length : 4),
);
const triggerLabel = computed(() =>
  loading.value && !hasLoaded.value
    ? '서버 점검 연결 확인 중'
    : error.value && !hasLoaded.value
      ? '서버 점검 연결 확인 실패. 눌러서 다시 확인'
      : `서버 점검 연결 ${tasks.value.length}건${pendingCount.value ? `, 미완료 ${pendingCount.value}건` : ''}. 점검 작업 목록 열기`,
);
const formatMonth = (month: string) => `${month.slice(0, 4)}년 ${Number(month.slice(5))}월`;
function statusLabel(task: InspectionTask) {
  if (task.state === 'ROLLED') return '이월';
  if (task.state === 'EXCLUDED') return '제외';
  if (task.issueDeleted)
    return task.sourceType === 'WORK_PLAN' ? '작업계획서 삭제됨' : '이슈 삭제됨';
  return STATUS_LABEL[task.issue.status];
}
function statusClass(task: InspectionTask) {
  if (task.state !== 'ACTIVE' || task.issueDeleted) return 'is-archived';
  return task.issue.status === 'DONE' ? 'is-done' : 'is-pending';
}
function targetLabel(task: InspectionTask) {
  if (task.common) return '공통 작업';
  const first = task.assets[0];
  if (!first) return '대상 자산 없음';
  const name = first.current?.name || first.name;
  return `${name}${task.assets.length > 1 ? ` 외 ${task.assets.length - 1}개` : ''}`;
}
let request = 0;
let pendingLoad: Promise<void> | undefined;
function load(force = false): Promise<void> {
  // 최초 조회 중 팝업을 열어도 같은 요청을 함께 기다린다.
  // 작업 추가 직후에는 진행 중인 조회보다 최신 결과가 필요하다.
  if (pendingLoad && !force) return pendingLoad;
  const token = ++request;
  if (!props.issueId && !props.assetId && !props.workPlanId && !props.workResultId) return Promise.resolve();
  loading.value = true;
  error.value = false;
  pendingLoad = (async () => {
    try {
      const params: Record<string, string | boolean> = { all_months: true };
      if (props.issueId) params.issue_id = props.issueId;
      if (props.assetId) params.asset_id = props.assetId;
      if (props.workPlanId) params.work_plan_id = props.workPlanId;
      if (props.workResultId) params.work_result_id = props.workResultId;
      const result = await getInspectionTasks(thisMonth(), params);
      if (token === request) {
        tasks.value = result.items;
        hasLoaded.value = true;
      }
    } catch {
      if (token === request) error.value = true;
    } finally {
      if (token === request) {
        loading.value = false;
        pendingLoad = undefined;
      }
    }
  })();
  return pendingLoad;
}
async function startAdd() {
  expanded.value = false;
  await nextTick();
  open.value = true;
}
function navigate(task?: InspectionTask) {
  const query: LocationQueryRaw = {
    month: task?.month || previewTasks.value[0]?.month || thisMonth(),
  };
  if (task) query.issue_id = task.issueId;
  else if (props.issueId) query.issue_id = props.issueId;
  else if (props.assetId) query.asset_id = props.assetId;
  expanded.value = false;
  emit('navigate');
  void router.push({ path: '/inspection/tasks', query });
}
watch(
  () => [props.issueId, props.assetId, props.workPlanId, props.workResultId],
  () => {
    ++request;
    pendingLoad = undefined;
    expanded.value = false;
    open.value = false;
    tasks.value = [];
    hasLoaded.value = false;
    loading.value = false;
    error.value = false;
    void load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  ++request;
});
</script>

<style scoped>
.inspection-links {
  display: inline-flex;
  flex: 0 0 auto;
  max-width: 100%;
}
.inspection-link-trigger {
  color: #677586;
  border-radius: 6px;
  padding: 4px 7px;
  min-height: 30px;
  font-size: 12px;
}
.inspection-link-trigger :deep(.q-btn__content) {
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
}
.inspection-link-trigger.has-links {
  color: #365f87;
  background: #edf4fb;
}
.inspection-link-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 27px;
  width: 27px;
  height: 19px;
  padding: 0 4px;
  border-radius: 4px;
  background: #e5e9ee;
  color: #586b80;
  font-size: 11px;
  font-weight: 600;
  line-height: 19px;
  text-align: center;
}
.has-links .inspection-link-count {
  background: #dbe9f8;
  color: #365f87;
}
.inspection-link-chevron {
  color: #8592a1;
}
.inspection-link-panel {
  width: 376px;
  max-width: calc(100vw - 32px);
  color: #344457;
}
.inspection-link-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 18px 14px;
}
.inspection-link-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
}
.inspection-link-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #68788b;
}
.inspection-link-total {
  margin-left: 4px;
}
.inspection-link-header .q-btn {
  color: #8390a0;
}
.inspection-link-summary {
  display: flex;
  justify-content: space-between;
  padding: 0 18px 10px;
  font-size: 12px;
  color: #536b86;
}
.inspection-link-summary > span + span {
  color: #7b8897;
}
.inspection-link-list {
  max-height: min(330px, 46vh);
  overflow-y: auto;
  border-top: 1px solid #edf0f4;
}
.inspection-link-row {
  display: block;
  position: relative;
  width: 100%;
  text-align: left;
  background: #fff;
  border: 0;
  border-bottom: 1px solid #edf0f4;
  padding: 12px 38px 12px 18px;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.inspection-link-row:last-child {
  border-bottom: 0;
}
.inspection-link-row:hover {
  background: #f5f8fc;
}
.inspection-link-row:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: -2px;
}
.inspection-link-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #65758a;
  margin-bottom: 5px;
}
.inspection-link-status {
  font-size: 11px;
  border-radius: 4px;
  padding: 1px 6px;
  white-space: nowrap;
}
.is-pending {
  background: #edf3fa;
  color: #3d648e;
}
.is-done {
  background: #eaf5ef;
  color: #397458;
}
.is-archived {
  background: #f0f1f3;
  color: #707986;
}
.inspection-link-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.inspection-link-meta {
  font-size: 12px;
  color: #6d7c8d;
  margin-top: 4px;
}
.inspection-link-row-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ba6b4;
}
.inspection-link-feedback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 156px;
  padding: 22px 18px;
  text-align: center;
  font-size: 12px;
  color: #68788b;
}
.inspection-link-feedback strong {
  color: #46586d;
  font-size: 13px;
  font-weight: 500;
}
.inspection-link-refresh-error {
  padding: 0 18px 10px;
  color: #68788b;
  font-size: 12px;
}
.inspection-link-refresh-error .q-btn {
  font-size: 12px;
}
.inspection-link-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  border-top: 1px solid #e6ebf1;
  padding: 12px 14px;
}
.inspection-link-footer .q-btn {
  font-size: 12px;
  padding: 5px 9px;
  border-radius: 5px;
}
</style>
