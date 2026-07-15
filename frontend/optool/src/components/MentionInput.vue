<template>
  <div ref="wrapRef" class="mention-input-wrap" @keydown="onKeydown">
    <q-input
      ref="inputRef"
      :model-value="modelValue"
      :rows="rows"
      :placeholder="placeholder"
      :dense="dense"
      outlined
      type="textarea"
      style="resize: none"
      @update:model-value="onInput"
      @blur="onBlur"
    />

    <div
      v-if="showMenu"
      class="mention-dropdown"
    >
      <div v-if="searching" class="q-pa-sm text-center text-grey-6">
        <q-spinner size="xs" color="primary" /> 검색 중...
      </div>
      <div
        v-else-if="searchResults.length === 0"
        class="q-pa-sm text-center text-grey-6 text-caption"
      >
        결과 없음
      </div>
      <q-list v-else dense>
        <q-item
          v-for="(u, i) in searchResults"
          :key="u.userId"
          clickable
          :active="i === activeIdx"
          active-class="bg-primary text-white"
          @mousedown.prevent="selectUser(u)"
          @mouseenter="activeIdx = i"
        >
          <q-item-section avatar>
            <q-avatar size="28px" color="primary" text-color="white" style="font-size: 11px">
              {{ (u.displayName || u.email)[0]?.toUpperCase() }}
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-body2">{{ u.displayName }}</q-item-label>
            <q-item-label caption class="text-grey-6">
              {{ [u.team, u.email].filter(Boolean).join(' · ') }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QInput } from 'quasar'
import { searchMentionUsers, type MentionUser } from 'src/services/mention'

const props = withDefaults(defineProps<{
  modelValue: string
  mentionedUsers: MentionUser[]
  rows?: number
  placeholder?: string
  dense?: boolean
}>(), { rows: 3, placeholder: '댓글 작성...', dense: false })

const emit = defineEmits<{
  'update:modelValue': [string]
  'update:mentionedUsers': [MentionUser[]]
}>()

const wrapRef = ref<HTMLElement | null>(null)
const inputRef = ref<InstanceType<typeof QInput> | null>(null)
const showMenu = ref(false)
const searching = ref(false)
const searchResults = ref<MentionUser[]>([])
const activeIdx = ref(0)
const mentionActive = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let reqSeq = 0

function getTextarea(): HTMLTextAreaElement | null {
  return inputRef.value?.getNativeElement() as HTMLTextAreaElement | null
}

function getMentionQuery(text: string, cursorPos: number): string | null {
  const before = text.slice(0, cursorPos)
  // If the char immediately before cursor is whitespace, no active mention
  if (before.length > 0 && /\s/.test(before.charAt(before.length - 1))) return null
  const match = before.match(/@([^\s@]*)$/)
  if (!match) return null
  return match[1] ?? ''
}

function getMentionStart(text: string, cursorPos: number): number {
  const before = text.slice(0, cursorPos)
  return before.lastIndexOf('@')
}

function onInput(val: string | number | null) {
  const text = String(val ?? '')
  emit('update:modelValue', text)

  const stillPresent = props.mentionedUsers.filter(m => text.includes(`@${m.displayName}`))
  if (stillPresent.length !== props.mentionedUsers.length) {
    emit('update:mentionedUsers', stillPresent)
  }

  const el = getTextarea()
  const cursorPos = el?.selectionStart ?? text.length
  const query = getMentionQuery(text, cursorPos)

  if (query !== null) {
    mentionActive.value = true
    triggerSearch(query)
  } else {
    mentionActive.value = false
    showMenu.value = false
    searchResults.value = []
    if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
    reqSeq++
  }
}

function triggerSearch(q: string) {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => void (async () => {
    const seq = ++reqSeq
    searching.value = true
    showMenu.value = true
    try {
      const results = await searchMentionUsers(q)
      if (seq === reqSeq) {
        searchResults.value = results
        activeIdx.value = 0
      }
    } catch {
      if (seq === reqSeq) searchResults.value = []
    } finally {
      if (seq === reqSeq) searching.value = false
    }
  })(), 200)
}

function selectUser(u: MentionUser) {
  if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  reqSeq++
  const el = getTextarea()
  const text = props.modelValue
  const cursorPos = el?.selectionStart ?? text.length
  const mentionStart = getMentionStart(text, cursorPos)
  if (mentionStart === -1) return

  const before = text.slice(0, mentionStart)
  const after = text.slice(cursorPos)
  const newText = `${before}@${u.displayName} ${after}`
  emit('update:modelValue', newText)

  if (!props.mentionedUsers.find(m => m.userId === u.userId)) {
    emit('update:mentionedUsers', [...props.mentionedUsers, u])
  }

  showMenu.value = false
  mentionActive.value = false
  searchResults.value = []

  const newCursor = mentionStart + u.displayName.length + 2
  setTimeout(() => {
    el?.setSelectionRange(newCursor, newCursor)
    el?.focus()
  }, 0)
}

function onKeydown(e: KeyboardEvent) {
  if (e.isComposing || !showMenu.value) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIdx.value = Math.min(activeIdx.value + 1, searchResults.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = Math.max(activeIdx.value - 1, 0)
  } else if (e.key === 'Enter' && searchResults.value.length > 0) {
    e.preventDefault()
    const u = searchResults.value[activeIdx.value]
    if (u) selectUser(u)
  } else if (e.key === 'Escape') {
    showMenu.value = false
    mentionActive.value = false
  }
}

function onBlur() {
  setTimeout(() => {
    showMenu.value = false
    mentionActive.value = false
  }, 150)
}

watch(() => props.modelValue, (val) => {
  if (!val) {
    showMenu.value = false
    mentionActive.value = false
    searchResults.value = []
  }
})
</script>

<style scoped>
.mention-input-wrap {
  position: relative;
}

.mention-dropdown {
  position: absolute;
  z-index: 9999;
  bottom: 100%;
  left: 0;
  width: 300px;
  max-height: 230px;
  overflow-y: auto;
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  margin-bottom: 2px;
}
</style>
