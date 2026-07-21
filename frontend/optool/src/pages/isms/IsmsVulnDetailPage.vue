<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <q-btn flat dense icon="arrow_back" @click="router.push('/isms-p/vulnerabilities')" />
      <div class="text-h6 q-ml-sm">취약점 상세</div>
    </div>

    <div v-if="loading" class="text-center q-pa-xl text-grey">불러오는 중...</div>

    <div v-else-if="vuln" class="row q-col-gutter-md">
      <!-- 기본 정보 -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-bold q-mb-sm">기본 정보</div>
            <div class="row q-col-gutter-sm">
              <InfoField class="col-6" label="점검일시" :value="vuln.checkDate" />
              <InfoField class="col-6" label="자산구분" :value="vuln.assetCategory" />
              <InfoField class="col-6" label="자산종류" :value="vuln.assetType" />
              <InfoField class="col-6" label="Zone" :value="vuln.zone" />
              <InfoField class="col-6" label="자산명" :value="vuln.assetName" />
              <InfoField class="col-6" label="호스트명" :value="vuln.hostname" />
              <InfoField class="col-6" label="IP" :value="vuln.ipAddress" />
              <InfoField class="col-6" label="분류" :value="vuln.classification" />
              <InfoField class="col-6" label="점검코드" :value="vuln.checkCode" />
              <InfoField class="col-6" label="위험도" :value="vuln.riskLevel" />
              <InfoField class="col-12" label="점검항목" :value="vuln.checkItem" />
              <InfoField class="col-12" label="점검결과" :value="vuln.checkResult" pre />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 조치 정보 (편집 가능) -->
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-bold q-mb-sm">조치 정보</div>
            <div class="row q-col-gutter-sm">
              <div class="col-6">
                <q-input v-model="form.assignee" dense outlined label="담당자" />
              </div>
              <div class="col-6">
                <q-select v-model="form.control_status" dense outlined label="통제여부"
                  :options="CONTROL_STATUS_OPTIONS" clearable />
              </div>
              <div class="col-6">
                <q-input v-model="form.planned_date" dense outlined type="date" label="조치예정일" />
              </div>
              <div class="col-6">
                <q-select v-model="form.action_status" dense outlined label="조치여부"
                  :options="ACTION_STATUS_OPTIONS" clearable />
                <q-btn
                  v-if="form.action_status === '접속불가'"
                  flat dense no-caps size="sm" color="primary"
                  label="접속불가 해제"
                  class="q-mt-xs"
                  :loading="saving"
                  @click="releaseUnreachable"
                />
              </div>
              <div class="col-12">
                <q-input v-model="form.action_plan" dense outlined type="textarea" autogrow label="조치계획" />
              </div>
              <div class="col-12">
                <q-input v-model="form.action_details" dense outlined type="textarea" autogrow label="조치내용" />
              </div>
              <div class="col-12">
                <q-input v-model="form.notes" dense outlined type="textarea" autogrow label="비고" />
              </div>
            </div>
            <div class="row justify-end q-mt-sm">
              <q-btn color="primary" label="저장" :loading="saving" @click="save" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- 수정 전/후 증적 -->
      <div class="col-12 col-md-6" v-for="side in (['before', 'after'] as const)" :key="side">
        <q-card flat bordered>
          <q-card-section
            class="paste-zone"
            :class="{ 'paste-zone--over': dragOverSide === side }"
            tabindex="0"
            @paste="(e: ClipboardEvent) => onPaste(e, side)"
            @dragover.prevent="dragOverSide = side"
            @dragleave.prevent="dragOverSide = null"
            @drop.prevent="(e: DragEvent) => onDrop(e, side)"
          >
            <div class="text-subtitle1 text-weight-bold q-mb-sm">
              수정 {{ side === 'before' ? '전' : '후' }} 증적
            </div>
            <q-input
              v-model="form[side === 'before' ? 'before_text' : 'after_text']"
              dense outlined type="textarea" autogrow
              :label="side === 'before' ? '수정전 설명' : '수정후 설명'"
              class="q-mb-sm"
            />
            <div class="row q-gutter-sm q-mb-sm">
              <div
                v-for="f in vuln[side === 'before' ? 'beforeFiles' : 'afterFiles']"
                :key="f.name"
                class="image-thumb"
              >
                <img :src="fileUrl(vuln.id, side, f.name)" @click="openLightbox(vuln.id, side, f)" />
                <q-btn
                  round dense size="xs" icon="close" color="negative"
                  class="thumb-delete"
                  @click="removeFile(side, f.name)"
                />
              </div>
            </div>
            <q-btn flat dense icon="add_photo_alternate" label="이미지 첨부" @click="triggerUpload(side)" />
            <div class="text-caption text-grey-6 q-mt-xs">
              이 영역을 클릭한 후 Ctrl+V로 붙여넣거나, 이미지를 끌어다 놓을 수 있습니다.
            </div>
            <input
              :ref="(el) => setInputRef(side, el as HTMLInputElement | null)"
              type="file" accept="image/*" class="hidden-input"
              @change="(e) => onFileSelected(e, side)"
            />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- 라이트박스 -->
    <q-dialog v-model="lightbox.open" maximized>
      <div class="lightbox-wrap" @click="lightbox.open = false">
        <img :src="lightbox.url" class="lightbox-img" @click.stop />
        <div class="lightbox-caption">{{ lightbox.caption }}</div>
        <q-btn round icon="close" color="white" text-color="black" class="lightbox-close" @click="lightbox.open = false" />
      </div>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import {
  getVulnerability, patchVulnerability, uploadVulnFile, deleteVulnFile,
  CONTROL_STATUS_OPTIONS, ACTION_STATUS_OPTIONS,
  type Vulnerability, type VulnFile,
} from 'src/services/isms/vulnerability'

