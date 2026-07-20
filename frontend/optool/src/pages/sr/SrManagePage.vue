<template>
  <q-page padding>
    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="text-h5 text-weight-bold">SR 관리</div>
        <div class="text-caption text-grey-6">접수된 SR을 검토 · 배정 · 처리합니다.</div>
      </div>
      <HelpButton feature="sr-manage" guide-path="/pm/sr/guide" class="q-mr-xs" />
      <q-btn v-if="isAdminUser" outline color="indigo-7" icon="settings" label="SR 기본 프로젝트" @click="srProjectDialog = true" class="q-mr-sm" />
      <q-btn outline color="green-7" icon="download" label="Excel" @click="downloadExcel" :loading="exporting" />
    </div>

    <!-- 통계 카드 (클릭 시 탭 이동) -->
    <div v-if="stats" class="row q-col-gutter-sm q-mb-lg">
      <div v-for="c in statCards" :key="c.label" class="col-6 col-sm-3 col-md-auto" style="min-width:110px">
        <q-card flat bordered class="text-center q-pa-sm stat-card"
          :class="c.tab ? 'cursor-pointer stat-card--clickable' : ''"
          @click="c.tab && switchTab(c.tab)">
          <div class="text-h4 text-weight-bold" :class="`text-${c.color}`">{{ c.value }}</div>
          <div class="text-caption text-grey-6">{{ c.label }}</div>
          <q-tooltip v-if="c.tab">{{ c.label }} 탭으로 이동</q-tooltip>
        </q-card>
      </div>
    </div>

    <!-- 상태 탭 -->
    <q-tabs v-model="activeTab" dense align="left" active-color="primary"
      indicator-color="primary" class="q-mb-sm bg-grey-1 rounded-borders">
      <q-tab name="all"         label="전체" />
      <q-tab name="SUBMITTED"   label="접수" />
      <q-tab name="REVIEWING"   label="검토 중" />
      <q-tab name="IN_PROGRESS" label="처리 중" />
      <q-tab name="COMPLETED"   label="처리 완료" />
      <q-tab name="CONFIRMING"  label="확인 중" />
      <q-tab name="CLOSED"      label="최종 완료" />
      <q-tab name="ON_HOLD"     label="보류" />
      <q-tab name="REJECTED"    label="반려" />
      <q-tab name="delayed"     label="⏰ 지연" />
    </q-tabs>

    <!-- 필터 / 검색 -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section class="q-pa-sm">

        <!-- 행 1: 검색 + 빠른 토글 + 상세 필터 버튼 + 액션 -->
        <div class="row items-center q-gutter-xs">
          <q-input
            v-model="search"
            placeholder="제목 · SR번호 · 요청자 검색"
            outlined dense clearable
            class="col"
            bg-color="white"
            @keyup.enter="applyFilter"
          >
            <template #prepend><q-icon name="search" color="grey-5" size="18px" /></template>
          </q-input>

          <q-chip
            clickable dense
            :color="filter.myAssigned ? 'primary' : 'grey-3'"
            :text-color="filter.myAssigned ? 'white' : 'grey-7'"
            icon="person_pin"
            class="q-mx-none"
            @click="filter.myAssigned = !filter.myAssigned; applyFilter()"
          >내 배정</q-chip>

          <q-chip
            clickable dense
            :color="filter.isUrgent ? 'negative' : 'grey-3'"
            :text-color="filter.isUrgent ? 'white' : 'grey-7'"
            icon="priority_high"
            class="q-mx-none"
            @click="filter.isUrgent = !filter.isUrgent; applyFilter()"
          >긴급</q-chip>

          <q-btn
            flat dense size="sm" icon="tune" label="상세 필터" no-caps
            :class="filterExpanded ? 'text-indigo-7 bg-indigo-1' : 'text-grey-7'"
            class="q-px-sm"
            @click="filterExpanded = !filterExpanded"
          >
            <q-badge v-if="advancedFilterCount" floating color="indigo-7" :label="advancedFilterCount" />
          </q-btn>

          <div style="width:1px; height:24px; background:rgba(0,0,0,0.1); margin:0 2px; flex-shrink:0" />

          <q-btn-dropdown flat dense size="sm" icon="bookmark_border" color="grey-6" no-icon-animation>
            <template #label><span class="text-caption">프리셋</span></template>
            <q-list dense style="min-width:180px">
              <q-item v-if="!presets.length" dense>
                <q-item-section class="text-grey-5 text-caption q-py-xs">저장된 프리셋 없음</q-item-section>
              </q-item>
              <q-item v-for="(p, i) in presets" :key="i" clickable v-close-popup @click="loadPreset(p)">
                <q-item-section>{{ p.name }}</q-item-section>
                <q-item-section side>
                  <q-btn flat round dense size="xs" icon="close" color="grey-5" @click.stop="removePreset(i)" />
                </q-item-section>
              </q-item>
              <q-separator v-if="presets.length" />
              <q-item clickable v-close-popup @click="savePreset">
                <q-item-section avatar><q-icon name="add" size="14px" /></q-item-section>
                <q-item-section>현재 필터 저장</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>

          <q-btn flat round dense icon="refresh" color="grey-5" size="sm" @click="resetFilter">
            <q-tooltip>필터 초기화</q-tooltip>
          </q-btn>

          <q-btn unelevated color="primary" icon="search" label="조회" size="sm"
            class="q-px-sm" @click="applyFilter" :loading="loading" />
        </div>

        <!-- 활성 상세 필터 칩 표시 (개별 제거 가능) -->
        <q-slide-transition>
          <div v-if="activeFilterChips.length" class="row q-gutter-xs q-mt-xs items-center">
            <q-chip
              v-for="chip in activeFilterChips" :key="chip.key"
              dense removable
              color="indigo-1"
              text-color="indigo-9"
              size="sm"
              @remove="clearFilter(chip.key)"
            >
              <span class="text-weight-medium text-caption">{{ chip.label }}</span>
              <span class="text-caption q-ml-xs" style="opacity:0.65">{{ chip.value }}</span>
            </q-chip>
            <q-btn flat dense size="xs" color="grey-5" label="전체 초기화" class="text-caption" @click="resetFilter" />
          </div>
        </q-slide-transition>

        <!-- 상세 필터 패널 (접힘/펼침) -->
        <q-slide-transition>
          <div v-show="filterExpanded">
            <q-separator class="q-mt-sm q-mb-sm" />

            <!-- 텍스트/선택 필터 -->
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-sm-6 col-md">
                <q-input v-model="filter.requesterDepartment" label="요청 부서" outlined dense clearable bg-color="white">
                  <template #prepend><q-icon name="business" size="16px" color="grey-5" /></template>
                </q-input>
              </div>
              <div class="col-12 col-sm-6 col-md">
                <q-input v-model="filter.requesterName" label="요청자" outlined dense clearable bg-color="white">
                  <template #prepend><q-icon name="person" size="16px" color="grey-5" /></template>
                </q-input>
              </div>
              <div class="col-12 col-sm-6 col-md">
                <q-select v-model="filter.requestType" label="요청 유형" outlined dense clearable bg-color="white"
                  :options="requestTypeOptions" emit-value map-options>
                  <template #prepend><q-icon name="category" size="16px" color="grey-5" /></template>
                </q-select>
              </div>
              <div class="col-12 col-sm-6 col-md">
                <q-input v-model="filter.relatedSystem" label="관련 시스템" outlined dense clearable bg-color="white">
                  <template #prepend><q-icon name="computer" size="16px" color="grey-5" /></template>
                </q-input>
              </div>
              <div class="col-12 col-sm-6 col-md">
                <q-select v-model="filter.priority" label="중요도" outlined dense clearable bg-color="white"
                  :options="priorityOptions" emit-value map-options>
                  <template #prepend><q-icon name="flag" size="16px" color="grey-5" /></template>
                </q-select>
              </div>
            </div>

            <!-- 날짜 범위 -->
            <div class="row q-col-gutter-md items-end">
              <div class="col-auto">
                <div class="text-caption text-grey-6 q-mb-xs">접수일</div>
                <div class="row items-center no-wrap q-gutter-xs">
                  <q-input v-model="filter.createdFrom" type="date" outlined dense clearable
                    bg-color="white" style="width:148px" />
                  <span class="text-grey-5 text-body2">~</span>
                  <q-input v-model="filter.createdTo" type="date" outlined dense clearable
                    bg-color="white" style="width:148px" />
                </div>
              </div>
              <div class="col-auto">
                <div class="text-caption text-grey-6 q-mb-xs">희망완료일</div>
                <div class="row items-center no-wrap q-gutter-xs">
                  <q-input v-model="filter.dueDateFrom" type="date" outlined dense clearable
                    bg-color="white" style="width:148px" />
                  <span class="text-grey-5 text-body2">~</span>
                  <q-input v-model="filter.dueDateTo" type="date" outlined dense clearable
                    bg-color="white" style="width:148px" />
                </div>
              </div>
            </div>
          </div>
        </q-slide-transition>

      </q-card-section>
    </q-card>

    <!-- 테이블 -->
    <q-card flat bordered>
      <q-table
        :rows="filteredRows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        flat
        :rows-per-page-options="[20, 50, 100]"
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
            <!-- 완료목표일 (지연 판정 기준) — 인라인 편집 -->
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
            <div class="text-subtitle1">조회된 SR이 없습니다.</div>
          </div>
        </template>
      </q-table>
    </q-card>

    <!-- 상태 변경 사유 다이얼로그 -->
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
            outlined
            autogrow
            :rows="3"
            autofocus
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

    <!-- SR 기본 프로젝트 설정 다이얼로그 -->
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
            emit-value
            map-options
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
  REQUEST_TYPE_OPTIONS, SR_PRIORITY_OPTIONS,
  type SRListItem, type SRStats, type SRStatus, type SRStatusChange,
} from 'src/services/sr'
import { listPmUsers, type PmUser } from 'src/services/pm/users'
import { listProjects, setSrDefaultProject, type Project } from 'src/services/pm/project'
import { useAuthStore } from 'src/stores/auth'
import { fmtDateKst } from 'src/utils/time/kst'

