<template>
  <q-page padding class="board-post-history-page">
    <div class="history-page-header row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" aria-label="문서로 돌아가기" @click="goToDocument" />
      <div class="q-ml-sm">
        <div class="text-h6">수정 이력</div>
        <div v-if="post" class="text-caption text-grey-6">{{ post.title }}</div>
      </div>
      <q-space />
      <q-btn v-if="post" outline dense icon="description" label="문서 보기" @click="goToDocument" />
    </div>

    <q-card v-if="loading" flat bordered class="q-pa-xl text-center">
      <q-spinner color="primary" size="32px" />
    </q-card>
    <q-card v-else-if="post" flat bordered>
      <q-card-section class="row items-center q-col-gutter-md">
        <div class="col">
          <div class="text-subtitle1 text-weight-medium">{{ post.title }}</div>
          <div class="text-caption text-grey-6">현재 문서 v{{ post.version }}</div>
        </div>
        <div v-if="post.adoptedVersion" class="adoption-status-chip">
          <q-icon name="task_alt" size="18px" />
          <span>v{{ post.adoptedVersion }} 채택 · {{ post.adoptedName }}</span>
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <div v-if="!history.length" class="text-center text-grey-6 q-pa-lg">수정 이력이 없습니다.</div>
        <q-card v-for="item in history" :key="item.id" flat bordered class="version-card q-mb-md">
          <q-card-section class="row items-center q-col-gutter-sm">
            <q-icon name="history" color="blue-grey-6" size="20px" />
            <div>
              <div class="text-weight-medium">v{{ item.version ?? '—' }}</div>
              <div class="text-caption text-grey-6">{{ item.changedBy }} · {{ formatDate(item.changedAt) }}</div>
            </div>
            <span v-if="item.version === post.version" class="version-tag version-tag--current">현재 버전</span>
            <span v-if="item.version && item.version === post.adoptedVersion" class="version-tag version-tag--adopted">채택된 버전</span>
            <q-space />
            <q-btn v-if="item.version && item.snapshot && item.version !== post.adoptedVersion && canAdoptVersion"
              flat dense size="sm" icon="task_alt" label="이 버전 채택" color="positive"
              :loading="adoptingVersion === item.version" @click="confirmAdoptVersion(item.version)" />
            <q-btn v-if="item.version && item.snapshot && item.version === post.adoptedVersion && canClearAdoption"
              flat dense size="sm" label="채택 취소" color="grey-7" @click="clearVersionAdoption" />
          </q-card-section>

          <q-expansion-item v-if="item.snapshot" dense label="버전 내용 보기" icon="article">
            <q-card-section class="version-content">
              <div class="text-subtitle2 q-mb-sm">{{ item.snapshot.title }}</div>
              <div v-if="item.snapshot.part || item.snapshot.category" class="text-caption text-grey-7 q-mb-md">
                <span v-if="item.snapshot.part">{{ item.snapshot.part }}</span>
                <span v-if="item.snapshot.part && item.snapshot.category"> · </span>
                <span v-if="item.snapshot.category">{{ item.snapshot.category }}</span>
              </div>
              <MarkdownContent :content="item.snapshot.content" />
              <q-list v-if="item.snapshot.attachments.length" dense bordered separator class="q-mt-md">
                <q-item v-for="attachment in item.snapshot.attachments" :key="attachment.fileId"
                  tag="a" :href="attachment.url" target="_blank" clickable>
                  <q-item-section avatar><q-icon name="attach_file" /></q-item-section>
                  <q-item-section>{{ attachment.originalName }}</q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-expansion-item>

          <q-expansion-item v-if="item.diff.length" dense label="이 버전에서 바뀐 항목" icon="difference">
            <q-markup-table flat dense separator="horizontal">
              <thead>
                <tr class="bg-grey-2 text-left">
                  <th style="width: 120px">항목</th>
                  <th>이전 내용</th>
                  <th>변경 내용</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(change, index) in item.diff" :key="index">
                  <td class="text-caption">{{ change.field }}</td>
                  <td class="pre-wrap">{{ change.before || '—' }}</td>
                  <td class="pre-wrap">{{ change.after || '—' }}</td>
                </tr>
              </tbody>
            </q-markup-table>
          </q-expansion-item>
        </q-card>
      </q-card-section>
    </q-card>
    <q-card v-else flat bordered class="q-pa-lg text-center">
      문서 이력을 불러오지 못했습니다.
      <div><q-btn flat color="primary" label="다시 불러오기" class="q-mt-sm" @click="load" /></div>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type PostHistoryOut, type PostOut } from 'src/services/boards'
