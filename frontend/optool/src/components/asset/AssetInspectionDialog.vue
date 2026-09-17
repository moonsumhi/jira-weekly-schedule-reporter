<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <q-card class="asset-inspection-dialog">
      <q-card-section class="row items-center q-pb-sm">
        <div class="text-subtitle1 text-weight-medium">서버 점검</div>
        <q-space /><q-btn
          flat
          round
          dense
          icon="close"
          aria-label="점검 이력 닫기"
          @click="emit('update:modelValue', false)"
        />
      </q-card-section>
      <q-card-section class="inspection-history-body q-pt-sm">
        <div v-if="loading" class="text-center q-pa-lg">
          <q-spinner color="primary" size="28px" />
        </div>
        <div v-if="error" class="text-negative text-caption q-mb-md" role="alert">
          {{ error }} <q-btn flat dense label="다시 불러오기" @click="load" />
        </div>
        <template v-if="task">
          <div class="row items-center q-gutter-sm q-mb-sm">
            <span class="text-caption text-grey-7"
              >{{ formatInspectionMonth(task.month) }} 점검</span
            >
            <q-badge color="grey-2" text-color="grey-8">{{ inspectionStatusLabel(task) }}</q-badge>
          </div>
          <h2>{{ task.issue.title }}</h2>
          <div class="text-caption text-grey-7 q-mt-sm">
            {{ task.issue.key }} · 담당 {{ task.issue.assigneeName || '미배정' }}
          </div>
          <dl class="inspection-history-fields">
            <dt>대상 서버</dt>
            <dd v-for="asset in task.assets" :key="asset.id">
              {{ asset.current?.name || asset.name
              }}<span v-if="asset.current?.ip || asset.ip">
                · {{ asset.current?.ip || asset.ip }}</span
              ><span v-if="asset.isDeleted"> (삭제됨)</span>
            </dd>
            <template v-if="task.fromMonth"
              ><dt>이월 전</dt>
              <dd>{{ formatInspectionMonth(task.fromMonth) }}</dd></template
            >
            <template v-if="task.toMonth"
              ><dt>이월 대상</dt>
              <dd>{{ formatInspectionMonth(task.toMonth) }}</dd></template
            >
            <template v-if="task.reason"
              ><dt>{{ task.state === 'EXCLUDED' ? '제외 사유' : '이월 사유' }}</dt>
              <dd class="inspection-history-reason">{{ task.reason }}</dd></template
            >
          </dl>
          <p v-if="task.issueDeleted" class="inspection-history-notice">
            {{ task.sourceType === 'WORK_PLAN' ? '작업계획서가' : '연결된 이슈가' }} 삭제되어 저장된
            점검 기록을 표시합니다.
          </p>
          <p v-else-if="historical" class="inspection-history-notice">
            점검 당시의 기록입니다. 원본에서는 현재 내용을 확인할 수 있습니다.
          </p>
          <div v-if="issueError" class="text-negative text-caption q-mt-md" role="alert">
            {{ issueError }}
          </div>
          <q-btn
            v-if="!task.issueDeleted"
            outline
            no-caps
            color="primary"
            class="q-mt-md"
            :label="task.sourceType === 'WORK_PLAN' ? '작업계획서 보기' : '연결된 이슈 보기'"
            :loading="issueLoading"
            @click="openIssue"
          />
        </template>
      </q-card-section>
      <q-card-actions class="q-pa-md">
        <q-btn
          v-if="task"
          flat
          no-caps
          color="grey-8"
          label="월간 작업에서 관리"
          @click="navigate"
        />
        <q-space /><q-btn
          flat
          color="primary"
          label="닫기"
          @click="emit('update:modelValue', false)"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
  <IssueDetailDialog
    v-if="issue"
    v-model="issueOpen"
    :project-id="issue.projectId"
    :issue="issue"
  />
  <WorkDocumentEntryDialog
    v-if="sourcePlan"
    v-model="sourcePlanOpen"
    :entry-id="sourcePlan.id"
    :title="sourcePlan.templateTitle"
    back-label="점검 이력으로 돌아가기"
    @saved="
      load();
      emit('changed');
    "
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  formatInspectionMonth,
  getInspectionTasks,
  inspectionStatusLabel,
  thisMonth,
  type InspectionTask,
} from 'src/services/inspection';
import { getIssue, type Issue } from 'src/services/pm/issue';
import { getErrorMessage } from 'src/utils/http/error';
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';
import type { InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
import { useAuthStore } from 'stores/auth';

const props = defineProps<{
  modelValue: boolean;
  assetId: string;
  selected: InspectionTask | null;
}>();
const emit = defineEmits<{ 'update:modelValue': [open: boolean]; changed: []; navigate: [] }>();
const router = useRouter();
const auth = useAuthStore();
const sourcePlan = ref<InspectionWorkPlan | null>(null),
  sourcePlanOpen = ref(false);
const task = ref<InspectionTask | null>(null),
  loading = ref(false),
  error = ref('');
const issue = ref<Issue | null>(null),
  issueOpen = ref(false),
  issueLoading = ref(false),
  issueError = ref('');
const historical = computed(
  () =>
    task.value &&
    (task.value.state !== 'ACTIVE' ||
      (task.value.month < thisMonth() && task.value.completedSnapshot)),
);
let request = 0;
async function load() {
  const selected = props.selected;
  if (!selected || !props.modelValue) return;
  const token = ++request;
  loading.value = true;
  error.value = '';
  task.value = null;
  issueError.value = '';
  issueLoading.value = false;
  try {
    const result = await getInspectionTasks(selected.month, {
      asset_id: props.assetId,
      issue_id: selected.issueId,
      include_overdue: false,
    });
    if (token !== request) return;
    task.value =
      result.items.find(
        (item) => item.month === selected.month && item.issueId === selected.issueId,
      ) ?? null;
    if (!task.value)
      error.value = '이 자산에 연결된 점검 기록을 찾을 수 없거나 조회 권한이 없습니다.';
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '점검 기록을 불러오지 못했습니다.');
  } finally {
    if (token === request) loading.value = false;
  }
}
async function openIssue() {
  if (!task.value || issueLoading.value) return;
  if (task.value.sourceType === 'WORK_PLAN') {
    if (!(auth.me?.isAdmin || auth.me?.permissions?.includes('job'))) {
      issueError.value = '작업계획서를 열려면 작업 관리 권한이 필요합니다.';
      return;
    }
    sourcePlan.value = task.value.workPlan || null;
    sourcePlanOpen.value = true;
    return;
  }
  const token = request,
    selected = task.value;
  issueLoading.value = true;
  issueError.value = '';
  try {
    const result = await getIssue(selected.issue.projectId, selected.issueId);
    if (token !== request) return;
    issue.value = result;
    await nextTick();
    if (token === request) issueOpen.value = true;
  } catch (e) {
    if (token === request)
      issueError.value = getErrorMessage(e, '이슈를 불러오지 못했습니다. 다시 시도해 주세요.');
  } finally {
    if (token === request) issueLoading.value = false;
  }
}
function navigate() {
  if (!task.value) return;
  const query = { month: task.value.month, issue_id: task.value.issueId, asset_id: props.assetId };
  emit('update:modelValue', false);
  emit('navigate');
  void router.push({ path: '/inspection/tasks', query });
}
watch(issueOpen, (open) => {
  if (!open && props.modelValue) {
    void load();
    emit('changed');
  }
});
watch(
  () => [props.modelValue, props.assetId, props.selected],
  () => {
    ++request;
    issueOpen.value = false;
    issue.value = null;
    sourcePlanOpen.value = false;
    sourcePlan.value = null;
    if (props.modelValue) void load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  ++request;
});
</script>

<style scoped>
.asset-inspection-dialog {
  width: 560px;
  max-width: calc(100vw - 32px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}
.inspection-history-body {
  overflow-y: auto;
}
.inspection-history-body h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.5;
  font-weight: 500;
  color: #33485f;
  overflow-wrap: anywhere;
}
.inspection-history-fields {
  margin: 24px 0 0;
  font-size: 13px;
  line-height: 1.8;
  color: #33485f;
  overflow-wrap: anywhere;
}
.inspection-history-fields dt {
  color: #7a8798;
  font-size: 12px;
  margin-top: 16px;
}
.inspection-history-fields dd {
  margin: 2px 0 0;
}
.inspection-history-fields dd span {
  color: #7a8798;
}
.inspection-history-reason {
  white-space: pre-wrap;
}
.inspection-history-notice {
  color: #7a8798;
  font-size: 12px;
  line-height: 1.8;
  margin: 20px 0 0;
}
</style>
