<template>
  <q-page class="q-pa-md">
    <q-inner-loading :showing="loading" />

    <!-- 파일 선택창이 열려있는 동안 DOM에서 제거되면 브라우저가 창을 강제로 닫으므로,
         v-if 블록 밖에 항상 마운트된 상태로 둔다 -->
    <input ref="fileInput" type="file" accept=".pdf,.hwp" style="display:none" @change="handleFileImport" />

    <template v-if="!loading && template">
      <!-- Header -->
      <div class="row items-center q-gutter-sm q-mb-md">
        <div>
          <div class="text-h6">{{ template.title }}</div>
          <div class="text-caption text-grey">{{ template.jira_issue_key }}</div>
        </div>
        <q-space />
        <q-toggle v-model="includeDeleted" label="삭제 포함" dense @update:model-value="load" />
        <q-btn outline icon="refresh" label="새로고침" :loading="tableLoading" @click="load" />
        <q-btn outline icon="upload_file" label="Import" :loading="importing" @click="triggerImport" />
        <q-btn color="primary" icon="add" :label="`${template.title} 추가`" @click="openCreate" />
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
          style="min-width: 220px"
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
                    dense outline icon="edit" label="수정"
                    :disable="props.row.isDeleted"
                    @click="openEdit(props.row)"
                  />
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

    <!-- Create / Edit Dialog -->
    <q-dialog v-model="formDialog" persistent @hide="importedImages = []; selectedPanelImage = ''; activePasteCell = null">
      <q-card style="width: 920px; max-width: 96vw; max-height: 92vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ isEdit ? `${template?.title} 수정` : `${template?.title} 추가` }}</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="col scroll" style="min-height: 0;">
          <div v-for="section in sections" :key="section.title" class="q-mb-md">

            <!-- Multiple section: table with header -->
            <template v-if="section.multiple">
              <table class="doc-table full-width">
                <thead>
                  <tr>
                    <th :colspan="section.fields.length + 2" class="section-title-cell">{{ section.title }}</th>
                  </tr>
                  <tr>
                    <th class="label-cell no-col">No.</th>
                    <th v-for="field in section.fields" :key="field.label" class="label-cell" :style="fieldColStyle(field.label)">{{ field.label }}</th>
                    <th class="label-cell" style="width:32px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIdx) in getRows(section.title)" :key="rowIdx">
                    <td class="no-cell">{{ rowIdx + 1 }}</td>
                    <td
                      v-for="field in section.fields"
                      :key="field.label"
                      class="value-cell"
                      :style="field.type === 'image' ? 'min-width:160px; width:160px; padding:0;' : ''"

                      @dragover.prevent="field.type === 'image' ? (dragOverCell = `${section.title}__${rowIdx}__${field.label}`) : undefined"
                      @dragleave="field.type === 'image' ? (dragOverCell = '') : undefined"
                      @drop.prevent="field.type === 'image' ? onDropImage(section.title, rowIdx, field.label, $event) : undefined"
                    >
                      <!-- 이미지 필드 -->
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
                          <!-- 배치된 이미지 목록 -->
                          <div v-if="getRowImages(section.title, rowIdx, field.label).length > 0" style="display:flex;flex-wrap:wrap;gap:4px;padding:4px;">
                            <div
                              v-for="(imgSrc, imgIdx) in getRowImages(section.title, rowIdx, field.label)"
                              :key="imgIdx"
                              style="position:relative;display:inline-block;"
                            >
                              <img
                                :src="imgSrc"
                                style="width:72px;height:56px;object-fit:cover;cursor:pointer;border:1px solid #ccc;border-radius:2px;"
                                @click.stop="previewImage(imgSrc)"
                              />
                              <q-btn
                                flat dense round icon="close" size="xs"
                                style="position:absolute;top:0;right:0;background:rgba(0,0,0,0.45);color:white;padding:0;min-width:16px;min-height:16px;"
                                @click.stop="removeRowImage(section.title, rowIdx, field.label, imgIdx)"
                              />
                            </div>
                          </div>
                          <!-- 이미지 추가 영역 -->
                          <div
                            style="display:flex;align-items:center;justify-content:center;min-height:36px;cursor:pointer;padding:2px;"
                            @click.stop="onImageCellClick(section.title, rowIdx, field.label)"
                            @dragover.prevent="dragOverCell = `${section.title}__${rowIdx}__${field.label}`"
                            @drop.prevent.stop="onDropImage(section.title, rowIdx, field.label, $event)"
                          >
                            <div v-if="importedImages.length > 0 && !selectedPanelImage" style="display:flex;flex-wrap:wrap;gap:2px;">
                              <img
                                v-for="(img, imgIdx) in importedImages"
                                :key="imgIdx"
                                :src="img"
                                draggable="false"
                                style="width:36px;height:28px;object-fit:cover;border:1px solid #ccc;border-radius:2px;opacity:0.6;pointer-events:none;"
                              />
                            </div>
                            <div v-else class="drop-hint">{{ selectedPanelImage ? '클릭하여 추가' : (getRowImages(section.title, rowIdx, field.label).length > 0 ? '+ 추가' : '이미지 선택 후 클릭 또는 드래그') }}</div>
                          </div>
                        </div>
                      </template>
                      <q-input
                        v-else-if="field.type !== 'boolean' && field.type !== 'select'"
                        :model-value="getRowVal(section.title, rowIdx, field.label)"
                        @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)"
                        :placeholder="field.placeholder"
                        :type="tableInputType(field.type)"
                        borderless dense autogrow
                        class="table-input"
                      />
                      <q-select
                        v-else-if="field.type === 'select'"
                        :model-value="getRowVal(section.title, rowIdx, field.label)"
                        @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)"
                        :options="field.options ?? []"
                        borderless dense
                        class="table-input"
                      />
                      <q-toggle
                        v-else
                        :model-value="getRowVal(section.title, rowIdx, field.label) === 'true'"
                        @update:model-value="setRowVal(section.title, rowIdx, field.label, String($event))"
                      />
                    </td>
                    <td class="no-cell">
                      <q-btn
                        v-if="getRows(section.title).length > 1"
                        icon="remove"
                        flat dense size="xs"
                        color="negative"
                        @click="removeRow(section.title, rowIdx)"
                      />
                    </td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr>
                    <td :colspan="section.fields.length + 2" class="add-row-cell">
                      <q-btn icon="add" label="항목 추가" size="sm" flat color="primary" @click="addRow(section)" />
                    </td>
                  </tr>
                </tfoot>
              </table>
            </template>

            <!-- Single section: label | value table -->
            <template v-else>
              <table class="doc-table full-width">
                <thead>
                  <tr>
                    <th colspan="4" class="section-title-cell">{{ section.title }}</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="(group, gi) in groupFieldsForTable(section.fields)" :key="gi">
                    <!-- Full-width row (textarea) -->
                    <tr v-if="group.full">
                      <td class="label-cell">{{ group.field1.label }}</td>
                      <td colspan="3" class="value-cell">
                        <q-input
                          v-if="group.field1.type !== 'boolean' && group.field1.type !== 'select'"
                          :model-value="getVal(section.title, group.field1.label)"
                          @update:model-value="setVal(section.title, group.field1.label, $event)"
                          :placeholder="group.field1.placeholder"
                          :type="tableInputType(group.field1.type)"
                          borderless dense autogrow
                          class="table-input"
                        />
                        <q-select
                          v-else-if="group.field1.type === 'select'"
                          :model-value="getVal(section.title, group.field1.label)"
                          @update:model-value="setVal(section.title, group.field1.label, $event)"
                          :options="group.field1.options ?? []"
                          borderless dense
                          class="table-input"
                        />
                        <q-toggle
                          v-else
                          :model-value="getVal(section.title, group.field1.label) === 'true'"
                          @update:model-value="setVal(section.title, group.field1.label, String($event))"
                        />
                      </td>
                    </tr>
                    <!-- Paired row (2 fields per row) -->
                    <tr v-else>
                      <td class="label-cell">{{ group.field1.label }}</td>
                      <td class="value-cell">
                        <q-input
                          v-if="group.field1.type !== 'boolean' && group.field1.type !== 'select'"
                          :model-value="getVal(section.title, group.field1.label)"
                          @update:model-value="setVal(section.title, group.field1.label, $event)"
                          :placeholder="group.field1.placeholder"
                          :type="tableInputType(group.field1.type)"
                          borderless dense autogrow
                          class="table-input"
                        />
                        <q-select
                          v-else-if="group.field1.type === 'select'"
                          :model-value="getVal(section.title, group.field1.label)"
                          @update:model-value="setVal(section.title, group.field1.label, $event)"
                          :options="group.field1.options ?? []"
                          borderless dense
                          class="table-input"
                        />
                        <q-toggle
                          v-else
                          :model-value="getVal(section.title, group.field1.label) === 'true'"
                          @update:model-value="setVal(section.title, group.field1.label, String($event))"
                        />
                      </td>
                      <template v-if="group.field2">
                        <td class="label-cell">{{ group.field2?.label }}</td>
                        <td class="value-cell">
                          <q-input
                            v-if="group.field2?.type !== 'boolean' && group.field2?.type !== 'select'"
                            :model-value="getVal(section.title, group.field2?.label ?? '')"
                            @update:model-value="setVal(section.title, group.field2?.label ?? '', $event)"
                            :placeholder="group.field2?.placeholder"
                            :type="tableInputType(group.field2?.type ?? 'text')"
                            borderless dense autogrow
                            class="table-input"
                          />
                          <q-select
                            v-else-if="group.field2?.type === 'select'"
                            :model-value="getVal(section.title, group.field2?.label ?? '')"
                            @update:model-value="setVal(section.title, group.field2?.label ?? '', $event)"
                            :options="group.field2?.options ?? []"
                            borderless dense
                            class="table-input"
                          />
                          <q-toggle
                            v-else
                            :model-value="getVal(section.title, group.field2?.label ?? '') === 'true'"
                            @update:model-value="setVal(section.title, group.field2?.label ?? '', String($event))"
                          />
                        </td>
                      </template>
                      <template v-else>
                        <td class="label-cell"></td>
                        <td class="value-cell"></td>
                      </template>
                    </tr>
                  </template>
                </tbody>
              </table>
            </template>

          </div>
        </q-card-section>

        <!-- 추출된 이미지 패널 -->
        <template v-if="importedImages.length > 0">
          <q-separator />
          <q-card-section class="image-panel q-py-sm">
            <div class="row items-center q-mb-xs">
              <span class="text-subtitle2">
                추출된 이미지 ({{ importedImages.length }}장)
                <span v-if="selectedPanelImage" class="text-positive q-ml-sm">— 이미지 선택됨. 배치할 셀을 클릭하세요</span>
                <span v-else class="text-grey q-ml-sm">— 이미지를 클릭해 선택 후 배치할 셀을 클릭하세요</span>
              </span>
              <q-space />
              <q-btn flat dense icon="close" size="sm" @click="importedImages = []; selectedPanelImage = ''" />
            </div>
            <div class="image-panel-scroll row q-gutter-sm">
              <div
                v-for="(img, idx) in importedImages"
                :key="idx"
                class="image-thumb"
                :class="{ 'image-thumb--selected': selectedPanelImage === img }"
                draggable="true"
                @click="selectedPanelImage = selectedPanelImage === img ? '' : img"
                @dragstart="selectedPanelImage = img; $event.dataTransfer?.setData('text/plain', String(idx))"
                @dragend="dragOverCell = ''"
              >
                <img :src="img" draggable="false" style="width: 100px; height: 80px; object-fit: cover; cursor: grab; pointer-events: none;" />
                <div class="text-caption text-center">{{ idx + 1 }}</div>
              </div>
            </div>
          </q-card-section>
        </template>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            :label="isEdit ? '수정' : '저장'"
            :loading="saving"
            @click="isEdit ? doEdit() : doCreate()"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

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
      <q-card>
        <q-card-section>
          <img :src="imagePreviewSrc" style="max-width: 80vw; max-height: 80vh" />
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Detail Dialog -->
    <q-dialog v-model="detailDialog">
      <q-card style="width: 920px; max-width: 96vw; max-height: 92vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">상세 보기</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <div v-if="detailLoading" class="text-center q-pa-xl">
          <q-spinner size="40px" color="primary" /><br />
          <span class="text-grey q-mt-sm">불러오는 중...</span>
        </div>
        <q-card-section v-else class="col scroll" style="min-height: 0;">
          <div v-if="detailRow">
            <div v-for="section in sections" :key="section.title" class="q-mb-md">

              <!-- Multiple section in detail -->
              <template v-if="section.multiple">
                <table class="doc-table full-width">
                  <thead>
                    <tr>
                      <th :colspan="section.fields.length + 1" class="section-title-cell">{{ section.title }}</th>
                    </tr>
                    <tr>
                      <th class="label-cell no-col">No.</th>
                      <th v-for="field in section.fields" :key="field.label" class="label-cell" :style="fieldColStyle(field.label)">{{ field.label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(rowData, rowIdx) in detailMultipleRows(detailRow, section.title)" :key="rowIdx">
                      <td class="no-cell">{{ rowIdx + 1 }}</td>
                      <td
                        v-for="field in section.fields"
                        :key="field.label"
                        class="value-cell"
                        :style="field.type === 'image' ? 'min-width:160px; width:160px' : ''"
                      >
                        <template v-if="field.type === 'image'">
                          <div v-if="toImageArray(rowData[field.label]).length > 0" style="padding:4px;display:flex;flex-wrap:wrap;gap:4px;">
                            <img
                              v-for="(imgSrc, imgIdx) in toImageArray(rowData[field.label])"
                              :key="imgIdx"
                              :src="imgSrc"
                              style="max-width:120px;max-height:100px;cursor:pointer;border:1px solid #eee;border-radius:4px;"
                              @click="previewImage(imgSrc)"
                            />
                          </div>
                          <span v-else class="text-grey-5 text-caption" style="padding: 4px;">-</span>
                        </template>
                        <q-input
                          v-else
                          :model-value="(rowData[field.label] as string) || ''"
                          :type="field.type !== 'boolean' && field.type !== 'select' ? tableInputType(field.type) : 'text'"
                          borderless dense readonly autogrow
                          class="table-input"
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </template>

              <!-- Single section in detail -->
              <template v-else>
                <table class="doc-table full-width">
                  <thead>
                    <tr>
                      <th colspan="4" class="section-title-cell">{{ section.title }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(group, gi) in groupFieldsForTable(section.fields)" :key="gi">
                      <tr v-if="group.full">
                        <td class="label-cell">{{ group.field1.label }}</td>
                        <td colspan="3" class="value-cell">
                          <q-input
                            :model-value="(detailRow.data[section.title] as Record<string,string>)?.[group.field1.label] || ''"
                            :type="group.field1.type !== 'boolean' && group.field1.type !== 'select' ? tableInputType(group.field1.type) : 'text'"
                            borderless dense readonly autogrow
                            class="table-input"
                          />
                        </td>
                      </tr>
                      <tr v-else>
                        <td class="label-cell">{{ group.field1.label }}</td>
                        <td class="value-cell">
                          <q-input
                            :model-value="(detailRow.data[section.title] as Record<string,string>)?.[group.field1.label] || ''"
                            :type="group.field1.type !== 'boolean' && group.field1.type !== 'select' ? tableInputType(group.field1.type) : 'text'"
                            borderless dense readonly autogrow
                            class="table-input"
                          />
                        </td>
                        <template v-if="group.field2">
                          <td class="label-cell">{{ group.field2?.label }}</td>
                          <td class="value-cell">
                            <q-input
                              :model-value="(detailRow.data[section.title] as Record<string,string>)?.[group.field2?.label ?? ''] || ''"
                              :type="group.field2?.type !== 'boolean' && group.field2?.type !== 'select' ? tableInputType(group.field2?.type ?? 'text') : 'text'"
                              borderless dense readonly autogrow
                              class="table-input"
                            />
                          </td>
                        </template>
                        <template v-else>
                          <td class="label-cell"></td>
                          <td class="value-cell"></td>
                        </template>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </template>

            </div>
            <div class="text-caption text-grey q-mt-sm">
              제출: {{ detailRow.createdBy }} · {{ toKST(detailRow.createdAt ?? '') }}
            </div>
          </div>
        </q-card-section>
        <q-separator v-if="!detailLoading" />
        <q-card-actions align="right">
          <q-btn flat label="닫기" v-close-popup />
          <q-btn v-if="!detailLoading" outline icon="edit" label="수정" @click="detailDialog = false; openEdit(detailRow!)" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { formTemplateService, type FormTemplate, type FormField, type FormSection } from 'src/services/formTemplates'
import { formEntryService, type FormEntry, type ImportSkipped } from 'src/services/formEntries'

const route = useRoute()
const $q = useQuasar()

const loading = ref(true)
const tableLoading = ref(false)
const saving = ref(false)
const includeDeleted = ref(false)

const template = ref<FormTemplate | null>(null)
const rows = ref<FormEntry[]>([])

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
const dragOverCell = ref('')
const imagePreviewSrc = ref('')
const imagePreviewOpen = ref(false)

const activePasteCell = ref<{ sectionTitle: string; rowIdx: number; fieldLabel: string } | null>(null)
const selectedPanelImage = ref<string>('')  // 패널에서 선택된 이미지 src

// dialogs
const formDialog = ref(false)
const detailDialog = ref(false)
const detailLoading = ref(false)
const isEdit = ref(false)
const detailRow = ref<FormEntry | null>(null)
const actingId = ref<string | null>(null)
const editingId = ref<string | null>(null)
const editingVersion = ref(1)

type RowData = Record<string, string | string[]>
type SectionValue = RowData | RowData[]
const formValues = ref<Record<string, SectionValue>>({})

const sections = computed<FormSection[]>(() =>
  template.value ? (template.value.sections as FormSection[]) : []
)

function toKST(utcStr: string): string {
  if (!utcStr) return '-'
  const d = new Date(utcStr)
  return d.toLocaleString('sv-SE', { timeZone: 'Asia/Seoul' }).slice(0, 16)
}

const columns = computed(() => [
  { name: 'preview', label: '내용 미리보기', field: 'id', align: 'left' as const },
  { name: 'created_by', label: '제출자', field: 'createdBy', align: 'left' as const },
  { name: 'created_at', label: '작업 일시', field: 'createdAt', align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
])

function getWorkDate(row: FormEntry): string {
  for (const sectionData of Object.values(row.data)) {
    if (Array.isArray(sectionData)) continue
    const d = sectionData?.['작업 일시'] ?? sectionData?.['작업 기간 (시작)']
    if (d) return String(d).slice(0, 10)
  }
  return '-'
}

function entryPreview(row: FormEntry): string {
  const firstSection = sections.value[0]
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

function setVal(sectionTitle: string, fieldLabel: string, val: string | number | null): void {
  if (!formValues.value[sectionTitle] || Array.isArray(formValues.value[sectionTitle])) {
    formValues.value[sectionTitle] = {}
  }
  const sec = formValues.value[sectionTitle]
  if (!Array.isArray(sec)) {
    sec[fieldLabel] = val == null ? '' : String(val)
  }
}

// ── Multiple section helpers ────────────────────────────────────────────────

function getRows(sectionTitle: string): RowData[] {
  const val = formValues.value[sectionTitle]
  if (Array.isArray(val)) return val as RowData[]
  return []
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
  arr.splice(imgIdx, 1)
  rowsArr[rowIdx][fieldLabel] = arr
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


function onDropImage(sectionTitle: string, rowIdx: number, fieldLabel: string, e: DragEvent) {
  dragOverCell.value = ''
  const idxStr = e.dataTransfer?.getData('text/plain') ?? ''
  const idx = idxStr !== '' ? Number(idxStr) : -1
  const src = (idx >= 0 && importedImages.value[idx]) ? importedImages.value[idx] : selectedPanelImage.value
  if (src) {
    addRowImage(sectionTitle, rowIdx, fieldLabel, src)
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

// ── Detail dialog helper ────────────────────────────────────────────────────

function detailMultipleRows(row: FormEntry, sectionTitle: string): RowData[] {
  const val = row.data[sectionTitle]
  if (Array.isArray(val)) return val as RowData[]
  return []
}

// ── Table layout helper ─────────────────────────────────────────────────────

function groupFieldsForTable(fields: FormField[]): Array<{ full: boolean; field1: FormField; field2: FormField | undefined }> {
  const result: Array<{ full: boolean; field1: FormField; field2: FormField | undefined }> = []
  let i = 0
  while (i < fields.length) {
    const f = fields[i]!
    if (f.type === 'textarea') {
      result.push({ full: true, field1: f, field2: undefined })
      i++
    } else {
      const next = (i + 1 < fields.length && fields[i + 1]?.type !== 'textarea') ? fields[i + 1] : undefined
      result.push({ full: false, field1: f, field2: next })
      i += next ? 2 : 1
    }
  }
  return result
}

// ── Form field helpers ──────────────────────────────────────────────────────

// 다중 섹션 컬럼 너비 힌트
const NARROW_COLS: Record<string, string> = {
  '제목': '25%',
  '테스트 케이스 ID': '13%',
  '리스크': '60px',
  '작업 시작 시간': '90px',
  '작업 종료 시간': '90px',
  '비고': '80px',
  '점검 결과': '80px',
}

function fieldColStyle(label: string): string {
  return NARROW_COLS[label] ? `width:${NARROW_COLS[label]};min-width:${NARROW_COLS[label]}` : ''
}

// 테이블 셀용: 일반 텍스트도 autogrow textarea로 렌더링해 잘림 방지
function tableInputType(type: string): 'textarea' | 'date' | 'datetime-local' | 'time' {
  if (type === 'date') return 'date'
  if (type === 'datetime') return 'datetime-local'
  if (type === 'time') return 'time'
  return 'textarea'
}

// ── Form state management ───────────────────────────────────────────────────

function resetForm() {
  const init: Record<string, SectionValue> = {}
  for (const section of sections.value) {
    if (section.multiple) {
      init[section.title] = [emptyRow(section)]
    } else {
      init[section.title] = Object.fromEntries(section.fields.map((f) => [f.label, '']))
    }
  }
  formValues.value = init
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleFileImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !template.value) return
  importing.value = true
  try {
    const result = await formEntryService.importFromFile(template.value.id, file)
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
    formValues.value = init
    importedImages.value = result.images ?? []
    isEdit.value = false
    editingId.value = null
    formDialog.value = true
    if (result.skipped && result.skipped.length > 0) {
      skippedItems.value = result.skipped
      skippedDialog.value = true
    } else {
      $q.notify({ type: 'positive', message: 'Import 완료. 내용을 확인 후 저장하세요.' })
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Import 실패. 파일을 확인하세요.' })
  } finally {
    importing.value = false
    input.value = ''
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  resetForm()
  formDialog.value = true
}

function openEdit(row: FormEntry) {
  isEdit.value = true
  editingId.value = row.id
  editingVersion.value = row.version
  const copy: Record<string, SectionValue> = {}
  for (const section of sections.value) {
    const saved = row.data[section.title]
    if (section.multiple) {
      if (Array.isArray(saved) && saved.length > 0) {
        copy[section.title] = saved.map((r: RowData) => ({ ...r }))
      } else {
        copy[section.title] = [emptyRow(section)]
      }
    } else {
      copy[section.title] = { ...(saved as Record<string, string> ?? {}) }
    }
  }
  formValues.value = copy
  formDialog.value = true
}

async function openDetail(row: FormEntry) {
  detailRow.value = row
  detailDialog.value = true
  detailLoading.value = true
  try {
    detailRow.value = await formEntryService.get(row.id)
  } catch {
    $q.notify({ type: 'negative', message: '상세 데이터를 불러오지 못했습니다.' })
    detailDialog.value = false
  } finally {
    detailLoading.value = false
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

async function doCreate() {
  if (!validate() || !template.value) return
  saving.value = true
  try {
    const entry = await formEntryService.create(template.value.id, formValues.value)
    rows.value.unshift(entry)
    formDialog.value = false
    $q.notify({ type: 'positive', message: '저장됐습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장 실패' })
  } finally {
    saving.value = false
  }
}

async function doEdit() {
  if (!validate() || !editingId.value) return
  saving.value = true
  try {
    const updated = await formEntryService.patch(editingId.value, formValues.value, editingVersion.value)
    rows.value = rows.value.map((r) => (r.id === updated.id ? updated : r))
    formDialog.value = false
    $q.notify({ type: 'positive', message: '수정됐습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '수정 실패' })
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
  if (!template.value) return
  tableLoading.value = true
  try {
    rows.value = await formEntryService.list(template.value.id, includeDeleted.value)
  } finally {
    tableLoading.value = false
  }
}

async function loadPage(id: string) {
  loading.value = true
  try {
    const [tmpl, entries] = await Promise.all([
      formTemplateService.get(id),
      formEntryService.list(id),
    ])
    template.value = tmpl
    rows.value = entries
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadPage(route.params['id'] as string)
  document.addEventListener('paste', handleGlobalPaste as EventListener)
})

onUnmounted(() => {
  document.removeEventListener('paste', handleGlobalPaste as EventListener)
})

watch(() => route.params['id'], (id) => {
  if (id) void loadPage(id as string)
})
</script>

<style scoped>
.doc-table {
  border-collapse: collapse;
  border: 1px solid #9e9e9e;
  font-size: 13px;
}
.doc-table th,
.doc-table td {
  border: 1px solid #9e9e9e;
}
.section-title-cell {
  background-color: #d6d6d6;
  font-weight: bold;
  text-align: center;
  padding: 5px 10px;
  font-size: 13px;
}
.label-cell {
  background-color: #f0f0f0;
  font-weight: 500;
  padding: 5px 10px;
  white-space: nowrap;
  vertical-align: middle;
  font-size: 12px;
}
.no-col {
  width: 36px;
  text-align: center;
}
.no-cell {
  background-color: #f0f0f0;
  text-align: center;
  padding: 2px 6px;
  vertical-align: middle;
  font-size: 12px;
  white-space: nowrap;
}
.value-cell {
  background-color: #ffffff;
  padding: 0 4px;
  vertical-align: middle;
}
.add-row-cell {
  background-color: #fafafa;
  text-align: center;
  padding: 4px;
}
.table-input {
  width: 100%;
}
.table-input :deep(.q-field__control) {
  min-height: unset !important;
  padding: 0;
}
.table-input :deep(.q-field__native) {
  padding: 4px 2px;
  min-height: unset !important;
  line-height: 1.4;
}
.table-input :deep(.q-field__marginal) {
  height: unset;
}
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
.image-panel { background: #f5f5f5; }
.image-panel-scroll { overflow-x: auto; flex-wrap: nowrap; }
.image-thumb { border: 1px solid #ddd; border-radius: 4px; padding: 4px; background: white; cursor: pointer; }
.image-thumb--selected { border: 2px solid #43a047; background: #f1f8e9; box-shadow: 0 0 0 2px #43a04766; }
</style>
