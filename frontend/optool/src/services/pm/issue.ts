import { api } from 'src/boot/axios'

export type IssueType = 'EPIC' | 'STORY' | 'TASK' | 'BUG' | 'SUB_TASK'
export type IssueStatus = 'BACKLOG' | 'TODO' | 'IN_PROGRESS' | 'IN_REVIEW' | 'DONE'
export type IssuePriority = 'LOWEST' | 'LOW' | 'MEDIUM' | 'HIGH' | 'HIGHEST'

export const ISSUE_STATUSES: IssueStatus[] = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE']

export const STATUS_LABEL: Record<IssueStatus, string> = {
  BACKLOG: '백로그',
  TODO: '할 일',
  IN_PROGRESS: '진행 중',
  IN_REVIEW: '검토 중',
  DONE: '완료',
}

export const STATUS_COLOR: Record<IssueStatus, string> = {
  BACKLOG: 'grey-5',
  TODO: 'blue-4',
  IN_PROGRESS: 'orange-6',
  IN_REVIEW: 'purple-5',
  DONE: 'green-6',
}

export const TYPE_ICON: Record<IssueType, string> = {
  EPIC: 'fa-solid fa-bolt',
  STORY: 'fa-solid fa-bookmark',
  TASK: 'fa-solid fa-check-square',
  BUG: 'fa-solid fa-bug',
  SUB_TASK: 'fa-solid fa-circle-dot',
}

export const TYPE_COLOR: Record<IssueType, string> = {
  EPIC: 'purple',
  STORY: 'green',
  TASK: 'blue',
  BUG: 'red',
  SUB_TASK: 'teal',
}

export const PRIORITY_LABEL: Record<IssuePriority, string> = {
  HIGHEST: '최고',
  HIGH: '높음',
  MEDIUM: '보통',
  LOW: '낮음',
  LOWEST: '최저',
}

export const PRIORITY_ICON: Record<IssuePriority, string> = {
  HIGHEST: 'fa-solid fa-angles-up',
  HIGH: 'fa-solid fa-angle-up',
  MEDIUM: 'fa-solid fa-equals',
  LOW: 'fa-solid fa-angle-down',
  LOWEST: 'fa-solid fa-angles-down',
}

export const PRIORITY_COLOR: Record<IssuePriority, string> = {
  HIGHEST: 'red',
  HIGH: 'orange',
  MEDIUM: 'blue',
  LOW: 'grey',
  LOWEST: 'grey-4',
}

export type SubtaskSummary = {
  id: string
  number: number
  title: string
  status: IssueStatus
  priority: IssuePriority
  assigneeName: string | null
}

export type Issue = {
  id: string
  projectId: string
  projectKey: string | null
  projectName: string | null
  number: number
  title: string
  description: string | null
  type: IssueType
  status: IssueStatus
  priority: IssuePriority
  assigneeId: string | null
  assigneeName: string | null
  reporterId: string
  reporterName: string
  sprintId: string | null
  epicId: string | null
  epicTitle: string | null
  parentIssueId: string | null
  labelIds: string[]
  startDate: string | null
  dueDate: string | null
  storyPoints: number | null
  effortMd: string | null
  attachments: { fileId: string; originalName: string; url: string; size: number; contentType: string }[]
  order: number
  linkedSrId: string | null
  subtasks: SubtaskSummary[]
  createdAt: string
  updatedAt: string
}

export type Attachment = {
  fileId: string
  originalName: string
  url: string
  size: number
  contentType: string
}

export type IssueCreate = {
  title: string
  description?: string
  type?: IssueType
  status?: IssueStatus
  priority?: IssuePriority
  assignee_id?: string | null
  sprint_id?: string | null
  epic_id?: string | null
  parent_issue_id?: string | null
  label_ids?: string[]
  start_date?: string | null
  due_date?: string | null
  story_points?: number | null
  effort_md?: string | null
  attachments?: { file_id: string; original_name: string; url: string; size: number; content_type: string }[]
}

export type IssuePatch = Partial<IssueCreate & { order: number }>

export type MentionedUser = {
  userId: string
  displayName: string
}

export type IssueComment = {
  id: string
  issueId: string
  parentId: string | null
  authorId: string
  authorName: string
  content: string
  attachments: Attachment[]
  mentionedUsers: MentionedUser[]
  createdAt: string
  updatedAt: string
}

