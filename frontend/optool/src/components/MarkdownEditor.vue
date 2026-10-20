<template>
  <div class="markdown-editor-shell">
    <div v-if="label" class="tui-label q-mb-xs">
      {{ label }}<span v-if="required" class="text-negative q-ml-xs">*</span>
    </div>
    <div ref="editorEl" />
    <q-card v-if="slashCommands && slashVisible" class="slash-command-menu" :style="slashMenuStyle" @mousedown.prevent>
      <div class="slash-command-heading">블록 삽입</div>
      <q-list v-if="filteredSlashCommands.length" dense>
        <q-item v-for="(item, index) in filteredSlashCommands" :key="item.id" clickable
          :active="index === slashActiveIndex" active-class="bg-blue-1"
          @mouseenter="slashActiveIndex = index" @click="runSlashCommand(item)">
          <q-item-section avatar><q-icon :name="item.icon" color="primary" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ item.label }}</q-item-label>
            <q-item-label caption>{{ item.description }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else class="slash-command-empty">일치하는 명령이 없습니다.</div>
    </q-card>
    <q-card v-if="mentions && mentionVisible" class="slash-command-menu mention-command-menu" :style="mentionMenuStyle" @mousedown.prevent>
      <div class="slash-command-heading">사용자 멘션</div>
      <div v-if="mentionSearching" class="q-pa-sm text-center text-grey-6"><q-spinner size="xs" color="primary" /> 검색 중...</div>
      <q-list v-else-if="mentionResults.length" dense>
        <q-item v-for="(user, index) in mentionResults" :key="user.userId" clickable
          :active="index === mentionActiveIndex" active-class="bg-blue-1"
          @mouseenter="mentionActiveIndex = index" @click="insertMention(user)">
          <q-item-section avatar><q-avatar size="28px" color="primary" text-color="white">{{ user.displayName[0] }}</q-avatar></q-item-section>
          <q-item-section><q-item-label>{{ user.displayName }}</q-item-label><q-item-label caption>{{ [user.team, user.email].filter(Boolean).join(' · ') }}</q-item-label></q-item-section>
        </q-item>
      </q-list>
      <div v-else class="slash-command-empty">검색 결과가 없습니다.</div>
    </q-card>
    <input ref="slashImageInput" class="slash-image-input" type="file" accept="image/*" @change="handleSlashImageSelected">
    <div v-if="hint" class="text-caption text-grey-5 q-mt-xs">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import Editor from '@toast-ui/editor'
import '@toast-ui/editor/dist/toastui-editor.css'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { searchMentionUsers, type MentionUser } from 'src/services/mention'

const props = defineProps<{
  modelValue:   string | null | undefined
  label?:       string | undefined
  rows?:        number | undefined
  required?:    boolean | undefined
  placeholder?: string | undefined
  hint?:        string | undefined
  uploadUrl?:   string | undefined
  slashCommands?: boolean | undefined
  mentions?: boolean | undefined
}>()

const emit = defineEmits<{ 'update:modelValue': [v: string]; uploading: [value: boolean]; 'mention-selected': [user: MentionUser] }>()
const $q = useQuasar()

const editorEl   = ref<HTMLElement>()
const slashImageInput = ref<HTMLInputElement>()
type EditorPosition = number | [number, number]
type EditorSelection = [number, number] | [[number, number], [number, number]]
interface ToastEditorApi {
  exec(name: string, payload?: Record<string, unknown>): void
  focus(): void
  getMarkdown(): string
  getSelection(): EditorSelection
  isMarkdownMode(): boolean
  replaceSelection(text: string, start?: EditorPosition, end?: EditorPosition): void
  setMarkdown(markdown: string): void
  destroy(): void
}
let editor: ToastEditorApi | null = null
let externalSet  = false
let isComposing  = false
const slashVisible = ref(false)
const slashQuery = ref('')
const slashActiveIndex = ref(0)
const slashRange = ref<{ start: number | [number, number]; end: number | [number, number] } | null>(null)
const slashMenuStyle = ref({ top: '0px', left: '8px' })
const mentionVisible = ref(false)
const mentionQuery = ref('')
const mentionResults = ref<MentionUser[]>([])
const mentionActiveIndex = ref(0)
const mentionSearching = ref(false)
const mentionRange = ref<{ start: number | [number, number]; end: number | [number, number] } | null>(null)
const mentionMenuStyle = ref({ top: '0px', left: '8px' })
let mentionTimer: ReturnType<typeof setTimeout> | null = null
let mentionRequestSequence = 0

type SlashCommand = {
  id: string
  label: string
  description: string
  keywords: string
  icon: string
  command?: string
  payload?: Record<string, number>
  action?: 'image'
}

const slashCommandItems: SlashCommand[] = [
  { id: 'paragraph', label: '텍스트', description: '일반 문단을 입력합니다', keywords: 'text paragraph 문단 일반', icon: 'notes', command: 'heading', payload: { level: 0 } },
  { id: 'heading1', label: '제목 1', description: '큰 제목을 추가합니다', keywords: 'heading title 제목 h1', icon: 'format_h1', command: 'heading', payload: { level: 1 } },
  { id: 'heading2', label: '제목 2', description: '중간 제목을 추가합니다', keywords: 'heading title 제목 h2', icon: 'format_h2', command: 'heading', payload: { level: 2 } },
  { id: 'heading3', label: '제목 3', description: '작은 제목을 추가합니다', keywords: 'heading title 제목 h3', icon: 'format_h3', command: 'heading', payload: { level: 3 } },
  { id: 'bullet', label: '글머리 기호 목록', description: '항목을 점 목록으로 정리합니다', keywords: 'bullet list 목록 글머리 기호', icon: 'format_list_bulleted', command: 'bulletList' },
  { id: 'numbered', label: '번호 매기기 목록', description: '항목에 번호를 붙입니다', keywords: 'number ordered list 번호 순서', icon: 'format_list_numbered', command: 'orderedList' },
  { id: 'checklist', label: '체크리스트', description: '완료 여부를 표시하는 목록입니다', keywords: 'check task todo checklist 할일 체크', icon: 'checklist', command: 'taskList' },
  { id: 'quote', label: '인용', description: '인용 블록을 추가합니다', keywords: 'quote 인용', icon: 'format_quote', command: 'blockQuote' },
  { id: 'divider', label: '구분선', description: '내용을 구분하는 선을 추가합니다', keywords: 'divider line 구분선 선', icon: 'horizontal_rule', command: 'hr' },
  { id: 'table', label: '표', description: '3행 3열 표를 삽입합니다', keywords: 'table 표', icon: 'table_chart', command: 'addTable', payload: { rowCount: 3, columnCount: 3 } },
  { id: 'code', label: '코드 블록', description: '코드나 명령어를 입력합니다', keywords: 'code block 코드', icon: 'code', command: 'codeBlock' },
  { id: 'image', label: '이미지', description: '이미지를 업로드해 삽입합니다', keywords: 'image picture 이미지 사진', icon: 'image', action: 'image' },
]

const filteredSlashCommands = computed(() => {
  const query = slashQuery.value.trim().toLocaleLowerCase()
  if (!query) return slashCommandItems
  return slashCommandItems.filter(item => `${item.label} ${item.description} ${item.keywords}`.toLocaleLowerCase().includes(query))
})

function closeSlashMenu() {
  slashVisible.value = false
  slashRange.value = null
  slashQuery.value = ''
  slashActiveIndex.value = 0
}

function updateSlashMenu() {
  if (!props.slashCommands || isComposing || !editor || !editorEl.value) return
  const selection = window.getSelection()
  if (!selection?.rangeCount || !selection.isCollapsed) {
    closeSlashMenu()
    return
  }
  const caret = selection.getRangeAt(0)
  if (!editorEl.value.contains(caret.startContainer)) {
    closeSlashMenu()
    return
  }

  const startElement = caret.startContainer.nodeType === Node.ELEMENT_NODE
    ? caret.startContainer as Element
    : caret.startContainer.parentElement
  const block = startElement?.closest('.ProseMirror p, .ProseMirror h1, .ProseMirror h2, .ProseMirror h3, .ProseMirror h4, .ProseMirror h5, .ProseMirror h6, .ProseMirror li, .ProseMirror pre, .ProseMirror blockquote')
  if (!block) {
    closeSlashMenu()
    return
  }

  const beforeCaret = document.createRange()
  beforeCaret.selectNodeContents(block)
  beforeCaret.setEnd(caret.startContainer, caret.startOffset)
  const textBeforeCaret = beforeCaret.toString()
  const match = /(?:^|\s)\/([^\s]*)$/u.exec(textBeforeCaret)
  if (!match || !editor.getSelection()) {
    closeSlashMenu()
    return
  }

  const query = match[1] ?? ''
  const tokenLength = query.length + 1
  const selectionPos = editor.getSelection()
  if (editor.isMarkdownMode()) {
    const end = (selectionPos as [[number, number], [number, number]])[1]
    slashRange.value = { start: [end[0], Math.max(1, end[1] - tokenLength)], end }
  } else {
    const end = (selectionPos as [number, number])[1]
    slashRange.value = { start: Math.max(0, end - tokenLength), end }
  }

  if (query !== slashQuery.value) slashActiveIndex.value = 0
  slashQuery.value = query
  slashVisible.value = true
  positionSlashMenu(caret)
}

function closeMentionMenu() {
  mentionVisible.value = false
  mentionRange.value = null
  mentionQuery.value = ''
  mentionResults.value = []
  if (mentionTimer) clearTimeout(mentionTimer)
  mentionTimer = null
  mentionRequestSequence += 1
}

function updateMentionMenu() {
  if (!props.mentions || isComposing || !editor || !editorEl.value) return
  const selection = window.getSelection()
  if (!selection?.rangeCount || !selection.isCollapsed) { closeMentionMenu(); return }
  const caret = selection.getRangeAt(0)
  if (!editorEl.value.contains(caret.startContainer)) { closeMentionMenu(); return }
  const startElement = caret.startContainer.nodeType === Node.ELEMENT_NODE
    ? caret.startContainer as Element
    : caret.startContainer.parentElement
  const block = startElement?.closest('.ProseMirror p, .ProseMirror h1, .ProseMirror h2, .ProseMirror h3, .ProseMirror h4, .ProseMirror h5, .ProseMirror h6, .ProseMirror li, .ProseMirror pre, .ProseMirror blockquote')
  if (!block) { closeMentionMenu(); return }
  const beforeCaret = document.createRange()
  beforeCaret.selectNodeContents(block)
  beforeCaret.setEnd(caret.startContainer, caret.startOffset)
  const textBeforeCaret = beforeCaret.toString()
  const match = /(?:^|\s)@([^\s@]*)$/u.exec(textBeforeCaret)
  if (!match) { closeMentionMenu(); return }
  const query = match[1] ?? ''
  const tokenLength = query.length + 1
  const selectionPos = editor.getSelection()
  if (editor.isMarkdownMode()) {
    const end = (selectionPos as [[number, number], [number, number]])[1]
    mentionRange.value = { start: [end[0], Math.max(1, end[1] - tokenLength)], end }
  } else {
    const end = (selectionPos as [number, number])[1]
    mentionRange.value = { start: Math.max(0, end - tokenLength), end }
  }
  // An empty query is the normal state immediately after typing `@`. Since
  // mentionQuery also starts empty, include visibility so that first lookup
  // still runs instead of waiting for the user to type another character.
  if (query !== mentionQuery.value || !mentionVisible.value) {
    mentionQuery.value = query
    mentionActiveIndex.value = 0
    if (mentionTimer) clearTimeout(mentionTimer)
    const sequence = ++mentionRequestSequence
    mentionSearching.value = true
    mentionVisible.value = true
    mentionTimer = setTimeout(() => {
      void searchMentionUsers(query, 30).then(results => {
        if (sequence === mentionRequestSequence) mentionResults.value = results
      }).catch(() => {
        if (sequence === mentionRequestSequence) mentionResults.value = []
      }).finally(() => {
        if (sequence === mentionRequestSequence) mentionSearching.value = false
      })
    }, 180)
  } else {
    mentionVisible.value = true
  }
  positionSlashMenu(caret)
  mentionMenuStyle.value = { ...slashMenuStyle.value }
}

function insertMention(user: MentionUser) {
  if (!editor || !mentionRange.value) return
  const range = mentionRange.value
  closeMentionMenu()
  editor.focus()
  editor.replaceSelection(`@${user.displayName} `, range.start, range.end)
  emit('mention-selected', user)
  emit('update:modelValue', editor.getMarkdown())
}

function positionSlashMenu(caret: Range) {
  const host = editorEl.value?.parentElement
  if (!host) return
  const hostRect = host.getBoundingClientRect()
  const caretRect = caret.getBoundingClientRect()
  const menuWidth = Math.min(320, host.clientWidth - 16)
  const left = Math.max(8, Math.min(caretRect.left - hostRect.left, host.clientWidth - menuWidth - 8))
  const top = Math.max(48, caretRect.bottom - hostRect.top + host.scrollTop + 4)
  slashMenuStyle.value = { top: `${top}px`, left: `${left}px` }
}

function handleSlashKeydown(event: KeyboardEvent) {
  if (props.mentions && mentionVisible.value && !isComposing && !event.isComposing) {
    if (event.key === 'Escape') {
      event.preventDefault(); event.stopPropagation(); closeMentionMenu(); return
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); event.stopPropagation()
      if (mentionResults.value.length) {
        const direction = event.key === 'ArrowDown' ? 1 : -1
        mentionActiveIndex.value = (mentionActiveIndex.value + direction + mentionResults.value.length) % mentionResults.value.length
      }
      return
    }
    if ((event.key === 'Enter' || event.key === 'Tab') && mentionResults.value.length) {
      event.preventDefault(); event.stopPropagation()
      const user = mentionResults.value[mentionActiveIndex.value]
      if (user) insertMention(user)
      return
    }
  }
  if (!props.slashCommands || !slashVisible.value || isComposing || event.isComposing) return
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    closeSlashMenu()
  } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    event.stopPropagation()
    const count = filteredSlashCommands.value.length
    if (!count) return
    const direction = event.key === 'ArrowDown' ? 1 : -1
    slashActiveIndex.value = (slashActiveIndex.value + direction + count) % count
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    const item = filteredSlashCommands.value[slashActiveIndex.value]
    if (!item) return
    event.preventDefault()
    event.stopPropagation()
    runSlashCommand(item)
  }
}

