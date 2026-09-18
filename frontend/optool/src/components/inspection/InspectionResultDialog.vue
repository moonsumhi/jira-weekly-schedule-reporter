<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="close">
    <q-card class="result-dialog">
      <q-card-section class="result-dialog-header row items-start no-wrap q-pb-sm">
        <div class="col">
          <div class="result-eyebrow">
            {{ task ? formatInspectionMonth(task.month) : '' }} · 작업 결과
          </div>
          <h2>{{ task?.issue.title }}</h2>
          <div class="text-caption text-grey-7">
            {{ task?.issue.key }} · {{ task?.issue.assigneeName }}
          </div>
        </div>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="작업 결과 닫기"
          :disable="busy"
          @click="close"
        />
      </q-card-section>
      <q-card-section class="result-dialog-body q-pt-sm">
        <div class="result-hint">
          작업 결과를 작성하거나 작업 관리의 결과서를 연결해 주세요.
        </div>
        <InspectionWorkPlanLinks :plans="relatedPlans" back-label="작업 결과로 돌아가기" />
        <q-input
          v-model="content"
          outlined
          type="textarea"
          label="작업 결과"
          autogrow
          autofocus
          :readonly="readonly"
          :disable="busy"
          maxlength="10000"
          placeholder="예: 로그 정리 후 디스크 사용량 90% → 60%, 서비스 정상 동작 확인"
          class="q-mt-lg"
        />
        <div class="result-documents q-mt-md">
          <div class="result-documents-heading">
            <span>작업결과서 <small v-if="selectedResults.length">{{ selectedResults.length }}개</small></span>
            <q-btn v-if="canLinkResults && !readonly" flat dense no-caps color="primary"
              :icon="selectingResults ? 'expand_less' : 'link'" :label="selectingResults ? '접기' : selectedResults.length ? '연결 변경' : '연결'"
              :disable="busy" :aria-expanded="selectingResults" aria-label="작업결과서 연결"
              @click="selectingResults = !selectingResults" />
          </div>
          <InspectionWorkPlanPicker v-if="selectingResults && canLinkResults && !readonly"
            v-model="selectedResults" kind="RESULT" :asset-ids="task?.assets.map((asset) => asset.id) || []" :disable="busy" />
          <InspectionWorkPlanLinks v-else-if="selectedResults.length" :plans="selectedResults" kind="RESULT" hide-label back-label="작업 결과로 돌아가기" />
          <p v-else class="result-documents-empty">연결된 작업결과서가 없습니다.</p>
        </div>
        <q-input
          v-model="performedOn"
          outlined
          type="date"
          stack-label
          label="작업일 (선택)"
          :readonly="readonly"
          :disable="busy"
          class="q-mt-md"
        />
        <q-input
          v-model="followUp"
          outlined
          type="textarea"
          autogrow
          label="추가 작업 계획 (선택)"
          :readonly="readonly"
          :disable="busy"
          maxlength="3000"
          placeholder="남은 작업, 담당자와 예정일 등을 적어 주세요."
          class="q-mt-md"
        />
        <p v-if="task?.result" class="text-caption text-grey-7 q-mb-none">
          {{ task.result.updatedBy }} · {{ reportTime(task.result.updatedAt) }}
        </p>
        <q-banner
          v-if="error"
          class="bg-red-1 text-negative rounded-borders q-mt-md"
          role="alert"
          >{{ error }}</q-banner
        >
      </q-card-section>
      <q-card-actions align="right" class="q-pa-md"
        ><q-btn flat :label="readonly ? '닫기' : '취소'" :disable="busy" @click="close" /><q-btn
          v-if="!readonly"
          unelevated
          color="primary"
          label="저장"
          :loading="busy"
          @click="save"
      /></q-card-actions>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from 'stores/auth';
import {
  formatInspectionMonth,
  inspectionError,
  saveInspectionResult,
  type InspectionTask,
  type InspectionResultInput,
} from 'src/services/inspection';
import { reportTime, saveReportTaskResult } from 'src/services/inspectionReports';
import type { InspectionWorkResult } from 'src/services/inspectionWorkPlans';
import InspectionWorkPlanLinks from './InspectionWorkPlanLinks.vue';
import InspectionWorkPlanPicker from './InspectionWorkPlanPicker.vue';
const props = defineProps<{
  modelValue: boolean;
  task: InspectionTask | null;
  readonly?: boolean;
  reportId?: string;
}>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>();
const $q = useQuasar(),
  auth = useAuthStore();
