import { api } from 'boot/axios'

export interface Link {
  id: string
  title: string
  url: string
  type: string
  color: string
  note?: string | null
  tags: string[]
  rank?: number | null
  isVisible: boolean
  createdAt?: string | null
}

export interface LinkCreate {
  title: string
  url: string
  type?: string
  color?: string
  note?: string | null
  tags?: string[]
  rank?: number | null
  is_visible?: boolean
}

export interface LinkPatch {
  title?: string
  url?: string
  type?: string
  color?: string
  note?: string | null
  tags?: string[]
  rank?: number | null
  is_visible?: boolean
}

export async function fetchLinks(visibleOnly = true): Promise<Link[]> {
  const { data } = await api.get<Link[]>('/links', { params: { visible_only: visibleOnly } })
  return data
}

export async function createLink(payload: LinkCreate): Promise<Link> {
  const { data } = await api.post<Link>('/links', payload)
  return data
}

export async function patchLink(id: string, payload: LinkPatch): Promise<Link> {
  const { data } = await api.patch<Link>(`/links/${id}`, payload)
  return data
}

export async function deleteLink(id: string): Promise<void> {
  await api.delete(`/links/${id}`)
}
