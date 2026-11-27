<template>
  <q-select
    v-model="selectedId"
    class="project-filter"
    :class="{ 'project-filter--active': selectedId }"
    outlined dense use-input hide-selected fill-input
    :clearable="!!selectedId"
    :input-debounce="0"
    :options="options"
    option-value="id" option-label="label" emit-value map-options
    options-selected-class="project-filter-selected"
    :placeholder="selectedLabel"
    :loading="loading"
    :aria-label="`프로젝트 필터: ${selectedLabel}`"
    behavior="menu"
    @filter="filterOptions"
    @popup-hide="search = ''"
  >
    <template #before-options>
      <div v-if="loadFailed" class="project-filter-notice" role="status">
        <span>프로젝트 목록을 불러오지 못했습니다.</span>
        <q-btn flat dense no-caps label="다시 시도" :loading="loading" @click.stop="loadProjects" />
      </div>
    </template>
    <template #after-options>
      <div v-if="search && options.length === 1" class="project-filter-notice" role="status">검색 결과가 없습니다.</div>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { listProjects } from 'src/services/pm/project'
import type { Issue } from 'src/services/pm/issue'

const props = withDefaults(defineProps<{ issues?: Issue[] }>(), { issues: () => [] })
const selectedId = defineModel<string | null>({ default: null })
const knownProjects = ref(new Map<string, { id: string; label: string }>())
const search = ref('')
const loading = ref(false)
const loadFailed = ref(false)
const selectedLabel = computed(() => selectedId.value
  ? knownProjects.value.get(selectedId.value)?.label ?? '선택한 프로젝트'
  : '전체 프로젝트')
const options = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return [
    { id: null, label: '전체 프로젝트' },
    ...[...knownProjects.value.values()]
      .filter(project => project.label.toLocaleLowerCase().includes(query))
      .sort((a, b) => a.label.localeCompare(b.label, 'ko', { numeric: true })),
  ]
})

// Retain known projects across calendar periods, including projects in returned work.
watch(() => props.issues, issues => {
  for (const issue of issues) {
    if (issue.projectId && (issue.projectName || issue.projectKey)) {
      knownProjects.value.set(issue.projectId, {
        id: issue.projectId,
        label: [issue.projectKey, issue.projectName].filter(Boolean).join(' · '),
      })
    }
  }
}, { immediate: true })

function filterOptions(value: string, update: (fn: () => void) => void) {
  update(() => { search.value = value })
}

async function loadProjects() {
  if (loading.value) return
  loading.value = true
  loadFailed.value = false
  try {
    for (const project of await listProjects()) {
      knownProjects.value.set(project.id, { id: project.id, label: `${project.key} · ${project.name}` })
    }
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => { void loadProjects() })
</script>

<style scoped>
.project-filter { width: 220px; max-width: 100%; flex-shrink: 0; }
.project-filter :deep(.q-field__control) { min-height: 36px; height: 36px; background: var(--bo-surface); }
.project-filter :deep(.q-field__marginal) { height: 36px; }
.project-filter :deep(.q-field__native) { font-size: 13px; }
.project-filter :deep(input::placeholder) { color: var(--bo-secondary); opacity: 1; }
.project-filter--active :deep(.q-field__control) { background: var(--bo-accent-soft); }
.project-filter--active :deep(.q-field__native) { color: var(--bo-accent-ink); }
.project-filter-notice { padding: 10px 16px; color: var(--bo-muted); font-size: 13px; }
:global(.project-filter-selected) { color: var(--bo-accent-ink) !important; background: var(--bo-accent-soft); }
</style>
