<template>
  <q-page padding class="sr-request-page">

    <div class="row items-center q-mb-md">
      <q-btn flat dense round icon="arrow_back" class="q-mr-xs" @click="$router.back()" />
      <div>
        <div class="text-h6 text-weight-bold">{{ editId ? 'SR 수정' : 'SR 접수' }}</div>
        <div class="text-caption text-grey-5">{{ editId ? 'SR 내용을 수정합니다.' : '데이터운영팀에 업무 요청을 접수합니다.' }}</div>
      </div>
    </div>

    <!-- 수정 모드 안내 배너 -->
    <q-banner v-if="editId" inline-actions rounded class="bg-amber-1 q-mb-md">
      <template #avatar><q-icon name="edit" color="amber-8" size="22px" /></template>
      <div class="text-weight-medium text-amber-9">SR을 수정하고 있습니다.</div>
      <div class="text-caption text-amber-7 q-mt-xs">수정 후 저장하면 변경 이력이 자동으로 기록됩니다.</div>
    </q-banner>

    <!-- ── 임시저장 불러오기 배너 ── -->
    <q-banner v-if="drafts.length && !draftId" inline-actions rounded class="bg-blue-1 q-mb-md draft-banner">
      <template #avatar>
        <q-icon name="restore_page" color="blue-7" size="22px" />
      </template>
      <div class="text-weight-medium text-blue-9">작성 중인 임시저장 SR이 있습니다.</div>
      <div class="text-caption text-blue-7 q-mt-xs">불러와서 이어서 작성할 수 있습니다.</div>
      <div class="q-mt-sm row q-gutter-xs">
        <q-chip
          v-for="d in drafts" :key="d.id"
          clickable dense icon="edit_note"
          color="blue-2" text-color="blue-10"
          :loading="draftLoading === d.id"
          @click="loadDraft(d.id)"
        >
          {{ d.title || '(제목 없음)' }}
          <span class="q-ml-xs text-blue-6" style="font-size:0.72rem">{{ fmtDate(d.createdAt) }}</span>
        </q-chip>
      </div>
      <template #action>
        <q-btn flat dense round icon="close" color="blue-7" size="sm" @click="drafts = []" />
      </template>
    </q-banner>

    <!-- 불러온 draft 표시 (수정 모드에서는 숨김) -->
    <q-banner v-if="draftId && !editId" inline-actions rounded class="bg-amber-1 q-mb-md">
      <template #avatar><q-icon name="edit_note" color="amber-8" size="20px" /></template>
      <span class="text-weight-medium text-amber-9">임시저장된 SR을 이어서 작성 중입니다.</span>
      <template #action>
        <q-btn flat dense label="새로 작성" color="amber-8" size="sm" @click="resetDraft" />
      </template>
    </q-banner>

    <q-stepper v-model="step" flat animated header-nav color="primary" class="sr-stepper">

      <!-- ── Step 1: 요청 유형 선택 ── -->
      <q-step :name="1" title="유형 선택" icon="category" :done="step > 1">
        <div class="step-body">
          <div class="section-label q-mb-md">어떤 유형의 요청인가요?</div>
          <div class="type-card-grid">
            <div
              v-for="t in typeCards" :key="t.value"
              class="type-card"
              :class="{ 'type-card--selected': form.requestType === t.value }"
              @click="selectType(t.value)"
            >
              <q-icon :name="t.icon" size="26px"
                :color="form.requestType === t.value ? 'primary' : 'grey-5'" />
              <div class="type-card__name">{{ t.label }}</div>
              <div class="type-card__desc">{{ t.desc }}</div>
            </div>
          </div>
        </div>
        <q-stepper-navigation>
          <q-btn unelevated color="primary" label="다음 단계" icon-right="chevron_right" @click="goToStep2" />
        </q-stepper-navigation>
      </q-step>

      <!-- ── Step 2: 공통 정보 ── -->
      <q-step :name="2" title="기본 정보" icon="edit_note" :done="step > 2">
        <div class="step-body">

          <!-- 선택된 유형 표시 -->
          <div v-if="selectedTypeCard" class="selected-type-badge q-mb-sm">
            <q-icon :name="selectedTypeCard.icon" size="16px" color="primary" />
            <span>{{ selectedTypeCard.label }}</span>
            <q-btn flat dense size="xs" label="유형 변경" color="grey-6" @click="step = 1" />
          </div>

          <div class="form-section">
            <div class="section-label">요청 제목</div>
            <q-input v-model="form.title" outlined dense
              placeholder="한 줄로 요약해주세요."
              :rules="[v => !!v || '필수 항목입니다.']" />
          </div>

          <div class="form-section">
            <div class="section-label">기본 정보</div>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-sm-6">
                <q-input v-model="form.requesterDepartment" label="요청 부서" outlined dense
                  :rules="[v => !!v || '필수 항목입니다.']" />
              </div>
              <div class="col-12 col-sm-6">
                <q-input v-model="form.relatedSystem" label="대상 시스템" outlined dense
                  placeholder="어떤 시스템에 대한 요청인지"
                  :rules="[v => !!v || '필수 항목입니다.']" />
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-label">요청 배경 <span class="optional">(선택)</span></div>
            <q-input v-model="form.background" outlined dense type="textarea" :rows="2"
              placeholder="이 요청이 발생하게 된 배경이나 상황을 설명해주세요." />
          </div>

          <div class="form-section">
            <div class="section-label">일정 및 중요도</div>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-sm-4">
                <q-input v-model="form.desiredDueDate" label="희망 완료일" outlined dense type="date" />
              </div>
              <div class="col-12 col-sm-4">
                <q-select v-model="form.priority" label="중요도" outlined dense
                  :options="priorityOptions" emit-value map-options />
              </div>
              <div class="col-12 col-sm-4 flex items-center q-pt-xs">
                <q-toggle v-model="form.isUrgent" label="긴급 요청" color="negative" dense />
              </div>
            </div>
            <q-slide-transition>
              <q-input v-if="form.isUrgent" v-model="form.urgentReason"
                label="긴급 사유" outlined dense type="textarea" :rows="2"
                class="q-mt-sm urgent-input"
                :rules="[v => !form.isUrgent || !!v || '긴급 사유를 입력해주세요.']" />
            </q-slide-transition>
          </div>

        </div>
        <q-stepper-navigation>
          <q-btn unelevated color="primary" label="다음 단계" icon-right="chevron_right" @click="goToStep3" />
          <q-btn flat color="grey-7" label="이전" class="q-ml-sm" @click="step = 1" />
        </q-stepper-navigation>
      </q-step>

      <!-- ── Step 3: 유형별 추가 정보 ── -->
      <q-step :name="3" title="추가 정보" icon="playlist_add" :done="step > 3">
        <div class="step-body">
          <!-- 추가 항목 없는 경우 (ETC 등) -->
          <div v-if="!currentTypeFields.length" class="no-extra-fields">
            <q-icon name="check_circle_outline" size="2.5rem" color="positive" />
            <div class="text-subtitle2 q-mt-sm">추가 입력 항목이 없습니다.</div>
            <div class="text-caption text-grey-5">다음 단계로 진행해주세요.</div>
          </div>

          <template v-else>
            <div class="section-label q-mb-md">
              {{ selectedTypeCard?.label }} — 유형별 필수 정보를 입력해주세요.
            </div>
            <div class="row q-col-gutter-md">
              <div
                v-for="field in currentTypeFields" :key="field.key"
                :class="field.half ? 'col-12 col-sm-6' : 'col-12'"
              >
                <!-- textarea -->
                <template v-if="field.type === 'textarea'">
                  <div class="field-label">
                    {{ field.label }}
                    <span v-if="field.required" class="text-negative"> *</span>
                  </div>
                  <q-input
                    v-model="typeDetail[field.key]"
                    outlined dense type="textarea"
                    :rows="field.rows ?? 3"
                    :placeholder="field.placeholder"
                    :rules="field.required ? [v => !!v || '필수 항목입니다.'] : []"
                  />
                </template>

                <!-- select -->
                <template v-else-if="field.type === 'select'">
                  <q-select
                    v-model="typeDetail[field.key]"
                    :label="field.label + (field.required ? ' *' : '')"
                    outlined dense
                    :options="field.options"
                    emit-value map-options
                    :rules="field.required ? [v => !!v || '필수 항목입니다.'] : []"
                  />
                </template>

                <!-- editor (rich text) -->
                <template v-else-if="field.type === 'editor'">
                  <div class="field-label">
                    {{ field.label }}
                    <span v-if="field.required" class="text-negative"> *</span>
                    <span class="editor-tip">
                      <q-icon name="info" size="13px" color="grey-5" />
                      이미지 붙여넣기(Ctrl+V)로 본문에 삽입할 수 있습니다.
                    </span>
                  </div>
                  <q-editor
                    ref="editorRef"
                    v-model="form.description"
                    :toolbar="editorToolbar"
                    min-height="12rem"
                    class="sr-editor"
                  />
                  <input ref="fileInputRef" type="file" class="hidden-input"
                    accept="image/*,.pdf,.hwp,.docx,.xlsx,.pptx,.zip"
                    @change="onFileInputChange" />
                  <teleport to="body">
                    <div v-if="imgToolbar.open" class="img-resize-toolbar"
                      :style="{ top: imgToolbar.y + 'px', left: imgToolbar.x + 'px' }">
                      <span class="img-toolbar-label">크기</span>
                      <q-btn-group flat dense>
                        <q-btn v-for="w in [25, 50, 75, 100]" :key="w"
                          flat dense size="xs" :label="w + '%'"
                          :class="imgToolbar.width === w ? 'text-white bg-primary' : 'text-grey-3'"
                          @click.stop="setImgWidth(w)" />
                      </q-btn-group>
                      <q-separator dark vertical class="q-mx-xs" />
                      <q-btn flat dense size="xs" icon="delete" color="red-3" @click.stop="removeImg" />
                    </div>
                  </teleport>
                </template>

                <!-- date / datetime / text -->
                <template v-else>
                  <q-input
                    v-model="typeDetail[field.key]"
                    :label="field.label + (field.required ? ' *' : '')"
                    outlined dense
                    :type="field.type === 'datetime' ? 'datetime-local' : field.type"
                    :placeholder="field.placeholder"
                    :rules="field.required ? [v => !!v || '필수 항목입니다.'] : []"
                  />
                </template>
              </div>
            </div>
          </template>
        </div>
        <q-stepper-navigation>
          <q-btn unelevated color="primary" label="다음 단계" icon-right="chevron_right" @click="goToStep4" />
          <q-btn flat color="grey-7" label="이전" class="q-ml-sm" @click="step = 2" />
        </q-stepper-navigation>
      </q-step>

      <!-- ── Step 4: 첨부 및 제출 ── -->
      <q-step :name="4" title="첨부 및 제출" icon="check_circle">
        <div class="step-body">

          <div class="form-section">
            <div class="section-label">추가 첨부파일 <span class="optional">(선택)</span></div>
            <q-uploader
              url="/api/pm/uploads"
              label="파일을 드래그하거나 클릭하여 업로드"
              multiple
              accept=".pdf,.hwp,.docx,.xlsx,.pptx,.zip,.jpg,.jpeg,.png,.gif"
              max-file-size="20971520"
              flat bordered class="full-width"
              :headers="uploadHeaders"
              @uploaded="onFileUploaded"
              @failed="onUploadFailed"
            />
            <div v-if="extraAttachments.length" class="q-mt-sm row q-gutter-xs">
              <q-chip v-for="(att, i) in extraAttachments" :key="i"
                removable @remove="extraAttachments.splice(i, 1)"
                icon="attach_file" color="blue-1" text-color="blue-9" size="sm">
                {{ att.originalName }}
              </q-chip>
            </div>
          </div>

          <div class="form-section">
            <div class="section-label">비고 <span class="optional">(선택)</span></div>
            <q-input v-model="form.note" outlined dense type="textarea" :rows="2" />
          </div>

          <!-- 제출 전 요약 -->
          <div class="form-section">
            <div class="section-label">제출 전 확인</div>
            <div class="summary-grid">
              <div class="summary-item">
                <div class="summary-key">요청 유형</div>
                <div class="summary-val">{{ selectedTypeCard?.label ?? '-' }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-key">요청 제목</div>
                <div class="summary-val">{{ form.title || '-' }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-key">요청자 / 부서</div>
                <div class="summary-val">{{ form.requesterName || '-' }} / {{ form.requesterDepartment || '-' }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-key">대상 시스템</div>
                <div class="summary-val">{{ form.relatedSystem || '-' }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-key">중요도</div>
                <div class="summary-val">
                  <q-badge :color="priorityColor(form.priority)" :label="priorityLabel(form.priority)" />
                  <q-badge v-if="form.isUrgent" color="negative" label="긴급" class="q-ml-xs" />
                </div>
              </div>
              <div class="summary-item">
                <div class="summary-key">희망 완료일 / 첨부파일</div>
                <div class="summary-val">{{ form.desiredDueDate || '-' }} · {{ editorAttachments.length + extraAttachments.length }}개</div>
              </div>
            </div>
          </div>

        </div>
        <q-stepper-navigation>
          <q-btn unelevated color="primary" :icon="editId ? 'save' : 'send'" :label="editId ? '수정 저장' : '접수하기'" :loading="saving" @click="save(true)" />
          <q-btn v-if="!editId" outline color="grey-6" label="임시저장" :loading="saving" class="q-ml-sm" @click="save(false)" />
          <q-btn flat color="grey-7" label="이전" class="q-ml-sm" @click="step = 3" />
        </q-stepper-navigation>
      </q-step>

    </q-stepper>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import {
  createSR, updateSR, getSR, listMySRs,
  SR_PRIORITY_OPTIONS, SR_PRIORITY_LABEL, SR_PRIORITY_COLOR,
  type SRAttachment, type SRAttachmentInput, type RequestType, type SRPriority, type SRListItem,
} from 'src/services/sr'
import { SR_TYPE_FIELDS, TYPE_CARDS } from 'src/services/sr-type-fields'

const $q        = useQuasar()
const router    = useRouter()
const route     = useRoute()
const authStore = useAuthStore()

// 수정 모드: /pm/sr/:id/edit 경로로 진입 시 editId가 설정됨
const editId = computed(() => route.params.id as string | undefined)

const step             = ref(1)
const saving           = ref(false)
const editorAttachments = ref<SRAttachment[]>([])
const extraAttachments  = ref<SRAttachment[]>([])
const editorRef        = ref()
const fileInputRef     = ref<HTMLInputElement | null>(null)
const selectedImg      = ref<HTMLImageElement | null>(null)
const imgToolbar       = ref({ open: false, x: 0, y: 0, width: 100 })
const drafts           = ref<SRListItem[]>([])
const draftId          = ref<string | null>(null)
const draftLoading     = ref<string | null>(null)

const form = ref({
  title:                '',
  requesterName:        authStore.me?.fullName || '',
  requesterDepartment:  '',
  requesterEmail:       authStore.me?.email || '',
  requestType:          null as string | null,
  relatedSystem:        '',
  background:           '',
  description:          '',
  desiredDueDate:       null as string | null,
  priority:             'MEDIUM',
  isUrgent:             false,
  urgentReason:         '',
  note:                 '',
})

const typeDetail = ref<Record<string, string | null>>({})

// 유형이 바뀌면 type_detail 초기화
watch(() => form.value.requestType, () => { if (!editId.value) typeDetail.value = {} })

// 에디터 HTML에서 사라진 파일 제거
watch(() => form.value.description, (html) => {
  editorAttachments.value = editorAttachments.value.filter(att => html.includes(att.url))
})

// ── computed ─────────────────────────────────────────────────────────
const typeCards         = TYPE_CARDS
const priorityOptions   = SR_PRIORITY_OPTIONS
const currentTypeFields = computed(() => SR_TYPE_FIELDS[form.value.requestType ?? ''] ?? [])
const selectedTypeCard  = computed(() => typeCards.find(t => t.value === form.value.requestType))

// ── 에디터 툴바 ──────────────────────────────────────────────────────
const editorToolbar = [
  ['bold', 'italic', 'underline', 'strike'],
  ['ordered', 'unordered', 'quote'],
  ['link', 'removeFormat'],
  [{ label: '파일/이미지 첨부', icon: 'attach_file', tip: '파일 또는 이미지를 본문에 삽입', handler: () => fileInputRef.value?.click() }],
  ['undo', 'redo'],
  ['fullscreen'],
]

// ── 파일 업로드 ──────────────────────────────────────────────────────
async function uploadFile(file: File): Promise<SRAttachment> {
  const fd = new FormData()
  fd.append('file', file)
  const token = authStore.token
  const res = await fetch('/api/pm/uploads', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  })
  if (!res.ok) throw new Error('upload failed')
  const d = await res.json() as { file_id?: string; fileId?: string; original_name?: string; originalName?: string; url: string; size: number; content_type?: string; contentType?: string }
  return { fileId: d.file_id || d.fileId || '', originalName: d.original_name || d.originalName || '', url: d.url, size: d.size, contentType: d.content_type || d.contentType || '' }
}

function insertIntoEditor(att: SRAttachment) {
  const isImage = att.contentType.startsWith('image/')
  const html = isImage
    ? `<img src="${att.url}" alt="${att.originalName}" style="max-width:100%;border-radius:4px;margin:4px 0;" />`
    : `<a href="${att.url}" target="_blank" style="display:inline-flex;align-items:center;gap:4px;">📎 ${att.originalName}</a>`
  editorRef.value?.runCmd('insertHTML', html)
}

async function onFileInputChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  ;(e.target as HTMLInputElement).value = ''
  try {
    const att = await uploadFile(file)
    editorAttachments.value.push(att)
    insertIntoEditor(att)
  } catch { $q.notify({ type: 'negative', message: '파일 업로드에 실패했습니다.' }) }
}

function onEditorPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      e.preventDefault(); e.stopPropagation()
      const file = item.getAsFile()
      if (!file) break
      void uploadFile(file).then(att => { editorAttachments.value.push(att); insertIntoEditor(att) })
        .catch(() => $q.notify({ type: 'negative', message: '이미지 붙여넣기 실패' }))
      break
    }
  }
}

