<template>
  <q-dialog :model-value="modelValue" persistent maximized transition-show="slide-up" transition-hide="slide-down"
    @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="column" style="width: 100%; height: 100%">
      <!-- Header -->
      <q-toolbar class="bg-primary text-white">
        <template v-if="issueStack.length > 0">
          <q-btn flat round dense icon="arrow_back" @click="goBack" class="q-mr-xs" />
          <span class="text-caption opacity-60 q-mr-sm" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px">
            {{ issueStack[issueStack.length - 1]?.title }}
          </span>
          <q-icon name="chevron_right" size="xs" class="opacity-60 q-mr-xs" />
        </template>
        <q-icon :name="TYPE_ICON[localIssue?.type ?? 'TASK']" class="q-mr-sm" />
        <span class="text-caption opacity-70 q-mr-sm" style="white-space: nowrap; flex-shrink: 0">{{ displayProjectKey }}-{{ localIssue?.number }}</span>
        <q-toolbar-title class="text-body1" style="min-width: 0">
          {{ localIssue?.title }}
        </q-toolbar-title>
        <q-btn flat round dense icon="close" @click="$emit('update:modelValue', false)" />
      </q-toolbar>

      <div class="col" style="position: relative; overflow: hidden; min-height: 0">
        <!-- 메인 콘텐츠 -->
        <div class="q-pa-md" style="position: absolute; top: 0; left: 0; right: 320px; bottom: 0; overflow-y: auto; overflow-x: hidden">
          <q-tabs v-model="tab" dense align="left" class="q-mb-md">
            <q-tab name="detail" label="상세" />
            <q-tab name="history" label="변경 이력" />
          </q-tabs>

          <q-tab-panels v-model="tab" animated>
            <!-- ── 상세 탭 ── -->
            <q-tab-panel name="detail" class="q-pa-none">
              <!-- 제목 -->
              <q-input
                v-model="editTitle"
                borderless
                dense
                class="text-h6 inline-field q-mb-xs"
                input-class="text-h6"
                @blur="saveField('title', editTitle)"
                @keydown.enter.prevent="saveField('title', editTitle)"
              />

              <!-- 연결된 SR 바로가기 -->
              <q-btn v-if="localIssue?.linkedSrId"
                flat dense no-caps
                icon="link" label="연결된 SR 바로가기"
                color="teal-7" class="q-mb-md text-caption"
                @click="emit('update:modelValue', false); void router.push(`/pm/sr/${localIssue.linkedSrId}`).catch(() => {})" />

              <!-- 설명 -->
              <div class="q-mb-md">
                <!-- 뷰 모드 -->
                <template v-if="!descriptionEditing">
                  <div
                    class="description-view rounded-borders q-pa-sm cursor-pointer"
                    @click="descriptionEditing = true"
                  >
                    <MarkdownContent v-if="editDescription?.trim()" :content="editDescription" />
                    <span v-else class="text-grey-5 text-body2">설명을 입력하세요...</span>
                  </div>
                </template>
                <!-- 편집 모드 -->
                <template v-else>
                  <MarkdownEditor v-model="editDescription" :rows="5" />
                  <div class="row q-gutter-xs q-mt-xs">
                    <q-btn unelevated size="sm" color="primary" label="저장" :loading="saving"
                      @click="saveField('description', editDescription).then(() => { descriptionEditing = false })" />
                    <q-btn flat size="sm" color="grey-7" label="취소"
                      @click="editDescription = localIssue?.description ?? ''; descriptionEditing = false" />
                  </div>
                </template>
              </div>

              <!-- 첨부파일 -->
              <template v-if="localIssue?.attachments?.length">
                <div class="text-caption text-grey-6 q-mb-xs">첨부파일</div>
                <div class="column q-gutter-xs q-mb-md">
                  <div v-for="att in localIssue.attachments" :key="att.fileId" class="row items-center q-gutter-xs">
                    <q-icon :name="fileIcon(att.contentType)" color="grey-7" size="18px" />
                    <a :href="att.url" target="_blank" class="text-caption text-primary" style="text-decoration:none">
                      {{ att.originalName }}
                    </a>
                    <span class="text-caption text-grey-5">({{ fmtSize(att.size) }})</span>
                  </div>
                </div>
              </template>

              <div class="text-caption text-grey-5 q-mb-lg">
                생성 {{ fmtDate(localIssue?.createdAt ?? '') }}
                · 수정 {{ fmtDate(localIssue?.updatedAt ?? '') }}
              </div>

              <!-- ── 하위 작업 (EPIC·SUB_TASK 제외) ── -->
              <template v-if="localIssue && localIssue.type !== 'EPIC' && localIssue.type !== 'SUB_TASK'">
                <q-separator class="q-mb-md" />
                <div class="text-subtitle2 q-mb-sm">하위 작업 {{ subIssues.length ? `(${subIssues.length})` : '' }}</div>
                <draggable
                  v-model="subIssues"
                  item-key="id"
                  handle=".drag-handle"
                  class="column q-gutter-xs q-mb-sm"
                  @end="onSubTaskDragEnd"
                >
                  <template #item="{ element: sub }">
                    <div class="row items-center q-px-sm q-py-xs sub-task-row no-wrap">
                      <q-icon name="drag_indicator" class="drag-handle text-grey-4 q-mr-xs" size="16px" style="cursor:grab" />
                      <q-checkbox
                        :model-value="(sub as Issue).status === 'DONE'"
                        dense
                        class="q-mr-xs"
                        @update:model-value="toggleSubTaskDone(sub as Issue)"
                      />
                      <span
                        class="text-body2 col ellipsis cursor-pointer"
                        :class="{ 'text-strike text-grey-5': (sub as Issue).status === 'DONE' }"
                        @click="drillDown(sub as Issue)"
                      >{{ (sub as Issue).title }}</span>
                      <span v-if="(sub as Issue).startDate" class="text-caption text-grey-5 q-ml-sm" style="white-space:nowrap">
                        {{ (sub as Issue).startDate!.slice(0, 10) }}
                      </span>
                      <q-avatar
                        v-if="(sub as Issue).assigneeName"
                        size="20px" color="primary" text-color="white"
                        class="q-ml-sm text-caption" style="font-size:10px;flex-shrink:0"
                      >{{ (sub as Issue).assigneeName![0] }}</q-avatar>
                    </div>
                  </template>
                  <template #footer>
                    <div v-if="subIssues.length === 0 && !addingSubTask" class="text-grey-6 text-caption q-px-sm">하위 작업이 없습니다.</div>
                  </template>
                </draggable>

                <!-- 인라인 추가 폼 -->
                <div v-if="addingSubTask" class="row q-gutter-sm items-center q-mb-md">
                  <q-input
                    v-model="newSubTaskTitle"
                    class="col"
                    dense outlined
                    placeholder="하위 작업 제목..."
                    autofocus
                    @keydown.enter="submitSubTask"
                    @keydown.esc="addingSubTask = false"
                  />
                  <q-btn color="primary" label="추가" size="sm" :loading="subTaskLoading" @click="submitSubTask" />
                  <q-btn flat label="취소" size="sm" @click="addingSubTask = false" />
                </div>
                <q-btn
                  v-else
                  flat dense size="sm" icon="add" label="하위 작업 추가" color="primary"
                  class="q-mb-md"
                  @click="addingSubTask = true; newSubTaskTitle = ''"
                />
              </template>

              <!-- ── 댓글 ── -->
              <q-separator class="q-mb-md" />
              <div class="text-subtitle2 q-mb-sm">댓글 {{ comments.length ? `(${comments.length})` : '' }}</div>
              <div class="column q-gutter-sm q-mb-md">
                <div v-if="topComments.length === 0" class="text-grey-6 text-caption">댓글이 없습니다.</div>
                <template v-for="c in topComments" :key="c.id">
                  <!-- 최상위 댓글 -->
                  <q-card flat bordered>
                    <q-card-section class="q-py-sm">
                      <div class="row items-center q-mb-xs">
                        <span class="text-caption text-weight-bold">{{ c.authorName }}</span>
                        <span class="text-caption text-grey-5 q-ml-sm">{{ fmtDate(c.createdAt) }}</span>
                        <q-space />
                        <q-btn flat dense round icon="reply" size="xs" color="primary" @click="toggleReply(c.id)" />
                        <q-btn flat dense round icon="delete" size="xs" color="negative" @click="removeComment(c.id)" />
                      </div>
                      <MentionContent
                        v-if="c.content"
                        :content="c.content"
                        :mentioned-users="c.mentionedUsers || []"
                        class="text-body2"
                      />
                      <!-- 첨부파일 -->
                      <div v-if="c.attachments?.length" class="q-mt-sm">
                        <CommentAttachments :attachments="c.attachments" />
                      </div>
                    </q-card-section>

                    <!-- 답글 목록 -->
                    <template v-if="repliesOf(c.id).length > 0">
                      <q-separator />
                      <q-card-section class="q-py-xs q-pl-lg">
                        <div v-for="r in repliesOf(c.id)" :key="r.id" class="q-py-xs reply-item">
                          <div class="row items-center">
                            <q-icon name="subdirectory_arrow_right" size="xs" color="grey-5" class="q-mr-xs" />
                            <span class="text-caption text-weight-bold">{{ r.authorName }}</span>
                            <span class="text-caption text-grey-5 q-ml-sm">{{ fmtDate(r.createdAt) }}</span>
                            <q-space />
                            <q-btn flat dense round icon="delete" size="xs" color="negative" @click="removeComment(r.id)" />
                          </div>
                          <MentionContent
                            v-if="r.content"
                            :content="r.content"
                            :mentioned-users="r.mentionedUsers || []"
                            class="text-body2 q-pl-md"
                          />
                          <div v-if="r.attachments?.length" class="q-pl-md q-mt-xs">
                            <CommentAttachments :attachments="r.attachments" />
                          </div>
                        </div>
                      </q-card-section>
                    </template>

                    <!-- 인라인 답글 입력 -->
                    <template v-if="replyingTo === c.id">
                      <q-separator />
                      <q-card-section class="q-py-sm q-pl-lg">
                        <div class="row q-gutter-sm items-stretch">
                          <MentionInput
                            v-model="replyText"
                            v-model:mentioned-users="replyMentionedUsers"
                            class="col"
                            :rows="2"
                            placeholder="답글 작성... (@로 멘션)"
                            :dense="true"
                          />
                          <div class="column q-gutter-xs justify-center">
                            <q-btn color="primary" label="등록" size="sm" :loading="commentLoading" @click="submitReply(c.id)" />
                            <q-btn flat label="취소" size="sm" @click="replyingTo = null" />
                          </div>
                        </div>
                      </q-card-section>
                    </template>
                  </q-card>
                </template>
              </div>
              <!-- 댓글 입력 -->
              <div class="column q-gutter-md">
                <!-- 파일 입력 (hidden) -->
                <input
                  ref="fileInputRef"
                  type="file"
                  multiple
                  accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.zip"
                  style="display:none"
                  @change="onFileInputChange"
                />

                <div @paste="handleCommentPaste">
                  <MentionInput
                    v-model="newComment"
                    v-model:mentioned-users="mentionedUsers"
                    :rows="3"
                    placeholder="댓글 작성... (@로 멘션, 이미지 붙여넣기 가능)"
                  />
                </div>

                <!-- 첨부 파일 프리뷰 -->
                <div v-if="pendingFiles.length > 0" class="row q-gutter-sm q-pa-xs attachment-preview-area">
                  <div
                    v-for="pf in pendingFiles"
                    :key="pf.id"
                    class="attachment-preview-item"
                  >
                    <div class="relative-position">
                      <img v-if="pf.preview" :src="pf.preview" class="preview-img" />
                      <div v-else class="preview-file-chip row items-center q-gutter-xs q-px-sm q-py-xs">
                        <q-icon name="attach_file" size="xs" color="grey-6" />
                        <span class="text-caption ellipsis" style="max-width:120px">{{ pf.file.name }}</span>
                        <span class="text-caption text-grey-5">{{ fmtSize(pf.file.size) }}</span>
                      </div>
                      <!-- 업로드 중 오버레이 -->
                      <div v-if="pf.uploading" class="preview-overlay">
                        <q-spinner color="white" size="sm" />
                      </div>
                      <div v-if="pf.error" class="preview-overlay preview-error">
                        <q-icon name="error" color="white" size="sm" />
                      </div>
                      <q-btn
                        round flat dense
                        icon="close"
                        size="xs"
                        color="grey-7"
                        class="preview-remove-btn"
                        @click="removePendingFile(pf.id)"
                      />
                    </div>
                  </div>
                </div>

                <!-- 버튼 행 -->
                <div class="row items-center q-gutter-sm">
                  <q-btn
                    flat dense no-caps
                    icon="attach_file"
                    label="파일 첨부"
                    color="grey-7"
                    size="sm"
                    @click="fileInputRef?.click()"
                  />
                  <q-space />
                  <q-btn color="primary" label="등록" :loading="commentLoading" no-caps @click="addComment" />
                  <q-btn flat label="취소" no-caps @click="newComment = ''; pendingFiles = []" />
                </div>
              </div>
            </q-tab-panel>

            <!-- ── 변경 이력 탭 ── -->
            <q-tab-panel name="history" class="q-pa-none">
              <div v-if="history.length === 0" class="text-grey-6 text-caption">변경 이력이 없습니다.</div>
              <q-list separator>
                <q-item v-for="h in history" :key="h.id" dense>
                  <q-item-section>
                    <q-item-label class="text-caption">
                      <span class="text-weight-bold">{{ h.userName }}</span>
                      이(가) <span class="text-primary">{{ historyAction(h) }}</span>:
                      <template v-if="h.field === 'comment'">
                        <template v-if="!h.oldValue">{{ h.newValue }}</template>
                        <template v-else-if="!h.newValue">{{ h.oldValue }}</template>
                        <template v-else>
                          <span class="text-grey-6 text-strike">{{ h.oldValue }}</span>
                          → <span class="text-positive">{{ h.newValue }}</span>
                        </template>
                      </template>
                      <template v-else>
                        <span class="text-grey-6 text-strike">{{ h.oldValue ?? '(없음)' }}</span>
                        → <span class="text-positive">{{ h.newValue ?? '(없음)' }}</span>
                      </template>
                    </q-item-label>
                    <q-item-label caption>{{ fmtDate(h.createdAt) }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>
          </q-tab-panels>
        </div>

        <!-- 사이드바 -->
        <div class="q-pa-md bg-grey-1 sidebar-panel" style="position: absolute; top: 0; right: 0; width: 320px; bottom: 0; overflow-y: auto; overflow-x: hidden; border-left: 1px solid #e0e0e0">
          <div class="column q-gutter-md">

            <div>
              <div class="sidebar-label">상태</div>
              <q-select v-model="localStatus" :options="statusOptions" dense outlined emit-value map-options
                @update:model-value="patchField('status', $event)" />
            </div>

            <div>
              <div class="sidebar-label">타입</div>
              <q-select v-model="localType" :options="typeOptions" dense outlined emit-value map-options
                @update:model-value="patchField('type', $event)" />
            </div>

            <div>
              <div class="sidebar-label">우선순위</div>
              <q-select v-model="localPriority" :options="priorityOptions" dense outlined emit-value map-options
                @update:model-value="patchField('priority', $event)" />
            </div>

            <q-separator />

            <div>
              <div class="sidebar-label">담당자</div>
              <q-select v-model="localAssigneeId" :options="memberOptions" dense outlined emit-value map-options clearable
                @update:model-value="patchField('assignee_id', $event)">
                <template #prepend>
                  <q-icon name="person" color="grey-6" size="18px" />
                </template>
              </q-select>
            </div>

            <div>
              <div class="sidebar-label">보고자</div>
              <div class="text-body2 q-py-xs">{{ localIssue?.reporterName || '-' }}</div>
            </div>

            <q-separator />

            <div>
              <div class="sidebar-label">스프린트</div>
              <q-select v-model="localSprintId" :options="sprintOptions" dense outlined emit-value map-options clearable
                @update:model-value="patchField('sprint_id', $event)" />
            </div>

            <div v-if="localIssue?.type !== 'EPIC'">
              <div class="sidebar-label">상위 Epic</div>
              <q-select v-model="localEpicId" :options="epicOptions" dense outlined emit-value map-options clearable
                @update:model-value="patchField('epic_id', $event)">
                <template #prepend>
                  <q-icon name="bolt" color="purple" size="18px" />
                </template>
              </q-select>
            </div>

            <div v-if="localIssue?.type !== 'EPIC'">
              <div class="sidebar-label">스토리 포인트</div>
              <q-input v-model.number="localStoryPoints" dense outlined type="number" :min="0" :max="999"
                @blur="patchField('story_points', localStoryPoints)" />
            </div>

            <div>
              <div class="sidebar-label">공수</div>
              <div style="display: flex; gap: 4px">
                <q-input v-model.number="localEffortValue" dense outlined type="number" :min="0"
                  style="flex: 1"
                  @blur="saveEffort" />
                <q-select v-model="localEffortUnit" :options="['일', '시간', '분']"
                  dense outlined style="width: 64px"
                  @update:model-value="saveEffort" />
              </div>
            </div>

            <q-separator />

            <div>
              <div class="sidebar-label">시작일</div>
              <q-input v-model="localStartDate" dense outlined type="date" stack-label
                @blur="patchField('start_date', localStartDate ? new Date(localStartDate).toISOString() : null)" />
            </div>

            <div>
              <div class="sidebar-label">마감일</div>
              <q-input v-model="localDueDate" dense outlined type="date" stack-label
                @blur="patchField('due_date', localDueDate ? new Date(localDueDate).toISOString() : null)" />
            </div>

            <q-separator />

            <div>
              <div class="sidebar-label">라벨</div>
              <q-select v-model="localLabelIds" :options="labelOptions" dense outlined emit-value map-options
                multiple use-chips @update:model-value="patchField('label_ids', $event)">
                <template #selected-item="{ opt, removeAtIndex, index }">
                  <q-chip dense removable
                    :style="{ backgroundColor: labelColorMap[opt.value] ?? '#6b7280', color: '#fff' }"
                    @remove="removeAtIndex(index)">
                    {{ opt.label }}
                  </q-chip>
                </template>
                <template #option="{ opt, itemProps }">
                  <q-item v-bind="itemProps">
                    <q-item-section avatar>
                      <q-badge :style="{ backgroundColor: opt.color }" :label="' '" class="q-px-sm" />
                    </q-item-section>
                    <q-item-section>{{ opt.label }}</q-item-section>
                  </q-item>
                </template>
              </q-select>
            </div>

            <q-separator />

            <q-btn flat dense color="negative" icon="delete" label="이슈 삭제" @click="confirmDelete" />
          </div>
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, defineComponent, h, type PropType } from 'vue'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import MarkdownContent from 'src/components/MarkdownContent.vue'
import { useRouter } from 'vue-router'
import { QIcon, QBtn } from 'quasar'
import draggable from 'vuedraggable'

