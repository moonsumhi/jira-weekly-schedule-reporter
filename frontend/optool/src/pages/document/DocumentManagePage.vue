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
        unelevated color="secondary" icon="create_new_folder" label="폴더 추가"
        @click="openCreateFolder"
      />
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
              @click.stop="confirmDeleteFile(f)">
              <q-tooltip>삭제</q-tooltip>
            </q-btn>
          </div>
        </div>
      </div>
    </template>

    <!-- 폴더 + 파일 브라우저 -->
    <template v-else>
      <div class="doc-layout">

        <!-- 좌측 폴더 트리 (scoped 모드에서는 숨김) -->
        <div v-if="!isScopedMode" class="folder-panel">
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
              flat dense round icon="edit" color="grey-6" size="xs"
              class="folder-del-btn"
              @click.stop="openRenameFolder(f)"
            >
              <q-tooltip>이름 변경</q-tooltip>
            </q-btn>
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
            <!-- scoped 모드: 루트 대신 scope 폴더명 표시, 루트로 이동 불가 -->
            <span v-if="isScopedMode" class="breadcrumb-item cursor-pointer" @click="selectFolder(scopeRootId)">{{ activeScopeFolder }}</span>
            <span v-else class="breadcrumb-item cursor-pointer" @click="selectFolder(null)">루트</span>
            <span v-for="b in scopedBreadcrumb" :key="b.id">
              <q-icon name="chevron_right" size="14px" class="q-mx-xs text-grey-5" />
              <span class="breadcrumb-item cursor-pointer" @click="selectFolder(b.id)">{{ b.name }}</span>
            </span>
          </div>

          <div v-if="isScopedMode && !scopeRootId" class="text-center q-pa-xl text-grey-5">
            <q-icon name="folder_off" size="48px" /><br />
            <div class="q-mt-sm">폴더 <strong>{{ activeScopeFolder }}</strong>를 먼저 만들거나 업로드해주세요.</div>
          </div>
          <div v-else-if="filesLoading" class="text-center q-pa-xl text-grey">불러오는 중...</div>
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
              <div class="file-card-name">
                {{ f.name }}
                <q-tooltip anchor="top middle" self="bottom middle" :delay="400">{{ f.name }}</q-tooltip>
              </div>
              <div class="file-card-meta text-grey-6">폴더</div>
              <div class="file-card-actions">
                <q-btn flat dense round icon="edit" color="grey-7" size="xs" @click.stop="openRenameFolder(f)">
                  <q-tooltip>이름 변경</q-tooltip>
                </q-btn>
                <q-btn v-if="isAdmin" flat dense round icon="delete" color="negative" size="xs" @click.stop="confirmDeleteFolder(f)">
                  <q-tooltip>삭제</q-tooltip>
                </q-btn>
              </div>
            </div>
            <div
              v-for="f in currentFiles"
              :key="f.id"
              class="file-card"
              @click="void openFile(f)"
            >
              <q-icon :name="fileIcon(f.extension)" size="36px" :color="fileColor(f.extension)" />
              <q-badge v-if="f.convertedFrom === 'hwp'" color="orange-3" text-color="orange-9" label="변환됨" class="q-mt-xs" style="font-size:9px" />
              <div class="file-card-name">
                {{ f.name }}
                <q-tooltip anchor="top middle" self="bottom middle" :delay="400" max-width="320px">
                  <div class="text-weight-bold">{{ f.name }}</div>
                  <div class="text-caption">{{ formatSize(f.size) }} · {{ f.extension?.toUpperCase() }}</div>
                </q-tooltip>
              </div>
              <div class="file-card-meta text-grey-6">{{ formatSize(f.size) }}</div>
              <div class="file-card-actions">
                <q-btn flat dense round icon="upload" color="orange-7" size="xs" @click.stop="triggerReplaceFor(f)">
                  <q-tooltip>파일 교체</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="edit" color="grey-7" size="xs" @click.stop="openEdit(f)">
                  <q-tooltip>이름/폴더 수정</q-tooltip>
                </q-btn>
                <q-btn v-if="isAdmin" flat dense round icon="delete" color="negative" size="xs" @click.stop="confirmDeleteFile(f)">
                  <q-tooltip>삭제</q-tooltip>
                </q-btn>
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
          <q-chip v-if="viewerFile?.convertedFrom === 'hwp'" dense color="orange-2" text-color="orange-9" icon="swap_horiz" class="q-ml-sm" style="font-size:11px">
            HWP에서 변환됨
          </q-chip>
          <q-space />
          <!-- 편집 모드일 때 -->
          <template v-if="editMode">
            <q-btn flat dense round icon="save" color="positive" :loading="contentSaving" @click="void saveEdit()">
              <q-tooltip>저장</q-tooltip>
            </q-btn>
            <q-btn flat dense round icon="cancel" color="grey-7" @click="cancelEdit">
              <q-tooltip>취소</q-tooltip>
            </q-btn>
          </template>
          <!-- 일반 모드 -->
          <template v-else>
            <q-btn v-if="isHwpFile" flat dense round icon="swap_horiz" color="orange-7" :loading="converting" @click="void convertHwpToDocx()">
              <q-tooltip>DOCX로 변환</q-tooltip>
            </q-btn>
            <q-btn v-if="canEdit" flat dense round icon="draw" color="teal" :loading="editLoading" @click="void enterEditMode()">
              <q-tooltip>편집</q-tooltip>
            </q-btn>
            <q-btn flat dense round icon="download" color="primary" @click="downloadFile">
              <q-tooltip>다운로드</q-tooltip>
            </q-btn>
            <q-btn flat dense round icon="edit" color="grey-7" @click="openEdit(viewerFile!)">
              <q-tooltip>파일명 수정</q-tooltip>
            </q-btn>
            <q-btn flat dense round icon="upload" color="orange-7" :loading="replacing" @click="triggerReplace">
              <q-tooltip>파일 교체</q-tooltip>
            </q-btn>
          </template>
          <input ref="replaceInput" type="file" style="display:none" @change="(e) => { void onReplaceSelected(e) }" />
          <q-btn flat dense round icon="close" @click="closeViewer" />
        </q-card-section>

        <q-card-section class="viewer-body q-pa-none">
          <!-- 편집 모드 로딩 -->
          <div v-if="editLoading" class="text-center q-pa-xl text-grey">
            <q-spinner size="40px" color="teal" /><br />편집기 로딩 중...
          </div>

          <!-- 텍스트 편집기 (txt/md/csv) -->
          <div v-else-if="editMode && isTextFile" class="viewer-editor-wrap">
            <textarea v-model="editorText" class="text-editor" spellcheck="false" />
          </div>

          <!-- DOCX 편집기 -->
          <div v-else-if="editMode && isDocxFile" class="viewer-editor-wrap">
            <div class="editor-toolbar">
              <q-btn flat dense size="sm" label="B" @click="execCmd('bold')" style="font-weight:bold" />
              <q-btn flat dense size="sm" label="I" @click="execCmd('italic')" style="font-style:italic" />
              <q-btn flat dense size="sm" label="U" @click="execCmd('underline')" style="text-decoration:underline" />
              <q-separator vertical class="q-mx-xs" />
              <q-btn flat dense size="sm" icon="format_list_bulleted" @click="execCmd('insertUnorderedList')" />
              <q-btn flat dense size="sm" icon="format_list_numbered" @click="execCmd('insertOrderedList')" />
              <q-separator vertical class="q-mx-xs" />
              <q-btn flat dense size="sm" icon="format_align_left" @click="execCmd('justifyLeft')" />
              <q-btn flat dense size="sm" icon="format_align_center" @click="execCmd('justifyCenter')" />
              <q-btn flat dense size="sm" icon="format_align_right" @click="execCmd('justifyRight')" />
            </div>
            <div ref="editorRef" contenteditable="true" class="html-editor" />
          </div>

          <!-- Excel 편집기 -->
          <div v-else-if="editMode && isXlsxFile" class="viewer-editor-wrap">
            <div class="xlsx-editor-wrap">
              <table class="xlsx-editor-table">
                <tbody>
                  <tr v-for="(row, ri) in xlsxEditData" :key="ri">
                    <td class="xlsx-row-num">{{ ri + 1 }}</td>
                    <td v-for="ci in xlsxMaxCols" :key="ci" class="xlsx-cell-td">
                      <input
                        :value="row[ci - 1] ?? ''"
                        class="xlsx-cell-input"
                        @input="(e) => { if (!xlsxEditData[ri]) xlsxEditData[ri] = []; xlsxEditData[ri][ci - 1] = (e.target as HTMLInputElement).value }"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
              <q-btn flat dense icon="add" label="행 추가" size="sm" class="q-mt-sm" @click="xlsxEditData.push(Array(xlsxMaxCols).fill(''))" />
            </div>
          </div>

          <!-- 미리보기 모드 (기존) -->
          <template v-else>
            <div v-if="viewerLoading" class="text-center q-pa-xl text-grey">
              <q-spinner size="40px" color="primary" /><br />불러오는 중...
            </div>
            <iframe v-else-if="viewerPdfUrl" :src="viewerPdfUrl" class="viewer-iframe" />
            <div v-else-if="viewerImageUrl" class="viewer-image">
              <img :src="viewerImageUrl" class="viewer-img" alt="" />
            </div>
            <div v-else-if="viewerExcelHtml" class="viewer-excel q-pa-md" v-html="viewerExcelHtml" />
            <div v-else-if="viewerText" class="viewer-text q-pa-md">
              <pre class="viewer-pre">{{ viewerText }}</pre>
            </div>
            <div v-else-if="!viewerLoading" class="text-center q-pa-xl text-grey">
              <q-icon name="insert_drive_file" size="64px" color="grey-4" /><br />
              미리보기를 지원하지 않는 파일입니다.<br />
              다운로드 버튼을 눌러 파일을 확인하세요.
            </div>
          </template>
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

    <!-- 폴더 추가 다이얼로그 -->
    <q-dialog v-model="createFolderDialog">
      <q-card style="min-width:360px">
        <q-card-section>
          <div class="text-h6">폴더 추가</div>
        </q-card-section>
        <q-card-section class="q-pt-none q-gutter-sm">
          <q-input
            v-model="newFolderName"
            label="폴더명"
            dense outlined autofocus
            :rules="[(v) => !!v || '폴더명을 입력하세요.']"
            @keyup.enter="void doCreateFolder()"
          />
          <q-select
            v-model="newFolderParentId"
            :options="[{ label: '루트 (최상위)', value: null }, ...folderOptions]"
            label="상위 폴더"
            dense outlined
            emit-value
            map-options
            :display-value="newFolderParentId ? folderOptions.find(o => o.value === newFolderParentId)?.label : '루트 (최상위)'"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="createFolderDialog = false" />
          <q-btn unelevated color="secondary" label="추가" :loading="creatingFolder" @click="void doCreateFolder()" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 폴더 이름 변경 다이얼로그 -->
    <q-dialog v-model="renameFolderDialog">
      <q-card style="min-width:360px">
        <q-card-section>
          <div class="text-h6">폴더 이름 변경</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input
            v-model="renameFolderName"
            label="폴더명"
            dense outlined autofocus
            :rules="[(v) => !!v || '폴더명을 입력하세요.']"
            @keyup.enter="void doRenameFolder()"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="renameFolderDialog = false" />
          <q-btn unelevated color="primary" label="저장" :loading="renamingFolder" @click="void doRenameFolder()" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import * as XLSX from 'xlsx'
