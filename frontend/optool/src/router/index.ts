import { defineRouter } from '#q-app/wrappers'
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router'
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

    return true
  })

  return Router
})
