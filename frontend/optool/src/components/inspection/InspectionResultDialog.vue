<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="close">
    <q-card class="result-dialog">
      <q-card-section class="row items-start no-wrap q-pb-sm">
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
      <q-card-section class="q-pt-sm">
        <div class="result-hint">
          작업 내용과 결과를 작성해 주세요. 저장한 내용은 월간 작업과 점검 보고서에 표시됩니다.
        </div>
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
} from 'src/services/inspection';
import { reportTime, saveReportTaskResult } from 'src/services/inspectionReports';
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
const content = ref(''),
  performedOn = ref(''),
  followUp = ref(''),
  busy = ref(false),
  error = ref(''),
  initial = ref('');
const draft = computed(() => JSON.stringify([content.value, performedOn.value, followUp.value]));
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    content.value = props.task?.result?.content || '';
    performedOn.value = props.task?.result?.performedOn || '';
    followUp.value = props.task?.result?.followUp || '';
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
    const body = {
      version: props.task.result?.version || 0,
      content: content.value,
      performed_on: performedOn.value || null,
      follow_up: followUp.value,
    };
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
  border-radius: 16px;
}
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
