<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-sm q-gutter-sm">
      <div class="text-h6">{{ project?.name }} — 보드</div>
      <q-badge v-if="project" color="primary" :label="project.key" />
      <q-space />
      <q-select
        v-model="selectedSprintId"
        :options="sprintOptions"
        label="스프린트"
        emit-value map-options
        dense outlined clearable
        style="min-width: 180px"
        @update:model-value="loadBoard"
      />
      <q-btn-toggle
        v-model="titleClamp"
        dense unelevated
        toggle-color="primary"
        color="white"
        text-color="grey-7"
        :options="[
          { value: false, slot: 'full' },
          { value: true,  slot: 'clamp' },
        ]"
      >
        <template #full>
          <q-icon name="notes" size="16px" />
          <q-tooltip>제목 전체 보기</q-tooltip>
        </template>
        <template #clamp>
          <q-icon name="short_text" size="16px" />
          <q-tooltip>제목 2줄 요약</q-tooltip>
        </template>
      </q-btn-toggle>
      <q-btn color="primary" icon="add" label="이슈 추가" @click="openCreateIssue" />
    </div>

    <!-- 컬럼 on/off 필터 + 날짜 필터 -->
    <div class="row items-center q-gutter-xs q-mb-sm">
      <q-chip
        v-for="status in ISSUE_STATUSES"
        :key="status"
        clickable dense size="sm"
        :color="visibleStatuses.has(status) ? STATUS_COLOR[status] : undefined"
        :text-color="visibleStatuses.has(status) ? 'white' : 'grey-7'"
        :outline="!visibleStatuses.has(status)"
        @click="toggleStatus(status)"
      >{{ STATUS_LABEL[status] }}</q-chip>

      <q-separator vertical inset class="q-mx-xs" style="height: 20px" />

      <!-- 우선순위 -->
      <q-chip
        :color="filterPriority ? 'orange-7' : undefined"
        :text-color="filterPriority ? 'white' : 'grey-8'"
        :outline="!filterPriority"
        clickable dense size="sm"
        :removable="!!filterPriority"
        @remove="filterPriority = null"
      >
        <q-icon v-if="filterPriority" :name="PRIORITY_ICON[filterPriority]" size="10px" class="q-mr-xs" />
        <span>{{ filterPriority ? PRIORITY_LABEL[filterPriority] : '우선순위' }}</span>
        <q-icon v-if="!filterPriority" name="expand_more" size="14px" class="q-ml-xs" />
        <q-menu>
          <q-list dense style="min-width: 150px">
            <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">우선순위 선택</q-item-label>
            <q-item v-for="opt in priorityOptions" :key="opt.value" clickable v-close-popup @click="filterPriority = opt.value">
              <q-item-section side style="padding-right: 8px; min-width: 24px">
                <q-icon :name="PRIORITY_ICON[opt.value]" :color="PRIORITY_COLOR[opt.value]" size="xs" />
              </q-item-section>
              <q-item-section>{{ opt.label }}</q-item-section>
              <q-item-section side v-if="filterPriority === opt.value">
                <q-icon name="check" color="orange-7" size="xs" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-chip>

      <!-- 유형 -->
      <q-chip
        :color="filterType ? TYPE_COLOR[filterType] : undefined"
        :text-color="filterType ? 'white' : 'grey-8'"
        :outline="!filterType"
        clickable dense size="sm"
        :removable="!!filterType"
        @remove="filterType = null"
      >
        <q-icon v-if="filterType" :name="TYPE_ICON[filterType]" size="10px" class="q-mr-xs" />
        <span>{{ filterType ? TYPE_LABEL[filterType] : '유형' }}</span>
        <q-icon v-if="!filterType" name="expand_more" size="14px" class="q-ml-xs" />
        <q-menu>
          <q-list dense style="min-width: 150px">
            <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">유형 선택</q-item-label>
            <q-item v-for="opt in typeOptions" :key="opt.value" clickable v-close-popup @click="filterType = opt.value">
              <q-item-section side style="padding-right: 8px; min-width: 24px">
                <q-icon :name="TYPE_ICON[opt.value]" :color="TYPE_COLOR[opt.value]" size="xs" />
              </q-item-section>
              <q-item-section>{{ opt.label }}</q-item-section>
              <q-item-section side v-if="filterType === opt.value">
                <q-icon name="check" :color="TYPE_COLOR[opt.value]" size="xs" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-chip>

      <!-- 담당자 -->
      <q-chip
        :color="filterAssigneeId ? 'teal' : undefined"
        :text-color="filterAssigneeId ? 'white' : 'grey-8'"
        :outline="!filterAssigneeId"
        clickable dense size="sm"
        :removable="!!filterAssigneeId"
        @remove="filterAssigneeId = null"
      >
        <q-icon v-if="filterAssigneeId" name="person" size="10px" class="q-mr-xs" />
        <span>{{ filterAssigneeId ? (memberOptions.find(m => m.value === filterAssigneeId)?.label ?? '담당자') : '담당자' }}</span>
        <q-icon v-if="!filterAssigneeId" name="expand_more" size="14px" class="q-ml-xs" />
        <q-menu>
          <q-list dense style="min-width: 170px">
            <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">담당자 선택</q-item-label>
            <q-item v-if="memberOptions.length === 0" class="text-grey-5 text-caption q-px-md q-py-xs">멤버가 없습니다</q-item>
            <q-item v-for="opt in memberOptions" :key="opt.value" clickable v-close-popup @click="filterAssigneeId = opt.value">
              <q-item-section side style="padding-right: 8px; min-width: 28px">
                <q-avatar size="22px" color="teal" text-color="white" font-size="11px">
                  {{ opt.label.charAt(0).toUpperCase() }}
                </q-avatar>
              </q-item-section>
              <q-item-section>{{ opt.label }}</q-item-section>
              <q-item-section side v-if="filterAssigneeId === opt.value">
                <q-icon name="check" color="teal" size="xs" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-menu>
      </q-chip>

      <q-chip
        :color="filterDateFrom || filterDateTo ? 'deep-orange-7' : undefined"
        :text-color="filterDateFrom || filterDateTo ? 'white' : 'grey-8'"
        :outline="!(filterDateFrom || filterDateTo)"
        clickable dense size="sm"
        :removable="!!(filterDateFrom || filterDateTo)"
        @remove="filterDateFrom = null; filterDateTo = null"
      >
        <q-icon name="event" size="10px" class="q-mr-xs" />
        <span>{{ filterDateFrom || filterDateTo
          ? `${filterDateFrom ?? '~'} ~ ${filterDateTo ?? '~'}`
          : '마감일' }}</span>
        <q-icon v-if="!(filterDateFrom || filterDateTo)" name="expand_more" size="14px" class="q-ml-xs" />
        <q-menu :offset="[0, 4]">
          <div class="q-pa-md" style="min-width: 240px">
            <div class="text-caption text-grey-6 q-mb-sm">마감일 기간</div>
            <q-input v-model="filterDateFrom" type="date" dense outlined clearable label="시작일" class="q-mb-sm" />
            <q-input v-model="filterDateTo"   type="date" dense outlined clearable label="종료일" />
          </div>
        </q-menu>
      </q-chip>
    </div>

    <q-inner-loading :showing="loading" />

    <!-- 칸반 컬럼 -->
    <div class="row q-col-gutter-sm no-wrap board-container">
      <div v-for="status in ISSUE_STATUSES" v-show="visibleStatuses.has(status)" :key="status" class="col board-column">
        <q-card flat bordered class="board-column-card">
          <q-card-section class="q-py-sm column-header">
            <div class="row items-center q-gutter-xs">
              <q-badge :color="STATUS_COLOR[status]" :label="STATUS_LABEL[status]" />
              <q-badge outline :label="(filteredBoard[status] ?? []).length" />
            </div>
          </q-card-section>
          <q-separator />

          <draggable
            :list="filteredBoard[status]"
            group="issues"
            item-key="id"
            class="board-draggable"
            @change="evt => onDragChange(evt, status)"
          >
            <template #item="{ element: el }">
              <q-card
                flat bordered
                class="issue-card cursor-pointer"
                :data-id="(el as Issue).id"
                @click="openIssueDetail(el as Issue)"
              >
                <q-card-section class="issue-card-section">
                  <div class="row items-center no-wrap issue-meta">
                    <q-icon :name="TYPE_ICON[(el as Issue).type]" :color="TYPE_COLOR[(el as Issue).type]" size="xs" class="q-mr-xs" />
                    <q-icon :name="PRIORITY_ICON[(el as Issue).priority]" :color="PRIORITY_COLOR[(el as Issue).priority]" size="xs" class="q-mr-xs" />
                    <span class="text-caption text-grey-6">{{ project?.key }}-{{ (el as Issue).number }}</span>
                    <q-space />
                    <span v-if="(el as Issue).assigneeName" class="text-caption text-grey-7 assignee-inline">{{ (el as Issue).assigneeName }}</span>
                  </div>
                  <div class="issue-title text-body2" :class="titleClamp ? 'clamp-2' : 'clamp-none'">{{ (el as Issue).title }}</div>

                  <!-- 하위작업 -->
                  <template v-if="(el as Issue).subtasks?.length">
                    <q-separator class="q-mt-xs q-mb-xs" />
                    <div class="row items-center q-mb-xs">
                      <q-icon name="fa-solid fa-circle-dot" color="teal" size="10px" class="q-mr-xs" />
                      <span class="text-caption text-grey-6">하위작업 {{ (el as Issue).subtasks.length }}개</span>
                    </div>
                    <div
                      v-for="sub in (el as Issue).subtasks"
                      :key="(sub as SubtaskSummary).id"
                      class="subtask-row row items-center q-gutter-xs no-wrap"
                      @click.stop="openSubtaskDetail((sub as SubtaskSummary).id)"
                    >
                      <q-icon
                        name="circle"
                        :color="STATUS_COLOR[(sub as SubtaskSummary).status]"
                        size="8px"
                        style="flex-shrink:0"
                      />
                      <span class="text-caption subtask-title">{{ (sub as SubtaskSummary).title }}</span>
                      <q-avatar
                        v-if="(sub as SubtaskSummary).assigneeName"
                        size="14px" color="teal" text-color="white"
                        class="text-caption" style="flex-shrink:0;font-size:8px"
                      >
                        {{ (sub as SubtaskSummary).assigneeName![0] }}
                      </q-avatar>
                    </div>
                  </template>
                </q-card-section>
              </q-card>
            </template>
          </draggable>
        </q-card>
      </div>
    </div>

    <!-- 이슈 생성 다이얼로그 -->
    <IssueFormDialog
      v-model="createDialog.open"
      :project-id="projectId"
      v-bind="selectedSprintId ? { sprintId: selectedSprintId } : {}"
      @created="onIssueCreated"
    />

    <!-- 이슈 상세 다이얼로그 -->
    <IssueDetailDialog
      v-model="detailDialog.open"
      :project-id="projectId"
      :project-key="project?.key ?? ''"
      :issue="detailDialog.issue"
      :initial-comment-id="detailDialog.commentId"
      @updated="onIssueUpdated"
      @deleted="onIssueDeleted"
      @update:model-value="!$event && loadBoard()"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify, Dialog } from 'quasar'
