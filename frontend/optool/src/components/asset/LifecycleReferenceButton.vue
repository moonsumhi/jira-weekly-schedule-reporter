<template>
  <q-btn v-if="entry" flat round dense size="xs" icon="info_outline" class="q-ml-xs"
    :aria-label="`${label} 근거 PDF 안내`" @click.stop>
    <q-tooltip>{{ label }} 근거 보기</q-tooltip>
    <q-menu max-width="400px" @click.stop>
      <div class="q-pa-md text-body2 lifecycle-reference">
        <div class="text-weight-medium q-mb-sm">{{ label }} 판단 근거</div>
        <div v-if="entry.note">{{ entry.note }}</div>
        <div v-if="entry.basis && entry.basis !== entry.note" class="q-mt-xs text-grey-8">{{ entry.basis }}</div>
        <div v-for="stage in stages" :key="`${stage.basis}-${stage.date}`" class="q-mt-xs text-caption text-grey-8">
          {{ stage.basis }}: {{ stage.date }}
        </div>
        <div v-for="document in documents" :key="document.path" class="q-mt-sm">
          <a :href="document.path" target="_blank" rel="noopener noreferrer" class="text-primary inline-block">
            <q-icon name="picture_as_pdf" class="q-mr-xs" />{{ document.title }} (PDF)
          </a>
          <div v-if="document.kind !== 'original_pdf'" class="text-caption text-grey-7">공식 자료의 내부망 보관본</div>
          <div v-if="document.archiveNote" class="q-mt-xs text-caption text-grey-7">{{ document.archiveNote }}</div>
        </div>
        <div v-for="notice in notices" :key="notice" class="q-mt-sm text-caption text-grey-7">{{ notice }}</div>
        <div v-if="!documents.length && !notices.length" class="q-mt-sm text-caption text-grey-7">등록된 근거 PDF가 없습니다. 정확한 제품·버전의 공식 자료 확인이 필요합니다.</div>
      </div>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LifecycleEvidence } from 'src/services/lifecycleAudit'
import { localLifecycleDocument, lifecycleDocumentNotice, type ReferenceDocument } from 'src/services/lifecycleReferences'
const props = defineProps<{ label: string; entry?: Partial<LifecycleEvidence> | null }>()
const stages = computed(() => [
  ...(props.entry?.milestone ? [props.entry.milestone] : []),
  ...(props.entry?.milestones ?? []),
].filter(stage => stage.date))
const sources = computed(() => [props.entry?.source, ...stages.value.map(stage => stage.source)])
const notices = computed(() => [...new Set(sources.value.map(lifecycleDocumentNotice).filter(Boolean))])
const documents = computed(() => {
  const unique = new Map<string, ReferenceDocument>()
  for (const source of sources.value) {
    const document = localLifecycleDocument(source)
    if (document) unique.set(document.path, document)
  }
  return [...unique.values()]
})
</script>
<style scoped>
.lifecycle-reference { max-width: min(400px, 85vw); overflow-wrap: anywhere; }
</style>
