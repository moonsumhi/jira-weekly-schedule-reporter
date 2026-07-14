import { api } from 'src/boot/axios'

// ── 타입 정의 ─────────────────────────────────────────────────────────

export type SRStatus =
  | 'DRAFT' | 'SUBMITTED' | 'REVIEWING' | 'PENDING_INFO'
  | 'REJECTED' | 'APPROVED' | 'ASSIGNED' | 'IN_PROGRESS'
  | 'COMPLETED' | 'CONFIRMING' | 'CLOSED' | 'ON_HOLD' | 'CANCELLED'

export type RequestType =
  | 'IMPROVEMENT' | 'BUG_FIX' | 'DATA_REQUEST'
  | 'PERMISSION' | 'CONFIG_CHANGE' | 'SERVER_INFRA'
  | 'SECURITY' | 'ETC'

export type ImpactScope =
  | 'PERSONAL' | 'DEPARTMENT' | 'ALL_USERS' | 'EXTERNAL_USERS' | 'EXTERNAL_SERVICE'

export type SRPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export type ReviewResult = 'APPROVED' | 'REJECTED' | 'ON_HOLD' | 'PENDING_INFO'

export const SR_STATUS_LABEL: Record<SRStatus, string> = {
  DRAFT: '임시저장',
  SUBMITTED: '접수',
  REVIEWING: '검토 중',
  PENDING_INFO: '추가 확인 요청',
  REJECTED: '반려',
  APPROVED: '승인',
  ASSIGNED: '담당자 배정',
  IN_PROGRESS: '처리 중',
  COMPLETED: '처리 완료',
  CONFIRMING: '요청자 확인 중',
  CLOSED: '최종 완료',
  ON_HOLD: '보류',
  CANCELLED: '취소',
}

export const SR_STATUS_COLOR: Record<SRStatus, string> = {
  DRAFT: 'grey-5',
  SUBMITTED: 'blue-5',
  REVIEWING: 'orange-5',
  PENDING_INFO: 'amber-7',
  REJECTED: 'red-6',
  APPROVED: 'teal-6',
  ASSIGNED: 'cyan-7',
  IN_PROGRESS: 'blue-8',
  COMPLETED: 'green-6',
  CONFIRMING: 'purple-5',
  CLOSED: 'green-9',
  ON_HOLD: 'brown-5',
  CANCELLED: 'grey-7',
}

export const REQUEST_TYPE_LABEL: Record<RequestType, string> = {
  IMPROVEMENT: '기능 개선 요청',
  BUG_FIX: '오류 수정 요청',
  DATA_REQUEST: '데이터 요청',
  PERMISSION: '권한 요청',
  CONFIG_CHANGE: '설정 변경 요청',
  SERVER_INFRA: '서버/인프라 요청',
  SECURITY: '보안 조치 요청',
  ETC: '기타',
}

export const IMPACT_SCOPE_LABEL: Record<ImpactScope, string> = {
  PERSONAL: '개인',
  DEPARTMENT: '부서',
  ALL_USERS: '전체 사용자',
  EXTERNAL_USERS: '외부 사용자',
  EXTERNAL_SERVICE: '대외 서비스',
}

export const SR_PRIORITY_LABEL: Record<SRPriority, string> = {
  CRITICAL: '긴급',
  HIGH: '높음',
  MEDIUM: '보통',
  LOW: '낮음',
}

export const SR_PRIORITY_COLOR: Record<SRPriority, string> = {
  CRITICAL: 'red',
  HIGH: 'orange',
  MEDIUM: 'blue',
  LOW: 'grey',
}

export const REQUEST_TYPE_OPTIONS = Object.entries(REQUEST_TYPE_LABEL).map(([value, label]) => ({ value, label }))
export const IMPACT_SCOPE_OPTIONS = Object.entries(IMPACT_SCOPE_LABEL).map(([value, label]) => ({ value, label }))
export const SR_PRIORITY_OPTIONS  = Object.entries(SR_PRIORITY_LABEL).map(([value, label]) => ({ value, label }))
export const SR_STATUS_OPTIONS    = Object.entries(SR_STATUS_LABEL).map(([value, label]) => ({ value, label }))

// ── 모델 타입 ────────────────────────────────────────────────────────

export type SRAttachment = {
  fileId: string
  originalName: string
  url: string
  size: number
  contentType: string
}

// 백엔드 전송용 snake_case 첨부파일 타입
export type SRAttachmentInput = {
  file_id: string
  original_name: string
  url: string
  size: number
  content_type: string
}

