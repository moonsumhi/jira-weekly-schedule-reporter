<template>
  <q-dialog :model-value="modelValue" @update:model-value="onDialogModelUpdate" @show="onDialogShow">
    <q-card style="width: 1080px; max-width: 96vw">

      <!-- 헤더 -->
      <q-card-section class="row items-center q-pb-none q-pt-md q-px-lg">
        <div>
          <div class="text-h6 text-weight-bold">이슈 추가</div>
          <div class="text-caption text-grey-6">새 이슈를 생성합니다</div>
        </div>
        <q-space />
        <q-btn flat round dense icon="close" @click="onDialogModelUpdate(false)" />
      </q-card-section>

      <q-separator class="q-mt-md" />

      <!-- 폼 본문 -->
      <q-card-section class="q-px-lg q-pt-sm q-pb-none" style="max-height: 70vh; overflow-y: auto">

        <!-- ── 기본 정보 ── -->
        <div class="section-label q-mt-sm q-mb-sm">기본 정보</div>
        <div style="display: flex; flex-direction: column; gap: 12px">
          <q-input
            ref="titleInputRef"
            v-model="form.title"
            label="제목 *"
            outlined dense hide-bottom-space
          />
          <div style="display: flex; gap: 12px">
            <q-select
              v-model="form.type"
              :options="typeOptions"
              label="타입"
              outlined dense emit-value map-options
              style="flex: 1"
            >
              <template #prepend>
                <q-icon :name="typeIcon(form.type)" :color="typeColor(form.type)" size="18px" />
              </template>
            </q-select>
            <q-select
              v-model="form.priority"
              :options="priorityOptions"
              label="우선순위"
              outlined dense emit-value map-options
              style="flex: 1"
            >
              <template #prepend>
                <q-icon name="flag" :color="priorityColor(form.priority)" size="18px" />
              </template>
              <template #option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section avatar>
                    <q-icon name="flag" :color="priorityColor(scope.opt.value)" size="18px" />
                  </q-item-section>
                  <q-item-section>{{ scope.opt.label }}</q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-select
              v-model="form.status"
              :options="statusOptions"
              label="상태"
              outlined dense emit-value map-options
              style="flex: 1"
            />
          </div>
        </div>

        <q-separator class="q-my-md" />

        <!-- ── 담당 ── -->
        <div class="section-label q-mb-sm">담당</div>
        <div style="display: flex; flex-direction: column; gap: 12px">
          <div style="display: flex; gap: 12px">
            <q-select
              v-model="form.assigneeId"
              :options="memberOptions"
              :label="form.type === 'TASK' ? '담당자 *' : '담당자'"
              outlined dense emit-value map-options clearable
              style="flex: 1"
            >
              <template #prepend>
                <q-icon name="person" color="grey-6" size="18px" />
              </template>
            </q-select>
            <q-input
              :model-value="reporterName"
              label="보고자"
              outlined dense readonly
              style="flex: 1"
            >
              <template #prepend>
                <q-icon name="person_outline" color="grey-6" size="18px" />
              </template>
            </q-input>
          </div>
          <div v-if="form.type !== 'EPIC'" style="display: flex; gap: 12px">
            <q-select
              v-model="form.epicId"
              :options="epicOptions"
              :label="form.type === 'TASK' ? '상위 Epic *' : '상위 Epic'"
              outlined dense emit-value map-options clearable
              style="flex: 1"
            >
              <template #prepend>
                <q-icon name="bolt" color="purple" size="18px" />
              </template>
            </q-select>
            <q-input
              v-model.number="form.storyPoints"
              label="스토리 포인트"
              outlined dense
              type="number"
              :min="0"
              :max="999"
              style="flex: 1"
            >
              <template #prepend>
                <q-icon name="speed" color="grey-6" size="18px" />
              </template>
            </q-input>
          </div>
        </div>

        <q-separator class="q-my-md" />

        <!-- ── 일정 ── -->
        <div class="section-label q-mb-sm">일정</div>
        <div style="display: flex; gap: 12px">
          <q-select
            v-model="form.sprintId"
            :options="sprintOptions"
            label="스프린트"
            outlined dense emit-value map-options clearable
            style="flex: 1"
          >
            <template #prepend>
              <q-icon name="loop" color="grey-6" size="18px" />
            </template>
          </q-select>
          <q-input
            v-model="form.startDate"
            :label="form.type === 'TASK' ? '시작일 *' : '시작일'"
            outlined dense
            type="date"
            stack-label
            style="flex: 1"
          />
          <q-input
            v-model="form.dueDate"
            :label="form.type === 'TASK' ? '마감일 *' : '마감일'"
            outlined dense
            type="date"
            stack-label
            style="flex: 1"
          />
          <div style="flex: 0 0 auto; display: flex; align-items: center">
            <q-checkbox v-model="form.showOnDashboard" label="대시보드 D-Day 표시" dense>
              <q-tooltip>완료 처리 전까지 담당자 대시보드의 D-Day 카드에 마감일이 표시됩니다.</q-tooltip>
            </q-checkbox>
          </div>
        </div>
        <div style="display: flex; gap: 12px; margin-top: 12px">
          <q-input
            v-model.number="form.effortValue"
            label="공수 (일)"
            outlined dense
            type="number"
            :min="0"
            step="0.001"
            stack-label
            style="flex: 0 0 160px"
          />
        </div>

        <q-separator class="q-my-md" />

        <!-- ── 기타 ── -->
        <div class="section-label q-mb-sm">기타</div>
        <div style="display: flex; flex-direction: column; gap: 12px; padding-bottom: 16px">
          <q-select
            v-model="form.labelIds"
            :options="labelOptions"
            label="라벨"
            outlined dense emit-value map-options
            multiple use-chips
          >
            <template #selected-item="{ opt, removeAtIndex, index }">
              <q-chip
                dense removable
                :style="{ backgroundColor: labelColorMap[opt.value] ?? '#6b7280', color: '#fff' }"
                @remove="removeAtIndex(index)"
              >
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
          <MarkdownEditor
            v-model="form.description"
            label="설명"
            :rows="5"
          />

          <!-- 첨부파일 -->
          <div>
            <div class="row items-center q-mb-xs">
              <span class="section-label">첨부파일</span>
              <q-space />
              <q-btn
                flat dense size="sm" icon="attach_file" label="파일 추가"
                color="primary" @click="triggerFileInput"
                :loading="uploadingCount > 0"
              />
              <input
                ref="fileInputRef"
                type="file"
                multiple
                :accept="ATTACHMENT_ACCEPT"
                style="display: none"
                @change="onFilesSelected"
              />
            </div>
            <div class="text-caption text-grey-5 q-mb-xs">{{ ATTACHMENT_HINT }}</div>
            <!-- 드롭존 (파일 없을 때) -->
            <div
              v-if="attachments.length === 0"
              class="drop-zone"
              :class="{ 'drop-zone--active': isDragging }"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="onDrop"
            >
              <q-icon name="cloud_upload" size="24px" color="grey-5" />
              <span class="text-caption text-grey-5 q-ml-xs">파일을 끌어다 놓거나 위 버튼을 클릭하세요</span>
            </div>
            <!-- 첨부 목록 -->
            <div v-else class="attachment-list">
              <div
                v-for="(att, i) in attachments"
                :key="att.fileId"
                class="attachment-item row items-center q-gutter-xs"
              >
                <q-icon :name="fileIcon(att.contentType)" color="grey-7" size="18px" />
                <a v-if="att.contentType.startsWith('image/')"
                  :href="att.url" target="_blank" class="attachment-name text-caption">{{ att.originalName }}</a>
                <span v-else class="attachment-name text-caption text-primary cursor-pointer" @click="openPreview(att)">
                  {{ att.originalName }}
                </span>
                <span class="text-caption text-grey-5">({{ fmtSize(att.size) }})</span>
                <q-space />
                <q-btn flat dense round icon="close" size="xs" color="grey" @click="removeAttachment(i)" />
              </div>
              <!-- 드롭존 (파일 있을 때도 추가 가능) -->
              <div
                class="drop-zone drop-zone--small"
                :class="{ 'drop-zone--active': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="onDrop"
              >
                <q-icon name="add" size="16px" color="grey-5" />
                <span class="text-caption text-grey-5 q-ml-xs">파일 추가</span>
              </div>
            </div>
          </div>

        </div>

      </q-card-section>

      <q-separator />

      <!-- 하단 버튼 -->
      <q-card-actions align="right" class="q-pa-md q-gutter-x-sm">
        <q-btn flat label="취소" @click="onDialogModelUpdate(false)" />
        <q-btn color="primary" label="이슈 추가" :loading="loading" :disable="loading" @click="submit" />
      </q-card-actions>

    </q-card>
    <AttachmentPreviewDialog v-model="previewOpen" :attachment="previewAttachment" />
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import { Dialog, Notify, type QInput } from 'quasar'
import {
  createIssue, listIssues, listLabels, uploadAttachment,
  ISSUE_STATUSES, STATUS_LABEL,
  type IssueType, type IssueStatus, type IssuePriority, type Issue, type Label, type Attachment,
} from 'src/services/pm/issue'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import { listProjectMembers, type ProjectMember } from 'src/services/pm/project'
import { useAuthStore } from 'src/stores/auth'
import { getErrorMessage } from 'src/utils/http/error'
import AttachmentPreviewDialog from 'src/components/AttachmentPreviewDialog.vue'

