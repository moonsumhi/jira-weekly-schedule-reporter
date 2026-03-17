import { api } from 'boot/axios'
import type {
  ServiceWorkPlan,
  ServiceWorkPlanCreate,
  ServiceWorkPlanPatch,
  ServiceWorkPlanHistory,
} from 'src/types/job'

const ENDPOINT = '/job'

export async function listServiceWorkPlans(
  includeDeleted: boolean
): Promise<ServiceWorkPlan[]> {
  const res = await api.get<ServiceWorkPlan[]>(ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function getServiceWorkPlan(id: string): Promise<ServiceWorkPlan> {
  const res = await api.get<ServiceWorkPlan>(`${ENDPOINT}/${id}`)
  return res.data
}

export async function createServiceWorkPlan(
  payload: ServiceWorkPlanCreate
): Promise<ServiceWorkPlan> {
  const res = await api.post<ServiceWorkPlan>(ENDPOINT, payload)
  return res.data
}

export async function patchServiceWorkPlan(
  id: string,
  payload: ServiceWorkPlanPatch
): Promise<ServiceWorkPlan> {
  const res = await api.patch<ServiceWorkPlan>(`${ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteServiceWorkPlan(id: string): Promise<void> {
  await api.delete(`${ENDPOINT}/${id}`)
}

export async function getServiceWorkPlanHistory(
  id: string
): Promise<ServiceWorkPlanHistory[]> {
  const res = await api.get<ServiceWorkPlanHistory[]>(`${ENDPOINT}/${id}/history`)
  return res.data
}
