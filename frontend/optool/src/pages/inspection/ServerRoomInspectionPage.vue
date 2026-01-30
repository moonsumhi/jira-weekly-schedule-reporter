<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">서버실 점검표</div>
      <q-space />

      <q-toggle v-model="includeDeleted" label="삭제 포함" dense />

      <q-btn
        outline
        icon="refresh"
        label="새로고침"
        :loading="loading"
        @click="load"
      />

      <q-btn
        color="primary"
        icon="add"
        label="점검표 추가"
        @click="openCreate"
      />
    </div>

    <q-card bordered>
      <!-- Filters -->
      <q-card-section class="row items-center q-gutter-sm">
        <q-input
          v-model="filter"
          dense
          outlined
          clearable
          debounce="200"
          placeholder="담당자 / 점검 결과 / 비고 검색"
          class="col"
        />
      </q-card-section>

      <q-separator />

      <!-- Table -->
      <q-card-section class="q-pa-none">
        <q-table
          :rows="filteredRows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="pagination"
          @update:pagination="onPagination"
          flat
          bordered
        >
          <!-- 점검 월 -->
          <template #body-cell-inspection_month="props">
            <q-td :props="props">
              <span class="text-weight-medium">{{ props.row.inspection_month }}</span>
            </q-td>
          </template>

          <!-- 자원사용량 이상 -->
          <template #body-cell-resource_usage_abnormal="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.resource_usage_abnormal ? 'negative' : 'positive'"
                outline
              >
                {{ props.row.resource_usage_abnormal ? '이상' : '정상' }}
              </q-badge>
            </q-td>
          </template>

          <!-- Actions -->
          <template #body-cell-actions="props">
            <q-td :props="props">
              <div class="row items-center justify-end q-gutter-xs">
                <q-btn
                  dense
                  outline
                  icon="edit"
                  label="수정"
                  :disable="Boolean(props.row.is_deleted)"
                  @click="openEdit(props.row)"
                />
                <q-btn
                  dense
                  outline
                  icon="history"
                  label="이력"
                  @click="openHistory(props.row)"
                />
                <q-btn
                  dense
                  color="negative"
                  icon="delete"
                  label="삭제"
                  :disable="Boolean(props.row.is_deleted)"
                  :loading="actingId === String(props.row.id) && actingType === 'delete'"
                  @click="confirmDelete(props.row)"
                />
              </div>
            </q-td>
          </template>

          <template #no-data>
            <div class="full-width row flex-center q-pa-lg text-grey-6">
              표시할 데이터가 없습니다.
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create dialog -->
    <q-dialog v-model="createDialog">
      <q-card style="width: 560px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">점검표 추가</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            월별 서버실 점검표를 작성합니다.
          </div>

          <q-input
            v-model="formData.inspection_month"
            outlined
            dense
            label="점검 월 (YYYY-MM)"
            mask="####-##"
            hint="예: 2026-01"
            class="q-mt-md"
          />
          <q-input
            v-model="formData.person_in_charge"
            outlined
            dense
            label="담당자"
            class="q-mt-sm"
          />
          <q-input
            v-model="formData.system_room_result"
            outlined
            dense
            label="시스템실 점검 결과"
            class="q-mt-sm"
          />
          <q-toggle
            v-model="formData.resource_usage_abnormal"
            label="자원사용량 이상"
            class="q-mt-sm"
          />
          <q-input
            v-model="formData.notes"
            outlined
            dense
            type="textarea"
            autogrow
            label="비고"
            class="q-mt-sm"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="생성"
            :loading="actingType === 'create'"
            @click="doCreate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit dialog -->
    <q-dialog v-model="editDialog">
      <q-card style="width: 560px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">점검표 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            점검 월: <b>{{ editFormData.inspection_month }}</b>
          </div>

          <q-input
            v-model="editFormData.person_in_charge"
            outlined
            dense
            label="담당자"
            class="q-mt-md"
          />
          <q-input
            v-model="editFormData.system_room_result"
            outlined
            dense
            label="시스템실 점검 결과"
            class="q-mt-sm"
          />
          <q-toggle
            v-model="editFormData.resource_usage_abnormal"
            label="자원사용량 이상"
            class="q-mt-sm"
          />
          <q-input
            v-model="editFormData.notes"
            outlined
            dense
            type="textarea"
            autogrow
            label="비고"
            class="q-mt-sm"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="저장"
            :loading="actingType === 'edit'"
            @click="doEdit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- History drawer -->
    <q-drawer
      v-model="historyOpen"
      side="right"
      bordered
      overlay
      :width="420"
    >
      <div class="q-pa-md">
        <div class="row items-center q-gutter-sm">
          <div class="text-h6">변경 이력</div>
          <q-space />
          <q-btn flat dense icon="close" @click="historyOpen = false" />
        </div>

        <div v-if="historyTarget" class="q-mt-sm text-caption text-grey-7">
          <div><b>점검 월</b>: {{ historyTarget.inspection_month }}</div>
          <div><b>담당자</b>: {{ historyTarget.person_in_charge }}</div>
          <div><b>ID</b>: {{ historyTarget.id }}</div>
        </div>

        <q-separator class="q-my-md" />

        <q-inner-loading :showing="historyLoading">
          <q-spinner size="32px" />
        </q-inner-loading>

        <q-list v-if="!historyLoading">
          <q-item v-for="h in historyItems" :key="h.id" clickable>
            <q-item-section>
              <q-item-label>
                <q-badge
                  :color="historyBadgeColor(h.action)"
                  outline
                  class="q-mr-sm"
                >
                  {{ h.action }}
                </q-badge>
                <span class="text-caption">
                  {{ formatKst(h.changed_at) }}
                </span>
              </q-item-label>
              <q-item-label caption>
                by {{ h.changed_by }}
              </q-item-label>

              <div v-if="h.diff?.length" class="q-mt-sm">
                <div class="text-caption text-grey-7 q-mb-xs">Changes</div>
                <div
                  v-for="d in h.diff.slice(0, 6)"
                  :key="d.path"
                  class="text-body2"
                >
                  <span class="text-grey-8">{{ d.path }}</span>
                  <span class="text-grey-6">: </span>
                  <span class="text-grey-9">{{ displayValue(d.before) }}</span>
                  <span class="text-grey-6"> → </span>
                  <span class="text-grey-9">{{ displayValue(d.after) }}</span>
                </div>
                <div
                  v-if="h.diff.length > 6"
                  class="text-caption text-grey-6 q-mt-xs"
                >
                  +{{ h.diff.length - 6 }} more…
                </div>
              </div>
            </q-item-section>
          </q-item>

          <div v-if="historyItems.length === 0" class="text-grey-6 q-pa-md">
            이력이 없습니다.
          </div>
        </q-list>
      </div>
    </q-drawer>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive } from 'vue'