import draggable from 'vuedraggable'
import {
  getBoard, updateIssue, getIssue,
  ISSUE_STATUSES, STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR, PRIORITY_ICON, PRIORITY_COLOR, PRIORITY_LABEL,
  type Issue, type IssueStatus, type IssuePriority, type IssueType, type SubtaskSummary,
} from 'src/services/pm/issue'
import { getProject, listProjectMembers, type Project, type ProjectMember } from 'src/services/pm/project'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import IssueFormDialog from './components/IssueFormDialog.vue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const projectId = route.params.projectId as string

const visibleStatuses = ref(new Set<IssueStatus>(ISSUE_STATUSES))
const titleClamp = ref(true)
const filterDateFrom = ref<string | null>(null)
const filterDateTo   = ref<string | null>(null)
const filterPriority  = ref<IssuePriority | null>(null)
const filterType      = ref<IssueType | null>(null)
const filterAssigneeId = ref<string | null>(null)
const members = ref<ProjectMember[]>([])

const TYPE_LABEL: Record<IssueType, string> = {
  EPIC: 'Epic', STORY: 'Story', TASK: 'Task', BUG: 'Bug', SUB_TASK: 'Sub-task',
}
const priorityOptions = [
  { label: '최고', value: 'HIGHEST' as IssuePriority }, { label: '높음', value: 'HIGH' as IssuePriority },
  { label: '보통', value: 'MEDIUM' as IssuePriority  }, { label: '낮음', value: 'LOW' as IssuePriority  },
  { label: '최저', value: 'LOWEST' as IssuePriority  },
]
const typeOptions = [
  { label: 'Epic',     value: 'EPIC'     as IssueType }, { label: 'Story', value: 'STORY'    as IssueType },
  { label: 'Task',     value: 'TASK'     as IssueType }, { label: 'Bug',   value: 'BUG'      as IssueType },
  { label: 'Sub-task', value: 'SUB_TASK' as IssueType },
]
const memberOptions = computed(() =>
  members.value.map(m => ({ label: m.userName || m.userEmail, value: m.userId }))
)

