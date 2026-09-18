<template>
  <q-page class="q-pa-md">
    <q-tabs v-if="isJobPage" :model-value="activeJobTab" dense no-caps align="left"
      active-color="primary" indicator-color="primary" class="job-category-tabs q-mb-md"
      @update:model-value="selectJobTab">
      <q-tab name="all" label="전체" />
      <q-tab v-for="item in jobTemplates" :key="item.id" :name="item.id" :label="item.title" />
    </q-tabs>
    <q-inner-loading :showing="loading" />

    <!-- 파일 선택창이 열려있는 동안 DOM에서 제거되면 브라우저가 창을 강제로 닫으므로,
         v-if 블록 밖에 항상 마운트된 상태로 둔다 -->
    <input ref="fileInput" type="file" :accept="isJobPage ? '.hwp,.hwpx,.doc,.docx' : '.hwp'" style="display:none" @change="handleFileImport" />

    <template v-if="!loading && (isAllJobs || template)">
      <!-- Header -->
      <div class="row items-center q-gutter-sm q-mb-md">
        <div>
          <div class="text-h6">{{ isAllJobs ? '전체 작업 관리' : template?.title }}</div>
          <div class="text-caption text-grey">{{ isAllJobs ? `전체 문서 ${rows.length}건` : template?.jiraIssueKey }}</div>
        </div>
        <q-space />
        <q-toggle v-model="includeDeleted" label="삭제 포함" dense @update:model-value="load" />
        <q-btn outline icon="refresh" label="새로고침" :loading="tableLoading" @click="load" />
        <q-btn outline icon="upload_file" label="Import" :loading="importing"
          :disable="isAllJobs && !jobTemplates.length" @click="startDocumentAction('import')" />
        <q-btn color="primary" icon="add" :label="isAllJobs ? '파일 추가' : `${template?.title} 추가`"
          :disable="importing || (isAllJobs && !jobTemplates.length)" @click="startDocumentAction('create')" />
      </div>

      <!-- Search bar -->
      <div class="row q-gutter-sm items-center q-mb-md">
        <q-select
          v-model="searchType"
          :options="searchTypeOptions"
          emit-value map-options
          dense outlined
          style="min-width: 120px"
        />
        <q-input
          v-if="searchType === 'content' || searchType === 'created_by'"
          v-model="searchValue"
          dense outlined clearable
          :placeholder="searchType === 'content' ? '내용 검색' : '제출자 검색'"
          style="min-width: 220px; width: 500px"
          @keyup.enter="void 0"
        />
        <template v-else-if="searchType === 'work_date'">
          <q-input v-model="searchDateFrom" type="date" dense outlined clearable label="시작" style="min-width: 160px" />
          <span class="text-grey">~</span>
          <q-input v-model="searchDateTo" type="date" dense outlined clearable label="종료" style="min-width: 160px" />
        </template>
        <q-btn flat icon="close" dense @click="resetSearch" v-if="hasSearch" />
      </div>

      <q-card bordered>
        <q-card-section class="q-pa-none">
          <q-table
            :rows="filteredRows"
            :columns="columns"
            row-key="id"
            :loading="tableLoading"
            :pagination="{ rowsPerPage: 10 }"
            flat
            bordered
          >
            <template #body-cell-preview="props">
              <q-td :props="props">
                <span class="text-grey-7 text-caption ellipsis" style="max-width: 300px; display: block;">
                  {{ entryPreview(props.row) }}
                </span>
              </q-td>
            </template>

            <template #body-cell-created_at="props">
              <q-td :props="props">{{ getWorkDate(props.row) }}</q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props">
                <div class="row items-center justify-end q-gutter-xs">
                  <q-btn dense outline icon="visibility" label="상세" @click="void openDetail(props.row)" />
                  <q-btn
                    dense color="negative" icon="delete" label="삭제"
                    :disable="props.row.isDeleted"
                    :loading="actingId === props.row.id"
                    @click="confirmDelete(props.row)"
                  />
                </div>
              </q-td>
            </template>

            <template #no-data>
              <div class="full-width row flex-center q-pa-lg text-grey-6">
                데이터가 없습니다.
              </div>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </template>

    <WorkDocumentEditor
      :model-value="formDialog" :title="template?.title ?? ''" :sections="sections"
      :is-edit="false" :saving="editorBusy" :dirty="isFormDirty"
      :sync-markdown="isJobPage && !documentMode"
      @update:model-value="onFormDialogModelUpdate"
      :show-markdown-edit="false"
      @hide="importedImages = []; importedImageGroups = []; placedImportedIndices = new Set(); selectedPanelImage = ''; activePasteCell = null; importedOriginalFile = null; markdownSourceData = null"
      @save="doCreate"
    >
      <template #assets><WorkDocumentAssets v-if="canLinkWorkDocument" v-model="formAssets" editing :disable="editorBusy" /></template>
      <template #section="{ section }">
        <div class="edit-section-rows">
          <div v-for="(row, rowIdx) in getRows(section.title)" :key="rowIdx" class="edit-row-card">
            <div v-if="section.multiple && !documentMode" class="edit-row-heading">
              <span class="edit-row-number">{{ String(rowIdx + 1).padStart(2, '0') }}</span>
              <span>{{ section.title }} {{ rowIdx + 1 }}</span>
              <q-space />
              <q-btn flat dense round icon="delete_outline" color="grey-6" :aria-label="`${section.title} ${rowIdx + 1} 삭제`"
                :disable="saving || getRows(section.title).length <= 1" @click="removeRow(section.title, rowIdx)" />
            </div>
            <div class="edit-field-groups">
              <div v-for="group in workResultFieldGroups(section)" :key="group.label" :class="['edit-field-group', { 'comparison-side': group.label, 'whole-document': documentMode }]">
                <div v-if="group.label" class="comparison-heading">{{ group.label }}</div>
                <div v-if="group.label" class="comparison-editor" :inert="saving ? true : undefined">
                  <MarkdownEditor :model-value="getRowVal(section.title, rowIdx, group.label)" :rows="8"
                    placeholder="내용을 입력하고 사진을 넣은 뒤, 이어서 내용을 작성하세요."
                    @uploading="imageUploads[`${section.title}:${rowIdx}:${group.label}`] = $event"
                    @update:model-value="setRowVal(section.title, rowIdx, group.label, $event)" />
                  <q-btn v-if="selectedPanelImage" flat dense color="primary" icon="add_photo_alternate" label="선택한 Import 이미지 넣기"
                    :disable="saving" @click="appendComparisonImage(section.title, rowIdx, group.label)" />
                </div>
                <div v-else class="edit-fields">
              <div v-for="field in group.fields" :key="field.label" :class="['edit-field', { wide: editorFieldWide(field) }]">
                <div class="edit-field-label">{{ field.label }}<span v-if="field.required" class="text-negative q-ml-xs">*</span></div>
                <template v-if="field.type === 'image'">
                          <div
                            class="image-drop-zone"
                            :class="{
                              'has-image': getRowImages(section.title, rowIdx, field.label).length > 0,
                              'drag-over': dragOverCell === `${section.title}__${rowIdx}__${field.label}`,
                              'paste-ready': activePasteCell?.sectionTitle === section.title && activePasteCell?.rowIdx === rowIdx && activePasteCell?.fieldLabel === field.label
                            }"
                            @dragover.prevent="dragOverCell = `${section.title}__${rowIdx}__${field.label}`"
                            @dragleave="dragOverCell = ''"
                            @drop.prevent.stop="onDropImage(section.title, rowIdx, field.label, $event)"
                            @paste.stop="onPasteImage(section.title, rowIdx, field.label, $event)"
                          >
                            <div v-if="getRowImages(section.title, rowIdx, field.label).length > 0" style="display:flex;flex-wrap:wrap;gap:4px;padding:4px;">
                              <div
                                v-for="(imgSrc, imgIdx) in getRowImages(section.title, rowIdx, field.label)"
                                :key="imgIdx"
                                style="position:relative;display:inline-block;"
                              >
                                <img
                                  :src="imgSrc"
                                  draggable="true"
                                  style="width:72px;height:56px;object-fit:cover;cursor:grab;border:1px solid #ccc;border-radius:2px;"
                                  @click.stop="previewImage(imgSrc)"
                                  @dragstart="onCellImageDragStart(section.title, rowIdx, field.label, imgIdx, $event)"
                                />
                                <q-btn
                                  flat dense round icon="close" size="xs"
                                  style="position:absolute;top:0;right:0;background:rgba(0,0,0,0.45);color:white;padding:0;min-width:16px;min-height:16px;"
                                  @click.stop="removeRowImage(section.title, rowIdx, field.label, imgIdx)"
                                />
                              </div>
                            </div>
                            <div
                              style="display:flex;align-items:center;justify-content:center;min-height:36px;cursor:pointer;padding:2px;"
                              @click.stop="onImageCellClick(section.title, rowIdx, field.label)"
                              @dragover.prevent="dragOverCell = `${section.title}__${rowIdx}__${field.label}`"
                              @drop.prevent.stop="onDropImage(section.title, rowIdx, field.label, $event)"
                            >
                              <div class="drop-hint">{{ selectedPanelImage ? '클릭하여 추가' : (getRowImages(section.title, rowIdx, field.label).length > 0 ? '+ 추가' : (visibleImportedImages.length > 0 ? '이미지를 맞게 넣어주세요' : '이미지 선택 후 클릭 또는 드래그')) }}</div>
                            </div>
                          </div>
                        </template>

                <MarkdownEditor v-else-if="row[`${field.label}__format`] === 'markdown'" :model-value="getRowVal(section.title, rowIdx, field.label)"
                  @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)"
                  @uploading="imageUploads[`${section.title}:${rowIdx}:${field.label}`] = $event" />
                <q-select v-else-if="field.type === 'select'" :model-value="getRowVal(section.title, rowIdx, field.label)"
                  @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)" :options="field.options ?? []"
                  outlined dense :aria-label="field.label" :disable="saving" />
                <q-toggle v-else-if="field.type === 'boolean'" :model-value="getRowVal(section.title, rowIdx, field.label) === 'true'"
                  @update:model-value="setRowVal(section.title, rowIdx, field.label, String($event))" :label="field.label" :disable="saving" />
                <q-input v-else :model-value="getRowVal(section.title, rowIdx, field.label)"
                  @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)" :type="tableInputType(field.type)"
                  :placeholder="field.placeholder" :aria-label="field.label" :aria-required="!!field.required"
                  outlined dense autogrow :disable="saving" />
              </div>
            </div>
          </div>
              </div>
            </div>
          <q-btn v-if="section.multiple && !documentMode" outline no-caps icon="add" :label="`${section.title} 항목 추가`"
            color="primary" class="edit-add-row" :disable="saving" @click="addRow(section)" />
        </div>
      </template>
              <template #images v-if="visibleImportedImages.length > 0">
          <q-separator />
          <q-card-section class="image-panel q-py-sm">
            <div class="row items-center q-mb-xs">
              <span class="text-subtitle2">
                추출된 이미지 ({{ visibleImportedImages.length }}장) — 직접 배치해주세요
                <span v-if="selectedPanelImage" class="text-positive q-ml-sm">— 이미지 선택됨. 배치할 셀을 클릭하세요</span>
                <span v-else class="text-grey q-ml-sm">— 이미지를 클릭해 선택 후 배치할 셀을 클릭하거나, 칸으로 직접 드래그하세요</span>
              </span>
              <q-space />
              <q-btn flat dense icon="close" size="sm" @click="importedImages = []; importedImageGroups = []; placedImportedIndices = new Set(); selectedPanelImage = ''" />
            </div>

            <!-- HWP: 문서에서 감지된 캡션별로 그룹 표시. 이미 칸에 배치된 이미지는 여기서 빠진다 -->
            <template v-if="importedImageGroupsWithOffset.length > 0">
              <div
                v-for="(group, gIdx) in importedImageGroupsWithOffset"
                :key="gIdx"
                class="q-mb-sm"
              >
                <div class="text-caption text-grey-7 q-mb-xs">
                  {{ group.caption || '(원본 문서에서 캡션을 찾지 못함)' }}
                </div>
                <div class="image-panel-scroll row q-gutter-sm">
                  <div
                    v-for="item in group.images"
                    :key="item.idx"
                    class="image-thumb"
                    :class="{ 'image-thumb--selected': selectedPanelImage === item.img }"
                    draggable="true"
                    @click="selectedPanelImage = selectedPanelImage === item.img ? '' : item.img"
                    @dragstart="selectedPanelImage = item.img; $event.dataTransfer?.setData('text/plain', String(item.idx))"
                    @dragend="dragOverCell = ''"
                  >
                    <img :src="item.img" draggable="false" style="width: 72px; height: 56px; object-fit: cover; cursor: grab; pointer-events: none;" />
                    <div class="text-caption text-center">{{ item.idx + 1 }}</div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 캡션 그룹 정보가 없는 가져온 사진은 기존처럼 flat하게 표시한다. 이미 칸에 배치된 이미지는 빠진다. -->
            <div v-else class="image-panel-scroll row q-gutter-sm">
              <div
                v-for="item in visibleImportedImages"
                :key="item.idx"
                class="image-thumb"
                :class="{ 'image-thumb--selected': selectedPanelImage === item.img }"
                draggable="true"
                @click="selectedPanelImage = selectedPanelImage === item.img ? '' : item.img"
                @dragstart="selectedPanelImage = item.img; $event.dataTransfer?.setData('text/plain', String(item.idx))"
                @dragend="dragOverCell = ''"
              >
                <img :src="item.img" draggable="false" style="width: 72px; height: 56px; object-fit: cover; cursor: grab; pointer-events: none;" />
                <div class="text-caption text-center">{{ item.idx + 1 }}</div>
              </div>
            </div>
          </q-card-section>
        </template>

    </WorkDocumentEditor>
    <!-- Import Skipped Dialog -->
    <q-dialog v-model="skippedDialog">
      <q-card style="width: 640px; max-width: 96vw; max-height: 80vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <q-icon name="warning" color="warning" size="sm" class="q-mr-sm" />
          <div class="text-h6">건너뜀 항목 ({{ skippedItems.length }}건)</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="col scroll text-caption text-grey-7 q-pb-xs">
          Import 완료. 아래 항목은 내용이 없어 건너뛰었습니다. 내용을 확인 후 저장하세요.
        </q-card-section>
        <q-card-section class="col scroll" style="min-height: 0;">
          <q-list separator>
            <q-item v-for="(item, idx) in skippedItems" :key="idx" dense>
              <q-item-section>
                <q-item-label>
                  <span class="text-weight-medium">{{ item.section }}</span>
                  <span class="text-grey-6 q-ml-xs">{{ item.row }}번째 행</span>
                </q-item-label>
                <q-item-label caption>{{ item.reason }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="닫기" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Extracted Image Panel (shown inside form dialog area, below form) -->
    <!-- Rendered as a floating panel attached to the page, visible when formDialog is open -->

    <!-- Image Preview Dialog -->
    <q-dialog v-model="imagePreviewOpen">
      <q-card flat style="width: auto; max-width: 90vw; max-height: 90vh; overflow: hidden;">
        <img :src="imagePreviewSrc" style="display: block; max-width: 90vw; max-height: 90vh; width: auto; height: auto;" />
      </q-card>
    </q-dialog>

    <q-dialog v-model="documentTypeDialog">
      <q-card style="width: 400px; max-width: 92vw">
        <q-card-section>
          <div class="text-h6">문서 종류 선택</div>
          <div class="text-caption text-grey q-mt-xs">{{ pendingDocumentAction === 'import' ? '가져올 파일의 문서 종류를 선택해 주세요.' : '추가할 문서 종류를 선택해 주세요.' }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select v-model="selectedDocumentType" :options="jobTemplates" option-value="id" option-label="title"
            emit-value map-options outlined dense label="문서 종류" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" :label="pendingDocumentAction === 'import' ? '파일 선택' : '작성하기'"
            :disable="!selectedDocumentType" @click="confirmDocumentType" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <WorkDocumentDetail
      v-model="detailDialog"
      :loading="detailLoading"
      :entry="detailRow"
      :title="template?.title ?? ''"
      :sections="sections"
      :creating="creatingDetail"
      :saving="detailSaving" :save-warning="detailSaveWarning"
      :link-assets="canLinkWorkDocument"
      :inspection-links="canLinkWorkDocument && isWorkPlanTemplate(template)"
      @update:model-value="onDetailDialogUpdate"
      @save="saveDetailForm"
      @export="exportDetailMarkdown"
      @export-file="exportDetailFile"
      @download-original="downloadOriginalFile"
      :exporting="exportingDocument"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, toRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { isAxiosError } from 'axios'
import { prepareWorkDocumentData, resultImageUrl, useWorkDocumentExport } from 'src/composables/useWorkDocument'
import { isWorkPlanTemplate } from 'src/services/inspectionWorkPlans'
import { saveWorkDocument, WorkDocumentInspectionError, type WorkDocumentInspection } from 'src/services/workDocumentInspection'
import { hasOriginalForm, synchronizedDocument } from 'src/utils/formEntryMarkdown'
import WorkDocumentDetail from 'src/components/WorkDocumentDetail.vue'
import WorkDocumentEditor from 'src/components/WorkDocumentEditor.vue'
import WorkDocumentAssets from 'src/components/WorkDocumentAssets.vue'
import { useAuthStore } from 'src/stores/auth'
import { comparisonFormatKey, comparisonMarkdown, workResultFieldGroups } from 'src/utils/workResultFields'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import { api } from 'src/boot/axios'
import { formTemplateService, type FormTemplate, type FormField, type FormSection } from 'src/services/formTemplates'
import { formEntryService, type FormEntry, type ImportSkipped, type ImportImageGroup, type OriginalFile, type WorkDocumentAsset } from 'src/services/formEntries'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()

const loading = ref(true)
const tableLoading = ref(false)
const saving = ref(false)
const detailSaveWarning = ref('')
const imageUploads = ref<Record<string, boolean>>({})
const insertingImages = ref(0)
const editorBusy = computed(() => saving.value || insertingImages.value > 0 || Object.values(imageUploads.value).some(Boolean))
const includeDeleted = ref(false)

const template = ref<FormTemplate | null>(null)
const rows = ref<FormEntry[]>([])
const jobTemplates = ref<FormTemplate[]>([])
const documentTypeDialog = ref(false)
const selectedDocumentType = ref<string | null>(null)
const pendingDocumentAction = ref<'create' | 'import'>('create')
const isJobPage = computed(() => route.path.startsWith('/job/'))
const canLinkWorkDocument = computed(() => isJobPage.value && template.value?.menu?.toLowerCase() === 'job'
  && !!(auth.me?.isAdmin || auth.me?.permissions?.includes('job')))
const isAllJobs = computed(() => isJobPage.value && !route.params['id'])
const activeJobTab = computed(() => isAllJobs.value ? 'all'
  : jobTemplates.value.find((item) => item.id === route.params['id'] || item.jiraIssueKey === route.params['id'])?.id ?? '')

function selectJobTab(value: string | number) {
  const destination = value === 'all' ? '/job/forms' : `/job/forms/${value}`
  if (route.path !== destination) void router.push(destination)
}

function entryTemplate(row: FormEntry): FormTemplate | null {
  return jobTemplates.value.find((item) => item.id === row.templateId)
    ?? (template.value?.id === row.templateId ? template.value : null)
}

// search
const searchType = ref<'content' | 'created_by' | 'work_date'>('content')
const searchValue = ref('')
const searchDateFrom = ref('')
const searchDateTo = ref('')

const searchTypeOptions = [
  { label: '내용', value: 'content' },
  { label: '제출자', value: 'created_by' },
  { label: '작업 일시', value: 'work_date' },
]

const hasSearch = computed(() => {
  if (searchType.value === 'content' || searchType.value === 'created_by') return !!searchValue.value
  if (searchType.value === 'work_date') return !!(searchDateFrom.value || searchDateTo.value)
  return false
})

function resetSearch() {
  searchValue.value = ''
  searchDateFrom.value = ''
  searchDateTo.value = ''
}

const filteredRows = computed(() => {
  return rows.value.filter((row) => {
    if (searchType.value === 'content' && searchValue.value) {
      if (!JSON.stringify(row.data).toLowerCase().includes(searchValue.value.toLowerCase())) return false
    }
    if (searchType.value === 'created_by' && searchValue.value) {
      if (!(row.createdBy ?? '').toLowerCase().includes(searchValue.value.toLowerCase())) return false
    }
    if (searchType.value === 'work_date' && (searchDateFrom.value || searchDateTo.value)) {
      const workDate = getWorkDate(row)
      if (workDate === '-') return false
      if (searchDateFrom.value && workDate < searchDateFrom.value) return false
      if (searchDateTo.value && workDate > searchDateTo.value) return false
    }
    return true
  })
})

// import
const importing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const skippedDialog = ref(false)
const skippedItems = ref<ImportSkipped[]>([])
const importedImages = ref<string[]>([])
const importedOriginalFile = ref<OriginalFile | null>(null)
// 캡션을 추출할 수 없는 문서는 그룹 없이 flat하게 표시한다.
// importedImages와 순서가 정확히 일치해야(그룹 펼친 게 flat 리스트) 아래 오프셋 계산이 맞는다.
const importedImageGroups = ref<ImportImageGroup[]>([])
// 이미 칸에 배치된 importedImages 원본 인덱스 — 패널에서는 숨기고, 칸에서 빼면 다시 보이게 함
const placedImportedIndices = ref<Set<number>>(new Set())

function markImportedIndex(idx: number): void {
  if (idx >= 0) placedImportedIndices.value.add(idx)
}

// 칸에서 이미지를 제거했을 때, 그게 추출된 이미지 패널에서 온 것이면 패널에 다시 보이게 한다
function unmarkImportedImage(src: string): void {
  const idx = importedImages.value.indexOf(src)
  if (idx !== -1) placedImportedIndices.value.delete(idx)
}
const dragOverCell = ref('')
const imagePreviewSrc = ref('')
const imagePreviewOpen = ref(false)

// 캡션 그룹 각각에 importedImages(flat) 안에서의 인덱스를 붙이고, 이미 칸에
// 배치된 이미지는 패널에서 숨긴다(드래그/클릭 배치는 이 flat 인덱스 기반으로 동작).
const importedImageGroupsWithOffset = computed(() => {
  let offset = 0
  return importedImageGroups.value
    .map((g) => {
      const images = g.images
        .map((img, i) => ({ img, idx: offset + i }))
        .filter((x) => !placedImportedIndices.value.has(x.idx))
      offset += g.images.length
      return { caption: g.caption, images }
    })
    .filter((g) => g.images.length > 0)
})

// 캡션 그룹 정보가 없는 경우의 flat 패널 목록 — 이미 배치된 이미지는 숨긴다.
const visibleImportedImages = computed(() =>
  importedImages.value
    .map((img, idx) => ({ img, idx }))
    .filter((x) => !placedImportedIndices.value.has(x.idx))
)

const activePasteCell = ref<{ sectionTitle: string; rowIdx: number; fieldLabel: string } | null>(null)
const selectedPanelImage = ref<string>('')  // 패널에서 선택된 이미지 src

// dialogs
const formDialog = ref(false)
const detailDialog = ref(false)
const detailLoading = ref(false)
const detailSaving = ref(false)
const creatingDetail = ref(false)
const detailRow = ref<FormEntry | null>(null)
const actingId = ref<string | null>(null)

type RowData = Record<string, string | string[]>
type SectionValue = RowData | RowData[]
const formValues = ref<Record<string, SectionValue>>({})
const formAssets = ref<WorkDocumentAsset[]>([])
watch(formDialog, open => { if (open) formAssets.value = [] })

// `structuredClone` cannot clone Vue reactive proxies. Form data is edited
// through reactive objects, so unwrap proxies recursively before keeping a
// snapshot or sending Markdown edits back to the API.
function cloneFormData<T>(value: T): T {
  if (value === null || typeof value !== 'object') return value
  const raw = toRaw(value as object)
  if (raw instanceof Date) return new Date(raw.getTime()) as T
  if (Array.isArray(raw)) return raw.map((item) => cloneFormData(item)) as T
  const result: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(raw as Record<string, unknown>)) {
    result[key] = cloneFormData(item)
  }
  return result as T
}

// 다이얼로그를 열 때(생성/수정 진입 시)의 스냅샷과 비교해 변경 여부를 판단.
// 변경이 없으면 ESC/바깥 클릭 시 바로 닫고, 변경이 있으면 확인을 받는다.
const formValuesSnapshot = ref('')
const isFormDirty = computed(() => formAssets.value.length > 0 || JSON.stringify(formValues.value) !== formValuesSnapshot.value)

function onFormDialogModelUpdate(val: boolean): void {
  if (editorBusy.value) return
  if (val) {
    formDialog.value = true
    return
  }
  if (!isFormDirty.value) {
    formDialog.value = false
    return
  }
  $q.dialog({
    title: '저장하지 않은 변경사항이 있습니다',
    message: '저장하지 않고 닫으시겠습니까?',
    cancel: { label: '취소', flat: true },
    ok: { label: '닫기', color: 'negative' },
  }).onOk(() => { formDialog.value = false })
}

const documentMode = ref(false)
const markdownEditMode = ref(false)
// Markdown 편집으로 전환할 때 원본 필드 데이터도 함께 보존해 원본 양식과
// Markdown 버전을 모두 유지한다.
const markdownSourceData = ref<Record<string, SectionValue> | null>(null)
const documentSections: FormSection[] = [{ title: '문서 본문', multiple: true, fields: [
  { label: '제목', type: 'text', required: true, fullWidth: true },
  { label: '내용', type: 'textarea', required: true, fullWidth: true },
] }]
function originalSections(data: Record<string, unknown>): FormSection[] {
  const base = template.value?.sections ?? []
  return data['가져온 추가 내용'] ? [...base, { title: '가져온 추가 내용', multiple: true, fields: [{ label: '내용', type: 'textarea', fullWidth: true }] }] : base
}
const sections = computed<FormSection[]>(() => documentMode.value ? documentSections : originalSections(formDialog.value ? formValues.value : detailRow.value?.data ?? {}))

const columns = computed(() => [
  ...(isAllJobs.value ? [{ name: 'document_type', label: '문서 종류', field: (row: FormEntry) => entryTemplate(row)?.title ?? '—', align: 'left' as const, sortable: true }] : []),
  { name: 'preview', label: '내용 미리보기', field: 'id', align: 'left' as const },
  { name: 'created_by', label: '제출자', field: 'createdBy', align: 'left' as const },
  { name: 'created_at', label: '작업 일시', field: 'createdAt', align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
])

function getWorkDate(row: FormEntry): string {
  for (const sectionData of Object.values(row.data)) {
    const values = Array.isArray(sectionData) ? sectionData[0] : sectionData
    const d = values?.['작업 일시'] ?? values?.['작업 기간 (시작)']
    if (d) return String(d).slice(0, 10)
  }
  return '-'
}

function entryPreview(row: FormEntry): string {
  const document = row.data['문서 본문']
  if (Array.isArray(document) && document[0] && !hasOriginalForm(entryTemplate(row)?.sections ?? [], row.data)) return String(document[0]['제목'] ?? '')
  const firstSection = entryTemplate(row)?.sections[0]
  if (!firstSection) return ''
  const sectionData = row.data[firstSection.title]
  if (!sectionData) return ''
  if (firstSection.multiple) {
    if (Array.isArray(sectionData) && sectionData.length > 0) {
      return Object.values(sectionData[0] as Record<string, string>).filter(Boolean).slice(0, 3).join(' / ')
    }
    return ''
  }
  return Object.values(sectionData as Record<string, string>).filter(Boolean).slice(0, 3).join(' / ')
}

// ── Single section helpers ──────────────────────────────────────────────────

function getVal(sectionTitle: string, fieldLabel: string): string {
  const sec = formValues.value[sectionTitle]
  if (!sec || Array.isArray(sec)) return ''
  const v = sec[fieldLabel]
  return Array.isArray(v) ? '' : (v ?? '')
}

function getRows(sectionTitle: string): RowData[] {
  const val = formValues.value[sectionTitle]
  if (Array.isArray(val)) return val
  return val ? [val] : []
}

function getRowVal(sectionTitle: string, rowIdx: number, fieldLabel: string): string {
  const r = getRows(sectionTitle)
  const v = r[rowIdx]?.[fieldLabel]
  if (Array.isArray(v)) return ''
  return v ?? ''
}

function getRowImages(sectionTitle: string, rowIdx: number, fieldLabel: string): string[] {
  return toImageArray(getRows(sectionTitle)[rowIdx]?.[fieldLabel])
}

function setRowVal(sectionTitle: string, rowIdx: number, fieldLabel: string, val: string | number | null): void {
  const rowsArr = getRows(sectionTitle)
  if (!rowsArr[rowIdx]) rowsArr[rowIdx] = {}
  rowsArr[rowIdx][fieldLabel] = val == null ? '' : String(val)
  if ((sectionTitle === '작업 결과' && ['작업 전', '작업 후'].includes(fieldLabel)) || (sectionTitle === '문서 본문' && fieldLabel === '내용')) {
    rowsArr[rowIdx][comparisonFormatKey(fieldLabel)] = 'markdown'
  }
}

function addRowImage(sectionTitle: string, rowIdx: number, fieldLabel: string, src: string): void {
  const rowsArr = getRows(sectionTitle)
  if (!rowsArr[rowIdx]) rowsArr[rowIdx] = {}
  const current = rowsArr[rowIdx][fieldLabel]
  const arr: string[] = Array.isArray(current) ? [...current] : (current ? [current] : [])
  arr.push(src)
  rowsArr[rowIdx][fieldLabel] = arr
}

function removeRowImage(sectionTitle: string, rowIdx: number, fieldLabel: string, imgIdx: number): void {
  const rowsArr = getRows(sectionTitle)
  if (!rowsArr[rowIdx]) return
  const current = rowsArr[rowIdx][fieldLabel]
  const arr: string[] = Array.isArray(current) ? [...current] : (current ? [current] : [])
  const [removed] = arr.splice(imgIdx, 1)
  rowsArr[rowIdx][fieldLabel] = arr
  if (removed) unmarkImportedImage(removed)
}

function emptyRow(section: FormSection): RowData {
  return Object.fromEntries(section.fields.map((f) => [f.label, '']))
}

function addRow(section: FormSection): void {
  const val = formValues.value[section.title]
  if (Array.isArray(val)) {
    val.push(emptyRow(section))
  } else {
    formValues.value[section.title] = [emptyRow(section)]
  }
}

function removeRow(sectionTitle: string, rowIdx: number): void {
  const rowsArr = getRows(sectionTitle)
  if (rowsArr.length > 1) rowsArr.splice(rowIdx, 1)
}

// ── Image drag & drop helpers ───────────────────────────────────────────────


interface CellImageDragPayload {
  source: 'cell'
  sectionTitle: string
  rowIdx: number
  fieldLabel: string
  imgIdx: number
}

function onCellImageDragStart(sectionTitle: string, rowIdx: number, fieldLabel: string, imgIdx: number, e: DragEvent) {
  const payload: CellImageDragPayload = { source: 'cell', sectionTitle, rowIdx, fieldLabel, imgIdx }
  e.dataTransfer?.setData('text/plain', JSON.stringify(payload))
  selectedPanelImage.value = ''
}

function onDropImage(sectionTitle: string, rowIdx: number, fieldLabel: string, e: DragEvent) {
  dragOverCell.value = ''
  const raw = e.dataTransfer?.getData('text/plain') ?? ''

  // 셀 → 셀 이동 (다른 칸에 이미 배치된 이미지를 드래그해온 경우)
  if (raw.startsWith('{')) {
    try {
      const payload = JSON.parse(raw) as Partial<CellImageDragPayload>
      if (payload.source === 'cell' && payload.sectionTitle && payload.fieldLabel && payload.rowIdx !== undefined && payload.imgIdx !== undefined) {
        const isSameCell = payload.sectionTitle === sectionTitle && payload.rowIdx === rowIdx && payload.fieldLabel === fieldLabel
        if (!isSameCell) {
          const src = getRowImages(payload.sectionTitle, payload.rowIdx, payload.fieldLabel)[payload.imgIdx]
          if (src) {
            removeRowImage(payload.sectionTitle, payload.rowIdx, payload.fieldLabel, payload.imgIdx)
            addRowImage(sectionTitle, rowIdx, fieldLabel, src)
            // 칸→칸 이동일 뿐 패널로 돌아간 게 아니므로, removeRowImage가 풀어준 표시를 다시 건다
            markImportedIndex(importedImages.value.indexOf(src))
          }
        }
        return
      }
    } catch {
      // JSON 파싱 실패 시 패널 드래그(숫자 인덱스)로 폴백
    }
  }

  // 패널 → 셀 배치(기존 동작)
  const idx = raw !== '' ? Number(raw) : -1
  const src = (idx >= 0 && importedImages.value[idx]) ? importedImages.value[idx] : selectedPanelImage.value
  if (src) {
    addRowImage(sectionTitle, rowIdx, fieldLabel, src)
    markImportedIndex(idx >= 0 ? idx : importedImages.value.indexOf(src))
    selectedPanelImage.value = ''
  }
}

function pasteImageFromClipboard(sectionTitle: string, rowIdx: number, fieldLabel: string, e: ClipboardEvent) {
  const readFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      const src = ev.target?.result as string
      if (src) addRowImage(sectionTitle, rowIdx, fieldLabel, src)
    }
    reader.readAsDataURL(file)
  }

  const items = e.clipboardData?.items
  if (items) {
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (file) { e.preventDefault(); readFile(file); return }
      }
    }
  }

  const files = e.clipboardData?.files
  if (files) {
    for (const file of Array.from(files)) {
      if (file.type.startsWith('image/')) {
        e.preventDefault(); readFile(file); return
      }
    }
  }
}

