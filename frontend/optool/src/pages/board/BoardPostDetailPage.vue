<template>
  <q-page padding class="board-post-detail-page">
    <div class="document-detail-layout" :class="{ 'document-nav-open': docNavOpen }">
      <aside v-if="docNavOpen" class="document-nav-panel">
        <q-card flat bordered>
          <q-card-section class="text-subtitle2">문서 탐색</q-card-section>
          <q-separator />
          <q-list dense class="q-py-sm">
            <q-item v-for="item in documentTree" :key="item.post.id" clickable
              :active="item.post.id === postId" active-class="bg-blue-1 text-primary"
              :style="{ paddingLeft: `${12 + item.depth * 18}px` }"
              @click="openFromSidebar(item.post)">
              <q-item-section avatar style="min-width: 28px">
                <q-btn v-if="hasChildren(item.post.id)" flat dense round size="xs"
                  :icon="collapsedIds.has(item.post.id) ? 'chevron_right' : 'expand_more'"
                  @click.stop="toggleExpanded(item.post.id)" />
                <q-icon v-else name="description" size="18px" />
              </q-item-section>
              <q-item-section><q-item-label lines="1">{{ item.post.title }}</q-item-label></q-item-section>
            </q-item>
            <q-item v-if="!documentTree.length"><q-item-section class="text-grey-6">문서가 없습니다.</q-item-section></q-item>
          </q-list>
        </q-card>
      </aside>
      <main class="document-detail-main">
    <div class="row items-center q-mb-md">
      <q-btn flat dense round icon="arrow_back" class="q-mr-xs" @click="goBack" />
      <q-btn flat dense round :icon="docNavOpen ? 'menu_open' : 'menu'" :title="docNavOpen ? '문서 탐색 닫기' : '문서 탐색 열기'" :aria-label="docNavOpen ? '문서 탐색 닫기' : '문서 탐색 열기'" class="q-mr-sm" @click="docNavOpen = !docNavOpen" />
      <div class="col">
        <div class="text-caption text-grey-5">{{ boardTitle }}</div>
      </div>
      <q-btn flat dense size="sm" :icon="following ? 'star' : 'star_border'"
        :label="following ? '관심 중' : '관심 표시'" :color="following ? 'amber-8' : 'grey-7'"
        :loading="followLoading" @click="toggleFollow" />
      <q-chip v-if="post?.adoptedVersion" dense color="positive" text-color="white" icon="task_alt" class="adoption-status-chip">
        v{{ post.adoptedVersion }} 채택 · {{ post.adoptedName }}
      </q-chip>
      <q-chip v-else-if="post?.adoptedBy" dense color="positive" text-color="white" icon="task_alt" class="adoption-status-chip">
        {{ post.adoptedName }}님이 이전 방식으로 채택
      </q-chip>
      <q-btn flat dense size="sm" icon="history" label="수정 이력" color="grey-7" @click="openHistory" />
      <q-btn flat dense size="sm" icon="link" label="링크 복사" color="grey-7" @click="copyLink" />
      <q-btn flat dense size="sm" icon="note_add" label="하위 문서" @click="addChild" />
      <q-btn v-if="canEdit" flat dense round icon="edit" class="q-ml-xs" @click="goEdit" />
      <q-btn v-if="canDelete" flat dense round icon="delete" color="negative" @click="confirmDelete" />
    </div>

    <q-card v-if="post" flat bordered>
      <q-card-section>
        <div v-if="ancestors.length" class="row items-center q-gutter-xs text-caption q-mb-sm">
          <template v-for="ancestor in ancestors" :key="ancestor.id">
            <a href="#" @click.prevent="openDocument(ancestor.id)">{{ ancestor.title }}</a>
            <q-icon name="chevron_right" />
          </template>
        </div>
        <div class="text-h6">{{ post.title }}</div>
        <div class="text-caption text-grey q-mt-xs">
          {{ post.authorName }} · {{ formatDate(post.createdAt) }}
          · v{{ post.version }}
          <span v-if="post.updatedAt && post.updatedAt !== post.createdAt"> · 최근 수정 {{ formatDate(post.updatedAt) }}</span>
          <span v-if="post.part"> · {{ post.part }}</span>
          <q-chip v-if="post.category" dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-sm">{{ post.category }}</q-chip>
        </div>
        <div v-if="post.ownerId !== post.authorId" class="text-caption text-grey-7 q-mt-xs">
          문서 책임자: {{ post.ownerName }}
        </div>
        <div v-if="post.editorIds?.length" class="text-caption text-grey-7 q-mt-xs">
          함께 수정: {{ editorSummary }}
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
              clickable
              :tag="att.contentType.startsWith('image/') ? 'a' : 'div'"
              :href="att.contentType.startsWith('image/') ? att.url : undefined"
              :target="att.contentType.startsWith('image/') ? '_blank' : undefined"
              @click="att.contentType.startsWith('image/') ? undefined : openPreview(att)">
              <q-item-section avatar>
                <q-icon :name="fileIcon(att.contentType)" color="blue-6" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-primary" style="font-size:0.85rem">{{ att.originalName }}</q-item-label>
                <q-item-label caption>{{ fmtSize(att.size) }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn flat dense round icon="download" size="sm" color="grey-6"
                  @click.stop="downloadFile(att.url, att.originalName)" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </template>
    </q-card>
    <q-card v-if="post" flat bordered class="q-mt-md">
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-subtitle1 text-weight-medium">댓글</div>
          <q-badge color="grey-6" :label="comments.length" class="q-ml-sm" />
        </div>
        <div v-if="commentsLoading" class="text-center q-py-md"><q-spinner color="primary" /></div>
        <div v-else-if="!comments.length" class="text-caption text-grey-6 q-py-sm">아직 댓글이 없습니다.</div>
        <div v-for="comment in comments" :key="comment.id" class="board-comment q-py-md">
          <div class="row items-center no-wrap">
            <q-avatar size="28px" color="blue-grey-2" text-color="blue-grey-9" class="q-mr-sm">
              {{ comment.authorName?.charAt(0) || '?' }}
            </q-avatar>
            <span class="text-weight-medium">{{ comment.authorName }}</span>
            <span class="text-caption text-grey-6 q-ml-sm">{{ formatDate(comment.createdAt) }}</span>
            <q-space />
            <q-btn v-if="canDeleteComment(comment)" flat dense round size="sm" icon="delete_outline" color="grey-6"
              title="댓글 삭제" @click="deleteComment(comment)" />
          </div>
          <div class="q-ml-xl q-mt-sm comment-content">
            <MentionContent :content="comment.content" :mentioned-users="comment.mentionedUsers" />
          </div>
          <div class="row items-center q-ml-xl q-mt-sm q-gutter-xs">
            <q-btn v-for="reaction in comment.reactions" :key="reaction.emoji" dense unelevated
              :color="hasReacted(reaction) ? 'blue-1' : 'grey-2'" text-color="grey-9"
              :label="`${reaction.emoji} ${reaction.users.length}`" @click="toggleReaction(comment, reaction.emoji)" />
            <q-btn flat dense round size="sm" icon="add_reaction" color="grey-7" title="이모지 반응">
              <q-menu><div class="row q-pa-xs q-gutter-xs">
                <q-btn v-for="emoji in reactionEmojis" :key="emoji" flat round dense :label="emoji"
                  @click="toggleReaction(comment, emoji)" />
              </div></q-menu>
            </q-btn>
          </div>
          <q-separator class="q-mt-md" />
        </div>
        <div class="q-mt-md">
          <div class="row items-start no-wrap q-gutter-sm">
            <div class="col">
              <MentionInput v-model="commentDraft" v-model:mentioned-users="commentMentionedUsers"
                placeholder="댓글을 작성하세요. @로 사용자를 멘션할 수 있습니다." :rows="3" dense />
            </div>
            <q-btn flat round dense icon="emoji_emotions" color="grey-7" title="댓글에 이모지 추가">
              <q-menu><div class="row q-pa-xs q-gutter-xs">
                <q-btn v-for="emoji in reactionEmojis" :key="emoji" flat round dense :label="emoji"
                  @click="insertCommentEmoji(emoji)" />
              </div></q-menu>
            </q-btn>
          </div>
          <div class="row justify-end q-mt-sm">
            <q-btn color="primary" icon="send" label="댓글 등록" :loading="commentSubmitting"
              :disable="!commentDraft.trim()" @click="submitComment" />
          </div>
        </div>
      </q-card-section>
    </q-card>
    <div v-else-if="loading" class="text-center q-py-xl">
      <q-spinner color="primary" size="32px" />
    </div>

    <AttachmentPreviewDialog v-model="previewOpen" :attachment="previewAttachment" />
      </main>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { boardService, type BoardComment, type BoardCommentReaction, type PostOut, type PostAttachment } from 'src/services/boards'
import MarkdownContent from 'src/components/MarkdownContent.vue'
import MentionContent from 'src/components/MentionContent.vue'
import MentionInput from 'src/components/MentionInput.vue'
import type { MentionUser } from 'src/services/mention'
import { useAuthStore } from 'stores/auth'
import { formatKst } from 'src/utils/time/kst'
import { downloadAttachment } from 'src/utils/attachment'
import AttachmentPreviewDialog from 'src/components/AttachmentPreviewDialog.vue'
import { listPmUsers } from 'src/services/pm/users'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()

const boardId = computed(() => route.params.boardId as string)
const postId = computed(() => route.params.postId as string)
const boardTitle = ref('')
const post = ref<PostOut | null>(null)
const allPosts = ref<PostOut[]>([])
const docNavOpen = ref(false)
const collapsedIds = ref(new Set<string>())
const editorNames = ref<Record<string, string>>({})
const editorSummary = computed(() => post.value?.editorIds?.map((id) => editorNames.value[id] ?? id).join(', ') ?? '')
function hasChildren(id: string) {
  return allPosts.value.some((item) => item.parentId === id && relatedDocumentIds.value.has(item.id))
}
function toggleExpanded(id: string) {
  const next = new Set(collapsedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsedIds.value = next
}
const relatedDocumentIds = computed(() => {
  const current = post.value
  if (!current) return new Set<string>()

  const documentsById = new Map(allPosts.value.map((item) => [item.id, item] as const))
  const relatedIds = new Set<string>([current.id])
  let parentId = current.parentId
  while (parentId && !relatedIds.has(parentId)) {
    const parent = documentsById.get(parentId)
    if (!parent) break
    relatedIds.add(parent.id)
    parentId = parent.parentId
  }

  if (current.parentId) {
    for (const sibling of allPosts.value) {
      if (sibling.parentId === current.parentId) relatedIds.add(sibling.id)
    }
  }

  const pending = [current.id]
  while (pending.length) {
    const ancestorId = pending.pop()!
    for (const child of allPosts.value) {
      if (child.parentId !== ancestorId || relatedIds.has(child.id)) continue
      relatedIds.add(child.id)
      pending.push(child.id)
    }
  }
  return relatedIds
})
const documentTree = computed(() => {
  const relatedPosts = allPosts.value.filter((item) => relatedDocumentIds.value.has(item.id))
  const children = new Map<string | null, PostOut[]>()
  const relatedById = new Map(relatedPosts.map((item) => [item.id, item] as const))
  const ids = new Set(relatedById.keys())
  for (const item of relatedPosts) {
    const parent = item.parentId && ids.has(item.parentId) ? item.parentId : null
    const group = children.get(parent) ?? []
    group.push(item)
    children.set(parent, group)
  }
  const result: { post: PostOut; depth: number }[] = []
  const seen = new Set<string>()
  function visit(parent: string | null, depth: number) {
    for (const item of children.get(parent) ?? []) {
      if (seen.has(item.id)) continue
      seen.add(item.id)
      result.push({ post: item, depth })
      if (!collapsedIds.value.has(item.id)) visit(item.id, depth + 1)
    }
  }
  visit(null, 0)
  for (const item of relatedPosts) {
    if (seen.has(item.id)) continue

    // Keep malformed/orphaned items reachable, but don't re-add descendants
    // that were intentionally hidden under a collapsed ancestor.
    let ancestorId = item.parentId
    const checkedAncestors = new Set([item.id])
    let hiddenByCollapsedAncestor = false
    while (ancestorId && !checkedAncestors.has(ancestorId)) {
      if (seen.has(ancestorId) && collapsedIds.value.has(ancestorId)) {
        hiddenByCollapsedAncestor = true
        break
      }
      checkedAncestors.add(ancestorId)
      ancestorId = relatedById.get(ancestorId)?.parentId ?? null
    }
    if (hiddenByCollapsedAncestor) continue

    result.push({ post: item, depth: 0 })
    seen.add(item.id)
    if (!collapsedIds.value.has(item.id)) visit(item.id, 1)
  }
  return result
})
const ancestors = computed(() => {
  const result: PostOut[] = []
  const seen = new Set<string>()
  let parentId = post.value?.parentId
  while (parentId && !seen.has(parentId)) {
    seen.add(parentId)
    const parent = allPosts.value.find((item) => item.id === parentId)
    if (!parent) break
    result.unshift(parent)
    parentId = parent.parentId
  }
  return result
})
const loading = ref(false)
const comments = ref<BoardComment[]>([])
const commentsLoading = ref(false)
const commentDraft = ref('')
const commentMentionedUsers = ref<MentionUser[]>([])
const commentSubmitting = ref(false)
const following = ref(false)
const followLoading = ref(false)
const reactionEmojis = ['👍', '❤️', '😂', '🎉', '👀', '🙏', '🚀']

const canEdit = computed(() => !!post.value && (auth.me?.isAdmin || String(post.value.ownerId) === String(auth.me?.id) || post.value.editorIds?.includes(String(auth.me?.id))))
const canDelete = computed(() => !!post.value && (auth.me?.isAdmin || String(post.value.ownerId) === String(auth.me?.id)))

async function toggleFollow() {
  if (!post.value) return
  followLoading.value = true
  try {
    if (following.value) {
      await boardService.unfollowPost(boardId.value, postId.value)
      following.value = false
      post.value.followerCount = Math.max(0, post.value.followerCount - 1)
    } else {
      await boardService.followPost(boardId.value, postId.value)
      following.value = true
      post.value.followerCount += 1
    }
  } catch {
    $q.notify({ type: 'negative', message: '관심 문서 설정을 저장하지 못했습니다.' })
  } finally {
    followLoading.value = false
  }
}

async function submitComment() {
  if (!post.value || !commentDraft.value.trim()) return
  commentSubmitting.value = true
  try {
    const content = commentDraft.value.trim()
    const mentionedIds = commentMentionedUsers.value
      .filter(user => content.includes(`@${user.displayName}`))
      .map(user => user.userId)
    comments.value.push(await boardService.createComment(boardId.value, postId.value, content, mentionedIds))
    commentDraft.value = ''
    commentMentionedUsers.value = []
  } catch {
    $q.notify({ type: 'negative', message: '댓글을 등록하지 못했습니다.' })
  } finally {
    commentSubmitting.value = false
  }
}

function insertCommentEmoji(emoji: string) {
  const separator = commentDraft.value && !/\s$/.test(commentDraft.value) ? ' ' : ''
  commentDraft.value += `${separator}${emoji}`
}

function canDeleteComment(comment: BoardComment) {
  return auth.me?.isAdmin || String(comment.authorId) === String(auth.me?.id)
}

async function deleteComment(comment: BoardComment) {
  try {
    await boardService.deleteComment(boardId.value, postId.value, comment.id)
    comments.value = comments.value.filter(item => item.id !== comment.id)
  } catch {
    $q.notify({ type: 'negative', message: '댓글을 삭제하지 못했습니다.' })
  }
}

function hasReacted(reaction: BoardCommentReaction) {
  return reaction.users.some(user => String(user.userId) === String(auth.me?.id))
}

async function toggleReaction(comment: BoardComment, emoji: string) {
  try {
    const updated = await boardService.toggleCommentReaction(boardId.value, postId.value, comment.id, emoji)
    const index = comments.value.findIndex(item => item.id === comment.id)
    if (index >= 0) comments.value[index] = updated
  } catch {
    $q.notify({ type: 'negative', message: '이모지 반응을 저장하지 못했습니다.' })
  }
}

const previewOpen = ref(false)
const previewAttachment = ref<PostAttachment | null>(null)
function openPreview(att: PostAttachment) {
  previewAttachment.value = att
  previewOpen.value = true
}

async function downloadFile(url: string, filename: string) {
  try {
    await downloadAttachment(url, filename)
  } catch {
    $q.notify({ type: 'negative', message: '파일 다운로드에 실패했습니다.' })
  }
}

function fileIcon(ct: string) {
  if (ct.startsWith('image/')) return 'image'
  if (ct.startsWith('video/')) return 'movie'
  if (ct.includes('pdf')) return 'picture_as_pdf'
  if (ct.includes('spreadsheet') || ct.includes('excel')) return 'table_chart'
  if (ct.includes('powerpoint') || ct.includes('presentation')) return 'slideshow'
  if (ct.includes('zip') || ct.includes('compressed')) return 'folder_zip'
  if (ct === 'text/html' || ct === 'application/json' || ct.includes('xml')) return 'code'
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

function goBack() {
  void router.push(`/board/${boardId.value}`)
}

function goEdit() {
  void router.push(`/board/${boardId.value}/edit/${postId.value}`)
}

function addChild() {
  void router.push({ path: `/board/${boardId.value}/write`, query: { parentId: postId.value } })
}

function openDocument(id: string) {
  void router.push(`/board/${boardId.value}/post/${id}`)
}

function openFromSidebar(item: PostOut) {
  if (collapsedIds.value.has(item.id)) toggleExpanded(item.id)
  openDocument(item.id)
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    $q.notify({ type: 'positive', message: '문서 링크를 복사했습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '링크를 복사하지 못했습니다.' })
  }
}

function confirmDelete() {
  $q.dialog({
    title: '게시글 삭제',
    message: '이 게시글을 삭제하시겠습니까?',
    cancel: true,
  }).onOk(() => { void (async () => {
    try {
      await boardService.deletePost(boardId.value, postId.value)
      goBack()
    } catch {
      $q.notify({ type: 'negative', message: '문서를 삭제할 수 없습니다. 하위 문서를 먼저 이동하거나 삭제해 주세요.' })
    }
  })() })
}

async function openHistory() {
  await router.push(`/board/${boardId.value}/post/${postId.value}/history`)
}

async function load() {
  loading.value = true
  try {
    const [boards, p, documents] = await Promise.all([
      boardService.listBoards(),
      boardService.getPost(boardId.value, postId.value),
      boardService.listPosts(boardId.value),
    ])
    boardTitle.value = boards.find((b) => b.id === boardId.value)?.title ?? '문서 관리'
    post.value = p
    allPosts.value = documents
    following.value = await boardService.getFollowStatus(boardId.value, postId.value).catch(() => false)
    commentsLoading.value = true
    comments.value = await boardService.listComments(boardId.value, postId.value).catch(() => [])
    commentsLoading.value = false
    const expandableIds = new Set(documents.filter((item) => documents.some((child) => child.parentId === item.id)).map((item) => item.id))
    const branchToExpand = new Set<string>()
    if (expandableIds.has(p.id)) branchToExpand.add(p.id)
    let ancestorId = p.parentId
    while (ancestorId && !branchToExpand.has(ancestorId)) {
      branchToExpand.add(ancestorId)
      ancestorId = documents.find((item) => item.id === ancestorId)?.parentId ?? null
    }
    collapsedIds.value = new Set([...expandableIds].filter((id) => !branchToExpand.has(id)))
    if (p.editorIds?.length) {
      try {
        const users = await listPmUsers()
        editorNames.value = Object.fromEntries(users.map((user) => [user.id, user.name || user.email]))
      } catch { /* 사용자 이름 조회 실패 시 ID 표시 */ }
    }
  } catch {
    commentsLoading.value = false
    $q.notify({ type: 'negative', message: '게시글을 찾을 수 없습니다.' })
    goBack()
  } finally {
    loading.value = false
  }
}

onMounted(() => { void load() })
watch(postId, () => { void load() })
</script>

<style scoped>
.board-post-detail-page { width: 100%; }
.board-post-detail-page :deep(.adoption-status-chip) {
  flex: 0 0 auto;
  max-width: none;
}
.board-post-detail-page :deep(.adoption-status-chip .q-chip__content) {
  white-space: nowrap;
}
.document-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  transition: grid-template-columns 180ms ease;
}
.document-detail-layout.document-nav-open {
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
}
.document-nav-panel,
.document-detail-main { min-width: 0; }
.document-nav-panel { overflow: hidden; }
@media (max-width: 700px) {
  .document-detail-layout.document-nav-open { grid-template-columns: minmax(0, 1fr); }
}
.pre-wrap { white-space: pre-wrap; word-break: break-word; }
</style>