function toggleStatus(status: IssueStatus) {
  const next = new Set(visibleStatuses.value)
  if (next.has(status) && next.size > 1) next.delete(status)
  else next.add(status)
  visibleStatuses.value = next
}

const project = ref<Project | null>(null)
const sprints = ref<Sprint[]>([])
const selectedSprintId = ref<string | null>(null)
const board = ref<Record<IssueStatus, Issue[]>>({
  BACKLOG: [], TODO: [], IN_PROGRESS: [], IMPLEMENTED: [], DONE: [],
})
const loading = ref(false)

const createDialog = ref({ open: false })
const detailDialog = ref({ open: false, issue: null as Issue | null, commentId: null as string | null })

const sprintOptions = computed(() => [
  { label: '전체', value: null },
  ...sprints.value.map(s => ({ label: `${s.name} (${s.status})`, value: s.id })),
])

const hasBoardFilter = computed(() =>
  !!(filterDateFrom.value || filterDateTo.value || filterPriority.value || filterType.value || filterAssigneeId.value)
)

const filteredBoard = computed(() => {
  if (!hasBoardFilter.value) return board.value
  const result = {} as Record<IssueStatus, Issue[]>
  for (const status of ISSUE_STATUSES) {
    result[status] = (board.value[status] ?? []).filter(issue => {
      if (filterDateFrom.value && (!issue.dueDate || issue.dueDate < filterDateFrom.value)) return false
      if (filterDateTo.value   && (!issue.dueDate || issue.dueDate > filterDateTo.value))   return false
      if (filterPriority.value   && issue.priority   !== filterPriority.value)   return false
      if (filterType.value       && issue.type       !== filterType.value)       return false
      if (filterAssigneeId.value && issue.assigneeId !== filterAssigneeId.value) return false
      return true
    })
  }
  return result
})

