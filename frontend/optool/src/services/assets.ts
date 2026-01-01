import { api } from 'boot/axios'
import type { AssetHistory, ServerAsset, FieldsMap } from 'src/types/assets'

const SERVERS = '/assets'

export async function listServers(includeDeleted: boolean): Promise<ServerAsset[]> {
  const res = await api.get<ServerAsset[]>(SERVERS, {
    params: { include_deleted: includeDeleted },
  })
  return res.data
}

export async function createServer(ip: string, name: string): Promise<ServerAsset> {
  const res = await api.post<ServerAsset>(SERVERS, { ip, name, fields: {} })
  return res.data
}

export async function patchServer(
  id: string,
  payload: Partial<Pick<ServerAsset, 'ip' | 'name'>> | { fields: FieldsMap }
): Promise<ServerAsset> {
  const res = await api.patch<ServerAsset>(`${SERVERS}/${id}`, payload)
  return res.data
}

export async function deleteServer(id: string): Promise<void> {
  await api.delete(`${SERVERS}/${id}`)
}

export async function getServerHistory(id: string): Promise<AssetHistory[]> {
  const res = await api.get<AssetHistory[]>(`${SERVERS}/${id}/history`)
  return res.data
}
