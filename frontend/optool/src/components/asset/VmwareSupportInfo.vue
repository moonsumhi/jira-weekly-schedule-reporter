<template>
  <div>
    <template v-if="detail">
      <div v-for="item in items" :key="item.label" class="row q-col-gutter-x-md q-mt-sm">
        <div class="col-4 form-field">
          <div class="field-label">{{ item.label }}</div>
          <div class="detail-value"><q-badge :color="item.color" outline>{{ item.status }}</q-badge></div>
        </div>
        <div class="col form-field">
          <div class="field-label">{{ item.dateLabel }}</div>
          <div class="detail-value">{{ item.date || '확인 불가' }}</div>
        </div>
      </div>
    </template>
    <template v-else>
      <div v-for="item in items" :key="item.label" class="eos-banner q-mt-sm" :class="`eos-banner--${item.color}`">
        <span class="eos-item"><span class="eos-item-label">{{ item.label }}</span><strong>{{ item.status }}</strong></span>
        <span class="eos-sep">·</span>
        <span class="eos-item"><span class="eos-item-label">{{ item.dateLabel }}</span><strong>{{ item.date || '확인 불가' }}</strong></span>
      </div>
    </template>
    <div class="text-caption text-grey-7 q-mt-xs">
      <q-icon name="info_outline" size="14px" class="q-mr-xs" />{{ VMWARE_GUIDANCE_NOTE }}
      <a :href="VMWARE_GUIDANCE_SOURCE" target="_blank" rel="noopener noreferrer">공식 기준</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getAutoEos } from 'src/services/eosDetection'
import { eosStatusColor, eosStatusLabel } from 'src/utils/rules/eos'
import { getVmwareGeneralSupportDate, getVmwareGuidanceDate, getVmwareGuidanceStatus, VMWARE_GUIDANCE_NOTE, VMWARE_GUIDANCE_SOURCE } from 'src/services/vmwareLifecycle'
const props = defineProps<{ dist: string; version: string; detail?: boolean }>()
const items = computed(() => {
  const eos = getAutoEos(props.dist, props.version)
  const guidanceDate = getVmwareGuidanceDate(props.dist, props.version)
  const guidance = getVmwareGuidanceStatus(guidanceDate)
  return [
    { label: 'EoS 여부', dateLabel: '일반 지원 종료 일자',
      status: eos ? eosStatusLabel(eos.status) : '확인 불가', color: eos ? eosStatusColor(eos.status) : 'grey',
      date: getVmwareGeneralSupportDate(props.dist, props.version, eos?.date) },
    { label: '기술 가이드 여부', dateLabel: '기술 가이드 종료 일자 (계약 조건부)',
      status: guidance.label, color: guidance.color, date: guidanceDate },
  ]
})
</script>

<style scoped>
.form-field { display: flex; flex-direction: column; min-width: 0; }
.field-label { font-size: 11px; color: #999; margin-bottom: 4px; min-height: 14px; line-height: 14px; }
.detail-value { font-size: 14px; color: #333; border-bottom: 1px solid rgba(0, 0, 0, .08); padding: 5px 2px; min-height: 32px; line-height: 21px; overflow-wrap: anywhere; }
.eos-banner { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 8px 12px; border-radius: 6px; font-size: 13px; }
.eos-banner--positive { background: #e8f5e9; color: #2e7d32; }
.eos-banner--negative { background: #fce4ec; color: #c62828; }
.eos-banner--warning { background: #fff3e0; color: #e65100; }
.eos-banner--grey { background: #f5f5f5; color: #616161; }
.eos-item { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.eos-item-label { font-size: 11px; opacity: .7; }
.eos-sep { opacity: .4; }
</style>
