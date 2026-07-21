<template>
  <q-page padding>

    <!-- ── 헤더 ───────────────────────────────────────────────────────── -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="text-h5 text-weight-bold">SR 관리</div>
        <div class="text-caption text-grey-6">접수된 SR을 검토 · 배정 · 처리합니다.</div>
      </div>
      <HelpButton feature="sr-manage" guide-path="/pm/sr/guide" class="q-mr-xs" />
      <q-btn v-if="isAdminUser" outline color="indigo-7" icon="settings" label="SR 기본 프로젝트"
        @click="srProjectDialog = true" class="q-mr-sm" />
      <q-btn outline color="green-7" icon="download" label="Excel" @click="downloadExcel" :loading="exporting" />
    </div>

    <!-- ── 통계 카드 ─────────────────────────────────────────────────── -->
    <div v-if="stats" class="row q-col-gutter-sm q-mb-lg">
      <div v-for="c in statCards" :key="c.label" class="col-6 col-sm-3 col-md-auto" style="min-width:110px">
        <q-card flat bordered class="text-center q-pa-sm stat-card"
          :class="c.tab ? 'cursor-pointer stat-card--clickable' : ''"
          @click="c.tab && switchStatTab(c.tab)">
          <div class="text-h4 text-weight-bold" :class="`text-${c.color}`">{{ c.value }}</div>
          <div class="text-caption text-grey-6">{{ c.label }}</div>
          <q-tooltip v-if="c.tab">{{ c.label }} 탭으로 이동</q-tooltip>
        </q-card>
      </div>
    </div>

    <!-- ── 검색 / 필터 바 ────────────────────────────────────────────── -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section class="q-pa-sm">
        <SrFilterBar
          :filter="srSearch.filter.value"
          :search="srSearch.search.value"
          :tab="srSearch.activeTab.value"
          :loading="loading"
          :pm-users="pmUsers"
          :presets="srSearch.presets.value"
          :active-chips="resolvedChips"
          @apply="onFilterApply"
          @reset="onFilterReset"
          @chip-remove="onChipRemove"
          @save-preset="onSavePreset"
          @load-preset="onLoadPreset"
          @remove-preset="onRemovePreset"
        />
      </q-card-section>
    </q-card>

    <!-- ── 결과 요약 + 정렬 컨트롤 ──────────────────────────────────── -->
    <div class="row items-center justify-between q-mb-xs">
      <div class="text-caption text-grey-6">
        총 <strong class="text-dark">{{ pagination.rowsNumber.toLocaleString() }}</strong>건
        <span v-if="srSearch.activeFilterCount.value || srSearch.activeTab.value !== 'all'" class="q-ml-xs">
          · 필터 <strong class="text-indigo-7">{{ totalActiveConditions }}</strong>개 적용
        </span>
        <span v-if="filteredRows.length !== rows.length" class="q-ml-xs text-primary">
          (검색 {{ filteredRows.length }}건)
        </span>
      </div>
      <div class="row items-center q-gutter-xs">
        <!-- 정렬 드롭다운 -->
        <q-btn-dropdown
          flat dense size="sm" no-icon-animation
          color="grey-7"
          :label="currentSortLabel"
          icon="sort"
        >
          <q-list dense>
            <q-item
              v-for="opt in SORT_OPTIONS" :key="opt.label"
              clickable v-close-popup
              :active="pagination.sortBy === opt.sortBy && pagination.descending === opt.descending"
              active-class="bg-blue-1"
              @click="applySort(opt)"
            >
              <q-item-section>{{ opt.label }}</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </div>
    </div>

    <!-- ── 테이블 ─────────────────────────────────────────────────────── -->
    <q-card flat bordered>
      <q-table
        :rows="filteredRows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        flat
        :rows-per-page-options="[10, 20, 50, 100]"
        v-model:pagination="pagination"
        @request="onTableRequest"
        no-data-label="조회된 SR이 없습니다."
      >
        <!-- 선택 시 일괄 액션 바 -->
        <template #top>
          <div v-if="selected.length" class="row items-center full-width q-py-xs q-px-sm bulk-bar">
            <span class="text-caption text-grey-7 q-mr-sm">{{ selected.length }}개 선택됨</span>
            <q-btn-dropdown
              color="blue-7" label="상태 일괄 변경" size="sm" unelevated
              :loading="bulkChanging" no-icon-animation>
              <q-list dense>
                <q-item v-for="opt in STATUS_OPTIONS" :key="opt.value"
                  clickable v-close-popup @click="bulkStatusChange(opt.value)">
                  <q-item-section>
                    <q-badge :color="statusColor(opt.value)" :label="opt.label" text-color="white" />
                  </q-item-section>
                </q-item>
              </q-list>
            </q-btn-dropdown>
            <q-btn flat dense size="sm" color="grey-6" icon="close" class="q-ml-xs"
              @click="selected = []">
              <q-tooltip>선택 해제</q-tooltip>
            </q-btn>
          </div>
        </template>

        <template #body="{ row }">
          <q-tr class="cursor-pointer" @click="navigateToDetail(row)">
            <q-td @click.stop>
              <q-checkbox :model-value="isSelected(row)" @update:model-value="toggleSelect(row)" dense />
            </q-td>
            <q-td>
              <span class="text-primary text-weight-medium">{{ row.srNo }}</span>
            </q-td>
            <q-td>
              <div class="row items-center q-gutter-xs no-wrap">
                <span>{{ formatTitle(row) }}</span>
                <q-badge v-if="row.isUrgent"  color="red"      label="긴급" />
                <q-badge v-if="row.isDelayed" color="negative" label="지연" />
              </div>
            </q-td>
            <q-td>{{ row.requesterDepartment }}</q-td>
            <q-td>{{ row.requesterName }}</q-td>
            <q-td class="text-center editable-cell" @click.stop>
              <div class="row items-center justify-center no-wrap">
                <q-badge :color="priorityColor(row.priority)" :label="priorityLabel(row.priority)" outline />
                <q-icon name="edit" size="11px" color="grey-4" class="edit-hint q-ml-xs" />
              </div>
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-card flat>
                  <q-list dense padding style="min-width:130px">
                    <q-item-label header class="text-caption text-grey-6 q-pb-xs">중요도 변경</q-item-label>
                    <q-item v-for="opt in priorityOptions" :key="opt.value"
                      clickable v-close-popup @click="inlinePatch(row, { priority: opt.value })"
                      :active="row.priority === opt.value" active-class="bg-blue-1">
                      <q-item-section>
                        <q-badge :color="priorityColor(opt.value)" :label="opt.label" outline />
                      </q-item-section>
                    </q-item>
                  </q-list>
                </q-card>
              </q-popup-proxy>
            </q-td>
            <!-- 인라인 상태 변경 -->
            <q-td class="text-center editable-cell" @click.stop>
              <div class="inline-block relative-position">
                <q-chip :color="statusColor(row.status)" text-color="white" dense size="sm"
                  :class="changingStatusId === row.id ? '' : 'cursor-pointer'">
                  <q-spinner v-if="changingStatusId === row.id" size="12px" class="q-mr-xs" />
                  {{ statusLabel(row.status) }}
                  <q-popup-proxy v-if="changingStatusId !== row.id" cover transition-show="scale" transition-hide="scale">
                    <q-card flat>
                      <q-list dense padding style="min-width:160px">
                        <q-item-label header class="text-caption text-grey-6 q-pb-xs">상태 변경</q-item-label>
                        <q-item v-for="opt in STATUS_OPTIONS" :key="opt.value"
                          clickable v-close-popup @click="requestStatusChange(row, opt.value)"
                          :active="row.status === opt.value" active-class="bg-blue-1">
                          <q-item-section>
                            <q-badge :color="statusColor(opt.value)" :label="opt.label"
                              text-color="white" style="font-size:0.72rem" />
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </q-card>
                  </q-popup-proxy>
                </q-chip>
              </div>
            </q-td>
            <q-td class="editable-cell" @click.stop="openAssigneePopup(row)">
              <div class="row items-center no-wrap">
                <span class="text-truncate" style="max-width:72px">{{ row.assigneeName || '-' }}</span>
                <q-icon name="edit" size="11px" color="grey-4" class="edit-hint q-ml-xs" />
              </div>
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-card flat class="q-pa-sm" style="min-width:220px">
                  <div class="text-caption text-grey-6 q-mb-sm">담당자 변경</div>
                  <q-select
                    v-model="assigneeInput"
                    :options="filteredPmUsers"
                    option-value="id" option-label="name"
                    emit-value map-options
                    label="담당자 선택"
                    dense outlined
                    use-input hide-selected fill-input
                    input-debounce="0"
                    @filter="filterUsers"
                  >
                    <template #no-option>
                      <q-item><q-item-section class="text-grey">없음</q-item-section></q-item>
                    </template>
                  </q-select>
                  <div class="row justify-end q-mt-sm q-gutter-xs">
                    <q-btn flat dense size="sm" label="취소" v-close-popup />
                    <q-btn unelevated dense size="sm" color="primary" label="저장"
                      v-close-popup :disable="!assigneeInput"
                      @click="saveAssignee(row)" />
                  </div>
                </q-card>
              </q-popup-proxy>
            </q-td>
            <q-td class="text-center editable-cell" @click.stop="openDatePopup(row)">
              <div class="row items-center justify-center no-wrap">
                <span :class="row.isDelayed ? 'text-negative text-weight-medium' : 'text-grey-7'">
                  {{ fmtDate(row.desiredDueDate) || '미지정' }}
                </span>
                <q-icon name="edit" size="11px" color="grey-4" class="edit-hint q-ml-xs" />
              </div>
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-card flat class="q-pa-sm" style="min-width:200px">
                  <div class="text-caption text-grey-6 q-mb-sm">희망완료일 변경</div>
                  <q-input v-model="dateInput" type="date" dense outlined />
                  <div class="row justify-end q-mt-sm q-gutter-xs">
                    <q-btn flat dense size="sm" label="취소" v-close-popup />
                    <q-btn unelevated dense size="sm" color="primary" label="저장"
                      v-close-popup @click="saveDueDate(row)" />
                  </div>
                </q-card>
              </q-popup-proxy>
            </q-td>
            <q-td class="text-center editable-cell" @click.stop="openPlannedDatePopup(row)">
              <div class="row items-center justify-center no-wrap">
                <span :class="row.isDelayed ? 'text-negative text-weight-medium' : 'text-grey-7'">
                  {{ fmtDate(row.plannedDueDate) || '미지정' }}
                </span>
                <q-icon name="edit" size="11px" color="grey-4" class="edit-hint q-ml-xs" />
              </div>
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-card flat class="q-pa-sm" style="min-width:220px">
                  <div class="text-caption text-grey-6 q-mb-sm">완료목표일 변경 <span class="text-grey-4">(지연 판정 기준)</span></div>
                  <q-input v-model="plannedDateInput" type="date" dense outlined class="q-mb-sm" />
                  <q-input v-model="plannedDateReason" label="변경 사유 (선택)" dense outlined type="textarea" rows="2" />
                  <div class="row justify-end q-mt-sm q-gutter-xs">
                    <q-btn flat dense size="sm" label="취소" v-close-popup />
                    <q-btn unelevated dense size="sm" color="primary" label="저장"
                      v-close-popup @click="savePlannedDueDate(row)" />
                  </div>
                </q-card>
              </q-popup-proxy>
            </q-td>
            <q-td class="text-center text-grey-6">{{ fmtDate(row.createdAt) }}</q-td>
            <q-td class="text-center" @click.stop>
              <q-btn flat dense round icon="open_in_new" size="sm" color="grey-7"
                @click="navigateToDetail(row)" />
            </q-td>
          </q-tr>
        </template>

        <template #no-data>
          <div class="full-width column flex-center q-pa-xl text-grey-5">
            <q-icon name="search_off" size="4rem" class="q-mb-md" />
            <div class="text-subtitle1">검색 조건에 맞는 SR이 없습니다.</div>
            <div class="text-caption q-mt-xs">필터를 변경하거나 검색어를 다시 확인해 주세요.</div>
            <q-btn
              outline color="primary" size="sm" label="필터 초기화"
              class="q-mt-md"
              @click="onFilterReset"
            />
          </div>
        </template>
      </q-table>
    </q-card>

    <!-- ── 상태 변경 사유 다이얼로그 ────────────────────────────────── -->
    <q-dialog v-model="statusDialog.open" persistent>
      <q-card style="min-width:400px">
        <q-card-section class="q-pb-sm">
          <div class="text-h6">{{ statusDialog.title }}</div>
          <div class="text-caption text-grey-6">상태를 <strong>{{ statusLabel(statusDialog.newStatus) }}</strong>으로 변경합니다.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="statusDialog.input"
            :label="statusDialog.inputLabel"
            outlined autogrow :rows="3" autofocus
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="변경" unelevated
            :disable="!statusDialog.input.trim()"
            @click="confirmStatusChange" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── SR 기본 프로젝트 설정 다이얼로그 ─────────────────────────── -->
    <q-dialog v-model="srProjectDialog">
      <q-card style="min-width:460px">
        <q-card-section class="bg-indigo-7 text-white q-pb-sm">
          <div class="text-h6">SR 기본 프로젝트 설정</div>
          <div class="text-caption opacity-80">담당자 배정 시 이슈가 자동 등록될 프로젝트를 선택하세요.</div>
        </q-card-section>
        <q-card-section class="q-pt-md">
          <q-select
            v-model="selectedSrProject"
            label="기본 프로젝트 *"
            outlined
            :options="projectOptions"
            option-label="label"
            option-value="value"
            emit-value map-options
            :loading="projectsLoading"
          />
          <div v-if="currentSrDefault" class="text-caption text-indigo-7 q-mt-xs">
            현재 기본 프로젝트: <strong>{{ currentSrDefault }}</strong>
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="indigo-7" unelevated label="저장" :loading="savingProject" @click="saveSrDefaultProject" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import type { QTableProps } from 'quasar'
import { api } from 'src/boot/axios'
import {
  listAllSRs, getSRStats, changeSRStatus, patchSRInline, changePlannedDueDate,
  SR_STATUS_LABEL, SR_STATUS_COLOR,
  REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL, SR_PRIORITY_COLOR,
  SR_PRIORITY_OPTIONS,
  type SRListItem, type SRStats, type SRStatus, type SRStatusChange,
} from 'src/services/sr'
import { listPmUsers, type PmUser } from 'src/services/pm/users'
import { listProjects, setSrDefaultProject, type Project } from 'src/services/pm/project'
import { useAuthStore } from 'src/stores/auth'
import { fmtDateKst } from 'src/utils/time/kst'
import HelpButton from 'src/components/HelpButton.vue'
import SrFilterBar from './components/SrFilterBar.vue'
import {
  useSrSearch,
  buildSrApiParams,
  SR_SORT_OPTIONS,
  type SrFilterState,
  type SrFilterPreset,
} from './useSrSearch'