import { documentService, type DocFile, type DocFolder } from 'src/services/documents'

const props = defineProps<{ scopeFolder?: string }>()

const $q = useQuasar()
const auth = useAuthStore()
const route = useRoute()
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

// scoped 모드: scope root 폴더 아래의 경로만 표시
const scopedBreadcrumb = computed(() => {
  if (!isScopedMode.value || !scopeRootId.value) return breadcrumb.value
  return breadcrumb.value.filter(b => b.id !== scopeRootId.value)
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

// ── 폴더 추가 ─────────────────────────────────────────────────────────────────
const createFolderDialog = ref(false)
const newFolderName = ref('')
const newFolderParentId = ref<string | null>(null)
const creatingFolder = ref(false)

function openCreateFolder() {
  newFolderName.value = ''
  newFolderParentId.value = selectedFolderId.value
  createFolderDialog.value = true
}

async function doCreateFolder() {
  if (!newFolderName.value.trim()) return
  creatingFolder.value = true
  try {
    const folder = await documentService.createFolder(newFolderName.value.trim(), newFolderParentId.value)
    folders.value.push(folder)
    $q.notify({ type: 'positive', message: '폴더가 생성되었습니다.' })
    createFolderDialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: '폴더 생성에 실패했습니다.' })
  } finally {
    creatingFolder.value = false
  }
}

