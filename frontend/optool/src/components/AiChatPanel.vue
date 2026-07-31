<template>
  <Teleport to="body">
    <Transition name="chat-panel">
      <div v-if="open" class="ai-chat-panel">
        <!-- 헤더 -->
        <div class="ai-chat-header">
          <div class="row items-center q-gutter-sm">
            <q-icon name="smart_toy" size="20px" color="white" />
            <span class="text-subtitle2 text-white text-weight-bold">AI 어시스턴트</span>
          </div>
          <div class="row items-center q-gutter-xs">
            <q-btn
              flat round dense
              icon="open_in_new"
              color="white"
              size="sm"
              title="새 탭에서 열기"
              @click="openInTab"
            />
            <q-btn
              flat round dense
              icon="close"
              color="white"
              size="sm"
              @click="emit('close')"
            />
          </div>
        </div>

        <!-- iframe -->
        <div v-if="!chatUrl" class="ai-chat-empty column items-center justify-center q-gutter-sm text-grey-5">
          <q-icon name="smart_toy" size="48px" />
          <div class="text-caption text-center">
            VITE_LIBRECHAT_URL 환경변수를<br>설정해 주세요.
          </div>
        </div>
        <iframe
          v-else
          :src="chatUrl"
          class="ai-chat-iframe"
          allow="clipboard-read; clipboard-write"
          referrerpolicy="strict-origin-when-cross-origin"
        />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const chatUrl = (import.meta as any).env?.VITE_LIBRECHAT_URL as string | undefined

function openInTab() {
  if (chatUrl) window.open(chatUrl, '_blank')
}
</script>

<style scoped>
.ai-chat-panel {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 420px;
  height: 680px;
  max-height: calc(100vh - 80px);
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 9999;
  background: #fff;
}

.ai-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: linear-gradient(135deg, #1976d2, #1565c0);
  flex-shrink: 0;
}

.ai-chat-iframe {
  flex: 1;
  width: 100%;
  border: none;
}

.ai-chat-empty {
  flex: 1;
}

/* 슬라이드 + 페이드 애니메이션 */
.chat-panel-enter-active,
.chat-panel-leave-active {
  transition: opacity 0.2s ease, transform 0.25s ease;
}
.chat-panel-enter-from,
.chat-panel-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.97);
}
</style>
