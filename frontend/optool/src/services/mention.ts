import { api } from 'src/boot/axios'

export type MentionUser = {
  userId: string
  displayName: string
  team: string | null
  email: string
  hasProjectAccess?: boolean
}

export async function searchMentionUsers(q: string, limit = 15, projectId?: string): Promise<MentionUser[]> {
  const { data } = await api.get<{ items: MentionUser[] }>('/auth/mention-search', {
    params: { q, limit, ...(projectId ? { project_id: projectId } : {}) },
  })
  return data.items
}