// 첨부파일 표시 인라인 컴포넌트
const CommentAttachments = defineComponent({
  props: { attachments: { type: Array as PropType<Attachment[]>, required: true } },
  setup(props) {
    return () => h('div', { class: 'comment-attachments' },
      props.attachments.map(a =>
        a.contentType.startsWith('image/')
          ? h('a', { href: a.url, target: '_blank', class: 'comment-img-wrap' },
              h('img', { src: a.url, class: 'comment-img', alt: a.originalName }))
          : h('a', {
              href: a.url, target: '_blank', download: a.originalName,
              class: 'comment-file-chip row items-center q-gutter-xs no-decoration',
            }, [
              h(QIcon, { name: 'attach_file', size: 'xs', color: 'grey-6' }),
              h('span', { class: 'text-caption' }, a.originalName),
              h('span', { class: 'text-caption text-grey-5' }, fmtSize(a.size)),
            ])
      )
    )
  },
})
import { Notify, Dialog } from 'quasar'
import {
  updateIssue, deleteIssue, listIssues, createIssue,
  listComments, createComment, deleteComment,
  uploadAttachment,
  getIssueHistory, listLabels,
  ISSUE_STATUSES, STATUS_LABEL,
  TYPE_ICON,
  type Issue, type IssueStatus, type IssueType, type IssuePriority,
  type IssueComment, type IssueHistory, type Label, type Attachment,
} from 'src/services/pm/issue'
import MentionInput from 'components/MentionInput.vue'
import MentionContent from 'components/MentionContent.vue'
import type { MentionUser } from 'src/services/mention'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import { listProjectMembers, type ProjectMember } from 'src/services/pm/project'
import { getErrorMessage } from 'src/utils/http/error'
import { fmtDatetimeKst } from 'src/utils/time/kst'