function scheduleSlashMenuUpdate() {
  if (isComposing || (!props.slashCommands && !props.mentions)) return
  if (props.slashCommands) requestAnimationFrame(updateSlashMenu)
  if (props.mentions) requestAnimationFrame(updateMentionMenu)
}

function runSlashCommand(item: SlashCommand) {
  if (!editor || !slashRange.value) return
  const range = slashRange.value
  closeSlashMenu()
  editor.focus()
  editor.replaceSelection('', range.start, range.end)
  if (item.action === 'image') {
    if (slashImageInput.value) {
      slashImageInput.value.value = ''
      slashImageInput.value.click()
    }
    return
  }
  if (item.command) editor.exec(item.command, item.payload)
  emit('update:modelValue', editor.getMarkdown())
}

function handleSlashImageSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  void queueUpload(file).then(url => {
    if (!url || !editor) {
      $q.notify({ type: 'negative', message: '이미지를 업로드하지 못했습니다.' })
      return
    }
    editor.focus()
    editor.exec('addImage', { imageUrl: url, altText: file.name })
    emit('update:modelValue', editor.getMarkdown())
  })
}

function handleEditorFocusout() {
  setTimeout(() => {
    if (editorEl.value && !editorEl.value.contains(document.activeElement)) { closeSlashMenu(); closeMentionMenu() }
  }, 0)
}

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
let pendingUploads = 0
function queueUpload(blob: Blob | File): Promise<string | null> {
  pendingUploads += 1
  emit('uploading', true)
  const run = uploadChain.then(() => uploadImageBlob(blob))
  uploadChain = run.then(() => undefined, () => undefined)
  return run.finally(() => {
    pendingUploads -= 1
    // Keep saving disabled until the consumer has inserted the returned image.
    setTimeout(() => emit('uploading', pendingUploads > 0), 0)
  })
}

