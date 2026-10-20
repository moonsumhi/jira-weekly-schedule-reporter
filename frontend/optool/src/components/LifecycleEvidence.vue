<template>
  <div class="text-caption text-grey-8 q-mt-sm">
    <div><strong>EoS: 서비스 종료</strong> · EoL: 제조사가 명시한 제품·버전 수명 종료</div>
    <div>공식 제공 주체의 지원 범위 기준이며, 기관의 개별 유지보수 계약 만료일과는 다릅니다.</div>
    <div v-for="item in evidence" :key="item.label" class="q-mt-xs">
      <strong>{{ item.label }}</strong>: {{ item.entry.note || item.entry.basis }}
      <div v-if="item.entry.milestone?.date && !item.entry.date" class="q-pl-sm">
        참고 지원 단계: {{ item.entry.milestone.basis }} — {{ item.entry.milestone.date }}
        <a v-if="item.entry.milestone.source" :href="item.entry.milestone.source" target="_blank" rel="noopener noreferrer">공식 근거</a>
      </div>
      <div v-else-if="item.entry.source" class="q-pl-sm">
        {{ item.entry.basis }}
        <a :href="item.entry.source" target="_blank" rel="noopener noreferrer">공식 근거</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import audit from 'src/data/lifecycle_audit.json'
import { softwareEvidence, softwareAliases, type LifecycleEvidence } from 'src/services/lifecycleAudit'
import { resolveDistName, getNetworkEos } from 'src/services/eosDetection'
import { normalizeVmware } from 'src/services/vmwareLifecycle'
const props = defineProps<{ fields: Record<string, unknown> | undefined }>()
const evidence = computed(() => {
  const rawProduct = props.fields?.['운영체제']
  const rawVersion = props.fields?.['version']
  const product = typeof rawProduct === 'string' ? rawProduct : ''
  const version = typeof rawVersion === 'string' ? rawVersion : typeof rawVersion === 'number' ? String(rawVersion) : ''
  const vmware = normalizeVmware(product, version)
  const key = `${vmware?.dist ?? resolveDistName(product)}|${vmware?.version ?? version}`
  const eol = audit.eol as Record<string, LifecycleEvidence>
  const eosEntry = softwareEvidence[key] ?? softwareEvidence[softwareAliases[key] ?? ''] ?? getNetworkEos(product)
  const eolEntry = eol[key] ?? eol[softwareAliases[key] ?? '']
  const result: Array<{label: string; entry: LifecycleEvidence}> = []
  if (eosEntry) result.push({ label: 'EoS 판단 근거', entry: eosEntry })
  if (eolEntry) result.push({ label: 'EoL 판단 근거', entry: eolEntry })
  return result
})
</script>