// ── 상수 ────────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  'SUBMITTED', 'REVIEWING', 'PENDING_INFO', 'APPROVED', 'ASSIGNED',
  'IN_PROGRESS', 'COMPLETED', 'CONFIRMING', 'CLOSED', 'ON_HOLD', 'REJECTED', 'CANCELLED',
].map(s => ({ value: s, label: (SR_STATUS_LABEL as Record<string, string>)[s] ?? s }))

const PRESET_KEY = 'sr-manage-presets'

type FilterState = {
  requestType:         string | null
  requesterDepartment: string
  requesterName:       string
  relatedSystem:       string
  priority:            string | null
  isUrgent:            boolean
  myAssigned:          boolean
  createdFrom:         string
  createdTo:           string
  dueDateFrom:         string
  dueDateTo:           string
}

type FilterPreset = { name: string; tab: string; filter: FilterState }

// ── refs / store ─────────────────────────────────────────────────────────

const $q        = useQuasar()
const route     = useRoute()
const router    = useRouter()
const authStore = useAuthStore()
const loading   = ref(false)
const exporting = ref(false)
const isAdminUser = computed(() => authStore.me?.isAdmin || false)

// SR 기본 프로젝트 설정
const srProjectDialog   = ref(false)
const projectsLoading   = ref(false)
const savingProject     = ref(false)
const allProjects       = ref<Project[]>([])
const selectedSrProject = ref<string | null>(null)

