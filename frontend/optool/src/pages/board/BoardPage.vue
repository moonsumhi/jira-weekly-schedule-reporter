<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6 col">{{ boardTitle }}</div>
      <q-btn icon="add" label="글쓰기" color="primary" @click="openWrite" />
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

    <!-- 게시글 보기 다이얼로그 -->
    <q-dialog v-model="viewDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section class="row items-start">
          <div class="col">
            <div class="text-h6">{{ viewPost?.title }}</div>
            <div class="text-caption text-grey q-mt-xs">
              {{ viewPost?.authorName }} · {{ formatDate(viewPost?.createdAt) }}
              <span v-if="viewPost?.part"> · {{ viewPost.part }}</span>
            </div>
          </div>
          <q-btn flat dense size="sm" icon="history" label="수정 이력" color="grey-7" @click="openHistory" />
        </q-card-section>
        <q-separator />
        <q-card-section>
          <MarkdownContent :content="viewPost?.content ?? ''" />
        </q-card-section>
        <template v-if="viewPost?.attachments?.length">
          <q-separator />
          <q-card-section>
            <div class="text-caption text-grey-7 q-mb-xs">첨부파일</div>
            <q-list dense bordered class="rounded-borders">
              <q-item v-for="att in viewPost.attachments" :key="att.fileId"
                clickable tag="a" :href="att.url" target="_blank">
                <q-item-section avatar>
                  <q-icon :name="fileIcon(att.contentType)" color="blue-6" size="20px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-primary" style="font-size:0.85rem">{{ att.originalName }}</q-item-label>
                  <q-item-label caption>{{ fmtSize(att.size) }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="open_in_new" color="grey-4" size="16px" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </template>
        <q-card-actions align="right">
          <q-btn flat label="닫기" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 수정 이력 다이얼로그 -->
    <q-dialog v-model="historyDialog">
      <q-card style="min-width: 480px; max-width: 700px">
        <q-card-section class="text-h6">수정 이력</q-card-section>
        <q-separator />
        <q-card-section style="max-height: 65vh" class="scroll q-gutter-md">
          <div v-if="historyLoading" class="text-center q-py-md">
            <q-spinner color="primary" size="24px" />
          </div>
          <div v-else-if="!history.length" class="text-center text-grey-5 q-py-md">수정 이력이 없습니다.</div>
          <template v-else>
          <div v-for="h in history" :key="h.id">
            <div class="row items-center q-mb-xs">
              <span class="text-caption text-grey-8 text-weight-medium">{{ h.changedBy }}</span>
              <span class="text-caption text-grey-5 q-ml-xs">{{ formatDate(h.changedAt) }}</span>
            </div>
            <q-markup-table flat dense bordered>
              <thead>
                <tr class="text-left bg-grey-2">
                  <th style="width:100px">항목</th>
                  <th>이전 값</th>
                  <th>변경 값</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(d, i) in h.diff" :key="i">
                  <td class="text-caption text-grey-8">{{ d.field }}</td>
                  <td class="text-caption text-strike text-grey-6 pre-wrap">{{ truncate(d.before) }}</td>
                  <td class="text-caption text-grey-9 pre-wrap">{{ truncate(d.after) }}</td>
                </tr>
              </tbody>
            </q-markup-table>
          </div>
          </template>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="닫기" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostOut, type PostHistoryOut } from 'src/services/boards'
import MarkdownContent from 'src/components/MarkdownContent.vue'
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
const viewDialog = ref(false)
const viewPost = ref<PostOut | null>(null)
const historyDialog = ref(false)
const historyLoading = ref(false)
const history = ref<PostHistoryOut[]>([])

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const, classes: 'cursor-pointer' },
  { name: 'part', label: '업무 파트', field: 'part', align: 'left' as const },
  { name: 'authorName', label: '작성자', field: 'authorName', align: 'left' as const },
  { name: 'createdAt', label: '작성일', field: (row: PostOut) => formatDate(row.createdAt), align: 'center' as const },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function fileIcon(ct: string) {
  if (ct.startsWith('image/')) return 'image'
  if (ct.includes('pdf')) return 'picture_as_pdf'
  if (ct.includes('spreadsheet') || ct.includes('excel')) return 'table_chart'
  if (ct.includes('zip') || ct.includes('compressed')) return 'folder_zip'
  return 'insert_drive_file'
}

function fmtSize(b: number) {
  if (b < 1024)    return `${b}B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)}KB`
  return `${(b / 1048576).toFixed(1)}MB`
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
  viewPost.value = row
  viewDialog.value = true
}

async function openHistory() {
  if (!viewPost.value) return
  historyDialog.value = true
  historyLoading.value = true
  try {
    history.value = await boardService.getPostHistory(boardId.value, viewPost.value.id)
  } catch {
    $q.notify({ type: 'negative', message: '수정 이력을 불러오는데 실패했습니다' })
  } finally {
    historyLoading.value = false
  }
}

function truncate(v: string | null, max = 120) {
  if (v == null || v === '') return '-'
  return v.length > max ? v.slice(0, max) + '…' : v
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

<style scoped>
.pre-wrap { white-space: pre-wrap; word-break: break-word; }
</style>
