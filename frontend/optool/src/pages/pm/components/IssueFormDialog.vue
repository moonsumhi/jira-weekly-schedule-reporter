<template>
  <q-dialog :model-value="modelValue" :persistent="loading" @update:model-value="onDialogModelUpdate" @show="onDialogShow">
    <q-card class="issue-create-dialog" style="width: 1080px; max-width: 96vw">

      <!-- 헤더 -->
      <q-card-section class="row items-center q-pb-none q-pt-md q-px-lg">
        <div>
          <div class="text-h6 text-weight-bold">{{ createdIssue ? '점검 작업 연결' : '이슈 추가' }}</div>
          <div class="text-caption text-grey-6">{{ createdIssue ? '생성된 이슈에 점검 정보를 연결합니다' : '새 이슈를 생성합니다' }}</div>
        </div>
        <q-space />
        <q-btn flat round dense icon="close" :disable="loading" @click="onDialogModelUpdate(false)" />
      </q-card-section>

      <q-separator class="q-mt-md" />
      <q-banner v-if="creationError" rounded class="creation-error q-mx-lg q-mt-md" role="alert">
        <template #avatar><q-icon name="error_outline" color="negative" /></template>
        <div v-if="createdIssue" class="text-weight-medium">
          {{ createdIssue.projectKey }}-{{ createdIssue.number }} 이슈는 생성되었습니다.
          점검 연결을 확인하지 못했으니 다시 시도해 주세요.
        </div>
        <div>{{ creationError }}</div>
      </q-banner>

      <!-- 폼 본문 -->
      <q-card-section class="issue-create-body q-px-lg q-pt-sm q-pb-none">

        <fieldset class="issue-fields" :disabled="loading || !!createdIssue" :inert="loading || !!createdIssue">
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
        </fieldset>

        <ServerAssetLinks :key="`${projectId}:${modelValue}`" v-model="workAssets" class="issue-work-assets" editing :disable="loading"
          label="작업 대상 서버 (선택)" :search-assets="searchAssets"
          hint="등록된 서버를 선택하면 해당 자산의 운영 이력에도 이슈가 표시됩니다." />

        <section v-if="canInspect" class="issue-inspection" :class="{ 'issue-inspection--enabled': inspectionEnabled }" aria-label="서버 점검 연결">
          <q-checkbox
            v-model="inspectionEnabled"
            label="서버 점검에 추가"
            color="primary"
            :disable="loading"
            aria-controls="issue-inspection-options"
            :aria-expanded="inspectionEnabled"
          />
          <p class="inspection-hint">이 이슈를 선택한 월의 서버 점검 작업에 추가합니다.</p>
          <div v-if="inspectionEnabled" id="issue-inspection-options" class="issue-inspection-options">
            <div class="inspection-month-info">
              <InspectionMonthPicker v-model="inspectionMonth" :disable="loading" />
              <div class="inspection-schedule">
                <q-icon name="event_available" size="18px" />
                <span v-if="inspectionDateLoading">점검일 확인 중…</span>
                <span v-else-if="inspectionDate">점검 예정일 {{ inspectionDate }}</span>
                <span v-else>선택한 월의 작업 목록에 등록됩니다.</span>
              </div>
              <p>{{ workAssets.length ? `선택한 서버 ${workAssets.length}대를 점검 작업의 대상 서버로 지정합니다.` : '대상 서버가 없는 작업은 공통 작업으로 등록해 주세요.' }}</p>
            </div>
            <div v-if="workAssets.length" class="inspection-selected-servers"><q-icon name="dns" size="18px" /><span>{{ workAssets.map(asset => asset.name).join(', ') }}</span></div>
            <q-checkbox v-else v-model="inspectionCommon" label="특정 서버 없이 공통 작업으로 등록" :disable="loading" />
          </div>
        </section>

        <fieldset class="issue-fields" :disabled="loading || !!createdIssue" :inert="loading || !!createdIssue">
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
        </fieldset>

      </q-card-section>

      <q-separator />

      <!-- 하단 버튼 -->
      <q-card-actions align="right" class="q-pa-md q-gutter-x-sm">
        <q-btn flat :label="createdIssue ? '연결 없이 닫기' : '취소'" :disable="loading" @click="onDialogModelUpdate(false)" />
        <q-btn color="primary" :label="submitLabel" :loading="loading" :disable="loading || uploadingCount > 0" @click="submit" />
      </q-card-actions>

    </q-card>
    <AttachmentPreviewDialog v-model="previewOpen" :attachment="previewAttachment" />
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import { Dialog, Notify, type QInput } from 'quasar'
import {
  createIssue, updateIssue, searchIssueAssets, listIssues, listLabels, uploadAttachment,
  ISSUE_STATUSES, STATUS_LABEL,
  type IssueType, type IssueStatus, type IssuePriority, type Issue, type Label, type Attachment,
} from 'src/services/pm/issue'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import { listProjectMembers, type ProjectMember } from 'src/services/pm/project'
import { useAuthStore } from 'src/stores/auth'
import { getErrorMessage } from 'src/utils/http/error'
import AttachmentPreviewDialog from 'src/components/AttachmentPreviewDialog.vue'
import InspectionMonthPicker from 'src/components/inspection/InspectionMonthPicker.vue'
import ServerAssetLinks from 'src/components/ServerAssetLinks.vue'
import type { ServerAssetLink } from 'src/services/assetLinks'
import {
  getInspectionDate, getInspectionTasks, registerInspection, searchInspectionAssets, thisMonth,
} from 'src/services/inspection'

