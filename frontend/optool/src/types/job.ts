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
  impact_scope?: string | null
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
  impact_scope?: string | null
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
  impact_scope?: string | null
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

export type JobWorkStepResult = {
  order: number
  task: string
  person: string
  completed: boolean
  notes?: string | null
}

export type ServiceWorkResult = {
  id: string
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  result: JobOutcome
  actual_start_time?: string | null
  actual_end_time?: string | null
  summary: string
  service_affected: boolean
  actual_downtime?: string | null
  step_results: JobWorkStepResult[]
  issues_occurred: boolean
  issue_details?: string | null
  action_taken?: string | null
  post_check_done: boolean
  post_check_details?: string | null
  plan_id?: string | null
  notes?: string | null
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
  version?: number | null
  is_deleted?: boolean | null
}

export type ServiceWorkResultCreate = {
  title: string
  work_date: string
  worker: string
  requester: string
  system_name: string
  category: JobCategory
  result: JobOutcome
  actual_start_time?: string | null
  actual_end_time?: string | null
  summary: string
  service_affected: boolean
  actual_downtime?: string | null
  step_results: JobWorkStepResult[]
  issues_occurred: boolean
  issue_details?: string | null
  action_taken?: string | null
  post_check_done: boolean
  post_check_details?: string | null
  plan_id?: string | null
  notes?: string | null
}

export type ServiceWorkResultPatch = {
  title?: string
  work_date?: string
  worker?: string
  requester?: string
  system_name?: string
  category?: JobCategory
  result?: JobOutcome
  actual_start_time?: string | null
  actual_end_time?: string | null
  summary?: string
  service_affected?: boolean
  actual_downtime?: string | null
  step_results?: JobWorkStepResult[]
  issues_occurred?: boolean
  issue_details?: string | null
  action_taken?: string | null
  post_check_done?: boolean
  post_check_details?: string | null
  plan_id?: string | null
  notes?: string | null
  version?: number | undefined
}

export type ServiceWorkResultHistory = {
  id: string
  result_id: string
  action: JobAction
  changed_at: string
  changed_by?: string | null
  patch?: Record<string, unknown> | null
  diff?: JobHistoryDiff[] | null
}