const props = defineProps<{
  modelValue: boolean
  projectId: string
  projectKey?: string
  issue: Issue | null
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  'updated': [Issue]
  'deleted': [string]
}>()

const router = useRouter()
const tab = ref('detail')

const displayProjectKey = computed(() => props.projectKey ?? props.issue?.projectKey ?? '')
const saving = ref(false)
const editTitle = ref('')
const editDescription = ref('')
const descriptionEditing = ref(false)

const comments = ref<IssueComment[]>([])
const history = ref<IssueHistory[]>([])
const newComment = ref('')
const mentionedUsers = ref<MentionUser[]>([])
const commentLoading = ref(false)
const replyingTo = ref<string | null>(null)
const replyText = ref('')
const replyMentionedUsers = ref<MentionUser[]>([])

// ── 첨부파일 상태 ──────────────────────────────────────────────────
interface PendingFile {
  id: string
  file: File
  preview: string | null  // 이미지일 때 data URL
  attachment: Attachment | null  // 업로드 완료 후 채워짐
  uploading: boolean
  error: boolean
}
const pendingFiles = ref<PendingFile[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

function isImage(file: File | Attachment): boolean {
  const type = 'contentType' in file ? file.contentType : file.type
  return type.startsWith('image/')
}

async function addPendingFile(file: File) {
  const id = crypto.randomUUID()
  const preview = isImage(file) ? await new Promise<string | null>(resolve => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target?.result as string)
    reader.onerror = () => resolve(null)
    reader.readAsDataURL(file)
  }) : null
  pendingFiles.value.push({ id, file, preview, attachment: null, uploading: true, error: false })

  try {
    const attachment = await uploadAttachment(file)
    const pf = pendingFiles.value.find(p => p.id === id)
    if (pf) {
      pf.attachment = attachment
      pf.uploading = false
    }
  } catch (e) {
    const pf = pendingFiles.value.find(p => p.id === id)
    if (pf) {
      pf.uploading = false
      pf.error = true
    }
    Notify.create({ type: 'negative', message: `"${file.name}" ${getErrorMessage(e, '업로드 실패')}` })
  }
}

