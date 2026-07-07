<template>
  <q-page class="q-pa-md">
    <!-- 헤더 -->
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h5">내 이슈</div>
      <q-space />
      <q-input
        v-model="search"
        dense outlined clearable
        placeholder="이슈 검색..."
        style="min-width: 220px"
        debounce="200"
      >
        <template #prepend><q-icon name="search" /></template>
      </q-input>
      <div class="row q-gutter-xs">
        <q-btn
          v-for="g in GROUPS"
          :key="g.value"
          :label="g.label"
          :color="activeGroup === g.value ? 'primary' : 'grey-7'"
          :outline="activeGroup === g.value"
          flat
          dense
          no-caps
          @click="activeGroup = g.value"
        />
      </div>
    </div>

    <q-inner-loading :showing="loading" />

    <div v-if="!loading" class="column q-gutter-md">
      <!-- ── 담당 중 ── -->
      <q-card v-if="showAssigned" flat bordered>
        <div
          class="row items-center q-px-md q-py-sm cursor-pointer section-toggle"
          @click="assignedOpen = !assignedOpen"
        >
          <q-icon :name="assignedOpen ? 'expand_less' : 'expand_more'" color="grey-7" class="q-mr-sm" />
          <span class="text-subtitle1 text-weight-medium q-mr-sm">담당 중</span>
          <q-badge color="primary" :label="filteredAssigned.length" />
        </div>
        <template v-if="assignedOpen">
          <q-separator />
          <div class="issue-table">
            <!-- 헤더 -->
            <div class="issue-table-header row items-center q-px-md q-py-xs text-caption text-grey-6">
              <div class="ic-icon"></div>
              <div class="ic-key">키</div>
              <div class="ic-title">요약</div>
              <div class="ic-priority">우선순위</div>
              <div class="ic-status">상태</div>
              <div class="ic-assignee">담당자</div>
              <div class="ic-due text-right">마감일</div>
            </div>
            <q-separator />
            <!-- 빈 상태 -->
            <div v-if="filteredAssigned.length === 0" class="q-pa-lg text-grey-6 text-body2 text-center">
              이슈가 없습니다.
            </div>
            <!-- 행 -->
            <div
              v-for="issue in filteredAssigned"
              :key="issue.id"
              class="issue-table-row row items-center q-px-md q-py-sm cursor-pointer"
              @click="openDetail(issue)"
            >
              <div class="ic-icon">
                <q-icon :name="TYPE_ICON[issue.type]" :color="TYPE_COLOR[issue.type]" size="xs" />
              </div>
              <div class="ic-key">
                <span class="text-caption text-primary text-weight-medium">
                  {{ issue.projectKey }}-{{ issue.number }}
                </span>
              </div>
              <div class="ic-title">
                <span class="text-body2 ellipsis-text">{{ issue.title }}</span>
              </div>
              <div class="ic-priority">
                <div class="row items-center q-gutter-xs no-wrap">
                  <q-icon :name="PRIORITY_ICON[issue.priority]" :color="PRIORITY_COLOR[issue.priority]" size="xs" />
                  <span class="text-caption">{{ PRIORITY_LABEL[issue.priority] }}</span>
                </div>
              </div>
              <div class="ic-status">
                <q-badge :color="STATUS_COLOR[issue.status]" :label="STATUS_LABEL[issue.status]" />
              </div>
              <div class="ic-assignee">
                <span class="text-caption text-grey-7">{{ issue.assigneeName ?? '미배정' }}</span>
              </div>
              <div class="ic-due text-right">
                <span :class="dueDateClass(issue.dueDate)" class="text-caption">
                  {{ fmtDue(issue.dueDate) }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </q-card>

      <!-- ── 내가 만든 ── -->
      <q-card v-if="showReported" flat bordered>
        <div
          class="row items-center q-px-md q-py-sm cursor-pointer section-toggle"
          @click="reportedOpen = !reportedOpen"
        >
          <q-icon :name="reportedOpen ? 'expand_less' : 'expand_more'" color="grey-7" class="q-mr-sm" />
          <span class="text-subtitle1 text-weight-medium q-mr-sm">내가 만든</span>
          <q-badge color="teal" :label="filteredReported.length" />
        </div>
        <template v-if="reportedOpen">
          <q-separator />
          <div class="issue-table">
            <div class="issue-table-header row items-center q-px-md q-py-xs text-caption text-grey-6">
              <div class="ic-icon"></div>
              <div class="ic-key">키</div>
              <div class="ic-title">요약</div>
              <div class="ic-priority">우선순위</div>
              <div class="ic-status">상태</div>
              <div class="ic-assignee">담당자</div>
              <div class="ic-due text-right">마감일</div>
            </div>
            <q-separator />
            <div v-if="filteredReported.length === 0" class="q-pa-lg text-grey-6 text-body2 text-center">
              이슈가 없습니다.
            </div>
            <div
              v-for="issue in filteredReported"
              :key="issue.id"
              class="issue-table-row row items-center q-px-md q-py-sm cursor-pointer"
              @click="openDetail(issue)"
            >
              <div class="ic-icon">
                <q-icon :name="TYPE_ICON[issue.type]" :color="TYPE_COLOR[issue.type]" size="xs" />
              </div>
              <div class="ic-key">
                <span class="text-caption text-primary text-weight-medium">
                  {{ issue.projectKey }}-{{ issue.number }}
                </span>
              </div>
              <div class="ic-title">
                <span class="text-body2 ellipsis-text">{{ issue.title }}</span>
              </div>
              <div class="ic-priority">
                <div class="row items-center q-gutter-xs no-wrap">
                  <q-icon :name="PRIORITY_ICON[issue.priority]" :color="PRIORITY_COLOR[issue.priority]" size="xs" />
                  <span class="text-caption">{{ PRIORITY_LABEL[issue.priority] }}</span>
                </div>
              </div>
              <div class="ic-status">
                <q-badge :color="STATUS_COLOR[issue.status]" :label="STATUS_LABEL[issue.status]" />
              </div>
              <div class="ic-assignee">
                <span class="text-caption text-grey-7">{{ issue.assigneeName ?? '미배정' }}</span>
              </div>
              <div class="ic-due text-right">
                <span :class="dueDateClass(issue.dueDate)" class="text-caption">
                  {{ fmtDue(issue.dueDate) }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </q-card>

      <!-- ── 프로젝트 현황 ── -->
      <q-card flat bordered>
        <div
          class="row items-center q-px-md q-py-sm cursor-pointer section-toggle"
          @click="statsOpen = !statsOpen"
        >
          <q-icon :name="statsOpen ? 'expand_less' : 'expand_more'" color="grey-7" class="q-mr-sm" />
          <span class="text-subtitle1 text-weight-medium">프로젝트 현황</span>
        </div>
        <template v-if="statsOpen">
          <q-separator />
          <q-card-section>
            <div v-if="stats.length === 0" class="text-grey-6 text-body2">프로젝트가 없습니다.</div>
            <div class="row q-col-gutter-md">
              <div v-for="stat in stats" :key="stat.projectId" class="col-12 col-sm-6 col-md-4">
                <q-card flat bordered>
                  <q-card-section class="q-pa-md">
                    <div class="row items-center q-mb-sm q-gutter-xs">
                      <q-badge color="primary" :label="stat.projectKey" />
                      <span class="text-subtitle2">{{ stat.projectName }}</span>
                    </div>
                    <div class="row q-gutter-sm">
                      <q-badge
                        v-for="(count, status) in stat.statusCounts"
                        :key="status"
                        :color="STATUS_COLOR[status as IssueStatus]"
                        :label="`${STATUS_LABEL[status as IssueStatus]} ${count}`"
                      />
                    </div>
                  </q-card-section>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </template>
      </q-card>
    </div>

    <!-- 이슈 상세 다이얼로그 -->
    <IssueDetailDialog
      v-if="detailIssue"
      v-model="detailOpen"
      :project-id="detailIssue.projectId"
      :project-key="detailIssue.projectKey ?? ''"
      :issue="detailIssue"
      @updated="load"
      @deleted="load"
      @update:model-value="!$event && load()"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Notify } from 'quasar'
import { api } from 'src/boot/axios'
import {
  STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR,
  PRIORITY_ICON, PRIORITY_COLOR, PRIORITY_LABEL,
  type Issue, type IssueStatus,
} from 'src/services/pm/issue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getErrorMessage } from 'src/utils/http/error'

type ProjectStat = {
  projectId: string
  projectName: string
  projectKey: string
  statusCounts: Record<IssueStatus, number>
}

const GROUPS = [
  { label: '전체', value: 'all' as const },
  { label: '담당 중', value: 'assigned' as const },
  { label: '내가 만든', value: 'reported' as const },
]

const loading = ref(false)
const myIssues = ref<Issue[]>([])
const reportedIssues = ref<Issue[]>([])
const stats = ref<ProjectStat[]>([])

const search = ref('')
const activeGroup = ref<'all' | 'assigned' | 'reported'>('all')
const assignedOpen = ref(true)
const reportedOpen = ref(true)
const statsOpen = ref(true)

const detailIssue = ref<Issue | null>(null)
const detailOpen = ref(false)

const showAssigned = computed(() => activeGroup.value === 'all' || activeGroup.value === 'assigned')
const showReported = computed(() => activeGroup.value === 'all' || activeGroup.value === 'reported')

watch(activeGroup, (val) => {
  if (val === 'assigned') assignedOpen.value = true
  if (val === 'reported') reportedOpen.value = true
})

function matchSearch(issue: Issue): boolean {
  if (!search.value) return true
  const q = search.value.toLowerCase()
  return (
    issue.title.toLowerCase().includes(q) ||
    `${issue.projectKey ?? ''}-${issue.number}`.toLowerCase().includes(q)
  )
}

const filteredAssigned = computed(() => myIssues.value.filter(matchSearch))
const filteredReported = computed(() => reportedIssues.value.filter(matchSearch))

function fmtDue(d: string | null): string {
  if (!d) return '-'
  const date = new Date(d)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.floor((date.getTime() - today.getTime()) / 86400000)
  if (diff < 0) return `D+${Math.abs(diff)}`
  if (diff === 0) return 'D-Day'
  return `D-${diff}`
}

function dueDateClass(d: string | null): string {
  if (!d) return 'text-grey-5'
  const date = new Date(d)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.floor((date.getTime() - today.getTime()) / 86400000)
  if (diff < 0) return 'text-negative text-weight-medium'
  if (diff === 0) return 'text-warning text-weight-medium'
  return 'text-grey-6'
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<{
      myIssues: Issue[]
      reportedIssues: Issue[]
      projectStats: ProjectStat[]
    }>('/pm/dashboard')
    myIssues.value = data.myIssues
    reportedIssues.value = data.reportedIssues
    stats.value = data.projectStats
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
}

function openDetail(issue: Issue) {
  detailIssue.value = issue
  detailOpen.value = true
}

onMounted(load)
</script>

<style scoped>
.section-toggle:hover {
  background: rgba(0, 0, 0, 0.03);
}

.issue-table-header {
  background: #f5f5f5;
}

.issue-table-row {
  border-top: 1px solid rgba(0, 0, 0, 0.07);
}
.issue-table-row:hover {
  background: rgba(0, 0, 0, 0.025);
}

/* 고정폭 컬럼 */
.ic-icon     { width: 28px;  flex-shrink: 0; }
.ic-key      { width: 96px;  flex-shrink: 0; padding-right: 8px; }
.ic-title    { flex: 1;      min-width: 0;   padding-right: 12px; }
.ic-priority { width: 72px;  flex-shrink: 0; }
.ic-status   { width: 84px;  flex-shrink: 0; }
.ic-assignee { width: 96px;  flex-shrink: 0; }
.ic-due      { width: 60px;  flex-shrink: 0; }

.ellipsis-text {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
