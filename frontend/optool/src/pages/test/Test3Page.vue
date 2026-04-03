<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">

      <!-- 헤더 -->
      <div class="col-12">
        <div class="text-h5">[pilot]파일 테스트(pdf) 1</div>
        <div class="text-caption text-grey-7">PDF 파일 업로드 및 미리보기</div>
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
                    label="미리보기"
                    icon="visibility"
                    color="primary"
                    :disable="!pdfUrl"
                    @click="showPreview = true"
                  />
                  <q-btn
                    label="초기화"
                    icon="refresh"
                    outline
                    color="grey-7"
                    @click="resetFile"
                  />
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 파일 정보 -->
      <div v-if="fileInfo" class="col-12">
        <q-card flat bordered>
          <q-card-section class="bg-primary text-white">
            <div class="text-h6 text-weight-bold">파일 정보</div>
          </q-card-section>
          <q-card-section>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-4">
                <q-card flat bordered class="text-center q-pa-sm">
                  <q-icon name="picture_as_pdf" size="32px" color="red-7" />
                  <div class="text-subtitle2 q-mt-xs text-weight-bold">{{ fileInfo.name }}</div>
                  <div class="text-caption text-grey-6">파일명</div>
                </q-card>
              </div>
              <div class="col-12 col-md-4">
                <q-card flat bordered class="text-center q-pa-sm">
                  <div class="text-h5 text-weight-bold text-info">{{ fileInfo.size }}</div>
                  <div class="text-caption text-grey-6">파일 크기</div>
                </q-card>
              </div>
              <div class="col-12 col-md-4">
                <q-card flat bordered class="text-center q-pa-sm">
                  <div class="text-h5 text-weight-bold text-positive">PDF</div>
                  <div class="text-caption text-grey-6">파일 형식</div>
                </q-card>
              </div>
            </div>
          </q-card-section>

          <!-- PDF 인라인 미리보기 -->
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm text-weight-bold">인라인 미리보기</div>
            <div class="pdf-preview-container" style="border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
              <iframe
                v-if="pdfUrl"
                :src="pdfUrl"
                width="100%"
                height="600px"
                style="border: none; display: block;"
                title="PDF 미리보기"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 안내 메시지 (파일 미선택 시) -->
      <div v-if="!fileInfo" class="col-12">
        <q-card flat bordered>
          <q-card-section class="text-center q-py-xl text-grey-6">
            <q-icon name="picture_as_pdf" size="64px" color="red-2" class="q-mb-md" />
            <div class="text-h6 text-grey-5">PDF 파일을 선택해주세요</div>
            <div class="text-caption q-mt-sm">위의 파일 선택 버튼을 클릭하여 PDF 파일을 업로드하면 미리보기가 표시됩니다.</div>
          </q-card-section>
        </q-card>
      </div>

    </div>

    <!-- 전체화면 미리보기 다이얼로그 -->
    <q-dialog v-model="showPreview" maximized>
      <q-card>
        <q-card-section class="row items-center q-pb-none bg-primary text-white">
          <div class="text-h6">PDF 미리보기 — {{ fileInfo?.name }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section class="q-pa-none" style="height: calc(100vh - 60px);">
          <iframe
            v-if="pdfUrl"
            :src="pdfUrl"
            width="100%"
            height="100%"
            style="border: none; display: block;"
            title="PDF 미리보기 전체화면"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const selectedFile = ref<File | null>(null)
const pdfUrl = ref<string | null>(null)
const showPreview = ref(false)

interface FileInfo {
  name: string
  size: string
}

const fileInfo = computed<FileInfo | null>(() => {
  if (!selectedFile.value) return null
  const bytes = selectedFile.value.size
  const size =
    bytes < 1024
      ? `${bytes} B`
      : bytes < 1024 * 1024
        ? `${(bytes / 1024).toFixed(1)} KB`
        : `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return { name: selectedFile.value.name, size }
})

function onFileSelected(file: File | null) {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = null
  }
  if (file) {
    pdfUrl.value = URL.createObjectURL(file)
  }
}

function resetFile() {
  selectedFile.value = null
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = null
  }
  showPreview.value = false
}
</script>

<style scoped>
@media print {
  .q-btn { display: none; }
  .q-card { box-shadow: none !important; border: 1px solid #ddd !important; }
}
</style>
