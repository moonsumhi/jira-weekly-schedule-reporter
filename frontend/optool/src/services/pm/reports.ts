import { api } from 'boot/axios'

export interface ReportStats {
  total: number
  completed: number
  inProgress: number
  delayed: number
  todo: number
  completionRate: number
}

export interface WorkItem {
  issueId: string
  issueNumber: number
  title: string
  type: string
  projectId: string
  projectName: string
  orgName: string | null
  assigneeId: string | null
  assigneeName: string | null
  status: string
  priority: string
  epicTitle: string | null
  sprintName: string | null
  startDate: string | null
  dueDate: string | null
  isDelayed: boolean
  storyPoints: number | null
}

export interface ProjectBreakdown {
  projectId: string
  projectName: string
  orgName: string | null
  stats: ReportStats
  completed: WorkItem[]
  inProgress: WorkItem[]
  delayed: WorkItem[]
  upcoming: WorkItem[]
}

export interface PersonBreakdown {
  userId: string
  userName: string
  stats: ReportStats
  completed: WorkItem[]
  inProgress: WorkItem[]
  delayed: WorkItem[]
  upcoming: WorkItem[]
}

// ── 수기 항목 ────────────────────────────────────────────────────────
export type ReportStatus = 'DRAFT' | 'REVIEWING' | 'CONFIRMED'
export type ManualItemSection = 'MAIN_AGENDA' | 'ISSUE_RISK' | 'DECISION_REQUIRED' | 'ANNOUNCEMENT' | 'ATTENDANCE'

export interface ManualItem {
  id: string
  section: ManualItemSection
  title: string
  owner: string | null
  linkedSrId: string | null
  linkedIssueId: string | null
  includeInReport: boolean
  sortOrder: number
  // MAIN_AGENDA
  category: string | null
  content: string | null
  agendaStatus: string | null
  // ISSUE_RISK
  itemType: string | null
  impact: string | null
  actionPlan: string | null
  // DECISION_REQUIRED
  background: string | null
  options: string | null
  requestedDecision: string | null
  desiredDate: string | null
  createdBy: string
  createdAt: string
  updatedBy: string | null
  updatedAt: string
}

export interface ManualItemCreate {
  section: ManualItemSection
  title: string
  owner?: string | null
  include_in_report?: boolean
  sort_order?: number
  category?: string | null
  content?: string | null
  agenda_status?: string | null
  item_type?: string | null
  impact?: string | null
  action_plan?: string | null
  background?: string | null
  options?: string | null
  requested_decision?: string | null
  desired_date?: string | null
}

// ── SR 요약 ──────────────────────────────────────────────────────────
export interface SrItem {
  srNo: string
  title: string
  status: string
  statusLabel: string
  requestType: string
  requestTypeLabel: string
  requesterName: string
  requesterDepartment: string
  assigneeName: string | null
  isUrgent: boolean
  desiredDueDate: string | null
  createdAt: string
}

export interface SrSummary {
  newThisWeek: SrItem[]
  completedThisWeek: SrItem[]
  pendingItems: SrItem[]
  openItems: SrItem[]
  byStatus: Record<string, number>
  totalOpen: number
  totalNew: number
  totalCompleted: number
}

// ── 주간 보고 ────────────────────────────────────────────────────────
export interface WeeklyReport {
  id: string
  reportYear: number
  reportWeek: number
  startDate: string
  endDate: string
  title: string
  department: string | null
  status: ReportStatus
  byProject: ProjectBreakdown[]
  byPerson: PersonBreakdown[]
  allItems: WorkItem[]
  upcomingItems: WorkItem[]
  stats: ReportStats
  manualItems: ManualItem[]
  srSummary: SrSummary | null
  adminComment: string | null
  createdBy: string
  createdByName: string | null
  createdAt: string
  updatedBy: string | null
  updatedByName: string | null
  updatedAt: string
  confirmedBy: string | null
  confirmedAt: string | null
}

export interface WeeklyReportCreate {
  report_year: number
  report_week: number
  start_date: string
  end_date: string
  title: string
  department?: string
  admin_comment?: string
}

export interface WeeklyReportPatch {
  title?: string
  department?: string
  admin_comment?: string
}

export async function listWeeklyReports(params: { year?: number; week?: number; status?: string } = {}) {
  const { data } = await api.get<WeeklyReport[]>('/pm/weekly-reports', { params })
  return data
}

