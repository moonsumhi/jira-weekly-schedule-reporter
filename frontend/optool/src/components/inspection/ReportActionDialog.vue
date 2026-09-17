<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="close">
    <q-card class="report-action-dialog">
      <q-card-section class="dialog-heading">
        <div>
          <div class="text-caption text-grey-7">{{ target?.hostName }}</div>
          <h2>조치 내역 {{ context?.action ? '수정' : '작성' }}</h2>
        </div>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="조치 내역 닫기"
          :disable="busy"
          @click="close"
        />
      </q-card-section>
      <q-card-section class="dialog-body q-pt-none">
        <div v-if="loading" class="text-center q-pa-lg">
          <q-spinner color="primary" size="28px" />
        </div>
        <template v-else-if="context">
          <q-btn-toggle
            v-model="resolved"
            unelevated
            no-caps
            toggle-color="primary"
            :disable="busy"
            :options="[
              { label: '조치 중', value: false },
              { label: '조치 완료', value: true },
            ]"
            class="action-status-toggle q-mb-lg"
          />
          <q-input
            v-model="memo"
            outlined
            type="textarea"
            label="조치 내용"
            autogrow
            autofocus
            :disable="busy"
            maxlength="10000"
            placeholder="수행한 조치와 확인한 결과를 적어 주세요."
          />
          <div class="evidence-heading q-mt-lg">
            <b>증빙 이미지</b>
            <q-btn
              flat
              dense
              no-caps
              icon="add_photo_alternate"
              label="이미지 추가"
              :disable="busy || reading"
              @click="fileInput?.click()"
            />
            <input
              ref="fileInput"
              class="hidden"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              multiple
              @change="addImages"
            />
          </div>
          <div v-if="images.length" class="edit-images">
            <div v-for="(src, i) in images" :key="i">
              <img :src="src" :alt="`조치 증빙 ${i + 1}`" />
              <q-btn
                round
                dense
                color="white"
                text-color="grey-8"
                icon="close"
                size="xs"
                :aria-label="`증빙 이미지 ${i + 1} 삭제`"
                :disable="busy || reading"
                @click="images.splice(i, 1)"
              />
            </div>
          </div>
          <p class="text-caption text-grey-7 q-mb-none">
            저장한 조치 내역은 자원 점검에도 반영됩니다.
          </p>
        </template>
        <q-banner
          v-if="error"
          class="bg-red-1 text-negative rounded-borders q-mt-md"
          role="alert"
          >{{ error }}</q-banner
        >
      </q-card-section>
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="취소" :disable="busy || reading" @click="close" />
        <q-btn
          unelevated
          color="primary"
          label="조치 저장"
          :loading="busy"
          :disable="loading || reading || !context"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { useQuasar } from 'quasar';
import { inspectionError } from 'src/services/inspection';
import {
  getReportAction,
  saveReportAction,
  type InspectionReport,
  type ReportActionTarget,
  type ReportActionEditContext,
} from 'src/services/inspectionReports';
const props = defineProps<{
  modelValue: boolean;
  report: InspectionReport;
  target: ReportActionTarget | null;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  saved: [report: InspectionReport, warning: string];
}>();
const $q = useQuasar();
const context = ref<ReportActionEditContext | null>(null);
const memo = ref(''),
  images = ref<string[]>([]),
  resolved = ref(false);
const loading = ref(false),
  busy = ref(false),
  reading = ref(false),
  error = ref(''),
  initial = ref('');
const fileInput = ref<HTMLInputElement | null>(null);
const draft = computed(() => JSON.stringify([memo.value, images.value, resolved.value]));
let generation = 0;
watch(
  () => props.modelValue,
  async (open) => {
    const token = ++generation;
    if (!open || !props.target) return;
    context.value = null;
    error.value = '';
    loading.value = true;
    try {
      const loaded = await getReportAction(props.report.id, props.target);
      if (token !== generation) return;
      context.value = loaded;
      memo.value = loaded.action?.memo || '';
      images.value = [...(loaded.action?.images || [])];
      resolved.value = loaded.action?.isResolved ?? false;
      initial.value = draft.value;
    } catch (e) {
      if (token === generation) error.value = inspectionError(e);
    } finally {
      if (token === generation) loading.value = false;
    }
  },
);
function discard(): boolean | Promise<boolean> {
  if (!props.modelValue) return true;
  if (busy.value || reading.value) return false;
  if (!context.value || draft.value === initial.value) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: '저장하지 않고 닫으시겠습니까?',
      message: '작성 중인 조치 내역이 있습니다.',
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
async function addImages(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = '';
  reading.value = true;
  try {
    for (const file of files) {
      if (
        !['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type) ||
        file.size > 3 * 1024 * 1024
      ) {
        $q.notify({
          type: 'warning',
          message: `${file.name}: 3MB 이하의 PNG, JPG, GIF, WebP 이미지를 선택해 주세요.`,
        });
        continue;
      }
      images.value.push(
        await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
            reader.onload = () => {
              if (typeof reader.result === 'string') resolve(reader.result);
              else reject(new Error('이미지를 읽지 못했습니다.'));
            };
          reader.onerror = () => reject(new Error('이미지를 읽지 못했습니다.'));
          reader.readAsDataURL(file);
        }),
      );
    }
  } catch {
    error.value = '이미지를 읽지 못했습니다. 파일을 다시 선택해 주세요.';
  } finally {
    reading.value = false;
  }
}
async function save() {
  if (!context.value || !props.target || busy.value || reading.value) return;
  busy.value = true;
  error.value = '';
  try {
    const result = await saveReportAction(props.report.id, props.target, context.value, {
      memo: memo.value,
      images: images.value,
      is_resolved: resolved.value,
    });
    initial.value = draft.value;
    emit('saved', result.report, result.warning);
    emit('update:modelValue', false);
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
</script>
<style scoped>
.report-action-dialog {
  width: 620px;
  max-width: calc(100vw - 32px);
  max-height: calc(100dvh - 48px);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}
.dialog-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
h2 {
  font-size: 19px;
  font-weight: 700;
  margin: 4px 0 0;
  line-height: 1.5;
}
.dialog-body {
  overflow-y: auto;
  min-height: 0;
}
.action-status-toggle {
  border: 1px solid #e0e5eb;
}
.evidence-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}
.edit-images {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 10px 0 18px;
}
.edit-images > div {
  position: relative;
  width: 108px;
  height: 88px;
}
.edit-images img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border: 1px solid #e0e5eb;
  border-radius: 8px;
}
.edit-images .q-btn {
  position: absolute;
  top: -6px;
  right: -6px;
}
</style>
