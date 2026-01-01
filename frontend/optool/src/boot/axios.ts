import { defineBoot } from '#q-app/wrappers'
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
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
  timeout: 20000,
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
      res.data = camelcaseKeys(res.data, { deep: true })
      return res
    },
    (err: unknown) => {
      // AxiosError is an Error, but keep lint happy even if it's unknown
      const error = err instanceof Error ? err : new Error(String(err))

      // If you need status check, you can safely narrow a bit:
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const status = (err as any)?.response?.status

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
