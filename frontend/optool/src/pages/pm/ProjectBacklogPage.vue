<template>
  <q-page class="q-pa-md">
    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <div>
        <div class="row items-center q-gutter-x-sm">
          <span class="text-h6 text-weight-bold">{{ project?.name ?? '...' }}</span>
          <q-badge v-if="project" color="primary" :label="project.key" />
        </div>
        <div class="text-caption text-grey-5 q-mt-xs">백로그</div>
      </div>
      <q-space />
      <q-btn color="primary" unelevated icon="add" label="이슈 추가" @click="createDialog.open = true" />
    </div>

    <!-- 필터 카드 -->
    <q-card class="filter-card q-mb-md" bordered>
      <!-- 검색 -->
      <div class="q-px-md q-pt-md q-pb-sm">
        <q-input
          v-model="filterSearch"
          dense
          outlined
          clearable
          placeholder="이슈 제목으로 검색..."
          class="filter-search-input"
        >
          <template #prepend>
            <q-icon name="search" color="grey-5" />
          </template>
          <template #append>
            <q-btn flat dense round icon="refresh" color="grey-5" size="sm" @click="loadIssues">
              <q-tooltip>새로고침</q-tooltip>
            </q-btn>
          </template>
        </q-input>
      </div>

      <q-separator />

      <!-- 필터 칩 행 -->
      <div class="row items-center q-px-md q-py-xs q-gutter-x-xs flex-wrap">
        <span class="text-caption text-grey-5 q-mr-xs" style="line-height: 32px">필터</span>

        <!-- 상태 -->
        <q-chip
          :color="filterStatus ? 'primary' : undefined"
          :text-color="filterStatus ? 'white' : 'grey-8'"
          :outline="!filterStatus"
          clickable
          :removable="!!filterStatus"
          @remove="filterStatus = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterStatus" name="radio_button_checked" size="10px" class="q-mr-xs" />
          <span>{{ filterStatus ? STATUS_LABEL[filterStatus] : '상태' }}</span>
          <q-icon v-if="!filterStatus" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">상태 선택</q-item-label>
              <q-item
                v-for="opt in statusOptions"
                :key="opt.value"
                clickable
                v-close-popup
                @click="filterStatus = opt.value"
              >
                <q-item-section side style="padding-right: 8px; min-width: 24px">
                  <q-badge :color="STATUS_COLOR[opt.value]" rounded style="width: 8px; height: 8px; min-width: 8px" />
                </q-item-section>
                <q-item-section>{{ opt.label }}</q-item-section>
                <q-item-section side v-if="filterStatus === opt.value">
                  <q-icon name="check" color="primary" size="xs" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!-- 우선순위 -->
        <q-chip
          :color="filterPriority ? 'orange-7' : undefined"
          :text-color="filterPriority ? 'white' : 'grey-8'"
          :outline="!filterPriority"
          clickable
          :removable="!!filterPriority"
          @remove="filterPriority = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon
            v-if="filterPriority"
            :name="PRIORITY_ICON[filterPriority]"
            size="10px"
            class="q-mr-xs"
          />
          <span>{{ filterPriority ? PRIORITY_LABEL[filterPriority] : '우선순위' }}</span>
          <q-icon v-if="!filterPriority" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">우선순위 선택</q-item-label>
              <q-item
                v-for="opt in priorityOptions"
                :key="opt.value"
                clickable
                v-close-popup
                @click="filterPriority = opt.value"
              >
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

        <!-- 타입 -->
        <q-chip
          :color="filterType ? TYPE_COLOR[filterType] : undefined"
          :text-color="filterType ? 'white' : 'grey-8'"
          :outline="!filterType"
          clickable
          :removable="!!filterType"
          @remove="filterType = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon
            v-if="filterType"
            :name="TYPE_ICON[filterType]"
            size="10px"
            class="q-mr-xs"
          />
          <span>{{ filterType ? TYPE_LABEL[filterType] : '유형' }}</span>
          <q-icon v-if="!filterType" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">유형 선택</q-item-label>
              <q-item
                v-for="opt in typeOptions"
                :key="opt.value"
                clickable
                v-close-popup
                @click="filterType = opt.value"
              >
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
          clickable
          :removable="!!filterAssigneeId"
          @remove="filterAssigneeId = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterAssigneeId" name="person" size="10px" class="q-mr-xs" />
          <span>{{ filterAssigneeId ? (memberOptions.find(m => m.value === filterAssigneeId)?.label ?? '담당자') : '담당자' }}</span>
          <q-icon v-if="!filterAssigneeId" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 170px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">담당자 선택</q-item-label>
              <q-item v-if="memberOptions.length === 0" class="text-grey-5 text-caption q-px-md q-py-xs">
                멤버가 없습니다
              </q-item>
              <q-item
                v-for="opt in memberOptions"
                :key="opt.value"
                clickable
                v-close-popup
                @click="filterAssigneeId = opt.value"
              >
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

        <!-- 필터 초기화 -->
        <q-btn
          v-if="hasFilter"
          flat dense no-caps
          icon="filter_list_off"
          label="초기화"
          color="negative"
          size="sm"
          class="q-ml-xs filter-clear-btn"
          @click="clearFilters"
        />

        <q-space />

        <!-- 이슈 수 -->
        <span class="text-caption text-grey-5 q-mr-sm" style="white-space: nowrap">
          <span class="text-weight-medium text-grey-7">{{ filteredCount }}</span>개 이슈
        </span>

        <!-- 접기/펼치기 -->
        <q-btn-group flat>
          <q-btn flat dense round icon="unfold_more" size="xs" color="grey-6" @click="expandAll">
            <q-tooltip>모두 펼치기</q-tooltip>
          </q-btn>
          <q-btn flat dense round icon="unfold_less" size="xs" color="grey-6" @click="collapseAll">
            <q-tooltip>모두 접기</q-tooltip>
          </q-btn>
        </q-btn-group>
      </div>
    </q-card>

    <q-inner-loading :showing="loading" />

    <!-- 트리 목록 -->
    <q-card flat bordered>
      <q-list separator>
        <q-item v-if="treeRows.length === 0 && !loading" class="q-pa-lg text-grey-6 justify-center">
          이슈가 없습니다.
        </q-item>

        <template v-for="row in treeRows" :key="row.id">
          <!-- 섹션 구분선 -->
          <q-item v-if="row.isDivider" dense class="bg-grey-2">
            <q-item-section>
              <span class="text-caption text-grey-6 text-weight-medium">{{ row.dividerLabel }}</span>
            </q-item-section>
          </q-item>

          <!-- 이슈 행 -->
          <q-item
            v-else-if="row.issue !== null"
            clickable
            @click="openDetail(row.issue)"
            :class="{ 'epic-row': row.issue.type === 'EPIC' }"
            :style="{ paddingLeft: `${row.indent * 28}px` }"
            class="tree-item"
          >
            <!-- 토글 (28px) -->
            <q-item-section class="tree-section-toggle">
              <q-btn
                v-if="row.hasChildren"
                flat dense round size="xs"
                :icon="collapsed.has(row.issue.id) ? 'chevron_right' : 'expand_more'"
                @click.stop="toggleCollapse(row.issue.id)"
              />
            </q-item-section>

            <!-- 타입 아이콘 (28px) -->
            <q-item-section class="tree-section-icon">
              <q-icon :name="TYPE_ICON[row.issue.type]" :color="TYPE_COLOR[row.issue.type]" size="18px" />
            </q-item-section>

            <!-- 본문 -->
            <q-item-section>
              <q-item-label :class="{ 'text-weight-bold': row.issue.type === 'EPIC' }">
                <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ row.issue.number }}</span>
                {{ row.issue.title }}
              </q-item-label>
              <q-item-label caption class="q-mt-xs">
                <q-badge :color="STATUS_COLOR[row.issue.status]" :label="STATUS_LABEL[row.issue.status]" class="q-mr-xs" />
                <q-icon :name="PRIORITY_ICON[row.issue.priority]" :color="PRIORITY_COLOR[row.issue.priority]" size="xs" />
                <span v-if="row.issue.epicTitle && row.issue.type !== 'EPIC'" class="text-grey-5 q-ml-sm text-caption">
                  {{ row.issue.epicTitle }}
                </span>
              </q-item-label>
            </q-item-section>

            <!-- 담당자 -->
            <q-item-section side>
              <div class="assignee-chip">
                <q-avatar
                  v-if="row.issue.assigneeName"
                  size="22px"
                  color="teal"
                  text-color="white"
                  font-size="10px"
                  class="q-mr-xs"
                >
                  {{ row.issue.assigneeName.charAt(0).toUpperCase() }}
                </q-avatar>
                <span class="text-caption" :class="row.issue.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                  {{ row.issue.assigneeName ?? '미배정' }}
                </span>
              </div>
            </q-item-section>
          </q-item>
        </template>
      </q-list>
    </q-card>

    <IssueFormDialog
      v-model="createDialog.open"
      :project-id="projectId"
      @created="onIssueCreated"
    />

    <IssueDetailDialog
      v-model="detailDialog.open"
      :project-id="projectId"
      :project-key="project?.key ?? ''"
      :issue="detailDialog.issue"
      @updated="onIssueUpdated"
      @deleted="onIssueDeleted"
      @update:model-value="!$event && loadIssues()"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify } from 'quasar'
