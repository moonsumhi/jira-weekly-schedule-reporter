import { api } from 'boot/axios'
import type {
  AssetSearchResult,
  IntegrityReport,
  MountSide,
  PlacementHistory,
  RackLayout,
  RackPlacement,
  RackSummary,
  UnplacedAsset,
} from 'src/types/racks'

const BASE = '/racks'

export async function listRacks(serverRoom?: string): Promise<RackSummary[]> {
  const res = await api.get<RackSummary[]>(BASE, {
    params: serverRoom ? { server_room: serverRoom } : {},
  })
  return res.data
}

export async function getRackLayout(rackId: string): Promise<RackLayout> {
  const res = await api.get<RackLayout>(`${BASE}/${rackId}/layout`)
  return res.data
}

export async function searchRackAssets(q: string): Promise<AssetSearchResult[]> {
  const res = await api.get<AssetSearchResult[]>(`${BASE}/assets/search`, { params: { q } })
  return res.data
}

export async function listUnplacedAssets(category?: string): Promise<UnplacedAsset[]> {
  const res = await api.get<UnplacedAsset[]>(`${BASE}/assets/unplaced`, {
    params: category ? { category } : {},
  })
  return res.data
}

export async function getRackHistory(rackId: string): Promise<PlacementHistory[]> {
  const res = await api.get<PlacementHistory[]>(`${BASE}/${rackId}/history`)
  return res.data
}

export async function integrityCheck(): Promise<IntegrityReport> {
  const res = await api.get<IntegrityReport>(`${BASE}/integrity-check`)
  return res.data
}

export type RackMigrationReport = {
  dryRun: boolean
  racksToCreate?: string[]
  racksCreated?: string[]
  placementsCreated: number
  skippedNoUnit: number
  skippedAlreadyPlaced: number
  skippedConflict: number
}

export async function migrateRackFromFields(dryRun: boolean): Promise<RackMigrationReport> {
  const res = await api.post<RackMigrationReport>(`${BASE}/migrate-from-fields`, undefined, {
    params: { dry_run: dryRun },
  })
  return res.data
}

export type PlacementInput = {
  assetCategory: string
  assetId: string
  rackId: string
  startU: number
  heightU: number
  mountSide: MountSide
}

export async function createPlacement(input: PlacementInput): Promise<RackPlacement> {
  const res = await api.post<RackPlacement>(`${BASE}/placements`, {
    asset_category: input.assetCategory,
    asset_id: input.assetId,
    rack_id: input.rackId,
    start_u: input.startU,
    height_u: input.heightU,
    mount_side: input.mountSide,
  })
  return res.data
}

export type MoveInput = {
  rackId: string
  startU: number
  heightU: number
  mountSide: MountSide
  expectedVersion?: number | undefined
}

export async function movePlacement(placementId: string, input: MoveInput): Promise<RackPlacement> {
  const res = await api.put<RackPlacement>(`${BASE}/placements/${placementId}`, {
    rack_id: input.rackId,
    start_u: input.startU,
    height_u: input.heightU,
    mount_side: input.mountSide,
    expected_version: input.expectedVersion ?? null,
  })
  return res.data
}

export async function removePlacement(placementId: string): Promise<RackPlacement> {
  const res = await api.delete<RackPlacement>(`${BASE}/placements/${placementId}`)
  return res.data
}
