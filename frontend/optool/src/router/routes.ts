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
        path: 'jira',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'search',
            component: () => import('pages/jira/TaskViewer.vue')
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
