import { api } from 'boot/axios'

export interface DDay {
  id: string
  title: string
  date: string
  color: string
  note?: string | null
  visibleUserIds?: string[]
  visibleTeams?: string[]
  visibleToAll?: boolean
  createdAt?: string | null
  createdBy?: string | null
  completed?: boolean
  completedAt?: string | null
}

export interface DDayCreate {
  title: string
  date: string
  color?: string
  note?: string | null
  visible_user_ids?: string[]
  visible_teams?: string[]
  visible_to_all?: boolean
}

export interface DDayPatch {
  title?: string
  date?: string
  color?: string
  note?: string | null
  visible_user_ids?: string[]
  visible_teams?: string[]
  visible_to_all?: boolean
}

export interface DDayAudienceUser {
  id: string
  email: string
  fullName?: string | null
  team?: string | null
}

export async function fetchDDays(): Promise<DDay[]> {
  const { data } = await api.get<DDay[]>('/ddays')
  return data
}

export async function fetchDDayAudience(): Promise<DDayAudienceUser[]> {
  const { data } = await api.get<DDayAudienceUser[]>('/ddays/audience')
  return data
}

export async function createDDay(payload: DDayCreate): Promise<DDay> {
  const { data } = await api.post<DDay>('/ddays', payload)
  return data
}

export async function patchDDay(id: string, payload: DDayPatch): Promise<DDay> {
  const { data } = await api.patch<DDay>(`/ddays/${id}`, payload)
  return data
}

export async function completeDDay(id: string): Promise<DDay> {
  const { data } = await api.post<DDay>('/ddays/' + id + '/complete')
  return data
}

export async function deleteDDay(id: string): Promise<void> {
  await api.delete(`/ddays/${id}`)
}
