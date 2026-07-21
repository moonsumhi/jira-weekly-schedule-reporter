<template>
  <div class="sr-filter-bar">

    <!-- ── 행 1: 통합 검색 + 검색/초기화 버튼 ───────────────────────────── -->
    <div class="row items-center q-gutter-sm q-mb-sm">
      <q-input
        v-model="localSearch"
        class="col"
        outlined dense clearable
        placeholder="SR 번호, 제목, 요청자 검색"
        bg-color="white"
        @keyup.enter="onApply"
      >
        <template #prepend>
          <q-icon name="search" color="grey-5" size="18px" />
        </template>
      </q-input>

      <q-btn
        unelevated color="primary"
        icon="search" label="검색"
        size="sm" class="q-px-md"
        :loading="loading"
        @click="onApply"
      />
      <q-btn
        flat dense size="sm"
        icon="refresh" color="grey-6"
        label="초기화"
        no-caps
        @click="onReset"
      />
    </div>

    <!-- ── 행 2: 상태 탭 칩 + 빠른 토글 ────────────────────────────────── -->
    <div class="row items-start justify-between q-mb-xs" style="gap:8px">
      <!-- 상태 칩 (가로 스크롤) -->
      <div class="status-chips-wrap">
        <q-chip
          v-for="s in statusOptions"
          :key="s.value"
          clickable dense
          :color="tabChipColor(s)"
          :text-color="tabChipTextColor(s)"
          :outline="tabChipState(s) === 'exclude'"
          style="margin: 2px 4px 2px 0"
          @click="onTabChange(s.value)"
        >
          <q-icon v-if="tabChipState(s) === 'exclude'" name="block" size="11px" class="q-mr-xs" />
          {{ s.label }}
          <q-tooltip v-if="s.value !== 'all'" anchor="bottom middle" self="top middle">
            {{ tabChipTooltip(s) }}
          </q-tooltip>
        </q-chip>
      </div>

      <!-- 빠른 토글: 긴급 / 지연 / 내 담당 -->
      <div class="row no-wrap" style="gap:4px; flex-shrink:0; padding-top:2px">
        <q-chip
          clickable dense
          :color="localFilter.isUrgent ? 'negative' : 'grey-2'"
          :text-color="localFilter.isUrgent ? 'white' : 'grey-7'"
          icon="priority_high"
          style="margin:2px"
          @click="onToggle('isUrgent')"
        >긴급</q-chip>
        <q-chip
          clickable dense
          :color="localFilter.isDelayed ? 'deep-orange-7' : 'grey-2'"
          :text-color="localFilter.isDelayed ? 'white' : 'grey-7'"
          icon="schedule"
          style="margin:2px"
          @click="onToggle('isDelayed')"
        >지연</q-chip>
        <q-chip
          clickable dense
          :color="localFilter.myAssigned ? 'primary' : 'grey-2'"
          :text-color="localFilter.myAssigned ? 'white' : 'grey-7'"
          icon="person_pin"
          style="margin:2px"
          @click="onToggle('myAssigned')"
        >내 담당</q-chip>
      </div>
    </div>

    <!-- ── 행 3: 적용된 필터 칩 ─────────────────────────────────────────── -->
    <q-slide-transition>
      <div v-if="activeChips.length" class="row items-center q-gutter-xs q-mb-xs">
        <q-chip
          v-for="chip in activeChips"
          :key="chip.key"
          dense removable
          color="indigo-1" text-color="indigo-9"
          size="sm"
          @remove="$emit('chip-remove', chip.key)"
        >
          <span class="text-weight-medium text-caption">{{ chip.label }}</span>
          <span v-if="chip.value !== 'ON'" class="text-caption q-ml-xs" style="opacity:0.65">{{ chip.value }}</span>
        </q-chip>
        <q-btn
          flat dense size="xs" color="grey-5"
          label="전체 초기화"
          class="text-caption"
          @click="onReset"
        />
      </div>
    </q-slide-transition>

    <!-- ── 행 4: 상세 필터 토글 + 프리셋 ───────────────────────────────── -->
    <div class="row items-center justify-between q-mb-xs">
      <q-btn
        flat dense size="sm"
        icon="tune"
        label="상세 필터"
        :class="expanded ? 'text-indigo-7' : 'text-grey-6'"
        no-caps class="q-px-xs"
        @click="expanded = !expanded"
      >
        <q-badge v-if="advancedFilterCount" color="indigo-7" :label="advancedFilterCount" class="q-ml-xs" />
      </q-btn>

      <q-btn-dropdown flat dense size="sm" icon="bookmark_border" color="grey-6" no-icon-animation>
        <template #label><span class="text-caption q-ml-xs">프리셋</span></template>
        <q-list dense style="min-width:190px">
          <q-item v-if="!presets.length" dense>
            <q-item-section class="text-grey-5 text-caption q-py-xs">저장된 프리셋 없음</q-item-section>
          </q-item>
          <q-item v-for="(p, i) in presets" :key="i" clickable v-close-popup @click="$emit('load-preset', p)">
            <q-item-section>{{ p.name }}</q-item-section>
            <q-item-section side>
              <q-btn flat round dense size="xs" icon="close" color="grey-5" @click.stop="$emit('remove-preset', i)" />
            </q-item-section>
          </q-item>
          <q-separator v-if="presets.length" />
          <q-item clickable v-close-popup @click="$emit('save-preset')">
            <q-item-section avatar><q-icon name="add" size="14px" /></q-item-section>
            <q-item-section>현재 필터 저장</q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
    </div>

    <!-- ── 상세 필터 패널 (접힘/펼침) ──────────────────────────────────── -->
    <q-slide-transition>
      <div v-show="expanded" class="advanced-panel">
        <q-separator class="q-mb-md" />

        <!-- 필터 그리드: md+ 3열, sm 2열, xs 1열 -->
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-12 col-sm-6 col-md-4">
            <q-input
              v-model="localFilter.requesterDepartment"
              label="요청 부서" outlined dense clearable bg-color="white"
            >
              <template #prepend><q-icon name="business" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-input
              v-model="localFilter.requesterName"
              label="요청자" outlined dense clearable bg-color="white"
            >
              <template #prepend><q-icon name="person" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-select
              v-model="localFilter.requestType"
              label="SR 유형" outlined dense clearable bg-color="white"
              :options="requestTypeOptions" emit-value map-options
            >
              <template #prepend><q-icon name="category" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-input
              v-model="localFilter.relatedSystem"
              label="관련 시스템" outlined dense clearable bg-color="white"
            >
              <template #prepend><q-icon name="computer" size="16px" color="grey-5" /></template>
            </q-input>
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-select
              v-model="localFilter.assigneeId"
              label="담당자" outlined dense clearable bg-color="white"
              :options="filteredUserOptions"
              emit-value map-options
              use-input fill-input hide-selected input-debounce="0"
              @filter="filterUsersFn"
            >
              <template #prepend><q-icon name="manage_accounts" size="16px" color="grey-5" /></template>
              <template #no-option>
                <q-item><q-item-section class="text-grey">없음</q-item-section></q-item>
              </template>
            </q-select>
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-select
              v-model="localFilter.priority"
              label="중요도" outlined dense clearable bg-color="white"
              :options="priorityOptions" emit-value map-options
            >
              <template #prepend><q-icon name="flag" size="16px" color="grey-5" /></template>
            </q-select>
          </div>
        </div>

        <!-- 날짜 필터 그리드: md+ 3열 -->
        <div class="row q-col-gutter-md">

          <!-- 접수일 -->
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-6 q-mb-xs">접수일</div>
            <div class="row q-gutter-xs q-mb-xs">
              <q-btn
                v-for="p in DATE_PRESETS" :key="p.value"
                flat dense size="xs" no-caps
                :color="isPresetActive('created', p.value) ? 'primary' : 'grey-5'"
                :label="p.label"
                @click="applyPreset('created', p.value)"
              />
            </div>
            <div class="row items-center no-wrap q-gutter-xs">
              <q-input v-model="localFilter.createdFrom" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
              <span class="text-grey-5">~</span>
              <q-input v-model="localFilter.createdTo" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
            </div>
            <div v-if="hasDateError('created')" class="text-negative text-caption q-mt-xs">
              시작일이 종료일보다 늦습니다.
            </div>
          </div>

          <!-- 희망완료일 -->
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-6 q-mb-xs">희망완료일</div>
            <div class="row q-gutter-xs q-mb-xs">
              <q-btn
                v-for="p in DATE_PRESETS" :key="p.value"
                flat dense size="xs" no-caps
                :color="isPresetActive('dueDate', p.value) ? 'primary' : 'grey-5'"
                :label="p.label"
                @click="applyPreset('dueDate', p.value)"
              />
            </div>
            <div class="row items-center no-wrap q-gutter-xs">
              <q-input v-model="localFilter.dueDateFrom" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
              <span class="text-grey-5">~</span>
              <q-input v-model="localFilter.dueDateTo" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
            </div>
            <div v-if="hasDateError('dueDate')" class="text-negative text-caption q-mt-xs">
              시작일이 종료일보다 늦습니다.
            </div>
          </div>

          <!-- 완료목표일 -->
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-6 q-mb-xs">완료목표일</div>
            <div class="row q-gutter-xs q-mb-xs">
              <q-btn
                v-for="p in DATE_PRESETS" :key="p.value"
                flat dense size="xs" no-caps
                :color="isPresetActive('plannedDate', p.value) ? 'primary' : 'grey-5'"
                :label="p.label"
                @click="applyPreset('plannedDate', p.value)"
              />
            </div>
            <div class="row items-center no-wrap q-gutter-xs">
              <q-input v-model="localFilter.plannedDueDateFrom" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
              <span class="text-grey-5">~</span>
              <q-input v-model="localFilter.plannedDueDateTo" type="date" outlined dense clearable bg-color="white" style="flex:1;min-width:0" />
            </div>
            <div v-if="hasDateError('plannedDate')" class="text-negative text-caption q-mt-xs">
              시작일이 종료일보다 늦습니다.
            </div>
          </div>
        </div>
      </div>
    </q-slide-transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { REQUEST_TYPE_OPTIONS, SR_PRIORITY_OPTIONS } from 'src/services/sr'
