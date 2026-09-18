<template>
  <q-dialog
    :model-value="modelValue"
    :maximized="$q.screen.lt.sm"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="inspection-dialog">
      <q-form class="dialog-form" @submit="save">
        <header class="dialog-header">
          <div>
            <div class="dialog-eyebrow">월간 작업</div>
            <h2>
              {{ task ? (planMode ? '점검 작업 수정' : '대상 자산 변경') : '점검 작업 추가' }}
            </h2>
            <p>
              {{
                task
                  ? '점검 작업 정보를 확인해 주세요.'
                  : '스케줄 관리 이슈 또는 작업계획서에서 가져옵니다.'
              }}
            </p>
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            color="grey-6"
            aria-label="등록창 닫기"
            :disable="saving"
            @click="emit('update:modelValue', false)"
          />
        </header>
        <div class="dialog-body">
          <q-banner v-if="error" rounded class="form-error" role="alert"
            ><template #avatar><q-icon name="error_outline" /></template>{{ error }}</q-banner
          >
          <div class="dialog-grid">
            <section class="work-section" aria-label="작업 정보">
              <div class="section-label">
                <span>01</span>
                <h3>작업 정보</h3>
              </div>
              <InspectionMonthPicker
                v-model="month"
                :disable="!!task || saving || !!createdIssueId"
                class="form-month"
              />
              <div v-if="task || issueId" class="pinned-issue">
                <q-icon name="link" size="20px" />
                <div>
                  <span>{{ planMode ? '작업계획서' : '연결할 이슈' }}</span
                  ><strong>{{ task?.issue.title || issueTitle || issueId }}</strong>
                </div>
              </div>
              <template v-else>
                <div class="entry-modes" role="tablist" aria-label="작업 등록 방식">
                  <button
                    type="button"
                    role="tab"
                    aria-label="스케줄 관리에서 가져오기"
                    :aria-selected="mode !== 'plan'"
                    :class="{ selected: mode !== 'plan' }"
                    :disabled="saving || !!createdIssueId"
                    @click="mode = 'existing'"
                  >
                    <q-icon name="link" size="19px" /><span
                      >스케줄 관리<small>이슈 가져오기</small></span
                    ><q-icon v-if="mode !== 'plan'" name="check_circle" size="16px" />
                  </button>
                  <button
                    type="button"
                    role="tab"
                    :aria-selected="mode === 'plan'"
                    aria-label="작업계획서에서 가져오기"
                    :class="{ selected: mode === 'plan' }"
                    :disabled="saving || !!createdIssueId || !canLinkPlans"
                    @click="mode = 'plan'"
                  >
                    <q-icon name="description" size="19px" /><span
                      >작업계획서<small>{{
                        canLinkPlans ? '계획서 가져오기' : '작업 관리 권한 필요'
                      }}</small></span
                    ><q-icon v-if="mode === 'plan'" name="check_circle" size="16px" />
                  </button>
                </div>
                <InspectionWorkPlanSelect
                  v-if="mode === 'plan'"
                  v-model="selectedPlan"
                  :disable="saving"
                  :disabled-ids="[...linkedPlanIds]"
                />
                <q-select
                  v-if="mode !== 'plan'"
                  v-model="projectId"
                  :options="projects"
                  option-value="id"
                  option-label="name"
                  emit-value
                  map-options
                  label="프로젝트"
                  outlined
                  dense
                  hide-bottom-space
                  :disable="saving || loading || !!createdIssueId"
                  :loading="loading"
                  @update:model-value="loadProject"
                  :rules="[(v) => !!v || '프로젝트를 선택해 주세요.']"
                >
                  <template #no-option
                    ><q-item
                      ><q-item-section class="text-grey"
                        >참여 중인 프로젝트가 없습니다.</q-item-section
                      ></q-item
                    ></template
                  >
                </q-select>
                <q-btn
                  v-if="mode !== 'plan'"
                  flat
                  dense
                  no-caps
                  color="primary"
                  :label="mode === 'new' ? '기존 이슈에서 선택' : '새 이슈 만들기'"
                  :disable="saving || !!createdIssueId"
                  class="new-issue-option"
                  @click="mode = mode === 'new' ? 'existing' : 'new'"
                />
                <template v-if="mode === 'existing'">
                  <q-select
                    :key="projectId"
                    v-model="selectedIssue"
                    :options="issueOptions"
                    option-value="id"
                    :option-label="issueLabel"
                    :option-disable="(i) => linkedIds.has(i.id)"
                    use-input
                    hide-selected
                    fill-input
                    clearable
                    input-debounce="180"
                    label="연결할 이슈 검색"
                    outlined
                    dense
                    hint="이슈 번호 또는 제목으로 검색하세요"
                    :disable="saving || loading || projectLoading || !projectId"
                    :loading="projectLoading"
                    @filter="filterIssues"
                    :rules="[(v) => !!v?.id || '목록에서 이슈를 선택해 주세요.']"
                  >
                    <template #option="scope"
                      ><q-item v-bind="scope.itemProps" class="issue-option">
                        <q-item-section
                          ><q-item-label caption
                            >{{ scope.opt.projectKey || selectedProject?.key }}-{{ scope.opt.number
                            }}<span class="q-ml-sm">{{
                              STATUS_LABEL[scope.opt.status as IssueStatus]
                            }}</span></q-item-label
                          ><q-item-label>{{ scope.opt.title }}</q-item-label></q-item-section
                        >
                        <q-item-section v-if="linkedIds.has(scope.opt.id)" side class="text-caption"
                          >이미 추가됨</q-item-section
                        >
                      </q-item></template
                    >
                    <template #no-option
                      ><q-item
                        ><q-item-section class="text-grey"
                          >일치하는 이슈가 없습니다.</q-item-section
                        ></q-item
                      ></template
                    >
                  </q-select>
                  <div v-if="selectedIssue" class="selected-issue">
                    <q-icon name="check_circle" color="primary" size="18px" />
                    <div>
                      <strong>{{ selectedIssue.title }}</strong
                      ><span
                        >{{ selectedIssue.assigneeName || '담당자 미배정' }}<i>·</i
                        >{{ STATUS_LABEL[selectedIssue.status] }}</span
                      >
                    </div>
                  </div>
                  <div v-else class="field-help">
                    <q-icon name="info_outline" size="15px" />담당자와 상태는 이슈와 동일하게
                    표시됩니다.
                  </div>
                </template>
                <template v-else-if="mode === 'new'">
                  <q-input
                    v-model="title"
                    outlined
                    dense
                    hide-bottom-space
                    label="작업 제목"
                    placeholder="예: 로그 보관 기간 조정"
                    :disable="saving || !!createdIssueId"
                    maxlength="255"
                    :rules="[(v) => !!v?.trim() || '제목을 입력해 주세요.']"
                  />
                  <div class="schedule-fields">
                    <q-select
                      v-model="assigneeId"
                      :options="members"
                      option-value="userId"
                      :option-label="memberLabel"
                      emit-value
                      map-options
                      clearable
                      label="담당자"
                      outlined
                      dense
                      hide-bottom-space
                      :disable="saving || !!createdIssueId || projectLoading"
                    />
                    <q-input
                      v-model="workDate"
                      type="date"
                      outlined
                      dense
                      hide-bottom-space
                      label="작업 예정일"
                      :loading="dateLoading"
                      :disable="saving || !!createdIssueId || dateLoading"
                      :rules="[(v) => !!v || '예정일을 선택해 주세요.']"
                    />
                  </div>
                  <q-input
                    v-model="description"
                    outlined
                    type="textarea"
                    rows="3"
                    label="작업 내용 (선택)"
                    placeholder="작업 내용과 확인할 사항을 입력해 주세요."
                    :disable="saving || !!createdIssueId"
                  />
                  <div class="field-help">
                    <q-icon name="event_available" size="15px" />예정일이 스케줄 관리 이슈의
                    일정에도 반영됩니다.
                  </div>
                </template>
                <q-banner v-if="createdIssueId" rounded class="created-notice"
                  >이슈는 생성됐지만 점검 작업에 추가되지 않았습니다. ‘작업 추가’를 다시 눌러
                  주세요.</q-banner
                >
              </template>
              <div v-if="planMode" class="schedule-fields plan-schedule">
                <q-select
                  v-model="assigneeId"
                  :options="planAssignees"
                  option-value="id"
                  option-label="name"
                  emit-value
                  map-options
                  clearable
                  use-input
                  input-debounce="200"
                  label="점검 담당자"
                  outlined
                  dense
                  :disable="saving"
                  @filter="filterPlanAssignees"
                />
                <q-input
                  v-model="workDate"
                  type="date"
                  outlined
                  dense
                  label="작업 예정일"
                  :loading="dateLoading"
                  :disable="saving || dateLoading"
                  :rules="[(v) => !!v || '예정일을 선택해 주세요.']"
                />
              </div>
            </section>
            <section class="target-section" aria-label="자산 선택">
              <div class="section-label">
                <span>02</span>
                <h3>자산 선택</h3>
                <b v-if="!common">{{ selectedAssets.length }}개 선택</b>
              </div>
              <InspectionTargetPicker
                v-if="modelValue"
                v-model="selectedAssets"
                v-model:common="common"
                :disable="saving"
              />
            </section>
          </div>
        </div>
        <footer class="dialog-footer">
          <div class="save-summary">
            <q-icon :name="common ? 'layers' : 'inventory_2'" size="17px" /><span>{{
              common
                ? '공통 작업'
                : selectedAssets.length
                  ? `자산 ${selectedAssets.length}개`
                  : '대상 자산을 선택해 주세요'
            }}</span>
          </div>
          <div class="footer-buttons">
            <q-btn
              flat
              no-caps
              label="취소"
              color="grey-7"
              :disable="saving"
              @click="emit('update:modelValue', false)"
            /><q-btn
              unelevated
              no-caps
              type="submit"
              color="primary"
              :label="task ? (planMode ? '변경 사항 저장' : '대상 자산 저장') : '작업 추가'"
              :loading="saving"
              :disable="!canSave"
            />
          </div>
        </footer>
      </q-form>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import { useAuthStore } from 'stores/auth';
