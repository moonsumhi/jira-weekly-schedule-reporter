import { ref, computed } from 'vue'
import { REQUEST_TYPE_LABEL, SR_PRIORITY_LABEL } from 'src/services/sr'

// ── 타입 ─────────────────────────────────────────────────────────────────────

export type SrFilterState = {
  requestType:         string | null
  requesterDepartment: string
  requesterName:       string
  relatedSystem:       string
  assigneeId:          string | null
  priority:            string | null
  isUrgent:            boolean
  isDelayed:           boolean
  myAssigned:          boolean
  createdFrom:         string
  createdTo:           string
  dueDateFrom:         string
  dueDateTo:           string
  plannedDueDateFrom:  string
  plannedDueDateTo:    string
}

export type SrFilterPreset = {
  name:   string
  tab:    string
  filter: SrFilterState
}

export type SrActiveChip = {
  key:   string
  label: string
  value: string
}

// ── 상수 ─────────────────────────────────────────────────────────────────────

const PRESET_KEY = 'sr-manage-presets'

export const SR_STATUS_TAB_OPTIONS = [
  { value: 'all',          label: '전체',       color: 'grey-7'   },
  { value: 'SUBMITTED',    label: '접수',        color: 'blue-5'   },
  { value: 'REVIEWING',    label: '검토 중',     color: 'orange-5' },
  { value: 'PENDING_INFO', label: '추가 확인',   color: 'amber-7'  },
  { value: 'IN_PROGRESS',  label: '처리 중',     color: 'blue-8'   },
  { value: 'COMPLETED',    label: '처리 완료',   color: 'green-6'  },
  { value: 'CONFIRMING',   label: '확인 중',     color: 'purple-5' },
  { value: 'CLOSED',       label: '최종 완료',   color: 'green-9'  },
  { value: 'ON_HOLD',      label: '보류',        color: 'brown-5'  },
  { value: 'REJECTED',     label: '반려',        color: 'red-6'    },
]

export const SR_SORT_OPTIONS = [
  { label: '최신 접수순',   sortBy: 'created_at',       descending: true  },
  { label: '오래된 접수순', sortBy: 'created_at',       descending: false },
  { label: '마감 임박순',   sortBy: 'desired_due_date', descending: false },
  { label: '우선순위순',    sortBy: 'priority',         descending: true  },
  { label: '최근 수정순',   sortBy: 'updated_at',       descending: true  },
]

// ── 헬퍼 ─────────────────────────────────────────────────────────────────────

export function defaultSrFilter(): SrFilterState {
  return {
    requestType: null, requesterDepartment: '', requesterName: '',
    relatedSystem: '', assigneeId: null, priority: null,
    isUrgent: false, isDelayed: false, myAssigned: false,
    createdFrom: '', createdTo: '',
    dueDateFrom: '', dueDateTo: '',
    plannedDueDateFrom: '', plannedDueDateTo: '',
  }
}

export function buildSrApiParams(
  filter: SrFilterState,
  tab: string,
  extra: Record<string, string | number | boolean> = {},
): Record<string, string | number | boolean> {
  const p: Record<string, string | number | boolean> = { ...extra }
  if (tab !== 'all')                  p.status               = tab
  if (filter.requestType)             p.request_type         = filter.requestType
  if (filter.requesterDepartment)     p.requester_department = filter.requesterDepartment
  if (filter.requesterName)           p.requester_name       = filter.requesterName
  if (filter.relatedSystem)           p.related_system       = filter.relatedSystem
  if (filter.assigneeId)              p.assignee_id          = filter.assigneeId
  if (filter.priority)                p.priority             = filter.priority
  if (filter.isUrgent)                p.is_urgent            = true
  if (filter.isDelayed)               p.is_delayed           = true
  if (filter.myAssigned)              p.my_assigned          = true
  if (filter.createdFrom)             p.created_from         = filter.createdFrom
  if (filter.createdTo)               p.created_to           = filter.createdTo
  if (filter.dueDateFrom)             p.desired_due_from     = filter.dueDateFrom
  if (filter.dueDateTo)               p.desired_due_to       = filter.dueDateTo
  if (filter.plannedDueDateFrom)      p.planned_due_from     = filter.plannedDueDateFrom
  if (filter.plannedDueDateTo)        p.planned_due_to       = filter.plannedDueDateTo
  return p
}