import {
  listIssues,
  ISSUE_STATUSES, STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR, PRIORITY_ICON, PRIORITY_COLOR, PRIORITY_LABEL,
  type Issue, type IssueStatus, type IssuePriority, type IssueType,
} from 'src/services/pm/issue'
import { getProject, listProjectMembers, type Project, type ProjectMember } from 'src/services/pm/project'
import IssueFormDialog from './components/IssueFormDialog.vue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const projectId = route.params.projectId as string

const project = ref<Project | null>(null)
const allIssues = ref<Issue[]>([])
const members = ref<ProjectMember[]>([])
const loading = ref(false)

const filterSearch = ref('')
const filterStatus = ref<IssueStatus | null>(null)
const filterPriority = ref<IssuePriority | null>(null)
const filterType = ref<IssueType | null>(null)
const filterAssigneeId = ref<string | null>(null)

const collapsed = ref(new Set<string>())

const createDialog = ref({ open: false })
const detailDialog = ref({ open: false, issue: null as Issue | null })

const TYPE_LABEL: Record<IssueType, string> = {
  EPIC: 'Epic', STORY: 'Story', TASK: 'Task', BUG: 'Bug', SUB_TASK: 'Sub-task',
}

const statusOptions: { label: string; value: IssueStatus }[] =
  ISSUE_STATUSES.map(s => ({ label: STATUS_LABEL[s], value: s }))

