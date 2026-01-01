<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">서버 자산 관리</div>
      <q-space />

      <q-toggle
        v-model="includeDeleted"
        label="삭제 포함"
        dense
      />

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
        label="서버 추가"
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
          placeholder="IP / 이름 / 필드 검색"
          class="col"
        />

        <q-select
          v-model="visibleKeys"
          dense
          outlined
          multiple
          use-chips
          emit-value
          map-options
          :options="fieldKeyOptions"
          label="표시할 필드"
          style="min-width: 260px;"
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
          <!-- IP inline edit -->
          <template #body-cell-ip="props">
            <q-td :props="props">
              <div class="row items-center q-gutter-xs">
                <span class="text-mono">{{ props.row.ip }}</span>
                <q-btn
                  flat dense round icon="edit" size="sm"
                  @click="openEditBase(props.row, 'ip')"
                />
              </div>
            </q-td>
          </template>

          <!-- NAME inline edit -->
          <template #body-cell-name="props">
            <q-td :props="props">
              <div class="row items-center q-gutter-xs">
                <span>{{ props.row.name }}</span>
                <q-btn
                  flat dense round icon="edit" size="sm"
                  @click="openEditBase(props.row, 'name')"
                />
              </div>
            </q-td>
          </template>

          <!-- Dynamic fields -->
          <template #body-cell-field="props">
            <q-td :props="props">
              <!-- EOS action badge -->
              <template v-if="colKey(props.col) === EOS_STATUS_KEY">
                <q-badge :color="eosStatusColor(getField(props.row, EOS_STATUS_KEY))" outline>
                  {{ eosStatusLabel(getField(props.row, EOS_STATUS_KEY)) }}
                </q-badge>

                <q-btn
                  flat dense round icon="edit" size="sm" class="q-ml-xs"
                  @click="openEditField(props.row, EOS_STATUS_KEY)"
                />
              </template>

              <!-- EOS date + soon warning -->
              <template v-else-if="colKey(props.col) === EOS_DATE_KEY">
                <span>{{ displayValue(getField(props.row, EOS_DATE_KEY)) }}</span>
                <q-icon
                  v-if="isDateSoon(getField(props.row, EOS_DATE_KEY), eosSoonDays)"
                  name="warning"
                  class="q-ml-xs text-warning"
                />
                <q-btn
                  flat dense round icon="edit" size="sm" class="q-ml-xs"
                  @click="openEditField(props.row, EOS_DATE_KEY)"
                />
              </template>

              <!-- Normal dynamic field -->
              <template v-else>
                <span>{{ displayValue(getField(props.row, colKey(props.col))) }}</span>
                <q-btn
                  flat dense round icon="edit" size="sm" class="q-ml-xs"
                  @click="openEditField(props.row, colKey(props.col))"
                />
              </template>
            </q-td>
          </template>

          <!-- Actions -->
          <template #body-cell-actions="props">
            <q-td :props="props">
              <div class="row items-center justify-end q-gutter-xs">
                <q-btn
                  dense
                  outline
                  icon="history"
                  label="이력"
                  @click="openHistory(props.row)"
                />
                <q-btn
                  dense
                  outline
                  icon="add"
                  label="필드"
                  @click="openAddField(props.row)"
                />
                <q-btn
                  dense
                  color="negative"
                  icon="delete"
                  label="삭제"
                  :disable="Boolean(props.row.isDeleted)"
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
      <q-card style="width: 520px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">서버 추가</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            필수: IP, 이름/설명. 나머지는 서버 생성 후 필드로 추가하세요.
          </div>

          <q-input v-model="createIp" outlined dense label="IP" class="q-mt-md" />
          <q-input v-model="createName" outlined dense label="Name/Desc" class="q-mt-sm" />
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

    <!-- Edit base (ip/name) dialog -->
    <q-dialog v-model="editBaseDialog">
      <q-card style="width: 520px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">기본 정보 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            {{ editingBaseKey === 'ip' ? 'IP' : 'Name/Desc' }} 수정
          </div>

          <q-input
            v-model="editBaseValue"
            outlined
            dense
            :label="editingBaseKey === 'ip' ? 'IP' : 'Name/Desc'"
            class="q-mt-md"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="저장"
            :loading="actingType === 'editBase' && actingId === (selectedRow ? String(selectedRow.id) : null)"
            @click="doEditBase"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit field dialog -->
    <q-dialog v-model="editFieldDialog">
      <q-card style="width: 560px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">필드 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Key: <b>{{ editFieldKey }}</b>
          </div>

          <!-- EOS status select -->
          <template v-if="editFieldKey === EOS_STATUS_KEY">
            <q-select
              v-model="editFieldValue"
              outlined
              dense
              emit-value
              map-options
              :options="eosStatusOptions"
              label="EOS 조치 상태"
              class="q-mt-md"
            />
          </template>

          <!-- others: textarea for flexible -->
          <template v-else>
            <q-input
              v-model="editFieldText"
              type="textarea"
              outlined
              autogrow
              label="값"
              class="q-mt-md"
              hint="문자/숫자/boolean/JSON 모두 가능 (JSON은 그대로 입력)"
            />
          </template>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="저장"
            :loading="actingType === 'editField' && actingId === (selectedRow ? String(selectedRow.id) : null)"
            @click="doEditField"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add field dialog -->
    <q-dialog v-model="addFieldDialog">
      <q-card style="width: 600px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">필드 추가</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            서버: <b>{{ selectedRow?.ip }}</b> / {{ selectedRow?.name }}
          </div>

          <q-input v-model="addFieldKey" outlined dense label="Field Key" class="q-mt-md" />
          <q-input
            v-model="addFieldText"
            type="textarea"
            outlined
            autogrow
            label="Value"
            class="q-mt-sm"
            hint="예: NCC-SRV-000123 / DONE / 2026-12-31 / JSON 가능"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="추가"
            :loading="actingType === 'addField' && actingId === (selectedRow?.id ?? null)"
            @click="doAddField"
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
          <div><b>IP</b>: {{ historyTarget.ip }}</div>
          <div><b>Name</b>: {{ historyTarget.name }}</div>
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
                  {{ formatKst(h.changedAt) }}
                </span>
              </q-item-label>
              <q-item-label caption>
                by {{ h.changedBy }}
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
                <div v-if="h.diff.length > 6" class="text-caption text-grey-6 q-mt-xs">
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
import { computed, onMounted, ref } from 'vue'
import { useQuasar, type QTableProps } from 'quasar'