function removePendingFile(id: string) {
  pendingFiles.value = pendingFiles.value.filter(p => p.id !== id)
}

function onFileInputChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files) return
  for (const file of Array.from(files)) void addPendingFile(file)
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function handleCommentPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        void addPendingFile(file)
      }
    }
  }
}

const topComments = computed(() => comments.value.filter(c => !c.parentId))
function repliesOf(parentId: string) {
  return comments.value.filter(c => c.parentId === parentId)
}
function toggleReply(commentId: string) {
  if (replyingTo.value === commentId) {
    replyingTo.value = null
  } else {
    replyingTo.value = commentId
    replyText.value = ''
  }
}
const sprints = ref<Sprint[]>([])
const members = ref<ProjectMember[]>([])
const labelsData = ref<Label[]>([])
const epics = ref<Issue[]>([])

const localIssue = ref<Issue | null>(null)
const localStatus = ref<IssueStatus>('BACKLOG')
const localType = ref<IssueType>('TASK')
const localPriority = ref<IssuePriority>('MEDIUM')
const localSprintId = ref<string | null>(null)
const localLabelIds = ref<string[]>([])
const localAssigneeId = ref<string | null>(null)
const localEpicId = ref<string | null>(null)
const localStoryPoints = ref<number | null>(null)
const localEffortValue = ref<number | null>(null)
const localEffortUnit = ref<string>('일')
const localStartDate = ref('')
const localDueDate = ref('')

