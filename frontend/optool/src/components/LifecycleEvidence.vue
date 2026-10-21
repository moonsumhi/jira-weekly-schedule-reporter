<template>
  <span>
    <LifecycleReferenceButton label="EoS" :entry="assetLifecycleEvidence(fields, 'eos')" />
    <LifecycleReferenceButton label="EoL" :entry="assetLifecycleEvidence(fields, 'eol')" />
  </span>
</template>
<script setup lang="ts">
import LifecycleReferenceButton from 'src/components/asset/LifecycleReferenceButton.vue'
import { assetLifecycleEvidence } from 'src/services/lifecycleReferences'
defineProps<{ fields: Record<string, unknown> | undefined }>()
</script>