function dataUrlToBlob(dataUrl: string): Blob {
  const sepIdx = dataUrl.indexOf(',')
  const header = dataUrl.slice(0, sepIdx)
  const b64    = dataUrl.slice(sepIdx + 1)
  const mime   = header.match(/data:([^;]+)/)?.[1] ?? 'image/png'
  const bytes  = new Uint8Array([...atob(b64)].map(c => c.charCodeAt(0)))
  return new Blob([bytes], { type: mime })
}

function usableImageSource(source: string): boolean {
  try {
    const url = new URL(source, window.location.origin)
    return ['http:', 'https:'].includes(url.protocol)
      || /^data:image\/[a-z0-9.+-]+;base64,/i.test(source)
  } catch {
    return false
  }
}

function htmlImageSources(html: string): string[] {
  if (!html || !/<img\b/i.test(html)) return []
  const parsed = new DOMParser().parseFromString(html, 'text/html')
  return Array.from(parsed.images)
    .map(image => image.getAttribute('src')?.trim() ?? '')
    .filter((source, index, sources) => usableImageSource(source) && sources.indexOf(source) === index)
}

function insertImageSource(source: string) {
  if (!editor || !usableImageSource(source)) return
  if (/^data:image\//i.test(source)) {
    void queueUpload(dataUrlToBlob(source)).then(url => {
      if (url && editor) editor.exec('addImage', { imageUrl: url, altText: '' })
    })
    return
  }
  editor.exec('addImage', { imageUrl: source, altText: '' })
}