// 하위 작업
const subIssues = ref<Issue[]>([])
const addingSubTask = ref(false)
const newSubTaskTitle = ref('')
const subTaskLoading = ref(false)

// 드릴다운 네비게이션 스택
const issueStack = ref<Issue[]>([])

const FIELD_LABEL: Record<string, string> = {
  title: '제목',
  description: '설명',
  type: '유형',
  status: '상태',
  priority: '우선순위',
  assignee_id: '담당자',
  sprint_id: '스프린트',
  epic_id: 'Epic',
  parent_issue_id: '상위 이슈',
  label_ids: '라벨',
  start_date: '시작일',
  due_date: '마감일',
  story_points: '스토리 포인트',
  effort_md: '공수',
  comment: '댓글',
}

const statusOptions = ISSUE_STATUSES.map(s => ({ label: STATUS_LABEL[s], value: s }))
const typeOptions = [
  { label: 'Epic', value: 'EPIC' },
  { label: 'Story', value: 'STORY' },
  { label: 'Task', value: 'TASK' },
  { label: 'Bug', value: 'BUG' },
  { label: 'Sub-task', value: 'SUB_TASK' },
]
const priorityOptions = [
  { label: '최고', value: 'HIGHEST' },
  { label: '높음', value: 'HIGH' },
  { label: '보통', value: 'MEDIUM' },
  { label: '낮음', value: 'LOW' },
  { label: '최저', value: 'LOWEST' },
]
const sprintOptions = computed(() => sprints.value.map(s => ({ label: s.name, value: s.id })))
const memberOptions = computed(() =>
  members.value.map(m => ({ label: m.userName || m.userEmail, value: m.userId }))
)
const epicOptions = computed(() =>
  epics.value
    .filter(e => e.id !== localIssue.value?.id)
    .map(e => ({ label: `#${e.number} ${e.title}`, value: e.id }))
)
const labelOptions = computed(() => labelsData.value.map(l => ({ label: l.name, value: l.id, color: l.color })))
const labelColorMap = computed(() => Object.fromEntries(labelsData.value.map(l => [l.id, l.color])))

