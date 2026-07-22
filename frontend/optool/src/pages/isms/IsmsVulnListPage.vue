<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6 col">취약점 목록</div>
      <q-btn flat dense icon="fa-solid fa-clock-rotate-left" label="가져오기 이력"
        @click="router.push('/isms-p/vulnerabilities/import-history')" />
      <q-btn flat dense icon="download" label="내보내기" :loading="exporting" @click="doExport" />
      <q-btn flat dense icon="upload" label="Excel 가져오기" @click="importDialog = true" />
      <q-btn
        color="primary" icon="add" label="새 취약점 추가"
        @click="router.push('/isms-p/vulnerabilities/new')"
      />
    </div>

    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-3">
            <q-input v-model="filter.search" dense outlined clearable debounce="400"
              label="검색 (점검코드/항목/호스트명/자산명/IP)"
              @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-select v-model="filter.assetType" dense outlined clearable emit-value map-options
              label="자산종류" :options="assetTypeOptions" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-select v-model="filter.riskLevel" dense outlined clearable
              label="위험도" :options="RISK_LEVEL_OPTIONS" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-select v-model="filter.controlStatus" dense outlined clearable
              label="통제여부" :options="CONTROL_STATUS_OPTIONS" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-select v-model="filter.actionStatus" dense outlined clearable
              label="조치여부" :options="ACTION_STATUS_OPTIONS" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-select v-model="filter.assignee" dense outlined clearable emit-value map-options
              label="담당자" :options="assigneeOptions" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-input v-model="filter.plannedDateFrom" dense outlined type="date" label="조치예정일 시작" @update:model-value="applyFilter" />
          </div>
          <div class="col-6 col-md-2">
            <q-input v-model="filter.plannedDateTo" dense outlined type="date" label="조치예정일 종료" @update:model-value="applyFilter" />
          </div>
          <div class="col-12 col-md-2 flex items-center">
            <q-btn flat dense label="필터 초기화" color="grey-7" @click="resetFilter" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered>
      <q-table
        :rows="rows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        flat
        :rows-per-page-options="[10, 25, 50, 100]"
        v-model:pagination="pagination"
        @request="onTableRequest"
        no-data-label="조회된 취약점이 없습니다."
      >
        <template #body="{ row }">
          <q-tr class="cursor-pointer" @click="router.push(`/isms-p/vulnerabilities/${row.id}`)">
            <q-td>{{ row.checkCode }}</q-td>
            <q-td class="ellipsis-cell" :title="row.checkItem">{{ row.checkItem }}</q-td>
            <q-td>{{ row.hostname || row.assetName }}</q-td>
            <q-td class="text-center">
              <q-badge :color="RISK_COLOR[row.riskLevel ?? ''] ?? 'grey'" :label="row.riskLevel || '-'" />
            </q-td>
            <q-td class="text-center">
              <q-badge :color="CONTROL_COLOR[row.controlStatus ?? ''] ?? 'grey'" :label="row.controlStatus || '-'" />
            </q-td>
            <q-td>{{ row.assignee || '-' }}</q-td>
            <q-td class="text-center">{{ row.actionStatus || '미조치' }}</q-td>
            <q-td class="text-center">{{ row.plannedDate || '-' }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card>

    <!-- Excel 가져오기 다이얼로그 -->
    <q-dialog v-model="importDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">Excel 가져오기</q-card-section>
        <q-card-section>
          <q-file
            v-model="importFile"
            label="xlsx/xlsm 파일 선택"
            accept=".xlsx,.xlsm"
            outlined dense
          />
          <div class="text-caption text-grey q-mt-sm">
            동일 항목(점검코드+호스트명+점검일시)은 기본 정보만 갱신되고, 조치 정보는 셀 값이 있을 때만 덮어씁니다.
            신규 항목은 추가됩니다.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="가져오기" :loading="importing" :disable="!importFile" @click="doImport" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useTablePagination } from 'src/composables/useTablePagination'
import {
  listVulnerabilities, getFilterOptions, exportVulnerabilities, importExcel,
  RISK_LEVEL_OPTIONS, CONTROL_STATUS_OPTIONS, ACTION_STATUS_OPTIONS,
  RISK_COLOR, CONTROL_COLOR,
  type Vulnerability,
} from 'src/services/isms/vulnerability'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const rows = ref<Vulnerability[]>([])
const loading = ref(false)
const { pagination } = useTablePagination({ rowsPerPage: 25 })

const assetTypeOptions = ref<string[]>([])
const assigneeOptions = ref<string[]>([])

const exporting = ref(false)
const importDialog = ref(false)
const importFile = ref<File | null>(null)
const importing = ref(false)

const filter = ref({
  search: '',
  assetType: null as string | null,
  riskLevel: null as string | null,
  controlStatus: null as string | null,
  actionStatus: null as string | null,
  assignee: null as string | null,
  plannedDateFrom: '',
  plannedDateTo: '',
})

