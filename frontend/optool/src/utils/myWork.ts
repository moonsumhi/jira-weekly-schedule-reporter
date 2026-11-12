import type { Issue } from 'src/services/pm/issue'
import type { SRListItem } from 'src/services/sr'

export const MY_WORK_SR_STATUSES = ['SUBMITTED', 'REVIEWING', 'PENDING_INFO', 'APPROVED', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD'] as const
const activeSrStatuses = new Set<string>(MY_WORK_SR_STATUSES)

type WorkDeadline = {
  dueDate: string | null
  daysLeft: number | null
  urgency: 'overdue' | 'today' | 'upcoming' | 'paused' | 'undated'
  deadlineLabel: string
}
type WorkIdentity = { id: string; key: string; title: string; context: string; status: string }
export type MyWorkItem = WorkIdentity & WorkDeadline & (
  { kind: 'issue'; issue: Issue } | { kind: 'sr'; sr: SRListItem }
)

function calendarDate(value: string | null | undefined): string | null {
  const date = value?.slice(0, 10) ?? ''
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  const parsed = Date.parse(`${date}T00:00:00Z`)
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === date ? date : null
}

export function workDeadline(due: string | null | undefined, today: string, paused = false): WorkDeadline {
  // Due dates are business dates, not instants. The caller supplies today's KST date.
  const dueDate = calendarDate(due)
  if (!dueDate) return { dueDate: null, daysLeft: null, urgency: 'undated', deadlineLabel: '마감일 없음' }
  const daysLeft = (Date.parse(`${dueDate}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)) / 86_400_000
  if (paused) return { dueDate, daysLeft, urgency: 'paused', deadlineLabel: '보류 중' }
  if (daysLeft < 0) return { dueDate, daysLeft, urgency: 'overdue', deadlineLabel: `${-daysLeft}일 지연` }
  if (daysLeft === 0) return { dueDate, daysLeft, urgency: 'today', deadlineLabel: '오늘 마감' }
  return { dueDate, daysLeft, urgency: 'upcoming', deadlineLabel: daysLeft === 1 ? '내일 마감' : `D-${daysLeft}` }
}

export function buildMyWork(issues: Issue[], srs: SRListItem[], userId: string | undefined, today: string): MyWorkItem[] {
  if (!userId) return []
  const ownSrs = srs.filter(sr => sr.assigneeId === userId && activeSrStatuses.has(sr.status))
  const linkedSrs = new Set(ownSrs.map(sr => sr.id))
  const rows: MyWorkItem[] = issues
    .filter(issue => issue.assigneeId === userId && issue.status !== 'DONE' && issue.status !== 'IMPLEMENTED'
      && !(issue.linkedSrId && linkedSrs.has(issue.linkedSrId)))
    .map(issue => ({
      id: `issue-${issue.id}`, kind: 'issue', issue,
      key: issue.projectKey ? `${issue.projectKey}-${issue.number}` : `#${issue.number}`,
      title: issue.title, context: issue.projectName || '스케줄 관리', status: issue.status,
      ...workDeadline(issue.dueDate, today),
    }))
  rows.push(...ownSrs.map(sr => ({
    id: `sr-${sr.id}`, kind: 'sr' as const, sr, key: sr.srNo,
    title: sr.title, context: sr.relatedSystem ? `SR · ${sr.relatedSystem}` : 'SR', status: sr.status,
    ...workDeadline(sr.plannedDueDate || sr.desiredDueDate, today, sr.status === 'ON_HOLD'),
  })))
  const rank = { overdue: 0, today: 1, upcoming: 2, paused: 3, undated: 4 }
  return rows.sort((a, b) => rank[a.urgency] - rank[b.urgency]
    || (a.daysLeft ?? Infinity) - (b.daysLeft ?? Infinity)
    || a.key.localeCompare(b.key, 'ko', { numeric: true }) || a.id.localeCompare(b.id))
}
