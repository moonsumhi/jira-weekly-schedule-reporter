<template>
  <div @input.capture="onInput">
    <q-input ref="input" v-model="text" dense outlined :maxlength="200"
      placeholder="프로젝트명 · 키 · 설명 · 일감 제목 검색" class="bo-search">
      <template #prepend><q-icon name="search" color="grey-5" /></template>
      <template #append>
        <q-icon v-show="text" name="close" color="grey-5" class="cursor-pointer" @click="clear" />
      </template>
    </q-input>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QInput } from 'quasar'

const emit = defineEmits<{ search: [value: string] }>()
const input = ref<QInput | null>(null)
const text = ref('')
// Keep QInput and its slots isolated from live search-result renders. During
// composition its internal model still holds the last committed text.
function onInput(event: Event) {
  const native = input.value?.nativeEl
  if (native && event.target === native) emit('search', native.value)
}
watch(text, value => emit('search', value))
function clear() {
  text.value = ''
  emit('search', '')
}
defineExpose({ nativeEl: computed(() => input.value?.nativeEl), clear })
</script>
