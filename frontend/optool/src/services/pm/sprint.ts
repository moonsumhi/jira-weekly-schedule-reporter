import { api } from 'src/boot/axios'

export type SprintStatus = 'PLANNED' | 'ACTIVE' | 'COMPLETED'

export type Sprint = {
  id: string
  projectId: string
  name: string
  goal: string | null
  status: SprintStatus
  startDate: string | null
  endDate: string | null
  issueCount: number
  createdAt: string
  updatedAt: string
}

export async function listSprints(projectId: string) {
  const { data } = await api.get<Sprint[]>(`/pm/projects/${projectId}/sprints`)
  return data
}

export async function createSprint(projectId: string, payload: {
  name: string
  goal?: string
  start_date?: string
  end_date?: string
}) {
  const { data } = await api.post<Sprint>(`/pm/projects/${projectId}/sprints`, payload)
  return data
}

export async function updateSprint(projectId: string, sprintId: string, payload: {
  name?: string
  goal?: string
  status?: SprintStatus
  start_date?: string | null
  end_date?: string | null
}) {
  const { data } = await api.patch<Sprint>(`/pm/projects/${projectId}/sprints/${sprintId}`, payload)
  return data
}

export async function deleteSprint(projectId: string, sprintId: string) {
  await api.delete(`/pm/projects/${projectId}/sprints/${sprintId}`)
}
