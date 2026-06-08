import { defineBoot } from '#q-app/wrappers'
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import camelcaseKeys from 'camelcase-keys'
import { Dialog } from 'quasar'
import type { Router } from 'vue-router'

import { useAuthStore } from 'stores/auth'

const BUILD_ID_KEY = 'app_build_id'
let knownBuildId: string | null = localStorage.getItem(BUILD_ID_KEY)
let buildDialogShown = false

function checkBuildId(
  buildId: string | undefined,
  auth: ReturnType<typeof useAuthStore>,
  router: Router,
) {
  if (!buildId || !auth.token) return
  if (!knownBuildId) {
    knownBuildId = buildId
    localStorage.setItem(BUILD_ID_KEY, buildId)
    return
  }
  if (knownBuildId !== buildId && !buildDialogShown) {
    buildDialogShown = true
    Dialog.create({
      title: '서버 업데이트',
      message: '새로운 버전이 배포되었습니다.\n페이지를 새로고침한 후 다시 로그인해주세요.',
      html: false,
      persistent: true,
      ok: { label: '다시 로그인', color: 'primary', unelevated: true },
      cancel: false,
    }).onOk(() => {
      localStorage.setItem(BUILD_ID_KEY, buildId)
      knownBuildId = buildId
      buildDialogShown = false
      auth.logout()
      void router.push({ name: 'auth' })
    })
  }
}

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

export default defineBoot(({ app, router }) => {
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
      checkBuildId(res.headers['x-build-id'] as string | undefined, auth, router)

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