const priorityOptions: { label: string; value: IssuePriority }[] = [
  { label: '최고', value: 'HIGHEST' }, { label: '높음', value: 'HIGH' },
  { label: '보통', value: 'MEDIUM' }, { label: '낮음', value: 'LOW' }, { label: '최저', value: 'LOWEST' },
]

const typeOptions: { label: string; value: IssueType }[] = [
  { label: 'Epic', value: 'EPIC' }, { label: 'Story', value: 'STORY' },
  { label: 'Task', value: 'TASK' }, { label: 'Bug', value: 'BUG' }, { label: 'Sub-task', value: 'SUB_TASK' },
]

const memberOptions = computed(() =>
  members.value.map(m => ({ label: m.userName || m.userEmail, value: m.userId }))
)

const hasFilter = computed(() =>
  !!(filterSearch.value || filterStatus.value || filterPriority.value || filterType.value || filterAssigneeId.value)
)

function clearFilters() {
  filterSearch.value = ''
  filterStatus.value = null
  filterPriority.value = null
  filterType.value = null
  filterAssigneeId.value = null
}

// ── 행 타입 (flat 구조로 vue-tsc 에러 방지) ──────────────────────────
interface BacklogRow {
  id: string
  isDivider: boolean
  dividerLabel: string
  issue: Issue | null
  indent: 0 | 1 | 2
  hasChildren: boolean
}