const projectOptions = computed(() =>
  allProjects.value.map(p => ({ label: `[${p.key}] ${p.name}`, value: p.id }))
)
const currentSrDefault = computed(() => {
  const p = allProjects.value.find(p => p.isSrDefault)
  return p ? `[${p.key}] ${p.name}` : null
})

const rows     = ref<SRListItem[]>([])
const stats    = ref<SRStats | null>(null)
const selected = ref<SRListItem[]>([])
const search   = ref('')
const activeTab = ref('all')

const pagination = ref({
  page:        1,
  rowsPerPage: 20,
  sortBy:      'created_at',
  descending:  true,
  rowsNumber:  0,
})

const filter = ref<FilterState>({
  requestType:         null,
  requesterDepartment: '',
  requesterName:       '',
  relatedSystem:       '',
  priority:            null,
  isUrgent:            false,
  myAssigned:          false,
  createdFrom:         '',
  createdTo:           '',
  dueDateFrom:         '',
  dueDateTo:           '',
})

// 인라인·일괄 상태 변경
const changingStatusId = ref<string | null>(null)
const bulkChanging     = ref(false)

// 사유/처리결과 입력이 필요한 상태 변경 다이얼로그
const STATUS_NEEDS_REASON      = new Set(['REJECTED', 'ON_HOLD', 'CANCELLED'])
const STATUS_NEEDS_RESULT      = new Set(['COMPLETED'])
const statusDialog = ref({
  open:       false,
  row:        null as SRListItem | null,
  newStatus:  '' as SRStatus,
  title:      '',
  inputLabel: '',
  input:      '',
  fieldKey:   '' as 'reason' | 'process_result',
})

