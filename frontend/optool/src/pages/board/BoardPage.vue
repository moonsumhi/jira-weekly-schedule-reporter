<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6 col">{{ boardTitle }}</div>
      <q-btn v-if="isInternal" icon="add" label="글쓰기" color="primary" @click="openWrite" />
    </div>

    <q-table
      :rows="posts"
      :columns="columns"
      row-key="id"
      flat
      bordered
      :loading="loading"
      no-data-label="게시글이 없습니다"
      @row-click="(_, row) => openPost(row)"
    >
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

    <!-- 글쓰기 / 수정 다이얼로그 -->
    <q-dialog v-model="writeDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section class="text-h6">{{ editTarget ? '게시글 수정' : '글쓰기' }}</q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="writeForm.title" label="제목" outlined dense autofocus />
          <q-input v-model="writeForm.content" label="내용" outlined type="textarea" rows="8" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" :label="editTarget ? '수정' : '등록'" @click="submitPost" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 게시글 보기 다이얼로그 -->
    <q-dialog v-model="viewDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">{{ viewPost?.title }}</div>
          <div class="text-caption text-grey q-mt-xs">
            {{ viewPost?.authorName }} · {{ formatDate(viewPost?.createdAt) }}
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section style="white-space: pre-wrap">{{ viewPost?.content }}</q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="닫기" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostOut } from 'src/services/boards'
import { useAuthStore } from 'stores/auth'

const route = useRoute()
const $q = useQuasar()
const auth = useAuthStore()

const boardId = ref(route.params.boardId as string)
const boardTitle = ref('')
const posts = ref<PostOut[]>([])
const loading = ref(false)
const writeDialog = ref(false)
const viewDialog = ref(false)
const saving = ref(false)
const viewPost = ref<PostOut | null>(null)
const editTarget = ref<PostOut | null>(null)
const writeForm = ref({ title: '', content: '' })

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const, classes: 'cursor-pointer' },
  { name: 'authorName', label: '작성자', field: 'authorName', align: 'left' as const },
  { name: 'createdAt', label: '작성일', field: (row: PostOut) => formatDate(row.createdAt), align: 'center' as const },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function formatDate(dt: string | null | undefined) {
  if (!dt) return ''
  return new Date(dt).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

const isInternal = computed(() => auth.me?.isInternal !== false)

function canEdit(row: PostOut) {
  return isInternal.value && (auth.me?.isAdmin || String(row.authorId) === String(auth.me?.id))
}

function canDelete(row: PostOut) {
  return isInternal.value && (auth.me?.isAdmin || String(row.authorId) === String(auth.me?.id))
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
  editTarget.value = null
  writeForm.value = { title: '', content: '' }
  writeDialog.value = true
}

function openEdit(row: PostOut) {
  editTarget.value = row
  writeForm.value = { title: row.title, content: row.content }
  writeDialog.value = true
}

async function submitPost() {
  if (!writeForm.value.title || !writeForm.value.content) return
  saving.value = true
  try {
    if (editTarget.value) {
      await boardService.patchPost(boardId.value, editTarget.value.id, writeForm.value)
    } else {
      await boardService.createPost(boardId.value, writeForm.value)
    }
    writeDialog.value = false
    await load()
  } catch {
    $q.notify({ type: 'negative', message: editTarget.value ? '수정에 실패했습니다' : '등록에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

function openPost(row: PostOut) {
  viewPost.value = row
  viewDialog.value = true
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