// ── 상수 ─────────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  'SUBMITTED', 'REVIEWING', 'PENDING_INFO', 'APPROVED', 'ASSIGNED',
  'IN_PROGRESS', 'COMPLETED', 'CONFIRMING', 'CLOSED', 'ON_HOLD', 'REJECTED', 'CANCELLED',
].map(s => ({ value: s, label: (SR_STATUS_LABEL as Record<string, string>)[s] ?? s }))

const SORT_OPTIONS = SR_SORT_OPTIONS

const priorityOptions = SR_PRIORITY_OPTIONS

// ── 스토어 / 라우터 ───────────────────────────────────────────────────────

const $q        = useQuasar()
const route     = useRoute()
const router    = useRouter()
const authStore = useAuthStore()

const isAdminUser = computed(() => authStore.me?.isAdmin || false)

// ── 검색 컴포저블 ─────────────────────────────────────────────────────────

const srSearch = useSrSearch()

// 전체 활성 조건 수 (탭 포함)
const totalActiveConditions = computed(() => {
  let n = srSearch.activeFilterCount.value
  if (srSearch.activeTab.value !== 'all') n++
  return n
})

// assigneeId 칩을 사람 이름으로 치환한 칩 목록
const resolvedChips = computed(() =>
  srSearch.activeChips.value.map(chip => {
    if (chip.key === 'assigneeId') {
      const user = pmUsers.value.find(u => u.id === chip.value)
      return { ...chip, value: user?.name ?? chip.value }
    }
    return chip
  }),
)

