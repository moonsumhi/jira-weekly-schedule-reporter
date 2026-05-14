// src/services/formTemplates.ts
import { api } from 'src/boot/axios'

export type FormField = {
  label: string
  type: string
  required?: boolean
  placeholder?: string
  options?: string[]
}

export type FormSection = {
  title: string
  fields: FormField[]
  multiple?: boolean
}

export type FormTemplate = {
  id: string
  title: string
  jira_issue_key: string
  sections: FormSection[]
  menu: string | null
  sort_order: number | null
  is_deleted: boolean
  created_at: string | null
}

export const formTemplateService = {
  async list(menu?: string, includeDeleted = false): Promise<FormTemplate[]> {
    const params: Record<string, unknown> = {}
    if (menu) params.menu = menu
    if (includeDeleted) params.include_deleted = true
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

  async delete(id: string): Promise<FormTemplate> {
    const { data } = await api.delete<FormTemplate>(`/form-templates/${id}`)
    return data
  },

  async restore(id: string): Promise<FormTemplate> {
    const { data } = await api.post<FormTemplate>(`/form-templates/${id}/restore`)
    return data
  },
}
