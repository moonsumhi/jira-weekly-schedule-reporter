<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]파일테스트4</div>
        <div class="text-caption text-grey-7">파일 분석 후 폼 틀 생성 및 DB 저장</div>
      </div>

      <!-- 파일 선택 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center q-col-gutter-md">
              <div class="col-12 col-md-8">
                <q-file
                  v-model="selectedFile"
                  :label="'파일 선택 (PDF / HWP / DOCX)'"
                  accept=".pdf,.hwp,.docx,.doc"
                  outlined
                  clearable
                  @update:model-value="onFileSelected"
                >
                  <template v-slot:prepend>
                    <q-icon :name="fileIcon" :color="fileIconColor" />
                  </template>
                </q-file>
              </div>
              <div class="col-12 col-md-4">
                <div class="row q-gutter-sm">
                  <q-btn
                    label="폼 분석"
                    icon="auto_awesome"
                    color="deep-purple"
                    :disable="!selectedFile || analyzing"
                    :loading="analyzing"
                    @click="analyzeContent"
                  />
                  <q-btn
                    label="초기화"
                    icon="refresh"
                    outline
                    color="grey-7"
                    @click="resetAll"
                  />
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 진행 상태 -->
      <div v-if="analyzing || saving" class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">{{ statusMessage }}</div>
            <q-linear-progress indeterminate color="deep-purple" class="q-mb-xs" />
          </q-card-section>
        </q-card>
      </div>

      <!-- 분석 결과: 폼 틀 미리보기 + 저장 -->
      <div v-if="result" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-deep-purple text-white row items-center">
            <q-icon name="auto_awesome" size="24px" class="q-mr-sm" />
            <div class="text-h6 text-weight-bold">{{ result.title }}</div>
            <q-space />
            <q-btn
              label="DB 저장"
              icon="save"
              color="white"
              text-color="deep-purple"
              :loading="saving"
              :disable="saving"
              @click="openSaveDialog"
            />
          </q-card-section>

          <q-card-section v-if="result.description || result.raw_summary">
            <div v-if="result.description" class="text-body2 text-grey-8 q-mb-sm">
              {{ result.description }}
            </div>
            <q-banner v-if="result.raw_summary" rounded class="bg-purple-1 text-grey-9">
              <template v-slot:avatar>
                <q-icon name="summarize" color="deep-purple" />
              </template>
              {{ result.raw_summary }}
            </q-banner>
          </q-card-section>

          <q-separator />

          <q-card-section>
            <div
              v-for="(section, sIdx) in result.sections"
              :key="sIdx"
              class="q-mb-lg"
            >
              <div class="text-subtitle1 text-weight-bold text-deep-purple q-mb-md">
                <q-icon name="segment" class="q-mr-xs" />{{ section.title }}
              </div>

              <div class="row q-col-gutter-md">
                <div
                  v-for="(field, fIdx) in section.fields"
                  :key="fIdx"
                  :class="fieldColClass(field)"
                >
                  <q-input
                    v-if="['text', 'number', 'date'].includes(field.type)"
                    model-value=""
                    :label="field.label + (field.required ? ' *' : '')"
                    :placeholder="field.placeholder"
                    :type="field.type === 'date' ? 'date' : (field.type as 'text' | 'number')"
                    outlined
                    dense
                    readonly
                    :hint="fieldTypeHint(field.type)"
                  />
                  <q-input
                    v-else-if="field.type === 'textarea'"
                    model-value=""
                    :label="field.label + (field.required ? ' *' : '')"
                    :placeholder="field.placeholder"
                    type="textarea"
                    outlined
                    dense
                    rows="3"
                    readonly
                    :hint="fieldTypeHint(field.type)"
                  />
                  <q-select
                    v-else-if="field.type === 'select'"
                    :model-value="null"
                    :label="field.label + (field.required ? ' *' : '')"
                    :options="field.options"
                    outlined
                    dense
                    readonly
                    :hint="fieldTypeHint(field.type)"
                  />
                  <q-checkbox
                    v-else-if="field.type === 'checkbox'"
                    :model-value="false"
                    :label="field.label"
                    disable
                  />
                </div>
              </div>

              <q-separator v-if="sIdx < result.sections.length - 1" class="q-mt-lg" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 저장 완료 -->
      <div v-if="savedTemplate" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-green-1 row items-center">
            <q-icon name="check_circle" color="positive" size="24px" class="q-mr-sm" />
            <div class="text-h6 text-weight-bold text-green-9">DB 저장 완료</div>
          </q-card-section>
          <q-card-section>
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  :model-value="savedTemplate.id"
                  label="저장된 템플릿 ID"
                  outlined
                  dense
                  readonly
                >
                  <template v-slot:append>
                    <q-btn flat dense icon="content_copy" @click="copyId" />
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  :model-value="savedTemplate.title"
                  label="템플릿 제목"
                  outlined
                  dense
                  readonly
                />
              </div>
              <div class="col-12">
                <q-input
                  :model-value="savedTemplate.created_at"
                  label="저장 일시"
                  outlined
                  dense
                  readonly
                />
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 안내 메시지 (파일 미선택 시) -->
      <div v-if="!selectedFile && !result" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="cloud_upload" size="64px" color="deep-purple-2" class="q-mb-md" />
            <div class="text-h6 text-grey-5">파일을 선택해주세요</div>
            <div class="text-caption q-mt-sm">
              PDF, HWP, DOCX 파일을 선택한 후 "폼 분석" 버튼을 클릭하면<br />
              AI가 문서 내용을 분석하여 폼 틀을 생성하고 DB에 저장할 수 있습니다.
            </div>
          </q-card-section>
        </q-card>
      </div>

    </div>

    <!-- 저장 다이얼로그 -->
    <q-dialog v-model="saveDialogOpen">
      <q-card style="min-width: 400px">
        <q-card-section class="row items-center">
          <div class="text-h6">폼 틀 DB 저장</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="saveTitle"
            label="템플릿 제목 *"
            outlined
            dense
            class="q-mb-md"
            :rules="[(v) => !!v || '제목을 입력해주세요.']"
          />
          <q-input
            v-model="saveIssueKey"
            label="Jira 이슈 키 (선택)"
            outlined
            dense
            placeholder="예: NCDC-000"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="취소" flat color="grey-7" v-close-popup />
          <q-btn
            label="저장"
            icon="save"
            color="deep-purple"
            :disable="!saveTitle"
            @click="saveTemplate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuasar } from 'quasar'