// ── 페이지네이션 / 정렬 ───────────────────────────────────────────────────

const pagination = ref({
  page:        1,
  rowsPerPage: 20,
  sortBy:      'created_at',
  descending:  true,
  rowsNumber:  0,
})

const currentSortLabel = computed(() => {
  const opt = SORT_OPTIONS.find(o =>
    o.sortBy === pagination.value.sortBy && o.descending === pagination.value.descending,
  )
  return opt?.label ?? '최신 접수순'
})

function applySort(opt: typeof SORT_OPTIONS[0]) {
  pagination.value.sortBy     = opt.sortBy
  pagination.value.descending = opt.descending
  pagination.value.page       = 1
  void fetchList()
  syncToUrl()
}

// ── 데이터 상태 ───────────────────────────────────────────────────────────

const loading   = ref(false)
const exporting = ref(false)
const rows      = ref<SRListItem[]>([])
const stats     = ref<SRStats | null>(null)
const selected  = ref<SRListItem[]>([])
const pmUsers   = ref<PmUser[]>([])

// 클라이언트사이드 키워드 필터 (현재 페이지 내에서)
const filteredRows = computed(() => {
  const q = (srSearch.search.value ?? '').trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(r =>
    r.title.toLowerCase().includes(q) ||
    r.srNo.toLowerCase().includes(q) ||
    r.requesterName.toLowerCase().includes(q),
  )
})

