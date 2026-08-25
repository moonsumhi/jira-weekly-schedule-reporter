import { api } from 'src/boot/axios'
import type { IssueType, IssuePriority } from 'src/services/pm/issue'

// ── 응답 타입 (camelCase 자동 변환됨) ──────────────────────────────
export type WeekdayOccurrence = { week: number; weekday: number }

export type RecurrenceRule = {
  freq: 'monthly'
  mode: 'day_of_month' | 'weekday'
  daysOfMonth: number[]
  weekdays: WeekdayOccurrence[]
  time: string
}

export type IssueBlueprint = {
  title: string
  description: string | null
  type: IssueType
  priority: IssuePriority
  assigneeId: string | null
  labelIds: string[]
  storyPoints: number | null
  effortMd: string | null
  showOnDashboard: boolean
}

export type RecurringIssueTemplate = {
  id: string
  name: string
  projectId: string
  blueprint: IssueBlueprint
  rule: RecurrenceRule
  leadDays: number
  autoEnabled: boolean
  active: boolean
  createdAt?: string
  createdBy?: string
  updatedAt?: string
  updatedBy?: string
}

export type Occurrence = {
  occurrenceDate: string
  roundLabel: string
  title: string
  issueId: string | null
  alreadyExists: boolean
}

export type GenerateResult = {
  created: Occurrence[]
  skipped: Occurrence[]
}

// ── 요청 페이로드 (백엔드는 snake_case) ────────────────────────────
export type TemplatePayload = {
  name: string
  project_id: string
  blueprint: {
    title: string
    description?: string | null
    type: IssueType
    priority: IssuePriority
    assignee_id?: string | null
    label_ids?: string[]
    story_points?: number | null
    effort_md?: string | null
    show_on_dashboard?: boolean
  }
  rule: {
    freq: 'monthly'
    mode: 'day_of_month' | 'weekday'
    days_of_month: number[]
    weekdays: WeekdayOccurrence[]
    time: string
  }
  lead_days: number
  auto_enabled: boolean
  active: boolean
}

export async function listRecurringTemplates(projectId?: string) {
  const { data } = await api.get<RecurringIssueTemplate[]>('/pm/recurring-issue-templates', {
    params: projectId ? { project_id: projectId } : {},
  })
  return data
}

export async function createRecurringTemplate(payload: TemplatePayload) {
  const { data } = await api.post<RecurringIssueTemplate>('/pm/recurring-issue-templates', payload)
  return data
}

export async function updateRecurringTemplate(id: string, payload: Omit<TemplatePayload, 'project_id'>) {
  const { data } = await api.patch<RecurringIssueTemplate>(`/pm/recurring-issue-templates/${id}`, payload)
  return data
}

export async function deleteRecurringTemplate(id: string) {
  await api.delete(`/pm/recurring-issue-templates/${id}`)
}

export async function previewOccurrences(id: string, year: number, month: number) {
  const { data } = await api.get<Occurrence[]>(`/pm/recurring-issue-templates/${id}/preview`, {
    params: { year, month },
  })
  return data
}

export async function generateOccurrences(id: string, year: number, month: number) {
  const { data } = await api.post<GenerateResult>(`/pm/recurring-issue-templates/${id}/generate`, null, {
    params: { year, month },
  })
  return data
}
