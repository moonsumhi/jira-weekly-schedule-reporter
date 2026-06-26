<template>
  <q-page class="doc-page q-pa-md">

    <!-- 상단 검색 + 업로드 -->
    <div class="doc-topbar q-mb-md">
      <q-input
        v-model="searchQuery"
        dense outlined clearable
        placeholder="문서 내용 검색..."
        style="flex:1; max-width:500px"
        @update:model-value="onSearch"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn
        unelevated color="primary" icon="upload_file" label="폴더 업로드"
        :loading="uploading"
        @click="triggerUpload"
      />
      <input
        ref="uploadInput"
        type="file"
        webkitdirectory
        multiple
        style="display:none"
        @change="(e) => { void onFolderSelected(e) }"
      />
    </div>

    <!-- 검색 결과 -->
    <template v-if="isSearching">
      <div class="text-subtitle2 text-grey-7 q-mb-sm">
        검색 결과: <strong>{{ searchResults.length }}</strong>건
      </div>
      <div v-if="searchLoading" class="text-center q-pa-xl text-grey">검색 중...</div>
      <div v-else-if="searchResults.length === 0" class="text-center q-pa-xl text-grey">검색 결과가 없습니다.</div>
      <div v-else class="search-results">
        <div
          v-for="f in searchResults"
          :key="f.id"
          class="search-item"
          @click="void openFile(f)"
        >
          <q-icon :name="fileIcon(f.extension)" size="28px" :color="fileColor(f.extension)" class="q-mr-md" />
          <div class="search-item-body">
            <div class="search-item-name">{{ f.name }}</div>
            <div v-if="f.snippet" class="search-item-snippet text-grey-7">{{ f.snippet }}</div>
          </div>
          <div class="search-item-actions">
            <q-btn v-if="isAdmin" flat dense round icon="delete" color="negative" size="sm"
              @click.stop="confirmDeleteFile(f)" />
          </div>
        </div>
      </div>
    </template>

    <!-- 폴더 + 파일 브라우저 -->
    <template v-else>
      <div class="doc-layout">

        <!-- 좌측 폴더 트리 -->
        <div class="folder-panel">
          <div class="folder-panel-title text-caption text-grey-6 q-mb-xs">폴더</div>
          <div
            class="folder-item"
            :class="{ 'folder-item--active': selectedFolderId === null }"
            @click="selectFolder(null)"
          >
            <q-icon name="home" size="16px" class="q-mr-xs" />
            전체 (루트)
          </div>
          <div
            v-for="f in flatFolderTree"
            :key="f.id"
            class="folder-item"
            :class="{ 'folder-item--active': selectedFolderId === f.id }"
            :style="{ paddingLeft: (8 + f.depth * 16) + 'px' }"
            @click="selectFolder(f.id)"
          >
            <q-icon name="folder" size="15px" color="amber-7" class="q-mr-xs" />
            <span class="folder-item-label">{{ f.name }}</span>
            <q-btn
              v-if="isAdmin"
              flat dense round icon="delete" color="negative" size="xs"
              class="folder-del-btn"
              @click.stop="confirmDeleteFolder(f)"
            />
          </div>
        </div>

        <!-- 우측 파일 목록 -->
        <div class="file-panel">
          <!-- 경로 브레드크럼 -->
          <div v-if="breadcrumb.length" class="file-breadcrumb q-mb-sm">
            <span class="breadcrumb-item cursor-pointer" @click="selectFolder(null)">루트</span>
            <span v-for="b in breadcrumb" :key="b.id">
              <q-icon name="chevron_right" size="14px" class="q-mx-xs text-grey-5" />
              <span class="breadcrumb-item cursor-pointer" @click="selectFolder(b.id)">{{ b.name }}</span>
            </span>
          </div>

          <div v-if="filesLoading" class="text-center q-pa-xl text-grey">불러오는 중...</div>
          <div v-else-if="childFolders.length === 0 && currentFiles.length === 0" class="text-center q-pa-xl text-grey-5">
            <q-icon name="folder_open" size="48px" /><br />파일이 없습니다.
          </div>
          <div v-else class="file-grid">
            <!-- 서브폴더 -->
            <div
              v-for="f in childFolders"
              :key="'folder-' + f.id"
              class="file-card file-card--folder"
              @click="selectFolder(f.id)"
            >
              <q-icon name="folder" size="36px" color="amber-7" />
              <div class="file-card-name">{{ f.name }}</div>
              <div class="file-card-meta text-grey-6">폴더</div>
              <div v-if="isAdmin" class="file-card-actions">
                <q-btn flat dense round icon="delete" color="negative" size="xs" @click.stop="confirmDeleteFolder(f)" />
              </div>
            </div>
            <div
              v-for="f in currentFiles"
              :key="f.id"
              class="file-card"
              @click="void openFile(f)"
            >
              <q-icon :name="fileIcon(f.extension)" size="36px" :color="fileColor(f.extension)" />
              <div class="file-card-name">{{ f.name }}</div>
              <div class="file-card-meta text-grey-6">{{ formatSize(f.size) }}</div>
              <div class="file-card-actions">
                <q-btn flat dense round icon="edit" color="grey-7" size="xs" @click.stop="openEdit(f)" />
                <q-btn v-if="isAdmin" flat dense round icon="delete" color="negative" size="xs" @click.stop="confirmDeleteFile(f)" />
              </div>
            </div>
          </div>
        </div>

      </div>
    </template>

    <!-- 파일 뷰어 다이얼로그 -->
    <q-dialog v-model="viewerOpen" maximized>
      <q-card class="viewer-card">
        <q-card-section class="viewer-header row items-center">
          <q-icon :name="fileIcon(viewerFile?.extension ?? '')" size="20px" :color="fileColor(viewerFile?.extension ?? '')" class="q-mr-sm" />
          <span class="text-h6 ellipsis">{{ viewerFile?.name }}</span>
          <q-space />
          <q-btn
            flat dense round icon="download" color="primary"
            :href="viewerDownloadUrl"
            target="_blank"
            title="다운로드"
          />
          <q-btn flat dense round icon="edit" color="grey-7" title="수정" @click="openEdit(viewerFile!)" />
          <q-btn flat dense round icon="close" @click="closeViewer" />
        </q-card-section>

        <q-card-section class="viewer-body q-pa-none">
          <div v-if="viewerLoading" class="text-center q-pa-xl text-grey">
            <q-spinner size="40px" color="primary" /><br />불러오는 중...
          </div>
          <iframe
            v-else-if="viewerPdfUrl"
            :src="viewerPdfUrl"
            class="viewer-iframe"
          />
          <div v-else-if="viewerExcelHtml" class="viewer-excel q-pa-md" v-html="viewerExcelHtml" />
          <div v-else-if="viewerText" class="viewer-text q-pa-md">
            <pre class="viewer-pre">{{ viewerText }}</pre>
          </div>
          <div v-else-if="!viewerLoading" class="text-center q-pa-xl text-grey">
            <q-icon name="insert_drive_file" size="64px" color="grey-4" /><br />
            미리보기를 지원하지 않는 파일입니다.<br />
            다운로드 버튼을 눌러 파일을 확인하세요.
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- 파일 수정 다이얼로그 -->
    <q-dialog v-model="editDialog">
      <q-card style="min-width:360px">
        <q-card-section>
          <div class="text-h6">파일 수정</div>
        </q-card-section>
        <q-card-section class="q-pt-none q-gutter-sm">
          <q-input
            v-model="editName"
            label="파일명"
            dense outlined
            :rules="[(v) => !!v || '파일명을 입력하세요.']"
          />
          <q-select
            v-model="editFolderId"
            :options="folderOptions"
            label="폴더"
            dense outlined
            emit-value
            map-options
            clearable
            :display-value="editFolderId ? folderOptions.find(o => o.value === editFolderId)?.label : '루트 (폴더 없음)'"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="editDialog = false" />
          <q-btn unelevated color="primary" label="저장" :loading="editSaving" @click="void doEdit()" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 삭제 확인 -->
    <q-dialog v-model="deleteDialog">
      <q-card style="min-width:320px">
        <q-card-section>
          <div class="text-h6">삭제 확인</div>
          <div class="q-mt-sm">{{ deleteTarget?.name }}을(를) 삭제하시겠습니까?</div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="deleteDialog = false" />
          <q-btn unelevated color="negative" label="삭제" :loading="deleting" @click="void doDelete()" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import * as XLSX from 'xlsx'
