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
        <div v-else-if="excelSheets.length" class="q-pa-md">
          <section v-for="sheet in excelSheets" :key="sheet.name" class="q-mb-lg">
            <div class="text-caption text-weight-bold q-mb-xs">{{ sheet.name }}</div>
            <div class="excel-sheet-scroll">
              <table class="excel-preview-table">
                <tbody>
                  <tr v-for="(row, rowIndex) in sheet.rows" :key="rowIndex">
                    <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
        <div v-else class="text-center q-pa-xl text-grey">
          <q-icon name="insert_drive_file" size="48px" class="q-mb-sm" /><br />
          미리보기를 지원하지 않는 형식입니다.
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
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
interface ExcelPreviewSheet {
  name: string
  rows: string[][]
}

const excelSheets = ref<ExcelPreviewSheet[]>([])
const MAX_EXCEL_PREVIEW_BYTES = 20 * 1024 * 1024
const MAX_EXCEL_PREVIEW_ROWS = 200
const MAX_EXCEL_PREVIEW_COLUMNS = 40
const MAX_EXCEL_PREVIEW_CELL_CHARS = 2000
let objectUrl: string | null = null

function formatExcelCell(cell: unknown): string {
  if (cell === null || cell === undefined) return ''
  const value =
    typeof cell === 'string' || typeof cell === 'number' || typeof cell === 'boolean'
      ? String(cell)
      : (JSON.stringify(cell) ?? '')
  return value.slice(0, MAX_EXCEL_PREVIEW_CELL_CHARS)
}

async function readLimitedArrayBuffer(response: Response, maxBytes: number): Promise<ArrayBuffer> {
  const contentLength = Number(response.headers.get('content-length'))
  if (Number.isFinite(contentLength) && contentLength > maxBytes) {
    throw new Error('스프레드시트 미리보기는 20MB 이하 파일만 지원합니다.')
  }

  if (!response.body) {
    const buffer = await response.arrayBuffer()
    if (buffer.byteLength > maxBytes) {
      throw new Error('스프레드시트 미리보기는 20MB 이하 파일만 지원합니다.')
    }
    return buffer
  }

  const reader = response.body.getReader()
  const chunks: Uint8Array[] = []
  let totalBytes = 0
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      totalBytes += value.byteLength
      if (totalBytes > maxBytes) {
        await reader.cancel()
        throw new Error('스프레드시트 미리보기는 20MB 이하 파일만 지원합니다.')
      }
      chunks.push(value)
    }
  } finally {
    reader.releaseLock()
  }

  const result = new Uint8Array(totalBytes)
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.byteLength
  }
  return result.buffer
}

function setIframeObjectUrl(blob: Blob) {
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  objectUrl = URL.createObjectURL(blob)
  iframeUrl.value = objectUrl
}

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
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  iframeUrl.value = null
  excelSheets.value = []
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
    loading.value = true
    try {
      // Use the shared API client so the current JWT is sent with the request.
      // Raw fetch bypasses the Axios auth interceptor.
      const resp = await api.get('/attachments/pptx-preview', {
        params: { path: attachmentRelPath(att.url) },
        responseType: 'blob',
      })
      setIframeObjectUrl(resp.data as Blob)
    } catch (e) {
      if (e && typeof e === 'object' && 'response' in e) {
        const response = (e as { response?: { data?: unknown } }).response
        if (response?.data instanceof Blob) {
          try {
            const body = JSON.parse(await response.data.text()) as { detail?: string }
            if (body.detail && e instanceof Error) e.message = body.detail
          } catch { /* Keep the original request error if the response isn't JSON. */ }
        }
      }
      $q.notify({ type: 'negative', message: e instanceof Error ? e.message : '프레젠테이션 미리보기를 불러오지 못했습니다.' })
    } finally {
      loading.value = false
    }
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
      const buf = await readLimitedArrayBuffer(resp, MAX_EXCEL_PREVIEW_BYTES)
      const wb = XLSX.read(buf, { type: 'array', sheetRows: MAX_EXCEL_PREVIEW_ROWS + 1 })
      const sheets: ExcelPreviewSheet[] = []
      for (const sheetName of wb.SheetNames) {
        const ws = wb.Sheets[sheetName]
        if (!ws) continue
        const rawRows = XLSX.utils.sheet_to_json<unknown[]>(ws, {
          header: 1,
          defval: '',
          blankrows: false,
          raw: false,
        })
        const rows = rawRows.slice(0, MAX_EXCEL_PREVIEW_ROWS).map((row) =>
          row
            .slice(0, MAX_EXCEL_PREVIEW_COLUMNS)
            .map(formatExcelCell),
        )
        sheets.push({ name: sheetName, rows })
      }
      excelSheets.value = sheets
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error instanceof Error ? error.message : '엑셀 미리보기를 불러오지 못했습니다.',
      })
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

onUnmounted(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl)
})
</script>

<style scoped>
.preview-iframe {
  width: 100%;
  height: 100%;
  min-height: calc(100vh - 100px);
  border: none;
}

.excel-sheet-scroll {
  max-width: 100%;
  overflow: auto;
}

.excel-preview-table {
  border-collapse: collapse;
  min-width: 100%;
}

.excel-preview-table td {
  border: 1px solid #d5dbe3;
  min-width: 80px;
  max-width: 360px;
  padding: 6px 8px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  vertical-align: top;
}
</style>
