<template>
  <div v-if="!record.asset || record.mappingState === 'manual'" class="exception-mapping">
    <ResourceAssetNotice :record="record" />
    <q-select
      v-if="canWrite"
      :model-value="record.mappingState === 'manual' ? record.asset : null"
      :options="options"
      :option-label="assetLabel"
      option-value="id"
      outlined
      dense
      clearable
      use-input
      input-debounce="200"
      label="연결할 자산"
      :disable="disable"
      @filter="search"
      @update:model-value="(asset) => emit('select', asset)"
    >
      <template #option="scope"
        ><q-item v-bind="scope.itemProps"
          ><q-item-section
            ><q-item-label>{{ scope.opt.name || scope.opt.assetName }}</q-item-label
            ><q-item-label caption>{{ scope.opt.ip || 'IP 미등록' }}</q-item-label></q-item-section
          ></q-item
        ></template
      >
      <template #no-option
        ><q-item
          ><q-item-section class="text-grey-7">{{
            error || '검색 결과가 없습니다. 자산을 선택하지 않아도 점검 결과는 표시됩니다.'
          }}</q-item-section></q-item
        ></template
      >
    </q-select>
    <span v-else-if="record.mappingState === 'manual'" class="text-caption text-grey-7"
      >이번 점검에 연결 · {{ record.asset?.name }}</span
    >
    <div v-if="error" class="text-caption text-negative" role="alert">{{ error }}</div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, onBeforeUnmount } from 'vue';
import { useAuthStore } from 'src/stores/auth';
import {
  inspectionError,
  searchInspectionAssets,
  type InspectionAsset,
} from 'src/services/inspection';
import type { ResourceServer } from 'src/services/inspectionReports';
import ResourceAssetNotice from './ResourceAssetNotice.vue';
defineProps<{ record: ResourceServer; disable?: boolean }>();
const emit = defineEmits<{ select: [asset: InspectionAsset | null] }>();
const auth = useAuthStore();
const canWrite = computed(() => auth.me?.isInternal !== false);
const options = ref<InspectionAsset[]>([]),
  error = ref('');
let generation = 0;
const assetLabel = (a: InspectionAsset) => `${a.name || a.assetName} · ${a.ip || 'IP 미등록'}`;
async function search(value: string, update: (fn: () => void) => void) {
  const request = ++generation;
  error.value = '';
  try {
    const data = await searchInspectionAssets(value);
    if (request === generation)
      update(() => {
        options.value = data;
      });
  } catch (e) {
    if (request === generation) {
      update(() => {
        options.value = [];
      });
      error.value = inspectionError(e);
    }
  }
}
onBeforeUnmount(() => {
  generation++;
});
</script>
<style scoped>
.exception-mapping {
  max-width: 580px;
  margin-top: 6px;
}
.exception-mapping :deep(.asset-notice) {
  margin-bottom: 8px;
}
</style>
