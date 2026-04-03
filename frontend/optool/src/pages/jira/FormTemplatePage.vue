<template>
  <q-page class="q-pa-md">
    <q-inner-loading :showing="loading" />

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
        <q-btn color="primary" icon="add" :label="`${template.title} 추가`" @click="openCreate" />
      </div>

      <q-card bordered>
        <q-card-section class="q-pa-none">
          <q-table
            :rows="rows"
            :columns="columns"
            row-key="id"
            :loading="tableLoading"
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

            <template #body-cell-status="props">
              <q-td :props="props">
                <q-badge :color="props.row.is_deleted ? 'grey' : 'positive'" outline>
                  {{ props.row.is_deleted ? '삭제됨' : '정상' }}
                </q-badge>
              </q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props">
                <div class="row items-center justify-end q-gutter-xs">
                  <q-btn dense outline icon="visibility" label="상세" @click="openDetail(props.row)" />
                  <q-btn
                    dense outline icon="edit" label="수정"
                    :disable="props.row.is_deleted"
                    @click="openEdit(props.row)"
                  />
                  <q-btn
                    dense color="negative" icon="delete" label="삭제"
                    :disable="props.row.is_deleted"
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
    <q-dialog v-model="formDialog" persistent>
      <q-card style="width: 800px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ isEdit ? `${template?.title} 수정` : `${template?.title} 추가` }}</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="col scroll" style="min-height: 0;">
          <div v-for="section in sections" :key="section.title" class="q-mb-lg">

            <!-- Multiple section (array) -->
            <template v-if="section.multiple">
              <div class="row items-center q-mb-sm">
                <div class="text-subtitle2 text-bold">{{ section.title }}</div>
                <q-space />
                <q-btn
                  icon="add"
                  label="항목 추가"
                  size="sm"
                  flat
                  color="primary"
                  @click="addRow(section)"
                />
              </div>
              <div
                v-for="(row, rowIdx) in getRows(section.title)"
                :key="rowIdx"
                class="q-mb-md q-pa-sm"
                style="border: 1px solid #e0e0e0; border-radius: 4px;"
              >
                <div class="row items-center q-mb-sm">
                  <div class="text-caption text-grey-7">항목 {{ rowIdx + 1 }}</div>
                  <q-space />
                  <q-btn
                    v-if="getRows(section.title).length > 1"
                    icon="delete"
                    size="xs"
                    flat
                    dense
                    color="negative"
                    @click="removeRow(section.title, rowIdx)"
                  />
                </div>
                <div class="row q-col-gutter-sm">
                  <div
                    v-for="field in section.fields"
                    :key="field.label"
                    :class="fieldColClass(field)"
                  >
                    <q-input
                      v-if="field.type !== 'boolean' && field.type !== 'select'"
                      :model-value="getRowVal(section.title, rowIdx, field.label)"
                      @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)"
                      :label="field.label"
                      :placeholder="field.placeholder"
                      :type="inputType(field.type)"
                      :required="field.required"
                      outlined dense
                    />
                    <q-select
                      v-else-if="field.type === 'select'"
                      :model-value="getRowVal(section.title, rowIdx, field.label)"
                      @update:model-value="setRowVal(section.title, rowIdx, field.label, $event)"
                      :label="field.label"
                      :options="field.options ?? []"
                      outlined dense
                    />
                    <q-toggle
                      v-else
                      :model-value="getRowVal(section.title, rowIdx, field.label) === 'true'"
                      @update:model-value="setRowVal(section.title, rowIdx, field.label, String($event))"
                      :label="field.label"
                    />
                  </div>
                </div>
              </div>
            </template>

            <!-- Single section -->
            <template v-else>
              <div class="text-subtitle2 text-bold q-mb-sm">{{ section.title }}</div>
              <div v-for="field in section.fields" :key="field.label" class="q-mb-sm">
                <q-input
                  v-if="field.type !== 'boolean' && field.type !== 'select'"
                  :model-value="getVal(section.title, field.label)"
                  @update:model-value="setVal(section.title, field.label, $event)"
                  :label="field.label"
                  :placeholder="field.placeholder"
                  :type="inputType(field.type)"
                  :required="field.required"
                  outlined dense
                />
                <q-select
                  v-else-if="field.type === 'select'"
                  :model-value="getVal(section.title, field.label)"
                  @update:model-value="setVal(section.title, field.label, $event)"
                  :label="field.label"
                  :options="field.options ?? []"
                  outlined dense
                />
                <q-toggle
                  v-else
                  :model-value="getVal(section.title, field.label) === 'true'"
                  @update:model-value="setVal(section.title, field.label, String($event))"
                  :label="field.label"
                />
              </div>
            </template>

          </div>
        </q-card-section>
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

    <!-- Detail Dialog -->
    <q-dialog v-model="detailDialog">
      <q-card style="width: 700px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">상세 보기</div>
          <q-space />
          <q-btn flat dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="col scroll" style="min-height: 0;">
          <div v-if="detailRow">
            <div v-for="section in sections" :key="section.title" class="q-mb-md">
              <div class="text-subtitle2 text-bold q-mb-xs">{{ section.title }}</div>

              <!-- Multiple section in detail -->
              <template v-if="section.multiple">
                <div
                  v-for="(rowData, rowIdx) in detailMultipleRows(detailRow, section.title)"
                  :key="rowIdx"
                  class="q-mb-sm q-pa-xs"
                  style="border: 1px solid #e0e0e0; border-radius: 4px;"
                >
                  <div class="text-caption text-grey q-mb-xs">항목 {{ rowIdx + 1 }}</div>
                  <q-list bordered separator dense>
                    <q-item v-for="field in section.fields" :key="field.label">
                      <q-item-section>
                        <q-item-label caption>{{ field.label }}</q-item-label>
                        <q-item-label>{{ rowData[field.label] || '-' }}</q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
              </template>

              <!-- Single section in detail -->
              <template v-else>
                <q-list bordered separator dense>
                  <q-item v-for="field in section.fields" :key="field.label">
                    <q-item-section>
                      <q-item-label caption>{{ field.label }}</q-item-label>
                      <q-item-label>{{ detailRow.data[section.title]?.[field.label] || '-' }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </template>

            </div>
            <div class="text-caption text-grey q-mt-md">
              제출: {{ detailRow.created_by }} · {{ detailRow.created_at }}
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { formTemplateService, type FormTemplate } from 'src/services/formTemplates'
import { formEntryService, type FormEntry } from 'src/services/formEntries'

type FormField = { label: string; type: string; required?: boolean; placeholder?: string; options?: string[] }
type FormSection = { title: string; fields: FormField[]; multiple?: boolean }

const route = useRoute()
const $q = useQuasar()

const loading = ref(true)
const tableLoading = ref(false)
const saving = ref(false)
const includeDeleted = ref(false)

const template = ref<FormTemplate | null>(null)
const rows = ref<FormEntry[]>([])

// dialogs
const formDialog = ref(false)
const detailDialog = ref(false)
const isEdit = ref(false)
const detailRow = ref<FormEntry | null>(null)
const actingId = ref<string | null>(null)
const editingId = ref<string | null>(null)
const editingVersion = ref(1)

// formValues: single section → Record<string,string>, multiple section → Array<Record<string,string>>
const formValues = ref<Record<string, any>>({})

const sections = computed<FormSection[]>(() =>
  template.value ? (template.value.sections as FormSection[]) : []
)

const columns = computed(() => [
  { name: 'preview', label: '내용 미리보기', field: 'id', align: 'left' as const },
  { name: 'status', label: '상태', field: 'is_deleted', align: 'center' as const },
  { name: 'created_by', label: '제출자', field: 'created_by', align: 'left' as const },
  { name: 'created_at', label: '제출일', field: 'created_at', align: 'left' as const, sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
])

function entryPreview(row: FormEntry): string {
  const firstSection = sections.value[0]
  if (!firstSection) return ''
  const sectionData = row.data[firstSection.title]
  if (!sectionData) return ''
  if (firstSection.multiple) {
    // Array type
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
  if (!sec || typeof sec !== 'object' || Array.isArray(sec)) return ''
  return (sec as Record<string, string>)[fieldLabel] ?? ''
}

function setVal(sectionTitle: string, fieldLabel: string, val: string | number | null): void {
  if (!formValues.value[sectionTitle] || Array.isArray(formValues.value[sectionTitle])) {
    formValues.value[sectionTitle] = {}
  }
  ;(formValues.value[sectionTitle] as Record<string, string>)[fieldLabel] = val == null ? '' : String(val)
}

// ── Multiple section helpers ────────────────────────────────────────────────

function getRows(sectionTitle: string): Array<Record<string, string>> {
  const val = formValues.value[sectionTitle]
  if (Array.isArray(val)) return val as Array<Record<string, string>>
  return []
}

function getRowVal(sectionTitle: string, rowIdx: number, fieldLabel: string): string {
  const rows = getRows(sectionTitle)
  return rows[rowIdx]?.[fieldLabel] ?? ''
}

function setRowVal(sectionTitle: string, rowIdx: number, fieldLabel: string, val: string | number | null): void {
  const rowsArr = getRows(sectionTitle)
  if (!rowsArr[rowIdx]) rowsArr[rowIdx] = {}
  rowsArr[rowIdx][fieldLabel] = val == null ? '' : String(val)
}

function emptyRow(section: FormSection): Record<string, string> {
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

// ── Detail dialog helper for multiple sections ──────────────────────────────

function detailMultipleRows(row: FormEntry, sectionTitle: string): Array<Record<string, string>> {
  const val = row.data[sectionTitle]
  if (Array.isArray(val)) return val as Array<Record<string, string>>
  return []
}

// ── Form field helpers ──────────────────────────────────────────────────────

function fieldColClass(field: FormField): string {
  if (field.type === 'textarea') return 'col-12'
  return 'col-12 col-md-6'
}

function inputType(type: string): 'text' | 'textarea' | 'date' | 'datetime-local' {
  if (type === 'textarea') return 'textarea'
  if (type === 'date') return 'date'
  if (type === 'datetime') return 'datetime-local'
  return 'text'
}

// ── Form state management ───────────────────────────────────────────────────

function resetForm() {
  const init: Record<string, any> = {}
  for (const section of sections.value) {
    if (section.multiple) {
      init[section.title] = [emptyRow(section)]
    } else {
      init[section.title] = Object.fromEntries(section.fields.map((f) => [f.label, '']))
    }
  }
  formValues.value = init
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
  const copy: Record<string, any> = {}
  for (const section of sections.value) {
    const saved = row.data[section.title]
    if (section.multiple) {
      // Expect array; fall back to single empty row
      if (Array.isArray(saved) && saved.length > 0) {
        copy[section.title] = saved.map((r: Record<string, string>) => ({ ...r }))
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

function openDetail(row: FormEntry) {
  detailRow.value = row
  detailDialog.value = true
}

function validate(): boolean {
  for (const section of sections.value) {
    if (section.multiple) {
      const rowsArr = getRows(section.title)
      for (let rowIdx = 0; rowIdx < rowsArr.length; rowIdx++) {
        for (const field of section.fields) {
          if (field.required && !getRowVal(section.title, rowIdx, field.label).trim()) {
            $q.notify({ type: 'warning', message: `${section.title} 항목 ${rowIdx + 1}: ${field.label} 항목은 필수입니다.` })
            return false
          }
        }
      }
    } else {
      for (const field of section.fields) {
        if (field.required && !getVal(section.title, field.label).trim()) {
          $q.notify({ type: 'warning', message: `${field.label} 항목은 필수입니다.` })
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
        rows.value = rows.value.map((r) => (r.id === row.id ? { ...r, is_deleted: true } : r))
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
})

watch(() => route.params['id'], (id) => {
  if (id) void loadPage(id as string)
})
</script>
