<template>
  <Teleport to="body" :disabled="!expanded">
    <div ref="panel" :class="['auto-work-panel', { 'auto-work-panel--expanded': expanded }]"
      :tabindex="expanded ? -1 : undefined" :role="expanded ? 'dialog' : undefined"
      :aria-modal="expanded ? 'true' : undefined" :aria-label="label"
      @keydown="handleKeydown">
      <q-card flat bordered class="auto-work-card">
        <slot :expanded="expanded" :toggle="toggle" />
      </q-card>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'

withDefaults(defineProps<{ label?: string }>(), { label: '자동 집계 업무' })

const expanded = ref(false)
const panel = ref<HTMLElement | null>(null)
let returnFocus: HTMLElement | null = null
let previousOverflow: string | null = null

function restoreScroll() {
  if (previousOverflow !== null) document.body.style.overflow = previousOverflow
  previousOverflow = null
}

async function toggle() {
  if (!expanded.value) {
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    expanded.value = true
    await nextTick()
    panel.value?.focus()
  } else {
    expanded.value = false
    restoreScroll()
    await nextTick()
    returnFocus?.focus()
    returnFocus = null
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!expanded.value || event.defaultPrevented) return
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    void toggle()
    return
  }
  if (event.key !== 'Tab' || !panel.value) return
  const focusable = [...panel.value.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )].filter(element => element.getClientRects().length > 0 && element.getAttribute('aria-hidden') !== 'true')
  if (!focusable.length) {
    event.preventDefault()
    panel.value.focus()
    return
  }
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) {
    event.preventDefault()
    last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}

onBeforeUnmount(restoreScroll)
</script>

<style scoped>
.auto-work-panel--expanded {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: white;
  outline: none;
}
.auto-work-panel--expanded .auto-work-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 0;
}
.auto-work-panel--expanded :deep(.auto-work-scroll) {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none !important;
  overflow: auto;
  overscroll-behavior: contain;
}
</style>
