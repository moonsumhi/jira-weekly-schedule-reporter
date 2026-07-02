import { defineRouter } from '#q-app/wrappers'
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router'
import { Notify } from 'quasar'
import routes from './routes'
import { useAuthStore } from 'stores/auth'

export default defineRouter(function () {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : process.env.VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(process.env.VUE_ROUTER_BASE),
  })

  // Ensure bootstrap runs once at most
  let bootstrapped = false

  Router.beforeEach(async (to) => {
    const auth = useAuthStore()

    // Restore session once (if token exists) so guards use real state
    if (!bootstrapped) {
      bootstrapped = true
      // bootstrap() already checks token internally
      await auth.bootstrap()
    }

    // 1) requiresAuth but not logged in -> go to auth(login) page
    if (to.meta.requiresAuth && !auth.isLoggedIn) {
      return { name: 'auth', query: { redirect: to.fullPath } }
    }

    // 2) guestOnly but already logged in -> go to app home
    if (to.meta.guestOnly && auth.isLoggedIn) {
      return { name: 'app-home' }
    }

    // 로그인 상태면 항상 최신 me 갱신 (30초 캐시 — 사이드바 권한 즉시 반영)
    if (auth.isLoggedIn) {
      try { await auth.fetchMe() } catch { /* token invalid */ }
    }

    // 3) 관리자
    if (to.meta.requiresAdmin) {
      if (!auth.me?.isAdmin) {
        Notify.create({ type: 'negative', message: '접근 권한이 없습니다. 관리자에게 문의하세요.' })
        return { name: 'app-home' }
      }
    }

    // 4) 메뉴 권한 체크
    if (to.meta.requiresPermission) {
      const perm = to.meta.requiresPermission as string
      if (auth.me && !auth.me.isAdmin && !(auth.me.permissions ?? []).includes(perm)) {
        Notify.create({ type: 'negative', message: '해당 메뉴에 대한 접근 권한이 없습니다. 관리자에게 문의하세요.' })
        return { name: 'app-home' }
      }
    }

    return true
  })

  return Router
})
