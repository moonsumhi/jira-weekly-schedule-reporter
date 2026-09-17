<template>
  <q-dialog
    :model-value="modelValue"
    :maximized="$q.screen.lt.sm"
    @update:model-value="emit('update:modelValue', $event)"
    @show="readImageSize"
  >
    <q-card class="inspection-image-preview">
      <header class="image-preview-toolbar">
        <div class="image-preview-title">
          <strong>{{ title }}</strong>
          <small v-if="dimensions">{{ dimensions }}</small>
        </div>
        <q-btn-toggle
          v-model="originalSize"
          flat
          no-caps
          dense
          toggle-color="primary"
          :disable="!ready"
          :options="[
            { label: '화면에 맞춤', value: false },
            { label: '원본 크기', value: true },
          ]"
          aria-label="이미지 표시 크기"
        />
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="이미지 닫기"
          @click="emit('update:modelValue', false)"
        />
      </header>
      <div class="inspection-image-stage" :class="{ original: originalSize }">
        <img
          v-show="!failed"
          ref="imageElement"
          :key="src"
          :src="src"
          :alt="title"
          @load="readImageSize"
          @error="failed = true"
        />
        <div v-if="failed" class="image-preview-error" role="alert">
          이미지를 불러오지 못했습니다.
        </div>
        <q-inner-loading :showing="!ready && !failed" color="primary" />
      </div>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
import { useQuasar } from 'quasar';
const props = defineProps<{ modelValue: boolean; src: string; title: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();
const $q = useQuasar();
const imageElement = ref<HTMLImageElement | null>(null);
const originalSize = ref(false),
  ready = ref(false),
  failed = ref(false),
  dimensions = ref('');
function readImageSize() {
  const image = imageElement.value;
  if (image?.complete && image.naturalWidth) {
    dimensions.value = `${image.naturalWidth} × ${image.naturalHeight}`;
    ready.value = true;
  }
}
watch(
  () => [props.modelValue, props.src],
  () => {
    if (props.modelValue) {
      originalSize.value = false;
      ready.value = false;
      failed.value = false;
      dimensions.value = '';
    }
  },
  { immediate: true },
);
</script>
<style scoped>
.inspection-image-preview {
  width: 94vw;
  max-width: 94vw;
  height: 92vh;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.image-preview-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  flex-shrink: 0;
}
.image-preview-title {
  flex: 1;
  min-width: 0;
}
.image-preview-title strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}
.image-preview-title small {
  color: #7b8798;
  font-size: 12px;
}
.inspection-image-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
  background: #f3f5f8;
}
.inspection-image-stage img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.inspection-image-stage.original img {
  width: auto;
  height: auto;
  max-width: none;
  max-height: none;
}
.image-preview-error {
  display: grid;
  place-items: center;
  height: 100%;
  color: #64748b;
}
@media (max-width: 599px) {
  .inspection-image-preview {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    max-height: 100vh;
    height: 100dvh;
    max-height: 100dvh;
    border-radius: 0;
  }
  .image-preview-toolbar {
    flex-wrap: wrap;
    gap: 8px;
    padding: 10px 12px;
  }
  .image-preview-title {
    flex-basis: calc(100% - 48px);
  }
  .image-preview-toolbar .q-btn-toggle {
    order: 3;
  }
  .inspection-image-stage {
    padding: 8px;
  }
}
</style>
