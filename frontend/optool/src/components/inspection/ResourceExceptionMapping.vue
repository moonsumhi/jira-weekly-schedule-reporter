<template>
  <div v-if="!record.asset || record.mappingState === 'manual'" class="exception-mapping">
    <ResourceAssetNotice :record="record" />
    <q-select
      v-if="canWrite"
      v-model="category"
      :options="categoryOptions"
      outlined
      dense
      emit-value
      map-options
      label="자산 유형"
      :disable="disable"
      class="q-mb-sm"
      @update:model-value="refreshOptions"
    />
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
      :loading="loading"
      :disable="disable"
      @filter="search"
      @update:model-value="(asset) => emit('select', asset)"
    >
      <template #option="scope"
        ><q-item v-bind="scope.itemProps"
          ><q-item-section
            ><q-item-label>{{ scope.opt.name || scope.opt.assetName }}</q-item-label
            ><q-item-label caption>{{ assetDetails(scope.opt) }}</q-item-label></q-item-section
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
  inspectionAssetCategories,
  type InspectionAssetCategory,
  type InspectionAsset,
} from 'src/services/inspection';
import type { ResourceServer } from 'src/services/inspectionReports';
import ResourceAssetNotice from './ResourceAssetNotice.vue';
defineProps<{ record: ResourceServer; disable?: boolean }>();
const emit = defineEmits<{ select: [asset: InspectionAsset | null] }>();
const auth = useAuthStore();
const canWrite = computed(() => auth.me?.isInternal !== false);
const options = ref<InspectionAsset[]>([]),
  error = ref(''),
  loading = ref(false),
  category = ref<InspectionAssetCategory | ''>('');
const categoryOptions = [
  { label: '전체 자산', value: '' },
  ...inspectionAssetCategories.map((value) => ({ label: value, value })),
];
let generation = 0;
let searchText = '';
const assetDetails = (a: InspectionAsset) =>
  [a.category || '서버', a.assetName && a.assetName !== a.name ? a.assetName : '', a.ip || 'IP 미등록']
    .filter(Boolean).join(' · ');
const assetLabel = (a: InspectionAsset) => `${a.name || a.assetName} · ${assetDetails(a)}`;
async function search(value: string, update: (fn: () => void) => void) {
  searchText = value;
  await loadOptions((data) => update(() => { options.value = data; }));
}
async function refreshOptions() {
  await loadOptions((data) => { options.value = data; });
}
async function loadOptions(setOptions: (data: InspectionAsset[]) => void) {
  const request = ++generation;
  error.value = '';
  loading.value = true;
  try {
    const data = await searchInspectionAssets(searchText, [], category.value || undefined);
    if (request === generation) setOptions(data);
  } catch (e) {
    if (request === generation) {
      setOptions([]);
      error.value = inspectionError(e);
    }
  } finally {
    if (request === generation) loading.value = false;
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
