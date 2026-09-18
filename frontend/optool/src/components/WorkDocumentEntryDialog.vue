<template>
  <WorkDocumentDetail v-model="open" :loading="loading" :entry="entry" :title="template?.title || title"
    :sections="sections" :saving="saving" :save-warning="saveWarning" :exporting="exportingDocument" :error="error"
    link-assets :back-label="backLabel || '자산으로 돌아가기'" :inspection-links="isWorkPlanTemplate(template)" :result-inspection-links="isWorkResultTemplate(template)" @retry="load" @save="save"
    @export="exportDetailMarkdown" @export-file="exportDetailFile" @download-original="downloadOriginalFile" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import WorkDocumentDetail from './WorkDocumentDetail.vue'
import { formEntryService, type FormEntry } from 'src/services/formEntries'
import { formTemplateService, type FormTemplate } from 'src/services/formTemplates'
import { prepareWorkDocumentData, useWorkDocumentExport, workDocumentSections, type WorkDocumentData } from 'src/composables/useWorkDocument'
import { getErrorMessage } from 'src/utils/http/error'
import { isWorkPlanTemplate, isWorkResultTemplate } from 'src/services/inspectionWorkPlans'
import { saveWorkDocument, WorkDocumentInspectionError, type WorkDocumentInspection } from 'src/services/workDocumentInspection'

const props = defineProps<{ entryId: string; title: string; backLabel?: string }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()
const $q = useQuasar()
const entry = ref<FormEntry | null>(null), template = ref<FormTemplate | null>(null)
const saveWarning = ref('')
const loading = ref(false), saving = ref(false), error = ref('')
const sections = computed(() => workDocumentSections(template.value, entry.value?.data ?? {}))
const { exportingDocument, exportDetailFile, downloadOriginalFile, exportDetailMarkdown } =
  useWorkDocumentExport(entry, template, sections, loading)
let request = 0

async function load() {
  const token = ++request
  saveWarning.value = ''
  entry.value = null; template.value = null; error.value = ''; loading.value = true
  try {
    const document = await formEntryService.get(props.entryId)
    if (token !== request) return
    if (document.isDeleted) throw new Error('삭제된 작업 문서입니다.')
    const documentTemplate = await formTemplateService.get(document.templateId)
    if (token !== request) return
    template.value = documentTemplate
    entry.value = document
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '작업 문서를 불러오지 못했습니다.')
  } finally {
    if (token === request) loading.value = false
  }
}

async function save(values: WorkDocumentData, assetIds?: string[], inspection?: WorkDocumentInspection | null) {
  if (!entry.value || !template.value || saving.value) return
  const token = request, document = entry.value, documentTemplate = template.value
  saving.value = true
  try {
    const data = await prepareWorkDocumentData(documentTemplate, values)
    const updated = await saveWorkDocument({ entry: document, templateId: documentTemplate.id, data, assetIds, inspection })
    if (token !== request) return
    saveWarning.value = ''
    entry.value = updated
    emit('saved')
    $q.notify({ type: 'positive', message: inspection ? '작업계획서를 저장하고 서버 점검에 등록했습니다.' : '수정됐습니다.' })
  } catch (e) {
    if (token === request) {
      if (e instanceof WorkDocumentInspectionError) {
        saveWarning.value = e.message
        entry.value = e.entry
        emit('saved')
      }
      $q.notify({ type: 'negative', message: getErrorMessage(e, '수정에 실패했습니다.') })
    }
  } finally {
    if (token === request) saving.value = false
  }
}

watch(() => [open.value, props.entryId], () => {
  ++request
  saving.value = false
  if (open.value) void load()
}, { immediate: true })
onBeforeUnmount(() => { ++request })
</script>
