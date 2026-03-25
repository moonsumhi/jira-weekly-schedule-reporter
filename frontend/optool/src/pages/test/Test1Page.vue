<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]주간보고5</div>
        <div class="text-caption text-grey-7">주간 Jira 업무 현황 보고서</div>
      </div>

      <!-- 기간 선택 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center q-col-gutter-md">
              <div class="col-12 col-md-3">
                <q-input v-model="startDate" label="시작일" readonly>
                  <template v-slot:append>
                    <q-icon name="event" class="cursor-pointer">
                      <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                        <q-date v-model="startDate" mask="YYYY-MM-DD" />
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="endDate" label="종료일" readonly>
                  <template v-slot:append>
                    <q-icon name="event" class="cursor-pointer">
                      <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                        <q-date v-model="endDate" mask="YYYY-MM-DD" />
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-3">
                <q-input
                  v-model="assigneesInput"
                  label="담당자 (쉼표 구분)"
                  placeholder="홍길동,김철수"
                />
              </div>
              <div class="col-12 col-md-3">
                <div class="row q-gutter-sm">
                  <q-btn label="조회" color="primary" :loading="loading" @click="fetchReport" />
                  <q-btn label="이번 주" outline color="secondary" @click="setCurrentWeek" />
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 보고서 본문 -->
      <div v-if="groups.length > 0" class="col-12">

        <!-- 보고서 제목 -->
        <q-card flat bordered class="q-mb-md">
          <q-card-section class="bg-primary text-white">
            <div class="text-h6 text-weight-bold">[pilot]주간보고5</div>
            <div class="text-subtitle2">{{ reportPeriodLabel }}</div>
          </q-card-section>

          <!-- 전체 요약 -->
          <q-card-section>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-3" v-for="stat in summaryStats" :key="stat.label">
                <q-card flat bordered class="text-center q-pa-sm">
                  <div class="text-h4 text-weight-bold" :class="stat.color">{{ stat.value }}</div>
                  <div class="text-caption text-grey-7">{{ stat.label }}</div>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <!-- 담당자별 보고 -->
        <q-card flat bordered v-for="group in groups" :key="group.assignee" class="q-mb-md">
          <q-card-section class="bg-grey-2">
            <div class="row items-center">
              <q-avatar color="primary" text-color="white" size="32px" class="q-mr-sm">
                {{ group.assignee.charAt(0) }}
              </q-avatar>
              <div>
                <div class="text-subtitle1 text-weight-bold">{{ group.assignee }}</div>
                <div class="text-caption text-grey-7">총 {{ group.count }}건</div>
              </div>
              <q-space />
              <div class="row q-gutter-xs">
                <q-badge
                  v-for="(cnt, status) in statusCounts(group.issues)"
                  :key="status"
                  :color="statusColor(status)"
                  class="q-px-sm q-py-xs"
                >
                  {{ statusLabel(status) }} {{ cnt }}
                </q-badge>
              </div>
            </div>
          </q-card-section>

          <q-card-section class="q-pa-none">
            <q-table
              flat
              :rows="group.issues"
              :columns="issueColumns"
              row-key="key"
              hide-bottom
              :rows-per-page-options="[0]"
            >
              <template #body-cell-key="props">
                <q-td :props="props">
                  <a :href="props.row.url" target="_blank" class="text-primary text-weight-medium">
                    {{ props.row.key }}
                  </a>
                  <q-btn
                    flat
                    dense
                    round
                    size="xs"
                    icon="attach_file"
                    color="grey-6"
                    class="q-ml-xs"
                    :loading="loadingAttachments[props.row.key]"
                    @click="toggleAttachments(props.row.key)"
                  >
                    <q-tooltip>첨부파일 새로고침</q-tooltip>
                  </q-btn>
                </q-td>
              </template>

              <template #body-cell-summary="props">
                <q-td :props="props">
                  <div>{{ props.row.summary }}</div>
                  <div
                    v-if="attachmentsMap[props.row.key] && attachmentsMap[props.row.key]!.length > 0"
                    class="q-mt-xs"
                  >
                    <q-expansion-item
                      v-for="att in attachmentsMap[props.row.key]"
                      :key="att.filename"
                      dense
                      :label="att.filename"
                      icon="description"
                      class="bg-grey-1 rounded-borders q-mb-xs"
                      header-class="text-caption text-grey-7"
                    >
                      <q-card flat>
                        <q-card-section class="q-pa-sm">
                          <pre class="text-caption" style="white-space: pre-wrap; word-break: break-word; margin: 0;">{{ att.text }}</pre>
                        </q-card-section>
                      </q-card>
                    </q-expansion-item>
                  </div>
                  <div
                    v-else-if="attachmentsMap[props.row.key] !== undefined && attachmentsMap[props.row.key]!.length === 0"
                    class="text-caption text-grey-5 q-mt-xs"
                  >
                    첨부파일 없음
                  </div>
                </q-td>
              </template>

              <template #body-cell-status="props">
                <q-td :props="props">
                  <q-badge :color="statusColor(props.row.status)" :label="props.row.status" />
                </q-td>
              </template>

              <template #body-cell-start="props">
                <q-td :props="props">
                  {{ props.row.start || '-' }}
                </q-td>
              </template>

              <template #body-cell-duedate="props">
                <q-td :props="props">
                  <span :class="isOverdue(props.row) ? 'text-negative text-weight-bold' : ''">
                    {{ props.row.duedate || '-' }}
                  </span>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>

        <!-- 인쇄 버튼 -->
        <div class="row justify-end q-mt-sm">
          <q-btn label="인쇄" icon="print" outline color="grey-7" @click="printReport" />
        </div>
      </div>

      <!-- 데이터 없음 -->
      <div v-else-if="searched && !loading" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="inbox" size="48px" class="q-mb-sm" />
            <div>조회된 업무가 없습니다.</div>
          </q-card-section>
        </q-card>
      </div>

    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Notify } from 'quasar'