// 인라인 편집 - PM 유저 / 날짜 / 담당자 선택 상태
const pmUsers           = ref<PmUser[]>([])
const filteredPmUsers   = ref<PmUser[]>([])
const dateInput         = ref('')
const assigneeInput     = ref<string | null>(null)
const plannedDateInput  = ref('')
const plannedDateReason = ref('')

// 프리셋
const presets = ref<FilterPreset[]>(JSON.parse(localStorage.getItem(PRESET_KEY) || '[]'))

// 상세 필터 패널 열림 상태
const filterExpanded = ref(false)

// 활성 상세 필터 칩 (적용된 필터를 태그로 표시)
const activeFilterChips = computed(() => {
  const chips: { key: string; label: string; value: string }[] = []
  const f = filter.value
  if (f.requesterDepartment) chips.push({ key: 'requesterDepartment', label: '부서', value: f.requesterDepartment })
  if (f.requesterName)       chips.push({ key: 'requesterName', label: '요청자', value: f.requesterName })
  if (f.requestType)         chips.push({ key: 'requestType', label: '유형', value: requestTypeLabel(f.requestType) })
  if (f.relatedSystem)       chips.push({ key: 'relatedSystem', label: '시스템', value: f.relatedSystem })
  if (f.priority)            chips.push({ key: 'priority', label: '중요도', value: priorityLabel(f.priority) })
  if (f.createdFrom || f.createdTo)
    chips.push({ key: 'createdDate', label: '접수일', value: `${f.createdFrom || '-'} ~ ${f.createdTo || '-'}` })
  if (f.dueDateFrom || f.dueDateTo)
    chips.push({ key: 'dueDate', label: '희망완료일', value: `${f.dueDateFrom || '-'} ~ ${f.dueDateTo || '-'}` })
  return chips
})

const advancedFilterCount = computed(() => activeFilterChips.value.length)

function clearFilter(key: string) {
  const f = filter.value
  if (key === 'requesterDepartment') f.requesterDepartment = ''
  else if (key === 'requesterName')  f.requesterName = ''
  else if (key === 'requestType')    f.requestType = null
  else if (key === 'relatedSystem')  f.relatedSystem = ''
  else if (key === 'priority')       f.priority = null
  else if (key === 'createdDate')    { f.createdFrom = ''; f.createdTo = '' }
  else if (key === 'dueDate')        { f.dueDateFrom = ''; f.dueDateTo = '' }
  applyFilter()
}

const requestTypeOptions = REQUEST_TYPE_OPTIONS
const priorityOptions    = SR_PRIORITY_OPTIONS

// ── 테이블 컬럼 ──────────────────────────────────────────────────────────

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'select',               label: '',          field: 'id',                   align: 'center', style: 'width:40px' },
  { name: 'sr_no',                label: 'SR 번호',   field: 'sr_no',                align: 'left',   sortable: true, style: 'width:120px' },
  { name: 'title',                label: '요청 제목', field: 'title',                align: 'left' },
  { name: 'requester_department', label: '부서',      field: 'requester_department', align: 'left',   sortable: true, style: 'width:90px' },
  { name: 'requester_name',       label: '요청자',    field: 'requester_name',       align: 'left',   sortable: true, style: 'width:80px' },
  { name: 'priority',             label: '중요도',    field: 'priority',             align: 'center', sortable: true, style: 'width:70px' },
  { name: 'status',               label: '상태',      field: 'status',               align: 'center', sortable: true, style: 'width:130px' },
  { name: 'assignee_name',        label: '담당자',    field: 'assignee_name',        align: 'left',   style: 'width:80px' },
  { name: 'desired_due_date',     label: '희망완료일', field: 'desired_due_date',    align: 'center', sortable: true, style: 'width:95px' },
  { name: 'planned_due_date',     label: '완료목표일', field: 'planned_due_date',    align: 'center', style: 'width:95px' },
  { name: 'created_at',           label: '접수일',    field: 'created_at',           align: 'center', sortable: true, style: 'width:90px' },
  { name: 'actions',              label: '',          field: 'id',                   align: 'center', style: 'width:50px' },
]