import InspectionWorkPlanSelect from './InspectionWorkPlanSelect.vue';
import type { InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
import {
  getReportParticipantOptions,
  type ReportParticipantUser,
} from 'src/services/inspectionReports';
import InspectionMonthPicker from './InspectionMonthPicker.vue';
import InspectionTargetPicker from './InspectionTargetPicker.vue';
import {
  listProjects,
  listProjectMembers,
  type Project,
  type ProjectMember,
} from 'src/services/pm/project';
import {
  listIssues,
  createIssue,
  STATUS_LABEL,
  type Issue,
  type IssueStatus,
} from 'src/services/pm/issue';
import {
  registerInspection,
  registerPlanInspection,
  changePlanInspection,
  getInspectionDate,
  getInspectionTasks,
  changeInspection,
  searchInspectionAssets,
  inspectionError,
  thisMonth,
  type InspectionAsset,
  type InspectionTask,
} from 'src/services/inspection';
const props = defineProps<{
  modelValue: boolean;
  initialMonth?: string | undefined;
  issueId?: string | undefined;
  issueTitle?: string | undefined;
  assetId?: string | undefined;
  task?: InspectionTask | null;
  initialMode?: 'existing' | 'new' | 'plan';
}>();
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'saved', month: string): void;
}>();
const $q = useQuasar();
const auth = useAuthStore();
const canLinkPlans = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('job'));
const selectedPlan = ref<InspectionWorkPlan | null>(null);
const month = ref(thisMonth()),
  mode = ref<'existing' | 'new' | 'plan'>('existing'),
  projectId = ref('');
