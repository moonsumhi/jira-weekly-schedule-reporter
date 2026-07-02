<template>
  <q-page padding>
    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <div class="col">
        <div class="text-h5 text-weight-bold">SR 관리</div>
        <div class="text-caption text-grey-6">접수된 SR을 검토 · 배정 · 처리합니다.</div>
      </div>
      <q-btn v-if="isAdminUser" outline color="indigo-7" icon="settings" label="SR 기본 프로젝트" @click="srProjectDialog = true" class="q-mr-sm" />
      <q-btn outline color="green-7" icon="download" label="Excel" @click="downloadExcel" :loading="exporting" />
    </div>

    <!-- 통계 카드 -->
    <div v-if="stats" class="row q-col-gutter-sm q-mb-lg">
      <div v-for="c in statCards" :key="c.label" class="col-6 col-sm-3 col-md-auto" style="min-width:110px">
        <q-card flat bordered class="text-center q-pa-sm stat-card">
          <div class="text-h4 text-weight-bold" :class="`text-${c.color}`">{{ c.value }}</div>
          <div class="text-caption text-grey-6">{{ c.label }}</div>
        </q-card>
      </div>
    </div>

    <!-- 상태 탭 -->
    <q-tabs v-model="activeTab" dense align="left" active-color="primary"
      indicator-color="primary" class="q-mb-sm bg-grey-1 rounded-borders">
      <q-tab name="all" label="전체" />
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

    <!-- 필터 -->
    <q-card flat bordered class="q-mb-md filter-card">
      <q-card-section class="q-py-sm q-px-md">
        <div class="row items-center q-gutter-xs q-mb-sm">
          <q-icon name="filter_list" size="16px" color="grey-6" />
          <span class="text-caption text-weight-medium text-grey-7">상세 필터</span>
          <q-space />
          <q-btn flat dense round icon="refresh" size="sm" color="grey-6" @click="resetFilter">
            <q-tooltip>초기화</q-tooltip>
          </q-btn>
        </div>
        <div class="row q-col-gutter-sm items-center">
          <div class="col-12 col-sm-6 col-md-3 col-lg-2">
            <q-input v-model="filter.requesterDepartment" label="요청 부서" outlined dense clearable
              bg-color="white" class="filter-input">
              <template #prepend><q-icon name="business" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-3 col-lg-2">
            <q-input v-model="filter.requesterName" label="요청자" outlined dense clearable
              bg-color="white" class="filter-input">
              <template #prepend><q-icon name="person" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-3 col-lg-2">
            <q-select v-model="filter.requestType" label="요청 유형" outlined dense clearable
              bg-color="white" class="filter-input"
              :options="requestTypeOptions" emit-value map-options>
              <template #prepend><q-icon name="category" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-3 col-lg-2">
            <q-input v-model="filter.relatedSystem" label="관련 시스템" outlined dense clearable
              bg-color="white" class="filter-input">
              <template #prepend><q-icon name="computer" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-3 col-lg-2">
            <q-select v-model="filter.priority" label="중요도" outlined dense clearable
              bg-color="white" class="filter-input"
              :options="priorityOptions" emit-value map-options>
              <template #prepend><q-icon name="flag" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm col-lg-auto">
            <div class="row items-center q-gutter-md q-pl-xs">
              <q-toggle v-model="filter.isUrgent" dense color="negative" size="sm">
                <template #default>
                  <span class="text-caption q-ml-xs" :class="filter.isUrgent ? 'text-negative text-weight-medium' : 'text-grey-7'">긴급</span>
                </template>
              </q-toggle>
              <q-toggle v-model="filter.myAssigned" dense color="primary" size="sm">
                <template #default>
                  <span class="text-caption q-ml-xs" :class="filter.myAssigned ? 'text-primary text-weight-medium' : 'text-grey-7'">내 배정</span>
                </template>
              </q-toggle>
              <q-btn color="primary" icon="search" label="조회" @click="fetchList" :loading="loading"
                unelevated size="sm" class="q-px-md" />
            </div>
          </div>
        </div>
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
        no-data-label="조회된 SR이 없습니다."
      >
        <template #top v-if="selected.length">
          <div class="text-caption text-grey-6 q-pa-sm">{{ selected.length }}개 선택됨</div>
        </template>

        <template #body="{ row }">
          <q-tr class="cursor-pointer" @click="$router.push(`/pm/sr/${row.id}`)">
            <q-td @click.stop>
              <q-checkbox :model-value="isSelected(row)" @update:model-value="toggleSelect(row)" dense />
            </q-td>
            <q-td>
              <span class="text-primary text-weight-medium">{{ row.srNo }}</span>
            </q-td>
            <q-td>
              <div class="row items-center q-gutter-xs no-wrap">
                <span>{{ row.title }}</span>
                <q-badge v-if="row.isUrgent"  color="red"      label="긴급" />
                <q-badge v-if="row.isDelayed" color="negative" label="지연" />
              </div>
            </q-td>
            <q-td>{{ row.requesterDepartment }}</q-td>
            <q-td>{{ row.requesterName }}</q-td>
            <q-td>{{ requestTypeLabel(row.requestType) }}</q-td>
            <q-td class="text-center">
              <q-badge :color="priorityColor(row.priority)" :label="priorityLabel(row.priority)" outline />
            </q-td>
            <q-td class="text-center">
              <q-chip :color="statusColor(row.status)" text-color="white" dense size="sm">
                {{ statusLabel(row.status) }}
              </q-chip>
            </q-td>
            <q-td>{{ row.assigneeName || '-' }}</q-td>
            <q-td class="text-center">
              <span :class="row.isDelayed ? 'text-negative text-weight-medium' : 'text-grey-7'">
                {{ fmtDate(row.desiredDueDate) }}
              </span>
            </q-td>
            <q-td class="text-center text-grey-6">{{ fmtDate(row.createdAt) }}</q-td>
            <q-td class="text-center" @click.stop>
              <q-btn flat dense round icon="open_in_new" size="sm" color="grey-7"
                @click="$router.push(`/pm/sr/${row.id}`)" />
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
import { useQuasar } from 'quasar'
import type { QTableProps } from 'quasar'
import { api } from 'src/boot/axios'
import {
  listAllSRs, getSRStats,
  SR_STATUS_LABEL, SR_STATUS_COLOR,
  REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL, SR_PRIORITY_COLOR,
  REQUEST_TYPE_OPTIONS, SR_PRIORITY_OPTIONS,
  type SRListItem, type SRStats,
} from 'src/services/sr'
import { listProjects, setSrDefaultProject, type Project } from 'src/services/pm/project'
import { useAuthStore } from 'src/stores/auth'

