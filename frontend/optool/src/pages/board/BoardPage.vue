<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6 col">{{ boardTitle }}</div>
      <q-input
        v-model="filter" dense outlined clearable
        placeholder="제목/내용/카테고리 검색"
        style="min-width: 260px"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <q-btn icon="add" label="글쓰기" color="primary" @click="openWrite" />
    </div>

    <q-table
      :rows="posts"
      :columns="columns"
      :filter="filter"
      :filter-method="filterPosts"
      row-key="id"
      flat
      bordered
      :loading="loading"
      no-data-label="게시글이 없습니다"
      @row-click="(_, row) => openPost(row)"
    >
      <template #body-cell-category="{ row }">
        <q-td>
          <q-chip v-if="row.category" dense size="sm" color="blue-1" text-color="blue-9">{{ row.category }}</q-chip>
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
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostOut } from 'src/services/boards'
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
const filter = ref('')

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const, classes: 'cursor-pointer' },
  { name: 'category', label: '카테고리', field: 'category', align: 'left' as const },
  { name: 'part', label: '업무 파트', field: 'part', align: 'left' as const },
  { name: 'authorName', label: '작성자', field: 'authorName', align: 'left' as const },
  { name: 'createdAt', label: '작성일', field: (row: PostOut) => formatDate(row.createdAt), align: 'center' as const },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function filterPosts(rows: readonly PostOut[], term: string): PostOut[] {
  const needle = term.toLowerCase()
  return rows.filter((r) =>
    r.title.toLowerCase().includes(needle) ||
    r.content.toLowerCase().includes(needle) ||
    (r.category ?? '').toLowerCase().includes(needle) ||
    (r.part ?? '').toLowerCase().includes(needle),
  )
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
