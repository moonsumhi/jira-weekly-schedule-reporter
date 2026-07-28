<template>
  <q-page padding class="board-post-form-page">
    <div class="row items-center q-mb-md">
      <q-btn flat dense round icon="arrow_back" class="q-mr-xs" @click="goBack" />
      <div class="col">
        <div class="text-h6 text-weight-bold">{{ isEdit ? '게시글 수정' : '글쓰기' }}</div>
        <div class="text-caption text-grey-5">{{ boardTitle }}</div>
      </div>
    </div>

    <q-card flat bordered class="q-pa-md">
      <div class="q-gutter-md">
        <q-input
          v-model="form.title" label="제목 *" outlined dense autofocus
          :rules="[v => !!v?.trim() || '제목을 입력해주세요.']"
        />
        <q-input v-model="form.part" label="업무 파트" outlined dense placeholder="예: 데이터운영팀, API 개발 파트 등" />
        <MarkdownEditor v-model="form.content" label="내용" required :rows="12" />

        <div>
          <div class="text-caption text-grey-7 q-mb-xs">첨부파일 <span class="text-grey-5">(선택)</span></div>
          <q-uploader
            url="/api/pm/uploads"
            label="파일을 드래그하거나 클릭하여 업로드"
            multiple
            accept=".pdf,.hwp,.docx,.xlsx,.pptx,.zip,.jpg,.jpeg,.png,.gif"
            max-file-size="20971520"
            flat bordered class="full-width"
            :headers="uploadHeaders"
            @uploaded="onFileUploaded"
            @failed="onUploadFailed"
          />
          <div v-if="attachments.length" class="q-mt-sm row q-gutter-xs">
            <q-chip v-for="(att, i) in attachments" :key="i"
              removable @remove="attachments.splice(i, 1)"
              icon="attach_file" color="blue-1" text-color="blue-9" size="sm">
              {{ att.originalName }}
            </q-chip>
          </div>
        </div>
      </div>
    </q-card>

    <div class="row justify-end q-gutter-sm q-mt-md">
      <q-btn flat color="grey-7" label="취소" @click="goBack" />
      <q-btn color="primary" :label="isEdit ? '수정' : '등록'" :loading="saving" @click="submit" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostAttachment, type PostAttachmentInput } from 'src/services/boards'
import { useAuthStore } from 'stores/auth'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'

const route  = useRoute()
const router = useRouter()
const $q     = useQuasar()
const authStore = useAuthStore()

const boardId   = computed(() => route.params.boardId as string)
const postId    = computed(() => route.params.postId as string | undefined)
const isEdit    = computed(() => !!postId.value)
const boardTitle = ref('')
const saving    = ref(false)
const attachments = ref<PostAttachment[]>([])

const form = ref({ title: '', part: '', content: '' })

const uploadHeaders = computed(() => {
  const token = authStore.token
  return token ? [{ name: 'Authorization', value: `Bearer ${token}` }] : []
})

function onFileUploaded(info: { files: readonly File[], xhr: XMLHttpRequest }) {
  try {
    const res = JSON.parse(info.xhr.response)
    attachments.value.push({
      fileId: res.file_id || res.fileId || '',
      originalName: res.original_name || res.originalName || '',
      url: res.url, size: res.size,
      contentType: res.content_type || res.contentType || '',
    })
  } catch { $q.notify({ type: 'warning', message: '파일 업로드 응답 처리 중 오류가 발생했습니다.' }) }
}
function onUploadFailed() {
  $q.notify({ type: 'negative', message: '파일 업로드 실패 (최대 20MB, 허용 형식 확인)' })
}

function goBack() {
  void router.push(`/board/${boardId.value}`)
}

async function load() {
  try {
    const boards = await boardService.listBoards()
    boardTitle.value = boards.find(b => b.id === boardId.value)?.title ?? '게시판'
  } catch { /* 게시판 제목 조회 실패는 무시 */ }

  if (isEdit.value) {
    try {
      const posts = await boardService.listPosts(boardId.value)
      const post = posts.find(p => p.id === postId.value)
      if (!post) {
        $q.notify({ type: 'negative', message: '게시글을 찾을 수 없습니다.' })
        goBack()
        return
      }
      form.value = { title: post.title, part: post.part ?? '', content: post.content }
      attachments.value = post.attachments ?? []
    } catch {
      $q.notify({ type: 'negative', message: '게시글을 불러오는데 실패했습니다.' })
      goBack()
    }
  }
}

async function submit() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    $q.notify({ type: 'warning', message: '제목과 내용을 입력해주세요.', position: 'top' })
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.value.title.trim(),
      part: form.value.part.trim(),
      content: form.value.content,
      attachments: attachments.value.map((a): PostAttachmentInput => ({
        file_id: a.fileId, original_name: a.originalName, url: a.url, size: a.size, content_type: a.contentType,
      })),
    }
    if (isEdit.value && postId.value) {
      await boardService.patchPost(boardId.value, postId.value, payload)
      $q.notify({ type: 'positive', message: '게시글이 수정되었습니다.' })
    } else {
      await boardService.createPost(boardId.value, payload)
      $q.notify({ type: 'positive', message: '게시글이 등록되었습니다.' })
    }
    goBack()
  } catch {
    $q.notify({ type: 'negative', message: isEdit.value ? '수정에 실패했습니다.' : '등록에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}

onMounted(() => { void load() })
</script>

<style scoped>
.board-post-form-page { max-width: 1200px; margin: 0 auto; }
</style>
