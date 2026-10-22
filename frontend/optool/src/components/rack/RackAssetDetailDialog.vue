<template>
  <q-dialog :model-value="modelValue" :persistent="working" @update:model-value="value => { if (!value) void close() }">
    <q-card class="rack-asset-dialog">
      <q-card-section class="row items-start no-wrap">
        <q-icon name="inventory_2" color="primary" size="24px" class="q-mr-md q-mt-xs" />
        <div class="col" style="min-width: 0">
          <div class="text-caption text-grey-7">랙 자산 · {{ placement?.assetCategory }}</div>
          <h2 class="rack-asset-title">{{ asset?.name || placement?.name }}</h2>
          <div class="text-caption text-grey-7 q-mt-xs">{{ rackName }} · {{ position }}</div>
        </div>
        <q-btn flat round dense icon="close" aria-label="자산 상세 정보 닫기" :disable="working" @click="close" />
      </q-card-section>
      <q-separator />
      <q-tabs v-model="tab" dense align="left" active-color="primary" indicator-color="primary">
        <q-tab name="placement" label="배치" :disable="working" />
        <q-tab name="basic" label="기본정보" :disable="working" />
      </q-tabs>
      <q-tab-panels v-model="tab" class="rack-asset-content">
        <q-tab-panel name="placement">
          <RackPlacementFields v-model="form" :racks="racks" :disabled="working || !canManage" asset-label="배치 자산">
            <template #asset>
              <div class="rack-asset-fixed-value">
                <span>{{ placement?.name }}</span><span class="text-caption text-grey-7">{{ placement?.assetCategory }}</span>
              </div>
            </template>
          </RackPlacementFields>
          <q-banner v-if="placementError" rounded class="bg-red-1 text-negative q-mt-md" role="alert">{{ placementError }}</q-banner>
        </q-tab-panel>
        <q-tab-panel name="basic">
          <div v-if="loading" role="status" aria-label="자산 정보 불러오는 중">
            <q-skeleton type="text" width="45%" class="q-mb-md" />
            <q-skeleton v-for="n in 5" :key="n" type="text" class="q-mb-sm" />
          </div>
          <q-banner v-else-if="error" rounded class="bg-red-1 text-negative" role="alert">
            {{ error }}<template #action><q-btn flat label="다시 시도" @click="load" /></template>
          </q-banner>
          <div v-else-if="asset" class="rack-asset-fields">
            <template v-for="entry in basicEntries" :key="entry.key">
              <div class="rack-asset-field-label">{{ entry.label }}</div>
              <q-input
                :model-value="entry.value"
                :aria-label="entry.label"
                :type="entry.multiline ? 'textarea' : 'text'"
                :autogrow="entry.multiline"
                readonly
                outlined
                dense
                hide-bottom-space
                bg-color="grey-1"
                class="rack-asset-field-value"
              />
            </template>
          </div>
        </q-tab-panel>
      </q-tab-panels>
      <q-separator />
      <q-card-actions align="right" class="q-pa-md">
        <template v-if="tab === 'placement'">
          <q-btn v-if="canManage" outline color="negative" icon="logout" label="반출" :loading="removing" :disable="working" @click="remove" />
          <q-space />
          <q-btn flat label="닫기" :disable="working" @click="close" />
          <q-btn v-if="canManage" unelevated color="primary" label="저장" :loading="saving" :disable="!canSave" @click="save" />
        </template>
        <template v-else>
          <q-btn flat label="닫기" :disable="working" @click="close" />
          <q-btn unelevated color="primary" icon="arrow_forward" label="자세히 보기"
            :disable="!asset || loading || working || !!error" @click="goToDetails" />
        </template>
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import RackPlacementFields from './RackPlacementFields.vue'
import { getServer } from 'src/services/assets'
import { movePlacement, removePlacement } from 'src/services/racks'
import { displayValue } from 'src/utils/format/value'
import { getErrorMessage, isRecord } from 'src/utils/http/error'
import { placementRangeError } from 'src/utils/rackPlacement'
import type { ServerAsset } from 'src/types/assets'
import type { RackPlacementAsset, RackPlacementForm, RackSummary } from 'src/types/racks'

