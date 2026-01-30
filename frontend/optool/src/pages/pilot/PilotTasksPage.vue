<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <div class="col-12">
        <div class="text-h5">Pilot 일감 처리 현황</div>
        <div class="text-caption text-grey-7">
          Pilot이 처리 중인 Jira 이슈 목록입니다.
        </div>
      </div>

      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center q-mb-md">
              <q-btn
                flat
                icon="refresh"
                label="새로고침"
                :loading="loading"
                @click="loadTasks"
              />
              <q-space />
              <q-badge :color="statusColor('pending')" class="q-mr-sm">
                대기 {{ counts.pending }}
              </q-badge>
              <q-badge :color="statusColor('completed')" class="q-mr-sm">
                완료 {{ counts.completed }}
              </q-badge>
              <q-badge :color="statusColor('failed')" class="q-mr-sm">
                실패 {{ counts.failed }}
              </q-badge>
              <q-badge v-if="counts.legacy > 0" :color="statusColor('legacy')">
                이전 {{ counts.legacy }}
              </q-badge>
            </div>

            <q-table
              flat
              bordered
              :rows="tasks"
              :columns="columns"
              row-key="issue_key"
              :loading="loading"
              :pagination="{ rowsPerPage: 20 }"
            >
              <template #body-cell-status="props">
                <q-td :props="props">
                  <q-badge :color="statusColor(props.row.status)">
                    {{ statusLabel(props.row.status) }}
                  </q-badge>
                </q-td>
              </template>

              <template #body-cell-issue_key="props">
                <q-td :props="props">
                  <a
                    v-if="props.row.issue_url"
                    :href="props.row.issue_url"
                    target="_blank"
                    class="text-primary"
                  >
                    {{ props.row.issue_key }}
                  </a>
                  <span v-else>{{ props.row.issue_key }}</span>
                </q-td>
              </template>

              <template #body-cell-summary="props">
                <q-td :props="props">
                  <span v-if="props.row.summary">{{ props.row.summary }}</span>
                  <span v-else class="text-grey">-</span>
                </q-td>
              </template>

              <template #body-cell-project_key="props">
                <q-td :props="props">
                  <q-badge v-if="props.row.project_key" color="blue-grey-4" outline>
                    {{ props.row.project_key }}
                  </q-badge>
                  <span v-else class="text-grey">-</span>
                </q-td>
              </template>

              <template #body-cell-pr_url="props">
                <q-td :props="props">
                  <a
                    v-if="props.row.pr_url"
                    :href="props.row.pr_url"
                    target="_blank"
                    class="text-primary"
                  >
                    PR 보기
                  </a>
                  <span v-else class="text-grey">-</span>
                </q-td>
              </template>

              <template #body-cell-sent_at="props">
                <q-td :props="props">
                  {{ formatDate(props.row.sent_at) }}
                </q-td>
              </template>

              <template #body-cell-completed_at="props">
                <q-td :props="props">
                  {{ formatDate(props.row.completed_at || props.row.failed_at) }}
                </q-td>
              </template>

              <template #body-cell-error="props">
                <q-td :props="props">
                  <span v-if="props.row.error" class="text-negative text-caption">
                    {{ props.row.error.slice(0, 50) }}{{ props.row.error.length > 50 ? '...' : '' }}
                  </span>
                  <span v-else class="text-grey">-</span>
                </q-td>
              </template>
            </q-table>
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
import { listPilotTasks, type PilotTask } from 'src/services/pilot'

const loading = ref(false)
const tasks = ref<PilotTask[]>([])

const columns = [
  { name: 'issue_key', label: '이슈', field: 'issue_key', align: 'left' as const, sortable: true },
  { name: 'summary', label: '요약', field: 'summary', align: 'left' as const, sortable: true },
  { name: 'project_key', label: '프로젝트', field: 'project_key', align: 'left' as const, sortable: true },
  { name: 'status', label: '상태', field: 'status', align: 'center' as const, sortable: true },
  { name: 'sent_at', label: '전송 시간', field: 'sent_at', align: 'left' as const, sortable: true },
  { name: 'completed_at', label: '완료 시간', field: 'completed_at', align: 'left' as const, sortable: true },
  { name: 'pr_url', label: 'PR', field: 'pr_url', align: 'center' as const },
  { name: 'error', label: '오류', field: 'error', align: 'left' as const },
]

const counts = computed(() => {
  const result = { pending: 0, completed: 0, failed: 0, legacy: 0 }
  for (const task of tasks.value) {
    if (task.status === 'pending') result.pending++
    else if (task.status === 'completed') result.completed++
    else if (task.status === 'failed') result.failed++
    else if (task.status === 'legacy') result.legacy++
  }
  return result
})

function statusColor(status: string): string {
  switch (status) {
    case 'pending': return 'warning'
    case 'completed': return 'positive'
    case 'failed': return 'negative'
    case 'legacy': return 'grey-6'
    default: return 'grey'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'pending': return '처리 중'
    case 'completed': return '완료'
    case 'failed': return '실패'
    case 'legacy': return '이전 데이터'
    default: return status
  }
}

function formatDate(isoStr: string | null): string {
  if (!isoStr) return '-'
  const dt = DateTime.fromISO(isoStr, { zone: 'utc' }).setZone('Asia/Seoul')
  return dt.toFormat('yyyy-MM-dd HH:mm')
}

async function loadTasks() {
  try {
    loading.value = true
    tasks.value = await listPilotTasks()
  } catch {
    Notify.create({ type: 'negative', message: '태스크 목록을 불러오지 못했습니다.' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadTasks()
})
</script>