// ── 폴더 이름 변경 ────────────────────────────────────────────────────────────
const renameFolderDialog = ref(false)
const renameFolderTarget = ref<DocFolder | null>(null)
const renameFolderName = ref('')
const renamingFolder = ref(false)

function openRenameFolder(f: DocFolder) {
  renameFolderTarget.value = f
  renameFolderName.value = f.name
  renameFolderDialog.value = true
}

async function doRenameFolder() {
  if (!renameFolderTarget.value || !renameFolderName.value.trim()) return
  renamingFolder.value = true
  try {
    const updated = await documentService.updateFolder(renameFolderTarget.value.id, renameFolderName.value.trim())
    const target = folders.value.find((f) => f.id === updated.id)
    if (target) target.name = updated.name
    $q.notify({ type: 'positive', message: '폴더 이름이 변경되었습니다.' })
    renameFolderDialog.value = false
  } catch {
    $q.notify({ type: 'negative', message: '이름 변경에 실패했습니다.' })
  } finally {
    renamingFolder.value = false
  }
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
const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'])

const viewerOpen = ref(false)
const viewerFile = ref<DocFile | null>(null)
const viewerPdfUrl = ref<string | null>(null)
const viewerImageUrl = ref<string | null>(null)
const viewerExcelHtml = ref<string | null>(null)
const viewerText = ref<string | null>(null)
const viewerLoading = ref(false)
const viewerDownloadUrl = ref('')

async function openFile(f: DocFile) {
  viewerFile.value = f
  viewerPdfUrl.value = null
  viewerImageUrl.value = null
  viewerExcelHtml.value = null
  viewerText.value = null
  viewerOpen.value = true
  viewerLoading.value = true
  viewerDownloadUrl.value = documentService.getDownloadUrl(f.id)

  const ext = f.extension?.toLowerCase()

  try {
    if (ext === 'pdf') {
      viewerPdfUrl.value = documentService.getContentUrl(f.id, auth.token ?? '')
    } else if (IMAGE_EXTS.has(ext ?? '')) {
      viewerImageUrl.value = documentService.getContentUrl(f.id, auth.token ?? '')
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
    } else if (ext === 'hwp') {
      // HWP → hwp5html로 변환한 HTML을 iframe으로 표시
      viewerPdfUrl.value = documentService.getHwpPreviewUrl(f.id, auth.token ?? '')
    } else {
      // DOCX, TXT, MD 등 텍스트 추출
      const meta = await documentService.getFileMeta(f.id)
      viewerText.value = meta.textContent ?? null
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: `미리보기 로드 실패: ${String(err)}` })
  } finally {
    viewerLoading.value = false
  }
}