const props = defineProps<{
  modelValue: boolean
  projectId: string
  sprintId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  'created': [Issue]
}>()

const ATTACHMENT_ACCEPT = '.jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.hwp,.hwpx,.txt,.csv,.zip,.mp4,.html,.htm,.log,.json,.xml,.yaml,.yml'
const ATTACHMENT_HINT = '지원 형식: 이미지, PDF, 워드/엑셀/파워포인트, 한글(HWP), TXT, CSV, ZIP, MP4, HTML, LOG, JSON, XML, YAML (최대 100MB)'

const auth = useAuthStore()
const loading = ref(false)
const titleInputRef = ref<QInput | null>(null)

// autofocus는 다이얼로그의 진입 트랜지션이 끝나기 전에 포커스를 걸어버려서,
// 트랜지션 중에 바로 한글을 입력하면 IME 조합이 깨져 첫 글자가 씹히거나
// 중복 입력되는 문제가 있었다. 트랜지션이 완전히 끝난 뒤(@show)에 포커스한다.
function onDialogShow() {
  void nextTick(() => titleInputRef.value?.focus())
}
const sprints = ref<Sprint[]>([])
const labelsData = ref<Label[]>([])
const members = ref<ProjectMember[]>([])
const epics = ref<Issue[]>([])
const attachments = ref<Attachment[]>([])
const uploadingCount = ref(0)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const reporterName = computed(() => auth.me?.fullName || auth.me?.email || '')

