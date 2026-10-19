<template>
  <div class="row q-col-gutter-x-md q-col-gutter-y-md">
    <div v-for="field in fields" :key="field.key" :class="field.wide ? 'col-12 form-field' : 'col-6 form-field'"
      :data-system-field="`${prefix}.${field.key}`">
      <div class="field-label">{{ field.label }}</div>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { systemInfoFieldError, type SystemInfoField, type SystemInfoValues } from 'src/types/assetSystemInfo'
const props = defineProps<{ fields: SystemInfoField[]; values: SystemInfoValues; prefix: string; editing: boolean; disabled: boolean }>()
const emit = defineEmits<{ change: [values: SystemInfoValues] }>()
function change(field: SystemInfoField, value: string | number | null) {
  const next = field.type === 'number' ? (value === '' || value === null ? null : Number(value))
    : field.type === 'date' ? value || null : value ?? ''
  emit('change', { ...props.values, [field.key]: next })
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.form-field { justify-content: flex-end; }
.detail-value { white-space: pre-line; }
</style>
