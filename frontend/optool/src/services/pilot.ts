// src/services/pilot.ts
import { api } from 'src/boot/axios'

export type PilotTask = {
  issue_key: string
  status: string
  sent_at: string | null
  completed_at: string | null
  failed_at: string | null
  pr_url: string | null
  error: string | null
}

export async function listPilotTasks() {
  const { data } = await api.get<PilotTask[]>('/pilot/tasks')
  return data
}