function onPasteImage(sectionTitle: string, rowIdx: number, fieldLabel: string, e: ClipboardEvent) {
  pasteImageFromClipboard(sectionTitle, rowIdx, fieldLabel, e)
}

function setActivePasteCell(sectionTitle: string, rowIdx: number, fieldLabel: string) {
  activePasteCell.value = { sectionTitle, rowIdx, fieldLabel }
}

function onImageCellClick(sectionTitle: string, rowIdx: number, fieldLabel: string) {
  if (selectedPanelImage.value) {
    addRowImage(sectionTitle, rowIdx, fieldLabel, selectedPanelImage.value)
    markImportedIndex(importedImages.value.indexOf(selectedPanelImage.value))
    selectedPanelImage.value = ''
  } else {
    setActivePasteCell(sectionTitle, rowIdx, fieldLabel)
  }
}

function handleGlobalPaste(e: ClipboardEvent) {
  if (!activePasteCell.value) return
  const { sectionTitle, rowIdx, fieldLabel } = activePasteCell.value
  pasteImageFromClipboard(sectionTitle, rowIdx, fieldLabel, e)
}

function toImageArray(val: string | string[] | undefined): string[] {
  if (Array.isArray(val)) return val
  if (typeof val === 'string' && val) return [val]
  return []
}

