// src/services/watch.ts
import { api } from 'src/boot/axios'

export type WatchRow = {
  id: string
  assignee: string
  start: string // ISO
  end: string   // ISO
  fields: Record<string, unknown>
  version: number
  is_deleted: boolean
  created_at: string
  created_by: string
  updated_at: string
  updated_by: string
}

export type WatchCreate = {
  assignee: string
  start: string
  end: string
  fields?: Record<string, unknown> | null
}

export type WatchPatch = Partial<{
  assignee: string
  start: string
  end: string
  fields: Record<string, unknown> | null
  version: number
}>

export async function listWatch(params?: { start?: string; end?: string; include_deleted?: boolean }) {
  const { data } = await api.get<WatchRow[]>('/watch', { params })
  return data
}

export async function createWatch(payload: WatchCreate) {
  const { data } = await api.post<WatchRow>('/watch', payload)
  return data
}

export async function patchWatch(id: string, payload: WatchPatch) {
  const { data } = await api.patch<WatchRow>(`/watch/${id}`, payload)
  return data
}

export async function deleteWatch(id: string) {
  await api.delete(`/watch/${id}`)
}
