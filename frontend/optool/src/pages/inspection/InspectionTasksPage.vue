<template>
  <q-page class="inspection-page">
    <div class="inspection-content">
      <header class="page-heading">
        <div>
          <div class="eyebrow">서버 점검</div>
          <h1>월간 작업</h1>
          <p>월별 점검 작업과 진행 상태를 확인합니다.</p>
        </div>
        <div class="heading-actions">
          <q-btn
            flat
            no-caps
            icon="description"
            label="점검 보고서"
            color="grey-7"
            :to="{ path: '/inspection/monthly-reports', query: { month } }"
            class="report-link"
          />
          <q-btn
            unelevated
            no-caps
            color="primary"
            icon="add"
            label="작업 추가"
            class="add-button"
            @click="openCreate('existing')"
          />
        </div>
      </header>

      <section v-if="assetId || issueId" class="context-banner" aria-label="적용 중인 조회 범위">
        <q-icon name="filter_alt" size="22px" />
        <div class="context-description">
          <strong>{{ issueId ? '선택한 작업의 점검 이력' : '선택한 서버의 점검 작업' }}</strong>
          <p>
            {{ issueId ? issueFilterLabel : assetFilterLabel }}에 등록된 점검 작업만 표시합니다.
          </p>
        </div>
        <q-btn outline no-caps color="primary" label="전체 작업 보기" @click="resetFilters" />
      </section>

      <section class="period-card" aria-label="점검 일정과 진행률">
        <div class="period-info">
          <div class="month-navigation">
            <q-btn
              flat
              round
              dense
              icon="chevron_left"
              aria-label="이전 달"
              :disable="month === '2000-01'"
              @click="moveMonth(-1)"
            />
            <InspectionMonthPicker v-model="month" class="page-month-picker" />
            <q-btn
              flat
              round
              dense
              icon="chevron_right"
              aria-label="다음 달"
              :disable="month === '2099-12'"
              @click="moveMonth(1)"
            />
            <q-btn
              v-if="month !== thisMonth()"
              flat
              dense
              no-caps
              label="이번 달"
              class="this-month"
              @click="month = thisMonth()"
            />
          </div>
          <div class="inspection-date">
            <q-icon name="event_available" size="17px" /><span
              >점검 예정일 <strong>{{ formattedDate }}</strong></span
            ><span v-if="dayLabel && !loading" class="day-label">{{ dayLabel }}</span>
          </div>
        </div>
        <div class="progress-summary">
          <div class="progress-caption">
            <span>{{ assetId || issueId ? '선택한 작업 진행률' : '전체 작업 진행률' }}</span
            ><span v-if="!loading"
              ><strong>{{ completedCount }}</strong> / {{ activeCount }} 완료</span
            ><q-skeleton v-else type="text" width="70px" />
          </div>
          <q-linear-progress
            :value="progress"
            instant-feedback
            rounded
            size="7px"
            color="teal-5"
            track-color="blue-grey-1"
            :indeterminate="loading"
          />
          <div class="progress-note">
            {{
              loading
                ? '작업을 불러오는 중입니다.'
                : pendingCount
                  ? `미완료 작업 ${pendingCount}건`
                  : activeCount
                    ? '등록된 작업을 모두 완료했습니다.'
                    : '등록된 작업이 없습니다.'
            }}
          </div>
        </div>
      </section>

      <q-banner v-if="error" rounded class="error-banner q-mt-md">
        <template #avatar><q-icon name="error_outline" /></template>{{ error }}
        <template #action><q-btn flat label="다시 불러오기" @click="load" /></template>
      </q-banner>

      <section class="work-panel" aria-label="월간 점검 작업 목록">
        <div class="panel-toolbar">
          <div class="view-tabs" role="tablist" aria-label="작업 상태 필터">
            <button
              v-for="tab in tabs"
              :key="tab.value"
              role="tab"
              :aria-selected="view === tab.value"
              :class="{ active: view === tab.value }"
              @click="
                view = tab.value;
                overdueOnly = false;
              "
            >
              {{ tab.label }}<span>{{ loading ? '–' : tab.count }}</span>
            </button>
          </div>
          <q-btn
            flat
            round
            dense
            icon="refresh"
            color="grey-6"
            aria-label="작업 새로고침"
            :loading="loading"
            @click="load"
          />
        </div>
        <div class="filter-bar">
          <q-input
            v-model="search"
            dense
            outlined
            clearable
            placeholder="작업명, 이슈 번호, 서버 검색"
            aria-label="작업 검색"
            class="task-search"
            hide-bottom-space
            ><template #prepend><q-icon name="search" size="19px" /></template
          ></q-input>
          <q-btn
            no-caps
            unelevated
            :icon="mine ? 'check' : 'person_outline'"
            label="내 작업"
            :aria-pressed="mine"
            class="mine-button"
            :class="{ selected: mine }"
            @click="mine = !mine"
          />
          <div v-if="assetId || issueId || overdueOnly" class="active-filters">
            <q-chip v-if="assetId" dense removable @remove="clearRouteFilter('asset_id')">{{
              assetFilterLabel
            }}</q-chip>
            <q-chip v-if="issueId" dense removable @remove="clearRouteFilter('issue_id')">{{
              issueFilterLabel
            }}</q-chip>
            <q-chip v-if="overdueOnly" dense removable @remove="overdueOnly = false"
              >이전 달 미완료</q-chip
            >
          </div>
        </div>

        <div v-if="loading" class="loading-list" aria-label="작업 불러오는 중" aria-busy="true">
          <div v-for="n in 4" :key="n" class="loading-row">
            <q-skeleton type="QAvatar" size="26px" />
            <div class="col">
              <q-skeleton type="text" width="65%" /><q-skeleton type="text" width="35%" />
            </div>
            <q-skeleton type="QChip" />
          </div>
        </div>
        <template v-else-if="!error && filtered.length">
          <div class="list-columns" aria-hidden="true">
            <span>작업</span><span>대상 서버</span><span>담당자</span><span>상태</span><span />
          </div>
          <section
            v-for="group in groups"
            :key="group.key"
            class="task-group"
            :aria-label="group.title"
          >
            <div
              v-if="group.key !== 'current' || groups.length > 1"
              class="group-heading"
              :class="{ 'group-heading--overdue': group.key === 'overdue' }"
            >
              <span
                ><q-icon :name="group.icon" size="16px" />{{ group.title
                }}<b>{{ group.total }}</b></span
              >
              <span v-if="group.key === 'overdue'" class="group-hint"
                >완료하거나 이월할 작업을 확인해 주세요.</span
              >
            </div>
            <ul class="task-list">
              <InspectionTaskRow
                v-for="task in group.items"
                :key="`${task.issueId}:${task.month}`"
                :task="task"
                :busy="busyIssues.includes(task.issueId)"
                :can-view-assets="canViewAssets"
                @open="openIssue(task)"
                @status="(status) => setStatus(task, status)"
                @targets="editTargets(task)"
                @work-plans-updated="load"
                @work-plans="
                  planTask = task;
                  planOpen = true;
                "
                @result="
                  resultTask = task;
                  resultOpen = true;
                "
                @rollover="askAction(task, 'rollover')"
                @exclude="askAction(task, 'exclude')"
              />
            </ul>
          </section>
          <footer class="list-footer">
            <span
              >{{ filtered.length }}개 작업<span v-if="pageCount > 1">
                중 {{ (page - 1) * pageSize + 1 }}–{{
                  Math.min(page * pageSize, filtered.length)
                }}</span
              ></span
            >
            <q-pagination
              v-if="pageCount > 1"
              v-model="page"
              :max="pageCount"
              :max-pages="5"
              direction-links
              boundary-numbers
              color="primary"
              size="sm"
            />
            <span v-else class="footer-hint"
              ><q-icon name="radio_button_unchecked" size="14px" /> 작업 앞의 원을 눌러 완료로
              표시하세요</span
            >
          </footer>
        </template>
        <div v-else-if="!error" class="empty-state">
          <div class="empty-icon">
            <q-icon
              :name="
                emptyKind === 'done'
                  ? 'task_alt'
                  : emptyKind === 'search'
                    ? 'search_off'
                    : 'playlist_add_check'
              "
              size="35px"
            />
          </div>
          <h2>
            {{
              isEmptyContext
                ? issueId
                  ? '이 작업의 점검 이력이 없습니다.'
                  : '이 서버에 등록된 점검 작업이 없습니다.'
                : emptyKind === 'done'
                  ? '미완료 작업이 없습니다.'
                  : emptyKind === 'search'
                    ? '검색 조건에 맞는 작업이 없습니다.'
                    : '등록된 점검 작업이 없습니다.'
            }}
          </h2>
          <p>
            {{
              isEmptyContext
                ? '다른 작업을 보려면 ‘전체 작업 보기’를 선택해 주세요.'
                : emptyKind === 'done'
                  ? '완료한 작업은 완료 탭에서 다시 확인할 수 있습니다.'
                  : emptyKind === 'search'
                    ? '검색어를 바꾸거나 필터를 초기화해 주세요.'
                    : '‘작업 추가’에서 이슈나 작업계획서를 가져와 주세요.'
            }}
          </p>
          <q-btn
            v-if="isEmptyContext"
            outline
            color="primary"
            label="전체 작업 보기"
            @click="resetFilters"
          />
          <q-btn
            v-else-if="emptyKind === 'search'"
            outline
            color="primary"
            label="필터 초기화"
            @click="resetFilters"
          />
          <q-btn
            v-else-if="emptyKind === 'done'"
            outline
            color="primary"
            label="완료한 작업 보기"
            @click="view = 'done'"
          />
          <q-btn
            v-else
            unelevated
            color="primary"
            icon="add"
            label="작업 추가"
            @click="openCreate('existing')"
          />
        </div>
      </section>
      <div
        v-if="!loading && overdueCount && view !== 'pending' && view !== 'all'"
        class="overdue-reminder"
      >
        <q-icon name="history" size="17px" /><span
          >이전 달 미완료 작업이 {{ overdueCount }}건 있습니다.</span
        ><q-btn
          flat
          dense
          no-caps
          label="확인하기"
          color="primary"
          @click="
            view = 'pending';
            overdueOnly = true;
          "
        />
      </div>
    </div>
    <InspectionResultDialog v-model="resultOpen" :task="resultTask" @saved="load" />
    <InspectionWorkPlanDialog v-model="planOpen" :task="planTask" @saved="load" />
    <WorkDocumentEntryDialog
      v-if="sourcePlan"
      v-model="sourcePlanOpen"
      :entry-id="sourcePlan.id"
      :title="sourcePlan.templateTitle"
      back-label="월간 작업으로 돌아가기"
      @saved="load"
    />
    <InspectionTaskDialog
      v-model="createOpen"
      :initial-month="month"
      :initial-mode="createMode"
      :task="editing"
      :asset-id="assetId"
      @saved="onTaskSaved"
    />
    <IssueDetailDialog
      v-if="selectedIssue"
      v-model="issueOpen"
      :issue="selectedIssue"
      :project-id="selectedIssue.projectId"
      @updated="load"
      @deleted="load"
    />
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter, type LocationQuery } from 'vue-router';
import { useQuasar } from 'quasar';
import InspectionWorkPlanDialog from 'src/components/inspection/InspectionWorkPlanDialog.vue';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';
import type { InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
import { useAuthStore } from 'stores/auth';
import {
  getInspectionTasks,
  changeInspection,
  changePlanInspection,
  inspectionError,
  thisMonth,
  type InspectionTask,
} from 'src/services/inspection';
import { getIssue, updateIssue, type Issue, type IssueStatus } from 'src/services/pm/issue';
import InspectionMonthPicker from 'src/components/inspection/InspectionMonthPicker.vue';
import InspectionTaskDialog from 'src/components/inspection/InspectionTaskDialog.vue';
import InspectionResultDialog from 'src/components/inspection/InspectionResultDialog.vue';
import InspectionTaskRow from 'src/components/inspection/InspectionTaskRow.vue';
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue';
const route = useRoute(),
  router = useRouter(),
  auth = useAuthStore(),
  $q = useQuasar();
const validMonth = (v: unknown): v is string =>
  typeof v === 'string' && /^20\d{2}-(0[1-9]|1[0-2])$/.test(v);
const month = ref(validMonth(route.query.month) ? route.query.month : thisMonth());
const assetId = computed(() =>
  typeof route.query.asset_id === 'string' ? route.query.asset_id : undefined,
);
const issueId = computed(() =>
  typeof route.query.issue_id === 'string' ? route.query.issue_id : undefined,
);
type View = 'pending' | 'done' | 'all' | 'history';
const view = ref<View>(assetId.value || issueId.value ? 'all' : 'pending');
const mine = ref(route.query.mine === '1'),
  overdueOnly = ref(false),
  search = ref('');
const items = ref<InspectionTask[]>([]),
  inspectionDate = ref(''),
  loading = ref(false),
  error = ref(''),
  busyIssues = ref<string[]>([]);
const createOpen = ref(false),
  createMode = ref<'existing' | 'new'>('existing'),
  editing = ref<InspectionTask | null>(null);
const resultTask = ref<InspectionTask | null>(null),
  resultOpen = ref(false);
const planTask = ref<InspectionTask | null>(null),
  planOpen = ref(false);
const selectedIssue = ref<Issue | null>(null),
  issueOpen = ref(false);
const sourcePlan = ref<InspectionWorkPlan | null>(null),
  sourcePlanOpen = ref(false);
const canViewAssets = computed(
  () => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('asset')),
);
const activeCount = computed(() => items.value.filter((t) => t.state === 'ACTIVE').length);
const completedCount = computed(
  () => items.value.filter((t) => t.state === 'ACTIVE' && t.issue.status === 'DONE').length,
);
const pendingCount = computed(() => activeCount.value - completedCount.value);
const overdueCount = computed(() => items.value.filter((t) => t.overdue).length);
const issueFilterLabel = computed(() => {
  const issue = items.value.find((t) => t.issueId === issueId.value)?.issue;
  return issue ? `${issue.key} · ${issue.title}` : '선택한 작업';
});
const isEmptyContext = computed(() => !!(issueId.value || assetId.value) && !items.value.length);
const progress = computed(() => (activeCount.value ? completedCount.value / activeCount.value : 0));
const formattedDate = computed(() =>
  inspectionDate.value && !loading.value
    ? new Date(`${inspectionDate.value}T00:00:00+09:00`).toLocaleDateString('ko-KR', {
        timeZone: 'Asia/Seoul',
        month: 'long',
        day: 'numeric',
        weekday: 'short',
      })
    : '—',
);
const dayLabel = computed(() => {
  if (!inspectionDate.value) return '';
  const today = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
  const days = Math.round((Date.parse(inspectionDate.value) - Date.parse(today)) / 86400000);
  return days === 0 ? '오늘 점검' : days > 0 ? `D-${days}` : '점검일 지남';
});
const assetFilterLabel = computed(
  () =>
    items.value.flatMap((t) => t.assets).find((a) => a.id === assetId.value)?.name || '선택한 자산',
);
const searched = computed(() =>
  items.value.filter((t) => {
    if (mine.value && t.issue.assigneeId !== String(auth.me?.id)) return false;
    const text = [
      t.issue.title,
      t.issue.key,
      t.issue.assigneeName,
      ...t.assets.flatMap((a) => [a.name, a.ip, a.assetName, a.current?.name, a.current?.ip]),
    ]
      .join(' ')
      .toLowerCase();
    return text.includes((search.value || '').trim().toLowerCase());
  }),
);
const tabs = computed(() => [
  {
    value: 'pending' as const,
    label: '미완료',
    count: searched.value.filter((t) => t.state === 'ACTIVE' && t.issue.status !== 'DONE').length,
  },
  {
    value: 'done' as const,
    label: '완료',
    count: searched.value.filter((t) => t.state === 'ACTIVE' && t.issue.status === 'DONE').length,
  },
  { value: 'all' as const, label: '전체', count: searched.value.length },
  {
    value: 'history' as const,
    label: '이월·제외',
    count: searched.value.filter((t) => t.state !== 'ACTIVE').length,
  },
]);
const groupFor = (t: InspectionTask) =>
  t.state !== 'ACTIVE' ? 'history' : t.overdue ? 'overdue' : 'current';
