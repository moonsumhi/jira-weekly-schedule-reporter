<template>
  <div class="size-grid-picker">
    <div class="size-grid" @mouseleave="hoverCell = null">
      <div
        v-for="cell in cells"
        :key="`${cell.r}-${cell.c}`"
        class="size-grid-cell"
        :class="{ 'size-grid-cell--active': isActive(cell.r, cell.c) }"
        v-close-popup
        @mouseenter="hoverCell = cell"
        @click="emit('select', cell.c, cell.r)"
      />
    </div>
    <div class="size-grid-label">{{ previewLabel }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{ w: number; h: number }>()
const emit = defineEmits<{ (e: 'select', w: number, h: number): void }>()

const cells = [1, 2, 3].flatMap((r) => [1, 2, 3].map((c) => ({ r, c })))
const hoverCell = ref<{ r: number; c: number } | null>(null)

function isActive(r: number, c: number): boolean {
  const ref_ = hoverCell.value ?? { r: props.h, c: props.w }
  return r <= ref_.r && c <= ref_.c
}

const previewLabel = computed(() => {
  const ref_ = hoverCell.value ?? { r: props.h, c: props.w }
  return `${ref_.c} x ${ref_.r}`
})
</script>

<style scoped>
.size-grid-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px;
}

.size-grid {
  display: grid;
  grid-template-columns: repeat(3, 20px);
  grid-template-rows: repeat(3, 20px);
  gap: 3px;
}

.size-grid-cell {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  background: #f5f7fa;
  border: 1px solid #cfd8dc;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
}

.size-grid-cell--active {
  background: #1e88e5;
  border-color: #1e88e5;
}

.size-grid-label {
  font-size: 11px;
  color: #52514e;
}
</style>
