import { api } from 'boot/axios'

export interface SettingOut {
  key: string
  value: string | null
}

export const settingsService = {
  get(key: string): Promise<SettingOut> {
    return api.get(`/settings/${key}`).then((r) => r.data)
  },
  put(key: string, value: string): Promise<SettingOut> {
    return api.put(`/settings/${key}`, { value }).then((r) => r.data)
  },
}
