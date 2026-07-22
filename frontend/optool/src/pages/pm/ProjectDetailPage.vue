<template>
  <q-page class="q-pa-none">
    <q-inner-loading :showing="loading" />

    <template v-if="project">
      <!-- ── 프로젝트 배너 헤더 ── -->
      <div class="project-banner q-pa-lg">
        <div class="row items-start no-wrap q-gutter-md">
          <!-- 뒤로 -->
          <q-btn
            flat dense round
            icon="arrow_back"
            color="white"
            class="q-mt-xs"
            @click="$router.push('/pm/projects')"
          />

          <!-- 아바타 + 정보 -->
          <div class="col row items-start q-gutter-md">
            <q-avatar color="white" text-color="primary" size="56px" class="text-h5 text-weight-bold shadow-2">
              {{ project.name[0]?.toUpperCase() ?? '' }}
            </q-avatar>
            <div class="col">
              <div class="row items-center q-gutter-sm q-mb-xs">
                <span class="text-h4 text-white text-weight-bold">{{ project.name }}</span>
                <q-chip dense color="white" text-color="primary" class="text-weight-bold">
                  {{ project.key }}
                </q-chip>
              </div>
              <div class="text-body2 banner-desc q-mb-sm">
                {{ project.description || '설명 없음' }}
              </div>
              <div class="row items-center q-gutter-md banner-meta text-caption">
                <span><q-icon name="group" size="xs" class="q-mr-xs" />멤버 {{ members.length }}명</span>
                <span><q-icon name="calendar_today" size="xs" class="q-mr-xs" />{{ fmtDate(project.createdAt) }} 생성</span>
              </div>
            </div>
          </div>

          <!-- 바로가기 버튼 -->
          <div class="column q-gutter-xs" style="flex-shrink:0">
            <q-btn
              outline color="white" dense no-caps
              icon="fa-solid fa-table-columns" label="보드"
              style="min-width:90px"
              @click="goTo('board')"
            />
            <q-btn
              outline color="white" dense no-caps
              icon="fa-solid fa-list" label="백로그"
              style="min-width:90px"
              @click="goTo('backlog')"
            />
            <q-btn
              outline color="white" dense no-caps
              icon="fa-solid fa-rotate" label="스프린트"
              style="min-width:90px"
              @click="goTo('sprints')"
            />
          </div>
        </div>
      </div>

      <!-- ── 탭 ── -->
      <div class="row q-px-lg" style="border-bottom: 1px solid rgba(0,0,0,0.1)">
        <q-tabs v-model="tab" dense align="left" indicator-color="primary" active-color="primary">
          <q-tab name="overview" label="개요" icon="info" />
          <q-tab name="members" label="멤버" icon="group" />
          <q-tab name="settings" label="설정" icon="settings" />
        </q-tabs>
      </div>

      <!-- ── 탭 패널 ── -->
      <q-tab-panels v-model="tab" animated class="q-pa-lg tab-panels-bg">

        <!-- 개요 탭 -->
        <q-tab-panel name="overview" class="q-pa-none">

          <!-- 이슈 현황 -->
          <div class="text-subtitle1 text-weight-medium q-mb-sm">이슈 현황</div>
          <div class="row q-col-gutter-md q-mb-md">
            <div v-for="s in statusStats" :key="s.status" class="col-6 col-sm-4 col-md">
              <q-card flat bordered class="stat-card text-center q-pa-lg">
                <div class="stat-count text-weight-bold q-mb-xs" :style="{ color: statFgColor(s.color) }">
                  {{ s.count }}
                </div>
                <q-badge :color="s.color" :label="s.label" class="stat-badge" />
              </q-card>
            </div>
          </div>

          <!-- 분포 바 -->
          <div class="dist-bar q-mb-lg" v-if="totalIssues > 0">
            <div
              v-for="s in statusStats.filter(s => s.count > 0)"
              :key="s.status"
              class="dist-segment"
              :style="{ flex: s.count, backgroundColor: distColor(s.color) }"
            >
              <q-tooltip>{{ s.label }}: {{ s.count }}개</q-tooltip>
            </div>
          </div>

          <div class="row q-col-gutter-md">
            <!-- 프로젝트 정보 -->
            <div class="col-12 col-md-6">
              <q-card flat bordered>
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle1 text-weight-medium">프로젝트 정보</div>
                </q-card-section>
                <q-separator />
                <q-card-section class="q-pa-none">
                  <div class="info-row">
                    <span class="info-label">프로젝트 키</span>
                    <q-badge color="primary" :label="project.key" />
                  </div>
                  <q-separator inset />
                  <div class="info-row">
                    <span class="info-label">생성일</span>
                    <span class="text-body2">{{ fmtDate(project.createdAt) }}</span>
                  </div>
                  <q-separator inset />
                  <div class="info-row">
                    <span class="info-label">멤버 수</span>
                    <span class="text-body2">{{ members.length }}명</span>
                  </div>
                  <q-separator inset />
                  <div class="info-row">
                    <span class="info-label">전체 이슈</span>
                    <span class="text-body2">{{ totalIssues }}개</span>
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <!-- 활성 스프린트 -->
            <div class="col-12 col-md-6">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle1 text-weight-medium">활성 스프린트</div>
                </q-card-section>
                <q-separator />
                <q-card-section v-if="activeSprint">
                  <div class="row items-center q-gutter-xs q-mb-sm">
                    <q-badge color="positive" label="진행 중" />
                    <span class="text-subtitle2">{{ activeSprint.name }}</span>
                  </div>
                  <div v-if="activeSprint.goal" class="text-body2 text-grey-7 q-mb-sm">
                    <q-icon name="flag" size="xs" class="q-mr-xs" />{{ activeSprint.goal }}
                  </div>
                  <div class="row q-gutter-md text-caption text-grey-6 q-mb-md">
                    <span v-if="activeSprint.startDate">
                      <q-icon name="event" size="xs" class="q-mr-xs" />
                      {{ fmtDate(activeSprint.startDate) }} ~ {{ fmtDate(activeSprint.endDate) }}
                    </span>
                    <span>
                      <q-icon name="task_alt" size="xs" class="q-mr-xs" />
                      이슈 {{ activeSprint.issueCount }}개
                    </span>
                  </div>
                  <q-btn color="primary" outline dense no-caps icon="open_in_new" label="보드 열기" @click="goTo('board')" />
                </q-card-section>
                <q-card-section v-else>
                  <div class="column items-center q-py-lg text-grey-5">
                    <q-icon name="loop" size="48px" class="q-mb-sm" />
                    <div class="text-body2">진행 중인 스프린트가 없습니다.</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </q-tab-panel>

        <!-- 멤버 탭 -->
        <q-tab-panel name="members" class="q-pa-none">
          <div class="row items-center q-mb-md">
            <div class="text-subtitle1 text-weight-medium">멤버 목록</div>
            <q-badge :label="`${members.length}명`" color="grey-5" text-color="grey-8" class="q-ml-sm" />
            <q-space />
            <q-btn v-if="isAdmin" color="primary" icon="person_add" label="멤버 추가" no-caps @click="openInvite" />
          </div>

          <q-card flat bordered>
            <q-table
              :rows="members"
              :columns="memberColumns"
              row-key="id"
              flat
              hide-bottom
              :rows-per-page-options="[0]"
              class="member-table"
            >
              <template #body-cell-user="{ row }">
                <q-td>
                  <div class="row items-center q-gutter-sm">
                    <q-avatar
                      :color="avatarColor(row.userName || row.userEmail)"
                      text-color="white"
                      size="34px"
                      class="text-body2 text-weight-medium"
                    >
                      {{ (row.userName || row.userEmail)[0]?.toUpperCase() ?? '' }}
                    </q-avatar>
                    <div>
                      <div class="text-body2 text-weight-medium">{{ row.userName || row.userEmail }}</div>
                      <div class="text-caption text-grey-6">{{ row.userEmail }}</div>
                    </div>
                  </div>
                </q-td>
              </template>

              <template #body-cell-role="{ row }">
                <q-td>
                  <q-select
                    v-if="isAdmin && row.userId !== myUserId"
                    :model-value="row.role"
                    :options="roleOptions"
                    dense outlined
                    emit-value map-options
                    style="min-width: 160px"
                    @update:model-value="val => changeRole(row, val)"
                  />
                  <div v-else class="row items-center q-gutter-xs">
                    <q-icon :name="roleIcon(row.role)" :color="roleColor(row.role)" size="xs" />
                    <span :class="`text-body2 text-${roleColor(row.role)}`">{{ roleLabel(row.role) }}</span>
                  </div>
                </q-td>
              </template>

              <template #body-cell-joinedAt="{ row }">
                <q-td>
                  <span class="text-body2 text-grey-6">{{ fmtDate(row.joinedAt) }}</span>
                </q-td>
              </template>

              <template #body-cell-actions="{ row }">
                <q-td class="text-right">
                  <q-btn
                    v-if="isAdmin && row.userId !== myUserId"
                    flat dense round icon="person_remove" color="negative" size="sm"
                    @click="confirmRemove(row)"
                  >
                    <q-tooltip>멤버 제거</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
            </q-table>
          </q-card>
        </q-tab-panel>

        <!-- 설정 탭 -->
        <q-tab-panel name="settings" class="q-pa-none">
          <div class="column q-gutter-lg settings-container">

            <!-- 기본 정보 -->
            <q-card flat bordered>
              <q-card-section class="q-pb-sm">
                <div class="text-subtitle1 text-weight-medium">기본 정보</div>
              </q-card-section>
              <q-separator />
              <q-card-section class="q-gutter-md">
                <q-input
                  v-model="editForm.name"
                  label="프로젝트 이름 *"
                  outlined
                  hint="표시되는 프로젝트 이름입니다."
                />
                <q-input
                  v-model="editForm.description"
                  label="설명"
                  outlined
                  type="textarea"
                  rows="3"
                  hint="프로젝트에 대한 간단한 설명을 입력하세요."
                />
              </q-card-section>
              <q-separator />
              <q-card-actions class="q-pa-md" align="right">
                <q-btn
                  color="primary" label="저장"
                  :loading="editLoading"
                  :disable="!editForm.name"
                  no-caps
                  @click="submitEdit"
                />
              </q-card-actions>
            </q-card>

            <!-- 라벨 관리 -->
            <q-card flat bordered>
              <q-card-section class="q-pb-sm">
                <div class="row items-center">
                  <div class="text-subtitle1 text-weight-medium">라벨 관리</div>
                  <q-space />
                  <q-btn flat dense no-caps icon="add" label="새 라벨" color="primary" @click="openLabelCreate" />
                </div>
              </q-card-section>
              <q-separator />
              <q-card-section v-if="labels.length === 0" class="q-py-xl text-center text-grey-5">
                <q-icon name="sell" size="40px" class="q-mb-sm" /><br />
                <span class="text-body2">등록된 라벨이 없습니다.</span>
              </q-card-section>
              <div v-else>
                <div
                  v-for="(label, idx) in labels"
                  :key="label.id"
                >
                  <q-separator v-if="idx > 0" />
                  <div class="row items-center q-px-md q-py-sm label-row">
                    <div
                      class="label-dot q-mr-md"
                      :style="{ backgroundColor: label.color }"
                    />
                    <span class="text-body2 col">{{ label.name }}</span>
                    <q-chip
                      dense
                      :style="{ backgroundColor: label.color, color: '#fff' }"
                      class="q-mr-md"
                    >
                      {{ label.name }}
                    </q-chip>
                    <q-btn flat dense round icon="edit" size="sm" color="grey-6" @click="openLabelEdit(label)">
                      <q-tooltip>수정</q-tooltip>
                    </q-btn>
                    <q-btn flat dense round icon="delete_outline" size="sm" color="negative" @click="confirmDeleteLabel(label)">
                      <q-tooltip>삭제</q-tooltip>
                    </q-btn>
                  </div>
                </div>
              </div>
            </q-card>

            <!-- 위험 영역 -->
            <q-card flat class="danger-card">
              <q-card-section>
                <div class="row items-center q-mb-xs">
                  <q-icon name="warning" color="negative" class="q-mr-sm" />
                  <span class="text-subtitle1 text-weight-medium text-negative">위험 영역</span>
                </div>
                <div class="text-body2 text-grey-7 q-mb-lg">
                  프로젝트를 삭제하면 모든 이슈, 스프린트, 댓글, 첨부파일 등 관련 데이터가 <strong>영구적으로 삭제</strong>됩니다. 이 작업은 되돌릴 수 없습니다.
                </div>
                <q-btn
                  v-if="isAdmin"
                  color="negative" outline no-caps
                  icon="delete_forever"
                  label="프로젝트 삭제"
                  @click="confirmDelete"
                />
                <div v-else class="text-caption text-grey-6">
                  <q-icon name="lock" size="xs" class="q-mr-xs" />프로젝트 삭제는 관리자만 가능합니다.
                </div>
              </q-card-section>
            </q-card>

          </div>
        </q-tab-panel>
      </q-tab-panels>
    </template>

    <!-- ── 라벨 다이얼로그 ── -->
    <q-dialog v-model="labelDialog.open" persistent>
      <q-card style="min-width: 380px">
        <q-card-section class="q-pb-sm">
          <div class="text-h6">{{ labelDialog.id ? '라벨 수정' : '새 라벨 만들기' }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-md">
          <q-input v-model="labelDialog.name" label="라벨 이름 *" outlined autofocus />
          <div>
            <div class="text-caption text-grey-6 q-mb-sm">색상 선택</div>
            <div class="row q-gutter-sm">
              <div
                v-for="c in LABEL_COLORS"
                :key="c"
                class="label-color-swatch cursor-pointer"
                :style="{ backgroundColor: c, outline: labelDialog.color === c ? '3px solid #1976d2' : '2px solid transparent' }"
                @click="labelDialog.color = c"
              />
            </div>
          </div>
          <div class="row items-center q-gutter-sm">
            <span class="text-caption text-grey-6">미리보기:</span>
            <q-chip dense :style="{ backgroundColor: labelDialog.color, color: '#fff' }">
              {{ labelDialog.name || '라벨' }}
            </q-chip>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="labelDialog.open = false" />
          <q-btn
            color="primary" :label="labelDialog.id ? '저장' : '생성'"
            :loading="labelDialog.loading"
            :disable="!labelDialog.name"
            no-caps
            @click="submitLabel"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── 멤버 추가 다이얼로그 ── -->
    <q-dialog v-model="inviteDialog.open" persistent>
      <q-card style="min-width: 440px">
        <q-card-section class="q-pb-sm">
          <div class="text-h6">멤버 추가</div>
          <div class="text-body2 text-grey-6">프로젝트에 참여할 사용자를 선택하세요.</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-md">
          <q-select
            v-model="inviteDialog.userId"
            :options="inviteUserOptions"
            label="사용자 *"
            outlined
            emit-value map-options
            use-input input-debounce="0"
            @filter="filterInviteUsers"
          >
            <template #prepend><q-icon name="search" /></template>
            <template #no-option>
              <q-item><q-item-section class="text-grey-6">검색 결과 없음</q-item-section></q-item>
            </template>
          </q-select>
          <q-select
            v-model="inviteDialog.role"
            :options="roleOptions"
            label="역할"
            outlined
            emit-value map-options
          />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="inviteDialog.open = false" />
          <q-btn
            color="primary" label="추가"
            :loading="inviteDialog.loading"
            :disable="!inviteDialog.userId"
            no-caps
            @click="submitInvite"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify, Dialog } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import {
  getProject, listProjectMembers, addProjectMember,
  changeProjectMemberRole, removeProjectMember,
  updateProject, deleteProject,
  type Project, type ProjectMember, type ProjectRole,
} from 'src/services/pm/project'
import { listSprints, type Sprint } from 'src/services/pm/sprint'
import {
  listIssues, listLabels, createLabel, updateLabel, deleteLabel,
  ISSUE_STATUSES, STATUS_LABEL, STATUS_COLOR,
  type IssueStatus, type Label,
} from 'src/services/pm/issue'
import { listPmUsers, type PmUser } from 'src/services/pm/organization'
import { getErrorMessage } from 'src/utils/http/error'

