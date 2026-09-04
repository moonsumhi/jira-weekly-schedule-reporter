<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm no-wrap">
      <div class="text-h6" style="flex-shrink: 0;">{{ boardTitle }}</div>
      <q-btn icon="add" label="글쓰기" color="primary" style="flex-shrink: 0; margin-left: 15px;" @click="openWrite" />
      <q-space />
      <q-select
        v-model="categoryFilter" dense outlined clearable
        :options="categoryOptions" emit-value map-options
        label="카테고리" style="flex: 0 0 160px"
      />
      <q-input
        v-model="filterText" dense outlined clearable
        placeholder="제목 / 내용 / 작성자 검색"
        style="flex: 0 1 500px; min-width: 150px"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>
    </div>

    <q-table
      :rows="posts"
      :columns="columns"
      :filter="tableFilter"
      :filter-method="filterPosts"
      row-key="id"
      flat
      bordered
      :loading="loading"
      v-model:pagination="pagination"
      :rows-per-page-options="[15, 30, 50, 100, 0]"
      no-data-label="게시글이 없습니다"
      @row-click="(_, row) => openPost(row)"
    >
      <template #body-cell-title="{ row }">
        <q-td class="cursor-pointer">
          <span
            v-if="row.category"
            class="text-primary"
            :class="{ 'text-weight-bold': categoryFilter === row.category }"
            @click.stop="toggleCategoryFilter(row.category)"
          >[{{ row.category }}]</span>{{ row.title }}
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
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostOut } from 'src/services/boards'
import { envCategoryService } from 'src/services/envCategory'
import { useAuthStore } from 'stores/auth'
import { formatKst } from 'src/utils/time/kst'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()

const boardId = ref(route.params.boardId as string)
const boardTitle = ref('')
const posts = ref<PostOut[]>([])
const loading = ref(false)
const filterText = ref('')
const categoryFilter = ref<string | null>(null)
const categoryOptions = ref<{ label: string; value: string }[]>([])
const tableFilter = computed(() => `${filterText.value}||${categoryFilter.value ?? ''}`)
const pagination = ref({ page: 1, rowsPerPage: 15 })

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const, classes: 'cursor-pointer', sortable: true },
  { name: 'part', label: '업무 파트', field: 'part', align: 'left' as const, sortable: true },
  { name: 'authorName', label: '작성자', field: 'authorName', align: 'left' as const, sortable: true },
  {
    name: 'createdAt', label: '작성일', field: (row: PostOut) => formatDate(row.createdAt), align: 'center' as const,
    sortable: true,
    sort: (_a: unknown, _b: unknown, rowA: PostOut, rowB: PostOut) =>
      new Date(rowA.createdAt ?? 0).getTime() - new Date(rowB.createdAt ?? 0).getTime(),
  },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function filterPosts(rows: readonly PostOut[]): PostOut[] {
  const needle = filterText.value.toLowerCase()
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
  return auth.me?.isAdmin || String(row.authorId) === String(auth.me?.id)
}

function canDelete(row: PostOut) {
  return auth.me?.isAdmin || String(row.authorId) === String(auth.me?.id)
}

async function load() {
  loading.value = true
  try {
    const [allBoards, allPosts] = await Promise.all([
      boardService.listBoards(),
      boardService.listPosts(boardId.value),
    ])
    const board = allBoards.find((b) => b.id === boardId.value)
    boardTitle.value = board?.title ?? '게시판'
    posts.value = allPosts
  } catch {
    $q.notify({ type: 'negative', message: '게시판을 불러오는데 실패했습니다' })
  } finally {
    loading.value = false
  }

  try {
    const items = await envCategoryService.itemsByKey('board_post_categories')
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
    title: '게시글 삭제',
    message: '이 게시글을 삭제하시겠습니까?',
    cancel: true,
  }).onOk(() => { void (async () => { await boardService.deletePost(boardId.value, row.id); await load() })() })
}

watch(() => route.params.boardId, (id) => {
  boardId.value = id as string
  void load()
})

onMounted(() => { void load() })
</script>
