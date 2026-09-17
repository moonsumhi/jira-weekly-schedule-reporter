<template>
  <div class="action-panel" :aria-busy="loading || saving || deleting">
    <header class="action-heading">
      <h3>조치 내역</h3>
      <div v-if="action && !editing && !loading && !loadError" class="action-buttons">
        <q-btn
          v-if="isInternal"
          flat
          dense
          no-caps
          icon="edit"
          label="수정"
          color="primary"
          :disable="deleting"
          @click="startEdit"
        />
        <q-btn
          v-if="isInternal"
          flat
          dense
          no-caps
          icon="delete_outline"
          label="삭제"
          color="grey-7"
          @click="confirmDelete"
          :loading="deleting"
        />
      </div>
    </header>
    <div v-if="loading" class="action-feedback" role="status">
      <q-spinner size="22px" color="primary" /><span>조치 내역을 불러오는 중입니다.</span>
    </div>
    <div v-else-if="loadError" class="action-feedback" role="alert">
      <span>조치 내역을 불러오지 못했습니다.</span
      ><q-btn outline no-caps color="primary" label="다시 불러오기" @click="load" />
    </div>
    <template v-else-if="action && !editing">
      <div class="action-content">
        <div class="action-byline">
          <span class="action-status" :class="{ resolved: action.isResolved }">{{
            action.isResolved ? '조치 완료' : '조치 중'
          }}</span
          ><span>{{ action.actor }}</span
          ><time>{{ displayDate(action.updatedAt || action.createdAt) }}</time>
        </div>
        <p v-if="action.memo" class="memo-box">{{ action.memo }}</p>
        <div v-if="action.images.length" class="action-evidence">
          <h4>
            증빙 이미지 <span>{{ action.images.length }}</span>
          </h4>
          <div class="action-images">
            <button
              v-for="(img, i) in action.images"
              :key="i"
              type="button"
              class="action-thumb"
              :aria-label="`조치 증빙 이미지 ${i + 1} 확대`"
              @click="
                previewImg = img;
                previewDialog = true;
              "
            >
              <q-img :src="img" fit="cover" /><span><q-icon name="zoom_in" size="16px" />확대</span>
            </button>
          </div>
        </div>
      </div>
    </template>
    <div v-else-if="!editing" class="action-feedback">
      <q-icon name="assignment" size="30px" color="grey-5" />
      <span>등록된 조치 내역이 없습니다.</span>
      <q-btn
        v-if="isInternal"
        outline
        no-caps
        color="primary"
        icon="add"
        label="조치 등록"
        @click="startEdit"
      />
    </div>
    <div v-if="editing" class="action-editor">
      <div class="action-editor-heading">
        <strong>{{ action ? '조치 수정' : '조치 등록' }}</strong
        ><q-toggle v-model="form.isResolved" label="조치 완료" dense size="sm" :disable="saving" />
      </div>
      <q-input
        v-model="form.memo"
        type="textarea"
        outlined
        autogrow
        label="조치 내용"
        placeholder="확인한 내용과 수행한 조치를 작성해 주세요."
        :disable="saving"
      />
      <div class="action-upload">
        <q-btn
          flat
          dense
          no-caps
          icon="add_photo_alternate"
          label="증빙 이미지 추가"
          color="primary"
          :disable="saving"
          @click="triggerImgInput"
        />
        <input
          ref="imgInput"
          type="file"
          accept="image/*"
          multiple
          class="hidden"
          @change="onImgChange"
        />
      </div>
      <div v-if="form.images.length" class="action-images">
        <div v-for="(img, i) in form.images" :key="i" class="img-wrap">
          <q-img :src="img" class="action-thumb" fit="cover" />
          <q-btn
            round
            dense
            unelevated
            icon="close"
            size="xs"
            color="white"
            text-color="grey-8"
            class="img-remove"
            :aria-label="`증빙 이미지 ${i + 1} 삭제`"
            :disable="saving"
            @click="removeImg(i)"
          />
        </div>
      </div>
      <div class="action-editor-footer">
        <q-btn flat no-caps label="취소" :disable="saving" @click="cancelEdit" /><q-btn
          unelevated
          no-caps
          color="primary"
          label="저장"
          @click="save"
          :loading="saving"
        />
      </div>
    </div>
  </div>
  <InspectionImagePreview
    v-model="previewDialog"
    :src="previewImg"
    :title="`${hostName} · 조치 증빙`"
  />
</template>
<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import InspectionImagePreview from 'src/components/inspection/InspectionImagePreview.vue';

interface ActionOut {
  id: string;
  reportId: string;
  hostName: string;
  memo: string;
  images: string[];
  actor: string;
  createdAt: string | null;
  updatedAt: string | null;
  isResolved: boolean;
}

const props = defineProps<{ reportId: string; hostName: string }>();

const $q = useQuasar();
const auth = useAuthStore();
const isInternal = computed(() => auth.me?.isInternal !== false);
const action = ref<ActionOut | null>(null);
const editing = ref(false);
const saving = ref(false);
const deleting = ref(false);
const loading = ref(false),
  loadError = ref(false);
let request = 0;
const imgInput = ref<HTMLInputElement | null>(null);

