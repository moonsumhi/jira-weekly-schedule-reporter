<template>
  <q-card-section class="q-py-sm asset-form-section">
    <div class="section-title-row"><span class="section-title">{{ title }}</span></div>
    <div class="section-divider" />
    <p v-if="hint" class="asset-form-section-hint">{{ hint }}</p>
    <div class="q-mt-md"><slot /></div>
  </q-card-section>
</template>

<script setup lang="ts">
defineProps<{ title: string; hint?: string | undefined }>()
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.asset-form-section-hint { margin: 12px 0 0; color: var(--bo-muted); font-size: 12px; line-height: 1.6; }
</style>
