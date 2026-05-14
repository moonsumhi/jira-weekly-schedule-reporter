import { defineBoot } from '#q-app/wrappers'
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import camelcaseKeys from 'camelcase-keys'

import { useAuthStore } from 'stores/auth'

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance
    $api: AxiosInstance
  }
}

/**
 * Axios instance for API calls
 */
const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
})

export default defineBoot(({ app }) => {
  const auth = useAuthStore()

  /**
   * Attach Authorization header automatically
   */
  const attachAuth = (config: InternalAxiosRequestConfig) => {
    if (auth.token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${auth.token}`
    }
    return config
  }

  /**
   * Request interceptors
   */
  axios.interceptors.request.use(attachAuth)
  api.interceptors.request.use(attachAuth)

  /**
   * Optional: handle 401 globally (token expired, revoked, etc.)
   */
  api.interceptors.response.use(
    (res) => {
      // Skip transformation for binary responses (blob, arraybuffer)
      if (res.config.responseType === 'blob' || res.config.responseType === 'arraybuffer') {
        return res
      }

      // Preserve user-defined 'fields' dict keys before camelCase transformation.
      // camelcaseKeys deep: true would transform e.g. eos_action_status → eosActionStatus
      // inside fields, but the frontend uses the original snake_case keys.
      type WithFields = { fields?: unknown }
      const saveFields = (item: unknown): unknown => {
        if (item && typeof item === 'object' && 'fields' in item) {
          return (item as WithFields).fields
        }
        return undefined
      }

      const savedFields = Array.isArray(res.data)
        ? res.data.map(saveFields)
        : saveFields(res.data)

      res.data = camelcaseKeys(res.data, { deep: true, exclude: [/[가-힣]/, /^[A-Z][A-Z0-9]*$/, /^\//] })

      // Restore original fields keys
      if (Array.isArray(res.data) && Array.isArray(savedFields)) {
        res.data.forEach((item: unknown, i: number) => {
          if (item && typeof item === 'object' && 'fields' in item && savedFields[i] !== undefined) {
            ;(item as WithFields).fields = savedFields[i]
          }
        })
      } else if (res.data && typeof res.data === 'object' && 'fields' in res.data && savedFields !== undefined) {
        ;(res.data as WithFields).fields = savedFields
      }

      return res
    },
    (err: unknown) => {
      const error = err instanceof Error ? err : new Error(String(err))
      const status = (err as AxiosError)?.response?.status

      if (status === 401) {
        // If logout() is async, change your store typing so it returns Promise<void>,
        // then you can restore `return auth.logout().finally(() => Promise.reject(error))`
        auth.logout()
      }

      return Promise.reject(error)
    }
  )

  // Make available in Options API
  app.config.globalProperties.$axios = axios
  app.config.globalProperties.$api = api
})

export { api }