export async function getWeeklyReport(id: string) {
  const { data } = await api.get<WeeklyReport>(`/pm/weekly-reports/${id}`)
  return data
}

export async function createWeeklyReport(payload: WeeklyReportCreate) {
  const { data } = await api.post<WeeklyReport>('/pm/weekly-reports', payload)
  return data
}

export async function updateWeeklyReport(id: string, payload: WeeklyReportPatch) {
  const { data } = await api.patch<WeeklyReport>(`/pm/weekly-reports/${id}`, payload)
  return data
}

export async function refreshWeeklyReport(id: string) {
  const { data } = await api.post<WeeklyReport>(`/pm/weekly-reports/${id}/refresh`)
  return data
}

export async function deleteWeeklyReport(id: string) {
  await api.delete(`/pm/weekly-reports/${id}`)
}

export async function changeWeeklyReportStatus(id: string, status: ReportStatus) {
  const { data } = await api.patch<WeeklyReport>(`/pm/weekly-reports/${id}/status`, { status })
  return data
}

export async function addManualItem(id: string, payload: ManualItemCreate) {
  const { data } = await api.post<WeeklyReport>(`/pm/weekly-reports/${id}/items`, payload)
  return data
}

export async function updateManualItem(id: string, itemId: string, payload: Partial<ManualItemCreate>) {
  const { data } = await api.patch<WeeklyReport>(`/pm/weekly-reports/${id}/items/${itemId}`, payload)
  return data
}

export async function deleteManualItem(id: string, itemId: string) {
  const { data } = await api.delete<WeeklyReport>(`/pm/weekly-reports/${id}/items/${itemId}`)
  return data
}

export async function previewWeeklyReport(id: string): Promise<string> {
  const { data } = await api.get<{ text: string }>(`/pm/weekly-reports/${id}/preview`)
  return data.text
}

export function weeklyExportListUrl(params: { year?: number; week?: number } = {}) {
  const qs = new URLSearchParams()
  if (params.year) qs.set('year', String(params.year))
  if (params.week) qs.set('week', String(params.week))
  return `/api/pm/weekly-reports/export/list?${qs}`
}

export function weeklyExportDetailUrl(id: string) {
  return `/api/pm/weekly-reports/${id}/export`
}

// ── 월간 보고 ────────────────────────────────────────────────────────
export interface MonthlyReport {
  id: string
  reportYear: number
  reportMonth: number
  title: string
  department: string | null
  byProject: ProjectBreakdown[]
  byPerson: PersonBreakdown[]
  allItems: WorkItem[]
  upcomingItems: WorkItem[]
  stats: ReportStats
  adminComment: string | null
  createdBy: string
  createdByName: string | null
  createdAt: string
  updatedBy: string | null
  updatedByName: string | null
  updatedAt: string
}

export interface MonthlyReportCreate {
  report_year: number
  report_month: number
  title: string
  department?: string
  admin_comment?: string
}

export interface MonthlyReportPatch {
  title?: string
  department?: string
  admin_comment?: string
}

export async function listMonthlyReports(params: { year?: number; month?: number; status?: string } = {}) {
  const { data } = await api.get<MonthlyReport[]>('/pm/monthly-reports', { params })
  return data
}

export async function getMonthlyReport(id: string) {
  const { data } = await api.get<MonthlyReport>(`/pm/monthly-reports/${id}`)
  return data
}

export async function createMonthlyReport(payload: MonthlyReportCreate) {
  const { data } = await api.post<MonthlyReport>('/pm/monthly-reports', payload)
  return data
}

export async function updateMonthlyReport(id: string, payload: MonthlyReportPatch) {
  const { data } = await api.patch<MonthlyReport>(`/pm/monthly-reports/${id}`, payload)
  return data
}

export async function refreshMonthlyReport(id: string) {
  const { data } = await api.post<MonthlyReport>(`/pm/monthly-reports/${id}/refresh`)
  return data
}

export async function deleteMonthlyReport(id: string) {
  await api.delete(`/pm/monthly-reports/${id}`)
}

export function monthlyExportListUrl(params: { year?: number; month?: number } = {}) {
  const qs = new URLSearchParams()
  if (params.year)  qs.set('year',  String(params.year))
  if (params.month) qs.set('month', String(params.month))
  return `/api/pm/monthly-reports/export/list?${qs}`
}

export function monthlyExportDetailUrl(id: string) {
  return `/api/pm/monthly-reports/${id}/export`
}