const form = ref<{
  title: string
  type: IssueType
  priority: IssuePriority
  status: IssueStatus
  sprintId: string | null
  assigneeId: string | null
  epicId: string | null
  storyPoints: number | null
  effortValue: number | null
  labelIds: string[]
  description: string
  startDate: string
  dueDate: string
  showOnDashboard: boolean
}>({
  title: '',
  type: 'TASK',
  priority: 'MEDIUM',
  status: 'BACKLOG',
  sprintId: props.sprintId ?? null,
  assigneeId: null,
  epicId: null,
  storyPoints: null,
  effortValue: null,
  labelIds: [],
  description: '',
  startDate: '',
  dueDate: '',
  showOnDashboard: false,
})

const typeOptions = [
  { label: 'Epic', value: 'EPIC' },
  { label: 'Story', value: 'STORY' },
  { label: 'Task', value: 'TASK' },
]

const priorityOptions = [
  { label: '최고', value: 'HIGHEST' },
  { label: '높음', value: 'HIGH' },
  { label: '보통', value: 'MEDIUM' },
  { label: '낮음', value: 'LOW' },
  { label: '최저', value: 'LOWEST' },
]

const statusOptions = ISSUE_STATUSES.map(s => ({ label: STATUS_LABEL[s], value: s }))
const sprintOptions = ref<{ label: string; value: string }[]>([])