const columns = [
  { name: 'checkCode', label: '점검코드', field: 'checkCode', align: 'left' as const },
  { name: 'checkItem', label: '점검항목', field: 'checkItem', align: 'left' as const },
  { name: 'hostname', label: '호스트명/자산명', field: 'hostname', align: 'left' as const },
  { name: 'riskLevel', label: '위험도', field: 'riskLevel', align: 'center' as const },
  { name: 'controlStatus', label: '통제여부', field: 'controlStatus', align: 'center' as const },
  { name: 'assignee', label: '담당자', field: 'assignee', align: 'left' as const },
  { name: 'actionStatus', label: '조치여부', field: 'actionStatus', align: 'center' as const },
  { name: 'plannedDate', label: '조치예정일', field: 'plannedDate', align: 'center' as const },
]

async function fetchList() {
  loading.value = true
  try {
    const skip = (pagination.value.page - 1) * pagination.value.rowsPerPage
    const page = await listVulnerabilities({
      skip,
      limit: pagination.value.rowsPerPage,
      search: filter.value.search || undefined,
      asset_type: filter.value.assetType || undefined,
      risk_level: filter.value.riskLevel || undefined,
      control_status: filter.value.controlStatus || undefined,
      action_status: filter.value.actionStatus || undefined,
      assignee: filter.value.assignee || undefined,
      planned_date_from: filter.value.plannedDateFrom || undefined,
      planned_date_to: filter.value.plannedDateTo || undefined,
    })
    rows.value = page.items
    pagination.value.rowsNumber = page.total
  } catch {
    $q.notify({ type: 'negative', message: '목록을 불러오는데 실패했습니다.' })
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
    search: '', assetType: null, riskLevel: null, controlStatus: null,
    actionStatus: null, assignee: null, plannedDateFrom: '', plannedDateTo: '',
  }
  pagination.value.page = 1
  void fetchList()
  syncToUrl()
}

function onTableRequest(props: { pagination: { page: number; rowsPerPage: number } }) {
  pagination.value.page = props.pagination.page
  pagination.value.rowsPerPage = props.pagination.rowsPerPage
  void fetchList()
  syncToUrl()
}

// ── URL 상태 동기화 (뒤로가기로 목록에 돌아왔을 때 필터 복원) ──────────────
function syncToUrl() {
  const q: Record<string, string> = {}
  if (filter.value.search) q.search = filter.value.search
  if (filter.value.assetType) q.assetType = filter.value.assetType
  if (filter.value.riskLevel) q.riskLevel = filter.value.riskLevel
  if (filter.value.controlStatus) q.controlStatus = filter.value.controlStatus
  if (filter.value.actionStatus) q.actionStatus = filter.value.actionStatus
  if (filter.value.assignee) q.assignee = filter.value.assignee
  if (filter.value.plannedDateFrom) q.plannedDateFrom = filter.value.plannedDateFrom
  if (filter.value.plannedDateTo) q.plannedDateTo = filter.value.plannedDateTo
  if (pagination.value.page > 1) q.page = String(pagination.value.page)
  if (pagination.value.rowsPerPage !== 25) q.rows = String(pagination.value.rowsPerPage)
  void router.replace({ query: q })
}

function initFromUrl() {
  const q = route.query
  if (q.search) filter.value.search = String(q.search)
  if (q.assetType) filter.value.assetType = String(q.assetType)
  if (q.riskLevel) filter.value.riskLevel = String(q.riskLevel)
  if (q.controlStatus) filter.value.controlStatus = String(q.controlStatus)
  if (q.actionStatus) filter.value.actionStatus = String(q.actionStatus)
  if (q.assignee) filter.value.assignee = String(q.assignee)
  if (q.plannedDateFrom) filter.value.plannedDateFrom = String(q.plannedDateFrom)
  if (q.plannedDateTo) filter.value.plannedDateTo = String(q.plannedDateTo)
  if (q.page) pagination.value.page = Number(q.page)
  if (q.rows) pagination.value.rowsPerPage = Number(q.rows)
}

async function doExport() {
  exporting.value = true
  try {
    await exportVulnerabilities()
  } catch {
    $q.notify({ type: 'negative', message: '내보내기에 실패했습니다.' })
  } finally {
    exporting.value = false
  }
}

async function doImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const result = await importExcel(importFile.value)
    $q.notify({ type: 'positive', message: `신규 ${result.inserted}건, 업데이트 ${result.updated}건 (총 ${result.total}건)` })
    importDialog.value = false
    importFile.value = null
    pagination.value.page = 1
    void fetchList()
  } catch {
    $q.notify({ type: 'negative', message: '가져오기에 실패했습니다.' })
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  initFromUrl()
  void fetchList()
  try {
    const opts = await getFilterOptions()
    assetTypeOptions.value = opts.assetTypes
    assigneeOptions.value = opts.assignees
  } catch {
    // 필터 옵션 로드 실패는 조용히 무시 (목록 자체는 계속 사용 가능)
  }
})
</script>

<style scoped>
.ellipsis-cell {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
