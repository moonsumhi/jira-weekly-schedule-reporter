<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="close">
    <q-card class="report-notes-dialog">
      <q-card-section class="row items-center no-wrap">
        <h2 class="col">추가 확인 사항 {{ note ? '수정' : '추가' }}</h2>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="추가 확인 사항 닫기"
          :disable="busy"
          @click="close"
        />
      </q-card-section>
      <q-card-section class="notes-body q-pt-none">
        <q-input
          v-model="notes"
          outlined
          type="textarea"
          autogrow
          autofocus
          label="내용"
          maxlength="5000"
          :disable="busy"
          placeholder="추가로 확인할 내용이나 전달할 사항을 적어 주세요."
        />
        <q-banner
          v-if="error"
          class="bg-red-1 text-negative rounded-borders q-mt-md"
          role="alert"
          >{{ error }}</q-banner
        >
      </q-card-section>
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="취소" :disable="busy" @click="close" />
        <q-btn
          unelevated
          color="primary"
          :label="note ? '저장' : '추가'"
          :disable="!notes.trim()"
          :loading="busy"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { uid, useQuasar } from 'quasar';
import {
  reportNotes,
  saveReportNotes,
  type InspectionReport,
  type ReportNote,
} from 'src/services/inspectionReports';
import { inspectionError } from 'src/services/inspection';
const props = defineProps<{
  modelValue: boolean;
  report: InspectionReport;
  note: ReportNote | null;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  saved: [report: InspectionReport];
}>();
const $q = useQuasar();
const notes = ref(''),
  initial = ref(''),
  error = ref(''),
  busy = ref(false);
let original: InspectionReport | null = null;
let noteId = '';
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    original = props.report;
    noteId = props.note?.id || uid();
    notes.value = initial.value = props.note?.content || '';
    error.value = '';
  },
);
function discard(): boolean | Promise<boolean> {
  if (!props.modelValue) return true;
  if (busy.value) return false;
  if (notes.value === initial.value) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: '저장하지 않고 닫으시겠습니까?',
      message: '작성 중인 추가 확인 사항이 있습니다.',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '닫기', color: 'negative' },
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}
async function close() {
  if (await discard()) emit('update:modelValue', false);
}
onBeforeRouteLeave(discard);
onBeforeRouteUpdate(discard);
async function save() {
  if (!original || busy.value || !notes.value.trim()) return;
  busy.value = true;
  error.value = '';
  try {
    const items = reportNotes(original);
    const item = { id: noteId, content: notes.value.trim() };
    const updated = await saveReportNotes(
      original,
      props.note
        ? items.map((existing) => (existing.id === noteId ? item : existing))
        : [...items, item],
    );
    initial.value = notes.value;
    emit('saved', updated);
    emit('update:modelValue', false);
    $q.notify({ type: 'positive', message: '추가 확인 사항을 저장했습니다.' });
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
</script>
<style scoped>
.report-notes-dialog {
  width: 620px;
  max-width: calc(100vw - 32px);
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
  border-radius: 16px;
}
h2 {
  font-size: 19px;
  font-weight: 700;
  line-height: 1.5;
  margin: 0;
}
.notes-body {
  overflow-y: auto;
  min-height: 0;
}
</style>
