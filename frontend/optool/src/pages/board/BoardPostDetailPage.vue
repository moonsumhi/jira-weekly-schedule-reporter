<template>
  <q-page padding class="board-post-detail-page">
    <div class="row items-center q-mb-md">
      <q-btn flat dense round icon="arrow_back" class="q-mr-xs" @click="goBack" />
      <div class="col">
        <div class="text-caption text-grey-5">{{ boardTitle }}</div>
      </div>
      <q-btn flat dense size="sm" icon="history" label="수정 이력" color="grey-7" @click="openHistory" />
      <q-btn v-if="canEdit" flat dense round icon="edit" class="q-ml-xs" @click="goEdit" />
      <q-btn v-if="canDelete" flat dense round icon="delete" color="negative" @click="confirmDelete" />
    </div>

    <q-card v-if="post" flat bordered>
      <q-card-section>
        <div class="text-h6">{{ post.title }}</div>
        <div class="text-caption text-grey q-mt-xs">
          {{ post.authorName }} · {{ formatDate(post.createdAt) }}
          <span v-if="post.part"> · {{ post.part }}</span>
          <q-chip v-if="post.category" dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-sm">{{ post.category }}</q-chip>
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <MarkdownContent :content="post.content" />
      </q-card-section>
      <template v-if="post.attachments?.length">
        <q-separator />
        <q-card-section>
          <div class="text-caption text-grey-7 q-mb-xs">첨부파일</div>
          <q-list dense bordered class="rounded-borders">
            <q-item v-for="att in post.attachments" :key="att.fileId"
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
    </q-card>
    <div v-else-if="loading" class="text-center q-py-xl">
      <q-spinner color="primary" size="32px" />
    </div>

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
import { ref, computed, onMounted } from 'vue'
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

const boardId = computed(() => route.params.boardId as string)
const postId = computed(() => route.params.postId as string)
const boardTitle = ref('')
const post = ref<PostOut | null>(null)
const loading = ref(false)
const historyDialog = ref(false)
const historyLoading = ref(false)
const history = ref<PostHistoryOut[]>([])

const canEdit = computed(() => !!post.value && (auth.me?.isAdmin || String(post.value.authorId) === String(auth.me?.id)))
const canDelete = canEdit

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

function truncate(v: string | null, max = 120) {
  if (v == null || v === '') return '-'
  return v.length > max ? v.slice(0, max) + '…' : v
}

function goBack() {
  void router.push(`/board/${boardId.value}`)
}

function goEdit() {
  void router.push(`/board/${boardId.value}/edit/${postId.value}`)
}

function confirmDelete() {
  $q.dialog({
    title: '게시글 삭제',
    message: '이 게시글을 삭제하시겠습니까?',
    cancel: true,
  }).onOk(() => { void (async () => { await boardService.deletePost(boardId.value, postId.value); goBack() })() })
}

async function openHistory() {
  historyDialog.value = true
  historyLoading.value = true
  try {
    history.value = await boardService.getPostHistory(boardId.value, postId.value)
  } catch {
    $q.notify({ type: 'negative', message: '수정 이력을 불러오는데 실패했습니다' })
  } finally {
    historyLoading.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const [boards, p] = await Promise.all([
      boardService.listBoards(),
      boardService.getPost(boardId.value, postId.value),
    ])
    boardTitle.value = boards.find((b) => b.id === boardId.value)?.title ?? '게시판'
    post.value = p
  } catch {
    $q.notify({ type: 'negative', message: '게시글을 찾을 수 없습니다.' })
    goBack()
  } finally {
    loading.value = false
  }
}

onMounted(() => { void load() })
</script>

<style scoped>
.board-post-detail-page { max-width: 900px; margin: 0 auto; }
.pre-wrap { white-space: pre-wrap; word-break: break-word; }
</style>