const planMode = computed(
  () => props.task?.sourceType === 'WORK_PLAN' || (!props.task && mode.value === 'plan'),
);
const linkedPlanIds = ref(new Set<string>());
const planAssignees = ref<ReportParticipantUser[]>([]);
let assigneeRequest = 0;
async function filterPlanAssignees(search: string, update: (fn: () => void) => void) {
  const token = ++assigneeRequest;
  try {
    const data = await getReportParticipantOptions(search);
    if (token !== assigneeRequest) return;
    update(() => {
      const selected = planAssignees.value.find((u) => u.id === assigneeId.value);
      planAssignees.value =
        selected && !data.users.some((u) => u.id === selected.id)
          ? [selected, ...data.users]
          : data.users;
    });
  } catch (e) {
    if (token === assigneeRequest) {
      error.value = inspectionError(e);
      update(() => {});
    }
  }
}
const selectedIssue = ref<Issue | null>(null),
  workDate = ref(''),
  suggestedDate = ref(''),
  createdIssueId = ref(''),
  title = ref(''),
  description = ref(''),
  assigneeId = ref<string | null>(null);
const common = ref(false),
  selectedAssets = ref<InspectionAsset[]>([]);
const projects = ref<Project[]>([]),
  members = ref<ProjectMember[]>([]),
  issues = ref<Issue[]>([]),
  issueOptions = ref<Issue[]>([]),
  linkedIds = ref(new Set<string>());
