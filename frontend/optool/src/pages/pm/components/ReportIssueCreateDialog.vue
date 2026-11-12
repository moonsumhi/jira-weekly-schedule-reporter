<template>
  <q-dialog :model-value="modelValue && step === 'project'" @update:model-value="closePicker" @hide="openIssueForm">
    <q-card class="report-project-picker">
      <q-card-section>
        <div class="text-h6 text-weight-bold">이슈를 추가할 프로젝트</div>
        <p class="text-body2 text-grey-7 q-mb-none q-mt-sm">프로젝트를 선택하면 이슈 작성 화면으로 이동합니다.</p>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-banner v-if="error" class="bg-red-1 text-negative q-mb-md" rounded>
          {{ error }}
          <template #action><q-btn flat label="다시 시도" @click="loadProjects" /></template>
        </q-banner>
        <q-select v-model="projectId" :options="filteredOptions" outlined use-input input-debounce="0"
          emit-value map-options label="프로젝트" :loading="loading" :disable="loading || !!error"
          autofocus @filter="filterProjects">
          <template #no-option><q-item><q-item-section class="text-grey-7">
            {{ projects.length ? '검색 결과가 없습니다.' : '추가할 수 있는 프로젝트가 없습니다.' }}
          </q-item-section></q-item></template>
        </q-select>
        <p class="text-caption text-grey-7 q-mb-none q-mt-md">이슈의 일정과 상태에 따라 보고서에 자동 반영됩니다.</p>
      </q-card-section>
      <q-separator />
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="취소" @click="emit('update:modelValue', false)" />
        <q-btn unelevated color="primary" label="다음" :disable="!projectId || loading || !!error" @click="step = 'issue'" />
      </q-card-actions>
    </q-card>
  </q-dialog>
  <IssueFormDialog v-if="modelValue && projectId && step === 'issue'" :key="projectId"
    :model-value="issueOpen" :project-id="projectId" @update:model-value="onIssueOpen"
    @created="emit('created', $event)" @updated="emit('updated', $event)" />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QSelectProps } from 'quasar'
import { listProjects, type Project } from 'src/services/pm/project'
import type { Issue } from 'src/services/pm/issue'
import { getErrorMessage } from 'src/utils/http/error'
import IssueFormDialog from './IssueFormDialog.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [boolean]
  created: [Issue]
  updated: [Issue]
}>()
const step = ref<'project' | 'issue'>('project')
const projectId = ref<string | null>(null)
const issueOpen = ref(false)
const projects = ref<Project[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
let request = 0
const filteredOptions = computed(() => projects.value
  .filter(p => `${p.key} ${p.name}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()))
  .map(p => ({ label: `${p.key} · ${p.name}`, value: p.id })))
const filterProjects: NonNullable<QSelectProps['onFilter']> = (value, update) => {
  update(() => { search.value = value })
}
async function loadProjects() {
  const token = ++request
  loading.value = true
  error.value = ''
  try {
    const result = await listProjects()
    if (token === request) projects.value = result
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '프로젝트를 불러오지 못했습니다.')
  } finally {
    if (token === request) loading.value = false
  }
}
watch(() => props.modelValue, open => {
  ++request
  if (!open) { issueOpen.value = false; return }
  step.value = 'project'
  projectId.value = null
  projects.value = []
  search.value = ''
  void loadProjects()
})
function closePicker(open: boolean) {
  if (!open && step.value === 'project') emit('update:modelValue', false)
}
function openIssueForm() {
  if (props.modelValue && step.value === 'issue') issueOpen.value = true
}
function onIssueOpen(open: boolean) {
  issueOpen.value = open
  if (!open) emit('update:modelValue', false)
}
</script>

<style scoped>
.report-project-picker { width: 480px; max-width: calc(100vw - 32px); }
</style>
