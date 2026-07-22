import { api } from 'boot/axios'

// camelcaseKeys 인터셉터로 인해 응답은 camelCase로 변환됨
export interface SubMenuItem {
  title: string
  icon: string
  link: string
  requireAdmin?: boolean
}

export interface MenuOut {
  id: string
  title: string
  icon: string
  sortOrder: number | null
  isVisible: boolean
  isExternalVisible: boolean
  isInternalVisible: boolean
  isSystem: boolean
  slug: string | null
  subIcons?: Record<string, string> | null
  subOrder?: string[] | null
  link?: string | null
  submenus?: SubMenuItem[]
  visibleTeams?: string[]
  createdAt: string | null
}

export interface MenuCreate {
  title: string
  icon?: string
  sort_order?: number | null
  is_visible?: boolean
  link?: string | null
  visible_teams?: string[]
}

export interface MenuPatch {
  title?: string
  icon?: string
  sort_order?: number | null
  is_visible?: boolean
  is_external_visible?: boolean
  is_internal_visible?: boolean
  sub_icons?: Record<string, string> | null
  sub_order?: string[] | null
  link?: string | null
  visible_teams?: string[]
}

export const menuService = {
  list(visibleOnly = true): Promise<MenuOut[]> {
    return api.get('/menus', { params: { visible_only: visibleOnly } }).then((r) => r.data)
  },
  create(payload: MenuCreate): Promise<MenuOut> {
    return api.post('/menus', payload).then((r) => r.data)
  },
  patch(id: string, payload: MenuPatch): Promise<MenuOut> {
    return api.patch(`/menus/${id}`, payload).then((r) => r.data)
  },
  remove(id: string): Promise<void> {
    return api.delete(`/menus/${id}`)
  },
}
