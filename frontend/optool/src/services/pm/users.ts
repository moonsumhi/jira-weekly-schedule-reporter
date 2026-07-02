import { api } from 'src/boot/axios'

export type PmUser = { id: string; name: string; email: string; team?: string }

export async function listPmUsers(team?: string): Promise<PmUser[]> {
  const { data } = await api.get<PmUser[]>('/pm/users', {
    params: team ? { team } : {},
  })
  return data
}