function handlePaste(e: Event) {
  const ce = e as ClipboardEvent
  if (!ce.clipboardData) return

  const items = Array.from(ce.clipboardData.items)

  const imageItems = items.filter(item => item.type.startsWith('image/'))

  // 이미지 여러 장을 한 번에 붙여넣으면 addImageBlobHook이 비동기로 동시에 여러 번
  // 호출되면서 완료 순서가 뒤섞여, 일부가 이미지가 아니라 빈 링크로 삽입되는 문제가
  // 있었다. 2장 이상이면 직접 순서대로 업로드 → 삽입해서 순서를 보장한다.
  if (imageItems.length > 0) {
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
  const sources = htmlImageSources(html)
  if (sources.length) {
    ce.preventDefault()
    ce.stopImmediatePropagation()
    sources.forEach(insertImageSource)
    return
  }
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
      ['table'],
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
        scheduleSlashMenuUpdate()
      },
    },
  }) as unknown as ToastEditorApi
  // capture phase so we intercept before ProseMirror embeds image as base64
  editorEl.value.addEventListener('paste', handlePaste, true)
  editorEl.value.addEventListener('keydown', handleSlashKeydown, true)
  editorEl.value.addEventListener('input', scheduleSlashMenuUpdate, true)
  editorEl.value.addEventListener('keyup', scheduleSlashMenuUpdate, true)
  editorEl.value.addEventListener('focusout', handleEditorFocusout, true)
  editorEl.value.addEventListener('compositionstart', handleCompositionStart, true)
  editorEl.value.addEventListener('compositionend', handleCompositionEnd, true)
})