// ── 이미지 크기 조절 ─────────────────────────────────────────────────
function onEditorClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.tagName === 'IMG') {
    selectedImg.value = target as HTMLImageElement
    const rect = target.getBoundingClientRect()
    imgToolbar.value = { open: true, x: Math.min(rect.left, window.innerWidth - 260), y: rect.bottom + 8, width: parseInt((target as HTMLImageElement).style.width) || 100 }
  } else { imgToolbar.value.open = false; selectedImg.value = null }
}

function setImgWidth(w: number) {
  if (!selectedImg.value) return
  selectedImg.value.style.width = `${w}%`; selectedImg.value.style.height = 'auto'
  imgToolbar.value.width = w; syncEditorModel()
}
function removeImg() {
  selectedImg.value?.remove(); imgToolbar.value.open = false; selectedImg.value = null; syncEditorModel()
}
function syncEditorModel() {
  const el = editorRef.value?.$el?.querySelector('[contenteditable]') as HTMLElement | null
  el?.dispatchEvent(new Event('input', { bubbles: true }))
}
function dismissImgToolbar(e: MouseEvent) {
  const toolbar = document.querySelector('.img-resize-toolbar')
  if (toolbar && !toolbar.contains(e.target as Node)) { imgToolbar.value.open = false; selectedImg.value = null }
}