const props = defineProps<{ modelValue: boolean; placement: RackPlacementAsset | null; rackName: string; rackId: string; racks: RackSummary[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [rackId: string]; removed: [] }>()
const auth = useAuthStore()
const $q = useQuasar()
const router = useRouter()
const canManage = computed(() => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('asset')))
const asset = ref<ServerAsset | null>(null)
const loading = ref(false)
const error = ref('')
const tab = ref('placement')
const form = ref<RackPlacementForm>({ rackId: '', startU: 1, heightU: 1, mountSide: 'FRONT' })
const baseline = ref('')
const saving = ref(false)
const removing = ref(false)
const confirming = ref(false)
const placementError = ref('')
const working = computed(() => saving.value || removing.value || confirming.value)
const dirty = computed(() => !!baseline.value && JSON.stringify(form.value) !== baseline.value)
const canSave = computed(() => canManage.value && !!props.placement && dirty.value && !working.value && !placementRangeError(form.value, props.racks))
const position = computed(() => {
  const p = props.placement
  return p ? `U${p.startU}${p.heightU > 1 ? `~U${p.endU}` : ''} · ${p.mountSide === 'REAR' ? '후면' : '전면'}` : ''
})
const assetLocation = computed(() => ({
  path: '/asset/list',
  query: { category: props.placement?.assetCategory ?? '', assetId: asset.value?.id ?? '' },
}))

const BASIC_KEYS = ['상태', '구분', '자산관리번호', 'SN', '서버명', '설명', '제조사', '수량', '용도', '소속부서', '위치', '담당자', 'tags']
const LABELS: Record<string, string> = {
  서버명: '자산명', 소속부서: '소속부서/사업', 용도: '용도(상세)', version: 'Version',
  tags: '태그',
}
type Entry = { key: string; label: string; value: string; multiline: boolean }
function entry(key: string, value: unknown, label = LABELS[key] ?? key): Entry {
  const formatted = Array.isArray(value) ? value.map(displayValue).join(', ') : displayValue(value)
  return { key, label, value: formatted, multiline: /설명|비고|사양|특이사항|변경사항/.test(key) || formatted.length > 80 || formatted.includes('\n') }
}
const basicEntries = computed(() => {
  const a = asset.value
  if (!a) return []
  return [
    entry('assetId', a.assetId, '자산 ID'), entry('assetNo', a.assetNo || a.fields['자산번호'], '자산번호'),
    entry('name', a.name, '호스트명'), entry('ip', a.ip, 'IP'),
    entry('rack', props.rackName, 'RackNo.'), entry('rackUnit', position.value, 'Rack Unit No.'),
    ...BASIC_KEYS.filter(key => a.fields[key] !== undefined && a.fields[key] !== null && a.fields[key] !== '')
      .map(key => entry(key, a.fields[key])),
    entry('운영체제', a.fields['운영체제'], ['네트워크', '정보보호시스템'].includes(props.placement?.assetCategory ?? '') ? '기종' : '운영체제'),
    entry('version', a.fields.version),
  ]
})

