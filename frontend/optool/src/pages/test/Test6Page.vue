<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]파일테스트3</div>
        <div class="text-caption text-grey-7">파일 분석 후 입력 가능한 폼 자동 생성 및 제출</div>
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
                    label="폼 생성"
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
      <div v-if="analyzing" class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">{{ statusMessage }}</div>
            <q-linear-progress indeterminate color="deep-purple" class="q-mb-xs" />
          </q-card-section>
        </q-card>
      </div>

      <!-- 입력 폼 -->
      <div v-if="result" class="col-12">
        <q-form @submit.prevent="submitForm">
          <q-card flat bordered>
            <q-card-section class="bg-deep-purple text-white row items-center">
              <q-icon name="edit_note" size="24px" class="q-mr-sm" />
              <div class="text-h6 text-weight-bold">{{ result.title }}</div>
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
                    <!-- text / number -->
                    <q-input
                      v-if="['text', 'number'].includes(field.type)"
                      v-model="(formData[fieldKey(sIdx, fIdx)] as string | number | null | undefined)"
                      :label="field.label + (field.required ? ' *' : '')"
                      :placeholder="field.placeholder"
                      :type="(field.type as 'text' | 'number')"
                      :rules="field.required ? [requiredRule] : []"
                      outlined
                      dense
                    />

                    <!-- date -->
                    <q-input
                      v-else-if="field.type === 'date'"
                      v-model="(formData[fieldKey(sIdx, fIdx)] as string | null | undefined)"
                      :label="field.label + (field.required ? ' *' : '')"
                      :rules="field.required ? [requiredRule] : []"
                      outlined
                      dense
                    >
                      <template v-slot:append>
                        <q-icon name="event" class="cursor-pointer">
                          <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <q-date
                              v-model="formData[fieldKey(sIdx, fIdx)]"
                              mask="YYYY-MM-DD"
                            >
                              <div class="row items-center justify-end">
                                <q-btn v-close-popup label="닫기" color="primary" flat />
                              </div>
                            </q-date>
                          </q-popup-proxy>
                        </q-icon>
                      </template>
                    </q-input>

                    <!-- textarea -->
                    <q-input
                      v-else-if="field.type === 'textarea'"
                      v-model="(formData[fieldKey(sIdx, fIdx)] as string | null | undefined)"
                      :label="field.label + (field.required ? ' *' : '')"
                      :placeholder="field.placeholder"
                      :rules="field.required ? [requiredRule] : []"
                      type="textarea"
                      outlined
                      dense
                      rows="3"
                    />

                    <!-- select -->
                    <q-select
                      v-else-if="field.type === 'select'"
                      v-model="formData[fieldKey(sIdx, fIdx)]"
                      :label="field.label + (field.required ? ' *' : '')"
                      :options="field.options"
                      :rules="field.required ? [requiredRule] : []"
                      outlined
                      dense
                    />

                    <!-- checkbox -->
                    <q-checkbox
                      v-else-if="field.type === 'checkbox'"
                      v-model="formData[fieldKey(sIdx, fIdx)]"
                      :label="field.label"
                    />
                  </div>
                </div>

                <q-separator v-if="sIdx < result.sections.length - 1" class="q-mt-lg" />
              </div>
            </q-card-section>

            <q-card-actions align="right" class="q-pa-md">
              <q-btn
                label="초기화"
                icon="clear_all"
                outline
                color="grey-7"
                @click="clearFormData"
              />
              <q-btn
                label="제출"
                icon="send"
                type="submit"
                color="deep-purple"
              />
            </q-card-actions>
          </q-card>
        </q-form>
      </div>

      <!-- 제출 결과 -->
      <div v-if="submittedData" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-green-1 row items-center">
            <q-icon name="check_circle" color="positive" size="24px" class="q-mr-sm" />
            <div class="text-h6 text-weight-bold text-green-9">제출 완료</div>
            <q-space />
            <q-btn
              label="JSON 복사"
              icon="content_copy"
              flat
              dense
              color="green-8"
              @click="copyJson"
            />
          </q-card-section>
          <q-card-section>
            <pre class="q-pa-sm bg-grey-2 rounded-borders text-body2" style="overflow-x: auto; white-space: pre-wrap;">{{ submittedJson }}</pre>
          </q-card-section>
        </q-card>
      </div>

      <!-- 안내 메시지 (파일 미선택 시) -->
      <div v-if="!selectedFile && !result" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="edit_note" size="64px" color="deep-purple-2" class="q-mb-md" />
            <div class="text-h6 text-grey-5">파일을 선택해주세요</div>
            <div class="text-caption q-mt-sm">
              PDF, HWP, DOCX 파일을 선택한 후 "폼 생성" 버튼을 클릭하면<br />
              AI가 문서 내용을 분석하여 입력 가능한 폼을 자동으로 생성합니다.
            </div>
          </q-card-section>
        </q-card>
      </div>

    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
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
const statusMessage = ref('')
const submittedData = ref<Record<string, unknown> | null>(null)

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

