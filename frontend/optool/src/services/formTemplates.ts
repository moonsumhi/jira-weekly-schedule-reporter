// src/services/formTemplates.ts
import { api } from 'src/boot/axios'

export type FormField = {
  label: string
  type: string
  required?: boolean
  placeholder?: string
  options?: string[]
  // axios 인터셉터가 camelCase로 변환 (백엔드는 full_width)
  // textarea가 아니어도 값 칸을 한 줄 전체 폭으로 표시 (추출 파싱 경계는 type 그대로 유지하기 위함)
  fullWidth?: boolean
}

export type FormSection = {
  title: string
  fields: FormField[]
  multiple?: boolean
  // axios 인터셉터가 camelCase로 변환 (백엔드는 images_below)
  imagesBelow?: boolean
}

export type FormTemplate = {
  id: string
  title: string
  // axios 인터셉터가 응답 키를 camelCase로 변환하므로 jiraIssueKey (백엔드는 jira_issue_key)
  jiraIssueKey: string
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