import { documentService, type DocFile, type DocFolder } from 'src/services/documents'

const $q = useQuasar()
const auth = useAuthStore()
const isAdmin = computed(() => !!auth.me?.isAdmin)

// ── 폴더 트리 ────────────────────────────────────────────────────────────────
const folders = ref<DocFolder[]>([])
const selectedFolderId = ref<string | null>(null)

const flatFolderTree = computed(() => {
  const result: Array<DocFolder & { depth: number }> = []
  function visit(parentId: string | null, depth: number) {
    folders.value
      .filter((f) => f.parentId === parentId)
      .forEach((f) => {
        result.push({ ...f, depth })
        visit(f.id, depth + 1)
      })
  }
  visit(null, 0)
  return result
})

const childFolders = computed(() =>
  folders.value.filter((f) => f.parentId === selectedFolderId.value)
)

const breadcrumb = computed(() => {
  const crumbs: DocFolder[] = []
  let id = selectedFolderId.value
  while (id) {
    const f = folders.value.find((x) => x.id === id)
    if (!f) break
    crumbs.unshift(f)
    id = f.parentId
  }
  return crumbs
})


function selectFolder(id: string | null) {
  selectedFolderId.value = id
  void loadFiles()
}

async function loadFolders() {
  try {
    folders.value = await documentService.getFolders()
  } catch { /* ignore */ }
}