function previewImage(src: string) {
  imagePreviewSrc.value = src
  imagePreviewOpen.value = true
}

function editorFieldWide(field: FormField): boolean {
  return !!field.fullWidth || field.type === 'textarea' || field.type === 'image'
}

async function prepareComparisonEditors(values: Record<string, SectionValue>, templateSections: FormSection[]) {
  for (const section of templateSections) {
    const stored = values[section.title]
    const sectionRows = Array.isArray(stored) ? stored : stored ? [stored] : []
    for (const row of sectionRows) {
      for (const group of workResultFieldGroups(section).filter((item) => item.label)) {
        for (const field of group.fields.filter((item) => item.type === 'image')) {
          row[field.label] = await Promise.all(toImageArray(row[field.label]).map(resultImageUrl))
        }
        row[group.label] = comparisonMarkdown(row, group.fields)
        row[comparisonFormatKey(group.label)] = 'markdown'
        for (const field of group.fields.filter((item) => item.type === 'image')) row[field.label] = []
      }
    }
  }
}

async function appendComparisonImage(sectionTitle: string, rowIdx: number, label: string) {
  const src = selectedPanelImage.value
  if (!src) return
  insertingImages.value += 1
  try {
    const url = await resultImageUrl(src)
    setRowVal(sectionTitle, rowIdx, label, `${getRowVal(sectionTitle, rowIdx, label)}\n\n![사진](<${url}>)\n\n`)
    markImportedIndex(importedImages.value.indexOf(src))
    selectedPanelImage.value = ''
  } catch { $q.notify({ type: 'negative', message: '이미지를 넣지 못했습니다. 다시 시도해 주세요.' }) }
  finally { insertingImages.value -= 1 }
}