async function loadIssueContent(issue: Issue) {
  localIssue.value = { ...issue }
  localStatus.value = issue.status
  localType.value = issue.type
  localPriority.value = issue.priority
  localSprintId.value = issue.sprintId
  localLabelIds.value = [...(issue.labelIds ?? [])]
  localAssigneeId.value = issue.assigneeId
  localEpicId.value = issue.epicId
  localStoryPoints.value = issue.storyPoints
  if (issue.effortMd) {
    const m = issue.effortMd.match(/^([\d.]+)\s*(.+)$/)
    localEffortValue.value = m ? parseFloat(m[1]!) : null
    const unit = m ? m[2]!.trim() : '일'
    localEffortUnit.value  = unit === 'MD' ? '일' : unit
  } else {
    localEffortValue.value = null
    localEffortUnit.value  = '일'
  }
  localStartDate.value = issue.startDate?.slice(0, 10) ?? ''
  localDueDate.value = issue.dueDate?.slice(0, 10) ?? ''
  editTitle.value = issue.title
  editDescription.value = issue.description ?? ''
  descriptionEditing.value = false
  addingSubTask.value = false
  replyingTo.value = null

  try {
    const [cmts, hist, subs, sp, lbls, mems, eps] = await Promise.all([
      listComments(props.projectId, issue.id),
      getIssueHistory(props.projectId, issue.id),
      listIssues(props.projectId, { parent_issue_id: issue.id, type: 'SUB_TASK' }),
      listSprints(props.projectId),
      listLabels(props.projectId),
      listProjectMembers(props.projectId),
      listIssues(props.projectId, { type: 'EPIC' }),
    ])
    comments.value = cmts
    history.value = hist
    subIssues.value = subs
      .filter(s => s.type === 'SUB_TASK' && s.id !== issue.id)
      .sort((a, b) => {
        if (a.order !== b.order) return a.order - b.order
        if (!a.startDate && !b.startDate) return 0
        if (!a.startDate) return 1
        if (!b.startDate) return -1
        return a.startDate.localeCompare(b.startDate)
      })
    sprints.value = sp
    labelsData.value = lbls
    members.value = mems
    epics.value = eps
  } catch {
    // ignore
  }
}