onMounted(async () => {
  const el = editorRef.value?.$el?.querySelector('[contenteditable]') as HTMLElement | null
  el?.addEventListener('paste', onEditorPaste as EventListener, true)
  el?.addEventListener('click', onEditorClick as EventListener)
  document.addEventListener('click', dismissImgToolbar)

  if (editId.value) {
    // 수정 모드: PENDING_INFO 상태 SR 불러오기
    await loadSrForEdit(editId.value)
  } else {
    try {
      drafts.value = await listMySRs({ status: 'DRAFT' })
    } catch { /* 조용히 실패 */ }
  }
})
onBeforeUnmount(() => {
  const el = editorRef.value?.$el?.querySelector('[contenteditable]') as HTMLElement | null
  el?.removeEventListener('paste', onEditorPaste as EventListener, true)
  el?.removeEventListener('click', onEditorClick as EventListener)
  document.removeEventListener('click', dismissImgToolbar)
})

// ── 스텝 이동 ────────────────────────────────────────────────────────
function goToStep2() {
  if (!form.value.requestType) {
    $q.notify({ type: 'warning', message: '요청 유형을 선택해주세요.', position: 'top' })
    return
  }
  step.value = 2
}

function goToStep3() {
  if (!form.value.title.trim()) {
    $q.notify({ type: 'warning', message: '요청 제목을 입력해주세요.', position: 'top' })
    return
  }
  if (!form.value.requesterDepartment.trim()) {
    $q.notify({ type: 'warning', message: '요청 부서를 입력해주세요.', position: 'top' })
    return
  }
  if (!form.value.relatedSystem.trim()) {
    $q.notify({ type: 'warning', message: '대상 시스템을 입력해주세요.', position: 'top' })
    return
  }
  step.value = 3
}

