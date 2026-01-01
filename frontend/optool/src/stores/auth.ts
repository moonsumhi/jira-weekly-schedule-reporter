import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from 'boot/axios'
import type { AxiosError } from 'axios'

export type UserMe = {
  id: string | number
  email: string
  fullName?: string | null
  isAdmin? : boolean
}

type ApiErrorBody = {
  detail?: string
  message?: string
}

function getErrorMessage(err: unknown, fallback: string) {
  const e = err as AxiosError<ApiErrorBody>
  return e.response?.data?.detail || e.response?.data?.message || e.message || fallback
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('accessToken'))
  const me = ref<UserMe | null>(null)
  const loading = ref(false)
  const lastError = ref<string | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(t: string | null) {
    token.value = t
    if (t) localStorage.setItem('accessToken', t)
    else localStorage.removeItem('accessToken')
  }

  function authHeader() {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  async function fetchMe() {
    if (!token.value) {
      me.value = null
      return null
    }
    const res = await api.get<UserMe>('/auth/me', {
      headers: authHeader(),
    })
    me.value = res.data
    return me.value
  }

  async function login(email: string, password: string) {
    loading.value = true
    lastError.value = null
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const res = await api.post<{ accessToken: string }>(
        '/auth/login',
        formData,
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )

      setToken(res.data.accessToken)
      await fetchMe()
      return true
    } catch (err) {
      lastError.value = getErrorMessage(err, 'Login failed')
      // keep state clean if login failed
      setToken(null)
      me.value = null
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, fullName?: string) {
    loading.value = true
    lastError.value = null
    try {
      await api.post('/auth/register', {
        email,
        password,
        full_name: fullName || null,
      })
      return true
    } catch (err) {
      lastError.value = getErrorMessage(err, 'Register failed')
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    setToken(null)
    me.value = null
  }

  /**
   * Optional: call once on app boot to restore session.
   * If token is invalid/expired, it logs out.
   */
  async function bootstrap() {
    if (!token.value) return
    try {
      await fetchMe()
    } catch {
      logout()
    }
  }

  return {
    // state
    token, me, loading, lastError,
    // getters
    isLoggedIn,
    // actions
    login, register, fetchMe, logout, bootstrap,
  }
})
