<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">계정 승인 관리</div>
      <q-space />
      <q-btn
        outline
        icon="refresh"
        label="새로고침"
        :loading="loading"
        @click="load"
      />
    </div>

    <q-card bordered>
      <q-card-section class="row items-center q-gutter-sm">
        <q-input
          v-model="filter"
          dense
          outlined
          clearable
          debounce="200"
          placeholder="이메일/이름 검색"
          class="col"
        />
        <q-select
          v-model="statusFilter"
          dense
          outlined
          :options="statusOptions"
          emit-value
          map-options
          label="상태"
          style="width: 180px"
        />
      </q-card-section>

      <q-separator />

      <q-card-section class="q-pa-none">
        <q-table
          :rows="filteredRows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="pagination"
          @update:pagination="pagination = $event"
          flat
          bordered
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row.status)" outline>
                {{ statusLabel(props.row.status) }}
              </q-badge>
            </q-td>
          </template>

          <template #body-cell-actions="props">
            <q-td :props="props" class="q-gutter-xs">
              <q-btn
                dense
                color="positive"
                icon="check"
                label="승인"
                :disable="props.row.status !== 'PENDING'"
                :loading="actingId === props.row.id && actingType === 'approve'"
                @click="openApprove(props.row)"
              />
              <q-btn
                dense
                color="negative"
                icon="close"
                label="반려"
                :disable="props.row.status !== 'PENDING'"
                :loading="actingId === props.row.id && actingType === 'reject'"
                @click="openReject(props.row)"
              />
            </q-td>
          </template>

          <template #no-data>
            <div class="full-width row flex-center q-pa-lg text-grey-6">
              승인 대기 계정이 없습니다.
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Approve dialog -->
    <q-dialog v-model="approveDialog">
      <q-card style="width: 520px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">승인 확인</div>
          <div class="text-body2 text-grey-7 q-mt-sm">
            아래 계정을 승인하시겠습니까?
          </div>

          <q-list bordered class="q-mt-md">
            <q-item>
              <q-item-section>
                <q-item-label><b>Email</b></q-item-label>
                <q-item-label caption>{{ selected?.email }}</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                <q-item-label><b>Name</b></q-item-label>
                <q-item-label caption>{{ selected?.full_name || '-' }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="positive"
            label="승인"
            :loading="actingType === 'approve' && actingId === selected?.id"
            @click="doApprove"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reject dialog -->
    <q-dialog v-model="rejectDialog">
      <q-card style="width: 560px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">반려 확인</div>
          <div class="text-body2 text-grey-7 q-mt-sm">
            아래 계정을 반려하시겠습니까? (선택) 사유를 남길 수 있습니다.
          </div>

          <q-list bordered class="q-mt-md">
            <q-item>
              <q-item-section>
                <q-item-label><b>Email</b></q-item-label>
                <q-item-label caption>{{ selected?.email }}</q-item-label>
              </q-item-section>
            </q-item>
            <q-item>
              <q-item-section>
                <q-item-label><b>Name</b></q-item-label>
                <q-item-label caption>{{ selected?.full_name || '-' }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <q-input
            v-model="rejectReason"
            class="q-mt-md"
            type="textarea"
            outlined
            autogrow
            label="반려 사유 (선택)"
            placeholder="예: 소속 확인 필요 / 이메일 도메인 정책 위반 등"
          />
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="negative"
            label="반려"
            :loading="actingType === 'reject' && actingId === selected?.id"
            @click="doReject"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

import { getErrorMessage } from 'src/utils/http/error'

import type { QTableProps } from 'quasar'

type PendingStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

type PendingUser = {
  id: string | number
  email: string
  full_name?: string | null
  status: PendingStatus
  requested_at?: string // ISO
}

type StatusFilter = PendingStatus | 'ALL'

type StatusOption = {
  label: string
  value: StatusFilter
}

const $q = useQuasar()

const loading = ref(false)
const rows = ref<PendingUser[]>([])

const filter = ref('')

const statusFilter = ref<StatusFilter>('PENDING')

const statusOptions: StatusOption[] = [
  { label: '전체', value: 'ALL' },
  { label: '대기', value: 'PENDING' },
  { label: '승인', value: 'APPROVED' },
  { label: '반려', value: 'REJECTED' },
]

const pagination = ref<QTableProps['pagination']>({
  page: 1,
  rowsPerPage: 10,
  sortBy: 'requested_at',
  descending: true,
})

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'email', label: 'Email', field: 'email', align: 'left', sortable: true },
  { name: 'full_name', label: 'Name', field: 'full_name', align: 'left', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'left', sortable: true },
  { name: 'requested_at', label: 'Requested At', field: 'requested_at', align: 'left', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

function statusLabel(s: PendingStatus) {
  if (s === 'PENDING') return '대기'
  if (s === 'APPROVED') return '승인'
  return '반려'
}
function statusColor(s: PendingStatus) {
  if (s === 'PENDING') return 'warning'
  if (s === 'APPROVED') return 'positive'
  return 'negative'
}

const filteredRows = computed(() => {
  const q = filter.value.trim().toLowerCase()
  return rows.value.filter((r) => {
    const passStatus = statusFilter.value === 'ALL' ? true : r.status === statusFilter.value
    const passText =
      !q ||
      r.email.toLowerCase().includes(q) ||
      (r.full_name || '').toLowerCase().includes(q)
    return passStatus && passText
  })
})

async function load() {
  loading.value = true
  try {
    // ✅ change this endpoint if your backend differs
    const res = await api.get<PendingUser[]>('/admin/users/pending')
    rows.value = res.data
  } catch (e: unknown) {
    $q.notify({
      type: 'negative',
      message: getErrorMessage(e, '승인 대기 목록 조회 실패'),
    })
  } finally {
    loading.value = false
  }
}

const approveDialog = ref(false)
const rejectDialog = ref(false)
const selected = ref<PendingUser | null>(null)
const rejectReason = ref('')

const actingId = ref<string | number | null>(null)
const actingType = ref<'approve' | 'reject' | null>(null)

function openApprove(user: PendingUser) {
  selected.value = user
  approveDialog.value = true
}

function openReject(user: PendingUser) {
  selected.value = user
  rejectReason.value = ''
  rejectDialog.value = true
}

async function doApprove() {
  if (!selected.value) return
  actingId.value = selected.value.id
  actingType.value = 'approve'
  try {
    await api.post(`/admin/users/${selected.value.id}/approve`)
    $q.notify({ type: 'positive', message: '승인 완료' })
    approveDialog.value = false
    // update locally (or reload)
    rows.value = rows.value.map((r) =>
      r.id === selected.value!.id ? { ...r, status: 'APPROVED' } : r
    )
  } catch (e: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '승인 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

async function doReject() {
  if (!selected.value) return
  actingId.value = selected.value.id
  actingType.value = 'reject'
  try {
    await api.post(`/admin/users/${selected.value.id}/reject`, {
      reason: rejectReason.value || null,
    })
    $q.notify({ type: 'info', message: '반려 완료' })
    rejectDialog.value = false
    rows.value = rows.value.map((r) =>
      r.id === selected.value!.id ? { ...r, status: 'REJECTED' } : r
    )
  } catch (e: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '반려 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

onMounted(() => {
  void load()
})
</script>
