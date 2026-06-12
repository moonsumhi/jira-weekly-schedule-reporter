<template>
  <q-page padding>
    <div class="row items-center q-mb-md q-gutter-sm">
      <div class="text-h6">서버 점검 (월1회)</div>
      <q-space />

      <!-- 보고서 선택 -->
      <q-select
        v-if="reports.length"
        v-model="selectedId"
        :options="reportOptions"
        emit-value map-options
        dense outlined
        label="보고서 선택"
        style="min-width: 240px"
        @update:model-value="loadReport"
      />

      <!-- 업로드 -->
      <q-btn v-if="isInternal" color="primary" icon="upload_file" label="Excel 업로드" dense @click="triggerUpload" :loading="uploading" />
      <input ref="fileInput" type="file" accept=".xlsx" class="hidden" @change="onFileChange" />

      <!-- 삭제 -->
      <q-btn
        v-if="isInternal && selectedId"
        flat dense round icon="delete"
        color="negative"
        @click="confirmDelete"
        :loading="deleting"
      >
        <q-tooltip>보고서 삭제</q-tooltip>
      </q-btn>
    </div>

    <!-- 보고서 없을 때 -->
    <div v-if="!reports.length && !loading" class="text-center text-grey-5 q-pa-xl">
      <q-icon name="description" size="48px" class="q-mb-sm" /><br />
      업로드된 보고서가 없습니다.<br />
      health_report_*.xlsx 파일을 업로드하세요.
    </div>

    <!-- 로딩 -->
    <div v-else-if="loading" class="text-center q-pa-xl">
      <q-spinner size="40px" />
    </div>

    <!-- 보고서 테이블 -->
    <template v-else-if="report">
      <!-- 보고서 메타 -->
      <div class="row items-center q-mb-sm text-caption text-grey-6">
        <span>{{ report.reportTitle }}</span>
        <q-space />
        <span>{{ report.serverCount ?? report.servers.length }}대 점검</span>
        <span class="q-ml-md">업로드: {{ report.uploadedBy }} · {{ report.uploadedAt }}</span>
      </div>

      <!-- 요약 테이블 -->
      <q-card flat bordered>
        <q-markup-table flat dense separator="horizontal">
          <thead>
            <tr class="text-left bg-grey-2">
              <th style="width:40px">No.</th>
              <th style="min-width:140px">Host Name</th>
              <th style="min-width:160px">IP</th>
              <th style="width:70px">CPU</th>
              <th style="width:70px">RAM</th>
              <th style="width:70px">Swap</th>
              <th style="width:80px">Disk 최대</th>
              <th style="width:70px">로그에러</th>
              <th>조치 필요 항목</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in report.servers"
              :key="s.hostName"
              class="cursor-pointer row-hover"
              @click="openDetail(s)"
            >
              <td class="text-caption text-grey-6">{{ s.no }}</td>
              <td class="text-caption text-weight-medium">{{ s.hostName }}</td>
              <td class="text-caption text-grey-7" style="font-size:11px">{{ s.ip }}</td>
              <td><span :class="metricClass(s.cpu)">{{ s.cpu }}</span></td>
              <td><span :class="metricClass(s.ram)">{{ s.ram }}</span></td>
              <td><span :class="metricClass(s.swap)">{{ s.swap }}</span></td>
              <td><span :class="metricClass(s.diskMax)">{{ s.diskMax }}</span></td>
              <td>
                <q-badge v-if="s.logErrors !== '-' && s.logErrors" :color="logErrorColor(s.logErrors)" outline>
                  {{ s.logErrors }}건
                </q-badge>
                <span v-else class="text-caption text-grey-5">-</span>
              </td>
              <td>
                <span :class="actionClass(s.actionItems)" class="text-caption action-preview">
                  {{ actionPreview(s.actionItems) }}
                </span>
              </td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card>
    </template>

    <!-- 상세 다이얼로그 -->
    <q-dialog v-model="detailDialog" maximized>
      <q-card v-if="detailServer" style="max-width:720px; margin: auto; height: fit-content; max-height: 90vh">
        <q-card-section class="row items-center q-pb-none">
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ detailServer.hostName }}</div>
            <div class="text-caption text-grey-6">{{ detailServer.ip }}</div>
          </div>
          <q-space />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-card-section>
          <!-- 성능 요약 -->
          <div class="row q-gutter-sm q-mb-md">
            <q-chip v-for="m in serverMetrics(detailServer)" :key="m.label"
              :color="m.color" text-color="white" dense>
              {{ m.label }}: {{ m.value }}
            </q-chip>
          </div>

          <q-separator class="q-mb-md" />

          <div class="text-subtitle2 q-mb-sm">조치 필요 항목</div>
          <div v-if="detailServer.actionItems" class="action-detail-text">{{ detailServer.actionItems }}</div>
          <div v-else class="text-caption text-grey-5">이상 없음</div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const auth = useAuthStore()