const props = defineProps<{
  modelValue: boolean
  projectId: string
  sprintId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  'created': [Issue]
  'updated': [Issue]
}>()

const ATTACHMENT_ACCEPT = '.jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.hwp,.hwpx,.txt,.csv,.zip,.mp4,.html,.htm,.log,.json,.xml,.yaml,.yml'
const ATTACHMENT_HINT = '지원 형식: 이미지, PDF, 워드/엑셀/파워포인트, 한글(HWP), TXT, CSV, ZIP, MP4, HTML, LOG, JSON, XML, YAML (최대 100MB)'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const createdIssue = ref<Issue | null>(null)
const creationError = ref('')
const canInspect = computed(() => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('server_check')))
const inspectionEnabled = ref(false)
const inspectionMonth = ref(thisMonth())
const inspectionCommon = ref(false)
const workAssets = ref<ServerAssetLink[]>([])
const searchAssets = (search: string) => searchIssueAssets(props.projectId, search)
watch(() => workAssets.value.length, length => { if (length) inspectionCommon.value = false })
const workAssetsChanged = computed(() => !!createdIssue.value && JSON.stringify((createdIssue.value.linkedAssets || []).map(asset => asset.id).sort()) !== JSON.stringify(workAssets.value.map(asset => asset.id).sort()))
const inspectionDate = ref('')
const inspectionDateLoading = ref(false)
const submitLabel = computed(() => {
  if (createdIssue.value) return inspectionEnabled.value ? '점검 연결 재시도' : workAssetsChanged.value ? '서버 연결 저장' : '닫기'
  return inspectionEnabled.value ? '이슈 및 점검 작업 추가' : '이슈 추가'
})
let inspectionDateRequest = 0
watch([inspectionEnabled, inspectionMonth, () => props.modelValue], async () => {
  const token = ++inspectionDateRequest
  inspectionDate.value = ''
  inspectionDateLoading.value = false
  if (!props.modelValue || !inspectionEnabled.value || !canInspect.value) return
  inspectionDateLoading.value = true
  try {
    const date = await getInspectionDate(inspectionMonth.value)
    if (token === inspectionDateRequest) inspectionDate.value = date
  } catch {
    // 점검일은 참고 정보이며, 월과 대상 서버로 등록할 수 있다.
  } finally {
    if (token === inspectionDateRequest) inspectionDateLoading.value = false
  }
})
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
    createdIssue.value = null
    creationError.value = ''
    inspectionEnabled.value = false
    inspectionMonth.value = thisMonth()
    inspectionCommon.value = false
    workAssets.value = []
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
  JSON.stringify(form.value) !== formSnapshot.value || attachments.value.length > 0 || inspectionEnabled.value || workAssets.value.length > 0
)