import { useQuasar, type QTableProps } from 'quasar'

import type {
  InspectionChecklist,
  InspectionChecklistCreate,
  InspectionHistory,
} from 'src/types/inspection'

import {
  listInspectionChecklists,
  createInspectionChecklist,
  patchInspectionChecklist,
  deleteInspectionChecklist,
  getInspectionHistory,
} from 'src/services/inspection'

import { getErrorMessage } from 'src/utils/http/error'
import { displayValue } from 'src/utils/format/value'
import { formatKst } from 'src/utils/time/kst'
import { historyBadgeColor } from 'src/utils/ui/badges'

const $q = useQuasar()

const loading = ref(false)
const rows = ref<InspectionChecklist[]>([])
const includeDeleted = ref(false)

const filter = ref('')

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  page: 1,
  rowsPerPage: 10,
  sortBy: 'inspection_month',
  descending: true,
})

function onPagination(p: NonNullable<QTableProps['pagination']>) {
  pagination.value = p
}

const columns: NonNullable<QTableProps['columns']> = [
  {
    name: 'inspection_month',
    label: '점검 월',
    field: 'inspection_month',
    align: 'left',
    sortable: true,
  },
  {
    name: 'person_in_charge',
    label: '담당자',
    field: 'person_in_charge',
    align: 'left',
    sortable: true,
  },
  {
    name: 'system_room_result',
    label: '시스템실 점검 결과',
    field: 'system_room_result',
    align: 'left',
    sortable: false,
  },
  {
    name: 'resource_usage_abnormal',
    label: '자원사용량 이상',
    field: 'resource_usage_abnormal',
    align: 'center',
    sortable: true,
  },
  {
    name: 'notes',
    label: '비고',
    field: 'notes',
    align: 'left',
    sortable: false,
  },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

const filteredRows = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return rows.value

  return rows.value.filter((r) => {
    if (r.person_in_charge.toLowerCase().includes(q)) return true
    if (r.system_room_result.toLowerCase().includes(q)) return true
    if (r.notes?.toLowerCase().includes(q)) return true
    if (r.inspection_month.includes(q)) return true
    return false
  })
})

