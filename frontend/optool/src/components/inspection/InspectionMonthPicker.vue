<template>
  <q-field
    :model-value="modelValue"
    outlined
    dense
    label="점검 월"
    stack-label
    :disable="disable"
    :rules="[(v) => /^20\d{2}-(0[1-9]|1[0-2])$/.test(v) || '점검 월을 선택해 주세요.']"
    hide-bottom-space
  >
    <template #control="{ id }">
      <button
        :id="id"
        type="button"
        class="month-trigger"
        :disabled="disable"
        aria-label="점검 월 선택"
        :aria-expanded="open"
        @click="showPicker"
      >
        <span>{{ monthLabel(modelValue) }}</span
        ><q-icon name="calendar_today" size="16px" />
      </button>
    </template>
    <q-popup-proxy
      v-model="open"
      no-parent-event
      anchor="bottom left"
      self="top left"
      class="month-popup"
    >
      <div class="month-picker">
        <div class="row items-center justify-between q-mb-sm">
          <q-btn
            flat
            round
            dense
            icon="chevron_left"
            aria-label="이전 연도"
            :disable="year <= 2000"
            @click="year--"
          />
          <strong>{{ year }}년</strong>
          <q-btn
            flat
            round
            dense
            icon="chevron_right"
            aria-label="다음 연도"
            :disable="year >= 2099"
            @click="year++"
          />
        </div>
        <div class="month-grid">
          <q-btn
            v-for="m in 12"
            :key="m"
            :label="`${m}월`"
            :flat="valueFor(m) !== modelValue"
            :unelevated="valueFor(m) === modelValue"
            :color="valueFor(m) === modelValue ? 'primary' : 'grey-8'"
            :aria-pressed="valueFor(m) === modelValue"
            @click="select(m)"
          />
        </div>
      </div>
    </q-popup-proxy>
  </q-field>
</template>
<script setup lang="ts">
import { ref } from 'vue';
const props = defineProps<{ modelValue: string; disable?: boolean }>();
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();
const open = ref(false),
  year = ref(new Date().getFullYear());
const monthLabel = (value: string) =>
  /^20\d{2}-(0[1-9]|1[0-2])$/.test(value)
    ? `${value.slice(0, 4)}년 ${Number(value.slice(5))}월`
    : '월 선택';
const valueFor = (m: number) => `${year.value}-${String(m).padStart(2, '0')}`;
function showPicker() {
  year.value = Number(props.modelValue.slice(0, 4)) || new Date().getFullYear();
  open.value = true;
}
function select(m: number) {
  emit('update:modelValue', valueFor(m));
  open.value = false;
}
</script>
<style scoped>
.month-trigger {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  text-align: left;
  cursor: pointer;
  padding: 0;
}
.month-trigger:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 3px;
  border-radius: 3px;
}
.month-picker {
  padding: 16px;
  width: 272px;
}
.month-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
</style>