const filtered = computed(() =>
  searched.value
    .filter((t) => {
      if (overdueOnly.value && !t.overdue) return false;
      if (view.value === 'pending') return t.state === 'ACTIVE' && t.issue.status !== 'DONE';
      if (view.value === 'done') return t.state === 'ACTIVE' && t.issue.status === 'DONE';
      if (view.value === 'history') return t.state !== 'ACTIVE';
      return true;
    })
    .sort((a, b) => {
      const rank = { overdue: 0, current: 1, history: 2 };
      return (
        rank[groupFor(a)] - rank[groupFor(b)] ||
        Number(a.issue.status === 'DONE') - Number(b.issue.status === 'DONE') ||
        a.issue.title.localeCompare(b.issue.title, 'ko')
      );
    }),
);
const page = ref(1),
  pageSize = 20;
const pageCount = computed(() => Math.ceil(filtered.value.length / pageSize));
const groups = computed(() => {
  const visible = filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize);
  return [
    { key: 'overdue', title: '이전 달 미완료 작업', icon: 'history' },
    { key: 'current', title: `${Number(month.value.slice(5))}월 점검 작업`, icon: 'checklist' },
    { key: 'history', title: '이월·제외 기록', icon: 'inventory_2' },
  ]
    .map((g) => ({
      ...g,
      items: visible.filter((t) => groupFor(t) === g.key),
      total: filtered.value.filter((t) => groupFor(t) === g.key).length,
    }))
    .filter((g) => g.items.length);
});
const emptyKind = computed(() =>
  search.value ||
  mine.value ||
  assetId.value ||
  issueId.value ||
  overdueOnly.value ||
  (items.value.length && view.value !== 'pending')
    ? 'search'
    : items.value.length && view.value === 'pending' && completedCount.value > 0
      ? 'done'
      : 'new',
);
watch([view, mine, search, overdueOnly, month, assetId, issueId], () => {
  page.value = 1;
});
watch(pageCount, (max) => {
  page.value = Math.max(1, Math.min(page.value, max));
});
let request = 0;
async function load() {
  if (!validMonth(month.value)) return;
  const token = ++request;
  loading.value = true;
  error.value = '';
  try {
    const params: Record<string, string | boolean> = {};
    if (assetId.value) params.asset_id = assetId.value;
    if (issueId.value) params.issue_id = issueId.value;
    const result = await getInspectionTasks(month.value, params);
    if (token !== request) return;
    items.value = result.items;
    inspectionDate.value = result.inspectionDate;
  } catch (e) {
    if (token === request) {
      error.value = inspectionError(e);
      items.value = [];
    }
  } finally {
    if (token === request) loading.value = false;
  }
}
watch(
  [month, assetId, issueId],
  () => {
    void load();
  },
  { immediate: true },
);
watch(month, (value) => {
  if (validMonth(value)) void router.replace({ query: { ...route.query, month: value } });
});
watch(
  () => route.query.month,
  (value) => {
    if (validMonth(value)) month.value = value;
  },
);
watch(
  () => route.fullPath,
  () => {
    // 같은 페이지의 사이드바 메뉴를 다시 눌러도 이전 검색·월·내 작업 조건을 남기지 않는다.
    if (route.path === '/inspection/tasks' && !Object.keys(route.query).length) {
      search.value = '';
      mine.value = false;
      overdueOnly.value = false;
      view.value = 'pending';
      month.value = thisMonth();
    }
  },
);
watch([assetId, issueId], () => {
  if (assetId.value || issueId.value) {
    search.value = '';
    mine.value = route.query.mine === '1';
    overdueOnly.value = false;
    view.value = 'all';
  }
});
function moveMonth(delta: number) {
  const d = new Date(`${month.value}-01T12:00:00`);
  d.setMonth(d.getMonth() + delta);
  const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  if (validMonth(value)) month.value = value;
}
function clearRouteFilter(key: string) {
  const q = { ...route.query };
  delete q[key];
  void router.replace({ query: q });
}
function resetFilters() {
  search.value = '';
  mine.value = false;
  overdueOnly.value = false;
  view.value = 'all';
  const q: LocationQuery = { ...route.query, month: month.value };
  delete q.asset_id;
  delete q.issue_id;
  delete q.mine;
  void router.replace({ query: q });
}
function openCreate(mode: 'existing' | 'new') {
  editing.value = null;
  createMode.value = mode;
  createOpen.value = true;
}
function onTaskSaved(savedMonth: string) {
  if (!editing.value) {
    search.value = '';
    mine.value = false;
    overdueOnly.value = false;
    view.value = 'all';
    const query: LocationQuery = { ...route.query, month: savedMonth };
    delete query.asset_id;
    delete query.issue_id;
    delete query.mine;
    void router.replace({ query });
  }
  if (month.value !== savedMonth) month.value = savedMonth;
  else void load();
}
function editTargets(t: InspectionTask) {
  editing.value = t;
  createOpen.value = true;
}
async function openIssue(t: InspectionTask) {
  if (t.sourceType === 'WORK_PLAN') {
    if (!(auth.me?.isAdmin || auth.me?.permissions?.includes('job'))) {
      $q.notify({ type: 'info', message: '작업계획서를 열려면 작업 관리 권한이 필요합니다.' });
      return;
    }
    sourcePlan.value = t.workPlan || null;
    sourcePlanOpen.value = true;
    return;
  }
  try {
    selectedIssue.value = await getIssue(t.issue.projectId, t.issueId);
    issueOpen.value = true;
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  }
}
async function setStatus(t: InspectionTask, status: IssueStatus, undo = false) {
  if (busyIssues.value.includes(t.issueId) || t.issue.status === status) return;
  const previous = t.issue.status;
  const preservesHistory = t.month < thisMonth() && status === 'DONE';
  busyIssues.value.push(t.issueId);
  try {
    let taskVersion = t.taskVersion;
    if (t.sourceType === 'WORK_PLAN')
      taskVersion = (await changePlanInspection(t, { status })).version;
    else await updateIssue(t.issue.projectId, t.issueId, { status });
    await load();
    if (!undo)
      $q.notify({
        type: 'positive',
        message: preservesHistory
          ? '작업을 완료했습니다. 해당 월의 완료 기록도 저장했습니다.'
          : status === 'DONE'
            ? '작업을 완료했습니다.'
            : '작업 상태를 변경했습니다.',
        timeout: 5000,
        actions: preservesHistory
          ? []
          : [
              {
                label: '되돌리기',
                color: 'white',
                handler: () => {
                  void setStatus(
                    {
                      ...t,
                      ...(taskVersion !== undefined ? { taskVersion } : {}),
                      issue: { ...t.issue, status },
                    },
                    previous,
                    true,
                  );
                },
              },
            ],
      });
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  } finally {
    busyIssues.value = busyIssues.value.filter((id) => id !== t.issueId);
  }
}
function nextInspectionMonth(source: string) {
  const d = new Date(`${source}-01T12:00:00`);
  d.setMonth(d.getMonth() + 1);
  const next = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  return next > thisMonth() ? next : thisMonth();
}
function askAction(t: InspectionTask, action: 'rollover' | 'exclude') {
  const target = nextInspectionMonth(t.month);
  $q.dialog({
    title:
      action === 'rollover'
        ? `${target.slice(0, 4)}년 ${Number(target.slice(5))}월로 이월`
        : '점검 대상에서 제외',
    message:
      action === 'rollover'
        ? `‘${t.issue.title}’ 작업을 ${target.slice(0, 4)}년 ${Number(target.slice(5))}월로 이월합니다. 사유를 입력해 주세요.`
        : `‘${t.issue.title}’ 작업을 점검 목록에서 제외합니다.`,
    prompt: {
      model: '',
      type: 'textarea',
      label: '사유',
      isValid: (v) => !!v.trim() && v.length <= 1000,
    },
    ok: {
      label: action === 'rollover' ? '이월하기' : '제외하기',
      color: action === 'rollover' ? 'primary' : 'negative',
    },
    cancel: { label: '취소', flat: true },
    persistent: true,
  }).onOk((reason: string) => {
    void performAction(t, action, reason);
  });
}
async function performAction(t: InspectionTask, action: 'rollover' | 'exclude', reason: string) {
  if (busyIssues.value.includes(t.issueId)) return;
  busyIssues.value.push(t.issueId);
  try {
    await changeInspection(t, { action, reason });
    await load();
    $q.notify({
      type: 'positive',
      message: action === 'rollover' ? '작업을 이월했습니다.' : '점검 대상에서 제외했습니다.',
    });
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  } finally {
    busyIssues.value = busyIssues.value.filter((id) => id !== t.issueId);
  }
}
</script>
<style scoped>
.context-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  margin-bottom: 18px;
  border: 1px solid #bad3ed;
  border-radius: 10px;
  background: #f1f7fe;
  color: #365e86;
}
.context-description {
  flex: 1;
  min-width: 0;
}
.context-description strong {
  font-size: 13px;
}
.context-description p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.context-banner > .q-icon {
  flex-shrink: 0;
}
.context-banner > .q-btn {
  flex-shrink: 0;
  font-size: 12px;
}
@media (max-width: 700px) {
  .context-banner {
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 16px;
  }
  .context-banner > .q-btn {
    margin-left: 34px;
  }
}
.inspection-page {
  background: #f5f7fa;
  padding: 24px 32px 40px;
  color: #25364b;
}
.inspection-content {
  max-width: 1440px;
  margin: 0 auto;
}
.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}
.eyebrow {
  color: #79899b;
  font-size: 12px;
  margin-bottom: 7px;
}
h1 {
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.8px;
  line-height: 1.3;
  margin: 0;
}
.page-heading p {
  font-size: 13px;
  color: #76869a;
  margin: 9px 0 0;
}
.heading-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}
.add-button {
  border-radius: 8px;
  padding: 8px 17px;
  font-size: 13px;
}
.report-link {
  font-size: 12px;
}
.period-card {
  background: #fff;
  border: 1px solid #e6ebf1;
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  margin-bottom: 18px;
}
.month-navigation {
  display: flex;
  gap: 5px;
  align-items: center;
  margin-left: -9px;
}
.page-month-picker {
  width: 174px;
}
.page-month-picker :deep(.q-field__control:before),
.page-month-picker :deep(.q-field__control:after) {
  border: 0;
}
.page-month-picker :deep(.q-field__label) {
  display: none;
}
.page-month-picker :deep(.q-field__control-container) {
  padding-top: 0;
}
.page-month-picker :deep(.month-trigger) {
  font-size: 21px;
  font-weight: 650;
  letter-spacing: -0.6px;
}
.page-month-picker :deep(.month-trigger .q-icon) {
  display: none;
}
.this-month {
  font-size: 11px;
  color: #7c8b9d;
}
.inspection-date {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #79899b;
  font-size: 12px;
  margin: 9px 0 0 29px;
}
.inspection-date strong {
  color: #607186;
  font-weight: 500;
  margin-left: 5px;
}
.day-label {
  color: #5d7da1;
  background: #eff4fa;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  margin-left: 5px;
}
.progress-summary {
  width: 290px;
  flex-shrink: 0;
}
.progress-caption {
  display: flex;
  justify-content: space-between;
  color: #7e8b9a;
  font-size: 12px;
  margin-bottom: 11px;
}
.progress-caption strong {
  font-size: 18px;
  color: #2d735c;
  margin-right: 3px;
}
.progress-note {
  font-size: 11px;
  color: #95a0ad;
  margin-top: 9px;
}
.work-panel {
  background: #fff;
  border: 1px solid #e5eaf1;
  border-radius: 12px;
  overflow: hidden;
}
.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid #eaf0f5;
}
.view-tabs {
  display: flex;
  gap: 23px;
}
.view-tabs button {
  position: relative;
  border: 0;
  background: none;
  padding: 17px 0 15px;
  color: #6f7e92;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}
.view-tabs button span {
  border-radius: 5px;
  font-size: 11px;
  min-width: 20px;
  padding: 1px 5px;
  background: #f1f4f7;
  color: #8c99a9;
  text-align: center;
}
.view-tabs button.active {
  color: #2865a1;
  font-weight: 700;
}
.view-tabs button.active:after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #347bb9;
}
.view-tabs button.active span {
  background: #eaf2fc;
  color: #3472a7;
}
.view-tabs button:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: -3px;
}
.filter-bar {
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.task-search {
  width: 320px;
}
.task-search :deep(.q-field__control) {
  border-radius: 7px;
  font-size: 12px;
  background: #fbfcfd;
}
.task-search :deep(.q-field__control:before) {
  border-color: #e7ecf1;
}
.mine-button {
  background: #f3f5f8;
  color: #728095;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 7px;
}
.mine-button.selected {
  background: #eaf2fc;
  color: #2b6baf;
}
.active-filters {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  color: #6883a0;
  font-size: 12px;
}
.list-columns {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 170px 115px 105px 32px;
  gap: 16px;
  padding: 0 24px 12px;
  font-size: 11px;
  color: #9ba5b3;
}
.list-columns span:first-child {
  padding-left: 44px;
}
.group-heading {
  padding: 8px 24px;
  background: #f8fafc;
  border-top: 1px solid #edf1f5;
  border-bottom: 1px solid #edf1f5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #7d8da1;
  font-size: 11px;
}
.group-heading > span:first-child {
  display: flex;
  align-items: center;
  gap: 7px;
}
.group-heading b {
  font-weight: 600;
  margin-left: 2px;
}
.group-heading--overdue {
  background: #fffbf3;
  border-color: #f5eedf;
  color: #a48141;
}
.group-hint {
  font-size: 10px;
  color: #b49c72;
}
.task-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.list-footer {
  border-top: 1px solid #edf1f5;
  padding: 14px 24px;
  color: #99a4b1;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.footer-hint {
  display: flex;
  align-items: center;
  gap: 6px;
}
.empty-state {
  padding: 65px 24px 75px;
  text-align: center;
}
.empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: #f0f5fa;
  color: #8da7bf;
  border-radius: 24px;
  margin-bottom: 16px;
}
.empty-state h2 {
  margin: 0;
  font-size: 17px;
  line-height: 1.5;
  font-weight: 600;
  color: #4b6179;
}
.empty-state p {
  margin: 10px 0 24px;
  font-size: 12px;
  color: #93a0af;
  line-height: 1.8;
}
.loading-list {
  padding: 4px 24px 20px;
}
.loading-row {
  padding: 22px 0;
  display: flex;
  align-items: center;
  gap: 18px;
  border-top: 1px solid #f0f3f7;
}
.overdue-reminder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 15px;
  color: #9b8c72;
  font-size: 12px;
}
.overdue-reminder .q-btn {
  font-size: 12px;
}
.error-banner {
  background: #fff1ef;
  color: #b76154;
  margin-bottom: 16px;
}
@media (max-width: 1250px) {
  .inspection-page {
    padding: 26px 24px;
  }
  .list-columns {
    grid-template-columns: minmax(200px, 1fr) 140px 90px 100px 28px;
    gap: 10px;
    padding-left: 18px;
    padding-right: 18px;
  }
}
@media (max-width: 850px) {
  .list-columns {
    display: none;
  }
  .period-card {
    gap: 20px;
    padding: 18px;
  }
  .progress-summary {
    width: 210px;
  }
  .group-hint {
    display: none;
  }
  .view-tabs {
    gap: 18px;
  }
}
@media (max-width: 600px) {
  .inspection-page {
    padding: 20px 12px;
  }
  .page-heading {
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 20px;
  }
  h1 {
    font-size: 22px;
  }
  .page-heading p {
    font-size: 11px;
    max-width: 190px;
  }
  .report-link {
    display: none;
  }
  .heading-actions {
    padding-top: 22px;
  }
  .add-button {
    padding: 6px 10px;
    font-size: 12px;
  }
  .period-card {
    display: block;
    padding: 16px;
    margin-bottom: 16px;
  }
  .progress-summary {
    width: auto;
    margin: 12px 8px 2px;
    padding-top: 12px;
    border-top: 1px solid #eff2f6;
  }
  .progress-note {
    display: none;
  }
  .inspection-date {
    flex-wrap: wrap;
    gap: 5px;
  }
  .page-month-picker {
    width: 165px;
  }
  .page-month-picker :deep(.month-trigger) {
    font-size: 19px;
  }
  .panel-toolbar {
    padding: 0 14px;
  }
  .view-tabs {
    gap: 16px;
  }
  .view-tabs button {
    font-size: 12px;
    gap: 4px;
    padding-top: 17px;
  }
  .filter-bar {
    padding: 14px;
    gap: 8px;
  }
  .task-search {
    width: auto;
    flex: 1;
    min-width: 160px;
  }
  .mine-button {
    padding: 6px 9px;
  }
  .group-heading {
    padding: 10px 16px;
  }
  .list-footer {
    padding: 13px 16px;
  }
  .footer-hint {
    display: none;
  }
  .overdue-reminder {
    flex-wrap: wrap;
  }
}
</style>
