<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]파일테스트2</div>
        <div class="text-caption text-grey-7">PDF 내용 파악 및 폼 틀 자동 생성</div>
      </div>

      <!-- 파일 선택 -->
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center q-col-gutter-md">
              <div class="col-12 col-md-8">
                <q-file
                  v-model="selectedFile"
                  label="PDF 파일 선택"
                  accept=".pdf"
                  outlined
                  clearable
                  @update:model-value="onFileSelected"
                >
                  <template v-slot:prepend>
                    <q-icon name="picture_as_pdf" color="red-7" />
                  </template>
                </q-file>
              </div>
              <div class="col-12 col-md-4">
                <div class="row q-gutter-sm">
                  <q-btn
                    label="내용 분석"
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

      <!-- 분석 결과: 문서 요약 -->
      <div v-if="result" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-deep-purple text-white row items-center">
            <q-icon name="auto_awesome" size="24px" class="q-mr-sm" />
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
        </q-card>
      </div>

      <!-- 생성된 폼 틀 -->
      <div v-if="result && result.sections.length" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-grey-2">
            <div class="row items-center">
              <div class="text-h6 text-weight-bold">자동 생성된 폼 틀</div>
              <q-space />
              <q-chip color="deep-purple" text-color="white" icon="grid_view">
                {{ totalFieldCount }}개 필드
              </q-chip>
            </div>
          </q-card-section>

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
                  <!-- text / number / date -->
                  <q-input
                    v-if="['text', 'number', 'date'].includes(field.type)"
                    :label="field.label + (field.required ? ' *' : '')"
                    :placeholder="field.placeholder"
                    :type="field.type === 'date' ? 'date' : (field.type as 'text' | 'number')"
                    outlined
                    dense
                    :hint="fieldTypeHint(field.type)"
                  />

                  <!-- textarea -->
                  <q-input
                    v-else-if="field.type === 'textarea'"
                    :label="field.label + (field.required ? ' *' : '')"
                    :placeholder="field.placeholder"
                    type="textarea"
                    outlined
                    dense
                    rows="3"
                    :hint="fieldTypeHint(field.type)"
                  />

                  <!-- select -->
                  <q-select
                    v-else-if="field.type === 'select'"
                    :label="field.label + (field.required ? ' *' : '')"
                    :options="field.options"
                    outlined
                    dense
                    :hint="fieldTypeHint(field.type)"
                  />

                  <!-- checkbox -->
                  <q-checkbox
                    v-else-if="field.type === 'checkbox'"
                    :label="field.label"
                    :hint="fieldTypeHint(field.type)"
                  />
                </div>
              </div>

              <q-separator v-if="sIdx < result.sections.length - 1" class="q-mt-lg" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 안내 메시지 (파일 미선택 시) -->
      <div v-if="!selectedFile && !result" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="auto_awesome" size="64px" color="deep-purple-2" class="q-mb-md" />
            <div class="text-h6 text-grey-5">PDF 파일을 선택해주세요</div>
            <div class="text-caption q-mt-sm">
              PDF 파일을 선택한 후 "내용 분석" 버튼을 클릭하면<br />
              AI가 문서 내용을 파악하여 자동으로 폼 틀을 생성합니다.
            </div>
          </q-card-section>
        </q-card>
      </div>

    </div>
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
const statusMessage = ref('')

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

const totalFieldCount = computed(() =>
  result.value?.sections.reduce((sum, s) => sum + s.fields.length, 0) ?? 0
)

function onFileSelected(file: File | null) {
  result.value = null
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

async function analyzeContent() {
  if (!selectedFile.value) return

  analyzing.value = true
  result.value = null

  try {
    statusMessage.value = 'PDF 텍스트 추출 중...'
    const text = await extractPdfText(selectedFile.value)

    if (!text.trim()) {
      $q.notify({ type: 'warning', message: 'PDF에서 텍스트를 추출할 수 없습니다.' })
      return
    }

    statusMessage.value = 'AI가 내용을 분석하고 폼 틀을 생성하는 중...'
    const res = await api.post('/test/analyze-pdf', {
      text,
      filename: selectedFile.value.name,
    })

    result.value = res.data
    $q.notify({ type: 'positive', message: '폼 틀 생성 완료!' })
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

function resetAll() {
  selectedFile.value = null
  result.value = null
  statusMessage.value = ''
}
</script>
