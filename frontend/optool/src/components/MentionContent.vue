<template>
  <span style="white-space: pre-wrap; word-break: break-word">
    <template v-for="(seg, i) in segments" :key="i">
      <span
        v-if="seg.type === 'mention'"
        class="mention-chip"
        :class="{ 'mention-chip--me': seg.isMe }"
        :title="seg.team ? `${seg.displayName} · ${seg.team}` : seg.displayName"
      >@{{ seg.displayName }}</span>
      <template v-else>{{ seg.text }}</template>
    </template>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from 'stores/auth'

type MentionedUserIn = { userId: string; displayName: string; team?: string | null }

const props = defineProps<{
  content: string
  mentionedUsers: MentionedUserIn[]
}>()

const auth = useAuthStore()

function escapeRegex(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

type Segment =
  | { type: 'text'; text: string }
  | { type: 'mention'; displayName: string; userId: string; isMe: boolean; team?: string | null }

const segments = computed<Segment[]>(() => {
  if (!props.mentionedUsers.length) return [{ type: 'text', text: props.content }]

  const sorted = [...props.mentionedUsers].sort((a, b) => b.displayName.length - a.displayName.length)
  const patterns = sorted.map(m => `@${escapeRegex(m.displayName)}`)
  const regex = new RegExp(`(${patterns.join('|')})`, 'g')

  const parts = props.content.split(regex)
  const myId = auth.me ? String(auth.me.id) : ''
  const result: Segment[] = []

  for (const part of parts) {
    if (!part) continue
    const mention = props.mentionedUsers.find(m => `@${m.displayName}` === part)
    if (mention) {
      result.push({
        type: 'mention',
        displayName: mention.displayName,
        userId: mention.userId,
        isMe: Boolean(myId && mention.userId === myId),
        team: mention.team ?? null,
      })
    } else {
      result.push({ type: 'text', text: part })
    }
  }
  return result
})
</script>

<style scoped>
.mention-chip {
  display: inline;
  background: rgba(25, 118, 210, 0.12);
  color: #1565c0;
  border-radius: 4px;
  padding: 0 3px;
  font-weight: 500;
  cursor: default;
}
.mention-chip--me {
  background: rgba(76, 175, 80, 0.15);
  color: #2e7d32;
}
</style>