// ── SR 기본 프로젝트 ──────────────────────────────────────────────────────

const srProjectDialog   = ref(false)
const projectsLoading   = ref(false)
const savingProject     = ref(false)
const allProjects       = ref<Project[]>([])
const selectedSrProject = ref<string | null>(null)

const projectOptions = computed(() =>
  allProjects.value.map(p => ({ label: `[${p.key}] ${p.name}`, value: p.id })),
)
const currentSrDefault = computed(() => {
  const p = allProjects.value.find(p => p.isSrDefault)
  return p ? `[${p.key}] ${p.name}` : null
})

// ── 인라인 편집 상태 ──────────────────────────────────────────────────────

const changingStatusId  = ref<string | null>(null)
const bulkChanging      = ref(false)
const filteredPmUsers   = ref<PmUser[]>([])
const dateInput         = ref('')
const assigneeInput     = ref<string | null>(null)
const plannedDateInput  = ref('')
const plannedDateReason = ref('')

const STATUS_NEEDS_REASON = new Set(['REJECTED', 'ON_HOLD', 'CANCELLED'])
const STATUS_NEEDS_RESULT = new Set(['COMPLETED'])

const statusDialog = ref({
  open:       false,
  row:        null as SRListItem | null,
  newStatus:  '' as SRStatus,
  title:      '',
  inputLabel: '',
  input:      '',
  fieldKey:   '' as 'reason' | 'process_result',
})

