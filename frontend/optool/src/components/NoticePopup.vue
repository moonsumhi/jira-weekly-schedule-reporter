<template>
  <div
    v-for="(notice, i) in queue" :key="notice.id"
    class="notice-popup-card"
    :style="{ top: `${16 + i * 32}px`, left: `${16 + i * 32}px`, zIndex: 3000 + i }"
  >
    <q-card style="min-width: 420px; max-width: 560px">
      <q-card-section class="row items-center">
        <q-icon name="campaign" color="primary" size="22px" class="q-mr-sm" />
        <div class="text-h6">{{ notice.title }}</div>
      </q-card-section>
      <q-separator />
      <q-card-section style="max-height: 50vh" class="scroll">
        <MarkdownContent :content="notice.content" />
      </q-card-section>
      <q-separator />
      <q-card-actions class="row items-center q-px-md">
        <q-checkbox v-model="dontShowToday[notice.id]" label="오늘 하루 보지 않기" dense size="sm" />
        <q-space />
        <q-btn flat label="닫기" color="primary" @click="close(notice.id)" />
      </q-card-actions>
    </q-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { noticeService, type NoticeOut } from 'src/services/notices'
import MarkdownContent from 'src/components/MarkdownContent.vue'

const queue = ref<NoticeOut[]>([])
const dontShowToday = reactive<Record<string, boolean>>({})

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function dismissKey(id: string) {
  return `notice_dismissed_${id}_${todayStr()}`
}

function close(id: string) {
  if (dontShowToday[id]) {
    localStorage.setItem(dismissKey(id), '1')
  }
  queue.value = queue.value.filter((n) => n.id !== id)
}

onMounted(async () => {
  try {
    const active = await noticeService.listActive()
    queue.value = active.filter((n) => !localStorage.getItem(dismissKey(n.id)))
  } catch { /* 공지 조회 실패는 조용히 무시 */ }
})
</script>

<style scoped>
.notice-popup-card {
  position: fixed;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  border-radius: 4px;
}
</style>
