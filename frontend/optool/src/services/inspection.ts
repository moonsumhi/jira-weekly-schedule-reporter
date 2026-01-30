import { api } from 'boot/axios'
import type {
  InspectionChecklist,
  InspectionChecklistCreate,
  InspectionChecklistPatch,
  InspectionHistory,
} from 'src/types/inspection'

const ENDPOINT = '/inspection'

export async function listInspectionChecklists(
  includeDeleted: boolean
): Promise<InspectionChecklist[]> {
  const res = await api.get<InspectionChecklist[]>(ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function createInspectionChecklist(
  payload: InspectionChecklistCreate
): Promise<InspectionChecklist> {
  const res = await api.post<InspectionChecklist>(ENDPOINT, payload)
  return res.data
}

export async function patchInspectionChecklist(
  id: string,
  payload: InspectionChecklistPatch
): Promise<InspectionChecklist> {
  const res = await api.patch<InspectionChecklist>(`${ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteInspectionChecklist(id: string): Promise<void> {
  await api.delete(`${ENDPOINT}/${id}`)
}

export async function getInspectionHistory(id: string): Promise<InspectionHistory[]> {
  const res = await api.get<InspectionHistory[]>(`${ENDPOINT}/${id}/history`)
  return res.data
}