import * as pdfjsLib from 'pdfjs-dist'
import { api } from 'boot/axios'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString()

const $q = useQuasar()

const selectedFile = ref<File | null>(null)
const analyzing = ref(false)
const saving = ref(false)
const statusMessage = ref('')
const saveDialogOpen = ref(false)
const saveTitle = ref('')
const saveIssueKey = ref('')

interface TemplateField {
  label: string
  type: string
  placeholder: string
  required: boolean
  options: string[]
}

interface TemplateSection {
  title: string
  fields: TemplateField[]
}

interface AnalysisResult {
  title: string
  description: string
  sections: TemplateSection[]
  raw_summary: string
}

interface SavedTemplate {
  id: string
  title: string
  created_at: string
}

const result = ref<AnalysisResult | null>(null)
const savedTemplate = ref<SavedTemplate | null>(null)

const fileExt = computed(() => {
  const name = selectedFile.value?.name ?? ''
  return name.includes('.') ? name.split('.').pop()?.toLowerCase() ?? '' : ''
})

const fileIcon = computed(() => {
  switch (fileExt.value) {
    case 'pdf': return 'picture_as_pdf'
    case 'hwp': return 'description'
    case 'docx':
    case 'doc': return 'article'
    default: return 'attach_file'
  }
})

const fileIconColor = computed(() => {
  switch (fileExt.value) {
    case 'pdf': return 'red-7'
    case 'hwp': return 'blue-7'
    case 'docx':
    case 'doc': return 'indigo-7'
    default: return 'grey-7'
  }
})