const LABEL_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#14b8a6', '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280',
]

// 아바타 색상 (이름 첫 글자 기반)
const AVATAR_COLORS = ['#7c3aed', '#0891b2', '#059669', '#d97706', '#dc2626', '#db2777']
function avatarColor(name: string): string {
  return AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length] ?? '#6b7280'
}

// Quasar 색상 → CSS hex
const COLOR_MAP: Record<string, string> = {
  'grey-5': '#bdbdbd', 'blue-4': '#42a5f5', 'orange-6': '#fb8c00',
  'purple-5': '#ab47bc', 'green-6': '#43a047',
}
function distColor(quasarColor: string): string {
  return COLOR_MAP[quasarColor] ?? '#9e9e9e'
}
function statFgColor(quasarColor: string): string {
  return COLOR_MAP[quasarColor] ?? '#555'
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const projectId = route.params.projectId as string

const project = ref<Project | null>(null)
const members = ref<ProjectMember[]>([])
const allUsers = ref<PmUser[]>([])
const sprints = ref<Sprint[]>([])
const labels = ref<Label[]>([])
const issueCounts = ref<Record<IssueStatus, number>>({ BACKLOG: 0, TODO: 0, IN_PROGRESS: 0, DONE: 0 })
const loading = ref(false)
const tab = ref('overview')

const myUserId = computed(() => String(auth.me?.id ?? ''))
const isAdmin = computed(() =>
  !!auth.me?.isAdmin ||
  members.value.some(m => m.userId === myUserId.value && (m.role === 'ADMIN' || m.role === 'PROJECT_MANAGER'))
)
const activeSprint = computed(() => sprints.value.find(s => s.status === 'ACTIVE') ?? null)
const totalIssues = computed(() => Object.values(issueCounts.value).reduce((a, b) => a + b, 0))

const statusStats = computed(() =>
  ISSUE_STATUSES.map(s => ({
    status: s,
    label: STATUS_LABEL[s],
    color: STATUS_COLOR[s],
    count: issueCounts.value[s],
  }))
)

const memberColumns = [
  { name: 'user', label: '사용자', field: 'userName', align: 'left' as const },
  { name: 'role', label: '역할', field: 'role', align: 'left' as const },
  { name: 'joinedAt', label: '참여일', field: 'joinedAt', align: 'left' as const },
  { name: 'actions', label: '', field: 'actions', align: 'right' as const },
]

const roleOptions = [
  { label: 'ADMIN', value: 'ADMIN' },
  { label: 'PROJECT MANAGER', value: 'PROJECT_MANAGER' },
  { label: 'DEVELOPER', value: 'DEVELOPER' },
  { label: 'VIEWER', value: 'VIEWER' },
]

function roleLabel(role: ProjectRole) {
  return { ADMIN: 'Admin', PROJECT_MANAGER: 'PM', DEVELOPER: 'Developer', VIEWER: 'Viewer' }[role]
}
function roleColor(role: ProjectRole) {
  return { ADMIN: 'primary', PROJECT_MANAGER: 'teal', DEVELOPER: 'grey-7', VIEWER: 'grey-5' }[role]
}
function roleIcon(role: ProjectRole) {
  return { ADMIN: 'shield', PROJECT_MANAGER: 'manage_accounts', DEVELOPER: 'code', VIEWER: 'visibility' }[role]
}

const editForm = ref({ name: '', description: '' })
const editLoading = ref(false)

const inviteDialog = ref<{ open: boolean; userId: string; role: ProjectRole; loading: boolean }>({ open: false, userId: '', role: 'DEVELOPER', loading: false })
const inviteUserOptions = ref<{ label: string; value: string }[]>([])

const allUserOptions = computed(() => {
  const memberIds = new Set(members.value.map(m => m.userId))
  return allUsers.value
    .filter(u => !memberIds.has(u.id))
    .map(u => ({ label: `${u.name || u.email} (${u.email})`, value: u.id }))
})

onMounted(async () => {
  loading.value = true
  try {
    const [proj, mems, users, sp, issues, lbls] = await Promise.all([
      getProject(projectId),
      listProjectMembers(projectId),
      listPmUsers(),
      listSprints(projectId),
      listIssues(projectId),
      listLabels(projectId),
    ])
    project.value = proj
    members.value = mems
    allUsers.value = users
    sprints.value = sp
    labels.value = lbls
    editForm.value = { name: proj.name, description: proj.description ?? '' }

    const counts: Record<IssueStatus, number> = { BACKLOG: 0, TODO: 0, IN_PROGRESS: 0, DONE: 0 }
    for (const issue of issues) counts[issue.status]++
    issueCounts.value = counts
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function goTo(view: 'board' | 'backlog' | 'sprints') {
  void router.push(`/pm/projects/${projectId}/${view}`)
}

function fmtDate(d: string | null | undefined) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })
}

async function submitEdit() {
  if (!editForm.value.name) return
  editLoading.value = true
  try {
    project.value = await updateProject(projectId, {
      name: editForm.value.name,
      ...(editForm.value.description ? { description: editForm.value.description } : {}),
    })
    Notify.create({ type: 'positive', message: '저장되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    editLoading.value = false
  }
}

// ── 라벨 ──
const labelDialog = ref({ open: false, id: '', name: '', color: '#3b82f6', loading: false })

function openLabelCreate() {
  labelDialog.value = { open: true, id: '', name: '', color: '#3b82f6', loading: false }
}
function openLabelEdit(label: Label) {
  labelDialog.value = { open: true, id: label.id, name: label.name, color: label.color, loading: false }
}

async function submitLabel() {
  if (!labelDialog.value.name) return
  labelDialog.value.loading = true
  try {
    if (labelDialog.value.id) {
      const updated = await updateLabel(projectId, labelDialog.value.id, {
        name: labelDialog.value.name,
        color: labelDialog.value.color,
      })
      const idx = labels.value.findIndex(l => l.id === labelDialog.value.id)
      if (idx !== -1) labels.value[idx] = updated
    } else {
      const created = await createLabel(projectId, { name: labelDialog.value.name, color: labelDialog.value.color })
      labels.value.push(created)
    }
    labelDialog.value.open = false
    Notify.create({ type: 'positive', message: labelDialog.value.id ? '수정되었습니다.' : '라벨이 생성되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    labelDialog.value.loading = false
  }
}

function confirmDeleteLabel(label: Label) {
  Dialog.create({
    title: '라벨 삭제',
    message: `"${label.name}" 라벨을 삭제하시겠습니까?`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteLabel(projectId, label.id)
        labels.value = labels.value.filter(l => l.id !== label.id)
        Notify.create({ type: 'positive', message: '삭제되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

function confirmDelete() {
  Dialog.create({
    title: '프로젝트 삭제',
    message: `"${project.value?.name}" 프로젝트를 삭제하시겠습니까? 모든 이슈와 스프린트가 영구 삭제됩니다.`,
    cancel: true, persistent: true,
    ok: { color: 'negative', label: '삭제' },
  }).onOk(() => {
    void (async () => {
      try {
        await deleteProject(projectId)
        Notify.create({ type: 'positive', message: '프로젝트가 삭제되었습니다.' })
        void router.replace('/pm/projects')
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

function openInvite() {
  inviteDialog.value = { open: true, userId: '', role: 'DEVELOPER', loading: false }
}

function filterInviteUsers(val: string, update: (fn: () => void) => void) {
  update(() => {
    inviteUserOptions.value = allUserOptions.value.filter(u =>
      u.label.toLowerCase().includes(val.toLowerCase())
    )
  })
}

async function submitInvite() {
  inviteDialog.value.loading = true
  try {
    const m = await addProjectMember(projectId, inviteDialog.value.userId, inviteDialog.value.role)
    members.value.push(m)
    inviteDialog.value.open = false
    Notify.create({ type: 'positive', message: '멤버가 추가되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '추가 실패') })
  } finally {
    inviteDialog.value.loading = false
  }
}

async function changeRole(member: ProjectMember, role: ProjectRole) {
  try {
    const updated = await changeProjectMemberRole(projectId, member.userId, role)
    const idx = members.value.findIndex(m => m.id === member.id)
    if (idx !== -1) members.value[idx] = updated
    Notify.create({ type: 'positive', message: '역할이 변경되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '역할 변경 실패') })
    members.value = await listProjectMembers(projectId)
  }
}

function confirmRemove(member: ProjectMember) {
  Dialog.create({
    title: '멤버 제거',
    message: `${member.userName || member.userEmail}을(를) 프로젝트에서 제거하시겠습니까?`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await removeProjectMember(projectId, member.userId)
        members.value = members.value.filter(m => m.id !== member.id)
        Notify.create({ type: 'positive', message: '멤버가 제거되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '제거 실패') })
      }
    })()
  })
}
</script>

<style scoped>
/* ── 배너 ── */
.project-banner {
  background: linear-gradient(135deg, #1565c0 0%, #0288d1 100%);
  min-height: 140px;
}
.banner-desc {
  color: rgba(255, 255, 255, 0.82);
}
.banner-meta {
  color: rgba(255, 255, 255, 0.7);
}

/* ── 탭 패널 ── */
.tab-panels-bg {
  background: #f8f9fa;
}
:deep(.q-tab-panels) {
  background: transparent;
}
:deep(.q-tab-panel) {
  padding: 0;
}

/* ── 이슈 현황 카드 ── */
.stat-card {
  background: #fff;
  transition: box-shadow 0.15s;
}
.stat-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.stat-count {
  font-size: 2rem;
  line-height: 1.1;
}
.stat-badge {
  font-size: 11px;
}

/* ── 분포 바 ── */
.dist-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 2px;
}
.dist-segment {
  border-radius: 2px;
  transition: flex 0.3s;
}

/* ── 프로젝트 정보 행 ── */
.info-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
}
.info-label {
  font-size: 13px;
  color: #9e9e9e;
  min-width: 96px;
  flex-shrink: 0;
}

/* ── 멤버 테이블 ── */
:deep(.member-table .q-table__top),
:deep(.member-table .q-table__bottom) {
  display: none;
}
:deep(.member-table tbody td) {
  padding: 10px 16px;
}

/* ── 설정 ── */

/* ── 라벨 행 ── */
.label-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.label-row:hover {
  background: #fafafa;
}

/* ── 위험 영역 ── */
.danger-card {
  border: 1px solid #ef9a9a !important;
  background: #fff8f8;
}

/* ── 라벨 색상 스와치 ── */
.label-color-swatch {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  outline-offset: 2px;
  transition: transform 0.1s;
}
.label-color-swatch:hover {
  transform: scale(1.15);
}
</style>
