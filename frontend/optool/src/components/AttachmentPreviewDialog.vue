<template>
  <q-dialog :model-value="modelValue" maximized @update:model-value="(v) => emit('update:modelValue', v)">
    <q-card class="column no-wrap" style="height:100vh">
      <q-card-section class="row items-center q-py-sm">
        <q-icon :name="fileIcon" color="blue-6" size="20px" class="q-mr-sm" />
        <span class="text-subtitle1 ellipsis">{{ attachment?.originalName }}</span>
        <q-space />
        <q-btn flat dense round icon="download" color="primary" @click="onDownload">
          <q-tooltip>다운로드</q-tooltip>
        </q-btn>
        <q-btn flat dense round icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>
      <q-separator />
      <q-card-section class="col q-pa-none" style="overflow:auto">
        <div v-if="loading" class="text-center q-pa-xl text-grey">
          <q-spinner size="40px" color="primary" /><br />불러오는 중...
        </div>
        <iframe v-else-if="iframeUrl" :src="iframeUrl" :sandbox="iframeSandbox" class="preview-iframe" />
        <div v-else-if="excelHtml" class="q-pa-md" v-html="excelHtml" />
        <div v-else class="text-center q-pa-xl text-grey">
          <q-icon name="insert_drive_file" size="48px" class="q-mb-sm" /><br />
          미리보기를 지원하지 않는 형식입니다.
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import * as XLSX from 'xlsx'
import { api } from 'src/boot/axios'
import { attachmentRelPath, downloadAttachment } from 'src/utils/attachment'

interface AttachmentLike {
  url: string
  originalName: string
  contentType?: string
  size?: number
}

const props = defineProps<{
  modelValue: boolean
  attachment: AttachmentLike | null
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const $q = useQuasar()
const loading = ref(false)
const iframeUrl = ref<string | null>(null)
const excelHtml = ref<string | null>(null)

function extOf(name: string | undefined): string {
  if (!name) return ''
  const i = name.lastIndexOf('.')
  return i === -1 ? '' : name.slice(i + 1).toLowerCase()
}

const ext = computed(() => extOf(props.attachment?.originalName))

const fileIcon = computed(() => {
  const e = ext.value
  if (props.attachment?.contentType?.startsWith('image/')) return 'image'
  if (e === 'pdf') return 'picture_as_pdf'
  if (e === 'xlsx' || e === 'xls') return 'table_chart'
  if (e === 'pptx' || e === 'ppt') return 'slideshow'
  if (e === 'html' || e === 'htm') return 'code'
  if (e === 'zip') return 'folder_zip'
  return 'insert_drive_file'
})

const iframeSandbox = computed(() => {
  // 업로드된 원본 HTML은 스크립트 실행을 차단해 XSS를 방지 (다른 형식은 백엔드에서 변환된 안전한 HTML)
  return ext.value === 'html' || ext.value === 'htm' ? 'allow-same-origin' : undefined
})

function apiBase(): string {
  return (api.defaults.baseURL ?? '/api').replace(/\/$/, '')
}

async function load() {
  iframeUrl.value = null
  excelHtml.value = null
  const att = props.attachment
  if (!att) return

  if (ext.value === 'pdf') {
    iframeUrl.value = att.url
    return
  }
  if (ext.value === 'hwp') {
    iframeUrl.value = `${apiBase()}/attachments/hwp-preview?path=${encodeURIComponent(attachmentRelPath(att.url))}`
    return
  }
  if (ext.value === 'docx') {
    iframeUrl.value = `${apiBase()}/attachments/docx-preview?path=${encodeURIComponent(attachmentRelPath(att.url))}`
    return
  }
  if (ext.value === 'pptx' || ext.value === 'ppt') {
    iframeUrl.value = `${apiBase()}/attachments/pptx-preview?path=${encodeURIComponent(attachmentRelPath(att.url))}`
    return
  }
  if (ext.value === 'html' || ext.value === 'htm') {
    iframeUrl.value = att.url
    return
  }
  if (ext.value === 'xlsx' || ext.value === 'xls') {
    loading.value = true
    try {
      const resp = await fetch(att.url)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const buf = await resp.arrayBuffer()
      const wb = XLSX.read(buf, { type: 'array' })
      let html = ''
      for (const sheetName of wb.SheetNames) {
        const ws = wb.Sheets[sheetName]
        if (!ws) continue
        html += `<div class="text-caption text-weight-bold q-mb-xs">${sheetName}</div>`
        html += XLSX.utils.sheet_to_html(ws)
      }
      excelHtml.value = html
    } catch {
      $q.notify({ type: 'negative', message: '엑셀 미리보기를 불러오지 못했습니다.' })
    } finally {
      loading.value = false
    }
  }
}

async function onDownload() {
  const att = props.attachment
  if (!att) return
  try {
    await downloadAttachment(att.url, att.originalName)
  } catch {
    $q.notify({ type: 'negative', message: '파일 다운로드에 실패했습니다.' })
  }
}

watch(() => [props.modelValue, props.attachment], ([open]) => {
  if (open) void load()
}, { immediate: true })
</script>

<style scoped>
.preview-iframe {
  width: 100%;
  height: 100%;
  min-height: calc(100vh - 100px);
  border: none;
}
</style>
