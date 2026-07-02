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

// ── 주간 보고 ────────────────────────────────────────────────────────
export interface WeeklyReport {
  id: string
  reportYear: number
  reportWeek: number
  startDate: string
  endDate: string
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
