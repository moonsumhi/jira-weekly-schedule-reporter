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

  // 바이너리 이미지(스크린샷, 브라우저 복사)는 addImageBlobHook에 위임
  const hasBinaryImage = items.some(item => item.type.startsWith('image/'))
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
      void uploadImageBlob(blob).then(url => {
        if (url && editor) {
          editor.focus()
          editor.exec('addImage', { imageUrl: url, altText: '' })
        }
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
        void uploadImageBlob(blob).then(url => {
          callback(url ?? '', url ? '' : '업로드 실패')
        })
      },
    },
    events: {
      change: () => {
        if (externalSet) return
        emit('update:modelValue', editor?.getMarkdown() ?? '')
      },
    },
  })
  // capture phase so we intercept before ProseMirror embeds image as base64
  editorEl.value.addEventListener('paste', handlePaste, true)
})

onBeforeUnmount(() => {
  editorEl.value?.removeEventListener('paste', handlePaste, true)
  editor?.destroy()
  editor = null
})

watch(() => props.modelValue, async (newVal) => {
  if (!editor) return
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