// ── computed ─────────────────────────────────────────────────────────────

const filteredRows = computed(() => {
  if (!search.value.trim()) return rows.value
  const q = search.value.toLowerCase()
  return rows.value.filter(r =>
    r.title.toLowerCase().includes(q) ||
    r.srNo.toLowerCase().includes(q) ||
    r.requesterName.toLowerCase().includes(q)
  )
})

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '전체',        value: stats.value.total,                   color: 'primary',  tab: 'all'         },
    { label: '진행 중',     value: stats.value.inProgress,              color: 'blue-8',   tab: 'IN_PROGRESS' },
    { label: '완료',        value: stats.value.completed,               color: 'positive', tab: 'COMPLETED'   },
    { label: '지연',        value: stats.value.delayed,                 color: 'negative', tab: 'delayed'     },
    { label: '보류',        value: stats.value.onHold,                  color: 'brown',    tab: 'ON_HOLD'     },
    { label: '반려',        value: stats.value.rejected,                color: 'red-8',    tab: 'REJECTED'    },
    { label: '긴급',        value: stats.value.urgentCount,             color: 'red',      tab: null          },
    { label: '평균처리(일)', value: stats.value.avgProcessingDays ?? '-', color: 'grey-7', tab: null          },
  ]
})

// ── 헬퍼 함수 ────────────────────────────────────────────────────────────

