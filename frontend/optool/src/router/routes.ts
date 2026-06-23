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
            meta: { requiresPermission: 'jira_search' },
            component: () => import('pages/jira/TaskViewer.vue')
          },
        ]
      },
      {
        path: 'asset',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'list',
            meta: { requiresPermission: 'asset_list' },
            component: () => import('pages/asset/ServerAssetPage.vue')
          }
        ]
      },
      {
        path: 'pilot',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'tasks',
            meta: { requiresPermission: 'pilot_tasks' },
            component: () => import('pages/pilot/PilotTasksPage.vue')
          }
        ]
      },
      {
        path: 'inspection',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'checklist',
            meta: { requiresPermission: 'inspection_checklist' },
            component: () => import('pages/inspection/ServerRoomInspectionPage.vue')
          },
          {
            path: 'health-summary',
            meta: { requiresPermission: 'health_report' },
            component: () => import('pages/inspection/HealthSummaryPage.vue')
          },
          {
            path: 'health-servers',
            meta: { requiresPermission: 'health_report' },
            component: () => import('pages/inspection/HealthServerListPage.vue')
          },
          {
            path: 'health-compare',
            meta: { requiresPermission: 'health_report' },
            component: () => import('pages/inspection/HealthComparePage.vue')
          }
        ]
      },
      {
        path: 'report',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'weekly',
            meta: { requiresPermission: 'weekly_report' },
            component: () => import('pages/report/WeeklyReportPage.vue')
          }
        ]
      },
      {
        path: 'job',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'forms/:id',
            component: () => import('pages/jira/FormTemplatePage.vue')
          }
        ]
      },
      {
        path: 'account',
        meta: { requiresAuth: true },
        children: [
          {
            path: 'settings',
            component: () => import('pages/account/AccountSettingsPage.vue')
          }
        ]
      },
      {
        path: 'board',
        meta: { requiresAuth: true },
        children: [
          {
            path: ':boardId',
            component: () => import('pages/board/BoardPage.vue')
          }
        ]
      },
      {
        path: 'admin',
        meta: { requiresAuth: true, requiresAdmin: true },
        children: [
          {
            path: 'approvals',
            component: () => import('pages/auth/AdminApprovalPage.vue')
          },
          {
            path: 'users',
            component: () => import('pages/auth/AdminUserListPage.vue')
          },
          {
            path: 'menus',
            component: () => import('pages/admin/MenuManagePage.vue')
          },
          {
            path: 'audit-log',
            component: () => import('pages/admin/AuditLogPage.vue')
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