import type { ServerAsset, AssetHistory, FieldsMap, FieldValue, EosActionStatus } from 'src/types/assets'
import { EOS_STATUS_KEY, EOS_DATE_KEY, eosStatusOptions } from 'src/types/assets'

import { listServers, createServer, patchServer, deleteServer, getServerHistory } from 'src/services/assets'

import { getErrorMessage } from 'src/utils/http/error'
import { displayValue } from 'src/utils/format/value'
import { parseSmartValue } from 'src/utils/parse/smartValue'
import { formatKst, isDateSoon } from 'src/utils/time/kst'
import { eosStatusColor, eosStatusLabel, normalizeEosStatus } from 'src/utils/rules/eos'
import { historyBadgeColor } from 'src/utils/ui/badges'

const $q = useQuasar()

const eosSoonDays = 90

const loading = ref(false)
const rows = ref<ServerAsset[]>([])
const includeDeleted = ref(false)

const filter = ref('')

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  page: 1,
  rowsPerPage: 10,
  sortBy: 'ip',
  descending: false,
})

function onPagination(p: NonNullable<QTableProps['pagination']>) {
  pagination.value = p
}

function getField(row: ServerAsset, key: string): FieldValue | undefined {
  return row.fields?.[key]
}

const allFieldKeys = computed<string[]>(() => {
  const set = new Set<string>()
  for (const r of rows.value) Object.keys(r.fields || {}).forEach((k) => set.add(k))

  const preferred = [EOS_STATUS_KEY, EOS_DATE_KEY, 'asset_tag']
  const rest = Array.from(set).filter((k) => !preferred.includes(k)).sort()
  return preferred.filter((k) => set.has(k)).concat(rest)
})

const fieldKeyOptions = computed(() => allFieldKeys.value.map((k) => ({ label: k, value: k })))
const visibleKeys = ref<string[]>([])

const shownFieldKeys = computed(() => {
  if (visibleKeys.value.length === 0) return allFieldKeys.value
  const picked = new Set(visibleKeys.value)
  return allFieldKeys.value.filter((k) => picked.has(k))
})

type ColumnWithFieldKey = {
  name: string
  label: string
  fieldKey?: string
}

function colKey(col: unknown): string {
  if (typeof col === 'object' && col !== null) {
    const c = col as ColumnWithFieldKey
    return c.fieldKey ?? c.label
  }
  return ''
}

const columns = computed<NonNullable<QTableProps['columns']>>(() => {
  const base: NonNullable<QTableProps['columns']> = [
    { name: 'ip', label: 'IP', field: 'ip', align: 'left', sortable: true },
    { name: 'name', label: 'Name/Desc', field: 'name', align: 'left', sortable: true },
  ]

  const dyn = shownFieldKeys.value.map((k) => ({
    name: 'field',
    label: k,
    field: (row: unknown) => {
      if (typeof row === 'object' && row !== null) {
        const r = row as { fields?: Record<string, unknown> }
        return r.fields?.[k]
      }
      return undefined
    },
    align: 'left' as const,
    sortable: true,
    fieldKey: k,
  }))

  const tail: NonNullable<QTableProps['columns']> = [
    { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
  ]

  return [...base, ...dyn, ...tail]
})

const filteredRows = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return rows.value
  const keys = shownFieldKeys.value

  return rows.value.filter((r) => {
    if (r.ip.toLowerCase().includes(q)) return true
    if (r.name.toLowerCase().includes(q)) return true
    for (const k of keys) {
      const v = r.fields?.[k]
      if (displayValue(v).toLowerCase().includes(q)) return true
    }
    return false
  })
})