function makeIssueRow(issue: Issue, indent: 0 | 1 | 2, hasChildren: boolean): BacklogRow {
  return { id: issue.id, isDivider: false, dividerLabel: '', issue, indent, hasChildren }
}

function makeDividerRow(id: string, label: string): BacklogRow {
  return { id, isDivider: true, dividerLabel: label, issue: null, indent: 0, hasChildren: false }
}

// ── 트리 빌드 ────────────────────────────────────────────────────────
const treeRows = computed<BacklogRow[]>(() => {
  const all = allIssues.value
  const epics   = all.filter(i => i.type === 'EPIC')
  const epicIds = new Set(epics.map(e => e.id))
  const mains   = all.filter(i => i.type !== 'EPIC' && i.type !== 'SUB_TASK')
  const mainIds = new Set(mains.map(m => m.id))
  const subs    = all.filter(i => i.type === 'SUB_TASK')

  const active = hasFilter.value

  const matches = (issue: Issue): boolean => {
    const q = filterSearch.value.toLowerCase()
    if (q && !issue.title.toLowerCase().includes(q)) return false
    if (filterStatus.value     && issue.status     !== filterStatus.value)     return false
    if (filterPriority.value   && issue.priority   !== filterPriority.value)   return false
    if (filterType.value       && issue.type       !== filterType.value)       return false
    if (filterAssigneeId.value && issue.assigneeId !== filterAssigneeId.value) return false
    return true
  }

  // subtask 인덱스 (parentIssueId → Issue[])
  const subsByParent: Record<string, Issue[]> = {}
  for (const s of subs) {
    const pid = s.parentIssueId
    if (pid && mainIds.has(pid)) {
      const existing = subsByParent[pid]
      if (existing) existing.push(s)
      else subsByParent[pid] = [s]
    }
  }

  // main 이슈 인덱스 (epicId → Issue[])
  const mainsByEpic: Record<string, Issue[]> = {}
  const orphanMains: Issue[] = []
  for (const m of mains) {
    const eid = m.epicId && epicIds.has(m.epicId) ? m.epicId : null
    if (eid) {
      const existing = mainsByEpic[eid]
      if (existing) existing.push(m)
      else mainsByEpic[eid] = [m]
    } else {
      orphanMains.push(m)
    }
  }

  // epic에 속하지 않는 subtask
  const orphanSubs = subs.filter(s => !s.parentIssueId || !mainIds.has(s.parentIssueId))

  const rows: BacklogRow[] = []

  // main 노드 + subtask 추가 헬퍼
  const addMain = (main: Issue, indent: 0 | 1 | 2, subIndent: 1 | 2) => {
    const children: Issue[] = subsByParent[main.id] ?? []
    const visibleSubs = active ? children.filter(matches) : children
    if (active && !matches(main) && visibleSubs.length === 0) return

    rows.push(makeIssueRow(main, indent, children.length > 0))
    if (!collapsed.value.has(main.id)) {
      for (const s of visibleSubs) {
        rows.push(makeIssueRow(s, subIndent, false))
      }
    }
  }

  // ── Epic 섹션 ──
  let hasEpicRows = false
  for (const epic of epics) {
    const epicMains: Issue[] = mainsByEpic[epic.id] ?? []
    const selfOk = !active || matches(epic)

    let hasVisibleDesc = !active && epicMains.length > 0
    if (active && !selfOk) {
      for (const m of epicMains) {
        const children: Issue[] = subsByParent[m.id] ?? []
        if (matches(m) || children.some(issue => matches(issue))) {
          hasVisibleDesc = true
          break
        }
      }
    }
    if (active && !selfOk && !hasVisibleDesc) continue

    rows.push(makeIssueRow(epic, 0, epicMains.length > 0))
    hasEpicRows = true

    if (!collapsed.value.has(epic.id)) {
      for (const m of epicMains) addMain(m, 1, 2)
    }
  }

  // ── 에픽 없음 섹션 ──
  const orphanRows: BacklogRow[] = []

  for (const m of orphanMains) {
    const children: Issue[] = subsByParent[m.id] ?? []
    const visibleSubs = active ? children.filter(matches) : children
    if (active && !matches(m) && visibleSubs.length === 0) continue

    orphanRows.push(makeIssueRow(m, 0, children.length > 0))
    if (!collapsed.value.has(m.id)) {
      for (const s of visibleSubs) orphanRows.push(makeIssueRow(s, 1, false))
    }
  }
  for (const s of orphanSubs) {
    if (!active || matches(s)) orphanRows.push(makeIssueRow(s, 0, false))
  }

  if (orphanRows.length > 0) {
    if (hasEpicRows) rows.push(makeDividerRow('divider-no-epic', '에픽 없음'))
    rows.push(...orphanRows)
  }

  return rows
})

