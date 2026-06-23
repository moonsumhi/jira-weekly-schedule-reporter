<template>
  <q-page padding>
    <div class="text-h6 q-mb-md">Audit Log</div>

    <!-- 필터 영역 -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-sm items-end">
          <div class="col-12 col-sm-3">
            <q-select
              v-model="filterActor"
              dense outlined label="작업자"
              :options="actorOptions"
              clearable emit-value map-options
            />
          </div>
          <div class="col-6 col-sm-2">
            <q-select v-model="filterAction" dense outlined label="액션" :options="actionOptions" emit-value map-options clearable />
          </div>
          <div class="col-6 col-sm-2">
            <q-select v-model="filterCategory" dense outlined label="카테고리" :options="categoryOptions" emit-value map-options />
          </div>
          <div class="col-6 col-sm-2">
            <q-input v-model="filterFrom" dense outlined label="시작일" :type="('date' as any)" clearable />
          </div>
          <div class="col-6 col-sm-2">
            <q-input v-model="filterTo" dense outlined label="종료일" :type="('date' as any)" clearable />
          </div>
          <div class="col-12 col-sm-1">
            <q-btn color="primary" icon="search" label="조회" @click="load" :loading="loading" class="full-width" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- 결과 테이블 -->
    <q-card flat bordered>
      <q-card-section class="q-pa-none">
        <div class="row items-center q-px-md q-pt-sm q-pb-xs">
          <span class="text-caption text-grey-7">총 {{ total }}건</span>
          <q-space />
          <q-btn flat dense round icon="download" color="grey-7" @click="doExport" :loading="exporting">
            <q-tooltip>Excel 내보내기</q-tooltip>
          </q-btn>
          <q-btn flat dense round icon="refresh" color="grey-7" @click="load" :loading="loading">
            <q-tooltip>새로고침</q-tooltip>
          </q-btn>
          <span class="text-caption text-grey-6">페이지 {{ page }} / {{ totalPages }}</span>
        </div>

        <q-markup-table flat dense separator="horizontal">
          <thead>
            <tr class="text-left">
              <th style="width:160px">일시 (KST)</th>
              <th style="width:200px">작업자</th>
              <th style="width:100px">카테고리</th>
              <th style="width:80px">액션</th>
              <th style="width:100px">export/수동추가</th>
              <th>변경 내용</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr>
                <td colspan="5" class="text-center q-pa-lg">
                  <q-spinner size="32px" />
                </td>
              </tr>
            </template>
            <template v-else-if="items.length === 0">
              <tr>
                <td colspan="5" class="text-center text-grey-6 q-pa-lg">데이터가 없습니다.</td>
              </tr>
            </template>
            <template v-else>
              <tr v-for="item in items" :key="item.id" class="cursor-pointer row-hover" @click="openDetail(item)">
                <td class="text-caption">{{ formatKst(item.changedAt) }}</td>
                <td class="text-caption">{{ item.changedBy }}</td>
                <td>
                  <q-badge :color="categoryColor(item.category)" outline>{{ item.category }}</q-badge>
                </td>
                <td>
                  <q-badge :color="actionColor(item.action)" outline>{{ item.action }}</q-badge>
                </td>
                <td>
                  <template v-if="item.source === 'export'">
                    <q-badge color="blue" outline>export</q-badge>
                  </template>
                  <template v-else-if="item.source === 'import'">
                    <q-badge color="purple" outline>자산 추가</q-badge>
                  </template>
                  <template v-else-if="item.source === 'manual'">
                    <q-badge color="grey-6" outline>수동추가</q-badge>
                  </template>
                  <template v-else>
                    <span class="text-caption text-grey-5">-</span>
                  </template>
                </td>
                <td>
                  <div v-if="item.diff && item.diff.length" class="diff-list">
                    <span
                      v-for="d in item.diff.slice(0, 3)"
                      :key="d.path"
                      class="diff-item text-caption"
                    >
                      <span class="text-grey-7">{{ d.path }}</span>:
                      <span class="text-grey-6 text-strike">{{ truncate(d.before) }}</span>
                      <q-icon name="arrow_forward" size="10px" color="grey-5" />
                      <span class="text-grey-9">{{ truncate(d.after) }}</span>
                    </span>
                    <span v-if="item.diff.length > 3" class="text-caption text-grey-5">
                      +{{ item.diff.length - 3 }}
                    </span>
                  </div>
                  <span v-else class="text-caption text-grey-5">-</span>
                </td>
              </tr>
            </template>
          </tbody>
        </q-markup-table>
      </q-card-section>

      <!-- 상세보기 다이얼로그 -->
      <q-dialog v-model="detailDialog">
        <q-card style="min-width: 480px; max-width: 640px">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-subtitle1 text-weight-bold">로그 상세</div>
            <q-space />
            <q-btn flat round dense icon="close" v-close-popup />
          </q-card-section>

          <q-card-section v-if="detailItem">
            <q-list dense>
              <q-item>
                <q-item-section>
                  <q-item-label caption>일시 (KST)</q-item-label>
                  <q-item-label>{{ formatKst(detailItem.changedAt) }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label caption>작업자</q-item-label>
                  <q-item-label>{{ detailItem.changedBy }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label caption>카테고리</q-item-label>
                  <q-item-label>
                    <q-badge :color="categoryColor(detailItem.category)" outline>{{ detailItem.category }}</q-badge>
                  </q-item-label>
                </q-item-section>
                <q-item-section>
                  <q-item-label caption>액션</q-item-label>
                  <q-item-label>
                    <q-badge :color="actionColor(detailItem.action)" outline>{{ detailItem.action }}</q-badge>
                  </q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="detailItem.source">
                <q-item-section>
                  <q-item-label caption>출처</q-item-label>
                  <q-item-label>{{ detailItem.source }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>

            <q-separator class="q-my-sm" />

            <div class="text-caption text-grey q-mb-xs">변경 내용</div>
            <div v-if="detailItem.diff && detailItem.diff.length">
              <!-- VIEW: 항목/내용 2열 -->
              <q-markup-table v-if="detailItem.action === 'VIEW'" flat dense bordered>
                <thead>
                  <tr class="text-left bg-grey-2">
                    <th style="width:120px">항목</th>
                    <th>내용</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in detailItem.diff" :key="d.path">
                    <td class="text-caption text-grey-8">{{ d.path }}</td>
                    <td class="text-caption text-grey-9">{{ formatVal(d.after) }}</td>
                  </tr>
                </tbody>
              </q-markup-table>

              <!-- CREATE: 항목/추가된 값 2열 -->
              <q-markup-table v-else-if="detailItem.action === 'CREATE'" flat dense bordered>
                <thead>
                  <tr class="text-left bg-grey-2">
                    <th style="width:120px">항목</th>
                    <th>추가된 값</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in detailItem.diff" :key="d.path">
                    <td class="text-caption text-grey-8">{{ d.path }}</td>
                    <td class="text-caption text-grey-9">{{ formatVal(d.after) }}</td>
                  </tr>
                </tbody>
              </q-markup-table>

              <!-- UPDATE / DELETE / RESTORE: 항목/이전 값/변경 값 3열 -->
              <q-markup-table v-else flat dense bordered>
                <thead>
                  <tr class="text-left bg-grey-2">
                    <th style="width:120px">항목</th>
                    <th>이전 값</th>
                    <th>변경 값</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in detailItem.diff" :key="d.path">
                    <td class="text-caption text-grey-8">{{ d.path }}</td>
                    <td class="text-caption text-strike text-grey-6">{{ formatVal(d.before) }}</td>
                    <td class="text-caption text-grey-9">{{ formatVal(d.after) }}</td>
                  </tr>
                </tbody>
              </q-markup-table>
            </div>
            <div v-else class="text-caption text-grey-5">변경 내용 없음</div>
          </q-card-section>
        </q-card>
      </q-dialog>

      <!-- 페이지네이션 -->
      <q-card-section class="row justify-center q-pt-sm q-pb-md" v-if="totalPages > 1">
        <q-pagination
          v-model="page"
          :max="totalPages"
          :max-pages="7"
          boundary-numbers
          @update:model-value="load"
        />
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from 'boot/axios'
import * as XLSX from 'xlsx'

interface DiffItem {
  path: string
  before: unknown
  after: unknown
}

interface AuditLogItem {
  id: string
  category: string
  assetId: string
  action: string
  source: string
  changedAt: string
  changedBy: string
  diff: DiffItem[] | null
}

const PAGE_SIZE = 50

const loading = ref(false)
const exporting = ref(false)
const items = ref<AuditLogItem[]>([])
const total = ref(0)
const page = ref(1)

const filterActor = ref<string | null>(null)
const filterAction = ref<string | null>(null)
const filterCategory = ref<string | null>(null)
const filterFrom = ref('')
const filterTo = ref('')

interface ActorOption { email: string; name: string }
const actors = ref<ActorOption[]>([])
const actorOptions = computed(() => [
  { label: '전체', value: null },
  ...actors.value.map((a) => ({ label: a.name, value: a.email })),
])

const actionOptions = [
  { label: 'CREATE', value: 'CREATE' },
  { label: 'UPDATE', value: 'UPDATE' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'RESTORE', value: 'RESTORE' },
  { label: 'LOGIN', value: 'LOGIN' },
  { label: 'LOGIN_FAILED', value: 'LOGIN_FAILED' },
  { label: 'VIEW', value: 'VIEW' },
]

const categoryOptions = [
  { label: '전체', value: null },
  { label: '서버', value: '서버' },
  { label: '네트워크', value: '네트워크' },
  { label: '정보보호시스템', value: '정보보호시스템' },
  { label: 'DBMS', value: 'DBMS' },
  { label: 'VMware', value: 'VMware' },
  { label: '작업계획서', value: '작업계획서' },
  { label: '작업계획서(서비스외)', value: '작업계획서(서비스외)' },
  { label: '작업결과서', value: '작업결과서' },
  { label: '서버실 점검', value: '서버실 점검' },
  { label: '당직', value: '당직' },
  { label: '로그인', value: '로그인' },
  { label: '활동', value: '활동' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const detailDialog = ref(false)
const detailItem = ref<AuditLogItem | null>(null)

function openDetail(item: AuditLogItem) {
  detailItem.value = item
  detailDialog.value = true
}

async function loadActors() {
  const res = await api.get<ActorOption[]>('/admin/audit-log/actors')
  actors.value = res.data
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: PAGE_SIZE }
    if (filterActor.value)    params.actor     = filterActor.value
    if (filterAction.value)   params.action    = filterAction.value
    if (filterCategory.value) params.category  = filterCategory.value
    if (filterFrom.value)     params.from_date = filterFrom.value
    if (filterTo.value)       params.to_date   = filterTo.value

    const res = await api.get<{ total: number; items: AuditLogItem[] }>('/admin/audit-log', { params })
    total.value = res.data.total
    items.value = res.data.items
  } finally {
    loading.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    const params: Record<string, string | number> = { page: 1, page_size: 5000 }
    if (filterActor.value)    params.actor     = filterActor.value
    if (filterAction.value)   params.action    = filterAction.value
    if (filterCategory.value) params.category  = filterCategory.value
    if (filterFrom.value)     params.from_date = filterFrom.value
    if (filterTo.value)       params.to_date   = filterTo.value

    const res = await api.get<{ total: number; items: AuditLogItem[] }>('/admin/audit-log', { params })
    const rows = res.data.items

    const data = rows.map((item) => ({
      '일시 (KST)': formatKst(item.changedAt),
      '작업자': item.changedBy,
      '카테고리': item.category,
      '액션': item.action,
      '출처': item.source ?? '',
      '변경 내용': item.diff
        ? item.diff.map((d) => `${d.path}: ${formatVal(d.before)} → ${formatVal(d.after)}`).join('\n')
        : '',
    }))

    const ws = XLSX.utils.json_to_sheet(data)
    ws['!cols'] = [
      { wch: 22 }, { wch: 28 }, { wch: 16 }, { wch: 14 }, { wch: 10 }, { wch: 60 },
    ]
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'AuditLog')

    const dateStr = new Date().toISOString().slice(0, 10)
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' }) as ArrayBuffer
    const blob = new Blob([wbout], { type: 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit_log_${dateStr}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

function formatKst(iso: string | null): string {
  if (!iso) return '-'
  const s = iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z'
  return new Date(s).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', hour12: false })
}

function formatVal(val: unknown): string {
  if (val == null) return '-'
  return typeof val === 'string' ? val : JSON.stringify(val)
}

function truncate(val: unknown): string {
  if (val == null) return '-'
  const s: string = typeof val === 'string' ? val : JSON.stringify(val) ?? '-'
  return s.length > 20 ? s.slice(0, 20) + '…' : s
}

function actionColor(action: string): string {
  if (action === 'CREATE') return 'positive'
  if (action === 'DELETE') return 'negative'
  if (action === 'RESTORE') return 'info'
  if (action === 'VIEW') return 'grey-6'
  return 'orange'
}

function categoryColor(cat: string): string {
  if (cat === '서버') return 'blue'
  if (cat === '네트워크') return 'teal'
  if (cat === 'DBMS') return 'deep-purple'
  if (cat === '정보보호시스템') return 'orange'
  if (cat === 'VMware') return 'green'
  return 'grey'
}

onMounted(() => {
  void loadActors()
  void load()
})
</script>

<style scoped>
.diff-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.diff-item {
  background: #f5f5f5;
  border-radius: 4px;
  padding: 1px 6px;
}
.text-strike {
  text-decoration: line-through;
  color: #aaa;
}
.row-hover:hover {
  background: #f5f5f5;
}
</style>
