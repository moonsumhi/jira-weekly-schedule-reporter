export type JobCategory = '정기' | '긴급' | '임시'
export type JobStatus = '초안' | '승인대기' | '승인됨' | '완료' | '취소'
export type JobAction = 'CREATE' | 'UPDATE' | 'DELETE'
export type JobOutcome = '성공' | '부분성공' | '실패'

export type JobWorkStep = {
  order: number
  task: string
  person: string
  duration?: string | null
}

export type ServiceWorkPlan = {
  id: string
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  purpose: string
  scope: string
  detail: string
  service_affected: boolean
  downtime?: string | null
  impact_scope?: string | null
  backup_done: boolean
  backup_details?: string | null
  steps: JobWorkStep[]
  rollback_possible: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  status: JobStatus
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
  version?: number | null
  is_deleted?: boolean | null
}

export type ServiceWorkPlanCreate = {
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  purpose: string
  scope: string
  detail: string
  service_affected: boolean
  downtime?: string | null
  impact_scope?: string | null
  backup_done: boolean
  backup_details?: string | null
  steps: JobWorkStep[]
  rollback_possible: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
}

export type ServiceWorkPlanPatch = {
  title?: string
  work_date?: string
  worker?: string
  requester?: string
  system_name?: string
  category?: JobCategory
  purpose?: string
  scope?: string
  detail?: string
  service_affected?: boolean
  downtime?: string | null
  impact_scope?: string | null
  backup_done?: boolean
  backup_details?: string | null
  steps?: JobWorkStep[]
  rollback_possible?: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  status?: JobStatus
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
  version?: number | undefined
}

export type JobHistoryDiff = { path: string; before: unknown; after: unknown }

export type ServiceWorkPlanHistory = {
  id: string
  plan_id: string
  action: JobAction
  changed_at: string
  changed_by?: string | null
  patch?: Record<string, unknown> | null
  diff?: JobHistoryDiff[] | null
}

// ─── 작업계획서(서비스 외) ─────────────────────────────────────────────────────

export type NonServiceWorkPlan = {
  id: string
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  purpose: string
  scope: string
  detail: string
  backup_done: boolean
  backup_details?: string | null
  steps: JobWorkStep[]
  rollback_possible: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  status: JobStatus
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
  version?: number | null
  is_deleted?: boolean | null
}

export type NonServiceWorkPlanCreate = {
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  purpose: string
  scope: string
  detail: string
  backup_done: boolean
  backup_details?: string | null
  steps: JobWorkStep[]
  rollback_possible: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
}

export type NonServiceWorkPlanPatch = {
  title?: string
  work_date?: string
  worker?: string
  requester?: string
  system_name?: string
  category?: JobCategory
  purpose?: string
  scope?: string
  detail?: string
  backup_done?: boolean
  backup_details?: string | null
  steps?: JobWorkStep[]
  rollback_possible?: boolean
  rollback_steps?: string | null
  rollback_duration?: string | null
  status?: JobStatus
  result_notes?: string | null
  work_summary?: string | null
  outcome?: JobOutcome | null
  issues_found?: string | null
  resolution?: string | null
  version?: number | undefined
}

export type NonServiceWorkPlanHistory = {
  id: string
  plan_id: string
  action: JobAction
  changed_at: string
  changed_by?: string | null
  patch?: Record<string, unknown> | null
  diff?: JobHistoryDiff[] | null
}

// ─── 작업결과서 ───────────────────────────────────────────────────────────────

export type JobResult = {
  id: string
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  work_summary: string
  issues_found?: string | null
  resolution?: string | null
  service_impact_actual?: string | null
  outcome: JobOutcome
  next_steps?: string | null
  related_plan_id?: string | null
  status: JobStatus
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
  version?: number | null
  is_deleted?: boolean | null
}

export type JobResultCreate = {
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  work_summary: string
  issues_found?: string | null
  resolution?: string | null
  service_impact_actual?: string | null
  outcome: JobOutcome
  next_steps?: string | null
  related_plan_id?: string | null
}

export type JobResultPatch = {
  title?: string
  work_date?: string
  worker?: string
  requester?: string
  system_name?: string
  category?: JobCategory
  work_summary?: string
  issues_found?: string | null
  resolution?: string | null
  service_impact_actual?: string | null
  outcome?: JobOutcome
  next_steps?: string | null
  related_plan_id?: string | null
  status?: JobStatus
  version?: number | undefined
}

export type JobResultHistory = {
  id: string
  plan_id: string
  action: JobAction
  changed_at: string
  changed_by?: string | null
  patch?: Record<string, unknown> | null
  diff?: JobHistoryDiff[] | null
}