const readonly = computed(() => props.readonly || auth.me?.isInternal === false);
const canLinkResults = computed(() => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('job')));
const selectedResults = ref<InspectionWorkResult[]>([]), selectingResults = ref(false);
const relatedPlans = computed(() => {
  const task = props.task;
  const plans = task?.workPlan ? [task.workPlan, ...(task.workPlans || [])] : task?.workPlans || [];
  return plans.filter((plan, index) => plans.findIndex((item) => item.id === plan.id) === index);
});
const content = ref(''),
  performedOn = ref(''),
  followUp = ref(''),
  busy = ref(false),
  error = ref(''),
  initial = ref('');
const draft = computed(() => JSON.stringify([content.value, performedOn.value, followUp.value, selectedResults.value.map((ref) => ref.id)]));
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    content.value = props.task?.result?.content || '';
    performedOn.value = props.task?.result?.performedOn || '';
    followUp.value = props.task?.result?.followUp || '';
    selectedResults.value = (props.task?.result?.workResults || []).map((ref) => ({ ...ref }));
    selectingResults.value = false;
    error.value = '';
    initial.value = draft.value;
  },
  { immediate: true },
);
function close() {
  if (busy.value) return;
  if (!readonly.value && draft.value !== initial.value) {
    $q.dialog({
      title: '저장하지 않고 닫으시겠습니까?',
      message: '저장하지 않은 내용이 있습니다.',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '닫기', color: 'negative' },
    }).onOk(() => emit('update:modelValue', false));
  } else emit('update:modelValue', false);
}
function protectResult(): boolean | Promise<boolean> {
  if (!props.modelValue || readonly.value || !auth.isLoggedIn) return true;
  if (busy.value) return false;
  if (draft.value === initial.value) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: '작성 중인 작업 결과가 있습니다',
      message: '저장하지 않고 다른 화면으로 이동할까요?',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '이동', color: 'negative' },
    })
      .onOk(() => {
        emit('update:modelValue', false);
        resolve(true);
      })
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}
onBeforeRouteLeave(protectResult);
onBeforeRouteUpdate(protectResult);
async function save() {
  if (!props.task || readonly.value || busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    const body: InspectionResultInput = {
      version: props.task.result?.version || 0,
      content: content.value,
      performed_on: performedOn.value || null,
      follow_up: followUp.value,
    };
    const previousIds = (props.task.result?.workResults || []).map((ref) => ref.id);
    const selectedIds = selectedResults.value.map((ref) => ref.id);
    if (canLinkResults.value && JSON.stringify(previousIds) !== JSON.stringify(selectedIds)) {
      body.work_result_ids = selectedIds;
    }
    if (props.reportId) await saveReportTaskResult(props.reportId, props.task, body);
    else await saveInspectionResult(props.task, body);
    emit('saved');
    emit('update:modelValue', false);
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
</script>
<style scoped>
.result-dialog {
  width: 580px;
  max-width: calc(100vw - 32px);
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px;
}
.result-dialog-header, .result-dialog > .q-card__actions { flex-shrink: 0; }
.result-dialog-body { flex: 1; min-height: 0; overflow-y: auto; }
.result-dialog > .q-card__actions { border-top: 1px solid #edf0f4; }
.result-documents { border: 1px solid #e2e8ef; border-radius: 8px; padding: 12px; }
.result-documents-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.result-documents-heading small { color: #718398; font-weight: 400; margin-left: 4px; }
.result-documents-empty { font-size: 12px; color: #718398; margin: 0; }
h2 {
  margin: 5px 0;
  font-size: 19px;
  line-height: 1.5;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.result-eyebrow {
  font-size: 12px;
  color: #617187;
}
.result-hint {
  font-size: 13px;
  color: #617187;
  line-height: 1.7;
}
</style>