const filteredCount = computed(() => treeRows.value.filter(r => !r.isDivider).length)

// ── 접기/펼치기 ──────────────────────────────────────────────────────
function toggleCollapse(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function expandAll() {
  collapsed.value = new Set()
}

function collapseAll() {
  const next = new Set<string>()
  for (const issue of allIssues.value) {
    if (issue.type === 'EPIC' || allIssues.value.some(s => s.parentIssueId === issue.id)) {
      next.add(issue.id)
    }
  }
  collapsed.value = next
}

// ── 데이터 로드 ──────────────────────────────────────────────────────
async function loadIssues() {
  loading.value = true
  try {
    allIssues.value = await listIssues(projectId)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '이슈 로드 실패') })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [proj, issues, mems] = await Promise.all([
      getProject(projectId),
      listIssues(projectId),
      listProjectMembers(projectId),
    ])
    project.value = proj
    allIssues.value = issues
    members.value = mems
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function openDetail(issue: Issue) {
  detailDialog.value = { open: true, issue }
}

function onIssueCreated(issue: Issue) {
  allIssues.value.unshift(issue)
}

function onIssueUpdated() {
  void loadIssues()
}

function onIssueDeleted(issueId: string) {
  allIssues.value = allIssues.value.filter(i => i.id !== issueId)
}
</script>

<style scoped>
/* ── 필터 카드 ── */
.filter-card {
  border-radius: 8px;
}
.filter-search-input :deep(.q-field__control) {
  border-radius: 6px;
}
.filter-chip {
  cursor: pointer;
  font-size: 12px;
  transition: opacity 0.15s;
}
.filter-chip:hover {
  opacity: 0.82;
}
.filter-clear-btn {
  font-size: 12px;
  border-radius: 14px;
}

/* ── 트리 행 ── */
.tree-item {
  min-height: 48px;
}
.epic-row {
  background: #f3f0ff;
}
.epic-row:hover {
  background: #e9e3ff;
}
.tree-section-toggle {
  min-width: 28px;
  max-width: 28px;
  padding: 0;
  flex: 0 0 28px;
}
.tree-section-icon {
  min-width: 28px;
  max-width: 28px;
  padding: 0;
  flex: 0 0 28px;
}
.assignee-chip {
  display: flex;
  align-items: center;
  white-space: nowrap;
}
</style>
