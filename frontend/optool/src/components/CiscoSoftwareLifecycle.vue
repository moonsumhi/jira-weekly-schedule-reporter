<template>
  <div v-if="visible" class="q-mt-sm">
    <div class="text-weight-medium">설치 Cisco 소프트웨어 — 하드웨어 EoS와 별도</div>
    <div v-if="editable" class="row q-col-gutter-sm q-mt-xs">
      <q-select class="col-6" outlined dense label="소프트웨어" :model-value="product" :options="products"
        @update:model-value="value => emit('change', 'Cisco 소프트웨어', value ?? '')" />
      <q-input class="col-6" outlined dense label="설치 버전" placeholder="예: 5.2(8g)" :model-value="version"
        @update:model-value="value => emit('change', 'Cisco 소프트웨어 버전', String(value ?? ''))" />
    </div>
    <div v-else class="text-caption q-mt-xs">{{ product || '소프트웨어 미지정' }} · {{ version || '버전 미입력' }}</div>
    <div class="text-caption q-mt-xs">
      서비스 종료일: <strong>{{ result?.date || '확인 필요' }}</strong>
      <q-badge v-if="result" class="q-ml-sm" :color="eosStatusColor(result.status)">{{ eosStatusLabel(result.status) }}</q-badge>
      <LifecycleReferenceButton label="소프트웨어 EoS" :entry="result" />
    </div>
    <div v-if="!result?.date" class="text-caption text-grey-8">{{ result?.note || '소프트웨어 종류와 설치 버전을 입력하면 별도로 확인합니다.' }}</div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import LifecycleReferenceButton from 'src/components/asset/LifecycleReferenceButton.vue'
import { getAutoEos } from 'src/services/eosDetection'
import { eosStatusColor, eosStatusLabel } from 'src/utils/rules/eos'
import { NETWORK_EOS_LIST } from 'src/constants/networkEos'
const props = defineProps<{ fields: Record<string, unknown> | undefined; editable?: boolean }>()
const emit = defineEmits<{ change: [key: string, value: string] }>()
const products = ['Cisco APIC', 'Cisco ACI Switch']
const text = (key: string) => {
  const value = props.fields?.[key]
  return typeof value === 'string' ? value : typeof value === 'number' ? String(value) : ''
}
const hardware = computed(() => {
  const normalized = text('운영체제').toLowerCase().replace(/[^a-z0-9]/g, '').replace(/^cisco/, '').replace(/^nexus/, '')
  return NETWORK_EOS_LIST.find(row => row.aliases.includes(normalized))
})
const product = computed(() => text('Cisco 소프트웨어') || (hardware.value?.label.startsWith('APIC-') ? 'Cisco APIC' : ''))
const version = computed(() => text('Cisco 소프트웨어 버전'))
const visible = computed(() => Boolean(product.value || hardware.value?.label.startsWith('Nexus')))
const result = computed(() => product.value ? getAutoEos(product.value, version.value) : null)
</script>
