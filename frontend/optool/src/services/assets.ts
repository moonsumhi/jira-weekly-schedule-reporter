import { api } from 'boot/axios'
import type { AssetHistory, ServerAsset, FieldsMap } from 'src/types/assets'

const SERVERS = '/assets'

export async function listServers(includeDeleted: boolean, category?: string): Promise<ServerAsset[]> {
  const res = await api.get<ServerAsset[]>(SERVERS, {
    params: { include_deleted: includeDeleted, ...(category ? { category } : {}) },
  })
  return res.data
}

export async function createServer(ip: string, name: string, fields?: FieldsMap, assetNo?: string | null, category?: string, assetId?: string | null): Promise<ServerAsset> {
  const res = await api.post<ServerAsset>(SERVERS, { ip, name, fields: fields ?? {}, asset_id: assetId ?? null, asset_no: assetNo ?? null }, {
    params: category ? { category } : {},
  })
  return res.data
}

export async function patchServer(
  id: string,
  payload: Partial<Pick<ServerAsset, 'ip' | 'name'>> & { fields?: FieldsMap; asset_id?: string | null; asset_no?: string | null },
  category?: string,
): Promise<ServerAsset> {
  const res = await api.patch<ServerAsset>(`${SERVERS}/${id}`, payload, {
    params: category ? { category } : {},
  })
  return res.data
}

export async function deleteServer(id: string, reason?: string, category?: string): Promise<ServerAsset> {
  const res = await api.delete<ServerAsset>(`${SERVERS}/${id}`, {
    data: { reason: reason ?? null },
    params: category ? { category } : {},
  })
  return res.data
}

export async function restoreServer(id: string, category?: string): Promise<ServerAsset> {
  const res = await api.post<ServerAsset>(`${SERVERS}/${id}/restore`, undefined, {
    params: category ? { category } : {},
  })
  return res.data
}

export async function getServerHistory(id: string, category?: string): Promise<AssetHistory[]> {
  const res = await api.get<AssetHistory[]>(`${SERVERS}/${id}/history`, {
    params: category ? { category } : {},
  })
  return res.data
}
