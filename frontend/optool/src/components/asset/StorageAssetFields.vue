<template>
  <div class="storage-fields">
    <AssetFormSection v-if="['all', 'basic'].includes(section)" title="기본 정보">
      <AssetFormFieldGrid v-model="values" :fields="basicFields" :editing="editing" :disabled="disabled" :errors="errors" />
    </AssetFormSection>
    <template v-if="['all', 'config'].includes(section)">
      <AssetFormSection title="모델·기종">
        <AssetFormFieldGrid v-model="values" :fields="modelFields" :editing="editing" :disabled="disabled" :errors="errors" />
      </AssetFormSection>
      <AssetFormSection title="용량·구성" hint="사용 가능 용량은 RAID 등을 적용한 전체 용량이며, 현재 남은 공간과 다릅니다." class="storage-capacity">
        <AssetFormFieldGrid v-model="values" :fields="capacityFields" :editing="editing" :disabled="disabled" :errors="errors" />
        <details v-if="editing" class="asset-form-help"><summary>용량 입력 예시</summary><p>2 TB 디스크 12개의 전체 디스크 용량은 24 TB입니다. 사용 가능 용량은 RAID·예비 영역을 적용한 뒤 장비에서 확인한 값을 입력하세요. 모르면 비워두어도 됩니다.</p></details>
      </AssetFormSection>
      <AssetFormSection title="도입·유지보수">
        <AssetFormFieldGrid v-model="values" :fields="STORAGE_PURCHASE" :editing="editing" :disabled="disabled" :errors="errors" />
      </AssetFormSection>
      <AssetFormSection v-if="legacyFields.length" title="추가 필드">
        <AssetFormFieldGrid v-model="values" :fields="legacyFields" :editing="editing" :disabled="disabled" :errors="errors" />
      </AssetFormSection>
    </template>
    <AssetFormSection v-if="['all', 'location'].includes(section)" title="연결 자산" :hint="editing ? '이 스토리지를 사용하는 서버·자산을 검색해 연결하세요. 연결 없이도 등록할 수 있습니다.' : undefined">
      <AssetFormFieldGrid v-model="values" :fields="STORAGE_CONNECTION" :editing="editing" :disabled="disabled" :errors="errors" />
      <AssetRelatedAssets :model-value="values['연결자산'] || ''" :editing="editing" :own-id="ownId || ''" :disabled="disabled" form-style expanded
        @update:model-value="v => values = { ...values, '연결자산': v }" />
    </AssetFormSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AssetFormFieldGrid from './AssetFormFieldGrid.vue'
import AssetFormSection from './AssetFormSection.vue'
import AssetRelatedAssets from './AssetRelatedAssets.vue'
import type { AssetFormField } from 'src/utils/assetFormFields'
import { STORAGE_IDENTITY, STORAGE_CAPACITY, STORAGE_CONNECTION, STORAGE_HARDWARE, STORAGE_PURCHASE, STORAGE_FORM_FIELDS, storageErrors } from 'src/utils/storageAssetForm'
const props = withDefaults(defineProps<{
  modelValue: Record<string, string>; editing?: boolean; disabled?: boolean; ownId?: string;
  section?: 'all' | 'basic' | 'config' | 'location'; validated?: boolean
}>(), { editing: true, section: 'all' })
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string>] }>()
const values = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
const errors = computed(() => props.validated ? storageErrors(values.value) : {})
const identity = (key: string) => STORAGE_IDENTITY.find(f => f.key === key)!
const basicFields: AssetFormField[] = [
  identity('서버명'),
  identity('구분'), { ...identity('상태'), label: '상태' }, identity('자산번호'),
  { key: 'rack_no', label: 'RackNo.', readonly: true, placeholder: '랙 배치 시 자동' },
  { key: 'rack_unit_no', label: 'Rack Unit No.', readonly: true, placeholder: '랙 배치 시 자동' },
  { key: '자산관리번호', label: '자산관리번호' }, { key: 'SN', label: 'SN' },
  { key: '위치', label: '위치', readonly: true, placeholder: '랙 배치로 관리' },
  { key: '설명', label: '용도·설명', required: true, placeholder: identity('설명').placeholder || '' },
]
const modelFields = [identity('운영체제'), ...STORAGE_HARDWARE.filter(f => ['version', '제조사'].includes(f.key))]
const capacityFields = [...STORAGE_CAPACITY, ...STORAGE_HARDWARE.filter(f => !['version', '제조사', 'SN', '자산관리번호'].includes(f.key))]
const known = new Set([...STORAGE_FORM_FIELDS.flatMap(f => [f.key, ...(f.unitKey ? [f.unitKey] : [])]), '자산유형', '서버명', '호스트명', '연결자산', 'tags', '위치', 'rack_no', 'rack_unit_no', 'eos_action_status', 'eos_date', 'eol_status', 'eol_date'])
const legacyFields = computed<AssetFormField[]>(() => Object.keys(values.value)
  .filter(key => !known.has(key) && !key.startsWith('__') && values.value[key]?.trim())
  .map(key => ({ key, label: key, wide: true })))
</script>

<style scoped>
:deep(.asset-links) { max-width: none; margin-bottom: 8px; }
.asset-form-help { margin-top: 16px; font-size: 12px; line-height: 1.6; color: var(--bo-muted); }
.asset-form-help summary { cursor: pointer; width: fit-content; }
.asset-form-help summary:focus-visible { outline: 2px solid var(--q-primary); outline-offset: 4px; }
.asset-form-help p { margin: 8px 0 0; }
</style>