import type { PmUser } from 'src/services/pm/users'
import {
  SR_STATUS_TAB_OPTIONS,
  type SrFilterState,
  type SrFilterPreset,
  type SrActiveChip,
  defaultSrFilter,
} from '../useSrSearch'

// ── Props / Emits ─────────────────────────────────────────────────────────

interface Props {
  filter:      SrFilterState
  search:      string
  tab:         string[]
  loading:     boolean
  pmUsers:     PmUser[]
  presets:     SrFilterPreset[]
  activeChips: SrActiveChip[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  apply:           [filter: SrFilterState, search: string, tab: string[]]
  reset:           []
  'chip-remove':   [key: string]
  'save-preset':   []
  'load-preset':   [preset: SrFilterPreset]
  'remove-preset': [index: number]
}>()

// ── 로컬 편집 상태 (적용 전 드래프트) ────────────────────────────────────

const localFilter    = ref<SrFilterState>({ ...props.filter })
// q-input clearable은 지울 때 null을 emit하므로 string | null로 선언
const localSearch    = ref<string | null>(props.search ?? '')
const localStatuses  = ref<string[]>([...props.tab])
const expanded       = ref(false)

// 부모에서 filter/search/tab이 변경되면 로컬 상태도 동기화
watch(() => props.filter, (v) => { localFilter.value = { ...v } }, { deep: true })
watch(() => props.search, (v) => { localSearch.value = v ?? '' })
watch(() => props.tab,    (v) => { localStatuses.value = [...v] }, { deep: true })

// 고급 필터가 적용된 상태로 로드되면 패널 자동 열기
watch(
  () => props.activeChips,
  (chips) => {
    const hasAdvanced = chips.some(c => !['isUrgent', 'isDelayed', 'myAssigned'].includes(c.key))
    if (hasAdvanced) expanded.value = true
  },
  { immediate: true },
)

// ── 옵션 ─────────────────────────────────────────────────────────────────

const statusOptions      = SR_STATUS_TAB_OPTIONS
const requestTypeOptions = REQUEST_TYPE_OPTIONS
const priorityOptions    = SR_PRIORITY_OPTIONS

const filteredUsers = ref<PmUser[]>([])
watch(() => props.pmUsers, (v) => { filteredUsers.value = v }, { immediate: true })

const filteredUserOptions = computed(() =>
  filteredUsers.value.map(u => ({
    label: `${u.name}${u.email ? ` (${u.email})` : ''}`,
    value: u.id,
  })),
)

function filterUsersFn(val: string, update: (fn: () => void) => void) {
  update(() => {
    const q = val.toLowerCase()
    filteredUsers.value = q
      ? props.pmUsers.filter(u =>
          u.name.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q),
        )
      : props.pmUsers
  })
}