const memberOptions = computed(() =>
  members.value.map(m => ({ label: m.userName || m.userEmail, value: m.userId }))
)
const epicOptions = computed(() =>
  [...epics.value]
    .sort((a, b) => (a.number ?? 0) - (b.number ?? 0))
    .map(e => ({ label: `#${e.number} ${e.title}`, value: e.id }))
)
const labelOptions = computed(() =>
  labelsData.value.map(l => ({ label: l.name, value: l.id, color: l.color }))
)
const labelColorMap = computed(() =>
  Object.fromEntries(labelsData.value.map(l => [l.id, l.color]))
)

function typeIcon(t: IssueType) {
  return { EPIC: 'bolt', STORY: 'menu_book', TASK: 'check_box_outline_blank', BUG: 'bug_report', SUB_TASK: 'radio_button_checked' }[t] ?? 'check_box_outline_blank'
}
function typeColor(t: IssueType) {
  return { EPIC: 'purple', STORY: 'green', TASK: 'primary', BUG: 'negative', SUB_TASK: 'teal' }[t] ?? 'grey'
}
function priorityColor(p: IssuePriority) {
  return { HIGHEST: 'red-9', HIGH: 'orange', MEDIUM: 'grey-6', LOW: 'blue-3', LOWEST: 'blue-2' }[p] ?? 'grey'
}

onMounted(async () => {
  try {
    const [sp, lbls, mems, eps] = await Promise.all([
      listSprints(props.projectId),
      listLabels(props.projectId),
      listProjectMembers(props.projectId),
      listIssues(props.projectId, { type: 'EPIC' }),
    ])
    sprints.value = sp
    sprintOptions.value = sp.map(s => ({ label: s.name, value: s.id }))
    labelsData.value = lbls
    members.value = mems
    epics.value = eps
  } catch {
    // ignore
  }
})

watch(() => props.modelValue, async (open) => {
  if (open) {
    form.value = {
      title: '',
      type: 'TASK',
      priority: 'MEDIUM',
      status: props.sprintId ? 'TODO' : 'BACKLOG',
      sprintId: props.sprintId ?? null,
      assigneeId: null,
      epicId: null,
      storyPoints: null,
      effortValue: null,
      labelIds: [],
      description: '',
      startDate: '',
      dueDate: '',
      showOnDashboard: false,
    }
    attachments.value = []
    formSnapshot.value = JSON.stringify(form.value)
    try {
      epics.value = await listIssues(props.projectId, { type: 'EPIC' })
    } catch {
      // keep existing
    }
  }
})

// ESC/배경 클릭/취소·닫기 버튼으로 닫으려 할 때, 입력한 내용이 있으면 확인 없이
// 그냥 닫혀 작성 중이던 내용을 잃어버리는 걸 막기 위한 변경사항 추적
const formSnapshot = ref('')
const isDirty = computed(() =>
  JSON.stringify(form.value) !== formSnapshot.value || attachments.value.length > 0
)

