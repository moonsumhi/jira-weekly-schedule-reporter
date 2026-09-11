<template>
  <q-page padding>

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="text-h5 text-weight-bold">내 SR 목록</div>
        <div class="text-caption text-grey-6">내가 등록했거나 같은 팀에서 등록한 SR 현황을 확인합니다.</div>
      </div>
      <HelpButton feature="sr-my" guide-path="/pm/sr/guide" class="q-mr-sm" />
      <q-btn color="primary" icon="add" label="SR 접수" to="/pm/sr/new" unelevated />
    </div>

    <div class="row items-center q-mb-sm" style="gap: 6px;">
      <span class="text-caption text-grey-6 q-mr-xs">등록자</span>
      <q-chip
        v-for="scope in ownerTabs" :key="scope.key"
        :color="ownerScope === scope.key ? 'primary' : 'grey-3'"
        :text-color="ownerScope === scope.key ? 'white' : 'grey-7'"
        clickable dense
        @click="ownerScope = scope.key"
      >
        {{ scope.label }}
        <span class="q-ml-xs" :class="ownerScope === scope.key ? 'text-white' : 'text-grey-5'" style="font-size:0.72rem">{{ scope.count }}</span>
      </q-chip>
      <q-space />
      <q-btn
        flat dense size="sm" no-caps icon="tune" label="상세 필터"
        :class="detailFiltersExpanded ? 'text-indigo-7' : 'text-grey-6'"
        class="q-px-xs" @click="detailFiltersExpanded = !detailFiltersExpanded"
      >
        <q-badge v-if="activeFilterCount" color="indigo-7" :label="activeFilterCount" class="q-ml-xs" />
      </q-btn>
      <q-btn v-if="activeFilterCount" flat dense size="sm" no-caps color="grey-6" icon="refresh" label="필터 초기화" @click="resetDetailFilters" />
    </div>

    <q-slide-transition>
      <div v-show="detailFiltersExpanded" class="sr-advanced-panel q-mb-sm">
        <q-separator class="q-mb-md" />
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-sm-6 col-md-3">
            <q-select v-model="categoryFilter" :options="categoryOptions" label="카테고리" dense outlined clearable emit-value map-options bg-color="white">
              <template #prepend><q-icon name="category" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select v-model="requesterFilter" :options="requesterOptions" label="접수자" dense outlined clearable emit-value map-options bg-color="white">
              <template #prepend><q-icon name="person" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select v-model="assigneeFilter" :options="assigneeOptions" label="담당자" dense outlined clearable emit-value map-options bg-color="white">
              <template #prepend><q-icon name="manage_accounts" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select v-model="statusFilter" :options="statusOptions" label="현재 상황" dense outlined clearable emit-value map-options bg-color="white">
              <template #prepend><q-icon name="task_alt" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
        </div>
      </div>
    </q-slide-transition>

    <!-- 탭 + 검색 -->
    <div class="row items-center q-mb-sm" style="gap: 8px;">
      <div class="row q-gutter-xs" style="flex:1; flex-wrap:wrap;">
        <q-chip
          v-for="tab in statusTabs" :key="tab.key"
          :color="activeTab === tab.key ? tab.color : 'grey-3'"
          :text-color="activeTab === tab.key ? 'white' : 'grey-7'"
          clickable dense
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.count > 0" class="q-ml-xs"
            :class="activeTab === tab.key ? 'text-white' : 'text-grey-5'"
            style="font-size:0.72rem">{{ tab.count }}</span>
        </q-chip>
      </div>
      <q-input
        v-model="search"
        dense outlined clearable
        placeholder="제목 · 시스템 · SR번호 · 요청자 검색"
        style="width: min(440px, 100%); min-width: 320px"
      >
        <template #prepend><q-icon name="search" size="18px" color="grey-5" /></template>
      </q-input>
    </div>

    <!-- 목록 카드 -->
    <q-card flat bordered class="sr-list-card">

      <!-- 로딩 -->
      <div v-if="loading" class="flex flex-center q-pa-xl">
        <q-spinner size="2.5rem" color="primary" />
      </div>

      <!-- 빈 상태 -->
      <div v-else-if="!filteredRows.length" class="column flex-center q-pa-xl text-grey-5">
        <q-icon name="inbox" size="3.5rem" class="q-mb-sm" />
        <div class="text-subtitle2">{{ search ? '검색 결과가 없습니다.' : '접수한 SR이 없습니다.' }}</div>
        <q-btn v-if="!search" color="primary" label="SR 접수하기" to="/pm/sr/new" class="q-mt-md" outline />
      </div>

      <!-- 행 목록 -->
      <div v-else>
        <div
          v-for="row in filteredRows" :key="row.id"
          class="sr-row"
          :class="{ 'sr-row--delayed': row.isDelayed }"
          @click="$router.push(`/pm/sr/${row.id}`)"
        >
          <!-- 우선순위 바 -->
          <div class="priority-bar" :style="{ background: priorityHex(row.priority) }" />

          <!-- 본문 -->
          <div class="sr-row__body">
            <div class="row items-center q-gutter-xs q-mb-xs">
              <span class="text-caption text-grey-5">{{ row.srNo }}</span>
              <q-badge v-if="row.isUrgent" color="red" label="긴급" style="font-size:0.65rem" />
              <q-badge v-if="row.isDelayed" color="negative" label="지연" style="font-size:0.65rem" />
            </div>
            <div class="sr-title text-body2 text-weight-medium text-dark">{{ formatTitle(row) }}</div>
          </div>

          <!-- 우측 메타 -->
          <div class="sr-row__meta text-right q-pr-sm">
            <div class="q-mb-xs">
              <q-chip :color="statusColor(row.status)" text-color="white" dense size="xs" style="font-size:0.7rem">
                {{ statusLabel(row.status) }}
              </q-chip>
            </div>
            <div class="text-caption text-grey-5 q-mb-xs">
              {{ row.assigneeName ? `담당: ${row.assigneeName}` : `접수 ${fmtDate(row.createdAt)}` }}
            </div>
            <div v-if="row.requesterId !== currentUserId" class="text-caption text-primary q-mb-xs">
              요청자 {{ row.requesterName }}<span v-if="row.requesterDepartment"> · {{ row.requesterDepartment }}</span>
            </div>
            <div v-if="row.plannedDueDate"
              class="text-caption"
              :class="row.isDelayed ? 'text-negative text-weight-medium' : 'text-grey-5'">
              완료 목표 {{ fmtDate(row.plannedDueDate) }}
            </div>
            <div v-if="row.desiredDueDate"
              class="text-caption"
              :class="row.isDelayed && !row.plannedDueDate ? 'text-negative text-weight-medium' : 'text-grey-5'">
              완료 희망 {{ fmtDate(row.desiredDueDate) }}
            </div>
          </div>

          <!-- 액션 -->
          <div class="sr-row__actions" @click.stop>
            <q-btn v-if="canCancel(row)" flat round dense icon="cancel" size="sm" color="grey-5"
              @click="onCancel(row)">
              <q-tooltip>취소</q-tooltip>
            </q-btn>
            <q-icon name="chevron_right" color="grey-4" size="18px" />
          </div>
        </div>
      </div>
    </q-card>

    <!-- 취소 다이얼로그 -->
    <q-dialog v-model="cancelDialog">
      <q-card style="min-width:420px">
        <q-card-section class="bg-negative text-white q-pb-sm">
          <div class="text-h6">SR 취소</div>
          <div class="text-caption opacity-80">{{ selectedSR?.srNo }} · {{ selectedSR?.title }}</div>
        </q-card-section>
        <q-card-section class="q-pt-md">
          <q-input v-model="cancelReason" label="취소 사유 *" outlined type="textarea" rows="4"
            :rules="[v => !!v || '취소 사유를 입력해주세요.']" />
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="닫기" v-close-popup />
          <q-btn color="negative" unelevated label="취소 확인" @click="confirmCancel" :loading="cancelling" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { fmtDateKst } from 'src/utils/time/kst'