const form = ref({ memo: '', images: [] as string[], isResolved: true });

const previewDialog = ref(false);
const previewImg = ref('');

function displayDate(value: string | null) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Asia/Seoul',
        dateStyle: 'short',
        timeStyle: 'short',
      }).format(date);
}
async function load() {
  const token = ++request;
  loading.value = true;
  loadError.value = false;
  action.value = null;
  try {
    const res = await api.get<ActionOut[]>(`/health-reports/${props.reportId}/actions`);
    if (token === request)
      action.value = res.data.find((a) => a.hostName === props.hostName) ?? null;
  } catch {
    if (token === request) loadError.value = true;
  } finally {
    if (token === request) loading.value = false;
  }
}

function startEdit() {
  if (action.value) {
    form.value = {
      memo: action.value.memo,
      images: [...action.value.images],
      isResolved: action.value.isResolved,
    };
  } else {
    form.value = { memo: '', images: [], isResolved: true };
  }
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
}

async function save() {
  saving.value = true;
  try {
    const res = await api.post<ActionOut>(
      `/health-reports/${props.reportId}/actions/${encodeURIComponent(props.hostName)}`,
      form.value,
    );
    action.value = res.data;
    editing.value = false;
    $q.notify({ type: 'positive', message: '조치 내역이 저장되었습니다.' });
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다.' });
  } finally {
    saving.value = false;
  }
}

function confirmDelete() {
  $q.dialog({
    title: '조치 내역 삭제',
    message: '이 조치 내역을 삭제하시겠습니까?',
    cancel: true,
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      deleting.value = true;
      try {
        await api.delete(
          `/health-reports/${props.reportId}/actions/${encodeURIComponent(props.hostName)}`,
        );
        action.value = null;
        $q.notify({ type: 'positive', message: '삭제되었습니다.' });
      } catch {
        $q.notify({ type: 'negative', message: '삭제에 실패했습니다.' });
      } finally {
        deleting.value = false;
      }
    })();
  });
}

function triggerImgInput() {
  imgInput.value?.click();
}

async function onImgChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = '';
  for (const file of files) {
    if (file.size > 3 * 1024 * 1024) {
      $q.notify({ type: 'warning', message: `${file.name}: 3MB 이하 이미지만 업로드 가능합니다.` });
      continue;
    }
    const b64 = await toBase64(file);
    form.value.images.push(b64);
  }
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function removeImg(i: number) {
  form.value.images.splice(i, 1);
}

watch(() => [props.reportId, props.hostName], load, { immediate: true });
onBeforeUnmount(() => {
  ++request;
});
</script>
<style scoped>
.hidden {
  display: none;
}
.action-panel {
  color: #25364a;
}
.action-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid #edf0f4;
}
.action-heading h3 {
  font-size: 15px;
  font-weight: 650;
  line-height: 1.5;
  margin: 0;
}
.action-buttons {
  display: flex;
  gap: 10px;
}
.action-buttons .q-btn {
  font-size: 12px;
}
.action-content,
.action-editor {
  padding: 20px;
}
.action-byline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 12px;
  color: #73849a;
}
.action-status {
  padding: 4px 8px;
  border-radius: 5px;
  background: #fff3df;
  color: #995517;
  font-weight: 500;
}
.action-status.resolved {
  background: #edf6f2;
  color: #347166;
}
.memo-box {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 14px;
  line-height: 1.9;
  margin: 18px 0 0;
}
.action-evidence {
  margin-top: 24px;
}
.action-evidence h4 {
  font-size: 12px;
  line-height: 1.5;
  font-weight: 500;
  color: #718299;
  margin: 0 0 10px;
}
.action-evidence h4 span {
  margin-left: 4px;
  color: #365f87;
}
.action-images {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.action-thumb {
  position: relative;
  display: block;
  padding: 0;
  width: 124px;
  height: 92px;
  border-radius: 8px;
  border: 1px solid #dce4ee;
  overflow: hidden;
  background: #f4f6f9;
}
button.action-thumb {
  cursor: zoom-in;
}
button.action-thumb:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 3px;
}
.action-thumb .q-img {
  width: 100%;
  height: 100%;
}
.action-thumb > span {
  position: absolute;
  right: 5px;
  bottom: 5px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px 5px;
  background: #fff;
  color: #435971;
  border-radius: 4px;
  font-size: 10px;
}
.img-wrap {
  position: relative;
}
.img-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  box-shadow: 0 1px 5px #0002;
}
.action-feedback {
  padding: 28px 20px;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 14px;
  font-size: 13px;
  color: #78899b;
  text-align: center;
}
.action-feedback .q-btn {
  font-size: 12px;
}
.action-editor-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  font-size: 13px;
}
.action-editor-heading strong {
  font-weight: 500;
}
.action-editor :deep(textarea) {
  min-height: 104px;
  font-size: 14px;
  line-height: 1.8;
}
.action-upload {
  margin: 14px 0;
}
.action-upload .q-btn {
  font-size: 12px;
}
.action-editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
@media (max-width: 599px) {
  .action-heading {
    padding: 16px;
  }
  .action-buttons {
    gap: 2px;
  }
  .action-content,
  .action-editor {
    padding: 16px;
  }
}
</style>