import MarkdownContent from 'src/components/MarkdownContent.vue'
import { useAuthStore } from 'stores/auth'
import { formatKst } from 'src/utils/time/kst'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const boardId = computed(() => String(route.params.boardId ?? ''))
const postId = computed(() => String(route.params.postId ?? ''))
const post = ref<PostOut | null>(null)
const history = ref<PostHistoryOut[]>([])
const loading = ref(false)
const adoptingVersion = ref<number | null>(null)
let requestId = 0

const canClearAdoption = computed(() => !!post.value?.adoptedBy &&
  (post.value.adoptedBy === String(auth.me?.id) || !!auth.me?.isAdmin))
const canAdoptVersion = computed(() => !post.value?.adoptedBy || canClearAdoption.value)

watch([boardId, postId], () => { void load() }, { immediate: true })

async function load() {
  if (!boardId.value || !postId.value) return
  const currentRequest = ++requestId
  loading.value = true
  try {
    const [loadedPost, loadedHistory] = await Promise.all([
      boardService.getPost(boardId.value, postId.value),
      boardService.getPostHistory(boardId.value, postId.value),
    ])
    if (currentRequest !== requestId) return
    post.value = loadedPost
    history.value = loadedHistory
  } catch {
    if (currentRequest === requestId) {
      post.value = null
      history.value = []
      $q.notify({ type: 'negative', message: '수정 이력을 불러오지 못했습니다.' })
    }
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

function goToDocument() {
  void router.push(`/board/${boardId.value}/post/${postId.value}`)
}

function confirmAdoptVersion(version: number) {
  $q.dialog({
    title: '버전 채택',
    message: `v${version} 내용을 현재 문서로 적용합니다. 지금 내용은 새 수정 이력으로 보존됩니다. 진행할까요?`,
    cancel: true,
  }).onOk(() => { void adoptVersion(version) })
}

async function adoptVersion(version: number) {
  if (!post.value) return
  adoptingVersion.value = version
  try {
    post.value = await boardService.adoptPost(boardId.value, postId.value, version)
    history.value = await boardService.getPostHistory(boardId.value, postId.value)
    $q.notify({ type: 'positive', message: `v${version} 내용을 현재 문서로 채택했습니다.` })
  } catch {
    $q.notify({ type: 'negative', message: '선택한 버전을 채택하지 못했습니다.' })
  } finally {
    adoptingVersion.value = null
  }
}

async function clearVersionAdoption() {
  if (!post.value) return
  try {
    post.value = await boardService.clearAdoption(boardId.value, postId.value)
    $q.notify({ type: 'positive', message: '버전 채택을 취소했습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '버전 채택을 취소하지 못했습니다.' })
  }
}

function formatDate(value: string | null | undefined) {
  return value ? formatKst(value) : ''
}
</script>

<style scoped>
.board-post-history-page { max-width: 1160px; margin: 0 auto; }
.adoption-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 1 auto;
  width: fit-content;
  min-width: 0;
  min-height: 28px;
  max-width: 100%;
  box-sizing: border-box;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--q-positive, #21ba45);
  color: #fff;
  line-height: 1.2;
}
.adoption-status-chip .q-icon { flex: 0 0 auto; }
.adoption-status-chip span {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.15;
  position: relative;
  top: -1px;
}
.history-page-header { min-height: 52px; }
.version-card { overflow: hidden; }
.version-card :deep(.q-card__section.row) { flex-wrap: wrap; }
.version-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  align-self: center;
  min-height: 24px;
  max-width: 100%;
  box-sizing: border-box;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
  white-space: nowrap;
}
.version-tag--current { background: #e3f2fd; color: #1565c0; }
.version-tag--adopted { background: #21ba45; color: #fff; }
.version-content { min-width: 0; overflow-wrap: anywhere; }
.pre-wrap { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>
