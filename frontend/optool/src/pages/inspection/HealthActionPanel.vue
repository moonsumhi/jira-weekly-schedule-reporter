<template>
  <div class="action-panel">
    <div class="section-title q-mb-sm">조치 현황</div>

    <!-- 기존 조치 표시 -->
    <template v-if="action && !editing">
      <div class="row items-center q-gutter-sm q-mb-sm">
        <q-badge :color="action.isResolved ? 'positive' : 'orange'" class="q-pa-xs">
          {{ action.isResolved ? '조치 완료' : '조치 중' }}
        </q-badge>
        <span class="text-caption text-grey-7">{{ action.actor }} · {{ action.updatedAt || action.createdAt }}</span>
        <q-space />
        <q-btn v-if="isInternal" flat dense round icon="edit" size="xs" color="primary" @click="startEdit" />
        <q-btn v-if="isInternal" flat dense round icon="delete" size="xs" color="negative" @click="confirmDelete" :loading="deleting" />
      </div>
      <div v-if="action.memo" class="memo-box q-mb-sm">{{ action.memo }}</div>
      <div v-if="action.images.length" class="row q-gutter-sm">
        <q-img
          v-for="(img, i) in action.images"
          :key="i"
          :src="img"
          class="action-thumb cursor-pointer"
          fit="cover"
          @click="previewImg = img; previewDialog = true"
        />
      </div>
    </template>

    <!-- 조치 없을 때 -->
    <div v-else-if="!action && !editing" class="row items-center q-gutter-sm">
      <q-badge color="grey-5" class="q-pa-xs">조치 미등록</q-badge>
      <q-btn v-if="isInternal" flat dense size="sm" color="primary" icon="add" label="조치 등록" @click="startEdit" />
    </div>

    <!-- 등록/수정 폼 -->
    <q-card v-if="editing" flat bordered class="q-pa-sm">
      <div class="row items-center q-mb-sm">
        <span class="text-caption text-weight-medium">{{ action ? '조치 수정' : '조치 등록' }}</span>
        <q-space />
        <q-toggle v-model="form.isResolved" label="조치 완료" dense size="sm" />
      </div>

      <q-input
        v-model="form.memo"
        type="textarea"
        outlined dense autogrow
        placeholder="조치 내용을 입력하세요"
        class="q-mb-sm"
      />

      <!-- 이미지 업로드 -->
      <div class="q-mb-sm">
        <q-btn flat dense size="sm" icon="image" label="이미지 추가" color="grey-7" @click="triggerImgInput" />
        <input ref="imgInput" type="file" accept="image/*" multiple class="hidden" @change="onImgChange" />
      </div>
      <div v-if="form.images.length" class="row q-gutter-sm q-mb-sm">
        <div v-for="(img, i) in form.images" :key="i" class="img-wrap">
          <q-img :src="img" class="action-thumb" fit="cover" />
          <q-btn
            round flat dense icon="close" size="xs" color="negative"
            class="img-remove"
            @click="removeImg(i)"
          />
        </div>
      </div>

      <div class="row q-gutter-sm justify-end">
        <q-btn flat dense label="취소" size="sm" @click="cancelEdit" />
        <q-btn unelevated dense color="primary" label="저장" size="sm" @click="save" :loading="saving" />
      </div>
    </q-card>
  </div>

  <!-- 이미지 전체보기 다이얼로그 -->
  <q-dialog v-model="previewDialog">
    <q-card style="max-width:90vw; max-height:90vh">
      <q-card-section class="row justify-end q-pa-xs">
        <q-btn flat round dense icon="close" v-close-popup />
      </q-card-section>
      <q-card-section class="q-pa-sm">
        <q-img :src="previewImg" style="max-height:80vh" fit="contain" />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAuthStore } from 'stores/auth'

interface ActionOut {
  id: string
  reportId: string
  hostName: string
  memo: string
  images: string[]
  actor: string
  createdAt: string | null
  updatedAt: string | null
  isResolved: boolean
}

const props = defineProps<{ reportId: string; hostName: string }>()

const $q = useQuasar()
const auth = useAuthStore()
const isInternal = computed(() => auth.me?.isInternal !== false)
const action = ref<ActionOut | null>(null)
const editing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const imgInput = ref<HTMLInputElement | null>(null)

const form = ref({ memo: '', images: [] as string[], isResolved: true })

const previewDialog = ref(false)
const previewImg = ref('')

async function load() {
  try {
    const res = await api.get<ActionOut[]>(`/health-reports/${props.reportId}/actions`)
    const found = res.data.find((a) => a.hostName === props.hostName)
    action.value = found ?? null
  } catch {
    action.value = null
  }
}

function startEdit() {
  if (action.value) {
    form.value = { memo: action.value.memo, images: [...action.value.images], isResolved: action.value.isResolved }
  } else {
    form.value = { memo: '', images: [], isResolved: true }
  }
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function save() {
  saving.value = true
  try {
    const res = await api.post<ActionOut>(
      `/health-reports/${props.reportId}/actions/${encodeURIComponent(props.hostName)}`,
      form.value,
    )
    action.value = res.data
    editing.value = false
    $q.notify({ type: 'positive', message: '조치 내역이 저장되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  $q.dialog({
    title: '조치 내역 삭제',
    message: '이 조치 내역을 삭제하시겠습니까?',
    cancel: true,
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      deleting.value = true
      try {
        await api.delete(`/health-reports/${props.reportId}/actions/${encodeURIComponent(props.hostName)}`)
        action.value = null
        $q.notify({ type: 'positive', message: '삭제되었습니다.' })
      } catch {
        $q.notify({ type: 'negative', message: '삭제에 실패했습니다.' })
      } finally {
        deleting.value = false
      }
    })()
  })
}

function triggerImgInput() {
  imgInput.value?.click()
}

async function onImgChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  for (const file of files) {
    if (file.size > 3 * 1024 * 1024) {
      $q.notify({ type: 'warning', message: `${file.name}: 3MB 이하 이미지만 업로드 가능합니다.` })
      continue
    }
    const b64 = await toBase64(file)
    form.value.images.push(b64)
  }
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function removeImg(i: number) {
  form.value.images.splice(i, 1)
}

watch(() => [props.reportId, props.hostName], load)
onMounted(load)
</script>

<style scoped>
.hidden { display: none; }
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-left: 3px solid #1976d2;
  padding-left: 8px;
}
.memo-box {
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.6;
  background: #f8f9fa;
  border-radius: 6px;
  padding: 10px 12px;
  font-family: monospace;
}
.action-thumb {
  width: 80px;
  height: 80px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}
.img-wrap {
  position: relative;
  width: 80px;
  height: 80px;
}
.img-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  background: white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}
</style>
