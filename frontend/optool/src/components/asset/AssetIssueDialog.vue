<template>
  <q-dialog :model-value="modelValue && !issue" :transition-duration="0" @update:model-value="close">
    <q-card class="asset-issue-feedback">
      <q-card-section class="row items-center"><strong>연결된 이슈</strong><q-space /><q-btn flat round dense icon="close" aria-label="이슈 닫기" @click="close" /></q-card-section>
      <q-card-section class="q-pt-none">
        <q-spinner v-if="loading" color="primary" size="28px" />
        <div v-else-if="error" class="text-negative text-caption" role="alert">{{ error }} <q-btn flat dense label="다시 불러오기" @click="load" /></div>
      </q-card-section>
    </q-card>
  </q-dialog>
  <IssueDetailDialog v-if="issue" :model-value="modelValue" :issue="issue" :project-id="issue.projectId"
    @update:model-value="close" @updated="emit('changed')" @deleted="close" />
</template>
<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { getIssue, type Issue } from 'src/services/pm/issue'
import { getErrorMessage } from 'src/utils/http/error'
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue'
const props = defineProps<{ modelValue: boolean; assetId: string; selected: { id: string; projectId: string } | null }>()
const emit = defineEmits<{ 'update:modelValue': [open: boolean]; changed: [] }>()
const issue = ref<Issue | null>(null), loading = ref(false), error = ref('')
let request = 0
function close() { emit('update:modelValue', false); emit('changed') }
async function load() {
  if (!props.selected || !props.modelValue) return
  const token = ++request
  loading.value = true; issue.value = null; error.value = ''
  try {
    const value = await getIssue(props.selected.projectId, props.selected.id)
    if (token !== request) return
    if (!value.linkedAssets?.some(asset => asset.id === props.assetId)) {
      error.value = '이 이슈는 더 이상 해당 자산에 연결되어 있지 않습니다.'
      return
    }
    issue.value = value
  } catch (e) { if (token === request) error.value = getErrorMessage(e, '이슈를 불러오지 못했습니다.') }
  finally { if (token === request) loading.value = false }
}
watch(() => [props.modelValue, props.assetId, props.selected], () => {
  ++request
  if (props.modelValue) void load()
}, { immediate: true })
onBeforeUnmount(() => { ++request })
</script>
<style scoped>
.asset-issue-feedback { width: 560px; max-width: calc(100vw - 32px); }
</style>