// ── 파일 목록 ────────────────────────────────────────────────────────────────
const currentFiles = ref<DocFile[]>([])
const filesLoading = ref(false)

async function loadFiles() {
  filesLoading.value = true
  try {
    if (selectedFolderId.value === null) {
      currentFiles.value = await documentService.getRootFiles()
    } else {
      currentFiles.value = await documentService.getFilesInFolder(selectedFolderId.value)
    }
  } catch {
    $q.notify({ type: 'negative', message: '파일 목록을 불러오지 못했습니다.' })
  } finally {
    filesLoading.value = false
  }
}

// ── 검색 ─────────────────────────────────────────────────────────────────────
const searchQuery = ref('')
const searchResults = ref<DocFile[]>([])
const searchLoading = ref(false)
const isSearching = computed(() => searchQuery.value.trim().length > 0)

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) return
  searchTimer = setTimeout(() => { void doSearch() }, 400)
}

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  searchLoading.value = true
  try {
    searchResults.value = await documentService.search(q)
  } catch {
    $q.notify({ type: 'negative', message: '검색에 실패했습니다.' })
  } finally {
    searchLoading.value = false
  }
}

// ── 업로드 ────────────────────────────────────────────────────────────────────
const uploadInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

function triggerUpload() {
  uploadInput.value?.click()
}

async function onFolderSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const files: File[] = []
  const paths: string[] = []
  for (const f of Array.from(input.files)) {
    files.push(f)
    paths.push((f as File & { webkitRelativePath: string }).webkitRelativePath || f.name)
  }

  uploading.value = true
  try {
    const result = await documentService.uploadFiles(files, paths)
    $q.notify({ type: 'positive', message: `${result.uploaded}개 파일 업로드 완료` })
    await loadFolders()

    // 업로드된 최상위 폴더로 자동 이동
    const topFolder = paths[0]?.split('/')[0]
    if (topFolder) {
      const found = folders.value.find((f) => f.name === topFolder && f.parentId === null)
      if (found) {
        selectedFolderId.value = found.id
      }
    }
    await loadFiles()
  } catch {
    $q.notify({ type: 'negative', message: '업로드에 실패했습니다.' })
  } finally {
    uploading.value = false
    input.value = ''
  }
}

// ── 파일 뷰어 ─────────────────────────────────────────────────────────────────
const viewerOpen = ref(false)
const viewerFile = ref<DocFile | null>(null)
const viewerPdfUrl = ref<string | null>(null)
const viewerExcelHtml = ref<string | null>(null)
const viewerText = ref<string | null>(null)
const viewerLoading = ref(false)
const viewerDownloadUrl = ref('')

