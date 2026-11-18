<template>
  <div class="asset-form-field-grid">
    <div v-for="field in fields" :key="field.key" class="form-field" :class="{ 'asset-form-field-wide': field.wide }">
      <div class="field-label">{{ field.label }}<span v-if="editing && field.required" class="text-primary"> *</span></div>
      <template v-if="editing">
        <div class="asset-form-control">
        <q-select v-if="field.type === 'multi'" :model-value="detailList(modelValue[field.key])" :options="field.options || []"
          borderless dense class="field-input" multiple use-chips clearable :aria-label="field.label"
          :disable="disabled" :readonly="field.readonly" :error="!!errors[field.key]" :error-message="errors[field.key]" hide-bottom-space
          @update:model-value="v => set(field.key, JSON.stringify(v || []))" />
        <q-select v-else-if="field.options" :model-value="modelValue[field.key] || null" :options="options(field)"
          :option-label="(value: string) => optionLabel(field, value)" :popup-content-class="field.optionDescriptions ? 'asset-category-options' : undefined"
          borderless dense class="field-input" :clearable="!field.required" :aria-label="field.label" :aria-required="!!field.required"
          :disable="disabled" :readonly="field.readonly" :error="!!errors[field.key]" :error-message="errors[field.key]" hide-bottom-space
          @update:model-value="v => set(field.key, v)">
          <template v-if="field.optionDescriptions" #option="scope">
            <q-item v-bind="scope.itemProps">
              <q-item-section>
                <q-item-label>{{ optionLabel(field, scope.opt) }}</q-item-label>
                <q-item-label v-if="field.optionDescriptions[scope.opt]" caption>{{ field.optionDescriptions[scope.opt] }}</q-item-label>
              </q-item-section>
            </q-item>
          </template>
        </q-select>
        <q-input v-else :model-value="modelValue[field.key] || ''" borderless dense class="field-input"
          :aria-label="field.label" :aria-required="!!field.required" :placeholder="field.placeholder" :type="field.type === 'textarea' ? 'textarea' : field.type === 'date' ? 'date' : field.type === 'number' ? 'number' : 'text'"
          :autogrow="field.type === 'textarea'" :rows="2" :min="field.type === 'number' ? 0 : undefined" :step="field.integer ? 1 : 'any'"
          :disable="disabled" :readonly="field.readonly" :error="!!errors[field.key]" :error-message="errors[field.key]" hide-bottom-space
          @update:model-value="v => set(field.key, v)" />
        <q-select v-if="field.unitKey" :model-value="modelValue[field.unitKey] || 'TB'" :options="CAPACITY_UNITS"
          borderless dense :aria-label="`${field.label} 단위`" class="field-input asset-form-unit" :disable="disabled" :readonly="field.readonly"
          :error="!!errors[field.unitKey]" :error-message="errors[field.unitKey]" hide-bottom-space @update:model-value="v => set(field.unitKey!, v)" />
        </div>
        <p v-if="field.hint" class="asset-form-field-hint">{{ field.hint }}</p>
      </template>
      <template v-else>
        <div class="detail-value">{{ field.type === 'multi' ? detailList(modelValue[field.key]).join(', ') || '-' : optionLabel(field, modelValue[field.key] || '') || '-' }}<template v-if="field.unitKey && modelValue[field.key]">{{ ' ' + (modelValue[field.unitKey] || 'TB') }}</template></div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AssetFormField } from 'src/utils/assetFormFields'
import { CAPACITY_UNITS, detailList } from 'src/utils/assetTypeDetails'
const props = withDefaults(defineProps<{
  modelValue: Record<string, string>; fields: AssetFormField[]; editing?: boolean;
  disabled?: boolean; errors?: Record<string, string>
}>(), { editing: true, errors: () => ({}) })
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string>] }>()
const options = (field: AssetFormField) => [...new Set([...(field.options || []), ...(props.modelValue[field.key] ? [props.modelValue[field.key]!] : [])])]
const optionLabel = (field: AssetFormField, value: string) => field.optionLabels?.[value] ?? value
function set(key: string, value: string | number | null) {
  emit('update:modelValue', { ...props.modelValue, [key]: value == null ? '' : String(value) })
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.asset-form-control { display: flex; align-items: flex-start; gap: 8px; }
.asset-form-control > :first-child { flex: 1; min-width: 0; }
.asset-form-control > .asset-form-unit { flex: 0 0 76px; }
.asset-form-field-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px 24px; }
.asset-form-field-wide { grid-column: 1 / -1; }
.asset-form-field-hint { margin: 6px 0 0; color: var(--bo-muted); font-size: 12px; line-height: 1.6; }
.detail-value { white-space: pre-wrap; }
:global(.asset-category-options .q-item__label--caption) { color: var(--bo-muted, #667085); line-height: 1.5; }
@media (max-width: 480px) { .asset-form-field-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
