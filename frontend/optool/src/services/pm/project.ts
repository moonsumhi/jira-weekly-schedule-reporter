import { api } from 'src/boot/axios'

export type ProjectRole = 'ADMIN' | 'PROJECT_MANAGER' | 'DEVELOPER' | 'VIEWER'

export type Project = {
  id: string
  orgId: string
  name: string
  key: string
  description: string | null
  isSrDefault: boolean
  createdAt: string
  updatedAt: string
}

export type ProjectMember = {
  id: string
  projectId: string
  userId: string
  userEmail: string
  userName: string
  role: ProjectRole
  joinedAt: string
}

export async function listProjects() {
  const { data } = await api.get<Project[]>('/pm/projects')
  return data
}

export async function createProject(payload: {
  org_id: string
  name: string
  key: string
  description?: string
}) {
  const { data } = await api.post<Project>('/pm/projects', payload)
  return data
}

export async function getProject(projectId: string) {
  const { data } = await api.get<Project>(`/pm/projects/${projectId}`)
  return data
}

export async function updateProject(projectId: string, payload: { name?: string; description?: string }) {
  const { data } = await api.patch<Project>(`/pm/projects/${projectId}`, payload)
  return data
}

export async function deleteProject(projectId: string) {
  await api.delete(`/pm/projects/${projectId}`)
}

export async function listProjectMembers(projectId: string) {
  const { data } = await api.get<ProjectMember[]>(`/pm/projects/${projectId}/members`)
  return data
}

export async function addProjectMember(projectId: string, userId: string, role: ProjectRole = 'DEVELOPER') {
  const { data } = await api.post<ProjectMember>(`/pm/projects/${projectId}/members`, { user_id: userId, role })
  return data
}

export async function changeProjectMemberRole(projectId: string, userId: string, role: ProjectRole) {
  const { data } = await api.patch<ProjectMember>(`/pm/projects/${projectId}/members/${userId}`, { role })
  return data
}

export async function removeProjectMember(projectId: string, userId: string) {
  await api.delete(`/pm/projects/${projectId}/members/${userId}`)
}

export async function setSrDefaultProject(projectId: string) {
  const { data } = await api.post<Project>(`/pm/projects/${projectId}/set-sr-default`)
  return data
}

export async function clearSrDefaultProject(projectId: string) {
  await api.delete(`/pm/projects/${projectId}/set-sr-default`)
}