function tableInputType(type: string): 'textarea' | 'date' | 'datetime-local' | 'time' {
  if (type === 'date') return 'date'
  if (type === 'datetime') return 'datetime-local'
  if (type === 'time') return 'time'
  return 'textarea'
}

// ── Form state management ───────────────────────────────────────────────────

function startDocumentAction(action: 'create' | 'import') {
  if (importing.value) return
  if (isAllJobs.value) {
    pendingDocumentAction.value = action
    selectedDocumentType.value = null
    documentTypeDialog.value = true
  } else if (action === 'import') {
    triggerImport()
  } else {
    openCreate()
  }
}

function confirmDocumentType() {
  const selected = jobTemplates.value.find((item) => item.id === selectedDocumentType.value)
  if (!selected) return
  template.value = selected
  documentTypeDialog.value = false
  if (pendingDocumentAction.value === 'import') triggerImport()
  else openCreate()
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleFileImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !template.value) return
  const targetTemplate = template.value
  const request = pageRequest
  importing.value = true
  try {
    if (isJobPage.value) {
      const body = new FormData()
      body.append('file', file)
      body.append('template_id', targetTemplate.id)
      const { data } = await api.post<{ data: Record<string, SectionValue>; warnings: string[]; originalFile?: OriginalFile | null }>('/form-entries/import-form', body)
      if (request !== pageRequest) return
      template.value = targetTemplate
      const importedData = cloneFormData(data.data)
      openDetailCreate(importedData, data.originalFile ?? null)
      $q.notify({ type: 'info', message: `Import 완료. 표 형식으로 내용을 확인하고 저장해주세요. ${data.warnings.join(' ')}`.trim(), timeout: 10000 })
      return
    }
    const result = await formEntryService.importFromFile(targetTemplate.id, file)
    if (request !== pageRequest) return
    template.value = targetTemplate
    const importedData = result.data
    const init: Record<string, SectionValue> = {}
    for (const section of sections.value) {
      const imported = importedData[section.title]
      if (section.multiple) {
        if (Array.isArray(imported) && imported.length > 0) {
          init[section.title] = (imported as Record<string, string>[]).map((r) => ({ ...r }))
        } else {
          init[section.title] = [emptyRow(section)]
        }
      } else {
        init[section.title] = { ...(imported as Record<string, string> ?? {}) }
      }
    }
    await prepareComparisonEditors(init, targetTemplate.sections)
    if (request !== pageRequest) return
    formValues.value = init
    markdownSourceData.value = null
    formValuesSnapshot.value = '{}'
    importedImages.value = result.images ?? []
    importedImageGroups.value = result.imageGroups ?? []
    importedOriginalFile.value = result.originalFile ?? null
    placedImportedIndices.value = new Set()
    formDialog.value = true
    if (result.skipped && result.skipped.length > 0) {
      skippedItems.value = result.skipped
      skippedDialog.value = true
    }
    $q.notify({ type: 'positive', message: 'Import 완료. 내용과 이미지 위치 확인 후 저장해주세요.' })
  } catch (error) {
    const detail = isAxiosError<{ detail?: unknown }>(error) ? error.response?.data?.detail : null
    $q.notify({
      type: 'negative',
      message: typeof detail === 'string' && detail.trim() ? detail : '파일을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.',
      timeout: 15000,
      actions: [{ label: '닫기', color: 'white' }],
    })
  } finally {
    importing.value = false
    input.value = ''
  }
}