const isInternal = computed(() => auth.me?.isInternal !== false)

interface ServerSummary {
  no: number | null
  hostName: string
  ip: string
  cpu: string
  ram: string
  swap: string
  diskMax: string
  logErrors: string
  actionItems: string
}

interface HealthReportListItem {
  id: string
  reportDate: string
  reportTitle: string
  serverCount: number
  uploadedAt: string | null
  uploadedBy: string
}

interface HealthReport extends HealthReportListItem {
  servers: ServerSummary[]
}

const loading = ref(false)
const uploading = ref(false)
const deleting = ref(false)

const reports = ref<HealthReportListItem[]>([])
const selectedId = ref<string | null>(null)
const report = ref<HealthReport | null>(null)

const fileInput = ref<HTMLInputElement | null>(null)

const reportOptions = computed(() =>
  reports.value.map((r) => ({
    label: `${r.reportDate} (${r.serverCount}대)`,
    value: r.id,
  }))
)

// ── 로딩 ────────────────────────────────────────────────────────────────────

async function loadList() {
  const res = await api.get<HealthReportListItem[]>('/health-reports')
  reports.value = res.data
  if (reports.value.length && !selectedId.value) {
    selectedId.value = reports.value[0]!.id
    await loadReport(selectedId.value)
  }
}

async function loadReport(id: string) {
  loading.value = true
  try {
    const res = await api.get<HealthReport>(`/health-reports/${id}`)
    report.value = res.data
  } finally {
    loading.value = false
  }
}

// ── 업로드 ───────────────────────────────────────────────────────────────────

function triggerUpload() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''

  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await api.post<HealthReport>('/health-reports', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const uploaded = res.data

    // 목록 갱신
    await loadList()
    selectedId.value = uploaded.id
    await loadReport(uploaded.id)

    $q.notify({ type: 'positive', message: `${uploaded.reportDate} 보고서 업로드 완료 (${uploaded.servers.length}대)` })
  } catch {
    $q.notify({ type: 'negative', message: '업로드 실패' })
  } finally {
    uploading.value = false
  }
}

// ── 삭제 ────────────────────────────────────────────────────────────────────

function confirmDelete() {
  if (!selectedId.value || !report.value) return
  $q.dialog({
    title: '보고서 삭제',
    message: `${report.value.reportDate} 보고서를 삭제하시겠습니까?`,
    cancel: true,
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      deleting.value = true
      try {
        await api.delete(`/health-reports/${selectedId.value}`)
        selectedId.value = null
        report.value = null
        await loadList()
        $q.notify({ type: 'positive', message: '삭제되었습니다.' })
      } finally {
        deleting.value = false
      }
    })()
  })
}

// ── 상세 다이얼로그 ────────────────────────────────────────────────────────────

const detailDialog = ref(false)
const detailServer = ref<ServerSummary | null>(null)

function openDetail(s: ServerSummary) {
  detailServer.value = s
  detailDialog.value = true
}

// ── 색상/포맷 유틸 ────────────────────────────────────────────────────────────

function parsePercent(val: string): number {
  const m = val.match(/([\d.]+)%/)
  return m ? parseFloat(m[1]!) : 0
}

function metricClass(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'text-negative text-weight-bold'
  if (pct >= 80) return 'text-orange text-weight-medium'
  return 'text-caption'
}

function logErrorColor(val: string): string {
  const n = parseInt(val)
  if (isNaN(n) || n === 0) return 'grey'
  if (n >= 100) return 'negative'
  return 'orange'
}

function actionClass(val: string): string {
  if (val.includes('⚠')) return 'text-negative'
  if (val.includes('△')) return 'text-orange'
  if (val.includes('이상 없음')) return 'text-positive'
  return 'text-grey-7'
}

function actionPreview(val: string): string {
  if (!val) return '-'
  const firstLine = val.split('\n')[0] ?? val
  return firstLine.length > 30 ? firstLine.slice(0, 30) + '…' : firstLine
}

function serverMetrics(s: ServerSummary) {
  return [
    { label: 'CPU', value: s.cpu, color: metricColor(s.cpu) },
    { label: 'RAM', value: s.ram, color: metricColor(s.ram) },
    { label: 'Swap', value: s.swap, color: metricColor(s.swap) },
    { label: 'Disk 최대', value: s.diskMax, color: metricColor(s.diskMax) },
  ]
}

function metricColor(val: string): string {
  const pct = parsePercent(val)
  if (pct >= 90) return 'negative'
  if (pct >= 80) return 'orange'
  return 'positive'
}

onMounted(() => {
  void loadList()
})
</script>

<style scoped>
.hidden { display: none; }
.row-hover:hover { background: #f5f5f5; }
.action-preview { white-space: nowrap; }
.action-detail-text {
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.6;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  max-height: 55vh;
  overflow-y: auto;
  font-family: monospace;
}
</style>
