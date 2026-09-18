import type { AssetCategory, AssetLink } from './assetLinks'
// src/services/formEntries.ts
import { api } from 'src/boot/axios'

type RowData = Record<string, string | string[]>
type SectionValue = RowData | RowData[]
type EntryData = Record<string, SectionValue>

export type ImportSkipped = {
  section: string
  row: number
  reason: string
}

export type ImportImageGroup = {
  caption: string
  images: string[]
}

export type OriginalFile = {
  url: string
  originalName: string
  contentType?: string | null
  size?: number | null
}

export type ImportResult = {
  data: EntryData
  skipped: ImportSkipped[]
  images?: string[]
  imageGroups?: ImportImageGroup[]
  originalFile?: OriginalFile | null
}

export type FormEntry = {
  id: string
  templateId: string
  data: EntryData
  linkedAssets?: WorkDocumentAsset[]
  originalFile?: OriginalFile | null
  version: number
  isDeleted: boolean
  createdAt?: string | null
  createdBy?: string | null
  updatedAt?: string | null
  updatedBy?: string | null
}

export type WorkDocumentAsset = AssetLink
export type AssetWorkDocument = {
  id: string; templateId: string; templateTitle: string; title: string; workDate: string;
  dateLabel?: string;
  createdAt: string | null; createdBy: string | null; assetCount: number;
}

export async function searchWorkDocumentAssets(search = '', category?: AssetCategory) {
  return (await api.get<WorkDocumentAsset[]>('/form-entries/asset-options', { params: { search, category } })).data
}

export async function listAssetWorkDocuments(assetId: string, offset = 0) {
  return (await api.get<{ total: number; items: AssetWorkDocument[] }>(`/form-entries/by-asset/${assetId}`, {
    params: { offset, limit: 20 },
  })).data
}

export const formEntryService = {
  async list(templateId: string, includeDeleted = false): Promise<FormEntry[]> {
    const { data } = await api.get<FormEntry[]>('/form-entries', {
      params: { template_id: templateId, include_deleted: includeDeleted },
    })
    return data
  },

  async get(id: string): Promise<FormEntry> {
    const { data } = await api.get<FormEntry>(`/form-entries/${id}`)
    return data
  },

  async create(templateId: string, entryData: EntryData, originalFile?: OriginalFile | null, assetIds?: string[]): Promise<FormEntry> {
    const { data } = await api.post<FormEntry>('/form-entries', {
      template_id: templateId,
      data: entryData,
      ...(assetIds !== undefined ? { asset_ids: assetIds } : {}),
      ...(originalFile ? {
        original_file: {
          url: originalFile.url,
          original_name: originalFile.originalName,
          content_type: originalFile.contentType,
          size: originalFile.size,
        },
      } : {}),
    })
    return data
  },

  async patch(id: string, entryData: EntryData, version: number, assetIds?: string[]): Promise<FormEntry> {
    const { data } = await api.patch<FormEntry>(`/form-entries/${id}`, {
      data: entryData,
      version,
      ...(assetIds !== undefined ? { asset_ids: assetIds } : {}),
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