function goToStep4() {
  const editorField = currentTypeFields.value.find(f => f.type === 'editor')
  if (editorField?.required) {
    const text = form.value.description.replace(/<[^>]*>/g, '').trim()
    if (!text) {
      $q.notify({ type: 'warning', message: `'${editorField.label}' 항목을 입력해주세요.`, position: 'top' })
      return
    }
  }
  const missing = currentTypeFields.value.find(f => f.type !== 'editor' && f.required && !typeDetail.value[f.key]?.trim())
  if (missing) {
    $q.notify({ type: 'warning', message: `'${missing.label}' 항목을 입력해주세요.`, position: 'top' })
    return
  }
  step.value = 4
}

function selectType(type: string) { form.value.requestType = type }

// ── Step 4 업로더 ────────────────────────────────────────────────────
const uploadHeaders = computed(() => {
  const token = authStore.token
  return token ? [{ name: 'Authorization', value: `Bearer ${token}` }] : []
})

function onFileUploaded(info: { files: readonly File[], xhr: XMLHttpRequest }) {
  try {
    const res = JSON.parse(info.xhr.response)
    extraAttachments.value.push({
      fileId: res.file_id || res.fileId || '',
      originalName: res.original_name || res.originalName || '',
      url: res.url, size: res.size,
      contentType: res.content_type || res.contentType || '',
    })
  } catch { $q.notify({ type: 'warning', message: '파일 업로드 응답 처리 중 오류가 발생했습니다.' }) }
}
function onUploadFailed() {
  $q.notify({ type: 'negative', message: '파일 업로드 실패 (최대 20MB, 허용 형식 확인)' })
}