import { DateTime } from 'luxon'
import { api } from 'boot/axios'
import qs from 'qs'
import type { AssigneeGroup, Issue } from 'src/types/jira'

const startDate = ref('')
const endDate = ref('')
const assigneesInput = ref('')
const loading = ref(false)
const searched = ref(false)
const groups = ref<AssigneeGroup[]>([])

interface AttachmentItem { filename: string; text: string }
const attachmentsMap = ref<Record<string, AttachmentItem[]>>({})
const loadingAttachments = ref<Record<string, boolean>>({})

const issueColumns = [
  { name: 'key', label: '이슈 키', field: 'key', align: 'left' as const, style: 'width: 120px' },
  { name: 'summary', label: '업무 내용', field: 'summary', align: 'left' as const },
  { name: 'status', label: '상태', field: 'status', align: 'center' as const, style: 'width: 120px' },
  { name: 'start', label: '시작일', field: 'start', align: 'center' as const, style: 'width: 110px' },
  { name: 'duedate', label: '마감일', field: 'duedate', align: 'center' as const, style: 'width: 110px' },
]

const reportPeriodLabel = computed(() => {
  if (!startDate.value || !endDate.value) return ''
  return `${startDate.value} ~ ${endDate.value}`
})

const summaryStats = computed(() => {
  const total = groups.value.reduce((s, g) => s + g.count, 0)
  let done = 0, inProgress = 0, todo = 0, blocked = 0
  for (const g of groups.value) {
    for (const issue of g.issues) {
      if (issue.status === 'Done') done++
      else if (issue.status === 'In Progress') inProgress++
      else if (issue.status === 'To Do') todo++
      else if (issue.status === 'Blocked') blocked++
    }
  }
  return [
    { label: '전체', value: total, color: 'text-primary' },
    { label: '완료', value: done, color: 'text-positive' },
    { label: '진행 중', value: inProgress, color: 'text-info' },
    { label: '대기', value: todo, color: 'text-warning' },
    { label: '차단', value: blocked, color: 'text-negative' },
  ]
})

function setCurrentWeek() {
  const now = DateTime.now().setZone('Asia/Seoul')
  const monday = now.startOf('week')
  const sunday = monday.plus({ days: 6 })
  startDate.value = monday.toFormat('yyyy-MM-dd')
  endDate.value = sunday.toFormat('yyyy-MM-dd')
}

function statusColor(status: string): string {
  switch (status) {
    case 'To Do': return 'warning'
    case 'In Progress': return 'info'
    case 'Done': return 'positive'
    case 'Blocked': return 'negative'
    default: return 'grey'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'To Do': return '대기'
    case 'In Progress': return '진행'
    case 'Done': return '완료'
    case 'Blocked': return '차단'
    default: return status
  }
}

function statusCounts(issues: Issue[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const issue of issues) {
    counts[issue.status] = (counts[issue.status] ?? 0) + 1
  }
  return counts
}

function isOverdue(issue: Issue): boolean {
  if (!issue.duedate) return false
  const due = DateTime.fromISO(issue.duedate, { zone: 'Asia/Seoul' })
  const today = DateTime.now().setZone('Asia/Seoul').startOf('day')
  return due < today && issue.status !== 'Done'
}

async function fetchReport() {
  if (!startDate.value || !endDate.value) {
    Notify.create({ type: 'warning', message: '시작일과 종료일을 선택해주세요.' })
    return
  }
  loading.value = true
  searched.value = false
  attachmentsMap.value = {}
  try {
    const assignees = assigneesInput.value
      ? assigneesInput.value.split(',').map(a => a.trim()).filter(a => a)
      : undefined

    const res = await api.get('/issues/today-tasks', {
      params: { start: startDate.value, end: endDate.value, assignees },
      paramsSerializer: (params) => qs.stringify(params, { arrayFormat: 'repeat' }),
    })
    groups.value = res.data.groups

    const allIssueKeys = groups.value.flatMap(g => g.issues.map(i => i.key))
    await loadAllAttachments(allIssueKeys)
  } catch {
    Notify.create({ type: 'negative', message: '데이터를 불러오지 못했습니다.' })
    groups.value = []
  } finally {
    loading.value = false
    searched.value = true
  }
}

async function loadAllAttachments(issueKeys: string[]) {
  await Promise.all(
    issueKeys.map(async (key) => {
      loadingAttachments.value[key] = true
      try {
        const res = await api.get(`/issues/${key}/attachments`)
        attachmentsMap.value[key] = res.data.attachments as AttachmentItem[]
      } catch {
        attachmentsMap.value[key] = []
      } finally {
        loadingAttachments.value[key] = false
      }
    })
  )
}

async function toggleAttachments(issueKey: string) {
  loadingAttachments.value[issueKey] = true
  try {
    const res = await api.get(`/issues/${issueKey}/attachments`)
    attachmentsMap.value[issueKey] = res.data.attachments as AttachmentItem[]
    if (attachmentsMap.value[issueKey].length === 0) {
      Notify.create({ type: 'info', message: '첨부파일이 없습니다.' })
    }
  } catch {
    Notify.create({ type: 'negative', message: '첨부파일을 불러오지 못했습니다.' })
    attachmentsMap.value[issueKey] = []
  } finally {
    loadingAttachments.value[issueKey] = false
  }
}

function printReport() {
  window.print()
}

onMounted(() => {
  setCurrentWeek()
})
</script>

<style scoped>
@media print {
  .q-btn { display: none; }
  .q-card { box-shadow: none !important; border: 1px solid #ddd !important; }
}
</style>
