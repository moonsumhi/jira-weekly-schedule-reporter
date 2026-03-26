<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]파일 테스트(pdf) 2</div>
        <div class="text-caption text-grey-7">PDF 파일 텍스트 인식</div>
      </div>

      <!-- 파일 업로드 -->
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
                    label="텍스트 추출"
                    icon="text_snippet"
                    color="primary"
                    :disable="!selectedFile || extracting"
                    :loading="extracting"
                    @click="extractText"
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
      <div v-if="extracting" class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">텍스트 추출 중...</div>
            <q-linear-progress
              :value="progress"
              color="primary"
              class="q-mb-xs"
            />
            <div class="text-caption text-grey-6">
              {{ currentPage }} / {{ totalPages }} 페이지 처리 중
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 추출 결과 -->
      <div v-if="extractedPages.length" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-primary text-white row items-center">
            <div class="text-h6 text-weight-bold">추출된 텍스트</div>
            <q-space />
            <div class="text-caption">총 {{ extractedPages.length }}페이지</div>
            <q-btn
              flat
              icon="copy_all"
              label="전체 복사"
              class="q-ml-md"
              @click="copyAllText"
            />
          </q-card-section>

          <q-card-section>
            <div class="row q-col-gutter-sm q-mb-md">
              <div class="col-auto">
                <q-chip color="info" text-color="white" icon="article">
                  {{ totalCharCount.toLocaleString() }}자
                </q-chip>
              </div>
              <div class="col-auto">
                <q-chip color="positive" text-color="white" icon="menu_book">
                  {{ totalPages }}페이지
                </q-chip>
              </div>
            </div>

            <q-list bordered separator>
              <q-expansion-item
                v-for="page in extractedPages"
                :key="page.pageNum"
                :label="`페이지 ${page.pageNum}`"
                :caption="page.text ? `${page.text.length.toLocaleString()}자` : '텍스트 없음'"
                icon="description"
                expand-separator
                default-opened
              >
                <q-card flat>
                  <q-card-section>
                    <div v-if="page.text" class="extracted-text text-body2">{{ page.text }}</div>
                    <div v-else class="text-grey-5 text-center q-py-md">
                      <q-icon name="text_fields" size="24px" class="q-mr-xs" />
                      이 페이지에는 인식 가능한 텍스트가 없습니다.
                    </div>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- 안내 메시지 (파일 미선택 시) -->
      <div v-if="!selectedFile && !extractedPages.length" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="text_snippet" size="64px" color="blue-2" class="q-mb-md" />
            <div class="text-h6 text-grey-5">PDF 파일을 선택해주세요</div>
            <div class="text-caption q-mt-sm">
              PDF 파일을 선택한 후 "텍스트 추출" 버튼을 클릭하면 각 페이지의 텍스트가 추출됩니다.
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

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString()

const $q = useQuasar()

const selectedFile = ref<File | null>(null)
const extracting = ref(false)
const currentPage = ref(0)
const totalPages = ref(0)

interface PageResult {
  pageNum: number
  text: string
}

const extractedPages = ref<PageResult[]>([])

const progress = computed(() =>
  totalPages.value > 0 ? currentPage.value / totalPages.value : 0
)

const totalCharCount = computed(() =>
  extractedPages.value.reduce((sum, p) => sum + p.text.length, 0)
)

function onFileSelected(file: File | null) {
  extractedPages.value = []
  currentPage.value = 0
  totalPages.value = 0
  if (!file) return
}

async function extractText() {
  if (!selectedFile.value) return

  extracting.value = true
  extractedPages.value = []
  currentPage.value = 0

  try {
    const arrayBuffer = await selectedFile.value.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise

    totalPages.value = pdf.numPages
    const results: PageResult[] = []

    for (let i = 1; i <= pdf.numPages; i++) {
      currentPage.value = i
      const page = await pdf.getPage(i)
      const content = await page.getTextContent()
      const text = content.items
        .map((item) => ('str' in item ? item.str : ''))
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim()
      results.push({ pageNum: i, text })
    }

    extractedPages.value = results
    $q.notify({ type: 'positive', message: `텍스트 추출 완료 (${pdf.numPages}페이지)` })
  } catch (err) {
    console.error(err)
    $q.notify({ type: 'negative', message: 'PDF 텍스트 추출 중 오류가 발생했습니다.' })
  } finally {
    extracting.value = false
  }
}

function copyAllText() {
  const all = extractedPages.value
    .map((p) => `[페이지 ${p.pageNum}]\n${p.text}`)
    .join('\n\n')
  void navigator.clipboard.writeText(all).then(() => {
    $q.notify({ type: 'positive', message: '전체 텍스트가 클립보드에 복사되었습니다.' })
  })
}

function resetAll() {
  selectedFile.value = null
  extractedPages.value = []
  currentPage.value = 0
  totalPages.value = 0
}
</script>

<style scoped>
.extracted-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
  line-height: 1.6;
}
</style>
