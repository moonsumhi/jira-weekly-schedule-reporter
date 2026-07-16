<template>
  <div>
    <q-btn
      flat dense round
      icon="notifications"
      :aria-label="`알림 (${notifStore.unreadCount}개 읽지 않음)`"
    >
      <q-badge
        v-if="notifStore.unreadCount > 0"
        color="red"
        floating
        rounded
        :label="notifStore.unreadCount > 99 ? '99+' : notifStore.unreadCount"
        style="font-size: 9px"
      />

      <q-menu
        anchor="bottom right"
        self="top right"
        :offset="[0, 4]"
        style="width: 360px; max-height: 480px"
        @before-show="notifStore.loadDropdown()"
      >
        <!-- 헤더 -->
        <div class="row items-center q-px-md q-py-sm bg-grey-1">
          <div class="col text-subtitle2 text-weight-bold">알림</div>
          <q-btn
            v-if="notifStore.unreadCount > 0"
            flat dense size="sm" color="primary"
            label="모두 읽음"
            @click.stop="notifStore.readAll()"
          />
          <q-btn
            flat dense round size="sm" icon="open_in_new" color="grey-7"
            class="q-ml-xs"
            title="전체 보기"
            @click.stop="$router.push('/notifications')"
          />
        </div>
        <q-separator />

        <!-- 로딩 -->
        <div v-if="notifStore.loading" class="q-pa-md text-center text-grey">
          <q-spinner size="sm" />
        </div>

        <!-- 비어있음 -->
        <div
          v-else-if="notifStore.dropdownItems.length === 0"
          class="q-pa-lg text-center text-grey text-caption"
        >
          새로운 알림이 없습니다.
        </div>

        <!-- 목록 -->
        <q-list v-else separator>
          <q-item
            v-for="n in notifStore.dropdownItems"
            :key="n.id"
            clickable
            :class="n.isRead ? 'bg-white' : 'bg-blue-1'"
            @click="handleClick(n)"
          >
            <q-item-section avatar>
              <q-icon
                :name="NOTIFICATION_TYPE_ICON[n.notificationType]"
                :color="NOTIFICATION_TYPE_COLOR[n.notificationType]"
                size="20px"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-caption text-weight-medium">{{ n.title }}</q-item-label>
              <q-item-label caption lines="2" class="text-grey-8">{{ n.message }}</q-item-label>
              <q-item-label caption class="text-grey-5" style="font-size: 10px">
                {{ formatRelative(n.createdAt) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <q-btn
                flat dense round size="xs" icon="close" color="grey-4"
                @click.stop="notifStore.archive(n.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <q-separator />
        <div class="q-pa-xs text-center">
          <q-btn flat dense size="sm" color="primary" label="알림 전체 보기" @click="$router.push('/notifications')" />
        </div>
      </q-menu>
    </q-btn>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useNotificationStore } from 'stores/notification'
import { NOTIFICATION_TYPE_ICON, NOTIFICATION_TYPE_COLOR, type Notification } from 'src/services/notification'
import { DateTime } from 'luxon'

const notifStore = useNotificationStore()
const router = useRouter()

function formatRelative(dateStr: string): string {
  const dt = DateTime.fromISO(dateStr)
  const diff = DateTime.now().diff(dt, ['minutes', 'hours', 'days'])
  if (diff.days >= 1) return dt.toFormat('MM/dd HH:mm')
  if (diff.hours >= 1) return `${Math.floor(diff.hours)}시간 전`
  if (diff.minutes >= 1) return `${Math.floor(diff.minutes)}분 전`
  return '방금 전'
}

function handleClick(n: Notification) {
  void notifStore.readAndNavigate(n, (url) => { void router.push(url) })
}
</script>