function onDialogModelUpdate(val: boolean) {
  if (val) {
    emit('update:modelValue', true)
    return
  }
  if (!isDirty.value) {
    emit('update:modelValue', false)
    return
  }
  Dialog.create({
    title: '저장하지 않은 변경사항이 있습니다',
    message: '저장하지 않고 닫으시겠습니까?',
    cancel: { label: '취소', flat: true },
    ok: { label: '닫기', color: 'negative' },
  }).onOk(() => emit('update:modelValue', false))
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function uploadFiles(files: File[]) {
  for (const file of files) {
    uploadingCount.value++
    try {
      const att = await uploadAttachment(file)
      attachments.value.push(att)
    } catch (e) {
      Notify.create({ type: 'negative', message: `${file.name}: ${getErrorMessage(e, '업로드 실패')}` })
    } finally {
      uploadingCount.value--
    }
  }
}

function onFilesSelected(e: Event) {
  const files = Array.from((e.target as HTMLInputElement).files ?? [])
  if (fileInputRef.value) fileInputRef.value.value = ''
  void uploadFiles(files)
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  void uploadFiles(files)
}

function removeAttachment(index: number) {
  attachments.value.splice(index, 1)
}

const previewOpen = ref(false)
const previewAttachment = ref<Attachment | null>(null)
function openPreview(att: Attachment) {
  previewAttachment.value = att
  previewOpen.value = true
}

function fileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return 'image'
  if (contentType.startsWith('video/')) return 'movie'
  if (contentType === 'application/pdf') return 'picture_as_pdf'
  if (contentType.includes('spreadsheet') || contentType.includes('excel')) return 'table_chart'
  if (contentType.includes('word')) return 'description'
  if (contentType.includes('powerpoint') || contentType.includes('presentation')) return 'slideshow'
  if (contentType === 'text/html' || contentType === 'application/json' || contentType.includes('xml')) return 'code'
  if (contentType === 'text/plain' || contentType === 'text/csv') return 'article'
  return 'attach_file'
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

async function submit() {
  if (!form.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목은 필수입니다.' })
    return
  }
  if (form.value.type === 'TASK' && (!form.value.startDate || !form.value.dueDate || !form.value.assigneeId || !form.value.epicId)) {
    Notify.create({ type: 'warning', message: 'Task 타입은 담당자, 상위 Epic, 시작일, 마감일이 필수입니다.' })
    return
  }
  loading.value = true
  try {
    const created = await createIssue(props.projectId, {
      title: form.value.title.trim(),
      type: form.value.type,
      priority: form.value.priority,
      status: form.value.status,
      ...(form.value.sprintId ? { sprint_id: form.value.sprintId } : {}),
      ...(form.value.assigneeId ? { assignee_id: form.value.assigneeId } : {}),
      ...(form.value.epicId ? { epic_id: form.value.epicId } : {}),
      ...(form.value.storyPoints != null ? { story_points: form.value.storyPoints } : {}),
      ...(form.value.effortValue != null ? { effort_md: `${form.value.effortValue} 일` } : {}),
      ...(form.value.labelIds.length ? { label_ids: form.value.labelIds } : {}),
      ...(form.value.description ? { description: form.value.description } : {}),
      ...(form.value.startDate ? { start_date: new Date(form.value.startDate).toISOString() } : {}),
      ...(form.value.dueDate ? { due_date: new Date(form.value.dueDate).toISOString() } : {}),
      show_on_dashboard: form.value.showOnDashboard,
      attachments: attachments.value.map(a => ({
        file_id: a.fileId,
        original_name: a.originalName,
        url: a.url,
        size: a.size,
        content_type: a.contentType,
      })),
    })
    emit('created', created)
    emit('update:modelValue', false)
    Notify.create({ type: 'positive', message: '이슈가 추가되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '추가 실패') })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9e9e9e;
}
.drop-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px dashed #ccc;
  border-radius: 6px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.drop-zone--small {
  padding: 8px;
  margin-top: 6px;
}
.drop-zone--active {
  border-color: #1976d2;
  background: #e3f2fd;
}
.attachment-list {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
.attachment-item {
  padding: 6px 10px;
  border-bottom: 1px solid #f0f0f0;
}
.attachment-item:last-of-type {
  border-bottom: none;
}
.attachment-name {
  color: #1976d2;
  text-decoration: none;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attachment-name:hover {
  text-decoration: underline;
}
</style>
