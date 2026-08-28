// 랙 배치 관련 타입. 응답은 axios 인터셉터가 camelCase 로 변환한다.
export type MountSide = 'FULL' | 'FRONT' | 'REAR'

export type RackSummary = {
  rackId: string
  assetCode?: string | null
  name: string
  serverRoom?: string | null
  totalU: number
  usedU: number
  freeU: number
  usageRate: number
  maxContiguousFreeU: number
  assetCount: number
  status?: string | null
  maxLoadKg?: number | null
  maxPowerW?: number | null
}

export type UnplacedAsset = {
  assetCategory: string
  assetId: string
  assetCode?: string | null
  assetNo?: string | null
  name: string
  ip?: string | null
}

export type PlacementHistoryPos = {
  rackId?: string | null
  rackName?: string | null
  startU?: number | null
  endU?: number | null
  mountSide?: string | null
}

export type PlacementHistory = {
  id: string
  action: string
  assetCategory?: string | null
  assetId?: string | null
  assetName?: string | null
  before?: PlacementHistoryPos | null
  after?: PlacementHistoryPos | null
  changedAt: string
  changedBy?: string | null
}

export type IntegrityIssue = {
  type: string
  placementId: string
  assetCategory?: string | null
  assetId?: string | null
  detail?: string | null
}

export type IntegrityReport = {
  checkedAt: string
  status: string
  issueCount: number
  issues: IntegrityIssue[]
}

export type RackPlacementAsset = {
  placementId: string      // 배치 문서 _id (이동/반출용)
  assetCategory: string
  assetId: string          // 자산의 Mongo _id
  assetCode?: string | null
  assetNo?: string | null
  name: string
  ip?: string | null
  startU: number
  endU: number
  heightU: number
  mountSide: MountSide
  version: number
}

export type RackLayout = {
  rack: RackSummary
  placements: RackPlacementAsset[]
}

export type AssetSearchResult = {
  assetCategory: string
  assetId: string
  assetCode?: string | null
  assetNo?: string | null
  name: string
  ip?: string | null
  placement?: {
    rackId: string
    rackName?: string | null
    serverRoom?: string | null
    startU: number
    endU: number
  } | null
}

export type RackPlacement = {
  id: string
  assetCategory: string
  assetId: string
  rackId: string
  startU: number
  heightU: number
  endU: number
  mountSide: MountSide
  occupiedSlots: string[]
  version: number
  isDeleted: boolean
}
