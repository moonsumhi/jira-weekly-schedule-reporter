// src/services/pilot.ts
import { api } from 'src/boot/axios'

export type PilotTask = {
  issue_key: string
  issue_url: string | null
  summary: string | null
  project_key: string | null
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