// ── 헬퍼 ────────────────────────────────────────────────────────────
function priorityLabel(v: string) { return (SR_PRIORITY_LABEL as Record<string, string>)[v] ?? v }
function priorityColor(v: string) { return (SR_PRIORITY_COLOR as Record<string, string>)[v] ?? 'grey' }
function fmtDate(d: string) { return d ? d.substring(0, 10) : '' }

// ── 임시저장 불러오기 ─────────────────────────────────────────────────
async function loadDraft(id: string) {
  draftLoading.value = id
  try {
    const sr = await getSR(id)

    // request_type을 먼저 세팅 → watcher(typeDetail 초기화)가 큐에 쌓임
    form.value.requestType         = sr.requestType
    form.value.title                = sr.title
    form.value.requesterDepartment = sr.requesterDepartment
    form.value.relatedSystem       = sr.relatedSystem ?? ''
    form.value.background           = sr.background ?? ''
    form.value.description          = sr.description
    form.value.desiredDueDate     = sr.desiredDueDate ? sr.desiredDueDate.substring(0, 10) : null
    form.value.priority             = sr.priority
    form.value.isUrgent            = sr.isUrgent
    form.value.urgentReason        = sr.urgentReason ?? ''
    form.value.note                 = sr.note ?? ''
    editorAttachments.value         = sr.attachments.filter(a => sr.description.includes(a.url))
    extraAttachments.value          = sr.attachments.filter(a => !sr.description.includes(a.url))
    draftId.value = id
    drafts.value  = []
    step.value    = sr.requestType ? 2 : 1

    // nextTick으로 watcher를 먼저 소진(typeDetail = {}) 시킨 뒤 복원
    await nextTick()
    typeDetail.value = (sr.typeDetail as Record<string, string | null>) ?? {}
  } catch {
    $q.notify({ type: 'negative', message: '임시저장 불러오기에 실패했습니다.' })
  } finally {
    draftLoading.value = null
  }
}