function drillDown(sub: Issue) {
  if (!localIssue.value) return
  issueStack.value.push({ ...localIssue.value })
  tab.value = 'detail'
  void loadIssueContent(sub)
}

function goBack() {
  const parent = issueStack.value.pop()
  if (parent) {
    tab.value = 'detail'
    void loadIssueContent(parent)
  }
}

function onSubTaskDragEnd() {
  subIssues.value.forEach((sub, idx) => {
    void updateIssue(props.projectId, sub.id, { order: idx })
  })
}

async function toggleSubTaskDone(sub: Issue) {
  const newStatus = sub.status === 'DONE' ? 'TODO' : 'DONE'
  try {
    const updated = await updateIssue(props.projectId, sub.id, { status: newStatus })
    const idx = subIssues.value.findIndex(s => s.id === sub.id)
    if (idx !== -1) subIssues.value[idx] = updated
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '상태 변경 실패') })
  }
}

async function submitSubTask() {
  if (!localIssue.value || !newSubTaskTitle.value.trim()) return
  subTaskLoading.value = true
  try {
    const created = await createIssue(props.projectId, {
      title: newSubTaskTitle.value.trim(),
      type: 'SUB_TASK',
      parent_issue_id: localIssue.value.id,
      assignee_id: localIssue.value.assigneeId,
    })
    subIssues.value.push(created)
    newSubTaskTitle.value = ''
    addingSubTask.value = false
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '하위 작업 추가 실패') })
  } finally {
    subTaskLoading.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open && props.issue) {
    issueStack.value = []
    tab.value = 'detail'
    void loadIssueContent(props.issue)
  } else if (!open) {
    issueStack.value = []
  }
}, { immediate: true })

function fmtDate(d: string) { return fmtDatetimeKst(d) }

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

function fileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return 'image'
  if (contentType === 'application/pdf') return 'picture_as_pdf'
  if (contentType.includes('spreadsheet') || contentType.includes('excel')) return 'table_chart'
  if (contentType.includes('word')) return 'description'
  return 'attach_file'
}

async function reloadHistory() {
  if (!localIssue.value) return
  try {
    history.value = await getIssueHistory(props.projectId, localIssue.value.id)
  } catch { /* ignore */ }
}

async function saveField(field: 'title' | 'description', value: string) {
  if (!localIssue.value) return
  const trimmed = value.trim()
  if (field === 'title' && !trimmed) {
    editTitle.value = localIssue.value.title
    return
  }
  const current = field === 'title' ? localIssue.value.title : (localIssue.value.description ?? '')
  if (trimmed === current.trim()) return
  saving.value = true
  try {
    const updated = await updateIssue(props.projectId, localIssue.value.id, { [field]: trimmed })
    localIssue.value = updated
    emit('updated', updated)
    void reloadHistory()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
    editTitle.value = localIssue.value.title
    editDescription.value = localIssue.value.description ?? ''
  } finally {
    saving.value = false
  }
}

function historyAction(h: IssueHistory): string {
  if (h.field === 'comment') {
    if (!h.oldValue) return '댓글 등록'
    if (!h.newValue) return '댓글 삭제'
    return '댓글 수정'
  }
  return `${FIELD_LABEL[h.field] ?? h.field} 변경`
}

function saveEffort() {
  const val = localEffortValue.value != null
    ? `${localEffortValue.value} ${localEffortUnit.value}`
    : null
  void patchField('effort_md', val)
}

async function patchField(field: string, value: unknown) {
  if (!localIssue.value) return
  try {
    const updated = await updateIssue(props.projectId, localIssue.value.id, { [field]: value })
    localIssue.value = updated
    emit('updated', updated)
    void reloadHistory()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '변경 실패') })
    if (localIssue.value) {
      localStatus.value = localIssue.value.status
      localType.value = localIssue.value.type
      localPriority.value = localIssue.value.priority
      localSprintId.value = localIssue.value.sprintId
      localAssigneeId.value = localIssue.value.assigneeId
    }
  }
}

