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
            meta: { requiresPermission: 'watch' },
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
            meta: { requiresPermission: 'jira' },
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
            meta: { requiresPermission: 'asset' },
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
            meta: { requiresPermission: 'job' },
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
            meta: { requiresPermission: 'inspection' },
            component: () => import('pages/inspection/ServerRoomInspectionPage.vue')
          },
          {
            path: 'health-summary',
            meta: { requiresPermission: 'server_check' },
            component: () => import('pages/inspection/HealthSummaryPage.vue')
          },
          {
            path: 'health-servers',
            meta: { requiresPermission: 'server_check' },
            component: () => import('pages/inspection/HealthServerListPage.vue')
          },
          {
            path: 'health-compare',
            meta: { requiresPermission: 'server_check' },
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
            meta: { requiresPermission: 'jira' },
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
        path: 'calendar',
        meta: { requiresAuth: true },
        children: [
          {
            path: '',
            meta: { requiresPermission: 'calendar' },
            component: () => import('pages/calendar/TeamCalendarPage.vue')
          }
        ]
      },
      {
        path: 'documents',
        meta: { requiresAuth: true },
        children: [
          {
            path: '',
            meta: { requiresPermission: 'document_manage' },
            component: () => import('pages/document/DocumentManagePage.vue')
          }
        ]
      },
      {
        path: 'isms-p',
        meta: { requiresAuth: true },
        children: [
          {
            path: ':folderName',
            component: () => import('pages/document/IsmsDocPage.vue')
          }
        ]
      },
      {
        path: 'pm',
        meta: { requiresAuth: true, requiresPermission: 'pm' },
        children: [
          {
            path: 'dashboard',
            component: () => import('pages/pm/PmDashboardPage.vue')
          },
          {
            path: 'projects',
            component: () => import('pages/pm/ProjectListPage.vue')
          },
          {
            path: 'projects/:projectId',
            component: () => import('pages/pm/ProjectDetailPage.vue')
          },
          {
            path: 'projects/:projectId/board',
            component: () => import('pages/pm/ProjectBoardPage.vue')
          },
          {
            path: 'projects/:projectId/backlog',
            component: () => import('pages/pm/ProjectBacklogPage.vue')
          },
          {
            path: 'projects/:projectId/sprints',
            component: () => import('pages/pm/ProjectSprintsPage.vue')
          },
          {
            path: 'organizations',
            component: () => import('pages/pm/OrgListPage.vue')
          },
          {
            path: 'organizations/:orgId',
            component: () => import('pages/pm/OrgDetailPage.vue')
          },
          {
            path: 'work-status',
            component: () => import('pages/pm/WorkStatusPage.vue')
          },
          {
            path: 'weekly-report',
            meta: { requiresAdmin: true },
            component: () => import('pages/pm/WeeklyReportPage.vue')
          },
          {
            path: 'weekly-report/:id',
            meta: { requiresAdmin: true },
            component: () => import('pages/pm/WeeklyReportDetailPage.vue')
          },
          {
            path: 'monthly-report',
            meta: { requiresAdmin: true },
            component: () => import('pages/pm/MonthlyReportPage.vue')
          },
          // ── SR (Service Request) ────────────────────────────
          {
            path: 'sr/new',
            meta: { requiresPermission: 'sr' },
            component: () => import('pages/sr/SrRequestPage.vue')
          },
          {
            path: 'sr/my',
            meta: { requiresPermission: 'sr' },
            component: () => import('pages/sr/SrMyListPage.vue')
          },
          {
            path: 'sr/manage',
            meta: { requiresPermission: 'sr' },
            component: () => import('pages/sr/SrManagePage.vue')
          },
          {
            path: 'sr/:id/edit',
            meta: { requiresPermission: 'sr' },
            component: () => import('pages/sr/SrRequestPage.vue')
          },
          {
            path: 'sr/:id',
            meta: { requiresPermission: 'sr' },
            component: () => import('pages/sr/SrDetailPage.vue')
          },
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
    path: '/pm/weekly-report/:id/print',
    meta: { requiresAuth: true },
    component: () => import('pages/pm/WeeklyReportPrintPage.vue')
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes
