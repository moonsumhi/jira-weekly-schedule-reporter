import { api } from 'src/boot/axios'

export type ColPreset = { name: string; cols: string[] }
export type CardSize = { w: number; h: number }

export type UserPrefs = {
  assetColPresets: ColPreset[]
  dashboardCardOrder: string[]
  dashboardCardSizes: Record<string, CardSize>
}

export async function getPrefs(): Promise<UserPrefs> {
  const { data } = await api.get<UserPrefs>('/auth/prefs')
  return data
}

export async function savePrefs(prefs: UserPrefs): Promise<UserPrefs> {
  const { data } = await api.put<UserPrefs>('/auth/prefs', {
    asset_col_presets: prefs.assetColPresets,
    dashboard_card_order: prefs.dashboardCardOrder,
    dashboard_card_sizes: prefs.dashboardCardSizes,
  })
  return data
}