import {
  listMySRs, cancelSR,
  SR_STATUS_LABEL, SR_STATUS_COLOR,
  REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL, SR_PRIORITY_COLOR,
  type SRListItem,
} from 'src/services/sr'

const $q = useQuasar()
const authStore = useAuthStore()
const loading      = ref(false)
const rows         = ref<SRListItem[]>([])
const cancelDialog = ref(false)
const cancelReason = ref('')
const cancelling   = ref(false)
const selectedSR   = ref<SRListItem | null>(null)
const activeTab    = ref('all')
const ownerScope   = ref<'all' | 'mine' | 'team'>('mine')
const detailFiltersExpanded = ref(false)
const search       = ref('')
const categoryFilter = ref<string | null>(null)
const requesterFilter = ref<string | null>(null)
const assigneeFilter = ref<string | null>(null)
const statusFilter = ref<string | null>(null)
const currentUserId = computed(() => String(authStore.me?.id ?? ''))
const activeFilterCount = computed(() => [categoryFilter.value, requesterFilter.value, assigneeFilter.value, statusFilter.value].filter(Boolean).length)

function resetDetailFilters() {
  categoryFilter.value = null
  requesterFilter.value = null
  assigneeFilter.value = null
  statusFilter.value = null
}

const ownerTabs = computed(() => {
  const mine = rows.value.filter(row => row.requesterId === currentUserId.value).length
  return [
    { key: 'all' as const, label: '전체', count: rows.value.length },
    { key: 'mine' as const, label: '내가 등록', count: mine },
    { key: 'team' as const, label: '팀원 등록', count: rows.value.length - mine },
  ]
})

