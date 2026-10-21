<template>
  <q-btn
    outline
    color="primary"
    icon="picture_as_pdf"
    label="PDF 저장"
    :disable="disabled || !roomId"
    :loading="saving"
    @click="download"
  >
    <q-tooltip>게시된 전체 배치도와 현재 인원 배정 현황을 저장합니다.</q-tooltip>
  </q-btn>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { exportFile, useQuasar } from 'quasar';
import { isAxiosError } from 'axios';
import { spaceApi } from 'src/services/spaces';
import { getErrorMessage } from 'src/utils/http/error';

const props = defineProps<{ roomId: string; disabled?: boolean }>();
const $q = useQuasar();
const saving = ref(false);

async function download() {
  if (saving.value || props.disabled || !props.roomId) return;
  saving.value = true;
  try {
    const response = await spaceApi.planPdf(props.roomId);
    const encoded = String(response.headers['content-disposition'] || '').match(
      /filename\*=UTF-8''([^;]+)/i,
    )?.[1];
    const filename = encoded ? decodeURIComponent(encoded) : '좌석배치도.pdf';
    if (exportFile(filename, response.data, { mimeType: 'application/pdf' }) !== true)
      throw new Error('PDF를 저장하지 못했습니다. 브라우저의 다운로드 설정을 확인해 주세요.');
    $q.notify({ type: 'positive', message: '좌석 배치도 PDF를 저장했습니다.' });
  } catch (error) {
    // Binary requests also receive API errors as blobs.
    if (isAxiosError(error) && error.response?.data instanceof Blob) {
      try {
        error.response.data = JSON.parse(await error.response.data.text());
      } catch {
        // Keep the standard fallback if a proxy returned a non-JSON response.
      }
    }
    $q.notify({
      type: 'negative',
      message: getErrorMessage(error, 'PDF를 만들지 못했습니다. 다시 시도해 주세요.'),
    });
  } finally {
    saving.value = false;
  }
}
</script>