const saving = ref(false),
  loading = ref(false),
  projectLoading = ref(false),
  dateLoading = ref(false),
  error = ref('');
const selectedProject = computed(() => projects.value.find((p) => p.id === projectId.value));
const issueLabel = (i: Issue | null) =>
  i ? `${i.projectKey || selectedProject.value?.key || ''}-${i.number} · ${i.title}` : '';
const memberLabel = (m: ProjectMember | null) => (m ? m.userName || m.userEmail : '');
const canSave = computed(() => {
  if (
    loading.value ||
    (!planMode.value && projectLoading.value) ||
    dateLoading.value ||
    saving.value ||
    (!common.value && !selectedAssets.value.length)
  )
    return false;
  if (planMode.value)
    return (
      !!workDate.value &&
      (!!props.task || (!!selectedPlan.value && !linkedPlanIds.value.has(selectedPlan.value.id)))
    );
  if (props.task || props.issueId || createdIssueId.value) return true;
  return (
    !!projectId.value &&
    (mode.value === 'existing'
      ? !!selectedIssue.value && !linkedIds.value.has(selectedIssue.value.id)
      : !!title.value.trim() && !!workDate.value)
  );
});
let generation = 0,
  projectRequest = 0,
  dateRequest = 0,
  linkedRequest = 0;
