export interface Issue {
  key: string
  summary: string
  status: string
  url: string
  created: string
  duedate: string
  start: string
}

export interface AssigneeGroup {
  assignee: string
  count: number
  issues: Issue[]
}
