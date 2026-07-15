import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchUnreadCount, fetchNotifications, markRead, markAllRead, archiveNotification, type Notification } from 'src/services/notification'

export const useNotificationStore = defineStore('notification', () => {
  const unreadCount = ref(0)
  const dropdownItems = ref<Notification[]>([])
  const loading = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function refreshUnreadCount(background = false) {
    try {
      unreadCount.value = await fetchUnreadCount(background)
    } catch {
      // silently ignore polling errors
    }
  }

  async function loadDropdown() {
    loading.value = true
    try {
      const page = await fetchNotifications({ isArchived: false, limit: 10 })
      dropdownItems.value = page.items
      unreadCount.value = page.unreadCount
    } finally {
      loading.value = false
    }
  }

  async function readAndNavigate(n: Notification, navigateFn: (url: string) => void) {
    if (!n.isRead) {
      await markRead(n.id)
      n.isRead = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      const idx = dropdownItems.value.findIndex((i) => i.id === n.id)
      if (idx !== -1) dropdownItems.value[idx] = { ...n }
    }
    if (n.targetUrl) navigateFn(n.targetUrl)
  }

  async function readAll() {
    await markAllRead()
    unreadCount.value = 0
    dropdownItems.value = dropdownItems.value.map((n) => ({ ...n, isRead: true }))
  }

  async function archive(id: string) {
    await archiveNotification(id)
    dropdownItems.value = dropdownItems.value.filter((n) => n.id !== id)
  }

  function startPolling() {
    if (pollTimer) return
    void refreshUnreadCount()
    pollTimer = setInterval(() => void refreshUnreadCount(true), 30_000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    unreadCount.value = 0
    dropdownItems.value = []
  }

  return {
    unreadCount, dropdownItems, loading,
    refreshUnreadCount, loadDropdown, readAndNavigate, readAll, archive,
    startPolling, stopPolling,
  }
})