watch([month, mode, () => props.modelValue], async () => {
  const token = ++dateRequest;
  if (
    !props.modelValue ||
    (mode.value !== 'new' && mode.value !== 'plan') ||
    props.task ||
    props.issueId ||
    createdIssueId.value
  ) {
    dateLoading.value = false;
    return;
  }
  dateLoading.value = true;
  workDate.value = '';
  try {
    const value = await getInspectionDate(month.value);
    if (token === dateRequest) {
      suggestedDate.value = value;
      const planDate = selectedPlan.value?.workDate.slice(0, 10);
      workDate.value =
        mode.value === 'plan' &&
        planDate &&
        /^\d{4}-\d{2}-\d{2}$/.test(planDate) &&
        planDate.startsWith(month.value + '-')
          ? planDate
          : value;
    }
  } catch (e) {
    if (token === dateRequest) error.value = inspectionError(e);
  } finally {
    if (token === dateRequest) dateLoading.value = false;
  }
});
watch([month, () => props.modelValue], async () => {
  const token = ++linkedRequest;
  linkedIds.value = new Set();
  linkedPlanIds.value = new Set();
  if (!props.modelValue || props.task) return;
  try {
    const result = await getInspectionTasks(month.value, { include_overdue: false });
    if (token === linkedRequest) {
      linkedIds.value = new Set(
        result.items
          .filter((t) => t.month === month.value && t.state !== 'EXCLUDED')
          .map((t) => t.issueId),
      );
      linkedPlanIds.value = new Set(
        result.items
          .filter(
            (t) =>
              t.month === month.value &&
              t.state !== 'EXCLUDED' &&
              t.sourceType === 'WORK_PLAN' &&
              t.workPlan,
          )
          .map((t) => t.workPlan!.id),
      );
    }
  } catch {
    /* 저장 시 서버에서도 중복 연결을 검증한다. */
  }
});
watch(
  () => props.modelValue,
  async (open) => {
    const token = ++generation;
    ++projectRequest;
    ++assigneeRequest;
    if (!open) {
      projectLoading.value = false;
      return;
    }
    error.value = '';
    loading.value = true;
    month.value = props.task?.month || props.initialMonth || thisMonth();
    mode.value = props.initialMode || 'existing';
    selectedIssue.value = null;
    createdIssueId.value = '';
    title.value = '';
    description.value = '';
    assigneeId.value = null;
    workDate.value = props.task?.plannedOn || '';
    planAssignees.value = [];
    if (props.task?.sourceType === 'WORK_PLAN') {
      assigneeId.value = props.task.issue.assigneeId;
      if (assigneeId.value)
        planAssignees.value = [
          { id: assigneeId.value, name: props.task.issue.assigneeName, team: '', email: '' },
        ];
    }
    projectId.value = '';
    projects.value = [];
    issues.value = [];
    issueOptions.value = [];
    members.value = [];
    common.value = props.task?.common ?? false;
    selectedPlan.value = null;
    selectedAssets.value = props.task?.assets.map((a) => a.current || a) ?? [];
    try {
      if (!props.issueId && !props.task && mode.value !== 'plan') {
        const nextProjects = await listProjects();
        if (token !== generation) return;
        projects.value = nextProjects;
        const previous = localStorage.getItem('inspection-project');
        projectId.value =
          projects.value.find((p) => p.id === previous)?.id || projects.value[0]?.id || '';
        if (projectId.value && !planMode.value) await loadProject();
      }
      if (props.assetId && !props.task) {
        const assets = await searchInspectionAssets('', [props.assetId]);
        if (token !== generation) return;
        selectedAssets.value = assets;
        if (!assets.length) error.value = '해당 자산은 삭제되었거나 선택할 수 없습니다.';
      }
    } catch (e) {
      if (token === generation) error.value = inspectionError(e);
    } finally {
      if (token === generation) loading.value = false;
    }
  },
);
watch(
  () => selectedPlan.value?.id,
  (id) => {
    const plan = selectedPlan.value;
    if (!id || !plan || mode.value !== 'plan') return;
    const assets = plan.linkedAssets.filter((a) => !a.isDeleted).map((a) => ({ ...a, status: '' }));
    selectedAssets.value = assets;
    common.value = false;
    const planned = plan.workDate.slice(0, 10);
    workDate.value =
      /^\d{4}-\d{2}-\d{2}$/.test(planned) && planned.startsWith(month.value + '-')
        ? planned
        : suggestedDate.value;
  },
);
watch(mode, async (value, old) => {
  error.value = '';
  if (!props.task && !props.issueId && (value === 'plan' || old === 'plan'))
    assigneeId.value = null;
  if (value === 'plan' || old !== 'plan' || props.task || props.issueId || projects.value.length)
    return;
  loading.value = true;
  const token = generation;
  try {
    const nextProjects = await listProjects();
    if (token !== generation) return;
    projects.value = nextProjects;
    projectId.value = nextProjects[0]?.id || '';
    if (projectId.value) await loadProject();
  } catch (e) {
    if (token === generation) error.value = inspectionError(e);
  } finally {
    if (token === generation) loading.value = false;
  }
});
async function loadProject() {
  const token = ++projectRequest,
    id = projectId.value;
  selectedIssue.value = null;
  assigneeId.value = null;
  issues.value = [];
  issueOptions.value = [];
  members.value = [];
  if (!id) return;
  projectLoading.value = true;
  const [issueResult, memberResult] = await Promise.allSettled([
    listIssues(id),
    listProjectMembers(id),
  ]);
  if (token !== projectRequest) return;
  if (issueResult.status === 'fulfilled') {
    issues.value = issueResult.value;
    issueOptions.value = issueResult.value;
  } else error.value = inspectionError(issueResult.reason);
  if (memberResult.status === 'fulfilled') members.value = memberResult.value;
  else error.value = inspectionError(memberResult.reason);
  projectLoading.value = false;
}
function filterIssues(value: string, update: (fn: () => void) => void) {
  const query = value.trim().toLocaleLowerCase();
  update(() => {
    issueOptions.value = issues.value.filter((i) =>
      issueLabel(i).toLocaleLowerCase().includes(query),
    );
  });
}
async function save() {
  if (!canSave.value) return;
  saving.value = true;
  error.value = '';
  try {
    const assetIds = common.value ? [] : selectedAssets.value.map((a) => a.id);
    if (
      assetIds.length &&
      (await searchInspectionAssets('', assetIds)).length !== assetIds.length
    ) {
      error.value = '삭제된 자산을 선택에서 제거해 주세요.';
      return;
    }
    if (props.task && planMode.value)
      await changePlanInspection(props.task, {
        asset_ids: assetIds,
        common: common.value,
        assignee_id: assigneeId.value,
        planned_on: workDate.value,
      });
    else if (props.task)
      await changeInspection(props.task, {
        action: 'targets',
        asset_ids: assetIds,
        common: common.value,
      });
    else if (mode.value === 'plan') {
      const plan = selectedPlan.value;
      if (!plan) return;
      await registerPlanInspection({
        month: month.value,
        work_plan_id: plan.id,
        asset_ids: assetIds,
        common: common.value,
        assignee_id: assigneeId.value,
        planned_on: workDate.value,
      });
    } else {
      let id =
        props.issueId ||
        createdIssueId.value ||
        (mode.value === 'existing' ? selectedIssue.value?.id : '') ||
        '';
      if (!id && mode.value === 'new') {
        const issue = await createIssue(projectId.value, {
          title: title.value.trim(),
          description: description.value,
          type: 'TASK',
          status: 'TODO',
          assignee_id: assigneeId.value,
          start_date: `${workDate.value}T00:00:00+09:00`,
          due_date: `${workDate.value}T23:59:59+09:00`,
        });
        id = issue.id;
        createdIssueId.value = id;
      }
      await registerInspection({
        month: month.value,
        issue_id: id,
        asset_ids: assetIds,
        common: common.value,
      });
      if (projectId.value) localStorage.setItem('inspection-project', projectId.value);
    }
    $q.notify({
      type: 'positive',
      message: props.task ? '점검 작업을 수정했습니다.' : '점검 작업을 추가했습니다.',
    });
    emit('saved', month.value);
    emit('update:modelValue', false);
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    saving.value = false;
  }
}
</script>
<style scoped>
.plan-schedule {
  margin-top: 20px;
}
.new-issue-option {
  align-self: flex-end;
  font-size: 12px;
}
.inspection-dialog {
  width: 920px;
  max-width: 95vw;
  border-radius: 14px;
  color: #30445c;
  max-height: 92vh;
}
.dialog-form {
  display: flex;
  flex-direction: column;
  max-height: 92vh;
}
.dialog-header {
  padding: 26px 30px 23px;
  border-bottom: 1px solid #edf1f5;
  display: flex;
  justify-content: space-between;
  gap: 15px;
  flex-shrink: 0;
}
.dialog-eyebrow {
  font-size: 11px;
  color: #8e9bad;
  margin-bottom: 6px;
}
h2 {
  margin: 0;
  font-size: 21px;
  font-weight: 650;
  letter-spacing: -0.5px;
  line-height: 1.5;
}
.dialog-header p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #788a9f;
}
.dialog-body {
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 0;
}
.dialog-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
}
.work-section {
  padding: 26px 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.target-section {
  background: #f8fafc;
  padding: 26px 26px 28px;
  border-left: 1px solid #edf1f5;
}
.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}
.section-label > span {
  font-size: 10px;
  color: #a1aebd;
  letter-spacing: 0.7px;
}
h3 {
  font-size: 13px;
  font-weight: 650;
  margin: 0;
  line-height: 1.5;
}
.section-label b {
  margin-left: auto;
  font-size: 11px;
  color: #6f8caf;
  font-weight: 500;
}
.form-month {
  width: 185px;
}
.entry-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.entry-modes button {
  padding: 12px 9px;
  display: flex;
  align-items: center;
  gap: 7px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  color: #8a98a9;
  text-align: left;
  cursor: pointer;
  font: inherit;
}
.entry-modes button > span {
  flex: 1;
  font-size: 12px;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.entry-modes button small {
  display: block;
  margin-top: 4px;
  font-size: 10px;
  font-weight: 400;
  color: #9aa5b2;
}
.entry-modes button.selected {
  border-color: #8eb4db;
  background: #f4f8ff;
  color: #3a74ad;
}
.entry-modes button:disabled {
  cursor: default;
  opacity: 0.6;
}
.entry-modes button:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 2px;
}
.work-section :deep(.q-field__control),
.target-section :deep(.q-field__control) {
  border-radius: 7px;
  font-size: 13px;
}
.work-section :deep(.q-field__label),
.target-section :deep(.q-field__label) {
  font-size: 12px;
}
.work-section :deep(.q-field__control:before),
.target-section :deep(.q-field__control:before) {
  border-color: #dfe6ee;
}
.target-section :deep(.q-field__control) {
  background: #fff;
}
.schedule-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.pinned-issue,
.selected-issue {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  border: 1px solid #e3edf8;
  border-radius: 8px;
  background: #f6f9fe;
  padding: 14px;
}
.pinned-issue strong,
.selected-issue strong {
  display: block;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.6;
}
.pinned-issue span,
.selected-issue span {
  font-size: 11px;
  color: #8b9bb0;
  display: block;
  margin-top: 4px;
}
.selected-issue i {
  font-style: normal;
  margin: 0 7px;
}
.field-help {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: #76889c;
  font-size: 11px;
  line-height: 1.7;
}
.field-help .q-icon {
  margin-top: 2px;
  flex-shrink: 0;
}
.issue-option {
  max-width: 550px;
  min-height: 60px;
}
.issue-option :deep(.q-item__label) {
  line-height: 1.6 !important;
  overflow-wrap: anywhere;
}
.form-error {
  background: #fff1ef;
  color: #b76056;
  font-size: 12px;
  margin: 18px 28px 0;
}
.created-notice {
  background: #edf4fd;
  color: #6688b0;
  font-size: 11px;
}
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 17px 26px;
  border-top: 1px solid #e8edf3;
  flex-shrink: 0;
  gap: 10px;
}
.save-summary {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: #95a3b4;
}
.footer-buttons {
  display: flex;
  gap: 8px;
}
.footer-buttons .q-btn {
  border-radius: 7px;
  padding: 7px 18px;
  font-size: 12px;
}
@media (max-width: 700px) {
  .inspection-dialog {
    max-width: 100vw;
    width: 100vw;
    max-height: 100dvh;
    border-radius: 0;
  }
  .dialog-form {
    height: 100%;
    max-height: 100%;
  }
  .dialog-header {
    padding: 20px;
  }
  h2 {
    font-size: 19px;
  }
  .dialog-grid {
    grid-template-columns: 1fr;
  }
  .work-section {
    padding: 22px 20px;
    gap: 17px;
  }
  .target-section {
    padding: 22px 20px;
    border-left: 0;
    border-top: 1px solid #edf1f5;
  }
  .dialog-footer {
    padding: 14px 16px;
  }
  .save-summary {
    font-size: 10px;
  }
  .footer-buttons .q-btn {
    padding: 7px 12px;
  }
  .form-error {
    margin: 16px 20px 0;
  }
}
</style>