onMounted(async () => {
  loading.value = true
  try {
    const [proj, sp, mem] = await Promise.all([getProject(projectId), listSprints(projectId), listProjectMembers(projectId)])
    project.value = proj
    sprints.value = sp
    members.value = mem
    const active = sp.find(s => s.status === 'ACTIVE')
    if (active) selectedSprintId.value = active.id
    await loadBoard()

    const issueId = route.query.issueId as string | undefined
    if (issueId) {
      const commentId = (route.query.commentId as string | undefined) ?? null
      const found = Object.values(board.value).flat().find(i => i.id === issueId)
      if (found) {
        openIssueDetail(found, commentId)
      } else {
        // 현재 필터(스프린트 등)에 해당 이슈가 없을 수 있으므로 직접 조회해서 연다.
        try {
          const issue = await getIssue(projectId, issueId)
          openIssueDetail(issue, commentId)
        } catch { /* 이슈를 찾을 수 없으면 조용히 무시 */ }
      }
    }
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

async function loadBoard() {
  try {
    const data = await getBoard(projectId, selectedSprintId.value ?? undefined)
    const empty: Record<IssueStatus, Issue[]> = { BACKLOG: [], TODO: [], IN_PROGRESS: [], IMPLEMENTED: [], DONE: [] }
    board.value = { ...empty, ...data }
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '보드 로드 실패') })
  }
}