function onFileSelected(file: File | null) {
  result.value = null
  savedTemplate.value = null
  if (!file) return
}

async function extractPdfText(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const texts: string[] = []

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const content = await page.getTextContent()
    const text = content.items
      .map((item) => ('str' in item ? item.str : ''))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
    if (text) texts.push(text)
  }

  return texts.join('\n')
}

async function extractServerText(file: File): Promise<string> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await api.post('/test/extract-text', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.text as string
}

async function analyzeContent() {
  if (!selectedFile.value) return

  analyzing.value = true
  result.value = null
  savedTemplate.value = null

  try {
    let text = ''
    const ext = selectedFile.value.name.split('.').pop()?.toLowerCase() ?? ''

    if (ext === 'pdf') {
      statusMessage.value = 'PDF 텍스트 추출 중...'
      text = await extractPdfText(selectedFile.value)
    } else {
      statusMessage.value = `${ext.toUpperCase()} 텍스트 추출 중...`
      text = await extractServerText(selectedFile.value)
    }

    if (!text.trim()) {
      $q.notify({ type: 'warning', message: '파일에서 텍스트를 추출할 수 없습니다.' })
      return
    }

    statusMessage.value = 'AI가 내용을 분석하고 폼 틀을 생성하는 중...'
    const res = await api.post('/test/analyze-pdf', {
      text,
      filename: selectedFile.value.name,
    })

    result.value = res.data
    saveTitle.value = (res.data as AnalysisResult).title
    $q.notify({ type: 'positive', message: '폼 틀 생성 완료! DB에 저장할 수 있습니다.' })
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    const detail = error?.response?.data?.detail ?? '분석 중 오류가 발생했습니다.'
    $q.notify({ type: 'negative', message: detail })
  } finally {
    analyzing.value = false
    statusMessage.value = ''
  }
}

function openSaveDialog() {
  saveDialogOpen.value = true
}

async function saveTemplate() {
  if (!result.value || !saveTitle.value) return

  saving.value = true
  saveDialogOpen.value = false
  statusMessage.value = 'DB에 저장 중...'

  try {
    const payload = {
      title: saveTitle.value,
      jira_issue_key: saveIssueKey.value || '',
      sections: result.value.sections.map((s) => ({
        title: s.title,
        fields: s.fields.map((f) => ({
          label: f.label,
          type: f.type,
          required: f.required,
          placeholder: f.placeholder,
          options: f.options,
        })),
      })),
    }

    const res = await api.post('/form-templates', payload)
    savedTemplate.value = {
      id: res.data.id,
      title: res.data.title,
      created_at: res.data.created_at,
    }
    $q.notify({ type: 'positive', message: '폼 틀이 DB에 저장되었습니다.' })
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    const detail = error?.response?.data?.detail ?? '저장 중 오류가 발생했습니다.'
    $q.notify({ type: 'negative', message: detail })
  } finally {
    saving.value = false
    statusMessage.value = ''
  }
}

function fieldColClass(field: TemplateField): string {
  if (field.type === 'textarea') return 'col-12'
  if (field.type === 'checkbox') return 'col-12 col-md-4'
  return 'col-12 col-md-6'
}

function fieldTypeHint(type: string): string {
  switch (type) {
    case 'text': return '텍스트 입력'
    case 'number': return '숫자 입력'
    case 'date': return '날짜 선택'
    case 'textarea': return '장문 입력'
    case 'select': return '항목 선택'
    case 'checkbox': return '체크박스'
    default: return ''
  }
}

async function copyId() {
  if (!savedTemplate.value) return
  try {
    await navigator.clipboard.writeText(savedTemplate.value.id)
    $q.notify({ type: 'positive', message: 'ID가 클립보드에 복사되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '복사에 실패했습니다.' })
  }
}

function resetAll() {
  selectedFile.value = null
  result.value = null
  savedTemplate.value = null
  statusMessage.value = ''
  saveTitle.value = ''
  saveIssueKey.value = ''
}
</script>
