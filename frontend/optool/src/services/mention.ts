import { api } from 'src/boot/axios'

export type MentionUser = {
  userId: string
  displayName: string
  team: string | null
  email: string
}

export async function searchMentionUsers(q: string, limit = 15): Promise<MentionUser[]> {
  if (!q.trim()) return []
  const { data } = await api.get<{ items: MentionUser[] }>('/auth/mention-search', {
    params: { q, limit },
  })
  return data.items
}
