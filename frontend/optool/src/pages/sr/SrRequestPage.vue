<template>
  <q-page padding class="sr-request-page">

    <div class="row items-center q-mb-md">
      <q-btn flat dense round icon="arrow_back" class="q-mr-xs" @click="$router.back()" />
      <div class="col">
        <div class="text-h6 text-weight-bold">{{ editId ? 'SR 수정' : 'SR 접수' }}</div>
        <div class="text-caption text-grey-5">{{ editId ? 'SR 내용을 수정합니다.' : '데이터운영팀에 업무 요청을 접수합니다.' }}</div>
      </div>
      <HelpButton feature="sr-new" guide-path="/pm/sr/guide" />
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
              maxlength="255" counter
              :rules="[v => !!v || '필수 항목입니다.', v => (v?.length ?? 0) <= 255 || '제목은 255자 이내로 입력해주세요.']" />
          </div>

          <div class="form-section">
            <div class="section-label">기본 정보</div>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-sm-6">
                <q-field label="요청자" outlined dense stack-label readonly>
                  <template #control>
                    <div class="self-center full-width text-body2">
                      {{ form.requesterName || form.requesterEmail }}
                      <span v-if="form.requesterDepartment" class="text-grey-6 text-caption q-ml-xs">({{ form.requesterDepartment }})</span>
                    </div>
                  </template>
                </q-field>
              </div>
              <div class="col-12 col-sm-6">
                <q-select v-model="form.relatedSystem" :options="systemOptions" label="대상 시스템 *" outlined dense
                  :rules="[v => !!v || '필수 항목입니다.']">
                  <template v-if="!systemOptions.length" #no-option>
                    <q-item>
                      <q-item-section class="text-grey">등록된 시스템이 없습니다. 관리자에게 문의하세요.</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </div>
            </div>
          </div>

          <div class="form-section">
            <q-input v-model="form.background" label="요청 배경 (선택)" outlined dense
              type="textarea" :rows="3"
              placeholder="이 요청이 발생하게 된 배경이나 상황을 설명해주세요." />
          </div>

          <div class="form-section">
            <div class="section-label">일정 및 중요도</div>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-sm-4">
                <q-input v-model="form.desiredDueDate" label="희망 완료일 *" outlined dense type="date"
                  :rules="[v => !!v || '희망 완료일을 입력해주세요.']" />
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
            <q-banner v-if="form.requestType === 'FIREWALL'" dense rounded class="bg-blue-1 text-blue-9 q-mb-md">
              <template #avatar><q-icon name="description" color="primary" /></template>
              방화벽 정책이 여러 건이면 엑셀 양식을 내려받아 작성 후 업로드하면 방화벽 정책 목록에 자동으로 채워집니다.
              <template #action>
                <q-btn
                  flat dense no-caps color="primary" icon="download" label="템플릿 다운로드"
                  href="/templates/firewall-policy-template.xlsx"
                  download="서비스포트(방화벽정책)작성표.xlsx"
                />
                <q-btn
                  flat dense no-caps color="primary" icon="upload_file" label="엑셀 업로드"
                  @click="firewallExcelInput?.click()"
                />
                <input
                  ref="firewallExcelInput"
                  type="file"
                  accept=".xlsx,.xls"
                  class="hidden"
                  @change="onFirewallExcelSelected"
                />
              </template>
            </q-banner>
            <div class="row q-col-gutter-md">
              <div
                v-for="field in currentTypeFields" :key="field.key"
                :class="field.half ? 'col-12 col-sm-6' : 'col-12'"
              >
                <!-- textarea -->
                <template v-if="field.type === 'textarea'">
                  <q-input
                    v-model="typeDetail[field.key]"
                    :label="field.label + (field.required ? ' *' : '')"
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

                <!-- editor → markdown -->
                <template v-else-if="field.type === 'editor'">
                  <MarkdownEditor
                    v-model="form.description"
                    :label="field.label"
                    :required="field.required"
                    :rows="6"
                  />
                </template>

                <!-- table → 반복 가능한 행 (1:N, N:1, N:M 관계 표현용) -->
                <template v-else-if="field.type === 'table'">
                  <div class="table-field">
                    <div class="text-caption text-grey-7 q-mb-xs">
                      {{ field.label }}{{ field.required ? ' *' : '' }}
                    </div>
                    <div v-if="!tableRows(field).length" class="text-caption text-grey-5 q-mb-sm">
                      추가된 항목이 없습니다. 출발지 · 목적지 조합이 여러 개면 행을 여러 개 추가해주세요.
                    </div>
                    <div
                      v-for="(row, i) in tableRows(field)" :key="i"
                      class="row q-col-gutter-sm items-center q-mb-xs table-field-row"
                    >
                      <div v-for="col in field.columns" :key="col.key" class="col-12 col-sm">
                        <q-input
                          :model-value="row[col.key]"
                          @update:model-value="v => updateTableCell(field, i, col.key, String(v ?? ''))"
                          :label="col.label" :placeholder="col.placeholder"
                          outlined dense
                        />
                      </div>
                      <div class="col-auto">
                        <q-btn flat round dense icon="close" color="grey-6" size="sm" @click="removeTableRow(field, i)" />
                      </div>
                    </div>
                    <q-btn flat dense icon="add" label="행 추가" color="primary" size="sm" class="q-mt-xs" @click="addTableRow(field)" />
                  </div>
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
              field-name="file"
              label="파일을 드래그하거나 클릭하여 업로드"
              multiple
              auto-upload
              accept=".pdf,.hwp,.hwpx,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.jpg,.jpeg,.png,.gif,.webp,.mp4,.html,.htm,.log,.json,.xml,.yaml,.yml"
              max-file-size="104857600"
              flat bordered class="full-width"
              :headers="uploadHeaders"
              @uploaded="onFileUploaded"
              @failed="onUploadFailed"
            />
            <div class="text-caption text-grey-5 q-mt-xs">지원 형식: 이미지, PDF, 워드/엑셀/파워포인트, 한글(HWP), ZIP, MP4, HTML, LOG, JSON, XML, YAML (최대 100MB)</div>
            <div v-if="extraAttachments.length" class="q-mt-sm">
              <!-- 이미지 썸네일 미리보기 -->
              <div v-if="extraAttachments.some(isImageAttachment)" class="row wrap q-gutter-sm q-mb-xs">
                <div v-for="(att, i) in extraAttachments" :key="att.fileId || i" v-show="isImageAttachment(att)" class="relative-position">
                  <a :href="att.url" target="_blank">
                    <img :src="att.url" :alt="att.originalName"
                      style="height:80px;max-width:160px;border-radius:6px;object-fit:cover;display:block;cursor:pointer" />
                  </a>
                  <q-btn round dense flat size="xs" icon="close"
                    style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.45);color:#fff"
                    @click="extraAttachments.splice(i, 1)" />
                </div>
              </div>
              <!-- 일반 파일 -->
              <div v-if="extraAttachments.some(att => !isImageAttachment(att))" class="row wrap q-gutter-xs">
                <q-chip v-for="(att, i) in extraAttachments" :key="att.fileId || i" v-show="!isImageAttachment(att)"
                  clickable @click="openPreview(att)"
                  removable @remove="extraAttachments.splice(i, 1)"
                  :icon="fileIcon(att.contentType)" color="blue-1" text-color="blue-9" size="sm">
                  {{ att.originalName }} <span class="text-grey-6 q-ml-xs">({{ formatFileSize(att.size) }})</span>
                </q-chip>
              </div>
            </div>
          </div>

          <div class="form-section">
            <q-input v-model="form.note" label="비고 (선택)" outlined dense type="textarea" :rows="3" />
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
                <div class="summary-val">{{ form.desiredDueDate || '-' }} · {{ extraAttachments.length }}개</div>
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

    <AttachmentPreviewDialog v-model="previewOpen" :attachment="previewAttachment" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import {
  createSR, updateSR, getSR, listMySRs,
  SR_PRIORITY_OPTIONS, SR_PRIORITY_LABEL, SR_PRIORITY_COLOR,
  type SRAttachment, type SRAttachmentInput, type RequestType, type SRPriority, type SRListItem,
} from 'src/services/sr'
import { SR_TYPE_FIELDS, TYPE_CARDS, type SRTypeField } from 'src/services/sr-type-fields'
import { envCategoryService } from 'src/services/envCategory'
import { api } from 'src/boot/axios'
import { listServers } from 'src/services/assets'
import AttachmentPreviewDialog from 'src/components/AttachmentPreviewDialog.vue'

