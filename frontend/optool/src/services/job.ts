import { api } from 'boot/axios'
import type {
  ServiceWorkPlan,
  ServiceWorkPlanCreate,
  ServiceWorkPlanPatch,
  ServiceWorkPlanHistory,
  ServiceWorkResult,
  ServiceWorkResultCreate,
  ServiceWorkResultPatch,
  ServiceWorkResultHistory,
  NonServiceWorkPlan,
  NonServiceWorkPlanCreate,
  NonServiceWorkPlanPatch,
  NonServiceWorkPlanHistory,
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

// ─── 작업 결과서 API ──────────────────────────────────────────────────────────

const RESULT_ENDPOINT = '/job-result'

export async function listServiceWorkResults(
  includeDeleted: boolean
): Promise<ServiceWorkResult[]> {
  const res = await api.get<ServiceWorkResult[]>(RESULT_ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function getServiceWorkResult(id: string): Promise<ServiceWorkResult> {
  const res = await api.get<ServiceWorkResult>(`${RESULT_ENDPOINT}/${id}`)
  return res.data
}

export async function createServiceWorkResult(
  payload: ServiceWorkResultCreate
): Promise<ServiceWorkResult> {
  const res = await api.post<ServiceWorkResult>(RESULT_ENDPOINT, payload)
  return res.data
}

export async function patchServiceWorkResult(
  id: string,
  payload: ServiceWorkResultPatch
): Promise<ServiceWorkResult> {
  const res = await api.patch<ServiceWorkResult>(`${RESULT_ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteServiceWorkResult(id: string): Promise<void> {
  await api.delete(`${RESULT_ENDPOINT}/${id}`)
}

export async function getServiceWorkResultHistory(
  id: string
): Promise<ServiceWorkResultHistory[]> {
  const res = await api.get<ServiceWorkResultHistory[]>(`${RESULT_ENDPOINT}/${id}/history`)
  return res.data
}

// ─── 작업계획서(서비스 외) API ────────────────────────────────────────────────

const NON_SERVICE_ENDPOINT = '/job-non-service'

export async function listNonServiceWorkPlans(
  includeDeleted: boolean
): Promise<NonServiceWorkPlan[]> {
  const res = await api.get<NonServiceWorkPlan[]>(NON_SERVICE_ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function getNonServiceWorkPlan(id: string): Promise<NonServiceWorkPlan> {
  const res = await api.get<NonServiceWorkPlan>(`${NON_SERVICE_ENDPOINT}/${id}`)
  return res.data
}

export async function createNonServiceWorkPlan(
  payload: NonServiceWorkPlanCreate
): Promise<NonServiceWorkPlan> {
  const res = await api.post<NonServiceWorkPlan>(NON_SERVICE_ENDPOINT, payload)
  return res.data
}

export async function patchNonServiceWorkPlan(
  id: string,
  payload: NonServiceWorkPlanPatch
): Promise<NonServiceWorkPlan> {
  const res = await api.patch<NonServiceWorkPlan>(`${NON_SERVICE_ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteNonServiceWorkPlan(id: string): Promise<void> {
  await api.delete(`${NON_SERVICE_ENDPOINT}/${id}`)
}

export async function getNonServiceWorkPlanHistory(
  id: string
): Promise<NonServiceWorkPlanHistory[]> {
  const res = await api.get<NonServiceWorkPlanHistory[]>(`${NON_SERVICE_ENDPOINT}/${id}/history`)
  return res.data
}
