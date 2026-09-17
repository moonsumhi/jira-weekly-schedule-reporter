import { api } from 'src/boot/axios'
import type { AssetWorkDocument } from './formEntries'
import type { InspectionTask } from './inspection'

export type AssetNote = {
  type: 'note'; id: string; assetId: string; content: string; occurredOn: string;
  version: number; createdBy: string; createdAt: string; updatedBy: string; updatedAt: string; canEdit: boolean;
}
export type AssetInspectionHistory = InspectionTask & { type: 'inspection'; id: string; createdAt: string }
export type AssetIssueHistory = { type: 'issue'; id: string; issue: InspectionTask['issue']; createdAt: string; startDate: string | null; dueDate: string | null }
export type AssetWorkHistoryItem = (AssetWorkDocument & { type: 'document' }) | AssetNote | AssetInspectionHistory | AssetIssueHistory
export type AssetNoteValues = { content: string; occurred_on: string }

export async function listAssetWorkHistory(assetId: string, offset = 0) {
  return (await api.get<{ total: number; items: AssetWorkHistoryItem[] }>(`/assets/${assetId}/work-history`, {
    params: { offset, limit: 20 },
  })).data
}
export async function getAssetNote(assetId: string, id: string): Promise<AssetNote> {
  return (await api.get<AssetNote>(`/assets/${assetId}/notes/${id}`)).data
}
export async function createAssetNote(assetId: string, values: AssetNoteValues, clientId: string): Promise<AssetNote> {
  return (await api.post<AssetNote>(`/assets/${assetId}/notes`, { ...values, client_id: clientId })).data
}
export async function updateAssetNote(assetId: string, note: AssetNote, values: AssetNoteValues): Promise<AssetNote> {
  return (await api.patch<AssetNote>(`/assets/${assetId}/notes/${note.id}`, { ...values, version: note.version })).data
}
export async function deleteAssetNote(assetId: string, note: AssetNote): Promise<void> {
  await api.delete(`/assets/${assetId}/notes/${note.id}`, { data: { version: note.version } })
}
