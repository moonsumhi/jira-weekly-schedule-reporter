export type FieldPrimitive = string | number | boolean | null
export type FieldValue = FieldPrimitive | Record<string, unknown> | unknown[]
export type FieldsMap = Record<string, FieldValue>

export type ServerAsset = {
  id: string
  ip: string
  name: string
  fields: FieldsMap
  createdAt?: string | null
  createdBy?: string | null
  updatedAt?: string | null
  updatedBy?: string | null
  version?: number | null
  isDeleted?: boolean | null
}

export type AssetAction = 'CREATE' | 'UPDATE' | 'DELETE'
export type HistoryDiff = { path: string; before: unknown; after: unknown }

export type AssetHistory = {
  id: string
  assetId: string
  action: AssetAction
  changedAt: string

  changedBy?: string | null
  createdBy?: string | null

  patch?: Record<string, unknown> | null
  diff?: HistoryDiff[] | null
}

export const EOS_STATUS_KEY = 'eos_action_status' as const
export const EOS_DATE_KEY = 'eos_date' as const

export const eosStatusOptions = [
  { label: '미조치', value: 'NONE' },
  { label: '계획', value: 'PLAN' },
  { label: '진행', value: 'DOING' },
  { label: '완료', value: 'DONE' },
  { label: '예외', value: 'EXCEPTION' },
] as const

export type EosActionStatus = typeof eosStatusOptions[number]['value']
