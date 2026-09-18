<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    :maximized="$q.screen.lt.sm"
    @update:model-value="close"
  >
    <q-card class="participants-dialog">
      <header class="participants-dialog-header">
        <div>
          <div class="participants-eyebrow">
            {{ formatInspectionMonth(report.month) }} · 점검 참여
          </div>
          <h2>{{ report.kind === 'PLAN' ? '참여 예정자와 담당 업무' : '참여자와 수행 업무' }}</h2>
          <p>
            {{
              report.kind === 'PLAN'
                ? '참여 예정자의 역할과 맡을 업무를 작성합니다.'
                : '참여자별 역할과 수행 업무를 작성합니다.'
            }}
          </p>
        </div>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="참여자 관리 닫기"
          :disable="saving"
          @click="close"
        />
      </header>
      <div class="participants-dialog-body">
        <div class="participant-picker">
          <q-select
            ref="userPicker"
            v-model="selectedUser"
            :options="userOptions"
            option-label="name"
            :option-disable="userSelected"
            use-input
            hide-selected
            fill-input
            input-debounce="250"
            outlined
            dense
            label="참여자 추가"
            placeholder="이름 · 소속 · 이메일 검색"
            :loading="searching"
            :disable="saving || entries.length >= 100"
            @filter="searchUsers"
            @update:model-value="addUser"
          >
            <template #prepend><q-icon name="person_add_alt" size="20px" /></template>
            <template #option="scope"
              ><q-item v-bind="scope.itemProps"
                ><q-item-section avatar
                  ><q-avatar size="32px" color="blue-grey-1" text-color="blue-grey-7">{{
                    scope.opt.name.slice(0, 1)
                  }}</q-avatar></q-item-section
                ><q-item-section
                  ><q-item-label>{{ scope.opt.name }}</q-item-label
                  ><q-item-label caption>{{
                    [scope.opt.team, scope.opt.email].filter(Boolean).join(' · ')
                  }}</q-item-label></q-item-section
                ><q-item-section v-if="userSelected(scope.opt)" side
                  ><span class="text-caption">추가됨</span></q-item-section
                ></q-item
              ></template
            >
            <template #no-option
              ><q-item
                ><q-item-section class="text-grey-7">{{
                  searchError || '선택할 수 있는 사용자가 없습니다.'
                }}</q-item-section></q-item
              ></template
            >
          </q-select>
          <div v-if="searchError" class="participant-search-error" role="alert">
            {{ searchError }}
            <q-btn
              flat
              dense
              label="다시 불러오기"
              color="primary"
              :disable="saving"
              @click="loadOptions"
            />
          </div>
          <p class="participant-picker-hint">
            참여자를 선택하면 이번 달 점검의 담당 작업이 표시됩니다. 역할은 여러 개 선택할 수
            있습니다.
          </p>
        </div>
        <div v-if="!entries.length" class="participants-empty">
          <q-icon name="groups" size="38px" /><strong>등록된 참여자가 없습니다.</strong>
          <p>위 검색창에서 점검 참여자를 선택해 주세요.</p>
        </div>
        <section v-for="(entry, index) in entries" :key="entry.userId" class="participant-editor">
          <div class="participant-editor-heading">
            <div class="participant-identity">
              <q-avatar size="34px">{{ entry.name.slice(0, 1) }}</q-avatar>
              <div>
                <b>{{ entry.name }}</b
                ><span>{{ entry.team || '소속 미등록' }}</span>
              </div>
            </div>
            <q-btn
              flat
              round
              dense
              icon="close"
              :aria-label="`${entry.name} 참여자 제외`"
              :disable="saving"
              @click="remove(index)"
            />
          </div>
          <q-select
            v-model="entry.roles"
            :options="roleOptions"
            option-value="value"
            option-label="label"
            emit-value
            map-options
            multiple
            use-chips
            outlined
            dense
            label="점검 역할"
            :disable="saving"
            :error="submitted && !entry.roles.length"
            error-message="역할을 한 개 이상 선택해 주세요."
            hide-bottom-space
          />
          <div v-if="assignedTasks(entry).length" class="participant-assigned-work">
            <div class="assigned-work-heading">
              <strong>담당 업무</strong><span>자동 연결</span>
            </div>
            <div
              v-for="task in assignedTasks(entry)"
              :key="task.issueId"
              class="assigned-work-item"
            >
              <span
                ><b>{{ task.key }}</b> · {{ task.title }}</span
              >
              <small v-if="report.kind !== 'PLAN'">{{ taskStatus(task.issueId) }}</small>
            </div>
          </div>
          <q-input
            v-model="entry.workSummary"
            outlined
            type="textarea"
            autogrow
            :label="report.kind === 'PLAN' ? '담당 업무' : '수행 업무'"
            maxlength="5000"
            :disable="saving"
            placeholder="예: 웹 서버 자원 점검 및 로그 정리, 재기동 후 서비스 정상 동작 확인"
          />
          <q-select
            v-model="entry.issueIds"
            :options="taskOptions(entry)"
            option-value="issueId"
            :option-label="taskLabel"
            emit-value
            map-options
            multiple
            use-chips
            outlined
            dense
            label="추가 참여 작업 (선택)"
            :disable="saving || !taskOptions(entry).length"
          >
            <template #selected-item="scope"
              ><q-chip
                removable
                dense
                :disable="saving"
                :title="taskLabel(scope.opt)"
                @remove="scope.removeAtIndex(scope.index)"
                >{{ scope.opt.key }}</q-chip
              ></template
            >
            <template #option="scope"
              ><q-item v-bind="scope.itemProps"
                ><q-item-section
                  ><q-item-label>{{ scope.opt.key }} · {{ scope.opt.title }}</q-item-label
                  ><q-item-label v-if="!currentTaskIds.has(scope.opt.issueId)" caption
                    >이전에 연결한 작업 · 현재 보고서의 작업 목록에는 없음</q-item-label
                  ></q-item-section
                ></q-item
              ></template
            >
          </q-select>
        </section>
        <q-banner
          v-if="saveError"
          class="bg-red-1 text-negative rounded-borders q-mt-md"
          role="alert"
          >{{ saveError }}</q-banner
        >
      </div>
      <footer class="participants-dialog-footer">
        <span>참여자 {{ entries.length }}명</span>
        <div>
          <q-btn flat label="취소" :disable="saving" @click="close" /><q-btn
            unelevated
            color="primary"
            label="참여자 저장"
            :loading="saving"
            @click="save"
          />
        </div>
      </footer>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { QSelect, useQuasar } from 'quasar';