function resetDraft() {
  draftId.value = null
  form.value = {
    title: '', requesterName: authStore.me?.fullName || '',
    requesterDepartment: '', requesterEmail: authStore.me?.email || '',
    requestType: null, relatedSystem: '', background: '', description: '',
    desiredDueDate: null, priority: 'MEDIUM', isUrgent: false, urgentReason: '', note: '',
  }
  typeDetail.value = {}
  editorAttachments.value = []
  extraAttachments.value  = []
  step.value = 1
}

// ── SR 수정 모드 불러오기 ─────────────────────────────────────────────
async function loadSrForEdit(id: string) {
  try {
    const sr = await getSR(id)
    form.value.requestType         = sr.requestType
    form.value.title                = sr.title
    form.value.requesterName        = sr.requesterName
    form.value.requesterDepartment  = sr.requesterDepartment
    form.value.requesterEmail       = sr.requesterEmail
    form.value.relatedSystem        = sr.relatedSystem ?? ''
    form.value.background           = sr.background ?? ''
    form.value.description          = sr.description
    form.value.desiredDueDate       = sr.desiredDueDate ? sr.desiredDueDate.substring(0, 10) : null
    form.value.priority             = sr.priority
    form.value.isUrgent             = sr.isUrgent
    form.value.urgentReason         = sr.urgentReason ?? ''
    form.value.note                 = sr.note ?? ''
    editorAttachments.value         = sr.attachments.filter(a => sr.description.includes(a.url))
    extraAttachments.value          = sr.attachments.filter(a => !sr.description.includes(a.url))
    draftId.value = id

    await nextTick()
    typeDetail.value = (sr.typeDetail as Record<string, string | null>) ?? {}
    step.value = 2
  } catch {
    $q.notify({ type: 'negative', message: 'SR 정보를 불러오지 못했습니다.' })
    void router.back()
  }
}