const result = ref<AnalysisResult | null>(null)
const formData = reactive<Record<string, string | number | boolean | null | undefined>>({})

function fieldKey(sIdx: number, fIdx: number): string {
  return `s${sIdx}_f${fIdx}`
}

function requiredRule(val: unknown): boolean | string {
  if (val === null || val === undefined || val === '') return '필수 항목입니다.'
  return true
}

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

const submittedJson = computed(() =>
  submittedData.value ? JSON.stringify(submittedData.value, null, 2) : ''
)

function onFileSelected(file: File | null) {
  result.value = null
  submittedData.value = null
  Object.keys(formData).forEach((k) => delete formData[k])
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
  submittedData.value = null
  Object.keys(formData).forEach((k) => delete formData[k])

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

    statusMessage.value = 'AI가 내용을 분석하고 폼을 생성하는 중...'
    const res = await api.post('/test/analyze-pdf', {
      text,
      filename: selectedFile.value.name,
    })

    result.value = res.data

    // 초기값 설정
    const sections = (res.data as AnalysisResult).sections
    sections.forEach((section, sIdx) => {
      section.fields.forEach((field, fIdx) => {
        const key = fieldKey(sIdx, fIdx)
        formData[key] = field.type === 'checkbox' ? false : ''
      })
    })

    $q.notify({ type: 'positive', message: '폼 생성 완료! 내용을 입력해주세요.' })
  } catch (err: unknown) {
    const error = err as { response?: { data?: { detail?: string } } }
    const detail = error?.response?.data?.detail ?? '분석 중 오류가 발생했습니다.'
    $q.notify({ type: 'negative', message: detail })
  } finally {
    analyzing.value = false
    statusMessage.value = ''
  }
}

function fieldColClass(field: TemplateField): string {
  if (field.type === 'textarea') return 'col-12'
  if (field.type === 'checkbox') return 'col-12 col-md-4'
  return 'col-12 col-md-6'
}

function submitForm() {
  if (!result.value) return

  const output: Record<string, unknown> = {
    title: result.value.title,
    filename: selectedFile.value?.name ?? '',
    submittedAt: new Date().toISOString(),
    sections: result.value.sections.map((section, sIdx) => ({
      title: section.title,
      fields: section.fields.map((field, fIdx) => ({
        label: field.label,
        type: field.type,
        value: formData[fieldKey(sIdx, fIdx)] ?? '',
      })),
    })),
  }

  submittedData.value = output
  $q.notify({ type: 'positive', message: '폼이 제출되었습니다.' })
}

function clearFormData() {
  if (!result.value) return
  result.value.sections.forEach((section, sIdx) => {
    section.fields.forEach((field, fIdx) => {
      formData[fieldKey(sIdx, fIdx)] = field.type === 'checkbox' ? false : ''
    })
  })
  submittedData.value = null
}

async function copyJson() {
  try {
    await navigator.clipboard.writeText(submittedJson.value)
    $q.notify({ type: 'positive', message: 'JSON이 클립보드에 복사되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '복사에 실패했습니다.' })
  }
}

function resetAll() {
  selectedFile.value = null
  result.value = null
  submittedData.value = null
  statusMessage.value = ''
  Object.keys(formData).forEach((k) => delete formData[k])
}
</script>
