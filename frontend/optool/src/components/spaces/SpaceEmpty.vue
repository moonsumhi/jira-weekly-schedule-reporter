<template>
  <div class="space-empty">
    <div class="space-empty__icon"><q-icon :name="icon" size="32px" /></div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
<script setup lang="ts">
withDefaults(defineProps<{ icon?: string; title: string; description: string }>(), {
  icon: 'search_off',
});
</script>
