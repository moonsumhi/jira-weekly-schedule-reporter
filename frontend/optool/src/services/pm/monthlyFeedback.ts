import { api } from 'src/boot/axios'

export interface MonthlyFeedback {
  id: string
  sourceReportId: string
  targetReportId: string
  title: string
  comment: string
  assigneeId: string
  assigneeName: string
  requesterId: string
  requesterName: string
  dueDate: string
  status: 'REQUESTED' | 'WRITING' | 'SUBMITTED' | 'APPLYING' | 'APPLIED' | 'CANCELLED'
  content: string
  reviewNote: string
}

export async function listFeedback(reportId: string) {
  return (await api.get<MonthlyFeedback[]>('/pm/monthly-feedback', { params: { report_id: reportId } })).data
}
export async function listMyFeedback() {
  return (await api.get<MonthlyFeedback[]>('/pm/monthly-feedback/mine')).data
}
export async function listFeedbackAssignees() {
  return (await api.get<{ id: string; name: string }[]>('/pm/monthly-feedback/assignees')).data
}
export async function createFeedback(payload: { source_report_id: string; title: string; comment: string; assignee_id: string; due_date: string }) {
  return (await api.post<MonthlyFeedback>('/pm/monthly-feedback', payload)).data
}
export async function feedbackAction(id: string, action: 'save' | 'submit' | 'cancel', content = '') {
  return (await api.post<MonthlyFeedback>(`/pm/monthly-feedback/${id}/action`, { action, content })).data
}
