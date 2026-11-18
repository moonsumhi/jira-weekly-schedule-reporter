<template>
  <div class="software-fields">
    <AssetFormSection v-if="['all', 'basic'].includes(section)" title="기본 정보">
      <AssetFormFieldGrid v-model="values" :fields="basicFields" :editing="editing" :disabled="disabled" :errors="errors" />
      <details v-if="editing && section === 'all'" class="asset-form-help"><summary>같은 제품이 여러 개라면?</summary><p>같은 제품·버전·계약으로 여러 서버에서 사용하면 한 건을 등록하고 서버를 여러 개 연결하세요. 계약이나 버전이 다르면 별도로 등록하고 관리명으로 구분하세요.</p></details>
    </AssetFormSection>
    <AssetFormSection v-for="group in groups" :key="group.id" :title="group.title" :hint="editing ? group.description : undefined">
      <AssetFormFieldGrid v-model="values" :fields="group.fields" :editing="editing" :disabled="disabled" :errors="errors" />
      <AssetRelatedAssets v-if="group.id === 'usage'" :model-value="values['연결자산'] || ''" :editing="editing"
        software :own-id="ownId || ''" :disabled="disabled" form-style expanded @update:model-value="setLinks" />
    </AssetFormSection>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import AssetRelatedAssets from './AssetRelatedAssets.vue'
import AssetFormFieldGrid from './AssetFormFieldGrid.vue'
import AssetFormSection from './AssetFormSection.vue'
import { PERIOD_LICENSES } from 'src/utils/assetTypeDetails'
import { SOFTWARE_PRODUCT, SOFTWARE_EXTRA_PRODUCT, SOFTWARE_LICENSE, SOFTWARE_USAGE, SOFTWARE_PURCHASE, SOFTWARE_FORM_FIELDS, softwareErrors, type SoftwareField } from 'src/utils/softwareAssetForm'
const props = withDefaults(defineProps<{
  modelValue: Record<string, string>; editing?: boolean; disabled?: boolean; ownId?: string;
  section?: 'all' | 'basic' | 'config' | 'usage'; validated?: boolean
}>(), { editing: true, section: 'all' })
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, string>] }>()
const values = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
const errors = computed(() => props.validated ? softwareErrors(values.value) : {})
const known = new Set([...SOFTWARE_FORM_FIELDS.map(f => f.key), '자산유형', '서버명', '연결자산', 'tags', '__ip__', 'eos_action_status', 'eos_date', 'eol_status', 'eol_date'])
const licenseFields = computed(() => SOFTWARE_LICENSE.filter(f => {
  if (f.key === '사용권만료일') return PERIOD_LICENSES.includes(values.value['사용권형태'] || '') || !!values.value[f.key]
  if (['라이선스기준', '라이선스수량', '라이선스식별번호'].includes(f.key)) return !['무상', '오픈소스'].includes(values.value['사용권형태'] || '') || !!values.value[f.key] || !!values.value['라이선스수량']
  return true
}))
const basicFields = computed(() => [
  ...SOFTWARE_PRODUCT.filter(f => !['version', '설명', '자산번호'].includes(f.key)),
  { key: '상태', label: '상태', options: ['운영', '점검', '미사용', '폐기예정', '폐기'] },
  ...SOFTWARE_PRODUCT.filter(f => f.key === '자산번호'),
  ...SOFTWARE_PRODUCT.filter(f => f.key === '설명').map(f => ({ key: f.key, label: f.label, required: !!f.required, placeholder: f.placeholder || '' })),
])
const productFields = [...SOFTWARE_PRODUCT.filter(f => f.key === 'version'), ...SOFTWARE_EXTRA_PRODUCT.filter(f => !['__name__', '상태'].includes(f.key))]
const groups = computed(() => {
  const legacy: SoftwareField[] = Object.keys(values.value).filter(key => !known.has(key) && !key.startsWith('__') && values.value[key]?.trim()).map(key => ({ key, label: key, wide: true }))
  if (values.value['서버명'] && values.value['__name__'] && values.value['서버명'] !== values.value['__name__']) legacy.unshift({ key: '서버명', label: '자산명', wide: true })
  return [
    { id: 'extra', sections: ['all', 'config'], title: '제품 정보', fields: productFields },
    { id: 'license', sections: ['all', 'config'], title: '라이선스·사용 기간', fields: licenseFields.value, description: '보유 수량은 서버 연결 개수와 별개입니다. 오픈소스도 사용권 형태를 기록할 수 있습니다.' },
    { id: 'purchase', sections: ['all', 'config'], title: '도입·유지보수', fields: SOFTWARE_PURCHASE },
    { id: 'legacy', sections: ['all', 'config'], title: '추가 필드', fields: legacy },
    { id: 'usage', sections: ['all', 'usage'], title: '사용처·서버 연결', fields: SOFTWARE_USAGE, description: '이 소프트웨어를 사용하는 서버를 검색해 연결하세요. 서버 연결 없이도 등록할 수 있습니다.' },
  ].filter(g => g.sections.includes(props.section) && (g.id !== 'legacy' || g.fields.length))
})
function setLinks(value: string) { values.value = { ...values.value, '연결자산': value } }
watch(() => values.value['사용권형태'], (value, old) => {
  if (value !== old && value && !PERIOD_LICENSES.includes(value) && values.value['사용권만료일']) values.value = { ...values.value, '사용권만료일': '' }
})
</script>

<style scoped>
:deep(.asset-links) { max-width: none; margin-bottom: 8px; }
.asset-form-help { margin-top: 16px; font-size: 12px; line-height: 1.6; color: var(--bo-muted); }
.asset-form-help summary { cursor: pointer; width: fit-content; }
.asset-form-help summary:focus-visible { outline: 2px solid var(--q-primary); outline-offset: 4px; }
.asset-form-help p { margin: 8px 0 0; }
</style>
