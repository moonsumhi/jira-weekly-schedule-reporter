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

/** JWT의 exp/iat(초) 클레임을 epoch ms로 반환. 디코드 실패 시 둘 다 null. */
function decodeTokenClaims(t: string): { exp: number | null; iat: number | null } {
  try {
    const payload = t.split('.')[1]
    if (!payload) return { exp: null, iat: null }
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = JSON.parse(decodeURIComponent(escape(window.atob(base64)))) as { exp?: number; iat?: number }
    return {
      exp: typeof json.exp === 'number' ? json.exp * 1000 : null,
      iat: typeof json.iat === 'number' ? json.iat * 1000 : null,
    }
  } catch {
    return { exp: null, iat: null }
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('accessToken'))
  const initialClaims = token.value ? decodeTokenClaims(token.value) : { exp: null, iat: null }
  const tokenExpiresAt = ref<number | null>(initialClaims.exp)
  const tokenIssuedAt = ref<number | null>(initialClaims.iat)
  const me = ref<UserMe | null>(null)
  const loading = ref(false)
  const lastError = ref<string | null>(null)
  const pendingCount = ref(0)
  let meFetchedAt = 0

  /**
   * background=true면 30초 주기 백그라운드 폴링 호출임을 표시하는 헤더를 붙인다.
   * 실제 사용자 활동이 아니므로 내부망 슬라이딩 세션 연장에서 제외된다 (app/routers/auth.py 참고).
   */
  async function fetchPendingCount(background = false) {
    try {
      const { data } = await api.get<{ id: string }[]>('/admin/users/pending', {
        params: { status: 'PENDING' },
        headers: background ? { 'X-Background-Poll': '1' } : {},
      })
      pendingCount.value = Array.isArray(data) ? data.length : 0
    } catch {
      pendingCount.value = 0
    }
  }

  const isLoggedIn = computed(() => !!token.value)

  function setToken(t: string | null) {
    token.value = t
    if (t) {
      localStorage.setItem('accessToken', t)
      const claims = decodeTokenClaims(t)
      tokenExpiresAt.value = claims.exp
      tokenIssuedAt.value = claims.iat
    } else {
      localStorage.removeItem('accessToken')
      tokenExpiresAt.value = null
      tokenIssuedAt.value = null
    }
  }

  /** 만료 임박 세션을 연장. 성공 시 true. */
  async function extendSession() {
    if (!token.value) return false
    try {
      const res = await api.post<{ accessToken: string }>('/auth/refresh', null, {
        headers: authHeader(),
      })
      setToken(res.data.accessToken)
      return true
    } catch {
      return false
    }
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
      lastError.value = getErrorMessage(err, '로그인에 실패했습니다.')
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
      lastError.value = getErrorMessage(err, '회원가입에 실패했습니다.')
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
    token, tokenExpiresAt, tokenIssuedAt, me, loading, lastError, pendingCount,
    // getters
    isLoggedIn,
    // actions
    login, register, fetchMe, logout, bootstrap, fetchPendingCount, setToken, extendSession,
  }
})
