import type { Issue, IssuePriority, IssueStatus, IssueType } from '../../services/pm/issue'

export type BacklogFilters = {
  search: string
  statusTabs: string[]
  priority: IssuePriority | null
  type: IssueType | null
  assigneeId: string | null
  dateFrom: string | null
  dateTo: string | null
}

const statuses: IssueStatus[] = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'IMPLEMENTED', 'DONE']
const priorities: IssuePriority[] = ['LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST']
const types: IssueType[] = ['EPIC', 'STORY', 'TASK', 'BUG', 'SUB_TASK']
const dueDayFormatter = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
})

export function defaultBacklogFilters(): BacklogFilters {
  return { search: '', statusTabs: [], priority: null, type: null, assigneeId: null, dateFrom: null, dateTo: null }
}

function calendarDate(value: unknown): string | null {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value ? value : null
}

function enumValue<T extends string>(value: unknown, values: T[]): T | null {
  return typeof value === 'string' && values.includes(value as T) ? value as T : null
}

export function normalizeBacklogFilters(value: unknown): BacklogFilters {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return defaultBacklogFilters()
  const saved = value as Record<string, unknown>
  const tabs = Array.isArray(saved.statusTabs) ? saved.statusTabs : [saved.status]
  let dateFrom = calendarDate(saved.dateFrom), dateTo = calendarDate(saved.dateTo)
  if (dateFrom && dateTo && dateFrom > dateTo) dateFrom = dateTo = null
  return {
    search: typeof saved.search === 'string' ? saved.search : '',
    // 사라진 상태는 버리고, 같은 상태의 포함/제외가 충돌하면 포함을 우선한다.
    statusTabs: statuses.flatMap(status => tabs.includes(status) ? [status] : tabs.includes(`!${status}`) ? [`!${status}`] : []),
    priority: enumValue(saved.priority, priorities),
    type: enumValue(saved.type, types),
    assigneeId: typeof saved.assigneeId === 'string' && saved.assigneeId.trim() ? saved.assigneeId.trim() : null,
    dateFrom, dateTo,
  }
}

export function backlogFilterKey(userId: string, projectId: string): string {
  return `backlog_filter_v2:${encodeURIComponent(userId)}:${encodeURIComponent(projectId)}`
}

export function readBacklogFilters(userId: string, projectId: string, storage: Pick<Storage, 'getItem'>) {
  try {
    const raw = storage.getItem(backlogFilterKey(userId, projectId))
    // 이전 키에는 사용자 정보가 없다. 다른 계정의 조건을 이어받지 않는다.
    const resetLegacy = raw === null && storage.getItem(`backlog_filter_${projectId}`) !== null
    return { filters: normalizeBacklogFilters(JSON.parse(raw ?? 'null')), resetLegacy }
  } catch {
    return { filters: defaultBacklogFilters(), resetLegacy: false }
  }
}

export function writeBacklogFilters(userId: string, projectId: string, filters: BacklogFilters, storage: Pick<Storage, 'setItem'>) {
  try {
    storage.setItem(backlogFilterKey(userId, projectId), JSON.stringify(normalizeBacklogFilters(filters)))
  } catch { /* 저장 공간 제한이 이슈 조회를 막지 않게 한다. */ }
}

export function hasBacklogFilters(filters: BacklogFilters): boolean {
  return !!(filters.search.trim() || filters.statusTabs.length || filters.priority || filters.type || filters.assigneeId || filters.dateFrom || filters.dateTo)
}

/** 백엔드의 naive UTC / UTC / offset datetime을 한국 날짜로 비교한다. */
export function backlogDueDay(value: string | null): string | null {
  if (!value) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return calendarDate(value)
  const date = new Date(/Z|[+-]\d{2}:?\d{2}$/i.test(value) ? value : `${value}Z`)
  return Number.isFinite(date.getTime())
    ? dueDayFormatter.format(date)
    : null
}

type FilterableIssue = Pick<Issue, 'title' | 'number' | 'projectKey' | 'linkedSrNo' | 'status' | 'priority' | 'type' | 'assigneeId' | 'dueDate'>

export function matchesBacklogIssue(issue: FilterableIssue, filters: BacklogFilters, projectKey = ''): boolean {
  const query = filters.search.trim().toLowerCase()
  if (query && ![issue.title, issue.linkedSrNo, `${issue.projectKey || projectKey}-${issue.number}`]
    .some(value => (value ?? '').toLowerCase().includes(query))) return false
  const included = filters.statusTabs.filter(status => !status.startsWith('!'))
  if (included.length && !included.includes(issue.status)) return false
  if (filters.statusTabs.includes(`!${issue.status}`)) return false
  if (filters.priority && issue.priority !== filters.priority) return false
  if (filters.type && issue.type !== filters.type) return false
  if (filters.assigneeId && issue.assigneeId !== filters.assigneeId) return false
  // 잘못 입력 중인 기간은 안내하고, 날짜 조건만 적용하지 않는다.
  const { dateFrom, dateTo } = normalizeBacklogFilters(filters)
  if (dateFrom || dateTo) {
    const day = backlogDueDay(issue.dueDate)
    if (!day || (dateFrom && day < dateFrom) || (dateTo && day > dateTo)) return false
  }
  return true
}
