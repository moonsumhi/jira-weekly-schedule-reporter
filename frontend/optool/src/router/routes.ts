import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'auth',
        component: () => import('pages/auth/AuthPage.vue'),
        meta: { guestOnly: true }
      },
      {
        path: 'app',
        name: 'app-home',
        component: () => import('pages/IndexPage.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'watch',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'timetable',
            component: () => import('pages/watch/WatchTimeTablePage.vue')
          }
        ]
      },
      {
        path: 'jira',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'search',
            component: () => import('pages/jira/TaskViewer.vue')
          }
        ]
      },
      {
        path: 'asset',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'list',
            component: () => import('pages/asset/ServerAssetPage.vue')
          }
        ]
      },
      {
        path: 'admin',
        meta: { requiresAuth: true, requireAdmin: true },
        children: [
          {
            path: 'approvals',
            component: () => import('pages/auth/AdminApprovalPage.vue')
          }
        ]
      }
    ]
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes
