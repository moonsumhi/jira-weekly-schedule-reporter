// src/services/formEntries.ts
import { api } from 'src/boot/axios'

type SectionValue = Record<string, string> | Record<string, string>[]
type EntryData = Record<string, SectionValue>

export type ImportSkipped = {
  section: string
  row: number
  reason: string
}

export type ImportResult = {
  data: EntryData
  skipped: ImportSkipped[]
}

export type FormEntry = {
  id: string
  templateId: string
  data: EntryData
  version: number
  isDeleted: boolean
  createdAt?: string | null
  createdBy?: string | null
  updatedAt?: string | null
  updatedBy?: string | null
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

  async importFromFile(templateId: string, file: File): Promise<ImportResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_id', templateId)
    const { data } = await api.post<ImportResult>('/form-entries/import', formData)
    return data
  },
}