// ── 테이블 컬럼 ───────────────────────────────────────────────────────────

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'select',               label: '',           field: 'id',                   align: 'center', style: 'width:40px'  },
  { name: 'sr_no',                label: 'SR 번호',    field: 'sr_no',                align: 'left',   sortable: true, style: 'width:120px' },
  { name: 'title',                label: '요청 제목',  field: 'title',                align: 'left',   sortable: true  },
  { name: 'requester_department', label: '부서',       field: 'requester_department', align: 'left',   sortable: true, style: 'width:90px'  },
  { name: 'requester_name',       label: '요청자',     field: 'requester_name',       align: 'left',   sortable: true, style: 'width:80px'  },
  { name: 'priority',             label: '중요도',     field: 'priority',             align: 'center', sortable: true, style: 'width:70px'  },
  { name: 'status',               label: '상태',       field: 'status',               align: 'center', sortable: true, style: 'width:130px' },
  { name: 'assignee_name',        label: '담당자',     field: 'assignee_name',        align: 'left',   sortable: true, style: 'width:80px'  },
  { name: 'desired_due_date',     label: '희망완료일', field: 'desired_due_date',     align: 'center', sortable: true, style: 'width:95px'  },
  { name: 'planned_due_date',     label: '완료목표일', field: 'planned_due_date',     align: 'center', sortable: true, style: 'width:95px'  },
  { name: 'created_at',           label: '접수일',     field: 'created_at',           align: 'center', sortable: true, style: 'width:90px'  },
  { name: 'actions',              label: '',           field: 'id',                   align: 'center', style: 'width:50px'  },
]

// ── 통계 카드 ─────────────────────────────────────────────────────────────

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '전체',         value: stats.value.total,                    color: 'primary',  tab: 'all'         },
    { label: '진행 중',      value: stats.value.inProgress,               color: 'blue-8',   tab: 'IN_PROGRESS' },
    { label: '완료',         value: stats.value.completed,                color: 'positive', tab: 'COMPLETED'   },
    { label: '지연',         value: stats.value.delayed,                  color: 'negative', tab: null          },
    { label: '보류',         value: stats.value.onHold,                   color: 'brown',    tab: 'ON_HOLD'     },
    { label: '반려',         value: stats.value.rejected,                 color: 'red-8',    tab: 'REJECTED'    },
    { label: '긴급',         value: stats.value.urgentCount,              color: 'red',      tab: null          },
    { label: '평균처리(일)', value: stats.value.avgProcessingDays ?? '-', color: 'grey-7',   tab: null          },
  ]
})