// ── 저장 ────────────────────────────────────────────────────────────
async function save(submit: boolean) {
  saving.value = true
  try {
    const payload = {
      title:                form.value.title,
      requester_name:       form.value.requesterName,
      requester_department: form.value.requesterDepartment,
      requester_email:      form.value.requesterEmail,
      request_type:         form.value.requestType as RequestType,
      related_system:       form.value.relatedSystem,
      background:           form.value.background,
      description:          form.value.description,
      desired_due_date:     form.value.desiredDueDate || null,
      priority:             form.value.priority as SRPriority,
      is_urgent:            form.value.isUrgent,
      urgent_reason:        form.value.urgentReason,
      note:                 form.value.note,
      attachments:          [...editorAttachments.value, ...extraAttachments.value].map((a): SRAttachmentInput => ({
        file_id: a.fileId, original_name: a.originalName, url: a.url, size: a.size, content_type: a.contentType,
      })),
      compliance_related:   false,
      type_detail:          Object.keys(typeDetail.value).length ? typeDetail.value : null,
      submit,
    }
    let sr
    if (draftId.value) {
      sr = await updateSR(draftId.value, payload)
      if (editId.value) {
        $q.notify({ type: 'positive', message: 'SR이 수정되었습니다.' })
      } else {
        $q.notify({ type: 'positive', message: submit ? `SR 접수 완료 (${sr.srNo})` : '임시저장되었습니다.' })
      }
    } else {
      sr = await createSR(payload)
      $q.notify({ type: 'positive', message: submit ? `SR 접수 완료 (${sr.srNo})` : '임시저장되었습니다.' })
    }
    void router.push(`/pm/sr/${sr.id}`)
  } catch (e) {
    const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
    const msg = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(' / ')
        : 'SR 접수에 실패했습니다.'
    $q.notify({ type: 'negative', message: msg })
  } finally { saving.value = false }
}
</script>

