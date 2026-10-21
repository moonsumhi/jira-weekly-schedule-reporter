<template>
  <div class="space-summary" aria-label="현황 요약">
    <div v-for="item in items" :key="item.label" class="space-stat">
      <div class="space-stat__icon" :class="item.tone">
        <q-icon :name="item.icon" size="22px" />
      </div>
      <div>
        <div class="space-stat__label">{{ item.label }}</div>
        <div class="space-stat__value">
          {{ item.value }}<span>{{ item.unit }}</span>
        </div>
      </div>
      <span v-if="item.hint" class="space-stat__hint">{{ item.hint }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  items: {
    label: string;
    value: number;
    unit: string;
    icon: string;
    tone?: string;
    hint?: string;
  }[];
}>();
</script>
