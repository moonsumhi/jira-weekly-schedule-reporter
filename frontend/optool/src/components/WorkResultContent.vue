<template>
  <div class="work-result-content" @click="openImage" @keydown.enter="openImage" @keydown.space="openImage" v-html="rendered" />
  <q-dialog v-model="previewOpen" @hide="previewSource = ''">
    <q-card class="image-preview-card">
      <q-bar><span>이미지 크게 보기</span><q-space /><q-btn flat round dense icon="close" aria-label="이미지 닫기" v-close-popup /></q-bar>
      <img :src="previewSource" :alt="previewAlt" class="image-preview-full" />
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked, Renderer } from 'marked'
const props = defineProps<{ content: string }>()
const previewOpen = ref(false)
const previewSource = ref('')
const previewAlt = ref('')
function openImage(event: MouseEvent | KeyboardEvent) {
  if (!(event.target instanceof HTMLImageElement)) return
  event.preventDefault()
  event.stopPropagation()
  previewSource.value = event.target.currentSrc || event.target.src
  previewAlt.value = event.target.alt || '문서 이미지 확대'
  previewOpen.value = true
}
function escapeHtml(text: string) { return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') }
function safeUrl(href: string, image: boolean): boolean {
  if (image && /^data:image\/(png|jpeg|gif|webp);base64,/i.test(href)) return true
  try { return (image ? ['http:', 'https:'] : ['http:', 'https:', 'mailto:']).includes(new URL(href, window.location.origin).protocol) }
  catch { return false }
}
const renderer = new Renderer()
renderer.table = (header, body) => `<div class="work-table-scroll" tabindex="0" role="region" aria-label="문서 표, 가로 스크롤 가능"><table><thead>${header}</thead><tbody>${body}</tbody></table></div>`
renderer.html = (html) => /^<br\s*\/?\s*>$/i.test(html.trim()) ? '<br>' : escapeHtml(html)
renderer.link = (href, _title, text) => href && safeUrl(href, false) ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${text}</a>` : text
renderer.image = (href, _title, text) => href && safeUrl(href, true) ? `<img src="${escapeHtml(href)}" alt="${escapeHtml(text)}" loading="lazy" role="button" tabindex="0" aria-label="${escapeHtml(text || '문서 이미지')} 크게 보기" title="클릭하여 크게 보기">` : escapeHtml(text)
const rendered = computed(() => marked(props.content, { renderer, breaks: true }))
</script>
<style scoped>
.work-result-content { overflow-wrap: anywhere; font-size: 14px; line-height: 1.8; min-width: 0; }
.work-result-content :deep(img) { display: block; max-width: 100%; height: auto; margin: 12px 0; border-radius: 6px; cursor: zoom-in; }
.work-result-content :deep(img:focus-visible) { outline: 2px solid var(--q-primary); outline-offset: 4px; }
.image-preview-card { width: 94vw; max-width: 94vw; max-height: 94vh; }
.image-preview-full { display: block; width: 100%; height: calc(90vh - 40px); object-fit: contain; }
.work-result-content :deep(p) { margin: 0 0 14px; white-space: pre-wrap; }
.work-result-content :deep(pre) { overflow: auto; padding: 12px; background: #f1f5f9; color: #1e293b; border-radius: 6px; }
.work-result-content :deep(h1), .work-result-content :deep(h2), .work-result-content :deep(h3) { font-size: 18px; line-height: 1.5; margin: 16px 0 8px; }
.work-result-content :deep(.work-table-scroll) { max-width: 100%; overflow-x: auto; margin: 16px 0; border: 1px solid #cbd5e1; border-radius: 8px; }
.work-result-content :deep(.work-table-scroll:focus-visible) { outline: 2px solid var(--q-primary); outline-offset: 3px; }
.work-result-content :deep(table) { width: 100%; border-collapse: collapse; }
.work-result-content :deep(td), .work-result-content :deep(th) { min-width: 180px; border: 1px solid #cbd5e1; padding: 12px 16px; vertical-align: top; word-break: keep-all; overflow-wrap: anywhere; }
.work-result-content :deep(th) { background: #64748b0d; font-weight: 600; }
</style>
