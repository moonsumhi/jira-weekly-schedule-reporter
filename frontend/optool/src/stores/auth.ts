import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from 'boot/axios'
import { getErrorMessage } from 'src/utils/http/error'

export type UserMe = {
  id: string | number
  email: string
  fullName?: string | null
  team?: string | null
  isAdmin?: boolean
  isInternal?: boolean
  permissions?: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('accessToken'))
  const me = ref<UserMe | null>(null)
  const loading = ref(false)
  const lastError = ref<string | null>(null)
  const pendingCount = ref(0)
  let meFetchedAt = 0

  async function fetchPendingCount() {
    try {
      const { data } = await api.get<{ id: string }[]>('/admin/users/pending', { params: { status: 'PENDING' } })
      pendingCount.value = Array.isArray(data) ? data.length : 0
    } catch {
      pendingCount.value = 0
    }
  }

  const isLoggedIn = computed(() => !!token.value)

  function setToken(t: string | null) {
    token.value = t
    if (t) localStorage.setItem('accessToken', t)
    else localStorage.removeItem('accessToken')
  }

  function authHeader() {
    return token.value ? { Authorization: `Bearer ${token.value}` } : {}
  }

  async function fetchMe(force = false) {
    if (!token.value) {
      me.value = null
      return null
    }
    // 30초 이내에 이미 가져왔으면 스킵 (force=true면 항상 호출)
    if (!force && me.value && Date.now() - meFetchedAt < 30_000) {
      return me.value
    }
    const res = await api.get<UserMe>('/auth/me', {
      headers: authHeader(),
    })
    me.value = res.data
    meFetchedAt = Date.now()
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

  async function register(email: string, password: string, fullName?: string, team?: string) {
    loading.value = true
    lastError.value = null
    try {
      await api.post('/auth/register', {
        email,
        password,
        full_name: fullName || null,
        team: team || null,
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
    token, me, loading, lastError, pendingCount,
    // getters
    isLoggedIn,
    // actions
    login, register, fetchMe, logout, bootstrap, fetchPendingCount, setToken,
  }
})