function onDialogModelUpdate(val: boolean) {
  if (loading.value) return
  if (val) {
    emit('update:modelValue', true)
    return
  }
  if ((createdIssue.value && !workAssetsChanged.value) || (!createdIssue.value && !isDirty.value)) {
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
  if (loading.value || uploadingCount.value > 0) return
  if (createdIssue.value && !inspectionEnabled.value && !workAssetsChanged.value) {
    emit('update:modelValue', false)
    return
  }
  if (!createdIssue.value && !form.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목은 필수입니다.' })
    return
  }
  if (!createdIssue.value && form.value.type === 'TASK' && (!form.value.startDate || !form.value.dueDate || !form.value.assigneeId || !form.value.epicId)) {
    Notify.create({ type: 'warning', message: 'Task 타입은 담당자, 상위 Epic, 시작일, 마감일이 필수입니다.' })
    return
  }
  const addInspection = canInspect.value && inspectionEnabled.value
  if (addInspection && (!/^20\d{2}-(0[1-9]|1[0-2])$/.test(inspectionMonth.value) || (!inspectionCommon.value && !workAssets.value.length))) {
    Notify.create({ type: 'warning', message: '점검 월과 대상 서버를 선택하거나 공통 작업으로 지정해 주세요.' })
    return
  }
  loading.value = true
  creationError.value = ''
  try {
    const assetIds = workAssets.value.map(a => a.id)
    if (addInspection && assetIds.length) {
      const available = new Set((await searchInspectionAssets('', assetIds)).map(a => a.id))
      if (assetIds.some(id => !available.has(id))) throw new Error('선택한 서버 중 삭제된 자산이 있습니다. 대상 서버를 다시 선택해 주세요.')
    }
    if (!createdIssue.value) {
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
        asset_ids: assetIds,
        attachments: attachments.value.map(a => ({
          file_id: a.fileId,
          original_name: a.originalName,
          url: a.url,
          size: a.size,
          content_type: a.contentType,
        })),
      })
      createdIssue.value = created
      emit('created', created)
    } else if (workAssetsChanged.value) {
      createdIssue.value = await updateIssue(props.projectId, createdIssue.value.id, { asset_ids: assetIds })
      emit('updated', createdIssue.value)
    }
    if (addInspection) {
      const payload = {
        month: inspectionMonth.value,
        issue_id: createdIssue.value.id,
        asset_ids: assetIds,
        common: inspectionCommon.value,
      }
      try {
        await registerInspection(payload)
      } catch (error) {
        // 응답만 유실된 경우에는 같은 이슈·월·대상이 이미 저장되었는지 확인한다.
        const existing = await getInspectionTasks(payload.month, {
          include_overdue: false,
          issue_id: payload.issue_id,
        }).catch(() => null)
        const linked = existing?.items.some(t => t.issueId === payload.issue_id && t.month === payload.month
          && t.state === 'ACTIVE' && t.common === payload.common
          && t.assets.length === assetIds.length && t.assets.every(a => assetIds.includes(a.id)))
        if (!linked) throw error
      }
    }
    emit('update:modelValue', false)
    const savedMonth = inspectionMonth.value
    const savedIssueId = createdIssue.value.id
    Notify.create({
      type: 'positive',
      message: addInspection ? `${Number(savedMonth.slice(5))}월 서버 점검에 이슈를 추가했습니다.` : '이슈가 추가되었습니다.',
      ...(addInspection ? {
        timeout: 8000,
        actions: [{ label: '월간 작업 보기', color: 'white', handler: () => {
          void router.push({ path: '/inspection/tasks', query: { month: savedMonth, issue_id: savedIssueId } })
        } }],
      } : {}),
    })
  } catch (e) {
    creationError.value = getErrorMessage(e, '저장하지 못했습니다. 다시 시도해 주세요.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.issue-create-dialog { display: flex; flex-direction: column; }
.issue-create-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
.issue-create-dialog > .q-card-actions { flex-shrink: 0; }
.issue-fields { border: 0; padding: 0; margin: 0; min-width: 0; }
.issue-fields:disabled { opacity: 0.65; }
.creation-error { background: #fff2ef; color: #9c4336; font-size: 12px; flex-shrink: 0; }
.issue-inspection { margin-top: 18px; padding: 10px 14px; border: 1px solid #e1e7ef; border-radius: 9px; background: #f8fafc; }
.issue-inspection--enabled { border-color: #a8c6e5; }
.issue-inspection > .q-checkbox { font-size: 13px; font-weight: 600; color: #365778; }
.inspection-hint { margin: 0 0 4px 40px; font-size: 12px; color: #718399; }
.issue-inspection-options { display: grid; grid-template-columns: 230px minmax(0, 1fr); gap: 24px; border-top: 1px solid #e1e7ef; padding: 18px 8px 6px; margin-top: 12px; }
.inspection-schedule { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #526a84; margin-top: 15px; }
.inspection-month-info p { margin: 10px 0 0; font-size: 12px; color: #718399; line-height: 1.7; }
.inspection-selected-servers { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.8; color: #526a84; overflow-wrap: anywhere; }
.issue-work-assets { max-width: none; }
@media (max-width: 700px) {
  .issue-inspection-options { grid-template-columns: minmax(0, 1fr); gap: 18px; }
  .inspection-hint { margin-left: 0; }
}
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
