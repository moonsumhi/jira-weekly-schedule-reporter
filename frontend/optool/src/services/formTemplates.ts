// src/services/formTemplates.ts
import { api } from 'src/boot/axios'

export type FormTemplate = {
  id: string
  title: string
  jira_issue_key: string
  sections: unknown[]
  menu: string | null
  sort_order: number | null
  created_at: string | null
}

export const formTemplateService = {
  async list(menu?: string): Promise<FormTemplate[]> {
    const params = menu ? { menu } : {}
    const { data } = await api.get<FormTemplate[]>('/form-templates', { params })
    return data
  },

  async get(id: string): Promise<FormTemplate> {
    const { data } = await api.get<FormTemplate>(`/form-templates/${id}`)
    return data
  },

  async patchSortOrder(id: string, sort_order: number): Promise<FormTemplate> {
    const { data } = await api.patch<FormTemplate>(`/form-templates/${id}`, { sort_order })
    return data
  },
}
