<template>
  <div class="hardware-fields">
    <div v-for="(row, rowIndex) in fieldRows" :key="rowIndex" class="hardware-field-row"
      :class="{ 'hardware-field-row--many': row.length > 2 }" :style="{ '--hardware-grid-columns': systemInfoRowColumns(row) }">
    <div v-for="field in row" :key="field.key" class="hardware-field form-field" :class="{ 'hardware-field--stacked': field.stacked }"
      :data-system-field="`${prefix}.${field.key}`">
      <div class="field-label">{{ field.label }}</div>
      <div class="hardware-field-content">
      <q-select v-if="editing && field.options && !field.allowCustom" :model-value="values[field.key]" :options="field.options"
        borderless dense clearable hide-bottom-space class="field-input" :aria-label="field.label" :disable="disabled"
        @update:model-value="value => change(field, value)" />
      <q-input v-else-if="editing" :model-value="systemInfoFieldValue(field, values) ?? null" :type="field.capacityTextKey ? 'text' : field.type || 'text'"
        borderless dense hide-bottom-space class="field-input" :aria-label="field.label" :disable="disabled"
        :input-class="field.type === 'number' ? 'text-right hardware-number' : undefined"
        :inputmode="field.type === 'number' && !field.capacityTextKey ? field.decimal ? 'decimal' : 'numeric' : undefined"
        :autogrow="field.type === 'textarea'" :rows="field.stacked ? 2 : 1" :placeholder="field.placeholder" :min="field.min" :max="field.max"
        :list="field.allowCustom ? `${prefix}.${field.key}.options` : undefined"
        :step="field.decimal ? 'any' : 1" :maxlength="field.maxLength || 256"
        :error="!!systemInfoFieldError(field, systemInfoFieldValue(field, values))" :error-message="systemInfoFieldError(field, systemInfoFieldValue(field, values))"
        @update:model-value="value => change(field, value)" />
      <datalist v-if="editing && field.allowCustom" :id="`${prefix}.${field.key}.options`">
        <option v-for="option in field.options" :key="option" :value="option" />
      </datalist>
      <div v-else-if="!editing" class="detail-value" :class="{ 'hardware-number text-right': field.type === 'number' }">{{ displayValue(field) }}</div>
      <div v-if="editing && field.hint" class="field-hint text-caption text-grey-6">{{ field.hint }}</div>
      <div v-if="field.bytes && typeof values[field.key] === 'number'" class="text-caption text-grey-6 text-right">{{ formatHardwareBytes(values[field.key]) }}</div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatHardwareBytes, systemInfoFieldError, systemInfoFieldValue, systemInfoRowColumns, updateSystemInfoField, type SystemInfoField, type SystemInfoValues } from 'src/types/assetSystemInfo'
const props = defineProps<{ fields: SystemInfoField[]; rows: string[][]; values: SystemInfoValues; prefix: string; editing: boolean; disabled: boolean }>()
const fieldRows = computed(() => props.rows.map(row => row.map(key => props.fields.find(field => field.key === key))
  .filter((field): field is SystemInfoField => field !== undefined)).filter(row => row.length))
const emit = defineEmits<{ change: [values: SystemInfoValues] }>()
function change(field: SystemInfoField, value: string | number | null) {
  emit('change', updateSystemInfoField(field, props.values, value))
}
function displayValue(field: SystemInfoField) {
  const value = systemInfoFieldValue(field, props.values)
  if (value === null || value === undefined || value === '') return '-'
  return field.capacityTextKey && typeof value === 'number' ? `${value} B` : value
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.hardware-fields { container-type: inline-size; }
.hardware-field-row { display: grid; grid-template-columns: var(--hardware-grid-columns); gap: 8px 16px; }
.hardware-field-row + .hardware-field-row { margin-top: 8px; }
.hardware-field { flex-direction: row; align-items: flex-start; gap: 10px; }
.hardware-field .field-label { flex: 0 0 84px; min-width: 0; margin: 0; padding-top: 7px; white-space: pre-line; overflow-wrap: anywhere; }
.hardware-field-row--many .hardware-field { gap: 6px; }
.hardware-field-row--many .field-label { flex-basis: 64px; }
.hardware-field-content { flex: 1 1 0; min-width: 0; }
.hardware-field-content .detail-value { white-space: pre-line; overflow-wrap: anywhere; min-height: 32px; padding-top: 5px; }
.hardware-field-content .field-input { width: 100%; }
.hardware-number, .field-input :deep(.hardware-number) { font-variant-numeric: tabular-nums; }
.field-hint { line-height: 1.4; padding-top: 4px; overflow-wrap: anywhere; }
@media (max-width: 400px) {
  .hardware-field { gap: 6px; }
  .hardware-field .field-label { flex-basis: 68px; }
}
.hardware-field--stacked { flex-direction: column; gap: 4px; }
.hardware-field--stacked .field-label { flex: 0 0 auto; padding-top: 0; }
.hardware-field--stacked .hardware-field-content { flex: 0 0 auto; width: 100%; }
@container (max-width: 600px) {
  .hardware-field-row--many { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@container (max-width: 420px) {
  .hardware-field-row { grid-template-columns: minmax(0, 1fr); }
}
</style>