async function mayDiscard(): Promise<boolean> {
  if (!props.modelValue) return true
  if (working.value) return false
  if (!dirty.value) return true
  confirming.value = true
  const accepted = await new Promise<boolean>(resolve => {
    $q.dialog({ title: '배치 변경사항 취소', message: '저장하지 않은 배치 변경사항이 있습니다. 변경사항을 버리고 이동할까요?',
      cancel: { label: '계속 편집', flat: true }, ok: { label: '변경사항 버리기', color: 'primary' } })
      .onOk(() => resolve(true)).onDismiss(() => resolve(false))
  })
  confirming.value = false
  return accepted
}
async function close() {
  if (await mayDiscard()) emit('update:modelValue', false)
}
async function goToDetails() {
  if (!asset.value || working.value) return
  const failure = await router.push(assetLocation.value)
  if (!failure) emit('update:modelValue', false)
}
function placementMessage(e: unknown, fallback: string): string {
  if (isRecord(e) && isRecord(e.response) && isRecord(e.response.data)) {
    const detail = e.response.data.detail
    if (isRecord(detail) && typeof detail.message === 'string') return detail.message
  }
  return getErrorMessage(e, fallback)
}
async function save() {
  const p = props.placement
  if (!canSave.value || !p) return
  const values = { ...form.value }
  saving.value = true
  placementError.value = ''
  try {
    await movePlacement(p.placementId, { ...values, expectedVersion: p.version })
    baseline.value = JSON.stringify(values)
    $q.notify({ type: 'positive', message: '배치를 수정했습니다.' })
    emit('update:modelValue', false)
    emit('saved', values.rackId)
  } catch (e) {
    placementError.value = placementMessage(e, '배치를 저장하지 못했습니다.')
  } finally {
    saving.value = false
  }
}
async function remove() {
  const p = props.placement
  if (!p || !canManage.value || working.value) return
  confirming.value = true
  const accepted = await new Promise<boolean>(resolve => {
    $q.dialog({ title: '자산 반출', message: `${p.name}을(를) 랙에서 반출할까요? 자산 정보는 유지되고 배치만 해제됩니다.${dirty.value ? ' 입력한 배치 변경사항은 저장되지 않습니다.' : ''}`,
      cancel: { label: '취소', flat: true }, ok: { label: '반출', color: 'negative', unelevated: true } })
      .onOk(() => resolve(true)).onDismiss(() => resolve(false))
  })
  confirming.value = false
  if (!accepted) return
  removing.value = true
  placementError.value = ''
  try {
    await removePlacement(p.placementId)
    baseline.value = JSON.stringify(form.value)
    $q.notify({ type: 'positive', message: '랙에서 반출했습니다.' })
    emit('update:modelValue', false)
    emit('removed')
  } catch (e) {
    placementError.value = placementMessage(e, '반출하지 못했습니다.')
  } finally {
    removing.value = false
  }
}

let request = 0
async function load() {
  const p = props.placement
  if (!props.modelValue || !p) return
  const token = ++request
  asset.value = null
  loading.value = true
  error.value = ''
  try {
    const result = await getServer(p.assetId, p.assetCategory)
    if (token === request) asset.value = result
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '자산 정보를 불러오지 못했습니다.')
  } finally {
    if (token === request) loading.value = false
  }
}
watch(() => [props.modelValue, props.placement?.placementId, props.placement?.assetCategory], () => {
  request++
  asset.value = null
  error.value = ''
  loading.value = false
  tab.value = 'placement'
  placementError.value = ''
  const p = props.placement
  form.value = { rackId: props.rackId, startU: p?.startU ?? 1, heightU: p?.heightU ?? 1, mountSide: p?.mountSide ?? 'FRONT' }
  baseline.value = JSON.stringify(form.value)
}, { immediate: true })
watch(tab, value => {
  if (value === 'basic' && props.modelValue && !asset.value && !loading.value) void load()
})
function beforeUnload(event: BeforeUnloadEvent) {
  if (props.modelValue && (dirty.value || working.value)) {
    event.preventDefault()
    event.returnValue = ''
  }
}
window.addEventListener('beforeunload', beforeUnload)
onBeforeRouteLeave(mayDiscard)
onBeforeRouteUpdate(mayDiscard)
onBeforeUnmount(() => {
  request++
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<style scoped>
.rack-asset-dialog { width: 620px; max-width: 95vw; max-height: 85vh; display: flex; flex-direction: column; border-radius: 12px; }
.rack-asset-dialog > * { flex-shrink: 0; }
.rack-asset-title { margin: 2px 0 0; font-size: 20px; line-height: 1.5; font-weight: 600; overflow-wrap: anywhere; }
.rack-asset-content { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
.rack-asset-fixed-value { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; min-height: 40px; padding: 8px 12px; border: 1px solid #cfd8dc; border-radius: 4px; overflow-wrap: anywhere; }
.rack-asset-fields { display: grid; grid-template-columns: 112px minmax(0, 1fr); align-items: center; gap: 12px 16px; }
.rack-asset-field-label { color: #607d8b; font-size: 13px; font-weight: 600; text-align: right; overflow-wrap: anywhere; }
.rack-asset-field-value { min-width: 0; }
.rack-asset-field-value :deep(.q-field__native) { color: #37474f; }
@media (max-width: 480px) { .rack-asset-fields { grid-template-columns: 88px minmax(0, 1fr); column-gap: 10px; } }
</style>