// ── 날짜 프리셋 ──────────────────────────────────────────────────────────

const DATE_PRESETS = [
  { label: '오늘',   value: 'today'     },
  { label: '7일',    value: '7d'        },
  { label: '30일',   value: '30d'       },
  { label: '이번달', value: 'thisMonth' },
  { label: '지난달', value: 'lastMonth' },
]

type DateField = 'created' | 'dueDate' | 'plannedDate'

function calcPreset(preset: string): { from: string; to: string } {
  const now  = new Date()
  const fmt  = (d: Date) => d.toISOString().slice(0, 10)
  let from = '', to = fmt(now)
  switch (preset) {
    case 'today':
      from = to
      break
    case '7d':
      from = fmt(new Date(now.getTime() - 7 * 86400000))
      break
    case '30d':
      from = fmt(new Date(now.getTime() - 30 * 86400000))
      break
    case 'thisMonth':
      from = fmt(new Date(now.getFullYear(), now.getMonth(), 1))
      break
    case 'lastMonth': {
      const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const last  = new Date(now.getFullYear(), now.getMonth(), 0)
      from = fmt(first)
      to   = fmt(last)
      break
    }
  }
  return { from, to }
}

function applyPreset(field: DateField, preset: string) {
  const { from, to } = calcPreset(preset)
  const f = localFilter.value
  if (field === 'created')      { f.createdFrom = from;         f.createdTo = to }
  else if (field === 'dueDate') { f.dueDateFrom = from;         f.dueDateTo = to }
  else                          { f.plannedDueDateFrom = from;  f.plannedDueDateTo = to }
}

