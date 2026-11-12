import type { WorkItem } from 'src/services/pm/reports'

function timestamp(value: string | null | undefined): number {
  if (!value) return Number.POSITIVE_INFINITY
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) || /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
    ? value : `${value}Z`
  const parsed = Date.parse(normalized)
  return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY
}

/** Sort a copy by start date, falling back to due date when no valid start exists. */
export function sortWorkItemsByDate(items: WorkItem[]): WorkItem[] {
  return [...items].sort((a, b) => {
    const aStart = timestamp(a.startDate), bStart = timestamp(b.startDate)
    const aDue = timestamp(a.dueDate), bDue = timestamp(b.dueDate)
    const primary = (Number.isFinite(aStart) ? aStart : aDue) - (Number.isFinite(bStart) ? bStart : bDue)
    if (primary) return primary
    const due = aDue - bDue
    if (due) return due
    return a.issueNumber - b.issueNumber || a.issueId.localeCompare(b.issueId)
  })
}