function downloadFile() {
  if (!viewerFile.value) return
  const url = documentService.getContentUrl(viewerFile.value.id, auth.token ?? '')
  const a = document.createElement('a')
  a.href = url
  a.download = viewerFile.value.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function closeViewer() {
  viewerOpen.value = false
  viewerPdfUrl.value = null
  viewerImageUrl.value = null
  viewerExcelHtml.value = null
  editMode.value = false
}

// ── 편집 모드 ─────────────────────────────────────────────────────────────────
const TEXT_EXTS = new Set(['txt', 'md', 'csv'])
const DOCX_EXTS = new Set(['docx'])
const XLSX_EDIT_EXTS = new Set(['xlsx', 'xls'])

const editMode = ref(false)
const editLoading = ref(false)
const contentSaving = ref(false)
const editorText = ref('')
const editorHtml = ref('')
const editorRef = ref<HTMLDivElement | null>(null)
const xlsxEditData = ref<string[][]>([])
const xlsxSheetName = ref('Sheet1')
const converting = ref(false)

const isTextFile = computed(() => TEXT_EXTS.has(viewerFile.value?.extension?.toLowerCase() ?? ''))
const isDocxFile = computed(() => DOCX_EXTS.has(viewerFile.value?.extension?.toLowerCase() ?? ''))
const isXlsxFile = computed(() => XLSX_EDIT_EXTS.has(viewerFile.value?.extension?.toLowerCase() ?? ''))
const isHwpFile = computed(() => viewerFile.value?.extension?.toLowerCase() === 'hwp')
const canEdit = computed(() => isTextFile.value || isDocxFile.value || isXlsxFile.value)

const xlsxMaxCols = computed(() =>
  xlsxEditData.value.reduce((m, r) => Math.max(m, r.length), 1)
)

watch([editMode, isDocxFile], async ([mode, isDocx]) => {
  if (mode && isDocx) {
    await nextTick()
    if (editorRef.value) editorRef.value.innerHTML = editorHtml.value
  }
})

async function enterEditMode() {
  if (!viewerFile.value) return
  editLoading.value = true
  try {
    const ext = viewerFile.value.extension?.toLowerCase() ?? ''
    if (TEXT_EXTS.has(ext) || DOCX_EXTS.has(ext)) {
      const res = await documentService.getEditContent(viewerFile.value.id)
      if (res.contentType === 'text') {
        editorText.value = res.content
      } else {
        editorHtml.value = res.content
      }
    } else if (XLSX_EDIT_EXTS.has(ext)) {
      const url = documentService.getContentUrl(viewerFile.value.id, auth.token ?? '')
      const resp = await fetch(url)
      const buf = await resp.arrayBuffer()
      const wb = XLSX.read(buf, { type: 'array' })
      const sn = wb.SheetNames[0] ?? 'Sheet1'
      xlsxSheetName.value = sn
      const ws = wb.Sheets[sn]
      xlsxEditData.value = ws ? XLSX.utils.sheet_to_json<string[]>(ws, { header: 1, defval: '' }) : [['']]
    }
    editMode.value = true
  } catch (err) {
    $q.notify({ type: 'negative', message: `편집 데이터 로드 실패: ${String(err)}` })
  } finally {
    editLoading.value = false
  }
}

function cancelEdit() {
  editMode.value = false
}

async function saveEdit() {
  if (!viewerFile.value) return
  contentSaving.value = true
  try {
    const ext = viewerFile.value.extension?.toLowerCase() ?? ''
    if (TEXT_EXTS.has(ext)) {
      await documentService.saveEditContent(viewerFile.value.id, 'text', editorText.value)
      viewerText.value = editorText.value
    } else if (DOCX_EXTS.has(ext)) {
      const html = editorRef.value?.innerHTML ?? editorHtml.value
      await documentService.saveEditContent(viewerFile.value.id, 'html', html)
    } else if (XLSX_EDIT_EXTS.has(ext)) {
      const wb = XLSX.utils.book_new()
      const ws = XLSX.utils.aoa_to_sheet(xlsxEditData.value)
      XLSX.utils.book_append_sheet(wb, ws, xlsxSheetName.value)
      const buffer = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
      const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const file = new File([blob], viewerFile.value.name)
      const updated = await documentService.replaceFile(viewerFile.value.id, file)
      viewerFile.value = updated
      // 미리보기 갱신
      const wb2 = XLSX.read(buffer, { type: 'array' })
      let html = ''
      for (const sn of wb2.SheetNames) {
        const ws2 = wb2.Sheets[sn]
        if (!ws2) continue
        html += `<div class="excel-sheet-name">${sn}</div>`
        html += XLSX.utils.sheet_to_html(ws2, { id: `sheet-${sn}` })
      }
      viewerExcelHtml.value = html
    }
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
    editMode.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: `저장 실패: ${String(err)}` })
  } finally {
    contentSaving.value = false
  }
}