async function addComment() {
  if (!localIssue.value) return
  const text = newComment.value.trim()
  const attachments = pendingFiles.value
    .filter(p => p.attachment && !p.error)
    .map(p => p.attachment as Attachment)
  if (!text && attachments.length === 0) return
  if (pendingFiles.value.some(p => p.uploading)) {
    Notify.create({ type: 'warning', message: '파일 업로드가 완료될 때까지 기다려 주세요.' })
    return
  }
  commentLoading.value = true
  try {
    const mentionIds = mentionedUsers.value.map(m => m.userId)
    const c = await createComment(props.projectId, localIssue.value.id, text, undefined, attachments, mentionIds)
    comments.value.push(c)
    newComment.value = ''
    mentionedUsers.value = []
    pendingFiles.value = []
    void reloadHistory()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '댓글 등록 실패') })
  } finally {
    commentLoading.value = false
  }
}

async function submitReply(parentId: string) {
  if (!localIssue.value || !replyText.value.trim()) return
  commentLoading.value = true
  try {
    const mentionIds = replyMentionedUsers.value.map(m => m.userId)
    const c = await createComment(props.projectId, localIssue.value.id, replyText.value.trim(), parentId, [], mentionIds)
    comments.value.push(c)
    replyText.value = ''
    replyMentionedUsers.value = []
    replyingTo.value = null
    void reloadHistory()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '답글 등록 실패') })
  } finally {
    commentLoading.value = false
  }
}

function removeComment(commentId: string) {
  if (!localIssue.value) return
  Dialog.create({
    title: '댓글 삭제',
    message: '이 댓글을 삭제하시겠습니까?',
    cancel: true,
    persistent: true,
    ok: { color: 'negative', label: '삭제' },
  }).onOk(() => {
    void (async () => {
      try {
        await deleteComment(props.projectId, localIssue.value!.id, commentId)
        comments.value = comments.value.filter(c => c.id !== commentId && c.parentId !== commentId)
        void reloadHistory()
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

function confirmDelete() {
  if (!localIssue.value) return
  Dialog.create({
    title: '이슈 삭제',
    message: `"${localIssue.value.title}"을 삭제하시겠습니까?`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteIssue(props.projectId, localIssue.value!.id)
        emit('deleted', localIssue.value!.id)
        emit('update:modelValue', false)
        Notify.create({ type: 'positive', message: '삭제되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}
</script>

<style scoped>
.inline-field :deep(.q-field__control) {
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}
.inline-field :deep(.q-field__control:hover),
.inline-field :deep(.q-field__control:focus-within) {
  background: rgba(0, 0, 0, 0.04);
}
/* 긴 셀렉트 라벨(에픽 제목 등)이 사이드바 폭을 밀어내지 못하도록 고정 */
.sidebar-panel .column > div,
.sidebar-panel .column > * {
  min-width: 0;
  max-width: 100%;
}
.sidebar-panel :deep(.q-field) {
  max-width: 100%;
}
.sidebar-panel :deep(.q-field__native) {
  overflow: hidden;
}
.sidebar-panel :deep(.q-field__native > span) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9e9e9e;
  margin-bottom: 4px;
}
.reply-item {
  border-left: 2px solid #e0e0e0;
  padding-left: 8px;
}
.sub-task-row {
  border-radius: 4px;
  transition: background 0.12s;
}
.sub-task-row:hover {
  background: rgba(0, 0, 0, 0.04);
}

/* ── 첨부파일 프리뷰 (입력 영역) ── */
.attachment-preview-area {
  flex-wrap: wrap;
}
.attachment-preview-item .relative-position {
  display: inline-flex;
  align-items: center;
}
.preview-img {
  max-height: 80px;
  max-width: 120px;
  border-radius: 6px;
  object-fit: cover;
  border: 1px solid #e0e0e0;
}
.preview-file-chip {
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  max-width: 180px;
}
.preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.45);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-error { background: rgba(180,0,0,0.5); }
.preview-remove-btn {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}

/* ── 댓글 내 첨부파일 표시 ── */
.comment-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.comment-img-wrap {
  display: inline-block;
}
.comment-img {
  max-height: 200px;
  max-width: 100%;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  cursor: zoom-in;
  display: block;
}
.comment-file-chip {
  display: inline-flex;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 4px 10px;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
}
.comment-file-chip:hover {
  background: #eeeeee;
}
.no-decoration { text-decoration: none; }

/* ── 설명 뷰 모드 (클릭해서 편집) ── */
.description-view {
  min-height: 48px;
  border: 1px solid transparent;
  transition: border-color 0.15s, background 0.15s;
}
.description-view:hover {
  border-color: rgba(0, 0, 0, 0.15);
  background: rgba(0, 0, 0, 0.03);
}
</style>
