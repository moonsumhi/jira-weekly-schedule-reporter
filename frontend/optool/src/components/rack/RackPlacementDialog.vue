<template>
  <q-dialog :model-value="modelValue" :persistent="saving" @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="rp-dialog">
      <q-card-section class="row items-center q-pb-none">
        <q-avatar size="30px" square rounded :color="mode === 'move' ? 'orange' : 'primary'" text-color="white">
          <q-icon :name="mode === 'move' ? 'edit_location_alt' : 'add_location_alt'" size="18px" />
        </q-avatar>
        <span class="text-h6 q-ml-sm">{{ mode === 'move' ? '배치 수정' : '자산 배치' }}</span>
      </q-card-section>

      <q-separator class="q-mt-md" />

      <q-card-section>
        <RackPlacementFields v-model="form" :racks="racks" :rack-readonly="mode === 'place'" :disabled="saving"
          :asset-label="mode === 'move' ? '이동할 자산' : '배치할 자산'">
          <template #asset>
          <div v-if="mode === 'move'" class="rp-fixed-value">
            <span>{{ asset?.name }}</span>
            <span class="text-caption text-grey-7">{{ asset?.assetCategory }}</span>
          </div>
          <div v-else-if="presetAsset" class="rp-fixed-value">
            <span>{{ presetAsset.name }}</span>
            <span class="text-caption text-grey-7">{{ presetAsset.assetCategory }}</span>
          </div>
          <div v-else class="rp-control">
            <q-select
              v-model="selectedAsset"
              :options="assetOptions"
              option-label="name"
              use-input
              fill-input
              hide-selected
              input-debounce="300"
              aria-label="배치할 자산"
              placeholder="미배치 자산 선택"
              outlined dense
              :loading="searching"
              :disable="saving"
              @filter="onAssetFilter"
            >
              <template #option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.name }}</q-item-label>
                    <q-item-label caption>{{ scope.opt.assetCategory }} · {{ scope.opt.ip || 'IP 없음' }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template #no-option>
                <q-item><q-item-section class="text-grey">미배치 자산이 없습니다.</q-item-section></q-item>
              </template>
            </q-select>
          </div>
          </template>
        </RackPlacementFields>
      </q-card-section>

      <q-separator />
      <q-card-actions align="right" class="q-px-md q-py-sm">
        <q-btn flat label="취소" :disable="saving" v-close-popup />
        <q-btn
          color="primary"
          :label="mode === 'move' ? '수정' : '배치'"
          :loading="saving"
          :disable="!canSave"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Notify } from 'quasar'
import { createPlacement, listUnplacedAssets, movePlacement } from 'src/services/racks'
import type { MountSide, RackPlacementAsset, RackPlacementForm, RackSummary, UnplacedAsset } from 'src/types/racks'
import RackPlacementFields from './RackPlacementFields.vue'
import { placementRangeError } from 'src/utils/rackPlacement'

const props = defineProps<{
  modelValue: boolean
  mode: 'place' | 'move'
  rackId: string
  racks: RackSummary[]
  presetStartU?: number | null
  presetHeight?: number | null
  presetMountSide?: MountSide | null
  asset?: RackPlacementAsset | null
  placementId?: string | null
  presetAsset?: { assetCategory: string; assetId: string; name: string } | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const form = ref<RackPlacementForm>({
  rackId: props.rackId,
  startU: 1,
  heightU: 1,
  mountSide: 'FRONT',
})

const selectedAsset = ref<UnplacedAsset | null>(null)
const assetOptions = ref<UnplacedAsset[]>([])
const allUnplaced = ref<UnplacedAsset[]>([])
const searching = ref(false)
const saving = ref(false)

const canSave = computed(() =>
  !saving.value && !placementRangeError(form.value, props.racks) && (props.mode === 'move' || !!selectedAsset.value),
)

// 다이얼로그 열릴 때 초기화
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.value = {
      rackId: props.rackId,
      startU: props.presetStartU ?? props.asset?.startU ?? 1,
      heightU: props.presetHeight ?? props.asset?.heightU ?? 1,
      mountSide: props.asset?.mountSide ?? props.presetMountSide ?? 'FRONT',
    }
    // 미배치 목록에서 고른 자산이 있으면 그대로 사용
    selectedAsset.value = props.presetAsset
      ? { assetCategory: props.presetAsset.assetCategory, assetId: props.presetAsset.assetId, name: props.presetAsset.name }
      : null
    assetOptions.value = []
    allUnplaced.value = []
    // 배치 모드에서 자산을 직접 골라야 하면 서버에서 배치 가능한 미배치 자산 목록을 로드
    if (props.mode === 'place' && !props.presetAsset) {
      searching.value = true
      listUnplacedAssets()
        .then((rows) => { allUnplaced.value = rows; assetOptions.value = rows })
        .catch(() => { allUnplaced.value = []; assetOptions.value = [] })
        .finally(() => { searching.value = false })
    }
  },
)

function onAssetFilter(val: string, update: (fn: () => void) => void) {
  const q = val.trim().toLowerCase()
  update(() => {
    assetOptions.value = !q
      ? allUnplaced.value
      : allUnplaced.value.filter((a) =>
          a.name.toLowerCase().includes(q)
          || (a.assetCode || '').toLowerCase().includes(q)
          || (a.assetNo || '').toLowerCase().includes(q)
          || (a.ip || '').toLowerCase().includes(q),
        )
  })
}

function errMessage(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String(detail.message)
  }
  return fallback
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  try {
    if (props.mode === 'move') {
      if (!props.placementId) return
      await movePlacement(props.placementId, {
        ...form.value,
        expectedVersion: props.asset?.version,
      })
      Notify.create({ type: 'positive', message: '수정했습니다.' })
    } else {
      if (!selectedAsset.value) return
      await createPlacement({
        assetCategory: selectedAsset.value.assetCategory,
        assetId: selectedAsset.value.assetId,
        ...form.value,
      })
      Notify.create({ type: 'positive', message: '배치했습니다.' })
    }
    emit('saved')
    emit('update:modelValue', false)
  } catch (e) {
    Notify.create({ type: 'negative', message: errMessage(e, '저장에 실패했습니다.') })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.rp-dialog {
  width: 520px;
  max-width: 95vw;
}
.rp-control {
  min-width: 0;
}
.rp-control :deep(.q-field) {
  width: 100%;
}
.rp-fixed-value {
  min-width: 0;
  min-height: 40px;
  border: 1px solid #cfd8dc;
  border-radius: 4px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.rp-fixed-value > span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
