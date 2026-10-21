<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm no-wrap">
      <div class="text-h6" style="flex-shrink: 0;">{{ boardTitle }}</div>
      <q-btn icon="note_add" label="새 문서" color="primary" style="flex-shrink: 0; margin-left: 15px;" @click="openWrite" />
      <q-space />
      <q-checkbox
        v-model="showChildDocuments"
        label="하위문서 표시"
        dense
        style="flex-shrink: 0"
      />
      <q-select
        v-model="categoryFilter" dense outlined clearable
        :options="categoryOptions" emit-value map-options
        label="카테고리" style="flex: 0 0 160px"
      />
      <q-input
        v-model="filterText" dense outlined clearable
        placeholder="문서 제목 / 내용 / 작성자 검색"
        style="flex: 0 1 500px; min-width: 150px"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>
    </div>

    <q-table
      v-if="ready"
      :rows="hierarchicalPosts"
      :columns="columns"
      :filter="tableFilter"
      :filter-method="filterPosts"
      :sort-method="hierarchySort"
      row-key="id"
      flat
      bordered
      :loading="loading"
      v-model:pagination="pagination"
      :rows-per-page-options="[15, 30, 50, 100, 0]"
      no-data-label="문서가 없습니다"
      @row-click="(_, row) => openPost(row)"
    >
      <template #body-cell-title="{ row }">
        <q-td class="cursor-pointer">
          <div class="board-document-title" :style="{ paddingLeft: `${Math.min(hierarchyDepth(row), 4) * 18}px` }">
            <div class="board-document-title-main">
              <q-icon v-if="row.parentId" name="subdirectory_arrow_right" size="16px" color="grey-6" class="q-mr-xs" />
              <q-icon name="description" size="17px" class="q-mr-xs" />
              <span
                v-if="row.category"
                class="text-primary"
                :class="{ 'text-weight-bold': categoryFilter === row.category }"
                @click.stop="toggleCategoryFilter(row.category)"
              >[{{ row.category }}]</span>
              <span class="board-document-title-text">{{ row.title }}</span>
            </div>
            <div v-if="parentDocument(row)" class="board-document-parent text-caption text-grey-7">
              <q-icon name="subdirectory_arrow_right" size="13px" class="q-mr-xs" />
              상위 문서: {{ parentDocument(row)?.title }}
            </div>
          </div>
        </q-td>
      </template>
      <template #body-cell-actions="{ row }">
        <q-td @click.stop>
          <q-btn
            v-if="canEdit(row)"
            flat dense icon="edit" size="sm"
            @click="openEdit(row)"
          />
          <q-btn
            v-if="canDelete(row)"
            flat dense icon="delete" color="negative" size="sm"
            @click="confirmDelete(row)"
          />
        </q-td>
      </template>
    </q-table>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostOut } from 'src/services/boards'
import { envCategoryService } from 'src/services/envCategory'
import { useAuthStore } from 'stores/auth'
import { formatKst } from 'src/utils/time/kst'
import { readBoardListState, writeBoardListState } from 'src/utils/boardListState'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()

const boardId = ref(route.params.boardId as string)
const boardTitle = ref('')
const posts = ref<PostOut[]>([])
const postsById = computed(() => new Map(posts.value.map((post) => [post.id, post] as const)))
const loading = ref(false)
const showChildDocuments = ref(true)
const initialState = readBoardListState(boardId.value, window.sessionStorage)
const ready = ref(false)
const filterText = ref<string | null>(initialState.search)
const categoryFilter = ref<string | null>(initialState.category)
const categoryOptions = ref<{ label: string; value: string }[]>([])
const tableFilter = computed(() => `${filterText.value}||${categoryFilter.value ?? ''}`)
const pagination = ref(initialState.pagination)

function parentDocument(row: PostOut) {
  return row.parentId ? postsById.value.get(row.parentId) ?? null : null
}

function hierarchyDepth(row: PostOut) {
  let depth = 0
  let parentId = row.parentId
  const seen = new Set([row.id])
  while (parentId && !seen.has(parentId)) {
    const parent = postsById.value.get(parentId)
    if (!parent) break
    seen.add(parent.id)
    depth += 1
    parentId = parent.parentId
  }
  return depth
}