const $q        = useQuasar()
const router    = useRouter()
const route     = useRoute()
const authStore = useAuthStore()

// 수정 모드: /pm/sr/:id/edit 경로로 진입 시 editId가 설정됨
const editId = computed(() => route.params.id as string | undefined)

const step             = ref(1)
const saving           = ref(false)
const extraAttachments  = ref<SRAttachment[]>([])
const drafts           = ref<SRListItem[]>([])
const draftId          = ref<string | null>(null)
const draftLoading     = ref<string | null>(null)
const systemOptions    = ref<string[]>([])

const form = ref({
  title:                '',
  requesterName:        authStore.me?.fullName || '',
  requesterDepartment:  authStore.me?.team || '',
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

const typeDetail = ref<Record<string, any>>({})

// 유형이 바뀌면 type_detail 초기화
watch(() => form.value.requestType, () => { if (!editId.value) typeDetail.value = {} })

// ── computed ─────────────────────────────────────────────────────────
const typeCards         = TYPE_CARDS
const priorityOptions   = SR_PRIORITY_OPTIONS
const currentTypeFields = computed(() => SR_TYPE_FIELDS[form.value.requestType ?? ''] ?? [])
const selectedTypeCard  = computed(() => typeCards.find(t => t.value === form.value.requestType))

async function loadSystemOptions() {
  try {
    const items = await envCategoryService.itemsByKey('target_system')
    systemOptions.value = items.map(i => i.label)
  } catch { /* 조용히 실패 */ }
}

// 관리 목록에 없는(과거 자유 텍스트 등) 값이 폼에 들어있으면 드롭다운에서 사라지지 않도록 끼워 넣는다.
function ensureSystemOption(value: string) {
  if (value && !systemOptions.value.includes(value)) {
    systemOptions.value = [value, ...systemOptions.value]
  }
}

onMounted(async () => {
  await loadSystemOptions()
  if (editId.value) {
    await loadSrForEdit(editId.value)
  } else {
    try {
      drafts.value = await listMySRs({ status: 'DRAFT' })
    } catch { /* 조용히 실패 */ }
  }
})

// ── 검증 ────────────────────────────────────────────────────────────
// q-stepper의 header-nav로 단계를 건너뛰어도(1 → 4) 저장 시점에 항상 재검증되도록
// 검증 로직을 함수로 분리해 "다음 단계" 버튼과 save() 양쪽에서 재사용한다.
function validateStep1(): boolean {
  if (!form.value.requestType) {
    $q.notify({ type: 'warning', message: '요청 유형을 선택해주세요.', position: 'top' })
    step.value = 1
    return false
  }
  return true
}

function validateStep2(): boolean {
  if (!form.value.title.trim()) {
    $q.notify({ type: 'warning', message: '요청 제목을 입력해주세요.', position: 'top' })
    step.value = 2
    return false
  }
  if (!form.value.relatedSystem.trim()) {
    $q.notify({ type: 'warning', message: '대상 시스템을 선택해주세요.', position: 'top' })
    step.value = 2
    return false
  }
  if (!form.value.desiredDueDate) {
    $q.notify({ type: 'warning', message: '희망 완료일을 입력해주세요.', position: 'top' })
    step.value = 2
    return false
  }
  return true
}

function validateStep3(): boolean {
  const editorField = currentTypeFields.value.find(f => f.type === 'editor')
  if (editorField?.required && !form.value.description.trim()) {
    $q.notify({ type: 'warning', message: `'${editorField.label}' 항목을 입력해주세요.`, position: 'top' })
    step.value = 3
    return false
  }
  const missing = currentTypeFields.value.find(f => {
    if (f.type === 'editor' || !f.required) return false
    if (f.type === 'table') {
      const rows = tableRows(f)
      return !rows.length || rows.some(r => (f.columns ?? []).some(c => !c.optional && !r[c.key]?.trim()))
    }
    const v = typeDetail.value[f.key]
    return typeof v === 'string' ? !v.trim() : !v
  })
  if (missing) {
    $q.notify({ type: 'warning', message: `'${missing.label}' 항목을 입력해주세요.`, position: 'top' })
    step.value = 3
    return false
  }
  return true
}

// ── 스텝 이동 ────────────────────────────────────────────────────────
function goToStep2() { if (validateStep1()) step.value = 2 }
function goToStep3() { if (validateStep1() && validateStep2()) step.value = 3 }
function goToStep4() { if (validateStep1() && validateStep2() && validateStep3()) step.value = 4 }

function selectType(type: string) { form.value.requestType = type }

// ── table 타입 필드 (반복 가능한 행) ─────────────────────────────────────
function tableRows(field: SRTypeField): Record<string, string>[] {
  const val = typeDetail.value[field.key]
  return Array.isArray(val) ? val : []
}
function addTableRow(field: SRTypeField) {
  const row: Record<string, string> = {}
  field.columns?.forEach(c => { row[c.key] = '' })
  typeDetail.value[field.key] = [...tableRows(field), row]
}
function removeTableRow(field: SRTypeField, index: number) {
  typeDetail.value[field.key] = tableRows(field).filter((_, i) => i !== index)
}
function updateTableCell(field: SRTypeField, index: number, colKey: string, value: string) {
  const rows = tableRows(field).map((r, i) => (i === index ? { ...r, [colKey]: value } : r))
  typeDetail.value[field.key] = rows
}

// ── 방화벽 정책 엑셀 업로드 (템플릿 다운로드 파일 구조 기준: B=번호, C=출발지 IP, D=목적지 IP, E=포트번호, F=용도, G=허용/차단) ──
const firewallExcelInput = ref<HTMLInputElement | null>(null)
const FIREWALL_EXCEL_SKIP_LABELS = new Set(['번호', '분류', '예시'])

function cellStr(v: unknown): string {
  if (typeof v === 'string') return v.trim()
  if (typeof v === 'number' || typeof v === 'boolean') return String(v).trim()
  return ''
}

// "172.20.20.20(양초원)" → "172.20.20.20" (괄호와 그 안 텍스트는 제외)
function stripParenNote(raw: string): string {
  return raw.replace(/\([^)]*\)/g, '').trim()
}
// 자산 조회용 순수 IP만 추출 (CIDR "/24" 등은 자산 매칭에 안 쓰므로 제외)
function extractLookupIp(raw: string): string {
  const noParen = stripParenNote(raw)
  const m = noParen.match(/[\d.]+/)
  return m ? m[0].replace(/\.+$/, '') : ''
}

async function onFirewallExcelSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const ws = wb.Sheets[wb.SheetNames[0]!]
    // header: 'A' → 시트의 실사용 범위 시작 컬럼과 무관하게 실제 셀 주소(컬럼 문자)로 읽는다.
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws!, { header: 'A', defval: '' })

    // IP → 자산명 매핑 (목적지/출발지 PC 이름이 비어있으면 자산에서 채워넣기 위함)
    // 자산 쪽 IP도 엑셀 쪽과 동일한 방식(괄호 제거 후 숫자·점만)으로 정규화해서 비교해야
    // 자산 IP에 여백/부가 텍스트가 섞여 있어도 매칭이 깨지지 않는다.
    const ipToName = new Map<string, string>()
    let assetsLoaded = false
    try {
      const assets = await listServers(false)
      assetsLoaded = true
      for (const a of assets) {
        const key = extractLookupIp(a.ip)
        if (key) ipToName.set(key, a.name)
      }
    } catch {
      $q.notify({ type: 'warning', message: '자산 목록을 불러오지 못해 PC 이름 자동 매칭 없이 진행합니다.', position: 'top' })
    }

    const parsed: Record<string, string>[] = []
    let matchedCount = 0
    for (const r of rows) {
      const label          = cellStr(r.B)
      if (FIREWALL_EXCEL_SKIP_LABELS.has(label)) continue
      const sourceIp        = stripParenNote(cellStr(r.C))
      const destinationIp   = stripParenNote(cellStr(r.D))
      const portProtocol    = cellStr(r.E)
      const purpose         = cellStr(r.F)
      const policy           = cellStr(r.G)
      if (!sourceIp && !destinationIp && !portProtocol) continue
      const sourceHost      = ipToName.get(extractLookupIp(sourceIp)) ?? ''
      const destinationHost = ipToName.get(extractLookupIp(destinationIp)) ?? ''
      if (sourceHost) matchedCount++
      if (destinationHost) matchedCount++
      parsed.push({
        sourceIp, sourceHost, destinationIp, destinationHost,
        portProtocol, portPurpose: policy ? `${purpose} (${policy})` : purpose,
      })
    }

    if (!parsed.length) {
      $q.notify({ type: 'warning', message: '엑셀에서 인식된 방화벽 정책이 없습니다. 템플릿 양식을 확인해주세요.', position: 'top' })
      return
    }
    typeDetail.value.firewallRules = parsed
    const matchMsg = assetsLoaded ? ` (자산에서 PC 이름 ${matchedCount}건 자동 매칭)` : ''
    $q.notify({ type: 'positive', message: `방화벽 정책 ${parsed.length}건을 불러왔습니다.${matchMsg}`, position: 'top' })

    // 업로드한 원본 엑셀도 첨부파일로 남겨 나중에 다운로드할 수 있게 한다.
    const form2 = new FormData()
    form2.append('file', file)
    const res = await api.post('/pm/uploads', form2)
    extraAttachments.value.push({
      fileId: res.data.file_id || res.data.fileId || '',
      originalName: res.data.original_name || res.data.originalName || file.name,
      url: res.data.url, size: res.data.size,
      contentType: res.data.content_type || res.data.contentType || file.type,
    })
  } catch {
    $q.notify({ type: 'negative', message: '엑셀 파일을 읽는 중 오류가 발생했습니다.', position: 'top' })
  }
}

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