import { useAuthStore } from 'stores/auth';
import {
  formatInspectionMonth,
  inspectionError,
  inspectionStatusLabel,
} from 'src/services/inspection';
import { assignedReportTasks } from 'src/utils/inspectionParticipants';
import {
  getReportParticipantOptions,
  saveReportParticipants,
  type InspectionReport,
  type ReportParticipantRole,
  type ReportParticipantTask,
  type ReportParticipantUser,
} from 'src/services/inspectionReports';
const props = defineProps<{ modelValue: boolean; report: InspectionReport }>();
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  saved: [report: InspectionReport];
}>();
const $q = useQuasar(),
  auth = useAuthStore();
interface Entry {
  userId: string;
  name: string;
  team: string;
  roles: string[];
  workSummary: string;
  issueIds: string[];
  previousTasks: ReportParticipantTask[];
}
const entries = ref<Entry[]>([]),
  userOptions = ref<ReportParticipantUser[]>([]),
  roles = ref<ReportParticipantRole[]>([]);
const userPicker = ref<QSelect | null>(null),
  selectedUser = ref<ReportParticipantUser | null>(null);
const searching = ref(false),
  saving = ref(false),
  searchError = ref(''),
  saveError = ref(''),
  submitted = ref(false),
  initial = ref(''),
  version = ref(0);