export type SR = {
  id: string
  srNo: string
  title: string
  status: SRStatus
  requestType: RequestType
  requesterId: string
  requesterName: string
  requesterDepartment: string
  requesterEmail: string
  relatedSystem: string | null
  relatedMenu: string | null
  relatedUrl: string | null
  background: string | null
  description: string
  purpose: string | null
  desiredDueDate: string | null
  desiredDeployDate: string | null
  isUrgent: boolean
  urgentReason: string | null
  impactScope: ImpactScope | null
  priority: SRPriority
  impactIfNotProcessed: string | null
  complianceRelated: boolean
  completionCriteria: string | null
  reviewerName: string | null
  note: string | null
  attachments: SRAttachment[]
  // 검토 정보
  reviewResult: ReviewResult | null
  reviewerId: string | null
  reviewerUserName: string | null
  reviewedAt: string | null
  reviewComment: string | null
  rejectReason: string | null
  holdReason: string | null
  pendingInfoContent: string | null
  // 처리 정보
  assigneeId: string | null
  assigneeName: string | null
  plannedStartDate: string | null
  plannedDueDate: string | null
  actualCompletedAt: string | null
  isDelayed: boolean
  processResult: string | null
  deployed: boolean
  deployedAt: string | null
  requesterConfirmed: boolean
  // 유형별 추가 항목
  typeDetail: Record<string, string | null> | null
  // 연결 정보
  relatedProjectId: string | null
  relatedIssueId: string | null
  convertedIssueId: string | null
  convertedTaskId: string | null
  convertedProjectId: string | null
  estimatedEffort: string | null
  deploymentRequired: boolean
  securityReviewRequired: boolean
  // 메타
  createdAt: string
  createdBy: string
  updatedAt: string
  updatedBy: string
  deletedAt: string | null
}

export type SRListItem = {
  id: string
  srNo: string
  title: string
  status: SRStatus
  requestType: RequestType
  requesterId: string
  requesterName: string
  requesterDepartment: string
  relatedSystem: string | null
  priority: SRPriority
  isUrgent: boolean
  desiredDueDate: string | null
  plannedDueDate: string | null
  actualCompletedAt: string | null
  assigneeId: string | null
  assigneeName: string | null
  isDelayed: boolean
  createdAt: string
  updatedAt: string
}

export type SRCreate = {
  title: string
  requester_name: string
  requester_department: string
  requester_email: string
  request_type: RequestType
  related_system?: string
  related_menu?: string
  related_url?: string
  background?: string
  description: string
  purpose?: string
  desired_due_date?: string | null
  desired_deploy_date?: string | null
  is_urgent: boolean
  urgent_reason?: string
  impact_scope?: ImpactScope | null
  priority: SRPriority
  impact_if_not_processed?: string
  compliance_related: boolean
  completion_criteria?: string
  reviewer_name?: string
  note?: string
  attachments?: SRAttachmentInput[]
  type_detail?: Record<string, string | null> | null
  submit: boolean
}

export type SRPatch = Partial<SRCreate>

export type SRReview = {
  result: ReviewResult
  comment?: string | undefined
  reject_reason?: string | undefined
  hold_reason?: string | undefined
  pending_info_content?: string | undefined
  related_project_id?: string | undefined
  related_issue_id?: string | undefined
}

export type SRAssign = {
  assignee_id: string
  assignee_name: string
  planned_start_date?: string | null | undefined
  planned_due_date?: string | null | undefined
  estimated_effort?: string | undefined
  deployment_required?: boolean | undefined
  security_review_required?: boolean | undefined
}

export type SRStatusChange = {
  status: SRStatus
  reason?: string | undefined
  process_result?: string | undefined
  deployed?: boolean | undefined
  deployed_at?: string | null | undefined
  actual_completed_at?: string | null | undefined
  requester_confirmed?: boolean | undefined
}

export type SRComment = {
  id: string
  srId: string
  writerId: string
  writerName: string
  content: string
  isInternal: boolean
  attachments: SRAttachment[]
  createdAt: string
  updatedAt: string
}

export type SRHistory = {
  id: string
  srId: string
  actionType: string
  beforeValue: string | null
  afterValue: string | null
  changedBy: string
  changedAt: string
}

