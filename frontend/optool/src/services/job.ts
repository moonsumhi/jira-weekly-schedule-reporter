import { api } from 'boot/axios'
import type {
  ServiceWorkPlan,
  ServiceWorkPlanCreate,
  ServiceWorkPlanPatch,
  ServiceWorkPlanHistory,
  NonServiceWorkPlan,
  NonServiceWorkPlanCreate,
  NonServiceWorkPlanPatch,
  NonServiceWorkPlanHistory,
  JobResult,
  JobResultCreate,
  JobResultPatch,
  JobResultHistory,
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

// ─── 작업계획서(서비스 외) ─────────────────────────────────────────────────────

const NS_ENDPOINT = '/job/non-service'

export async function listNonServiceWorkPlans(
  includeDeleted: boolean
): Promise<NonServiceWorkPlan[]> {
  const res = await api.get<NonServiceWorkPlan[]>(NS_ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function getNonServiceWorkPlan(id: string): Promise<NonServiceWorkPlan> {
  const res = await api.get<NonServiceWorkPlan>(`${NS_ENDPOINT}/${id}`)
  return res.data
}

export async function createNonServiceWorkPlan(
  payload: NonServiceWorkPlanCreate
): Promise<NonServiceWorkPlan> {
  const res = await api.post<NonServiceWorkPlan>(NS_ENDPOINT, payload)
  return res.data
}

export async function patchNonServiceWorkPlan(
  id: string,
  payload: NonServiceWorkPlanPatch
): Promise<NonServiceWorkPlan> {
  const res = await api.patch<NonServiceWorkPlan>(`${NS_ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteNonServiceWorkPlan(id: string): Promise<void> {
  await api.delete(`${NS_ENDPOINT}/${id}`)
}

export async function getNonServiceWorkPlanHistory(
  id: string
): Promise<NonServiceWorkPlanHistory[]> {
  const res = await api.get<NonServiceWorkPlanHistory[]>(`${NS_ENDPOINT}/${id}/history`)
  return res.data
}

// ─── 작업결과서 ───────────────────────────────────────────────────────────────

const RESULT_ENDPOINT = '/job/result'

export async function listJobResults(includeDeleted: boolean): Promise<JobResult[]> {
  const res = await api.get<JobResult[]>(RESULT_ENDPOINT, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function getJobResult(id: string): Promise<JobResult> {
  const res = await api.get<JobResult>(`${RESULT_ENDPOINT}/${id}`)
  return res.data
}

export async function createJobResult(payload: JobResultCreate): Promise<JobResult> {
  const res = await api.post<JobResult>(RESULT_ENDPOINT, payload)
  return res.data
}

export async function patchJobResult(
  id: string,
  payload: JobResultPatch
): Promise<JobResult> {
  const res = await api.patch<JobResult>(`${RESULT_ENDPOINT}/${id}`, payload)
  return res.data
}

export async function deleteJobResult(id: string): Promise<void> {
  await api.delete(`${RESULT_ENDPOINT}/${id}`)
}

export async function getJobResultHistory(id: string): Promise<JobResultHistory[]> {
  const res = await api.get<JobResultHistory[]>(`${RESULT_ENDPOINT}/${id}/history`)
  return res.data
}