function hierarchySort(rows: readonly PostOut[], sortBy: string | null, descending: boolean) {
  const rowIds = new Set(rows.map((row) => row.id))
  const childrenByParent = new Map<string | null, PostOut[]>()
  for (const row of rows) {
    const parentId = row.parentId && rowIds.has(row.parentId) ? row.parentId : null
    const siblings = childrenByParent.get(parentId) ?? []
    siblings.push(row)
    childrenByParent.set(parentId, siblings)
  }

  const compareSiblings = (left: PostOut, right: PostOut) => {
    if (!sortBy) return 0
    let comparison = 0
    if (sortBy === 'updatedAt') {
      const leftDate = new Date(left.updatedAt ?? left.createdAt ?? 0).getTime()
      const rightDate = new Date(right.updatedAt ?? right.createdAt ?? 0).getTime()
      comparison = leftDate - rightDate
    } else {
      const leftValue = sortBy === 'title' ? left.title
        : sortBy === 'part' ? left.part
          : sortBy === 'authorName' ? left.authorName : ''
      const rightValue = sortBy === 'title' ? right.title
        : sortBy === 'part' ? right.part
          : sortBy === 'authorName' ? right.authorName : ''
      comparison = leftValue.localeCompare(rightValue, 'ko')
    }
    return descending ? -comparison : comparison
  }

  const sortedRows: PostOut[] = []
  const visited = new Set<string>()
  const visit = (parentId: string | null) => {
    const siblings = [...(childrenByParent.get(parentId) ?? [])]
    if (sortBy) siblings.sort(compareSiblings)
    for (const row of siblings) {
      if (visited.has(row.id)) continue
      visited.add(row.id)
      sortedRows.push(row)
      visit(row.id)
    }
  }
  visit(null)
  for (const row of rows) {
    if (visited.has(row.id)) continue
    visited.add(row.id)
    sortedRows.push(row)
    visit(row.id)
  }
  return sortedRows
}

const visiblePosts = computed(() => showChildDocuments.value
  ? posts.value
  : posts.value.filter((post) => !post.parentId))
const hierarchicalPosts = computed(() => hierarchySort(visiblePosts.value, null, false))

function childDocumentsPreferenceKey(userId: string | number, currentBoardId: string) {
  return `board-show-child-documents:${String(userId)}:${encodeURIComponent(currentBoardId)}`
}

function restoreChildDocumentsPreference() {
  const userId = auth.me?.id
  if (userId == null) return
  try {
    showChildDocuments.value = window.localStorage.getItem(
      childDocumentsPreferenceKey(userId, boardId.value),
    ) !== 'false'
  } catch { /* 저장소를 사용할 수 없는 환경에서는 기본 표시 상태를 유지 */ }
}

watch(() => [auth.me?.id, boardId.value] as const, restoreChildDocumentsPreference, { immediate: true })
watch(showChildDocuments, (show) => {
  const userId = auth.me?.id
  if (userId == null) return
  try {
    window.localStorage.setItem(
      childDocumentsPreferenceKey(userId, boardId.value),
      String(show),
    )
  } catch { /* 저장소를 사용할 수 없는 환경에서는 현재 화면 상태만 적용 */ }
}, { flush: 'sync' })

