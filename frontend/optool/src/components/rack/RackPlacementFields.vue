<template>
  <div class="rp-form-grid">
    <template v-if="$slots.asset">
      <div class="rp-label">{{ assetLabel }} <span class="rp-required">*</span></div>
      <div class="rp-control"><slot name="asset" /></div>
    </template>
    <div class="rp-label">랙 <span class="rp-required">*</span></div>
    <div class="rp-control">
      <q-select v-model="form.rackId" :options="rackOptions" emit-value map-options
        aria-label="랙" outlined dense :readonly="rackReadonly" :disable="disabled" />
    </div>
    <div class="rp-label">시작 U <span class="rp-required">*</span></div>
    <div class="rp-control">
      <q-input v-model.number="form.startU" type="number" aria-label="시작 U" outlined dense min="1" step="1" :disable="disabled" />
    </div>
    <div class="rp-label">높이(U) <span class="rp-required">*</span></div>
    <div class="rp-control">
      <q-input v-model.number="form.heightU" type="number" aria-label="높이(U)" outlined dense min="1" step="1" :disable="disabled" />
    </div>
    <div class="rp-label">장착면</div>
    <div class="rp-control">
      <q-select v-model="form.mountSide" :options="MOUNT_OPTIONS" emit-value map-options aria-label="장착면" outlined dense :disable="disabled" />
    </div>
    <div class="rp-label">점유 예정</div>
    <div class="rp-range" :class="rangeError ? 'text-negative' : 'text-grey-8'" aria-live="polite">
      <span v-if="rangeError">{{ rangeError }}</span>
      <span v-else>U{{ form.startU }}~U{{ form.startU + form.heightU - 1 }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RackPlacementForm, RackSummary } from 'src/types/racks'
import { placementRangeError } from 'src/utils/rackPlacement'

const form = defineModel<RackPlacementForm>({ required: true })
const props = withDefaults(defineProps<{
  racks: RackSummary[]
  rackReadonly?: boolean
  disabled?: boolean
  assetLabel?: string
}>(), { rackReadonly: false, disabled: false, assetLabel: '배치할 자산' })
const MOUNT_OPTIONS = [{ label: '전면', value: 'FRONT' }, { label: '후면', value: 'REAR' }]
const rackOptions = computed(() => props.racks.map(rack => ({ label: `${rack.name} (${rack.usedU}/${rack.totalU}U)`, value: rack.rackId })))
const rangeError = computed(() => placementRangeError(form.value, props.racks))
</script>

<style scoped>
.rp-form-grid { display: grid; grid-template-columns: 112px minmax(0, 1fr); align-items: center; gap: 12px 16px; }
.rp-label { color: #607d8b; font-size: 13px; font-weight: 600; text-align: right; }
.rp-required { color: #d32f2f; }
.rp-control { min-width: 0; }
.rp-range { min-width: 0; min-height: 40px; display: flex; align-items: center; padding: 8px 12px; border: 1px solid #eceff1; border-radius: 4px; background: #f7f9fa; font-size: 13px; }
@media (max-width: 480px) { .rp-form-grid { grid-template-columns: 88px minmax(0, 1fr); column-gap: 10px; } }
</style>
