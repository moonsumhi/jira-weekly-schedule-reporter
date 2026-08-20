<template>
  <div>
    <div v-if="label" class="tui-label q-mb-xs">
      {{ label }}<span v-if="required" class="text-negative q-ml-xs">*</span>
    </div>
    <div ref="editorEl" />
    <div v-if="hint" class="text-caption text-grey-5 q-mt-xs">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import Editor from '@toast-ui/editor'
import '@toast-ui/editor/dist/toastui-editor.css'
import { api } from 'boot/axios'

const props = defineProps<{
  modelValue:   string | null | undefined
  label?:       string | undefined
  rows?:        number | undefined
  required?:    boolean | undefined
  placeholder?: string | undefined
  hint?:        string | undefined
  uploadUrl?:   string | undefined
}>()

const emit = defineEmits<{ 'update:modelValue': [v: string] }>()

const editorEl   = ref<HTMLElement>()
let editor: Editor | null = null
let externalSet  = false
let isComposing  = false

const editorMinHeight = `${Math.max((props.rows ?? 4) * 36, 160)}px`

async function uploadImageBlob(blob: Blob | File): Promise<string | null> {
  try {
    const fd = new FormData()
    fd.append('file', blob, blob instanceof File ? blob.name : 'image.png')
    const { data } = await api.post<{ url: string }>(props.uploadUrl ?? '/pm/uploads', fd)
    return data.url
  } catch {
    return null
  }
}

// 이미지 업로드를 전부 이 큐를 통해 직렬화한다. 같은 이미지를 빠르게 연속으로
// 붙여넣으면(Ctrl+V 반복) addImageBlobHook 호출이 서로 겹치면서 일부가 빈 링크로
// 삽입되는 문제가 있었는데, 붙여넣기 방식(단일/다중, hook/직접삽입)과 무관하게
// 모든 업로드를 하나의 체인으로 묶어 항상 이전 업로드가 끝난 뒤 다음이 시작되도록 한다.
let uploadChain: Promise<unknown> = Promise.resolve()
function queueUpload(blob: Blob | File): Promise<string | null> {
  const run = uploadChain.then(() => uploadImageBlob(blob))
  uploadChain = run.then(() => undefined, () => undefined)
  return run
}

function dataUrlToBlob(dataUrl: string): Blob {
  const sepIdx = dataUrl.indexOf(',')
  const header = dataUrl.slice(0, sepIdx)
  const b64    = dataUrl.slice(sepIdx + 1)
  const mime   = header.match(/data:([^;]+)/)?.[1] ?? 'image/png'
  const bytes  = new Uint8Array([...atob(b64)].map(c => c.charCodeAt(0)))
  return new Blob([bytes], { type: mime })
}

function handlePaste(e: Event) {
  const ce = e as ClipboardEvent
  if (!ce.clipboardData) return

  const items = Array.from(ce.clipboardData.items)

  const imageItems = items.filter(item => item.type.startsWith('image/'))

  // 이미지 여러 장을 한 번에 붙여넣으면 addImageBlobHook이 비동기로 동시에 여러 번
  // 호출되면서 완료 순서가 뒤섞여, 일부가 이미지가 아니라 빈 링크로 삽입되는 문제가
  // 있었다. 2장 이상이면 직접 순서대로 업로드 → 삽입해서 순서를 보장한다.
  if (imageItems.length > 1) {
    ce.preventDefault()
    ce.stopImmediatePropagation()
    const blobs = imageItems.map(item => item.getAsFile()).filter((f): f is File => !!f)
    void (async () => {
      for (const blob of blobs) {
        const url = await queueUpload(blob)
        if (url && editor) editor.exec('addImage', { imageUrl: url, altText: '' })
      }
    })()
    return
  }

  // 바이너리 이미지 한 장(스크린샷, 브라우저 복사)은 addImageBlobHook에 위임
  const hasBinaryImage = imageItems.length > 0
  if (hasBinaryImage) return

  // HTML clipboard with <img> (HWP, Word, etc.) — block alt-text insertion
  const html = ce.clipboardData.getData('text/html')
  if (html && /<img/i.test(html)) {
    ce.preventDefault()
    ce.stopImmediatePropagation()

    const plainText = ce.clipboardData.getData('text/plain').trim()
    if (plainText) {
      // Mixed text+image: insert text only (HWP alt-text garbage 방지)
      document.execCommand('insertText', false, plainText)
      return
    }

    // Pure image via HTML: try base64 data URL
    const match = html.match(/src="(data:image\/[^;]+;base64,[^"]+)"/)
    const dataSrc = match?.[1]
    if (dataSrc && editor) {
      const blob = dataUrlToBlob(dataSrc)
      void queueUpload(blob).then(url => {
        if (url && editor) editor.exec('addImage', { imageUrl: url, altText: '' })
      })
    }
    // local-path src with no text: blocked silently
  }
}

onMounted(() => {
  if (!editorEl.value) return
  editor = new Editor({
    el:              editorEl.value,
    height:          'auto',
    minHeight:       editorMinHeight,
    initialValue:    props.modelValue ?? '',
    initialEditType: 'wysiwyg',
    previewStyle:    'tab',
    placeholder:     props.placeholder ?? '내용을 입력하세요. (마크다운 문법 지원: # 제목, **굵게**, - 목록)',
    toolbarItems: [
      ['heading', 'bold', 'italic', 'strike'],
      ['hr', 'quote'],
      ['ul', 'ol', 'task'],
      ['image', 'link'],
      ['code', 'codeblock'],
    ],
    hooks: {
      addImageBlobHook: (blob, callback) => {
        void queueUpload(blob).then(url => {
          callback(url ?? '', url ? '' : '업로드 실패')
        })
      },
    },
    events: {
      change: () => {
        if (externalSet || isComposing) return
        emit('update:modelValue', editor?.getMarkdown() ?? '')
      },
    },
  })
  // capture phase so we intercept before ProseMirror embeds image as base64
  editorEl.value.addEventListener('paste', handlePaste, true)
  editorEl.value.addEventListener('compositionstart', () => { isComposing = true }, true)
  editorEl.value.addEventListener('compositionend', () => {
    isComposing = false
    if (!externalSet) emit('update:modelValue', editor?.getMarkdown() ?? '')
  }, true)
})

onBeforeUnmount(() => {
  editorEl.value?.removeEventListener('paste', handlePaste, true)
  editorEl.value?.removeEventListener('compositionstart', () => { isComposing = true }, true)
  editorEl.value?.removeEventListener('compositionend', () => { isComposing = false }, true)
  editor?.destroy()
  editor = null
})

watch(() => props.modelValue, async (newVal) => {
  if (!editor || isComposing) return
  const cur = editor.getMarkdown()
  if ((newVal ?? '') !== cur) {
    externalSet = true
    editor.setMarkdown(newVal ?? '')
    await nextTick()
    externalSet = false
  }
})
</script>

<style scoped>
.tui-label { font-size: 0.8rem; font-weight: 500; color: #555; }

:deep(.toastui-editor-defaultUI) {
  border-radius: 4px;
  border-color: rgba(0, 0, 0, 0.22);
  font-size: 0.9rem;
}
:deep(.toastui-editor-toolbar) {
  background: #fafafa;
  border-bottom-color: rgba(0, 0, 0, 0.1);
}
:deep(.toastui-editor-mode-switch) {
  background: #f5f5f5;
}
:deep(.toastui-editor .ProseMirror) {
  font-size: 0.9rem;
  line-height: 1.7;
}
:deep(.toastui-editor-contents) {
  font-size: 0.9rem;
  line-height: 1.7;
}
</style>