function openCreate() {
  if (!template.value) return
  const data = Object.fromEntries(template.value.sections.map((section) => {
    const row = Object.fromEntries(section.fields.map((field) => [field.label, field.type === 'image' ? [] : '']))
    return [section.title, section.multiple ? [row] : row]
  })) as Record<string, SectionValue>
  openDetailCreate(data)
}

function openDetailCreate(data: Record<string, SectionValue>, originalFile: OriginalFile | null = null): void {
  if (!template.value) return
  detailSaveWarning.value = ''
  importedOriginalFile.value = originalFile
  creatingDetail.value = true
  detailRow.value = {
    id: `new-${Date.now()}`,
    templateId: template.value.id,
    data: cloneFormData(data),
    version: 0,
    isDeleted: false,
  }
  detailDialog.value = true
}

function onDetailDialogUpdate(open: boolean): void {
  detailDialog.value = open
  if (!open) {
    ++detailRequest
    if (route.query.entryId) {
      const query = { ...route.query }; delete query.entryId
      void router.replace({ query })
    }
  }
  if (!open && creatingDetail.value) {
    creatingDetail.value = false
    detailRow.value = null
    importedOriginalFile.value = null
  }
}

function reflectSavedDocument(saved: FormEntry) {
  const index = rows.value.findIndex(row => row.id === saved.id)
  if (index < 0) rows.value.unshift(saved)
  else rows.value.splice(index, 1, saved)
}

