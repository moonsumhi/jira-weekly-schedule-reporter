<template>
  <q-page class="ai-chat-page">
    <div v-if="!chatUrl" class="column items-center justify-center full-height q-gutter-md text-grey-6">
      <q-icon name="smart_toy" size="64px" />
      <div class="text-h6">AI 채팅 URL이 설정되지 않았습니다</div>
      <div class="text-body2 text-center">
        빌드 환경변수 <code>VITE_LIBRECHAT_URL</code> 을 설정해 주세요.
      </div>
    </div>
    <iframe
      v-else
      :src="chatUrl"
      class="chat-frame"
      allow="clipboard-read; clipboard-write"
      referrerpolicy="strict-origin-when-cross-origin"
    />
  </q-page>
</template>

<script setup lang="ts">
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const chatUrl = (import.meta as any).env?.VITE_LIBRECHAT_URL as string | undefined
</script>

<style scoped>
.ai-chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 50px); /* MainLayout 헤더 높이 */
  padding: 0;
}

.chat-frame {
  flex: 1;
  width: 100%;
  height: 100%;
  border: none;
}
</style>
