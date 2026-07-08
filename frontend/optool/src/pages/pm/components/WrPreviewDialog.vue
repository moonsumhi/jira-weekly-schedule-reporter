<template>
  <q-dialog :model-value="modelValue" full-width @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="max-width:800px;width:100%">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">보고서 미리보기</div>
        <q-space />
        <q-btn flat dense icon="content_copy" label="복사" no-caps color="grey-7" @click="copyText" />
        <q-btn flat round dense icon="close" @click="$emit('update:modelValue', false)" />
      </q-card-section>
      <q-separator class="q-mt-sm" />
      <q-card-section style="max-height:75vh;overflow-y:auto">
        <q-inner-loading :showing="loading" />
        <pre v-if="text" class="preview-text">{{ text }}</pre>
        <div v-else-if="!loading" class="text-grey-5 text-center q-pa-lg">미리보기를 불러올 수 없습니다.</div>
      </q-card-section>
      <q-separator />
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="닫기" no-caps @click="$emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Notify } from 'quasar'
import { previewWeeklyReport } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{ modelValue: boolean; reportId: string }>()
defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const loading = ref(false)
const text = ref('')

watch(() => props.modelValue, async (open) => {
  if (!open) return
  loading.value = true
  text.value = ''
  try {
    text.value = await previewWeeklyReport(props.reportId)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '미리보기 로드 실패') })
  } finally {
    loading.value = false
  }
}, { immediate: true })

async function copyText() {
  if (!text.value) return
  try {
    await navigator.clipboard.writeText(text.value)
    Notify.create({ type: 'positive', message: '클립보드에 복사되었습니다.' })
  } catch {
    Notify.create({ type: 'warning', message: '복사에 실패했습니다.' })
  }
}
</script>

<style scoped>
.preview-text {
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
</style>