async function saveDetailForm(values: Record<string, Record<string, unknown> | Record<string, unknown>[]>, assetIds?: string[], inspection?: WorkDocumentInspection | null) {
  if (!detailRow.value || !template.value || detailSaving.value) return
  detailSaving.value = true
  const wasCreating = creatingDetail.value
  try {
    const payload = await prepareWorkDocumentData(template.value, values)
    const saved = await saveWorkDocument({
      ...(!wasCreating ? { entry: detailRow.value } : {}),
      templateId: template.value.id, data: payload, originalFile: importedOriginalFile.value,
      assetIds, inspection,
    })
    detailSaveWarning.value = ''
    reflectSavedDocument(saved)
    detailRow.value = saved
    creatingDetail.value = false
    importedOriginalFile.value = null
    if (wasCreating) detailDialog.value = false
    $q.notify({ type: 'positive', message: inspection ? '작업계획서를 저장하고 서버 점검에 등록했습니다.' : wasCreating ? '저장됐습니다.' : '수정됐습니다.' })
  } catch (error: unknown) {
    if (error instanceof WorkDocumentInspectionError) {
      detailSaveWarning.value = error.message
      reflectSavedDocument(error.entry)
      detailRow.value = error.entry
      creatingDetail.value = false
      importedOriginalFile.value = null
    }
    const detail = apiErrorDetail(error)
    $q.notify({ type: 'negative', message: detail || '저장하지 못했습니다.' })
  } finally {
    detailSaving.value = false
  }
}