export type SRStats = {
  total: number
  submitted: number
  inProgress: number
  completed: number
  rejected: number
  onHold: number
  delayed: number
  cancelled: number
  urgentCount: number
  byType: Record<string, number>
  byDepartment: Record<string, number>
  bySystem: Record<string, number>
  byAssignee: Record<string, number>
  avgProcessingDays: number | null
  onTimeRate: number | null
}

export type SRListFilter = {
  status?: string
  request_type?: string
  requester_department?: string
  requester_name?: string
  related_system?: string
  assignee_id?: string
  priority?: string
  is_urgent?: boolean
  is_delayed?: boolean
  my_assigned?: boolean
  desired_due_from?: string
  desired_due_to?: string
  planned_due_from?: string
  planned_due_to?: string
  skip?: number
  limit?: number
}

// ── 요청자용 API ──────────────────────────────────────────────────────

export async function createSR(payload: SRCreate) {
  const { data } = await api.post<SR>('/schedule/service-requests', payload)
  return data
}

export async function listMySRs(params?: {
  status?: string
  request_type?: string
  related_system?: string
  priority?: string
  desired_due_date_from?: string
  desired_due_date_to?: string
}) {
  const { data } = await api.get<SRListItem[]>('/schedule/service-requests/my', { params })
  return data
}

export async function getSR(id: string) {
  const { data } = await api.get<SR>(`/schedule/service-requests/${id}`)
  return data
}

export async function updateSR(id: string, payload: SRPatch) {
  const { data } = await api.put<SR>(`/schedule/service-requests/${id}`, payload)
  return data
}

export async function cancelSR(id: string, reason: string) {
  const { data } = await api.post<SR>(`/schedule/service-requests/${id}/cancel`, null, { params: { reason } })
  return data
}

export async function uploadSRAttachment(file: File): Promise<SRAttachment> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<SRAttachment>('/schedule/service-requests/uploads', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function addComment(id: string, content: string, isInternal = false, attachments: SRAttachment[] = []) {
  const { data } = await api.post<SRComment>(`/schedule/service-requests/${id}/comments`, {
    content,
    is_internal: isInternal,
    attachments: attachments.map(a => ({
      file_id: a.fileId,
      original_name: a.originalName,
      url: a.url,
      size: a.size,
      content_type: a.contentType,
    })),
  })
  return data
}

export async function listComments(id: string) {
  const { data } = await api.get<SRComment[]>(`/schedule/service-requests/${id}/comments`)
  return data
}

export async function listHistory(id: string) {
  const { data } = await api.get<SRHistory[]>(`/schedule/service-requests/${id}/history`)
  return data
}

// ── 관리자용 API ──────────────────────────────────────────────────────

export async function listAllSRs(filter?: SRListFilter | Record<string, string | number | boolean>) {
  const { data } = await api.get<{ items: SRListItem[]; total: number }>('/admin/schedule/service-requests', { params: filter })
  return data
}

export async function getAdminSR(id: string) {
  const { data } = await api.get<SR>(`/admin/schedule/service-requests/${id}`)
  return data
}

export type SRInlinePatch = {
  priority?:         string
  desired_due_date?: string | null
  assignee_id?:      string | null
  assignee_name?:    string | null
}

export async function patchSRInline(id: string, payload: SRInlinePatch) {
  const { data } = await api.patch<SR>(`/admin/schedule/service-requests/${id}`, payload)
  return data
}

export async function updateAdminSR(id: string, payload: SRPatch) {
  const { data } = await api.put<SR>(`/admin/schedule/service-requests/${id}`, payload)
  return data
}

export async function reviewSR(id: string, payload: SRReview) {
  const { data } = await api.post<SR>(`/admin/schedule/service-requests/${id}/review`, payload)
  return data
}

export async function assignSR(id: string, payload: SRAssign) {
  const { data } = await api.post<SR>(`/admin/schedule/service-requests/${id}/assign`, payload)
  return data
}

export async function changeSRStatus(id: string, payload: SRStatusChange) {
  const { data } = await api.post<SR>(`/admin/schedule/service-requests/${id}/status`, payload)
  return data
}

export async function convertToIssue(id: string, issueId: string) {
  const { data } = await api.post<SR>(`/admin/schedule/service-requests/${id}/convert-to-issue`, null, { params: { issue_id: issueId } })
  return data
}

export async function deleteSR(id: string) {
  await api.delete(`/admin/schedule/service-requests/${id}`)
}

export async function getSRStats(params?: { date_from?: string; date_to?: string }) {
  const { data } = await api.get<SRStats>('/admin/schedule/service-requests/stats/summary', { params })
  return data
}

