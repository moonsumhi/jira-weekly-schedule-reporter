<template>
  <q-btn flat round dense size="xs" icon="info_outline" class="q-ml-xs" aria-label="EoTG 계약 조건 및 공식 기준">
    <q-menu max-width="320px">
      <div class="q-pa-md text-body2">
        <div>{{ VMWARE_GUIDANCE_NOTE }}</div>
        <a :href="VMWARE_GUIDANCE_SOURCE" target="_blank" rel="noopener noreferrer" class="inline-block q-mt-sm">공식 기준 (PDF)</a>
      </div>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { VMWARE_GUIDANCE_NOTE, VMWARE_GUIDANCE_SOURCE } from 'src/services/vmwareLifecycle'
</script>
