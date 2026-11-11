<template>
  <div class="hardware-fields">
    <div v-for="(row, rowIndex) in fieldRows" :key="rowIndex" class="hardware-field-row"
      :class="{ 'hardware-field-row--many': row.length > 2 }" :style="{ '--hardware-columns': row.length }">
    <div v-for="field in row" :key="field.key" class="hardware-field form-field" :class="{ 'hardware-field--stacked': field.stacked }"
      :data-system-field="`${prefix}.${field.key}`">
      <div class="field-label">{{ field.label }}</div>
      <div class="hardware-field-content">
      <q-select v-if="editing && field.options" :model-value="values[field.key]" :options="field.options"
        borderless dense clearable hide-bottom-space class="field-input" :aria-label="field.label" :disable="disabled"
        @update:model-value="value => change(field, value)" />
      <q-input v-else-if="editing" :model-value="values[field.key] ?? null" :type="field.type || 'text'"
        borderless dense hide-bottom-space class="field-input" :aria-label="field.label" :disable="disabled"
        :autogrow="field.type === 'textarea'" :placeholder="field.placeholder" :min="field.min" :max="field.max"
        :step="field.decimal ? 'any' : 1" :maxlength="field.maxLength || 256"
        :error="!!systemInfoFieldError(field, values[field.key])" :error-message="systemInfoFieldError(field, values[field.key])"
        @update:model-value="value => change(field, value)" />
      <div v-else class="detail-value">{{ values[field.key] === null || values[field.key] === undefined || values[field.key] === '' ? '-' : values[field.key] }}</div>
      <div v-if="field.bytes && values[field.key] != null && values[field.key] !== ''" class="text-caption text-grey-6">{{ formatHardwareBytes(values[field.key]) }}</div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatHardwareBytes, systemInfoFieldError, type SystemInfoField, type SystemInfoValues } from 'src/types/assetSystemInfo'
const props = defineProps<{ fields: SystemInfoField[]; rows: string[][]; values: SystemInfoValues; prefix: string; editing: boolean; disabled: boolean }>()
const fieldRows = computed(() => props.rows.map(row => row.map(key => props.fields.find(field => field.key === key))
  .filter((field): field is SystemInfoField => field !== undefined)).filter(row => row.length))
const emit = defineEmits<{ change: [values: SystemInfoValues] }>()
function change(field: SystemInfoField, value: string | number | null) {
  const next = field.type === 'number' ? (value === '' || value === null ? null : Number(value))
    : field.type === 'date' ? value || null : value ?? ''
  emit('change', { ...props.values, [field.key]: next })
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.hardware-fields { container-type: inline-size; }
.hardware-field-row { display: grid; grid-template-columns: repeat(var(--hardware-columns), minmax(0, 1fr)); gap: 8px 16px; }
.hardware-field-row + .hardware-field-row { margin-top: 8px; }
.hardware-field { flex-direction: row; align-items: flex-start; gap: 10px; }
.hardware-field .field-label { flex: 0 0 84px; min-width: 0; margin: 0; padding-top: 7px; white-space: pre-line; overflow-wrap: anywhere; }
.hardware-field-row--many .hardware-field { gap: 6px; }
.hardware-field-row--many .field-label { flex-basis: 64px; }
.hardware-field-content { flex: 1 1 0; min-width: 0; }
.hardware-field-content .detail-value { white-space: pre-line; overflow-wrap: anywhere; min-height: 32px; padding-top: 5px; }
.hardware-field-content .field-input { width: 100%; }
@media (max-width: 400px) {
  .hardware-field { gap: 6px; }
  .hardware-field .field-label { flex-basis: 68px; }
}
.hardware-field--stacked { flex-direction: column; gap: 4px; }
.hardware-field--stacked .field-label { flex: 0 0 auto; padding-top: 0; }
.hardware-field--stacked .hardware-field-content { flex: 0 0 auto; width: 100%; }
@container (max-width: 440px) {
  .hardware-field-row--many { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@container (max-width: 280px) {
  .hardware-field-row { grid-template-columns: minmax(0, 1fr); }
}
</style>