function onDragChange(
  evt: { added?: { element: Issue; newIndex: number }; removed?: { element: Issue; oldIndex: number } },
  targetStatus: IssueStatus,
) {
  if (!evt.added) return
  const issue = evt.added.element
  const fromStatus = issue.status

  Dialog.create({
    title: '상태 변경',
    message: `<b>${issue.title}</b><br><br>
      <span style="color:#888">${STATUS_LABEL[fromStatus]}</span>
      &nbsp;→&nbsp;
      <span style="font-weight:600">${STATUS_LABEL[targetStatus]}</span>
      <br><br>상태를 변경하시겠습니까?`,
    html: true,
    ok: { label: '변경', color: 'primary', unelevated: true },
    cancel: { label: '취소', flat: true },
    persistent: true,
  }).onOk(() => {
    updateIssue(projectId, issue.id, { status: targetStatus })
      .then(() => loadBoard())
      .catch(async (e) => {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '상태 변경 실패') })
        await loadBoard()
      })
  }).onCancel(() => {
    void loadBoard()
  })
}

function openCreateIssue() {
  createDialog.value.open = true
}

function openIssueDetail(issue: Issue, commentId: string | null = null) {
  detailDialog.value = { open: true, issue, commentId }
}

async function openSubtaskDetail(subtaskId: string) {
  try {
    const full = await getIssue(projectId, subtaskId)
    detailDialog.value = { open: true, issue: full, commentId: null }
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '하위작업 로드 실패') })
  }
}

function onIssueCreated(issue: Issue) {
  board.value[issue.status].push(issue)
}

function onIssueUpdated() {
  void loadBoard()
}

function onIssueDeleted(issueId: string) {
  for (const status of ISSUE_STATUSES) {
    board.value[status] = board.value[status].filter(i => i.id !== issueId)
  }
}
</script>

<style scoped>
/* ── 보드 컨테이너 ── */
.board-container {
  overflow-x: auto;
  height: calc(100vh - 130px);
  align-items: stretch;
}

/* ── 컬럼 ── */
.board-column {
  min-width: 240px;
  max-width: 320px;
  height: 100%;
}

.board-column-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.column-header {
  flex-shrink: 0;
}

/* ── 드래그 영역: 남은 공간을 채우고, 카드들이 균등 분배 ── */
.board-draggable {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  min-height: 60px;
  overflow-y: auto; /* 카드가 최소 높이 이하로 줄 수 없을 때 스크롤 fallback */
}

/* ── 이슈 카드: 콘텐츠 높이 기준으로 flex 분배, 하위작업 있어도 짤리지 않음 ── */
.issue-card {
  flex: 1 1 auto;
  min-height: 52px;
  overflow: hidden; /* flex로 강제 축소될 때만 클립 */
  cursor: pointer;
}
.issue-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.issue-card-section {
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
}

.issue-meta {
  flex-shrink: 0;
  margin-bottom: 2px;
}

.issue-title {
  line-height: 1.3;
  font-size: 13px;
  word-break: break-word;
}
.clamp-2 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.clamp-none {
  white-space: normal;
}

.assignee-inline {
  max-width: 80px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

/* ── 하위작업 ── */
.subtask-row {
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
}
.subtask-row:hover {
  background: rgba(0, 0, 0, 0.04);
}
.subtask-title {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #555;
}
</style>
