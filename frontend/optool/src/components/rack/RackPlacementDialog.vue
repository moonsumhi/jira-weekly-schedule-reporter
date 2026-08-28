<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="rp-dialog">
      <q-card-section class="row items-center q-pb-none">
        <q-avatar size="30px" square rounded :color="mode === 'move' ? 'orange' : 'primary'" text-color="white">
          <q-icon :name="mode === 'move' ? 'edit_location_alt' : 'add_location_alt'" size="18px" />
        </q-avatar>
        <span class="text-h6 q-ml-sm">{{ mode === 'move' ? '배치 수정' : '자산 배치' }}</span>
      </q-card-section>

      <q-card-section>
        <div class="row q-col-gutter-sm">
          <!-- 자산 선택 (배치) 또는 표시 (이동/프리셋) -->
          <div v-if="mode === 'move'" class="col-12 rp-asset-fixed">
            <div class="text-caption text-grey-7">이동할 자산</div>
            <div class="text-body1">{{ asset?.name }} <span class="text-caption text-grey">({{ asset?.assetCategory }})</span></div>
          </div>
          <div v-else-if="presetAsset" class="col-12 rp-asset-fixed">
            <div class="text-caption text-grey-7">배치할 자산</div>
            <div class="text-body1">{{ presetAsset.name }} <span class="text-caption text-grey">({{ presetAsset.assetCategory }})</span></div>
          </div>
          <div v-else class="col-12">
            <q-select
              v-model="selectedAsset"
              :options="assetOptions"
              option-label="name"
              use-input
              input-debounce="300"
              label="배치할 자산 (미배치) *"
              outlined dense
              :loading="searching"
              @filter="onAssetFilter"
            >
              <template #option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.name }}</q-item-label>
                    <q-item-label caption>{{ scope.opt.assetCategory }} · {{ scope.opt.assetCode || scope.opt.ip || '-' }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template #no-option>
                <q-item><q-item-section class="text-grey">미배치 자산이 없습니다.</q-item-section></q-item>
              </template>
            </q-select>
          </div>

          <!-- 대상 랙 -->
          <div class="col-12">
            <q-select
              v-model="form.rackId"
              :options="rackOptions"
              emit-value map-options
              label="랙 *"
              outlined dense
              :readonly="mode === 'place'"
            />
          </div>

          <div class="col-4">
            <q-input v-model.number="form.startU" type="number" label="시작 U *" outlined dense min="1" />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.heightU" type="number" label="높이(U) *" outlined dense min="1" />
          </div>
          <div class="col-4">
            <q-select v-model="form.mountSide" :options="MOUNT_OPTIONS" emit-value map-options label="장착면" outlined dense />
          </div>

          <div class="col-12 text-caption" :class="rangeValid ? 'text-grey-7' : 'text-negative'">
            점유 예정: U{{ form.startU }}~U{{ endU }}
            <span v-if="!rangeValid"> — 시작 U/높이를 확인하세요</span>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="취소" v-close-popup />
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
import { computed, reactive, ref, watch } from 'vue'
import { Notify } from 'quasar'
import { createPlacement, listUnplacedAssets, movePlacement } from 'src/services/racks'
import type { MountSide, RackPlacementAsset, RackSummary, UnplacedAsset } from 'src/types/racks'

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

const MOUNT_OPTIONS = [
  { label: '전면', value: 'FRONT' },
  { label: '후면', value: 'REAR' },
  { label: '전체(전·후면)', value: 'FULL' },
]

const form = reactive<{ rackId: string; startU: number; heightU: number; mountSide: MountSide }>({
  rackId: props.rackId,
  startU: 1,
  heightU: 1,
  mountSide: 'FULL',
})

const selectedAsset = ref<UnplacedAsset | null>(null)
const assetOptions = ref<UnplacedAsset[]>([])
const allUnplaced = ref<UnplacedAsset[]>([])
const searching = ref(false)
const saving = ref(false)

const rackOptions = computed(() =>
  props.racks.map((r) => ({ label: `${r.name} (${r.usedU}/${r.totalU}U)`, value: r.rackId })),
)

const endU = computed(() => form.startU + form.heightU - 1)
const rangeValid = computed(() => form.startU >= 1 && form.heightU >= 1)
const canSave = computed(() =>
  rangeValid.value && !!form.rackId && (props.mode === 'move' || !!selectedAsset.value),
)

// 다이얼로그 열릴 때 초기화
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.rackId = props.mode === 'move' ? props.rackId : props.rackId
    form.startU = props.presetStartU ?? props.asset?.startU ?? 1
    form.heightU = props.presetHeight ?? props.asset?.heightU ?? 1
    form.mountSide = props.asset?.mountSide ?? props.presetMountSide ?? 'FULL'
    // 미배치 목록에서 고른 자산이 있으면 그대로 사용
    selectedAsset.value = props.presetAsset
      ? { assetCategory: props.presetAsset.assetCategory, assetId: props.presetAsset.assetId, name: props.presetAsset.name }
      : null
    assetOptions.value = []
    allUnplaced.value = []
    // 배치 모드에서 자산을 직접 골라야 하면 미배치 목록(서버·네트워크·정보보호시스템)을 로드
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
  saving.value = true
  try {
    if (props.mode === 'move') {
      if (!props.placementId) return
      await movePlacement(props.placementId, {
        rackId: form.rackId,
        startU: form.startU,
        heightU: form.heightU,
        mountSide: form.mountSide,
        expectedVersion: props.asset?.version,
      })
      Notify.create({ type: 'positive', message: '수정했습니다.' })
    } else {
      if (!selectedAsset.value) return
      await createPlacement({
        assetCategory: selectedAsset.value.assetCategory,
        assetId: selectedAsset.value.assetId,
        rackId: form.rackId,
        startU: form.startU,
        heightU: form.heightU,
        mountSide: form.mountSide,
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
  width: 460px;
  max-width: 95vw;
}
.rp-asset-fixed {
  padding: 4px 0;
}
</style>
