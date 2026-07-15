import { api } from 'src/boot/axios'

export type NotificationType =
  | 'MENTION'
  | 'ASSIGNED'
  | 'COMMENT_CREATED'
  | 'STATUS_CHANGED'
  | 'REVIEW_REQUESTED'
  | 'APPROVAL_REQUESTED'
  | 'DUE_DATE_APPROACHING'
  | 'DUE_DATE_OVERDUE'
  | 'NOTICE'
  | 'SYSTEM'

export type TargetType = 'SR' | 'PM_ISSUE' | 'SYSTEM'

export type Notification = {
  id: string
  recipientUserId: string
  senderUserId: string | null
  senderName: string | null
  notificationType: NotificationType
  title: string
  message: string
  targetType: TargetType | null
  targetId: string | null
  targetUrl: string | null
  isRead: boolean
  readAt: string | null
  isArchived: boolean
  createdAt: string
  updatedAt: string
}

export type NotificationListPage = {
  items: Notification[]
  total: number
  unreadCount: number
}

export async function fetchNotifications(params?: {
  isRead?: boolean
  isArchived?: boolean
  skip?: number
  limit?: number
}): Promise<NotificationListPage> {
  const { data } = await api.get<NotificationListPage>('/notifications', {
    params: params ? {
      is_read: params.isRead,
      is_archived: params.isArchived,
      skip: params.skip,
      limit: params.limit,
    } : undefined,
  })
  return data
}

export async function fetchUnreadCount(background = false): Promise<number> {
  const { data } = await api.get<{ count: number }>('/notifications/unread-count', {
    headers: background ? { 'X-Background-Poll': '1' } : {},
  })
  return data.count
}

export async function markRead(notificationId: string): Promise<void> {
  await api.post(`/notifications/${notificationId}/read`)
}

export async function markAllRead(): Promise<void> {
  await api.post('/notifications/read-all')
}

export async function archiveNotification(notificationId: string): Promise<void> {
  await api.post(`/notifications/${notificationId}/archive`)
}

export const NOTIFICATION_TYPE_LABEL: Record<NotificationType, string> = {
  MENTION: '멘션',
  ASSIGNED: '담당 배정',
  COMMENT_CREATED: '댓글',
  STATUS_CHANGED: '상태 변경',
  REVIEW_REQUESTED: '검토 요청',
  APPROVAL_REQUESTED: '승인 요청',
  DUE_DATE_APPROACHING: '마감 임박',
  DUE_DATE_OVERDUE: '마감 초과',
  NOTICE: '공지',
  SYSTEM: '시스템',
}

export const NOTIFICATION_TYPE_ICON: Record<NotificationType, string> = {
  MENTION: 'alternate_email',
  ASSIGNED: 'person_add',
  COMMENT_CREATED: 'chat_bubble_outline',
  STATUS_CHANGED: 'sync_alt',
  REVIEW_REQUESTED: 'rate_review',
  APPROVAL_REQUESTED: 'thumb_up',
  DUE_DATE_APPROACHING: 'schedule',
  DUE_DATE_OVERDUE: 'warning',
  NOTICE: 'campaign',
  SYSTEM: 'info',
}

export const NOTIFICATION_TYPE_COLOR: Record<NotificationType, string> = {
  MENTION: 'blue',
  ASSIGNED: 'teal',
  COMMENT_CREATED: 'grey-7',
  STATUS_CHANGED: 'orange',
  REVIEW_REQUESTED: 'purple',
  APPROVAL_REQUESTED: 'green',
  DUE_DATE_APPROACHING: 'amber',
  DUE_DATE_OVERDUE: 'red',
  NOTICE: 'primary',
  SYSTEM: 'grey',
}