// ── 컴포저블 ─────────────────────────────────────────────────────────────────

export function useSrSearch() {
  const filter    = ref<SrFilterState>(defaultSrFilter())
  const search    = ref('')
  const activeTab = ref('all')
  const presets   = ref<SrFilterPreset[]>(
    JSON.parse(localStorage.getItem(PRESET_KEY) ?? '[]') as SrFilterPreset[],
  )

  // 적용된 필터 칩 목록 (search·tab 제외, 고급 필터만)
  const activeChips = computed<SrActiveChip[]>(() => {
    const chips: SrActiveChip[] = []
    const f = filter.value
    const rtLabel = (v: string) => (REQUEST_TYPE_LABEL as Record<string, string>)[v] ?? v
    const prLabel = (v: string) => (SR_PRIORITY_LABEL  as Record<string, string>)[v] ?? v

    if (f.requesterDepartment)                      chips.push({ key: 'requesterDepartment', label: '요청 부서',   value: f.requesterDepartment })
    if (f.requesterName)                            chips.push({ key: 'requesterName',       label: '요청자',      value: f.requesterName })
    if (f.requestType)                              chips.push({ key: 'requestType',          label: '유형',        value: rtLabel(f.requestType) })
    if (f.relatedSystem)                            chips.push({ key: 'relatedSystem',        label: '관련 시스템', value: f.relatedSystem })
    if (f.assigneeId)                               chips.push({ key: 'assigneeId',           label: '담당자',      value: f.assigneeId })
    if (f.priority)                                 chips.push({ key: 'priority',             label: '중요도',      value: prLabel(f.priority) })
    if (f.isUrgent)                                 chips.push({ key: 'isUrgent',             label: '긴급',        value: 'ON' })
    if (f.isDelayed)                                chips.push({ key: 'isDelayed',            label: '지연',        value: 'ON' })
    if (f.myAssigned)                               chips.push({ key: 'myAssigned',           label: '내 담당',     value: 'ON' })
    if (f.createdFrom || f.createdTo)               chips.push({ key: 'created',              label: '접수일',      value: `${f.createdFrom || '-'} ~ ${f.createdTo || '-'}` })
    if (f.dueDateFrom || f.dueDateTo)               chips.push({ key: 'dueDate',              label: '희망완료일',  value: `${f.dueDateFrom || '-'} ~ ${f.dueDateTo || '-'}` })
    if (f.plannedDueDateFrom || f.plannedDueDateTo) chips.push({ key: 'plannedDate',          label: '완료목표일',  value: `${f.plannedDueDateFrom || '-'} ~ ${f.plannedDueDateTo || '-'}` })
    return chips
  })

  const activeFilterCount = computed(() => activeChips.value.length)

  function clearChip(key: string) {
    const f = filter.value
    switch (key) {
      case 'requesterDepartment': f.requesterDepartment = '';              break
      case 'requesterName':       f.requesterName       = '';              break
      case 'requestType':         f.requestType         = null;            break
      case 'relatedSystem':       f.relatedSystem       = '';              break
      case 'assigneeId':          f.assigneeId          = null;            break
      case 'priority':            f.priority            = null;            break
      case 'isUrgent':            f.isUrgent            = false;           break
      case 'isDelayed':           f.isDelayed           = false;           break
      case 'myAssigned':          f.myAssigned          = false;           break
      case 'created':             f.createdFrom = ''; f.createdTo = '';    break
      case 'dueDate':             f.dueDateFrom = ''; f.dueDateTo = '';    break
      case 'plannedDate':         f.plannedDueDateFrom = ''; f.plannedDueDateTo = ''; break
    }
  }

  function reset() {
    filter.value    = defaultSrFilter()
    search.value    = ''
    activeTab.value = 'all'
  }

  function readUrl(query: Record<string, string | (string | null)[]>) {
    const s = (k: string): string | undefined => {
      const v = query[k]
      return v ? String(v) : undefined
    }
    const st = s('tab')
    if (st) {
      // backwards compat: tab=delayed → isDelayed toggle
      if (st === 'delayed') {
        filter.value.isDelayed = true
        activeTab.value = 'all'
      } else {
        activeTab.value = st
      }
    }
    const f = filter.value
    if (s('dept'))     f.requesterDepartment = s('dept')!
    if (s('name'))     f.requesterName       = s('name')!
    if (s('type'))     f.requestType         = s('type')!
    if (s('sys'))      f.relatedSystem       = s('sys')!
    if (s('assignee')) f.assigneeId          = s('assignee')!
    if (s('priority')) f.priority            = s('priority')!
    if (s('urgent'))   f.isUrgent            = s('urgent') === '1'
    if (s('delayed'))  f.isDelayed           = s('delayed') === '1'
    if (s('mine'))     f.myAssigned          = s('mine') === '1'
    if (s('cfrom'))    f.createdFrom         = s('cfrom')!
    if (s('cto'))      f.createdTo           = s('cto')!
    if (s('dfrom'))    f.dueDateFrom         = s('dfrom')!
    if (s('dto'))      f.dueDateTo           = s('dto')!
    if (s('pfrom'))    f.plannedDueDateFrom  = s('pfrom')!
    if (s('pto'))      f.plannedDueDateTo    = s('pto')!
    if (s('q'))        search.value          = s('q')!
  }

  function toUrlQuery(
    page: number,
    rowsPerPage: number,
    sortBy: string,
    descending: boolean,
  ): Record<string, string> {
    const q: Record<string, string> = {}
    const f = filter.value
    if (activeTab.value !== 'all')  q.tab      = activeTab.value
    if (f.requesterDepartment)      q.dept     = f.requesterDepartment
    if (f.requesterName)            q.name     = f.requesterName
    if (f.requestType)              q.type     = f.requestType
    if (f.relatedSystem)            q.sys      = f.relatedSystem
    if (f.assigneeId)               q.assignee = f.assigneeId
    if (f.priority)                 q.priority = f.priority
    if (f.isUrgent)                 q.urgent   = '1'
    if (f.isDelayed)                q.delayed  = '1'
    if (f.myAssigned)               q.mine     = '1'
    if (f.createdFrom)              q.cfrom    = f.createdFrom
    if (f.createdTo)                q.cto      = f.createdTo
    if (f.dueDateFrom)              q.dfrom    = f.dueDateFrom
    if (f.dueDateTo)                q.dto      = f.dueDateTo
    if (f.plannedDueDateFrom)       q.pfrom    = f.plannedDueDateFrom
    if (f.plannedDueDateTo)         q.pto      = f.plannedDueDateTo
    if (search.value)               q.q        = search.value
    if (page > 1)                   q.page     = String(page)
    if (rowsPerPage !== 20)         q.rows     = String(rowsPerPage)
    if (sortBy !== 'created_at')    q.sort     = sortBy
    if (!descending)                q.asc      = '1'
    return q
  }

  function savePreset(name: string) {
    const list = [...presets.value, { name, tab: activeTab.value, filter: { ...filter.value } }]
    presets.value = list
    localStorage.setItem(PRESET_KEY, JSON.stringify(list))
  }

  function loadPreset(p: SrFilterPreset) {
    activeTab.value = p.tab
    filter.value    = { ...p.filter }
  }

  function removePreset(i: number) {
    const list = presets.value.filter((_, idx) => idx !== i)
    presets.value = list
    localStorage.setItem(PRESET_KEY, JSON.stringify(list))
  }

  return {
    filter, search, activeTab, presets,
    activeChips, activeFilterCount,
    clearChip, reset, readUrl, toUrlQuery,
    savePreset, loadPreset, removePreset,
  }
}