// ── 헬퍼 ─────────────────────────────────────────────────────────────────

function isSelected(row: SRListItem) { return selected.value.some(r => r.id === row.id) }
function toggleSelect(row: SRListItem) {
  const idx = selected.value.findIndex(r => r.id === row.id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(row)
}

function statusLabel(s: string)      { return (SR_STATUS_LABEL   as Record<string, string>)[s] ?? s }
function statusColor(s: string)      { return (SR_STATUS_COLOR   as Record<string, string>)[s] ?? 'grey' }
function priorityLabel(s: string)    { return (SR_PRIORITY_LABEL as Record<string, string>)[s] ?? s }
function priorityColor(s: string)    { return (SR_PRIORITY_COLOR as Record<string, string>)[s] ?? 'grey' }
function requestTypeLabel(s: string) { return (REQUEST_TYPE_LABEL as Record<string, string>)[s] ?? s }
function fmtDate(d: string | null)   { return fmtDateKst(d) }
function formatTitle(row: SRListItem) {
  const type = requestTypeLabel(row.requestType)
  const sys  = row.relatedSystem ? `(${row.relatedSystem})` : ''
  return `[${type}]${sys} ${row.title}`
}

// ── 탭 전환 (통계 카드 클릭) ──────────────────────────────────────────────

function switchStatTab(tab: string) {
  const newFilter = { ...srSearch.filter.value }
  // 통계 카드의 '지연' 탭 클릭 → isDelayed 토글로 처리
  if (tab === 'delayed') {
    newFilter.isDelayed = true
    srSearch.filter.value = newFilter
    srSearch.activeTab.value = 'all'
  } else {
    srSearch.activeTab.value = tab
  }
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

// ── 상세 페이지 이동 ──────────────────────────────────────────────────────

function navigateToDetail(row: SRListItem) {
  sessionStorage.setItem('sr-list-ids', JSON.stringify(filteredRows.value.map(r => r.id)))
  void router.push(`/pm/sr/${row.id}`)
}

// ── API 조회 ──────────────────────────────────────────────────────────────

async function fetchList() {
  loading.value = true
  try {
    const skip = (pagination.value.page - 1) * pagination.value.rowsPerPage
    const params = buildSrApiParams(srSearch.filter.value, srSearch.activeTab.value, {
      skip,
      limit:      pagination.value.rowsPerPage,
      sort_by:    pagination.value.sortBy || 'created_at',
      descending: pagination.value.descending,
    })
    const [page, srStats] = await Promise.all([listAllSRs(params), getSRStats()])
    rows.value  = page.items
    stats.value = srStats
    pagination.value.rowsNumber = page.total
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || 'SR 목록을 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

// ── 필터 바 이벤트 핸들러 ────────────────────────────────────────────────

function onFilterApply(newFilter: SrFilterState, newSearch: string, newTab: string) {
  srSearch.filter.value    = newFilter
  srSearch.search.value    = newSearch
  srSearch.activeTab.value = newTab
  pagination.value.page    = 1
  void fetchList()
  syncToUrl()
}

function onFilterReset() {
  srSearch.reset()
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

function onChipRemove(key: string) {
  srSearch.clearChip(key)
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

function onSavePreset() {
  $q.dialog({
    title: '프리셋 저장',
    prompt: { model: '', label: '프리셋 이름', type: 'text' },
    cancel: true,
  }).onOk((name: string) => {
    if (!name.trim()) return
    srSearch.savePreset(name.trim())
    $q.notify({ type: 'positive', message: '프리셋이 저장되었습니다.' })
  })
}

function onLoadPreset(p: SrFilterPreset) {
  srSearch.loadPreset(p)
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

function onRemovePreset(i: number) {
  srSearch.removePreset(i)
}

// ── 페이지네이션 핸들러 ───────────────────────────────────────────────────

function onTableRequest(props: {
  pagination: { page: number; rowsPerPage: number; sortBy: string; descending: boolean }
}) {
  pagination.value.page        = props.pagination.page
  pagination.value.rowsPerPage = props.pagination.rowsPerPage
  pagination.value.sortBy      = props.pagination.sortBy
  pagination.value.descending  = props.pagination.descending
  void fetchList()
  syncToUrl()
}

// ── URL 동기화 ────────────────────────────────────────────────────────────

function syncToUrl() {
  const q = srSearch.toUrlQuery(
    pagination.value.page,
    pagination.value.rowsPerPage,
    pagination.value.sortBy,
    pagination.value.descending,
  )
  void router.replace({ query: q })
}

function initFromUrl() {
  srSearch.readUrl(route.query as Record<string, string | (string | null)[]>)
  const q = route.query
  if (q.page) pagination.value.page        = Number(q.page)
  if (q.rows) pagination.value.rowsPerPage = Number(q.rows)
  if (q.sort) pagination.value.sortBy      = String(q.sort)
  if (q.asc)  pagination.value.descending  = q.asc !== '1'
}

// ── 인라인 필드 편집 ─────────────────────────────────────────────────────

async function inlinePatch(
  row: SRListItem,
  patch: { priority?: string; desired_due_date?: string | null; assignee_id?: string | null; assignee_name?: string | null },
) {
  try {
    await patchSRInline(row.id, patch)
    if (patch.priority !== undefined)         row.priority       = patch.priority as SRListItem['priority']
    if (patch.desired_due_date !== undefined) row.desiredDueDate = patch.desired_due_date
    if (patch.assignee_id      !== undefined) row.assigneeId     = patch.assignee_id
    if (patch.assignee_name    !== undefined) row.assigneeName   = patch.assignee_name
    $q.notify({ type: 'positive', message: '변경되었습니다.', timeout: 1500 })
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '변경에 실패했습니다.' })
  }
}

function openDatePopup(row: SRListItem) {
  dateInput.value = row.desiredDueDate ? row.desiredDueDate.substring(0, 10) : ''
}

function saveDueDate(row: SRListItem) {
  const iso = dateInput.value ? `${dateInput.value}T00:00:00Z` : null
  void inlinePatch(row, { desired_due_date: iso })
}

function openPlannedDatePopup(row: SRListItem) {
  plannedDateInput.value  = row.plannedDueDate ? row.plannedDueDate.substring(0, 10) : ''
  plannedDateReason.value = ''
}

async function savePlannedDueDate(row: SRListItem) {
  if (!plannedDateInput.value) return
  const iso = `${plannedDateInput.value}T00:00:00Z`
  try {
    await changePlannedDueDate(row.id, iso, plannedDateReason.value.trim() || undefined)
    row.plannedDueDate = iso
    $q.notify({ type: 'positive', message: '완료목표일이 변경되었습니다.', timeout: 1500 })
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '변경에 실패했습니다.' })
  }
}

function openAssigneePopup(row: SRListItem) {
  assigneeInput.value   = row.assigneeId ?? null
  filteredPmUsers.value = pmUsers.value
}

function filterUsers(val: string, update: (fn: () => void) => void) {
  update(() => {
    const q = val.toLowerCase()
    filteredPmUsers.value = q
      ? pmUsers.value.filter(u =>
          u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
        )
      : pmUsers.value
  })
}

function saveAssignee(row: SRListItem) {
  const user = pmUsers.value.find(u => u.id === assigneeInput.value)
  if (!user) return
  void inlinePatch(row, { assignee_id: user.id, assignee_name: user.name })
}

// ── 상태 변경 ────────────────────────────────────────────────────────────

function requestStatusChange(row: SRListItem, newStatus: string) {
  if (row.status === newStatus) return
  const ns = newStatus as SRStatus
  if (STATUS_NEEDS_REASON.has(newStatus)) {
    statusDialog.value = { open: true, row, newStatus: ns, title: '변경 사유 입력', inputLabel: '사유 *', input: '', fieldKey: 'reason' }
  } else if (STATUS_NEEDS_RESULT.has(newStatus)) {
    statusDialog.value = { open: true, row, newStatus: ns, title: '처리 결과 입력', inputLabel: '처리 결과 *', input: '', fieldKey: 'process_result' }
  } else {
    void doStatusChange(row, ns, {})
  }
}

function confirmStatusChange() {
  const { row, newStatus, input, fieldKey } = statusDialog.value
  if (!input.trim()) return
  statusDialog.value.open = false
  const extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>> =
    fieldKey === 'reason' ? { reason: input.trim() } : { process_result: input.trim() }
  if (row) void doStatusChange(row, newStatus, extra)
  else     void doBulkStatusChange(newStatus, extra)
}

async function doStatusChange(
  row: SRListItem,
  newStatus: SRStatus,
  extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>>,
) {
  changingStatusId.value = row.id
  try {
    await changeSRStatus(row.id, { status: newStatus, ...extra })
    row.status = newStatus
    $q.notify({ type: 'positive', message: `"${statusLabel(newStatus)}"로 변경되었습니다.` })
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '상태 변경에 실패했습니다.' })
  } finally {
    changingStatusId.value = null
  }
}

// ── 일괄 상태 변경 ────────────────────────────────────────────────────────

function bulkStatusChange(newStatus: string) {
  if (!selected.value.length) return
  const ns = newStatus as SRStatus
  if (STATUS_NEEDS_REASON.has(newStatus) || STATUS_NEEDS_RESULT.has(newStatus)) {
    statusDialog.value = {
      open: true, row: null, newStatus: ns,
      title: STATUS_NEEDS_RESULT.has(newStatus) ? '처리 결과 입력' : '변경 사유 입력',
      inputLabel: STATUS_NEEDS_RESULT.has(newStatus) ? '처리 결과 *' : '사유 *',
      input: '',
      fieldKey: STATUS_NEEDS_RESULT.has(newStatus) ? 'process_result' : 'reason',
    }
  } else {
    void doBulkStatusChange(ns, {})
  }
}

async function doBulkStatusChange(
  newStatus: SRStatus,
  extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>>,
) {
  bulkChanging.value = true
  let successCount = 0
  for (const row of selected.value) {
    try {
      await changeSRStatus(row.id, { status: newStatus, ...extra })
      row.status = newStatus
      successCount++
    } catch { /* 개별 실패 무시 */ }
  }
  bulkChanging.value = false
  $q.notify({ type: 'positive', message: `${successCount}개가 "${statusLabel(newStatus)}"로 변경되었습니다.` })
  selected.value = []
}

// ── 엑셀 다운로드 ────────────────────────────────────────────────────────

async function downloadExcel() {
  exporting.value = true
  try {
    const params = buildSrApiParams(srSearch.filter.value, srSearch.activeTab.value)
    const res = await api.get('/admin/schedule/service-requests/export', { params, responseType: 'blob' })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'SR_목록.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    $q.notify({ type: 'negative', message: 'Excel 다운로드에 실패했습니다.' })
  } finally {
    exporting.value = false
  }
}

// ── SR 기본 프로젝트 ──────────────────────────────────────────────────────

async function loadProjects() {
  projectsLoading.value = true
  try {
    allProjects.value = await listProjects()
    const current = allProjects.value.find(p => p.isSrDefault)
    selectedSrProject.value = current?.id ?? null
  } catch { /* 무시 */ } finally {
    projectsLoading.value = false
  }
}

async function saveSrDefaultProject() {
  if (!selectedSrProject.value) return
  savingProject.value = true
  try {
    await setSrDefaultProject(selectedSrProject.value)
    await loadProjects()
    $q.notify({ type: 'positive', message: 'SR 기본 프로젝트가 설정되었습니다.' })
    srProjectDialog.value = false
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '설정 실패' })
  } finally {
    savingProject.value = false
  }
}

// ── 생명주기 ──────────────────────────────────────────────────────────────

onMounted(() => {
  initFromUrl()
  void fetchList()
  void listPmUsers().then(users => {
    pmUsers.value         = users
    filteredPmUsers.value = users
  })
})

watch(srProjectDialog, (open) => { if (open) void loadProjects() })
</script>

<style scoped>
.stat-card { transition: transform 0.15s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-card--clickable:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }

.bulk-bar {
  background: #e8f0fe;
  border-radius: 4px;
  min-height: 36px;
}

.editable-cell {
  cursor: pointer;
  transition: background-color 0.12s;
}
.editable-cell:hover {
  background-color: rgba(25, 118, 210, 0.07) !important;
}
.editable-cell .edit-hint {
  opacity: 0;
  transition: opacity 0.12s;
  flex-shrink: 0;
}
.editable-cell:hover .edit-hint {
  opacity: 1;
}
</style>