function handleCompositionStart() {
  isComposing = true
}

function handleCompositionEnd() {
  isComposing = false
  if (!externalSet) emit('update:modelValue', editor?.getMarkdown() ?? '')
  scheduleSlashMenuUpdate()
}

onBeforeUnmount(() => {
  emit('uploading', false)
  editorEl.value?.removeEventListener('paste', handlePaste, true)
  editorEl.value?.removeEventListener('keydown', handleSlashKeydown, true)
  editorEl.value?.removeEventListener('input', scheduleSlashMenuUpdate, true)
  editorEl.value?.removeEventListener('keyup', scheduleSlashMenuUpdate, true)
  editorEl.value?.removeEventListener('focusout', handleEditorFocusout, true)
  editorEl.value?.removeEventListener('compositionstart', handleCompositionStart, true)
  editorEl.value?.removeEventListener('compositionend', handleCompositionEnd, true)
  if (mentionTimer) clearTimeout(mentionTimer)
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
.markdown-editor-shell { position: relative; min-width: 0; }
.tui-label { font-size: 0.8rem; font-weight: 500; color: #555; }
.slash-image-input { display: none; }
.slash-command-menu {
  position: absolute;
  z-index: 3000;
  width: min(320px, calc(100% - 16px));
  max-height: 320px;
  overflow-y: auto;
  background: #fff;
  box-shadow: 0 6px 22px rgba(15, 23, 42, 0.18);
}
.slash-command-heading {
  padding: 9px 14px 5px;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
}
.slash-command-empty { padding: 16px; color: #64748b; font-size: 13px; }

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
