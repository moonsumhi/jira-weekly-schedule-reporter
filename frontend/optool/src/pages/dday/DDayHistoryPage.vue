<template>
  <q-page class="q-pa-md dday-history-page">
    <div class="row items-center q-gutter-sm q-mb-md">
      <q-icon name="event_available" color="primary" size="28px" />
      <div>
        <div class="text-h5">D-day 이력</div>
        <div class="text-caption text-grey-7">완료 처리된 D-day를 확인할 수 있습니다.</div>
      </div>
      <q-space />
      <q-btn flat no-caps icon="arrow_back" label="대시보드" to="/app" />
      <q-btn flat round icon="refresh" :loading="loading" aria-label="새로고침" @click="loadHistory">
        <q-tooltip>새로고침</q-tooltip>
      </q-btn>
    </div>

    <q-card flat bordered>
      <q-card-section class="row items-center q-gutter-sm q-pb-sm">
        <div class="text-subtitle1 text-weight-medium">완료 내역</div>
        <q-badge color="grey-3" text-color="grey-8" :label="`${rows.length}건`" />
        <q-space />
        <q-input
          v-model="filter"
          dense outlined clearable
          placeholder="이름 또는 메모 검색"
          style="width: min(320px, 100%)"
        >
          <template #prepend><q-icon name="search" /></template>
        </q-input>
      </q-card-section>

      <q-table
        :rows="rows"
        :columns="columns"
        table-style="table-layout: fixed; width: 100%;"
        :filter="filter"
        row-key="id"
        flat
        :loading="loading"
        v-model:pagination="pagination"
        :rows-per-page-options="[10, 20, 50]"
        no-data-label="완료 처리된 D-day 이력이 없습니다."
      >
        <template #header-cell="headerProps">
          <q-th
            :props="{ ...headerProps, col: { ...headerProps.col, sortable: false } }"
            @click="headerProps.col.sortable && headerProps.sort(headerProps.col)"
          >
            <span class="dday-header-label">
              {{ headerProps.col.label }}
              <q-icon
                v-if="headerProps.col.sortable"
                :name="$q.iconSet.table.arrowUp"
                class="dday-header-sort-icon"
                :class="{
                  'dday-header-sort-icon--active': headerProps.col.name === pagination.sortBy,
                  'dday-header-sort-icon--descending': headerProps.col.name === pagination.sortBy && pagination.descending,
                }"
              />
            </span>
          </q-th>
        </template>
        <template #body-cell-date="slotProps">
          <q-td :props="slotProps" class="text-no-wrap dday-date-cell">
            {{ slotProps.row.date }}
          </q-td>
        </template>
        <template #body-cell-completedAt="slotProps">
          <q-td :props="slotProps" class="text-no-wrap">
            {{ formatDate(slotProps.row.completedAt) }}
            <q-badge
              v-if="completionOffsetDays(slotProps.row) !== null"
              class="q-ml-sm"
              outline
              :color="completionOffsetColor(completionOffsetDays(slotProps.row))"
              :label="`(${completionOffsetLabel(completionOffsetDays(slotProps.row))}일)`"
            >
              <q-tooltip>{{ completionOffsetDescription(completionOffsetDays(slotProps.row)) }}</q-tooltip>
            </q-badge>
          </q-td>
        </template>
      </q-table>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { QTableProps } from 'quasar'
import { useQuasar } from 'quasar'
import { fetchDDayHistory, type DDay } from 'src/services/ddays'

const $q = useQuasar()
const rows = ref<DDay[]>([])
const loading = ref(false)
const filter = ref('')
const pagination = ref({ sortBy: 'completedAt', descending: true, rowsPerPage: 20 })

const columns: NonNullable<QTableProps['columns']> = [
  {
    name: 'title', label: '이름', field: 'title', align: 'left', sortable: true,
    style: 'width: 25%; min-width: 25%; max-width: 25%; text-align: left; padding-left: 32px; vertical-align: middle;',
    headerStyle: 'width: 25%; min-width: 25%; max-width: 25%; text-align: left; padding-left: 32px; vertical-align: middle;',
  },
  {
    // ISO-formatted dates sort chronologically as strings.
    name: 'date', label: 'D-day 날짜', field: 'date', align: 'center', sortable: true,
    style: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle; line-height: 1.4;',
    headerStyle: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle; line-height: 1.4;',
  },
  {
    name: 'note', label: '메모', field: (row: DDay) => row.note ?? '', align: 'center',
    style: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle;',
    headerStyle: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle;',
  },
  {
    name: 'completedAt', label: '처리일', field: (row: DDay) => row.completedAt ?? '', align: 'center', sortable: true,
    style: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle;',
    headerStyle: 'width: 25%; min-width: 25%; max-width: 25%; text-align: center; vertical-align: middle;',
  },
]

function formatDate(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

function dateOnlyKey(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const key = Date.UTC(year, month - 1, day)
  const parsed = new Date(key)
  if (parsed.getUTCFullYear() !== year || parsed.getUTCMonth() !== month - 1 || parsed.getUTCDate() !== day) return null
  return key
}

function completionOffsetDays(dday: DDay): number | null {
  if (!dday.completedAt) return null
  const targetKey = dateOnlyKey(dday.date)
  const completedAt = new Date(dday.completedAt)
  if (targetKey === null || Number.isNaN(completedAt.getTime())) return null

  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(completedAt)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value
  const year = Number(part('year'))
  const month = Number(part('month'))
  const day = Number(part('day'))
  if (!year || !month || !day) return null
  const completedKey = Date.UTC(year, month - 1, day)
  return Math.round((completedKey - targetKey) / 86_400_000)
}

function completionOffsetLabel(offset: number | null): string {
  if (offset === null) return ''
  return offset > 0 ? `+${offset}` : String(offset)
}

function completionOffsetColor(offset: number | null): string {
  if (offset === null || offset === 0) return 'grey-7'
  return offset < 0 ? 'positive' : 'negative'
}

function completionOffsetDescription(offset: number | null): string {
  if (offset === null) return ''
  if (offset < 0) return `예정일보다 ${Math.abs(offset)}일 일찍 완료`
  if (offset > 0) return `예정일보다 ${offset}일 늦게 완료`
  return '예정일 당일 완료'
}

async function loadHistory() {
  loading.value = true
  try {
    rows.value = await fetchDDayHistory()
  } catch {
    $q.notify({ type: 'negative', message: 'D-day 이력을 불러오지 못했습니다.' })
  } finally {
    loading.value = false
  }
}

onMounted(() => void loadHistory())
</script>

<style scoped>
.dday-header-label {
  position: relative;
  display: inline-block;
  white-space: nowrap;
}

.dday-header-sort-icon {
  position: absolute;
  top: 50%;
  left: calc(100% + 4px);
  transform: translateY(-50%);
  opacity: 0.45;
  pointer-events: none;
}

.dday-header-label:hover .dday-header-sort-icon,
.dday-header-sort-icon--active {
  opacity: 0.9;
}

.dday-header-sort-icon--descending {
  transform: translateY(-50%) rotate(180deg);
}

.dday-date-cell {
  width: 150px;
  min-width: 150px;
  text-align: center !important;
  vertical-align: middle;
  line-height: 1.4;
}
</style>