function isPresetActive(field: DateField, preset: string): boolean {
  const { from, to } = calcPreset(preset)
  const f = localFilter.value
  if (field === 'created')      return f.createdFrom === from         && f.createdTo === to
  if (field === 'dueDate')      return f.dueDateFrom === from         && f.dueDateTo === to
  return f.plannedDueDateFrom === from && f.plannedDueDateTo === to
}

function hasDateError(field: DateField): boolean {
  const f = localFilter.value
  let from = '', to = ''
  if (field === 'created')      { from = f.createdFrom;         to = f.createdTo }
  else if (field === 'dueDate') { from = f.dueDateFrom;         to = f.dueDateTo }
  else                          { from = f.plannedDueDateFrom;  to = f.plannedDueDateTo }
  return !!(from && to && from > to)
}

// ── 상세 필터 활성 수 (로컬 드래프트 기준, 토글 제외) ────────────────────

const advancedFilterCount = computed(() => {
  const f = localFilter.value
  let n = 0
  if (f.requesterDepartment)                        n++
  if (f.requesterName)                              n++
  if (f.requestType)                                n++
  if (f.relatedSystem)                              n++
  if (f.assigneeId)                                 n++
  if (f.priority)                                   n++
  if (f.createdFrom || f.createdTo)                 n++
  if (f.dueDateFrom || f.dueDateTo)                 n++
  if (f.plannedDueDateFrom || f.plannedDueDateTo)   n++
  return n
})

// ── 이벤트 핸들러 ────────────────────────────────────────────────────────

function onApply() {
  if (hasDateError('created') || hasDateError('dueDate') || hasDateError('plannedDate')) return
  emit('apply', { ...localFilter.value }, localSearch.value ?? '', localStatuses.value)
}

function onReset() {
  localFilter.value   = defaultSrFilter()
  localSearch.value   = ''
  localStatuses.value = []
  emit('reset')
}

// ── 상태 칩 헬퍼 ─────────────────────────────────────────────────────────────

type TabState = 'include' | 'exclude' | 'none'

function tabChipState(s: { value: string }): TabState {
  if (s.value === 'all') return localStatuses.value.length === 0 ? 'include' : 'none'
  if (localStatuses.value.includes(s.value))        return 'include'
  if (localStatuses.value.includes(`!${s.value}`))  return 'exclude'
  return 'none'
}

function tabChipColor(s: { value: string; color: string }) {
  const st = tabChipState(s)
  if (st === 'include') return s.color
  if (st === 'exclude') return s.color   // outline 모드에서 테두리 색으로 사용
  return 'grey-2'
}

function tabChipTextColor(s: { value: string; color: string }) {
  const st = tabChipState(s)
  if (st === 'include') return 'white'
  if (st === 'exclude') return s.color
  return 'grey-8'
}

function tabChipTooltip(s: { value: string; label: string }) {
  const st = tabChipState(s)
  if (st === 'include') return `다시 클릭 → ${s.label} 제외`
  if (st === 'exclude') return `다시 클릭 → 해제`
  return `클릭 → ${s.label}만 보기 / 복수 선택 가능`
}

function onTabChange(tab: string) {
  if (tab === 'all') {
    localStatuses.value = []
  } else {
    const st = tabChipState({ value: tab })
    if (st === 'none') {
      // 중립 → include 추가
      localStatuses.value = [...localStatuses.value, tab]
    } else if (st === 'include') {
      // include → exclude 전환
      localStatuses.value = localStatuses.value.filter(s => s !== tab).concat(`!${tab}`)
    } else {
      // exclude → 해제
      localStatuses.value = localStatuses.value.filter(s => s !== `!${tab}`)
    }
  }
  emit('apply', { ...localFilter.value }, localSearch.value ?? '', localStatuses.value)
}

function onToggle(key: 'isUrgent' | 'isDelayed' | 'myAssigned') {
  localFilter.value[key] = !localFilter.value[key]
  // 빠른 토글은 즉시 조회
  emit('apply', { ...localFilter.value }, localSearch.value ?? '', localStatuses.value)
}
</script>

<style scoped>
.status-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.advanced-panel {
  padding-bottom: 4px;
}
</style>
