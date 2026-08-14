import { api } from 'boot/axios'

// camelcaseKeys 인터셉터로 인해 응답은 camelCase로 변환됨
export interface EnvItem {
  id: string
  label: string
  value?: string | null
  sortOrder: number
  isActive: boolean
}

export interface EnvCategoryOut {
  id: string
  key: string
  label: string
  isSystem: boolean
  items: EnvItem[]
}

export const envCategoryService = {
  list(): Promise<EnvCategoryOut[]> {
    return api.get('/env-categories').then((r) => r.data)
  },
  itemsByKey(key: string): Promise<EnvItem[]> {
    return api.get(`/env-categories/by-key/${key}`).then((r) => r.data)
  },
  createCategory(payload: { key: string; label: string }): Promise<EnvCategoryOut> {
    return api.post('/env-categories', payload).then((r) => r.data)
  },
  patchCategory(id: string, payload: { label?: string }): Promise<EnvCategoryOut> {
    return api.patch(`/env-categories/${id}`, payload).then((r) => r.data)
  },
  removeCategory(id: string): Promise<void> {
    return api.delete(`/env-categories/${id}`)
  },
  addItem(categoryId: string, payload: { label: string; value?: string }): Promise<EnvCategoryOut> {
    return api.post(`/env-categories/${categoryId}/items`, payload).then((r) => r.data)
  },
  patchItem(
    categoryId: string,
    itemId: string,
    payload: { label?: string; value?: string; sortOrder?: number; isActive?: boolean },
  ): Promise<EnvCategoryOut> {
    const body: Record<string, unknown> = {}
    if (payload.label !== undefined) body.label = payload.label
    if (payload.value !== undefined) body.value = payload.value
    if (payload.sortOrder !== undefined) body.sort_order = payload.sortOrder
    if (payload.isActive !== undefined) body.is_active = payload.isActive
    return api.patch(`/env-categories/${categoryId}/items/${itemId}`, body).then((r) => r.data)
  },
  removeItem(categoryId: string, itemId: string): Promise<EnvCategoryOut> {
    return api.delete(`/env-categories/${categoryId}/items/${itemId}`).then((r) => r.data)
  },
  reorderItems(categoryId: string, itemIds: string[]): Promise<EnvCategoryOut> {
    return api.put(`/env-categories/${categoryId}/items/reorder`, { item_ids: itemIds }).then((r) => r.data)
  },
}