const InfoField = defineComponent({
  props: { label: String, value: [String, null] as unknown as () => string | null | undefined, pre: Boolean },
  setup(props) {
    return () => h('div', [
      h('div', { class: 'text-caption text-grey-6' }, props.label),
      h('div', { class: props.pre ? 'text-body2' : 'text-body2 ellipsis', style: props.pre ? 'white-space:pre-wrap' : '' }, props.value || '-'),
    ])
  },
})

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const vulnId = route.params.id as string
const vuln = ref<Vulnerability | null>(null)
const loading = ref(false)
const saving = ref(false)

const form = ref({
  assignee: '' as string | null,
  control_status: null as string | null,
  action_plan: '' as string | null,
  planned_date: '' as string | null,
  action_status: null as string | null,
  action_details: '' as string | null,
  before_text: '' as string | null,
  after_text: '' as string | null,
  notes: '' as string | null,
})

const beforeInputRef = ref<HTMLInputElement | null>(null)
const afterInputRef = ref<HTMLInputElement | null>(null)

function setInputRef(side: 'before' | 'after', el: HTMLInputElement | null) {
  if (side === 'before') beforeInputRef.value = el
  else afterInputRef.value = el
}

function fileUrl(id: string, side: 'before' | 'after', name: string): string {
  return `/api/uploads/isms-p/${id}/${side}/${name}`
}

function triggerUpload(side: 'before' | 'after') {
  (side === 'before' ? beforeInputRef.value : afterInputRef.value)?.click()
}

async function uploadFile(file: File, side: 'before' | 'after') {
  if (!vuln.value) return
  try {
    const files = await uploadVulnFile(vuln.value.id, side, file)
    if (side === 'before') vuln.value.beforeFiles = files
    else vuln.value.afterFiles = files
  } catch {
    $q.notify({ type: 'negative', message: '이미지 업로드에 실패했습니다.' })
  }
}

async function onFileSelected(e: Event, side: 'before' | 'after') {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  await uploadFile(file, side)
}

const dragOverSide = ref<'before' | 'after' | null>(null)

function onPaste(e: ClipboardEvent, side: 'before' | 'after') {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        void uploadFile(file, side)
      }
      break
    }
  }
}

function onDrop(e: DragEvent, side: 'before' | 'after') {
  dragOverSide.value = null
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    void uploadFile(file, side)
  }
}

function removeFile(side: 'before' | 'after', filename: string) {
  if (!vuln.value) return
  $q.dialog({
    title: '이미지 삭제',
    message: '이 이미지를 삭제하시겠습니까?',
    cancel: true,
  }).onOk(() => {
    void (async () => {
      if (!vuln.value) return
      try {
        const files = await deleteVulnFile(vuln.value.id, side, filename)
        if (side === 'before') vuln.value.beforeFiles = files
        else vuln.value.afterFiles = files
      } catch {
        $q.notify({ type: 'negative', message: '삭제에 실패했습니다.' })
      }
    })()
  })
}

const lightbox = ref({ open: false, url: '', caption: '' })

function openLightbox(id: string, side: 'before' | 'after', f: VulnFile) {
  lightbox.value = { open: true, url: fileUrl(id, side, f.name), caption: f.original }
}

async function load() {
  loading.value = true
  try {
    const data = await getVulnerability(vulnId)
    vuln.value = data
    form.value = {
      assignee: data.assignee ?? '',
      control_status: data.controlStatus ?? null,
      action_plan: data.actionPlan ?? '',
      planned_date: data.plannedDate ?? '',
      action_status: data.actionStatus ?? null,
      action_details: data.actionDetails ?? '',
      before_text: data.beforeText ?? '',
      after_text: data.afterText ?? '',
      notes: data.notes ?? '',
    }
  } catch {
    $q.notify({ type: 'negative', message: '취약점을 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!vuln.value) return
  saving.value = true
  try {
    const updated = await patchVulnerability(vuln.value.id, form.value)
    vuln.value = { ...vuln.value, ...updated }
    if (updated.cascadeCount) {
      const verb = updated.actionStatus === '접속불가' ? '접속불가로 변경' : '접속불가 해제'
      $q.notify({ type: 'positive', message: `저장되었습니다. 담당자 ${vuln.value.assignee}의 동일 IP(${vuln.value.ipAddress}) ${updated.cascadeCount}건도 함께 ${verb}되었습니다.` })
    } else {
      $q.notify({ type: 'positive', message: '저장되었습니다.' })
    }
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}

async function releaseUnreachable() {
  form.value.action_status = '미조치'
  await save()
}

onMounted(load)
</script>

<style scoped>
.image-thumb {
  position: relative;
  width: 160px;
  height: 120px;
}
.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
}
.thumb-delete {
  position: absolute;
  top: -6px;
  right: -6px;
}
.hidden-input {
  display: none;
}
.paste-zone {
  outline: none;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
.paste-zone--over {
  background-color: rgba(59, 130, 246, 0.08);
  outline: 2px dashed #3b82f6;
}
.lightbox-wrap {
  background: rgba(0, 0, 0, 0.9);
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}
.lightbox-img {
  max-width: 92vw;
  max-height: 88vh;
  object-fit: contain;
  cursor: default;
}
.lightbox-caption {
  color: white;
  margin-top: 8px;
}
.lightbox-close {
  position: absolute;
  top: 16px;
  right: 16px;
}
</style>
