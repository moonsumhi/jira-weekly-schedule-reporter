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

const props = defineProps<{
  modelValue:   string | null | undefined
  label?:       string | undefined
  rows?:        number | undefined
  required?:    boolean | undefined
  placeholder?: string | undefined
  hint?:        string | undefined
}>()

const emit = defineEmits<{ 'update:modelValue': [v: string] }>()

const editorEl   = ref<HTMLElement>()
let editor: Editor | null = null
let externalSet  = false

const editorMinHeight = `${Math.max((props.rows ?? 4) * 36, 160)}px`

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
      ['link'],
      ['code', 'codeblock'],
    ],
    events: {
      change: () => {
        if (externalSet) return
        emit('update:modelValue', editor?.getMarkdown() ?? '')
      },
    },
  })
})

onBeforeUnmount(() => {
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

/* 테두리/라운딩 */
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
/* 에디터 본문 폰트 크기 */
:deep(.toastui-editor .ProseMirror) {
  font-size: 0.9rem;
  line-height: 1.7;
}
:deep(.toastui-editor-contents) {
  font-size: 0.9rem;
  line-height: 1.7;
}
</style>