function execCmd(cmd: string) {
  document.execCommand(cmd, false)
  editorRef.value?.focus()
}

async function convertHwpToDocx() {
  if (!viewerFile.value) return
  converting.value = true
  try {
    const newFile = await documentService.convertToDocx(viewerFile.value.id)
    currentFiles.value.unshift(newFile)
    $q.notify({ type: 'positive', message: 'DOCX로 변환되었습니다.' })
    await openFile(newFile)
  } catch (err) {
    $q.notify({ type: 'negative', message: `변환 실패: ${String(err)}` })
  } finally {
    converting.value = false
  }
}

// ── 파일 교체 ─────────────────────────────────────────────────────────────────
const replaceInput = ref<HTMLInputElement | null>(null)
const replaceTargetId = ref<string | null>(null)
const replacing = ref(false)

function triggerReplace() {
  if (!viewerFile.value) return
  replaceTargetId.value = viewerFile.value.id
  replaceInput.value?.click()
}

function triggerReplaceFor(f: DocFile) {
  replaceTargetId.value = f.id
  replaceInput.value?.click()
}

async function onReplaceSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !replaceTargetId.value) return

  replacing.value = true
  try {
    const updated = await documentService.replaceFile(replaceTargetId.value, file)
    $q.notify({ type: 'positive', message: `"${updated.name}" 교체 완료` })
    await loadFiles()
    // 뷰어가 열려있으면 새 파일로 다시 열기
    if (viewerOpen.value && viewerFile.value?.id === replaceTargetId.value) {
      closeViewer()
      await openFile(updated)
    }
  } catch {
    $q.notify({ type: 'negative', message: '파일 교체에 실패했습니다.' })
  } finally {
    replacing.value = false
    replaceTargetId.value = null
    input.value = ''
  }
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
    case 'png': case 'jpg': case 'jpeg': case 'gif': case 'webp': case 'bmp': return 'image'
    default: return 'insert_drive_file'
  }
}

