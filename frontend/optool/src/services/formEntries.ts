// src/services/formEntries.ts
import { api } from 'src/boot/axios'

type SectionValue = Record<string, string> | Record<string, string>[]
type EntryData = Record<string, SectionValue>

export type FormEntry = {
  id: string
  template_id: string
  data: EntryData
  version: number
  is_deleted: boolean
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
}

export const formEntryService = {
  async list(templateId: string, includeDeleted = false): Promise<FormEntry[]> {
    const { data } = await api.get<FormEntry[]>('/form-entries', {
      params: { template_id: templateId, include_deleted: includeDeleted },
    })
    return data
  },

  async create(templateId: string, entryData: EntryData): Promise<FormEntry> {
    const { data } = await api.post<FormEntry>('/form-entries', {
      template_id: templateId,
      data: entryData,
    })
    return data
  },

  async patch(id: string, entryData: EntryData, version: number): Promise<FormEntry> {
    const { data } = await api.patch<FormEntry>(`/form-entries/${id}`, {
      data: entryData,
      version,
    })
    return data
  },

  async remove(id: string): Promise<void> {
    await api.delete(`/form-entries/${id}`)
  },

  async importFromFile(templateId: string, file: File): Promise<EntryData> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_id', templateId)
    const { data } = await api.post<{ data: EntryData }>('/form-entries/import', formData)
    return data.data
  },
}