<style scoped>
.draft-banner :deep(.q-banner__content) { padding: 10px 0; }
.sr-stepper :deep(.q-stepper__header) { border-bottom: 1px solid #eee; }
.sr-stepper :deep(.q-stepper__step-inner) { padding: 20px 0 8px; }

.step-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 4px;
}

.section-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #616161;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.optional { font-size: 0.72rem; font-weight: 400; color: #bdbdbd; text-transform: none; margin-left: 4px; }

.form-section { display: flex; flex-direction: column; gap: 8px; }

.field-label { font-size: 0.8rem; color: #555; }

/* ── 유형 카드 ── */
.type-card-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 600px) {
  .type-card-grid { grid-template-columns: repeat(2, 1fr); }
}

.type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 16px 10px;
  border: 1.5px solid rgba(0,0,0,0.1);
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  background: #fafafa;
}
.type-card:hover {
  border-color: var(--q-primary);
  background: #fff;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.12);
}
.type-card--selected {
  border-color: var(--q-primary);
  background: #e8f1fd;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.18);
}
.type-card__name { font-size: 0.82rem; font-weight: 600; color: #333; }
.type-card__desc { font-size: 0.7rem; color: #9e9e9e; line-height: 1.3; }

/* ── 선택된 유형 뱃지 ── */
.selected-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--q-primary);
  background: #e8f1fd;
  border-radius: 20px;
  padding: 4px 12px 4px 10px;
}

/* ── 에디터 ── */
.editor-tip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 0.72rem;
  color: #bdbdbd;
  font-weight: 400;
  text-transform: none;
  margin-left: 8px;
}
.sr-editor {
  border: 1px solid rgba(0,0,0,0.22);
  border-radius: 4px;
  transition: border-color 0.2s;
}
.sr-editor:focus-within { border-color: var(--q-primary); }
.sr-editor :deep(.q-editor__content) { min-height: 12rem; font-size: 0.9rem; line-height: 1.75; padding: 12px 14px; }
.hidden-input { display: none; }

/* ── 긴급 입력 ── */
.urgent-input :deep(.q-field__control) { background: #fff5f5; }

/* ── 추가 항목 없음 ── */
.no-extra-fields {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: #757575;
}

/* ── 이미지 리사이즈 툴바 ── */
.img-resize-toolbar {
  position: fixed;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(30, 30, 30, 0.88);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  padding: 4px 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.img-toolbar-label { font-size: 0.72rem; color: #aaa; margin-right: 2px; white-space: nowrap; }

/* ── 요약 그리드 ── */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 6px;
  overflow: hidden;
}
.summary-item {
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.summary-item:nth-child(odd)        { border-right: 1px solid rgba(0,0,0,0.06); }
.summary-item:nth-last-child(-n+2)  { border-bottom: none; }
.summary-key { font-size: 0.72rem; color: #9e9e9e; margin-bottom: 3px; }
.summary-val { font-size: 0.88rem; color: #212121; }
</style>
