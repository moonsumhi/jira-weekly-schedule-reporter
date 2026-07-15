<template>
  <div class="markdown-content" v-html="rendered" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()

const renderer = new marked.Renderer()

const rendered = computed(() => {
  if (!props.content?.trim()) return ''
  return marked(props.content, { renderer, breaks: true }) as string
})
</script>

<style scoped>
.markdown-content :deep(h1) { font-size: 1.5rem; font-weight: 700; margin: 0.6em 0 0.3em; }
.markdown-content :deep(h2) { font-size: 1.25rem; font-weight: 700; margin: 0.6em 0 0.3em; }
.markdown-content :deep(h3) { font-size: 1.1rem; font-weight: 600; margin: 0.5em 0 0.25em; }
.markdown-content :deep(p)  { margin: 0.4em 0; line-height: 1.6; }
.markdown-content :deep(ul),
.markdown-content :deep(ol) { margin: 0.4em 0; padding-left: 1.4em; }
.markdown-content :deep(li) { margin: 0.15em 0; }
.markdown-content :deep(code) {
  background: #f1f3f4; border-radius: 3px; padding: 1px 5px;
  font-family: monospace; font-size: 0.9em;
}
.markdown-content :deep(pre) {
  background: #f1f3f4; border-radius: 6px; padding: 0.75em 1em;
  overflow-x: auto; margin: 0.5em 0;
}
.markdown-content :deep(pre code) { background: none; padding: 0; }
.markdown-content :deep(blockquote) {
  border-left: 3px solid #bdbdbd; margin: 0.5em 0;
  padding: 0.25em 0.75em; color: #555;
}
.markdown-content :deep(hr) { border: none; border-top: 1px solid #e0e0e0; margin: 0.75em 0; }
.markdown-content :deep(strong) { font-weight: 700; }
.markdown-content :deep(em)     { font-style: italic; }
.markdown-content :deep(a)      { color: #1976d2; text-decoration: underline; }
.markdown-content :deep(table)  { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
.markdown-content :deep(th),
.markdown-content :deep(td)     { border: 1px solid #e0e0e0; padding: 0.35em 0.6em; }
.markdown-content :deep(th)     { background: #f5f5f5; font-weight: 600; }
</style>