const { exportingDocument, exportDetailFile, downloadOriginalFile, exportDetailMarkdown } =
  useWorkDocumentExport(detailRow, template, sections, detailLoading)

let detailRequest = 0
async function openDetail(row: FormEntry) {
  const selectedTemplate = entryTemplate(row)
  if (!selectedTemplate) return
  const request = ++detailRequest
  detailSaveWarning.value = ''
  template.value = selectedTemplate
  markdownEditMode.value = false
  documentMode.value = !!row.data['문서 본문'] && !hasOriginalForm(selectedTemplate.sections, row.data)
  detailRow.value = row
  detailDialog.value = true
  detailLoading.value = true
  try {
    const full = await formEntryService.get(row.id)
    if (request !== detailRequest) return
    detailRow.value = full
    documentMode.value = !!detailRow.value.data['문서 본문'] && !hasOriginalForm(selectedTemplate.sections, detailRow.value.data)
  } catch {
    if (request !== detailRequest) return
    $q.notify({ type: 'negative', message: '상세 데이터를 불러오지 못했습니다.' })
    detailDialog.value = false
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}

function validate(): boolean {
  for (const section of sections.value) {
    const requiredFields = section.fields.filter((f) => f.required)
    if (requiredFields.length === 0) continue

    if (section.multiple) {
      const rowsArr = getRows(section.title)
      for (let i = 0; i < rowsArr.length; i++) {
        for (const field of requiredFields) {
          const v = rowsArr[i]?.[field.label]
          const empty = Array.isArray(v) ? v.length === 0 : !v
          if (empty) {
            $q.notify({ type: 'negative', message: `[${section.title}] ${i + 1}번째 행의 "${field.label}"은(는) 필수 입력입니다.` })
            return false
          }
        }
      }
    } else {
      for (const field of requiredFields) {
        if (!getVal(section.title, field.label)) {
          $q.notify({ type: 'negative', message: `[${section.title}] "${field.label}"은(는) 필수 입력입니다.` })
          return false
        }
      }
    }
  }
  return true
}

function apiErrorDetail(error: unknown): string {
  const response = (error as { response?: { data?: unknown } } | null)?.response
  const data = response?.data
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return error instanceof Error && error.message ? error.message : ''
}

async function saveData(): Promise<Record<string, SectionValue>> {
  if (markdownEditMode.value && template.value) {
    const merged = cloneFormData(markdownSourceData.value ?? detailRow.value?.data ?? {}) as Record<string, SectionValue>
    merged['문서 본문'] = cloneFormData(formValues.value['문서 본문'] ?? [])
    return merged
  }
  if (!isJobPage.value || documentMode.value || !template.value) return formValues.value
  const original = JSON.parse(JSON.stringify(formValues.value)) as Record<string, SectionValue>
  for (const section of template.value.sections) {
    const stored = original[section.title]
    const items = Array.isArray(stored) ? stored : stored ? [stored] : []
    for (const item of items) {
      for (const field of section.fields.filter(field => field.type === 'image')) {
        item[field.label] = await Promise.all(toImageArray(item[field.label]).map(resultImageUrl))
      }
    }
  }
  return synchronizedDocument(template.value.title, originalSections(original), original, window.location.origin)
}

async function doCreate() {
  if (editorBusy.value) return
  if (!validate() || !template.value) return
  saving.value = true
  try {
    const entry = await formEntryService.create(template.value.id, await saveData(), importedOriginalFile.value,
      canLinkWorkDocument.value ? formAssets.value.map(a => a.id) : undefined)
    rows.value.unshift(entry)
    formDialog.value = false
    $q.notify({ type: 'positive', message: '저장됐습니다.' })
  } catch (error: unknown) {
    console.error('작업 문서 저장 실패', error)
    const detail = apiErrorDetail(error)
    $q.notify({ type: 'negative', message: detail ? `저장 실패: ${detail}` : '저장 실패' })
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: FormEntry) {
  $q.dialog({
    title: '삭제 확인',
    message: '이 항목을 삭제하시겠습니까?',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    actingId.value = row.id
    formEntryService.remove(row.id)
      .then(() => {
        rows.value = rows.value.map((r) => (r.id === row.id ? { ...r, isDeleted: true } : r))
        $q.notify({ type: 'positive', message: '삭제됐습니다.' })
      })
      .catch(() => {
        $q.notify({ type: 'negative', message: '삭제 실패' })
      })
      .finally(() => {
        actingId.value = null
      })
  })
}

async function load() {
  await loadPage()
}

let pageRequest = 0
async function loadPage() {
  const request = ++pageRequest
  const id = route.params['id'] as string | undefined
  const allJobs = isAllJobs.value
  const jobPage = isJobPage.value
  loading.value = true
  tableLoading.value = true
  try {
    const templates = jobPage ? await formTemplateService.list('job') : []
    if (request !== pageRequest) return
    const order = ['작업계획서(서비스)', '작업계획서(서비스외)', '작업결과서', '반입신청서']
    const rank = (item: FormTemplate) => {
      const index = order.indexOf(item.title.replace(/\s/g, ''))
      return index < 0 ? order.length : index
    }
    jobTemplates.value = templates.sort((a, b) => rank(a) - rank(b))
    if (allJobs) {
      const entries = await Promise.all(templates.map((item) => formEntryService.list(item.id, includeDeleted.value)))
      if (request !== pageRequest) return
      template.value = null
      rows.value = entries.flat().sort((a, b) => (b.createdAt ?? '').localeCompare(a.createdAt ?? ''))
    } else if (id) {
      const tmpl = templates.find((item) => item.id === id || item.jiraIssueKey === id) ?? await formTemplateService.get(id)
      const entries = await formEntryService.list(tmpl.id, includeDeleted.value)
      if (request !== pageRequest) return
      template.value = tmpl
      rows.value = entries
    }
    await openLinkedEntry()
  } catch {
    if (request !== pageRequest) return
    rows.value = []
    template.value = null
    $q.notify({ type: 'negative', message: '작업 목록을 불러오지 못했습니다. 다시 시도해 주세요.' })
  } finally {
    if (request === pageRequest) {
      loading.value = false
      tableLoading.value = false
    }
  }
}

onMounted(() => {
  void loadPage()
  document.addEventListener('paste', handleGlobalPaste as EventListener)
})

onUnmounted(() => {
  ++pageRequest
  ++detailRequest
  document.removeEventListener('paste', handleGlobalPaste as EventListener)
})

watch(() => route.path, () => {
  ++detailRequest
  documentTypeDialog.value = false
  detailDialog.value = false
  formDialog.value = false
  resetSearch()
  void loadPage()
})

async function openLinkedEntry() {
  const id = typeof route.query.entryId === 'string' ? route.query.entryId : ''
  if (!id || (detailDialog.value && detailRow.value?.id === id)) return
  const row = rows.value.find(item => item.id === id)
  if (row) await openDetail(row)
  else $q.notify({ type: 'warning', message: '연결된 작업 문서를 찾을 수 없습니다. 삭제 여부를 확인해 주세요.' })
}
watch(() => route.query.entryId, () => { if (!loading.value) void openLinkedEntry() })
</script>

<style scoped>
.edit-section-rows { display: flex; flex-direction: column; gap: 18px; }
.edit-row-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 24px; background: #fff; }
.edit-row-heading { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; color: #64748b; font-size: 12px; }
.edit-row-number { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: #eff3fb; color: #4d6594; font-weight: 600; }
.edit-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; }
.edit-field-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.edit-field-group { grid-column: 1 / -1; min-width: 0; }
.edit-field-group.comparison-side { grid-column: auto; min-width: 0; min-height: 0; overflow: hidden; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; display: flex; flex-direction: column; }
.edit-field-group.whole-document { grid-column: 1 / -1; }
.comparison-side .edit-fields { grid-template-columns: minmax(0, 1fr); }
.comparison-editor { width: 100%; max-width: 100%; min-width: 0; min-height: 0; overflow: hidden; display: flex; flex: 1 1 auto; flex-direction: column; }
.comparison-editor > div { width: 100%; max-width: 100%; min-width: 0; min-height: 0; display: flex; flex: 1 1 auto; flex-direction: column; }
.comparison-editor :deep(.toastui-editor-defaultUI), .comparison-editor :deep(.toastui-editor-main), .comparison-editor :deep(.toastui-editor-main-container), .comparison-editor :deep(.toastui-editor-ww-container), .comparison-editor :deep(.toastui-editor-contents) { width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.comparison-editor :deep(.toastui-editor-main), .comparison-editor :deep(.toastui-editor-main-container), .comparison-editor :deep(.toastui-editor-ww-container), .comparison-editor :deep(.toastui-editor-contents) { height: auto; overflow: visible; }
.comparison-editor :deep(.toastui-editor-defaultUI-toolbar) { flex-wrap: wrap; height: auto; min-height: 45px; padding: 4px; }
.comparison-editor :deep(.toastui-editor-toolbar-group) { margin: 0; }
.comparison-editor :deep(.toastui-editor-contents img) { max-width: 100%; height: auto; }
.comparison-editor :deep(.toastui-editor-contents) { overflow-wrap: anywhere; word-break: break-word; }
.comparison-editor :deep(.toastui-editor-contents table) { width: 100%; max-width: 100%; table-layout: fixed; }
.comparison-editor :deep(.toastui-editor-contents td), .comparison-editor :deep(.toastui-editor-contents th) { min-width: 0; max-width: 100%; vertical-align: top; word-break: break-word; overflow-wrap: anywhere; }
.comparison-heading { font-size: 15px; font-weight: 650; padding-bottom: 14px; margin-bottom: 18px; border-bottom: 2px solid #94a3b8; }
.comparison-side:nth-child(2) .comparison-heading { border-bottom-color: var(--q-primary); color: var(--q-primary); }
@media (max-width: 700px) { .edit-field-groups { grid-template-columns: minmax(0, 1fr); } }
.edit-field { min-width: 0; }.edit-field.wide { grid-column: 1 / -1; }
.edit-field-label { font-size: 12px; font-weight: 500; color: #64748b; margin-bottom: 8px; }
.edit-field :deep(.q-field__control) { border-radius: 7px; }
.edit-field :deep(.q-field__native) { line-height: 1.8; font-size: 14px; }
.edit-add-row { align-self: flex-start; border-radius: 7px; }
.edit-field .image-drop-zone { border: 1px dashed #cbd5e1; border-radius: 8px; min-height: 100px; height: auto; padding: 8px; }
:global(body.body--dark) .edit-row-card { background: #182334; border-color: #334155; }
:global(body.body--dark) .edit-field-label { color: #94a3b8; }
@media (max-width: 600px) { .edit-fields { grid-template-columns: 1fr; }.edit-row-card { padding: 18px; } }
.job-category-tabs { border-bottom: 1px solid #e0e0e0; }
.image-drop-zone {
  min-height: 80px;
  width: 100%;
  height: 100%;
  border: 2px dashed #ccc;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 4px;
}
.image-drop-zone.drag-over {
  border-color: #1976d2;
  background: #e3f2fd;
}
.image-drop-zone:focus {
  outline: none;
  border-color: #1976d2;
}
.image-drop-zone.paste-ready {
  border-color: #43a047;
  background: #f1f8e9;
}
.image-drop-zone.has-image { border-style: solid; }
.drop-hint { font-size: 11px; color: #aaa; text-align: center; }
.remove-img-btn { position: absolute; top: 2px; right: 2px; }
/* 캡션 그룹이 많으면 패널이 다이얼로그 전체를 밀어내 배치할 셀이 화면 밖으로
   나가버려 드래그가 사실상 불가능해지므로, 패널 자체를 독립적으로 스크롤되는
   고정 높이 영역으로 제한한다 — 항상 배치 대상 표와 같이 보이게 하기 위함. */
.image-panel { background: #f5f5f5; max-height: 260px; overflow-y: auto; }
.image-panel-scroll { overflow-x: auto; flex-wrap: nowrap; }
.image-thumb { border: 1px solid #ddd; border-radius: 4px; padding: 4px; background: white; cursor: pointer; }
.image-thumb--selected { border: 2px solid #43a047; background: #f1f8e9; box-shadow: 0 0 0 2px #43a04766; }
</style>