let request = 0;
const payload = computed(() =>
  entries.value.map((e) => ({
    user_id: e.userId,
    roles: e.roles,
    work_summary: e.workSummary,
    issue_ids: e.issueIds,
  })),
);
const dirty = computed(() => JSON.stringify(payload.value) !== initial.value);
const roleOptions = computed(() => [
  ...new Map(
    [...roles.value, ...(props.report.participants || []).flatMap((p) => p.roles)].map((r) => [
      r.value,
      r,
    ]),
  ).values(),
]);
const currentTaskIds = computed(() => new Set(props.report.snapshot.tasks.map((t) => t.issueId)));
const assignedByUser = computed(
  () =>
    new Map(
      entries.value.map((entry) => [entry.userId, assignedReportTasks(props.report, entry.userId)]),
    ),
);
const assignedTasks = (entry: Entry) => assignedByUser.value.get(entry.userId) || [];
function taskStatus(issueId: string) {
  const task = props.report.snapshot.tasks.find((task) => task.issueId === issueId);
  return task ? inspectionStatusLabel(task) : '';
}
watch(
  () => props.modelValue,
  (open) => {
    ++request;
    if (!open) return;
    entries.value = (props.report.participants || []).map((p) => ({
      userId: p.userId,
      name: p.name,
      team: p.team,
      roles: p.roles.map((r) => r.value),
      workSummary: p.workSummary,
      issueIds: p.tasks.map((t) => t.issueId),
      previousTasks: p.tasks,
    }));
    version.value = props.report.version;
    initial.value = JSON.stringify(payload.value);
    selectedUser.value = null;
    userOptions.value = [];
    roles.value = [];
    searchError.value = '';
    saveError.value = '';
    submitted.value = false;
    void loadOptions();
  },
  { immediate: true },
);
function userSelected(user: ReportParticipantUser) {
  return entries.value.some((e) => e.userId === user.id);
}
async function loadOptions() {
  const token = ++request;
  searching.value = true;
  searchError.value = '';
  try {
    const data = await getReportParticipantOptions();
    if (token !== request) return;
    userOptions.value = data.users;
    roles.value = data.roles;
  } catch (e) {
    if (token === request) searchError.value = inspectionError(e);
  } finally {
    if (token === request) searching.value = false;
  }
}
async function searchUsers(q: string, update: (callback: () => void) => void) {
  const token = ++request;
  searching.value = true;
  searchError.value = '';
  try {
    const data = await getReportParticipantOptions(q);
    if (token !== request) {
      return;
    }
    update(() => {
      userOptions.value = data.users;
      roles.value = data.roles;
    });
  } catch (e) {
    if (token === request) {
      searchError.value = inspectionError(e);
      update(() => {
        userOptions.value = [];
      });
    }
  } finally {
    if (token === request) searching.value = false;
  }
}
async function addUser(user: ReportParticipantUser | null) {
  if (!user) return;
  if (!userSelected(user) && entries.value.length < 100)
    entries.value.push({
      userId: user.id,
      name: user.name,
      team: user.team,
      roles: [],
      workSummary: '',
      issueIds: [],
      previousTasks: [],
    });
  await nextTick();
  selectedUser.value = null;
  userPicker.value?.updateInputValue('', true);
}
function taskOptions(entry: Entry): ReportParticipantTask[] {
  const assigned = new Set(assignedTasks(entry).map((task) => task.issueId));
  const current = props.report.snapshot.tasks
    .filter((task) => !assigned.has(task.issueId) || entry.issueIds.includes(task.issueId))
    .map((t) => ({
      issueId: t.issueId,
      month: t.month,
      key: t.issue.key,
      title: t.issue.title,
    }));
  return [...current, ...entry.previousTasks.filter((t) => !currentTaskIds.value.has(t.issueId))];
}
const taskLabel = (task: ReportParticipantTask) => `${task.key} · ${task.title}`;
function remove(index: number) {
  entries.value.splice(index, 1);
}
function confirmLeave(): boolean | Promise<boolean> {
  if (!props.modelValue || !auth.isLoggedIn) return true;
  if (saving.value) return false;
  if (!dirty.value) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: '저장하지 않고 닫으시겠습니까?',
      message: '저장하지 않은 참여자 정보가 있습니다.',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '닫기', color: 'negative' },
    })
      .onOk(() => {
        emit('update:modelValue', false);
        resolve(true);
      })
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}
async function close() {
  if (await confirmLeave()) emit('update:modelValue', false);
}
onBeforeRouteLeave(confirmLeave);
onBeforeRouteUpdate(confirmLeave);
function beforeUnload(event: BeforeUnloadEvent) {
  if (props.modelValue && dirty.value) event.preventDefault();
}
window.addEventListener('beforeunload', beforeUnload);
onBeforeUnmount(() => {
  ++request;
  window.removeEventListener('beforeunload', beforeUnload);
});
async function save() {
  submitted.value = true;
  saveError.value = '';
  if (entries.value.some((e) => !e.roles.length)) {
    saveError.value = '참여자별 점검 역할을 선택해 주세요.';
    return;
  }
  if (props.report.state !== 'DRAFT' || auth.me?.isInternal === false) return;
  saving.value = true;
  try {
    const doc = await saveReportParticipants(props.report.id, version.value, payload.value);
    initial.value = JSON.stringify(payload.value);
    emit('saved', doc);
    emit('update:modelValue', false);
  } catch (e) {
    saveError.value = inspectionError(e);
  } finally {
    saving.value = false;
  }
}
</script>
<style scoped>
.participants-dialog {
  width: 740px;
  max-width: calc(100vw - 40px);
  max-height: 90vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  color: #293b50;
}
.participants-dialog-header {
  padding: 26px 28px 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  border-bottom: 1px solid #e6ecf2;
}
.participants-eyebrow {
  color: #73859a;
  font-size: 12px;
}
h2 {
  margin: 8px 0;
  font-size: 22px;
  line-height: 1.4;
  font-weight: 700;
  letter-spacing: -0.6px;
}
.participants-dialog-header p {
  margin: 0;
  font-size: 13px;
  color: #6e8093;
  line-height: 1.8;
}
.participants-dialog-body {
  padding: 24px 28px;
  overflow: auto;
}
.participant-picker-hint {
  font-size: 12px;
  color: #7b8b9d;
  line-height: 1.8;
  margin: 10px 0 20px;
}
.participant-editor {
  padding: 20px;
  border: 1px solid #e2e9f0;
  border-radius: 10px;
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.participant-editor-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.participant-assigned-work {
  padding: 12px 14px;
  background: #f5f8fc;
  border-radius: 7px;
}
.assigned-work-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #536b82;
}
.assigned-work-heading span {
  font-size: 11px;
  color: #7b8b9d;
}
.assigned-work-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  font-size: 12px;
  line-height: 1.65;
  color: #435870;
  overflow-wrap: anywhere;
}
.assigned-work-item small {
  flex-shrink: 0;
  color: #7b8b9d;
}
.participant-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}
.participant-identity .q-avatar {
  color: #55778c;
  background: #eef3f7;
  font-size: 14px;
}
.participant-identity b {
  display: block;
  font-size: 14px;
  font-weight: 650;
}
.participant-identity span {
  display: block;
  font-size: 11px;
  color: #798b9e;
  margin-top: 3px;
}
.participants-empty {
  color: #90a0b0;
  text-align: center;
  padding: 30px 10px;
}
.participants-empty strong {
  display: block;
  color: #60778d;
  font-size: 15px;
  font-weight: 600;
  margin: 13px 0 8px;
}
.participants-empty p {
  font-size: 12px;
  line-height: 1.8;
  margin: 0;
}
.participant-search-error {
  font-size: 12px;
  color: #ad5858;
  margin-top: 10px;
}
.participants-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-top: 1px solid #e6ecf2;
  padding: 18px 28px;
}
.participants-dialog-footer > span {
  color: #7c8da0;
  font-size: 12px;
}
.participants-dialog-footer > div {
  display: flex;
  gap: 8px;
}
@media (max-width: 599px) {
  .participants-dialog {
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }
  .participants-dialog-header,
  .participants-dialog-body {
    padding: 20px;
  }
  .participants-dialog-footer {
    padding: 16px 20px;
  }
  .participant-editor {
    padding: 16px;
  }
  h2 {
    font-size: 20px;
  }
}
</style>