export type IssueHistory = {
  id: string
  issueId: string
  userId: string
  userName: string
  field: string
  oldValue: string | null
  newValue: string | null
  createdAt: string
}

export type Label = {
  id: string
  project_id: string
  name: string
  color: string
}

export type IssueFilter = {
  status?: IssueStatus
  assignee_id?: string
  priority?: IssuePriority
  sprint_id?: string
  type?: IssueType
  search?: string
  parent_issue_id?: string
}

export async function uploadAttachment(file: File): Promise<Attachment> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Attachment>('/pm/uploads', form)
  return data
}

export async function listIssues(projectId: string, filter?: IssueFilter) {
  const { data } = await api.get<Issue[]>(`/pm/projects/${projectId}/issues`, { params: filter })
  return data
}

export async function createIssue(projectId: string, payload: IssueCreate) {
  const { data } = await api.post<Issue>(`/pm/projects/${projectId}/issues`, payload)
  return data
}

export async function getIssue(projectId: string, issueId: string) {
  const { data } = await api.get<Issue>(`/pm/projects/${projectId}/issues/${issueId}`)
  return data
}

export async function updateIssue(projectId: string, issueId: string, payload: IssuePatch) {
  const { data } = await api.patch<Issue>(`/pm/projects/${projectId}/issues/${issueId}`, payload)
  return data
}

export async function deleteIssue(projectId: string, issueId: string) {
  await api.delete(`/pm/projects/${projectId}/issues/${issueId}`)
}

export async function listComments(projectId: string, issueId: string) {
  const { data } = await api.get<IssueComment[]>(`/pm/projects/${projectId}/issues/${issueId}/comments`)
  return data
}

export async function createComment(
  projectId: string,
  issueId: string,
  content: string,
  parentId?: string,
  attachments: Attachment[] = [],
  mentionedUserIds: string[] = [],
) {
  const { data } = await api.post<IssueComment>(
    `/pm/projects/${projectId}/issues/${issueId}/comments`,
    {
      content,
      ...(parentId ? { parent_id: parentId } : {}),
      attachments: attachments.map(a => ({
        file_id: a.fileId,
        original_name: a.originalName,
        url: a.url,
        size: a.size,
        content_type: a.contentType,
      })),
      mentioned_user_ids: mentionedUserIds,
    },
  )
  return data
}

export async function patchComment(
  projectId: string,
  issueId: string,
  commentId: string,
  content: string,
  mentionedUserIds: string[] = [],
) {
  const { data } = await api.patch<IssueComment>(
    `/pm/projects/${projectId}/issues/${issueId}/comments/${commentId}`,
    { content, mentioned_user_ids: mentionedUserIds },
  )
  return data
}

export async function deleteComment(projectId: string, issueId: string, commentId: string) {
  await api.delete(`/pm/projects/${projectId}/issues/${issueId}/comments/${commentId}`)
}

export async function getIssueHistory(projectId: string, issueId: string) {
  const { data } = await api.get<IssueHistory[]>(`/pm/projects/${projectId}/issues/${issueId}/history`)
  return data
}

export async function listLabels(projectId: string) {
  const { data } = await api.get<Label[]>(`/pm/projects/${projectId}/labels`)
  return data
}

export async function createLabel(projectId: string, payload: { name: string; color: string }) {
  const { data } = await api.post<Label>(`/pm/projects/${projectId}/labels`, payload)
  return data
}

export async function updateLabel(projectId: string, labelId: string, payload: { name: string; color: string }) {
  const { data } = await api.patch<Label>(`/pm/projects/${projectId}/labels/${labelId}`, payload)
  return data
}

export async function deleteLabel(projectId: string, labelId: string) {
  await api.delete(`/pm/projects/${projectId}/labels/${labelId}`)
}

export async function getBoard(projectId: string, sprintId?: string) {
  const { data } = await api.get<Record<IssueStatus, Issue[]>>(`/pm/projects/${projectId}/board`, {
    params: sprintId ? { sprint_id: sprintId } : {},
  })
  return data
}

export async function getWorkStatus(params: {
  start_date: string
  end_date: string
  project_id?: string
}) {
  const { data } = await api.get<Issue[]>('/pm/work-status', { params })
  return data
}