async function load() {
  loading.value = true
  try {
    rows.value = await listServers(includeDeleted.value)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

/** Create */
const createDialog = ref(false)
const createIp = ref('')
const createName = ref('')

const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'editBase' | 'editField' | 'addField' | 'delete' | null>(null)

function openCreate() {
  createIp.value = ''
  createName.value = ''
  createDialog.value = true
}

async function doCreate() {
  const ip = createIp.value.trim()
  const name = createName.value.trim()
  if (!ip || !name) {
    $q.notify({ type: 'warning', message: 'IP와 Name/Desc는 필수입니다.' })
    return
  }

  actingType.value = 'create'
  try {
    const created = await createServer(ip, name)
    rows.value = [created, ...rows.value]
    createDialog.value = false
    $q.notify({ type: 'positive', message: '생성 완료' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '생성 실패') })
  } finally {
    actingType.value = null
  }
}

/** Edit base */
const editBaseDialog = ref(false)
const selectedRow = ref<ServerAsset | null>(null)
const editingBaseKey = ref<'ip' | 'name'>('name')
const editBaseValue = ref('')

function openEditBase(row: ServerAsset, key: 'ip' | 'name') {
  selectedRow.value = row
  editingBaseKey.value = key
  editBaseValue.value = key === 'ip' ? row.ip : row.name
  editBaseDialog.value = true
}

async function doEditBase() {
  if (!selectedRow.value) return
  const key = editingBaseKey.value
  const val = editBaseValue.value.trim()
  if (!val) {
    $q.notify({ type: 'warning', message: '값을 입력하세요.' })
    return
  }

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'editBase'
  try {
    const updated = await patchServer(String(selectedRow.value.id), { [key]: val })
    rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
    editBaseDialog.value = false
    $q.notify({ type: 'positive', message: '저장됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** Edit field */
const editFieldDialog = ref(false)
const editFieldKey = ref('')
const editFieldValue = ref<EosActionStatus | null>(null)
const editFieldText = ref('')

function openEditField(row: ServerAsset, key: string) {
  selectedRow.value = row
  editFieldKey.value = key

  const current = row.fields?.[key]
  if (key === EOS_STATUS_KEY) {
    editFieldValue.value = normalizeEosStatus(current)
    editFieldText.value = ''
  } else {
    editFieldText.value = typeof current === 'string' ? current : displayValue(current)
    editFieldValue.value = null
  }

  editFieldDialog.value = true
}

async function doEditField() {
  if (!selectedRow.value) return
  const key = editFieldKey.value.trim()
  if (!key) return

  const value: FieldValue =
    key === EOS_STATUS_KEY ? (editFieldValue.value ?? null) : parseSmartValue(editFieldText.value)

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'editField'
  try {
    const nextFields: FieldsMap = { ...(selectedRow.value.fields || {}) }
    nextFields[key] = value
    const updated = await patchServer(String(selectedRow.value.id), { fields: nextFields })
    rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
    editFieldDialog.value = false
    $q.notify({ type: 'positive', message: '저장됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** Add field */
const addFieldDialog = ref(false)
const addFieldKey = ref('')
const addFieldText = ref('')

function openAddField(row: ServerAsset) {
  selectedRow.value = row
  addFieldKey.value = ''
  addFieldText.value = ''
  addFieldDialog.value = true
}

async function doAddField() {
  if (!selectedRow.value) return
  const key = addFieldKey.value.trim()
  if (!key) {
    $q.notify({ type: 'warning', message: 'Field Key는 필수입니다.' })
    return
  }

  const value = parseSmartValue(addFieldText.value)

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'addField'
  try {
    const nextFields: FieldsMap = { ...(selectedRow.value.fields || {}) }
    nextFields[key] = value
    const updated = await patchServer(selectedRow.value.id, { fields: nextFields })
    rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
    addFieldDialog.value = false
    $q.notify({ type: 'positive', message: '추가됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '추가 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** Delete */
function confirmDelete(row: ServerAsset) {
  $q.dialog({
    title: '삭제',
    message: `정말 삭제하시겠습니까?\n${row.ip} / ${row.name}`,
    cancel: true,
    persistent: true,
  }).onOk(() => void doDelete(row))
}

async function doDelete(row: ServerAsset) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    await deleteServer(row.id)
    rows.value = rows.value.map((r) => (r.id === row.id ? { ...r, isDeleted: true } : r))
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
const historyTarget = ref<ServerAsset | null>(null)
const historyLoading = ref(false)
const historyItems = ref<AssetHistory[]>([])

async function loadHistory(assetId: string) {
  historyLoading.value = true
  try {
    historyItems.value = await getServerHistory(assetId)
  } catch (err: unknown) {
    historyItems.value = []
    $q.notify({ type: 'negative', message: getErrorMessage(err, '이력 조회 실패') })
  } finally {
    historyLoading.value = false
  }
}

function openHistory(row: ServerAsset) {
  historyTarget.value = row
  historyItems.value = []
  historyOpen.value = true
  void loadHistory(row.id)
}

onMounted(() => void load())
</script>
