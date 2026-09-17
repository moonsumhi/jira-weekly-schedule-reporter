<template>
  <q-dialog :model-value="modelValue" @update:model-value="close">
    <q-card class="asset-note-dialog">
      <q-card-section class="row items-center q-pb-sm">
        <div class="text-subtitle1 text-weight-medium">{{ !noteId ? '운영 메모 추가' : editing ? '운영 메모 수정' : '운영 메모' }}</div>
        <q-space /><q-btn flat round dense icon="close" aria-label="운영 메모 닫기" :disable="saving" @click="close" />
      </q-card-section>
      <q-form class="asset-note-form" @submit="save">
        <q-card-section class="asset-note-body q-pt-sm">
          <div v-if="loading" class="text-center q-pa-lg"><q-spinner color="primary" size="28px" /></div>
          <div v-if="error" class="text-negative text-caption q-mb-md" role="alert">
            {{ error }}
            <q-btn v-if="!loading && noteId && !note" flat dense label="다시 불러오기" @click="load" />
          </div>
          <template v-if="!loading && editing">
            <q-input v-model="occurredOn" outlined dense type="date" label="일자" class="note-date q-mb-md" :disable="saving" />
            <q-input v-model="content" type="textarea" outlined autofocus label="운영 메모" placeholder="어떤 일이 있었는지 간단히 남겨 주세요."
              :rows="5" maxlength="5000" counter :disable="saving" />
          </template>
          <template v-else-if="!loading && note">
            <div class="text-caption text-grey-7 q-mb-md">일자 {{ note.occurredOn }}</div>
            <div class="note-content">{{ note.content }}</div>
            <div class="text-caption text-grey-7 q-mt-lg">{{ note.createdBy }} · {{ fmtDatetimeKst(note.createdAt) }} 등록</div>
            <div v-if="note.version > 1" class="text-caption text-grey-7">{{ note.updatedBy }} · {{ fmtDatetimeKst(note.updatedAt) }} 수정</div>
          </template>
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn v-if="note && !editing && canEdit" flat color="negative" label="삭제" :disable="saving" @click="confirmDelete" />
          <q-space />
          <q-btn flat :label="editing ? '취소' : '닫기'" :disable="saving" @click="close" />
          <q-btn v-if="editing" color="primary" label="저장" type="submit" :loading="saving" :disable="!content.trim() || !occurredOn || assetDeleted" />
          <q-btn v-else-if="note && canEdit" outline color="primary" label="수정" @click="startEdit" />
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { createAssetNote, deleteAssetNote, getAssetNote, updateAssetNote, type AssetNote } from 'src/services/assetWorkHistory'
import { fmtDateKst, fmtDatetimeKst } from 'src/utils/time/kst'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{ modelValue: boolean; assetId: string; noteId: string | null; assetDeleted?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [open: boolean]; saved: [note: AssetNote]; removed: [id: string] }>()
const $q = useQuasar()
const note = ref<AssetNote | null>(null), loading = ref(false), saving = ref(false), editing = ref(false)
const content = ref(''), occurredOn = ref(''), error = ref('')
const canEdit = computed(() => note.value?.canEdit && !props.assetDeleted)
let request = 0, clientId = '', initial = ''
const snapshot = () => JSON.stringify([content.value, occurredOn.value])
function close() {
  if (saving.value) return
  const finish = () => emit('update:modelValue', false)
  if (editing.value && snapshot() !== initial) {
    $q.dialog({ title: '작성 중인 운영 메모가 있습니다', message: '저장하지 않고 닫으시겠습니까?',
      cancel: { label: '계속 작성', flat: true }, ok: { label: '닫기', color: 'negative' } }).onOk(finish)
  } else finish()
}
function startEdit() {
  content.value = note.value?.content ?? ''
  occurredOn.value = note.value?.occurredOn ?? fmtDateKst(new Date().toISOString())
  initial = snapshot()
  editing.value = true
}
async function load() {
  const token = ++request
  note.value = null; editing.value = false; error.value = ''; saving.value = false
  if (!props.noteId) {
    loading.value = false
    clientId = [...crypto.getRandomValues(new Uint8Array(16))].map(v => v.toString(16).padStart(2, '0')).join('')
    startEdit()
    return
  }
  loading.value = true
  try {
    const value = await getAssetNote(props.assetId, props.noteId)
    if (token === request) note.value = value
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '운영 메모를 불러오지 못했습니다.')
  } finally { if (token === request) loading.value = false }
}
async function save() {
  if (saving.value || !editing.value || !content.value.trim() || !occurredOn.value || props.assetDeleted) return
  const token = request
  saving.value = true; error.value = ''
  try {
    const values = { content: content.value.trim(), occurred_on: occurredOn.value }
    const updated = note.value ? await updateAssetNote(props.assetId, note.value, values)
      : await createAssetNote(props.assetId, values, clientId)
    if (token !== request) return
    emit('saved', updated)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: '운영 메모를 저장했습니다.' })
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '운영 메모를 저장하지 못했습니다. 다시 시도해 주세요.')
  } finally { if (token === request) saving.value = false }
}
function confirmDelete() {
  $q.dialog({ title: '운영 메모 삭제', message: '이 운영 메모를 삭제하시겠습니까?',
    cancel: { label: '취소', flat: true }, ok: { label: '삭제', color: 'negative' } }).onOk(() => { void remove() })
}
async function remove() {
  if (!note.value || !canEdit.value || saving.value) return
  const token = request, current = note.value
  saving.value = true; error.value = ''
  try {
    await deleteAssetNote(props.assetId, current)
    if (token !== request) return
    emit('removed', current.id)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: '운영 메모를 삭제했습니다.' })
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '운영 메모를 삭제하지 못했습니다.')
  } finally { if (token === request) saving.value = false }
}
watch(() => [props.modelValue, props.assetId, props.noteId], () => {
  ++request
  if (props.modelValue) void load()
}, { immediate: true })
onBeforeUnmount(() => { ++request })
</script>

<style scoped>
.asset-note-dialog { width: 560px; max-width: calc(100vw - 32px); max-height: 85vh; display: flex; flex-direction: column; }
.asset-note-form { display: flex; flex-direction: column; min-height: 0; }
.asset-note-body { overflow-y: auto; }
.note-date { max-width: 200px; }
.note-content { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.8; font-size: 14px; color: #33485f; }
</style>