async function openFile(f: DocFile) {
  viewerFile.value = f
  viewerPdfUrl.value = null
  viewerExcelHtml.value = null
  viewerText.value = null
  viewerOpen.value = true
  viewerLoading.value = true
  viewerDownloadUrl.value = documentService.getDownloadUrl(f.id)

  const ext = f.extension?.toLowerCase()

  try {
    if (ext === 'pdf') {
      viewerPdfUrl.value = documentService.getContentUrl(f.id, auth.token ?? '')
    } else if (ext === 'xlsx' || ext === 'xls') {
      const contentUrl = documentService.getContentUrl(f.id, auth.token ?? '')
      const fetchResp = await fetch(contentUrl)
      if (!fetchResp.ok) throw new Error(`HTTP ${fetchResp.status}`)
      const arrayBuffer = await fetchResp.arrayBuffer()
      const wb = XLSX.read(arrayBuffer, { type: 'array' })
      let html = ''
      for (const sheetName of wb.SheetNames) {
        const ws = wb.Sheets[sheetName]
        if (!ws) continue
        html += `<div class="excel-sheet-name">${sheetName}</div>`
        html += XLSX.utils.sheet_to_html(ws, { id: `sheet-${sheetName}` })
      }
      viewerExcelHtml.value = html
    } else {
      const meta = await documentService.getFileMeta(f.id)
      viewerText.value = meta.textContent ?? null
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: `미리보기 로드 실패: ${String(err)}` })
  } finally {
    viewerLoading.value = false
  }
}

function closeViewer() {
  viewerOpen.value = false
  viewerPdfUrl.value = null
  viewerExcelHtml.value = null
}

// ── 수정 ─────────────────────────────────────────────────────────────────────
const editDialog = ref(false)
const editTarget = ref<DocFile | null>(null)
const editName = ref('')
const editFolderId = ref<string | null>(null)
const editSaving = ref(false)

const folderOptions = computed(() =>
  folders.value.map((f) => ({ label: f.name, value: f.id }))
)

function openEdit(f: DocFile) {
  editTarget.value = f
  editName.value = f.name
  editFolderId.value = f.folderId ?? null
  editDialog.value = true
}

async function doEdit() {
  if (!editTarget.value || !editName.value.trim()) return
  editSaving.value = true
  try {
    await documentService.updateFile(editTarget.value.id, {
      name: editName.value.trim(),
      folder_id: editFolderId.value,
    })
    $q.notify({ type: 'positive', message: '수정되었습니다.' })
    editDialog.value = false
    // 뷰어에 열려있으면 이름 갱신
    if (viewerFile.value?.id === editTarget.value.id) {
      viewerFile.value = { ...viewerFile.value, name: editName.value.trim(), folderId: editFolderId.value }
    }
    await loadFolders()
    await loadFiles()
  } catch {
    $q.notify({ type: 'negative', message: '수정에 실패했습니다.' })
  } finally {
    editSaving.value = false
  }
}

// ── 삭제 ─────────────────────────────────────────────────────────────────────
const deleteDialog = ref(false)
const deleteTarget = ref<{ id: string; name: string; type: 'file' | 'folder' } | null>(null)
const deleting = ref(false)

function confirmDeleteFile(f: DocFile) {
  deleteTarget.value = { id: f.id, name: f.name, type: 'file' }
  deleteDialog.value = true
}

function confirmDeleteFolder(f: DocFolder & { depth?: number }) {
  deleteTarget.value = { id: f.id, name: f.name, type: 'folder' }
  deleteDialog.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    if (deleteTarget.value.type === 'file') {
      await documentService.deleteFile(deleteTarget.value.id)
    } else {
      await documentService.deleteFolder(deleteTarget.value.id)
    }
    $q.notify({ type: 'positive', message: '삭제되었습니다.' })
    deleteDialog.value = false
    await loadFolders()
    await loadFiles()
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '삭제 실패'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    deleting.value = false
  }
}