function isSelected(row: SRListItem) { return selected.value.some(r => r.id === row.id) }
function toggleSelect(row: SRListItem) {
  const idx = selected.value.findIndex(r => r.id === row.id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(row)
}

function statusLabel(s: string)      { return (SR_STATUS_LABEL    as Record<string,string>)[s] ?? s }
function statusColor(s: string)      { return (SR_STATUS_COLOR    as Record<string,string>)[s] ?? 'grey' }
function priorityLabel(s: string)    { return (SR_PRIORITY_LABEL  as Record<string,string>)[s] ?? s }
function priorityColor(s: string)    { return (SR_PRIORITY_COLOR  as Record<string,string>)[s] ?? 'grey' }
function requestTypeLabel(s: string) { return (REQUEST_TYPE_LABEL as Record<string,string>)[s] ?? s }
function fmtDate(d: string | null)   { return fmtDateKst(d) }
function formatTitle(row: SRListItem) {
  const type = requestTypeLabel(row.requestType)
  const sys  = row.relatedSystem ? `(${row.relatedSystem})` : ''
  return `[${type}]${sys} ${row.title}`
}

// ── 탭 전환 ──────────────────────────────────────────────────────────────

function switchTab(tab: string) {
  if (activeTab.value === tab) return
  activeTab.value = tab
}

// ── 상세 페이지 이동 (목록 순서 저장) ────────────────────────────────────

function navigateToDetail(row: SRListItem) {
  sessionStorage.setItem('sr-list-ids', JSON.stringify(filteredRows.value.map(r => r.id)))
  void router.push(`/pm/sr/${row.id}`)
}

// ── API 조회 ─────────────────────────────────────────────────────────────

async function fetchList() {
  loading.value = true
  try {
    const skip = (pagination.value.page - 1) * pagination.value.rowsPerPage
    const params: Record<string, string | number | boolean> = {
      skip,
      limit:      pagination.value.rowsPerPage,
      sort_by:    pagination.value.sortBy || 'created_at',
      descending: pagination.value.descending,
    }
    // 탭 → API status 파라미터 (서버사이드 필터)
    if (activeTab.value === 'delayed') {
      params.is_delayed = true
    } else if (activeTab.value !== 'all') {
      params.status = activeTab.value
    }
    if (filter.value.requestType)         params.request_type         = filter.value.requestType
    if (filter.value.requesterDepartment) params.requester_department = filter.value.requesterDepartment
    if (filter.value.requesterName)       params.requester_name       = filter.value.requesterName
    if (filter.value.relatedSystem)       params.related_system       = filter.value.relatedSystem
    if (filter.value.priority)            params.priority             = filter.value.priority
    if (filter.value.isUrgent)            params.is_urgent            = true
    if (filter.value.myAssigned)          params.my_assigned          = true
    if (filter.value.createdFrom)         params.created_from         = filter.value.createdFrom
    if (filter.value.createdTo)           params.created_to           = filter.value.createdTo
    if (filter.value.dueDateFrom)         params.desired_due_from     = filter.value.dueDateFrom
    if (filter.value.dueDateTo)           params.desired_due_to       = filter.value.dueDateTo

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

function applyFilter() {
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

function resetFilter() {
  filter.value = {
    requestType: null, requesterDepartment: '', requesterName: '',
    relatedSystem: '', priority: null, isUrgent: false, myAssigned: false,
    createdFrom: '', createdTo: '', dueDateFrom: '', dueDateTo: '',
  }
  search.value = ''
  pagination.value.page = 1
  void fetchList()
}

// ── 서버사이드 페이지네이션 핸들러 ──────────────────────────────────────

function onTableRequest(props: { pagination: { page: number; rowsPerPage: number; sortBy: string; descending: boolean } }) {
  pagination.value.page        = props.pagination.page
  pagination.value.rowsPerPage = props.pagination.rowsPerPage
  pagination.value.sortBy      = props.pagination.sortBy
  pagination.value.descending  = props.pagination.descending
  void fetchList()
  syncToUrl()
}

// ── 인라인 필드 편집 (priority / desired_due_date / assignee) ────────────

async function inlinePatch(row: SRListItem, patch: { priority?: string; desired_due_date?: string | null; assignee_id?: string | null; assignee_name?: string | null }) {
  try {
    await patchSRInline(row.id, patch)
    if (patch.priority !== undefined)         row.priority        = patch.priority as SRListItem['priority']
    if (patch.desired_due_date !== undefined) row.desiredDueDate  = patch.desired_due_date
    if (patch.assignee_id     !== undefined)  row.assigneeId      = patch.assignee_id
    if (patch.assignee_name   !== undefined)  row.assigneeName    = patch.assignee_name
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
  assigneeInput.value = row.assigneeId ?? null
  filteredPmUsers.value = pmUsers.value
}

function filterUsers(val: string, update: (fn: () => void) => void) {
  update(() => {
    const q = val.toLowerCase()
    filteredPmUsers.value = q
      ? pmUsers.value.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
      : pmUsers.value
  })
}

function saveAssignee(row: SRListItem) {
  const user = pmUsers.value.find(u => u.id === assigneeInput.value)
  if (!user) return
  void inlinePatch(row, { assignee_id: user.id, assignee_name: user.name })
}

// ── 인라인 상태 변경 ─────────────────────────────────────────────────────

function requestStatusChange(row: SRListItem, newStatus: string) {
  if (row.status === newStatus) return
  const ns = newStatus as SRStatus
  if (STATUS_NEEDS_REASON.has(newStatus)) {
    statusDialog.value = {
      open: true, row, newStatus: ns,
      title: '변경 사유 입력',
      inputLabel: '사유 *',
      input: '',
      fieldKey: 'reason',
    }
  } else if (STATUS_NEEDS_RESULT.has(newStatus)) {
    statusDialog.value = {
      open: true, row, newStatus: ns,
      title: '처리 결과 입력',
      inputLabel: '처리 결과 *',
      input: '',
      fieldKey: 'process_result',
    }
  } else {
    void doStatusChange(row, ns, {})
  }
}

function confirmStatusChange() {
  const { row, newStatus, input, fieldKey } = statusDialog.value
  if (!input.trim()) return
  statusDialog.value.open = false
  const extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>> = fieldKey === 'reason'
    ? { reason: input.trim() }
    : { process_result: input.trim() }
  if (row) {
    void doStatusChange(row, newStatus, extra)
  } else {
    void doBulkStatusChange(newStatus, extra)
  }
}

async function doStatusChange(row: SRListItem, newStatus: SRStatus, extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>>) {
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

// ── 일괄 상태 변경 ───────────────────────────────────────────────────────

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

async function doBulkStatusChange(newStatus: SRStatus, extra: Partial<Pick<SRStatusChange, 'reason' | 'process_result'>>) {
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

// ── 필터 프리셋 ──────────────────────────────────────────────────────────

function savePreset() {
  $q.dialog({
    title: '프리셋 저장',
    prompt: { model: '', label: '프리셋 이름', type: 'text' },
    cancel: true,
  }).onOk((name: string) => {
    if (!name.trim()) return
    const newPresets = [...presets.value, { name: name.trim(), tab: activeTab.value, filter: { ...filter.value } }]
    presets.value = newPresets
    localStorage.setItem(PRESET_KEY, JSON.stringify(newPresets))
    $q.notify({ type: 'positive', message: '프리셋이 저장되었습니다.' })
  })
}

function loadPreset(p: FilterPreset) {
  activeTab.value       = p.tab
  filter.value          = { ...p.filter }
  pagination.value.page = 1
  void fetchList()
}

function removePreset(i: number) {
  const newPresets = presets.value.filter((_, idx) => idx !== i)
  presets.value = newPresets
  localStorage.setItem(PRESET_KEY, JSON.stringify(newPresets))
}

// ── 엑셀 다운로드 ────────────────────────────────────────────────────────

async function downloadExcel() {
  exporting.value = true
  try {
    const params: Record<string, string | boolean> = {}
    if (activeTab.value === 'delayed') {
      params.is_delayed = true
    } else if (activeTab.value !== 'all') {
      params.status = activeTab.value
    }
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

// ── URL 상태 동기화 ───────────────────────────────────────────────────────

function syncToUrl() {
  const q: Record<string, string> = {}
  if (activeTab.value !== 'all')              q.tab      = activeTab.value
  if (filter.value.requesterDepartment)        q.dept     = filter.value.requesterDepartment
  if (filter.value.requesterName)              q.name     = filter.value.requesterName
  if (filter.value.requestType)                q.type     = filter.value.requestType
  if (filter.value.relatedSystem)              q.sys      = filter.value.relatedSystem
  if (filter.value.priority)                   q.priority = filter.value.priority
  if (filter.value.isUrgent)                   q.urgent   = '1'
  if (filter.value.myAssigned)                 q.mine     = '1'
  if (filter.value.createdFrom)                q.cfrom    = filter.value.createdFrom
  if (filter.value.createdTo)                  q.cto      = filter.value.createdTo
  if (filter.value.dueDateFrom)                q.dfrom    = filter.value.dueDateFrom
  if (filter.value.dueDateTo)                  q.dto      = filter.value.dueDateTo
  if (search.value)                            q.q        = search.value
  if (pagination.value.page > 1)               q.page     = String(pagination.value.page)
  if (pagination.value.rowsPerPage !== 20)     q.rows     = String(pagination.value.rowsPerPage)
  void router.replace({ query: q })
}

function initFromUrl() {
  const q = route.query
  if (q.tab)      activeTab.value                      = String(q.tab)
  if (q.dept)     filter.value.requesterDepartment     = String(q.dept)
  if (q.name)     filter.value.requesterName           = String(q.name)
  if (q.type)     filter.value.requestType             = String(q.type)
  if (q.sys)      filter.value.relatedSystem           = String(q.sys)
  if (q.priority) filter.value.priority                = String(q.priority)
  if (q.urgent)   filter.value.isUrgent                = q.urgent === '1'
  if (q.mine)     filter.value.myAssigned              = q.mine === '1'
  if (q.cfrom)    filter.value.createdFrom             = String(q.cfrom)
  if (q.cto)      filter.value.createdTo               = String(q.cto)
  if (q.dfrom)    filter.value.dueDateFrom             = String(q.dfrom)
  if (q.dto)      filter.value.dueDateTo               = String(q.dto)
  if (q.q)        search.value                         = String(q.q)
  if (q.page)     pagination.value.page                = Number(q.page)
  if (q.rows)     pagination.value.rowsPerPage         = Number(q.rows)
  // 고급 필터가 복원되면 패널 자동 열기
  const f = filter.value
  if (f.requesterDepartment || f.requesterName || f.requestType || f.relatedSystem ||
      f.priority || f.createdFrom || f.createdTo || f.dueDateFrom || f.dueDateTo) {
    filterExpanded.value = true
  }
}

// ── 생명주기 / 감시 ───────────────────────────────────────────────────────

onMounted(() => {
  initFromUrl()
  void fetchList()
  void listPmUsers().then(users => { pmUsers.value = users; filteredPmUsers.value = users })
})

watch(activeTab, () => {
  selected.value = []
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
})
watch(filter,      syncToUrl, { deep: true })
watch(search,      syncToUrl)
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

/* 인라인 편집 가능 셀 */
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
