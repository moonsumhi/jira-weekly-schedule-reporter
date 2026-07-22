<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <!-- 헤더 -->
      <div class="col-12">
        <div class="row items-center">
          <div class="col">
            <div class="text-h5 text-weight-bold">알림</div>
            <div class="text-caption text-grey-6">수신된 알림 목록</div>
          </div>
          <q-btn
            v-if="unreadCount > 0"
            outline color="primary" size="sm" icon="done_all" label="모두 읽음"
            @click="onMarkAllRead"
          />
        </div>
      </div>

      <!-- 필터 탭 -->
      <div class="col-12">
        <q-tabs
          v-model="tab"
          dense
          align="left"
          class="text-grey-7"
          active-color="primary"
          indicator-color="primary"
          narrow-indicator
        >
          <q-tab name="all" label="전체" />
          <q-tab name="unread">
            <div class="row items-center no-wrap q-gutter-xs">
              <span>읽지 않음</span>
              <q-badge v-if="unreadCount > 0" color="red" :label="unreadCount" />
            </div>
          </q-tab>
          <q-tab name="archived" label="보관됨" />
        </q-tabs>
        <q-separator />
      </div>

      <!-- 목록 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-linear-progress v-if="loading" indeterminate color="primary" />

          <div v-if="!loading && items.length === 0" class="q-pa-xl text-center text-grey">
            <q-icon name="notifications_none" size="48px" class="q-mb-sm" /><br>
            알림이 없습니다.
          </div>

          <q-list separator>
            <q-item
              v-for="n in items"
              :key="n.id"
              :class="n.isRead ? '' : 'bg-blue-1'"
              class="q-py-md"
            >
              <q-item-section avatar>
                <q-icon
                  :name="NOTIFICATION_TYPE_ICON[n.notificationType]"
                  :color="NOTIFICATION_TYPE_COLOR[n.notificationType]"
                  size="22px"
                />
              </q-item-section>

              <q-item-section
                class="cursor-pointer"
                @click="handleItemClick(n)"
              >
                <q-item-label class="text-body2 text-weight-medium">{{ n.title }}</q-item-label>
                <q-item-label caption class="text-grey-8 q-mt-xs">{{ n.message }}</q-item-label>
                <q-item-label caption class="text-grey-5 q-mt-xs" style="font-size: 11px">
                  {{ formatDate(n.createdAt) }}
                  <q-badge
                    v-if="!n.isRead"
                    color="blue" label="새 알림"
                    class="q-ml-xs"
                    style="font-size: 9px"
                  />
                </q-item-label>
              </q-item-section>

              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="!n.isRead"
                    flat round dense size="xs"
                    icon="mark_email_read"
                    color="primary"
                    title="읽음으로 표시"
                    @click.stop="onMarkRead(n)"
                  />
                  <q-btn
                    v-if="!n.isArchived"
                    flat round dense size="xs"
                    icon="archive"
                    color="grey-5"
                    title="보관"
                    @click.stop="onArchive(n)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <!-- 더 불러오기 -->
      <div v-if="hasMore" class="col-12 text-center">
        <q-btn outline color="primary" label="더 보기" :loading="loadingMore" @click="loadMore" />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { DateTime } from 'luxon'
import {
  fetchNotifications, markRead, markAllRead, archiveNotification,
  NOTIFICATION_TYPE_ICON, NOTIFICATION_TYPE_COLOR,
  type Notification,
} from 'src/services/notification'
import { useNotificationStore } from 'stores/notification'
import { getErrorMessage } from 'src/utils/http/error'

const $q = useQuasar()
const router = useRouter()
const notifStore = useNotificationStore()

const tab = ref<'all' | 'unread' | 'archived'>('all')
const items = ref<Notification[]>([])
const total = ref(0)
const unreadCount = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const PAGE_SIZE = 30

const hasMore = computed(() => items.value.length < total.value)

async function load(reset = true) {
  if (reset) {
    loading.value = true
    items.value = []
  } else {
    loadingMore.value = true
  }
  try {
    const isArchived = tab.value === 'archived'
    const params: Parameters<typeof fetchNotifications>[0] = {
      isArchived,
      skip: reset ? 0 : items.value.length,
      limit: PAGE_SIZE,
    }
    if (tab.value === 'unread') params.isRead = false
    const page = await fetchNotifications(params)
    if (reset) {
      items.value = page.items
    } else {
      items.value.push(...page.items)
    }
    total.value = page.total
    unreadCount.value = page.unreadCount
    notifStore.unreadCount = page.unreadCount
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '알림 로드 실패') })
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  await load(false)
}

function formatDate(dateStr: string): string {
  const normalized = /Z|[+-]\d{2}:?\d{2}$/.test(dateStr) ? dateStr : dateStr + 'Z'
  return DateTime.fromISO(normalized).setZone('Asia/Seoul').toFormat('yyyy.MM.dd HH:mm')
}

async function handleItemClick(n: Notification) {
  if (!n.isRead) await onMarkRead(n)
  if (n.targetUrl) void router.push(n.targetUrl)
}

async function onMarkRead(n: Notification) {
  try {
    await markRead(n.id)
    n.isRead = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    notifStore.unreadCount = unreadCount.value
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '읽음 처리 실패') })
  }
}

async function onMarkAllRead() {
  try {
    await markAllRead()
    items.value = items.value.map((n) => ({ ...n, isRead: true }))
    unreadCount.value = 0
    notifStore.unreadCount = 0
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '읽음 처리 실패') })
  }
}

async function onArchive(n: Notification) {
  try {
    await archiveNotification(n.id)
    items.value = items.value.filter((i) => i.id !== n.id)
    total.value = Math.max(0, total.value - 1)
    notifStore.dropdownItems = notifStore.dropdownItems.filter((i) => i.id !== n.id)
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '보관 처리 실패') })
  }
}

watch(tab, () => void load())
onMounted(() => void load())
</script>
