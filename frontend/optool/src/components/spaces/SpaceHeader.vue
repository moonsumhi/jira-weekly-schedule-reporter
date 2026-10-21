<template>
  <header class="space-header">
    <div class="space-header__intro">
      <slot name="leading" />
      <div class="space-header__heading">
        <div class="space-eyebrow">{{ eyebrow || '인적자원 관리' }}</div>
        <h1>{{ title }}</h1>
        <p v-if="description">{{ description }}</p>
      </div>
    </div>
    <div class="space-header__actions">
      <slot />
      <q-btn
        flat
        round
        icon="refresh"
        aria-label="새로고침"
        :loading="loading"
        @click="$emit('reload')"
        ><q-tooltip>새로고침</q-tooltip></q-btn
      >
    </div>
  </header>
  <q-banner v-if="error" rounded class="bg-red-1 text-negative q-mb-md" role="alert"
    >{{ error
    }}<template #action><q-btn flat label="다시 시도" @click="$emit('reload')" /></template
  ></q-banner>
  <q-linear-progress v-if="loading" indeterminate class="q-mb-md" />
</template>
<script setup lang="ts">
import 'src/css/spaces.scss';
defineProps<{
  title: string;
  eyebrow?: string;
  description?: string;
  error: string;
  loading: boolean;
}>();
defineEmits<{ reload: [] }>();
</script>
