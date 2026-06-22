import { api } from 'boot/axios'

export interface DDay {
  id: string
  title: string
  date: string
  color: string
  note?: string | null
  createdAt?: string | null
}

export interface DDayCreate {
  title: string
  date: string
  color?: string
  note?: string | null
}

export interface DDayPatch {
  title?: string
  date?: string
  color?: string
  note?: string | null
}

export async function fetchDDays(): Promise<DDay[]> {
  const { data } = await api.get<DDay[]>('/ddays')
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

export async function deleteDDay(id: string): Promise<void> {
  await api.delete(`/ddays/${id}`)
}
