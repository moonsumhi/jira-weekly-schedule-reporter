<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md q-gutter-sm">
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
      <q-btn color="primary" icon="add" label="이슈 추가" @click="openCreateIssue" />
    </div>

    <q-inner-loading :showing="loading" />

    <!-- 칸반 컬럼 -->
    <div class="row q-col-gutter-sm no-wrap board-container">
      <div v-for="status in ISSUE_STATUSES" :key="status" class="col board-column">
        <q-card flat bordered class="full-height">
          <q-card-section class="q-py-sm">
            <div class="row items-center q-gutter-xs">
              <q-badge :color="STATUS_COLOR[status]" :label="STATUS_LABEL[status]" />
              <q-badge outline :label="(board[status] ?? []).length" />
            </div>
          </q-card-section>
          <q-separator />

          <draggable
            :list="board[status]"
            group="issues"
            item-key="id"
            class="q-pa-xs column q-gutter-xs"
            style="min-height: 60px"
            @change="evt => onDragChange(evt, status)"
          >
            <template #item="{ element: el }">
              <q-card
                flat bordered
                class="issue-card cursor-pointer"
                :data-id="(el as Issue).id"
                @click="openIssueDetail(el as Issue)"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="TYPE_ICON[(el as Issue).type]" :color="TYPE_COLOR[(el as Issue).type]" size="xs" />
                    <q-icon :name="PRIORITY_ICON[(el as Issue).priority]" :color="PRIORITY_COLOR[(el as Issue).priority]" size="xs" />
                    <span class="text-caption text-grey-6">{{ project?.key }}-{{ (el as Issue).number }}</span>
                  </div>
                  <div class="text-body2">{{ (el as Issue).title }}</div>
                  <div v-if="(el as Issue).assigneeName" class="row items-center q-mt-xs">
                    <q-avatar size="20px" color="primary" text-color="white" class="text-caption">
                      {{ (el as Issue).assigneeName![0] }}
                    </q-avatar>
                    <span class="text-caption text-grey-6 q-ml-xs">{{ (el as Issue).assigneeName }}</span>
                  </div>
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
      @updated="onIssueUpdated"
      @deleted="onIssueDeleted"
      @update:model-value="!$event && loadBoard()"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify } from 'quasar'
import draggable from 'vuedraggable'
import {
  getBoard, updateIssue,
  ISSUE_STATUSES, STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR, PRIORITY_ICON, PRIORITY_COLOR,
  type Issue, type IssueStatus,
} from 'src/services/pm/issue'
import { getProject, type Project } from 'src/services/pm/project'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import IssueFormDialog from './components/IssueFormDialog.vue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const projectId = route.params.projectId as string

const project = ref<Project | null>(null)
const sprints = ref<Sprint[]>([])
const selectedSprintId = ref<string | null>(null)
const board = ref<Record<IssueStatus, Issue[]>>({
  BACKLOG: [], TODO: [], IN_PROGRESS: [], IN_REVIEW: [], DONE: [],
})
const loading = ref(false)

const createDialog = ref({ open: false })
const detailDialog = ref({ open: false, issue: null as Issue | null })

const sprintOptions = computed(() => [
  { label: '전체 (백로그 제외)', value: null },
  ...sprints.value.map(s => ({ label: `${s.name} (${s.status})`, value: s.id })),
])

onMounted(async () => {
  loading.value = true
  try {
    const [proj, sp] = await Promise.all([getProject(projectId), listSprints(projectId)])
    project.value = proj
    sprints.value = sp
    const active = sp.find(s => s.status === 'ACTIVE')
    if (active) selectedSprintId.value = active.id
    await loadBoard()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

async function loadBoard() {
  try {
    const data = await getBoard(projectId, selectedSprintId.value ?? undefined)
    const empty: Record<IssueStatus, Issue[]> = { BACKLOG: [], TODO: [], IN_PROGRESS: [], IN_REVIEW: [], DONE: [] }
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
  updateIssue(projectId, issue.id, { status: targetStatus })
    .then(() => loadBoard())
    .catch(async (e) => {
      Notify.create({ type: 'negative', message: getErrorMessage(e, '상태 변경 실패') })
      await loadBoard()
    })
}

function openCreateIssue() {
  createDialog.value.open = true
}

function openIssueDetail(issue: Issue) {
  detailDialog.value = { open: true, issue }
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
.board-container {
  overflow-x: auto;
  min-height: calc(100vh - 160px);
}
.board-column {
  min-width: 240px;
  max-width: 320px;
}
.issue-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
