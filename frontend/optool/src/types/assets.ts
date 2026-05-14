export type FieldPrimitive = string | number | boolean | null
export type FieldValue = FieldPrimitive | Record<string, unknown> | unknown[]
export type FieldsMap = Record<string, FieldValue>

export type ServerAsset = {
  id: string
  ip: string
  name: string
  assetId?: string | null
  assetNo?: string | null
  fields: FieldsMap
  createdAt?: string | null
  createdBy?: string | null
  updatedAt?: string | null
  updatedBy?: string | null
  version?: number | null
  isDeleted?: boolean | null
  deleteReason?: string | null
  deletedAt?: string | null
  deletedBy?: string | null
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
  { label: '지원 기간 중', value: 'ACTIVE' },
  { label: 'EoS 지남', value: 'EOS' },
] as const

export type EosActionStatus = typeof eosStatusOptions[number]['value']