function rememberList() {
  if (!ready.value) return
  writeBoardListState(boardId.value, { search: filterText.value ?? '', category: categoryFilter.value, pagination: { ...pagination.value } }, window.sessionStorage)
}
watch([filterText, categoryFilter, pagination], rememberList, { deep: true, flush: 'sync' })
onBeforeRouteLeave(rememberList)

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const, classes: 'cursor-pointer', sortable: true },
  { name: 'part', label: '업무 파트', field: 'part', align: 'left' as const, sortable: true },
  { name: 'authorName', label: '작성자', field: 'authorName', align: 'left' as const, sortable: true },
  {
    name: 'updatedAt', label: '최근 수정', field: (row: PostOut) => formatDate(row.updatedAt ?? row.createdAt), align: 'center' as const,
    sortable: true,
    sort: (_a: unknown, _b: unknown, rowA: PostOut, rowB: PostOut) =>
      new Date(rowA.updatedAt ?? rowA.createdAt ?? 0).getTime() - new Date(rowB.updatedAt ?? rowB.createdAt ?? 0).getTime(),
  },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function filterPosts(rows: readonly PostOut[]): PostOut[] {
  const needle = (filterText.value ?? '').toLowerCase()
  return rows.filter((r) => {
    if (categoryFilter.value && r.category !== categoryFilter.value) return false
    if (!needle) return true
    return r.title.toLowerCase().includes(needle) ||
      r.content.toLowerCase().includes(needle) ||
      r.authorName.toLowerCase().includes(needle)
  })
}

function toggleCategoryFilter(category: string) {
  categoryFilter.value = categoryFilter.value === category ? null : category
}

function formatDate(dt: string | null | undefined) {
  if (!dt) return ''
  return formatKst(dt)
}

function canEdit(row: PostOut) {
  return auth.me?.isAdmin || String(row.ownerId) === String(auth.me?.id) || row.editorIds?.includes(String(auth.me?.id))
}

function canDelete(row: PostOut) {
  return auth.me?.isAdmin || String(row.ownerId) === String(auth.me?.id)
}

let loadRequest = 0
async function load() {
  const request = ++loadRequest
  const requestedBoard = boardId.value
  loading.value = true
  try {
    const [allBoards, allPosts] = await Promise.all([
      boardService.listBoards(),
      boardService.listPosts(requestedBoard),
    ])
    if (request !== loadRequest) return
    const board = allBoards.find((b) => b.id === requestedBoard)
    boardTitle.value = board?.title ?? '문서 관리'
    posts.value = allPosts
  } catch {
    if (request !== loadRequest) return
    $q.notify({ type: 'negative', message: '게시판을 불러오는데 실패했습니다' })
  } finally {
    if (request === loadRequest) { loading.value = false; ready.value = true }
  }

  try {
    const items = await envCategoryService.itemsByKey('board_post_categories')
    if (request !== loadRequest) return
    categoryOptions.value = items.map((i) => ({ label: i.label, value: i.label }))
  } catch { /* 카테고리 목록 조회 실패는 무시 (선택 항목) */ }
}

function openWrite() {
  void router.push(`/board/${boardId.value}/write`)
}

function openEdit(row: PostOut) {
  void router.push(`/board/${boardId.value}/edit/${row.id}`)
}

function openPost(row: PostOut) {
  void router.push(`/board/${boardId.value}/post/${row.id}`)
}

function confirmDelete(row: PostOut) {
  $q.dialog({
    title: '문서 삭제',
    message: '이 문서를 삭제하시겠습니까? 하위 문서가 있으면 먼저 이동해야 합니다.',
    cancel: true,
  }).onOk(() => { void (async () => {
    try {
      await boardService.deletePost(boardId.value, row.id)
      await load()
    } catch {
      $q.notify({ type: 'negative', message: '문서를 삭제할 수 없습니다. 하위 문서를 먼저 이동하거나 삭제해 주세요.' })
    }
  })() })
}

watch(() => route.params.boardId, (id) => {
  if (typeof id !== 'string' || id === boardId.value) return
  rememberList()
  ready.value = false
  boardId.value = id
  const restored = readBoardListState(boardId.value, window.sessionStorage)
  filterText.value = restored.search
  categoryFilter.value = restored.category
  pagination.value = restored.pagination
  posts.value = []
  void load()
})

onMounted(() => { void load() })
</script>

<style scoped>
:deep(.q-table thead th) {
  font-size: 13px;
}
.board-document-title {
  min-width: 0;
}
.board-document-title-main {
  display: flex;
  align-items: center;
  min-width: 0;
}
.board-document-title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.board-document-parent {
  margin: 2px 0 0 40px;
  line-height: 1.3;
}
</style>