const $q        = useQuasar()
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
const rows      = ref<SRListItem[]>([])
const stats     = ref<SRStats | null>(null)
const selected  = ref<SRListItem[]>([])
const activeTab = ref('all')

const filter = ref({
  requestType:          null as string | null,
  requesterDepartment:  '',
  requesterName:        '',
  relatedSystem:        '',
  priority:             null as string | null,
  isUrgent:             false,
  myAssigned:           false,
})

const requestTypeOptions = REQUEST_TYPE_OPTIONS
const priorityOptions    = SR_PRIORITY_OPTIONS

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'select',              label: '',          field: 'id',                   align: 'center', style: 'width:40px' },
  { name: 'sr_no',              label: 'SR 번호',   field: 'sr_no',                align: 'left',   sortable: true, style: 'width:120px' },
  { name: 'title',              label: '요청 제목', field: 'title',                align: 'left' },
  { name: 'requester_department',label: '부서',     field: 'requester_department', align: 'left',   style: 'width:90px' },
  { name: 'requester_name',     label: '요청자',    field: 'requester_name',       align: 'left',   style: 'width:80px' },
  { name: 'request_type',       label: '유형',      field: 'request_type',         align: 'left',   style: 'width:110px' },
  { name: 'priority',           label: '중요도',    field: 'priority',             align: 'center', style: 'width:70px' },
  { name: 'status',             label: '상태',      field: 'status',               align: 'center', style: 'width:130px' },
  { name: 'assignee_name',      label: '담당자',    field: 'assignee_name',        align: 'left',   style: 'width:80px' },
  { name: 'desired_due_date',   label: '희망완료일',field: 'desired_due_date',     align: 'center', style: 'width:95px' },
  { name: 'created_at',         label: '접수일',    field: 'created_at',           align: 'center', style: 'width:90px' },
  { name: 'actions',            label: '',          field: 'id',                   align: 'center', style: 'width:50px' },
]

const filteredRows = computed(() => {
  if (activeTab.value === 'all')     return rows.value
  if (activeTab.value === 'delayed') return rows.value.filter(r => r.isDelayed)
  return rows.value.filter(r => r.status === activeTab.value)
})

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '전체',       value: stats.value.total,             color: 'primary' },
    { label: '진행 중',    value: stats.value.inProgress,        color: 'blue-8' },
    { label: '완료',       value: stats.value.completed,         color: 'positive' },
    { label: '지연',       value: stats.value.delayed,           color: 'negative' },
    { label: '보류',       value: stats.value.onHold,            color: 'brown' },
    { label: '반려',       value: stats.value.rejected,          color: 'red-8' },
    { label: '긴급',       value: stats.value.urgentCount,       color: 'red' },
    { label: '평균처리(일)',value: stats.value.avgProcessingDays ?? '-', color: 'grey-7' },
  ]
})

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
function fmtDate(d: string | null)   { return d ? d.substring(0, 10) : '-' }

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, string | number | boolean> = { limit: 200 }
    if (filter.value.requestType)         params.request_type = filter.value.requestType
    if (filter.value.requesterDepartment) params.requester_department = filter.value.requesterDepartment
    if (filter.value.requesterName)       params.requester_name = filter.value.requesterName
    if (filter.value.relatedSystem)       params.related_system = filter.value.relatedSystem
    if (filter.value.priority)            params.priority = filter.value.priority
    if (filter.value.isUrgent)            params.is_urgent = true
    if (filter.value.myAssigned)          params.my_assigned = true
    rows.value  = await listAllSRs(params)
    stats.value = await getSRStats()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || 'SR 목록을 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filter.value = { requestType: null, requesterDepartment: '', requesterName: '', relatedSystem: '', priority: null, isUrgent: false, myAssigned: false }
  void fetchList()
}

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

onMounted(fetchList)
watch(activeTab, () => { selected.value = [] })
watch(srProjectDialog, (open) => { if (open) void loadProjects() })
</script>

<style scoped>
.stat-card { transition: transform 0.15s; }
.stat-card:hover { transform: translateY(-2px); }

.filter-card { background: #fafafa; }
.filter-input :deep(.q-field__control) { background: white; }
</style>