function fileColor(ext: string): string {
  switch (ext?.toLowerCase()) {
    case 'pdf': return 'red-7'
    case 'xlsx': case 'xls': return 'green-7'
    case 'hwp': return 'blue-7'
    case 'docx': case 'doc': return 'indigo-6'
    case 'png': case 'jpg': case 'jpeg': case 'gif': case 'webp': case 'bmp': return 'teal-6'
    default: return 'grey-6'
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// scopeFolder prop 또는 ?folder= 쿼리로 특정 폴더 자동 선택
const activeScopeFolder = computed(() => props.scopeFolder ?? (route.query['folder'] as string | undefined))

// scoped 모드: 좌측 폴더 트리 숨김, 해당 폴더 하위만 표시
const isScopedMode = computed(() => !!activeScopeFolder.value)
const scopeRootId = ref<string | null>(null)


onMounted(async () => {
  await loadFolders()
  const name = activeScopeFolder.value
  if (name) {
    const match = folders.value.find((f) => f.name === name)
    if (match) {
      scopeRootId.value = match.id
      selectFolder(match.id)
      return
    }
  }
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

/* 이미지 뷰어 */
.viewer-image {
  height: 100%;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px;
  background: #f0f0f0;
}

.viewer-img {
  max-width: 100%;
  height: auto;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  border-radius: 4px;
}

.viewer-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.8;
  font-family: 'Noto Sans KR', sans-serif;
  color: #263238;
  margin: 0;
}

/* ── 편집기 ── */
.viewer-editor-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.text-editor {
  flex: 1;
  width: 100%;
  height: 100%;
  padding: 16px;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Noto Sans KR', monospace;
  font-size: 14px;
  line-height: 1.8;
  color: #263238;
  background: #fafafa;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  gap: 2px;
  flex-shrink: 0;
}

.html-editor {
  flex: 1;
  padding: 20px 32px;
  overflow-y: auto;
  outline: none;
  font-family: 'Noto Sans KR', sans-serif;
  font-size: 14px;
  line-height: 1.9;
  color: #263238;
  background: #fff;
}
.html-editor:focus { background: #fefefe; }

.xlsx-editor-wrap {
  flex: 1;
  overflow: auto;
  padding: 12px;
  background: #fafafa;
}

.xlsx-editor-table {
  border-collapse: collapse;
  font-size: 13px;
}

.xlsx-row-num {
  padding: 2px 8px;
  color: #999;
  background: #f0f0f0;
  border: 1px solid #ddd;
  text-align: center;
  font-size: 11px;
  user-select: none;
  min-width: 32px;
}

.xlsx-cell-td {
  border: 1px solid #ddd;
  padding: 0;
}

.xlsx-cell-input {
  width: 120px;
  min-width: 80px;
  padding: 4px 6px;
  border: none;
  outline: none;
  font-size: 13px;
  font-family: inherit;
  background: transparent;
}
.xlsx-cell-input:focus {
  background: #e8f0fe;
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