const ownerRows = computed(() => {
  if (ownerScope.value === 'mine') return rows.value.filter(row => row.requesterId === currentUserId.value)
  if (ownerScope.value === 'team') return rows.value.filter(row => row.requesterId !== currentUserId.value)
  return rows.value
})

const categoryOptions = computed(() => Array.from(new Set(ownerRows.value.map(row => row.requestType)))
  .map(value => ({ value, label: requestTypeLabel(value) }))
  .sort((a, b) => a.label.localeCompare(b.label, 'ko')))

const requesterOptions = computed(() => {
  const options = new Map<string, string>()
  ownerRows.value.forEach(row => options.set(row.requesterId, row.requesterName))
  return Array.from(options, ([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ko'))
})

const assigneeOptions = computed(() => {
  const options = new Map<string, string>()
  ownerRows.value.forEach(row => options.set(row.assigneeId ?? '__unassigned__', row.assigneeName ?? '미지정'))
  return Array.from(options, ([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ko'))
})

const statusOptions = computed(() => Array.from(new Set(ownerRows.value.map(row => row.status)))
  .map(value => ({ value, label: statusLabel(value) }))
  .sort((a, b) => a.label.localeCompare(b.label, 'ko')))

const GROUP_MAP: Record<string, string> = {
  DRAFT: 'draft',
  SUBMITTED: 'active', REVIEWING: 'active', APPROVED: 'active', ASSIGNED: 'active', IN_PROGRESS: 'active',
  PENDING_INFO: 'pending',
  COMPLETED: 'done', CONFIRMING: 'done', CLOSED: 'done',
  REJECTED: 'ended', ON_HOLD: 'ended', CANCELLED: 'ended',
}

const GROUP_META = [
  { key: 'all',     label: '전체',      color: 'grey-7'   },
  { key: 'draft',   label: '임시저장',  color: 'grey-6'   },
  { key: 'active',  label: '진행 중',   color: 'blue-7'   },
  { key: 'pending', label: '확인 요청', color: 'amber-8'  },
  { key: 'done',    label: '완료',      color: 'positive' },
  { key: 'ended',   label: '반려/취소', color: 'grey-5'   },
]

const statusTabs = computed(() => {
  const counts: Record<string, number> = {}
  ownerRows.value.forEach(r => {
    const g = GROUP_MAP[r.status] ?? 'ended'
    counts[g] = (counts[g] ?? 0) + 1
  })
  return GROUP_META
    .filter(m => m.key === 'all' || (counts[m.key] ?? 0) > 0)
    .map(m => ({ ...m, count: m.key === 'all' ? ownerRows.value.length : (counts[m.key] ?? 0) }))
})

const filteredRows = computed(() => {
  let list = ownerRows.value
  if (categoryFilter.value) list = list.filter(row => row.requestType === categoryFilter.value)
  if (requesterFilter.value) list = list.filter(row => row.requesterId === requesterFilter.value)
  if (assigneeFilter.value) {
    list = list.filter(row => (row.assigneeId ?? '__unassigned__') === assigneeFilter.value)
  }
  if (statusFilter.value) list = list.filter(row => row.status === statusFilter.value)
  if (activeTab.value !== 'all') {
    list = list.filter(r => GROUP_MAP[r.status] === activeTab.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(r =>
      r.title.toLowerCase().includes(q) ||
      (r.relatedSystem ?? '').toLowerCase().includes(q) ||
      r.srNo.toLowerCase().includes(q) ||
      r.requesterName.toLowerCase().includes(q)
    )
  }
  return list
})

const PRIORITY_HEX: Record<string, string> = {
  CRITICAL: '#ef5350', HIGH: '#ff9800', MEDIUM: '#42a5f5', LOW: '#bdbdbd',
}

function priorityHex(p: string)      { return PRIORITY_HEX[p] ?? '#bdbdbd' }
function formatTitle(row: SRListItem) {
  const type = requestTypeLabel(row.requestType)
  const sys  = row.relatedSystem ? `(${row.relatedSystem})` : ''
  return `[${type}]${sys} ${row.title}`
}
function statusLabel(s: string)      { return (SR_STATUS_LABEL   as Record<string,string>)[s] ?? s }
function statusColor(s: string)      { return (SR_STATUS_COLOR   as Record<string,string>)[s] ?? 'grey' }
function priorityLabel(s: string)    { return (SR_PRIORITY_LABEL as Record<string,string>)[s] ?? s }
function priorityColor(s: string)    { return (SR_PRIORITY_COLOR as Record<string,string>)[s] ?? 'grey' }
function requestTypeLabel(s: string) { return (REQUEST_TYPE_LABEL as Record<string,string>)[s] ?? s }
function fmtDate(d: string | null)   { return fmtDateKst(d) }
function canCancel(row: SRListItem)  { return row.requesterId === currentUserId.value && !['CLOSED','CANCELLED','REJECTED'].includes(row.status) }

async function fetchList() {
  loading.value = true
  try {
    rows.value = await listMySRs()
  } catch {
    $q.notify({ type: 'negative', message: 'SR 목록을 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

function onCancel(row: SRListItem) {
  selectedSR.value   = row
  cancelReason.value = ''
  cancelDialog.value = true
}

async function confirmCancel() {
  if (!cancelReason.value.trim() || !selectedSR.value) return
  cancelling.value = true
  try {
    await cancelSR(selectedSR.value.id, cancelReason.value)
    $q.notify({ type: 'positive', message: 'SR이 취소되었습니다.' })
    cancelDialog.value = false
    void fetchList()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '취소에 실패했습니다.' })
  } finally {
    cancelling.value = false
  }
}

// suppress unused warning — kept for template compatibility
void priorityLabel; void priorityColor

onMounted(fetchList)
</script>

<style scoped>
.sr-list-card { overflow: hidden; }
.sr-advanced-panel { padding-bottom: 4px; }

.sr-row {
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  transition: background 0.15s;
  cursor: pointer;
}
.sr-row:last-child { border-bottom: none; }
.sr-row:hover { background: #f5f8ff; }
.sr-row--delayed { background: #fff8f8; }
.sr-row--delayed:hover { background: #fff0f0; }

.priority-bar {
  width: 4px;
  align-self: stretch;
  min-height: 64px;
  flex-shrink: 0;
}

.sr-row__body {
  flex: 1;
  padding: 14px 12px;
  min-width: 0;
}
.sr-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sr-row__meta {
  flex-shrink: 0;
  padding: 14px 8px 14px 4px;
  min-width: 130px;
}

.sr-row__actions {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-right: 10px;
  flex-shrink: 0;
}
</style>