function isImageAttachment(att: SRAttachment) { return att.contentType?.startsWith('image/') ?? false }

const previewOpen = ref(false)
const previewAttachment = ref<SRAttachment | null>(null)
function openPreview(att: SRAttachment) {
  previewAttachment.value = att
  previewOpen.value = true
}
function fileIcon(ct: string) {
  if (ct.startsWith('image/')) return 'image'
  if (ct.startsWith('video/')) return 'movie'
  if (ct.includes('pdf')) return 'picture_as_pdf'
  if (ct.includes('spreadsheet') || ct.includes('excel')) return 'table_chart'
  if (ct.includes('powerpoint') || ct.includes('presentation')) return 'slideshow'
  if (ct.includes('zip') || ct.includes('compressed')) return 'folder_zip'
  if (ct === 'text/html' || ct === 'application/json' || ct.includes('xml')) return 'code'
  return 'insert_drive_file'
}
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

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
    ensureSystemOption(form.value.relatedSystem)
    form.value.background           = sr.background ?? ''
    form.value.description          = sr.description ?? ''
    form.value.desiredDueDate     = sr.desiredDueDate ? sr.desiredDueDate.substring(0, 10) : null
    form.value.priority             = sr.priority
    form.value.isUrgent            = sr.isUrgent
    form.value.urgentReason        = sr.urgentReason ?? ''
    form.value.note                 = sr.note ?? ''
    extraAttachments.value          = sr.attachments
    draftId.value = id
    drafts.value  = []
    step.value    = sr.requestType ? 2 : 1

    // nextTick으로 watcher를 먼저 소진(typeDetail = {}) 시킨 뒤 복원
    await nextTick()
    typeDetail.value = sr.typeDetail ?? {}
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
    requesterDepartment: authStore.me?.team || '', requesterEmail: authStore.me?.email || '',
    requestType: null, relatedSystem: '', background: '', description: '',
    desiredDueDate: null, priority: 'MEDIUM', isUrgent: false, urgentReason: '', note: '',
  }
  typeDetail.value = {}
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
    ensureSystemOption(form.value.relatedSystem)
    form.value.background           = sr.background ?? ''
    form.value.description          = sr.description ?? ''
    form.value.desiredDueDate       = sr.desiredDueDate ? sr.desiredDueDate.substring(0, 10) : null
    form.value.priority             = sr.priority
    form.value.isUrgent             = sr.isUrgent
    form.value.urgentReason         = sr.urgentReason ?? ''
    form.value.note                 = sr.note ?? ''
    extraAttachments.value          = sr.attachments
    draftId.value = id

    await nextTick()
    typeDetail.value = sr.typeDetail ?? {}
    step.value = 2
  } catch {
    $q.notify({ type: 'negative', message: 'SR 정보를 불러오지 못했습니다.' })
    void router.back()
  }
}

// ── 저장 ────────────────────────────────────────────────────────────
async function save(submit: boolean) {
  // header-nav로 단계를 건너뛰고 바로 저장을 눌러도 필수 항목이 채워져 있는지 재검증
  if (!validateStep1() || !validateStep2() || !validateStep3()) return

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
      description:          form.value.description.trim() || null,
      desired_due_date:     form.value.desiredDueDate || null,
      priority:             form.value.priority as SRPriority,
      is_urgent:            form.value.isUrgent,
      urgent_reason:        form.value.urgentReason,
      note:                 form.value.note,
      attachments:          extraAttachments.value.map((a): SRAttachmentInput => ({
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
.table-field {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
}
.table-field-row {
  padding: 4px 0;
  border-bottom: 1px dashed #eee;
}
.table-field-row:last-of-type { border-bottom: none; }

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