// ── 유틸 ──────────────────────────────────────────────────────────────────────
function fileIcon(ext: string): string {
  switch (ext?.toLowerCase()) {
    case 'pdf': return 'picture_as_pdf'
    case 'xlsx': case 'xls': return 'table_chart'
    case 'hwp': return 'article'
    case 'docx': case 'doc': return 'description'
    case 'txt': case 'md': return 'text_snippet'
    default: return 'insert_drive_file'
  }
}

function fileColor(ext: string): string {
  switch (ext?.toLowerCase()) {
    case 'pdf': return 'red-7'
    case 'xlsx': case 'xls': return 'green-7'
    case 'hwp': return 'blue-7'
    case 'docx': case 'doc': return 'indigo-6'
    default: return 'grey-6'
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(() => {
  void loadFolders()
  void loadFiles()
})
</script>

<style scoped>
.doc-page {
  background: #f4f6f9;
  min-height: 100vh;
}

.doc-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  align-items: start;
}

/* 폴더 패널 */
.folder-panel {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8edf5;
  padding: 12px 8px;
  min-height: 300px;
}

.folder-panel-title {
  padding: 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.folder-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #37474f;
  transition: background 0.15s;
  position: relative;
}

.folder-item:hover { background: #f0f4ff; }
.folder-item--active { background: #e8eeff; color: #1a237e; font-weight: 600; }

/* 파일 패널 */
.file-panel {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8edf5;
  padding: 16px;
  min-height: 300px;
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
}

.file-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px 12px;
  border-radius: 10px;
  border: 1px solid #eee;
  cursor: pointer;
  position: relative;
  transition: box-shadow 0.15s, border-color 0.15s;
  text-align: center;
}

.file-card:hover {
  border-color: #90caf9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.file-card--folder {
  background: #fffde7;
  border-color: #ffe082;
}
.file-card--folder:hover {
  border-color: #ffb300;
}

.file-breadcrumb {
  font-size: 13px;
  color: #546e7a;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.breadcrumb-item {
  color: #1a237e;
  font-weight: 500;
}
.breadcrumb-item:hover { text-decoration: underline; }

.file-card-name {
  font-size: 12px;
  font-weight: 600;
  color: #263238;
  margin-top: 8px;
  word-break: break-all;
  line-height: 1.3;
  max-height: 3.9em;
  overflow: hidden;
}

.file-card-meta { font-size: 11px; margin-top: 4px; }

.file-card-actions {
  position: absolute;
  top: 4px;
  right: 2px;
  display: flex;
  gap: 0;
  opacity: 0;
  transition: opacity 0.15s;
}
.file-card:hover .file-card-actions { opacity: 1; }

/* 검색 결과 */
.search-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-item {
  display: flex;
  align-items: flex-start;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e8edf5;
  padding: 14px 16px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.search-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }

.search-item-body { flex: 1; min-width: 0; }

.search-item-name { font-size: 14px; font-weight: 600; color: #1a237e; }

.search-item-snippet {
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.search-item-actions { flex-shrink: 0; }

/* 뷰어 */
.viewer-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.viewer-header {
  border-bottom: 1px solid #e8edf5;
  padding: 12px 16px;
  flex-shrink: 0;
}

.viewer-body {
  flex: 1;
  overflow: hidden;
}

.viewer-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

.viewer-text { height: 100%; overflow-y: auto; }

.viewer-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.8;
  font-family: 'Noto Sans KR', sans-serif;
  color: #263238;
  margin: 0;
}

/* 엑셀 뷰어 */
.viewer-excel {
  height: 100%;
  overflow: auto;
}

.viewer-excel :deep(.excel-sheet-name) {
  font-size: 13px;
  font-weight: 700;
  color: #1a237e;
  padding: 12px 4px 6px;
  border-bottom: 2px solid #3f51b5;
  margin-bottom: 8px;
}

.viewer-excel :deep(table) {
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 32px;
  min-width: 100%;
}

.viewer-excel :deep(td),
.viewer-excel :deep(th) {
  border: 1px solid #ddd;
  padding: 5px 10px;
  white-space: nowrap;
  color: #263238;
}

.viewer-excel :deep(tr:first-child td),
.viewer-excel :deep(th) {
  background: #e8eaf6;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.viewer-excel :deep(tr:nth-child(even)) {
  background: #f5f5f5;
}
</style>
