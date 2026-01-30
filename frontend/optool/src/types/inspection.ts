export type InspectionChecklist = {
  id: string
  inspection_month: string // YYYY-MM format
  person_in_charge: string // 담당자
  system_room_result: string // 시스템실 점검 결과
  resource_usage_abnormal: boolean // 자원사용량 이상 여부
  notes?: string | null // 비고
  created_at?: string | null
  created_by?: string | null
  updated_at?: string | null
  updated_by?: string | null
  version?: number | null
  is_deleted?: boolean | null
}

export type InspectionChecklistCreate = {
  inspection_month: string
  person_in_charge: string
  system_room_result: string
  resource_usage_abnormal: boolean
  notes?: string | null
}

export type InspectionChecklistPatch = {
  inspection_month?: string
  person_in_charge?: string
  system_room_result?: string
  resource_usage_abnormal?: boolean
  notes?: string | null
  version?: number
}

export type InspectionAction = 'CREATE' | 'UPDATE' | 'DELETE'
export type InspectionHistoryDiff = { path: string; before: unknown; after: unknown }

export type InspectionHistory = {
  id: string
  checklist_id: string
  action: InspectionAction
  changed_at: string
  changed_by?: string | null
  patch?: Record<string, unknown> | null
  diff?: InspectionHistoryDiff[] | null
}