async function load() {
  loading.value = true
  try {
    rows.value = await listInspectionChecklists(includeDeleted.value)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

/** Create */
const createDialog = ref(false)
const formData = reactive<InspectionChecklistCreate>({
  inspection_month: '',
  person_in_charge: '',
  system_room_result: '',
  resource_usage_abnormal: false,
  notes: '',
})

const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'edit' | 'delete' | null>(null)

function openCreate() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  formData.inspection_month = `${year}-${month}`
  formData.person_in_charge = ''
  formData.system_room_result = ''
  formData.resource_usage_abnormal = false
  formData.notes = ''
  createDialog.value = true
}

async function doCreate() {
  const month = formData.inspection_month.trim()
  const personInCharge = formData.person_in_charge.trim()
  const result = formData.system_room_result.trim()

  if (!month || !personInCharge || !result) {
    $q.notify({ type: 'warning', message: '점검 월, 담당자, 점검 결과는 필수입니다.' })
    return
  }

  actingType.value = 'create'
  try {
    const created = await createInspectionChecklist({
      inspection_month: month,
      person_in_charge: personInCharge,
      system_room_result: result,
      resource_usage_abnormal: formData.resource_usage_abnormal,
      notes: formData.notes || null,
    })
    rows.value = [created, ...rows.value]
    createDialog.value = false
    $q.notify({ type: 'positive', message: '생성 완료' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '생성 실패') })
  } finally {
    actingType.value = null
  }
}

/** Edit */
const editDialog = ref(false)
const selectedRow = ref<InspectionChecklist | null>(null)
const editFormData = reactive({
  inspection_month: '',
  person_in_charge: '',
  system_room_result: '',
  resource_usage_abnormal: false,
  notes: '' as string | null,
})

function openEdit(row: InspectionChecklist) {
  selectedRow.value = row
  editFormData.inspection_month = row.inspection_month
  editFormData.person_in_charge = row.person_in_charge
  editFormData.system_room_result = row.system_room_result
  editFormData.resource_usage_abnormal = row.resource_usage_abnormal
  editFormData.notes = row.notes || ''
  editDialog.value = true
}

async function doEdit() {
  if (!selectedRow.value) return

  const personInCharge = editFormData.person_in_charge.trim()
  const result = editFormData.system_room_result.trim()

  if (!personInCharge || !result) {
    $q.notify({ type: 'warning', message: '담당자, 점검 결과는 필수입니다.' })
    return
  }

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'edit'
  try {
    const updated = await patchInspectionChecklist(selectedRow.value.id, {
      person_in_charge: personInCharge,
      system_room_result: result,
      resource_usage_abnormal: editFormData.resource_usage_abnormal,
      notes: editFormData.notes || null,
    })
    rows.value = rows.value.map((r) =>
      r.id === selectedRow.value!.id ? updated : r
    )
    editDialog.value = false
    $q.notify({ type: 'positive', message: '저장됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** Delete */
function confirmDelete(row: InspectionChecklist) {
  $q.dialog({
    title: '삭제',
    message: `정말 삭제하시겠습니까?\n${row.inspection_month} / ${row.person_in_charge}`,
    cancel: true,
    persistent: true,
  }).onOk(() => void doDelete(row))
}

async function doDelete(row: InspectionChecklist) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    await deleteInspectionChecklist(row.id)
    rows.value = rows.value.map((r) =>
      r.id === row.id ? { ...r, is_deleted: true } : r
    )
    $q.notify({ type: 'info', message: '삭제됨(soft delete)' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '삭제 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** History */
const historyOpen = ref(false)
const historyTarget = ref<InspectionChecklist | null>(null)
const historyLoading = ref(false)
const historyItems = ref<InspectionHistory[]>([])

async function loadHistory(checklistId: string) {
  historyLoading.value = true
  try {
    historyItems.value = await getInspectionHistory(checklistId)
  } catch (err: unknown) {
    historyItems.value = []
    $q.notify({ type: 'negative', message: getErrorMessage(err, '이력 조회 실패') })
  } finally {
    historyLoading.value = false
  }
}

function openHistory(row: InspectionChecklist) {
  historyTarget.value = row
  historyItems.value = []
  historyOpen.value = true
  void loadHistory(row.id)
}

onMounted(() => void load())
</script>
