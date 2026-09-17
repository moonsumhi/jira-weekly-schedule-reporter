<template>
  <div class="inspection-target-picker">
    <div class="common-choice">
      <q-toggle v-model="common" label="공통 작업" :disable="disable" color="primary" dense /><span
        >자산을 지정하지 않는 작업</span
      >
    </div>
    <div v-if="common" class="common-empty">
      <q-icon name="layers" size="36px" /><strong>공통 작업은 자산을 선택하지 않습니다.</strong>
      <p>예: 운영 절차 확인, 점검 문서 정리</p>
    </div>
    <template v-else>
      <div class="asset-search">
        <q-input
          v-model="assetSearch"
          outlined
          dense
          clearable
          debounce="250"
          placeholder="자산명, 관리번호 또는 IP 검색"
          aria-label="대상 자산 검색"
          hide-bottom-space
          :disable="disable"
          @update:model-value="loadAssets"
          ><template #prepend><q-icon name="search" size="18px" /></template
        ></q-input>
        <q-select
          v-model="assetCategory"
          :options="categoryOptions"
          outlined
          dense
          emit-value
          map-options
          aria-label="자산 유형"
          :disable="disable"
          @update:model-value="loadAssets"
        />
      </div>
      <div class="asset-results" aria-label="등록된 자산" :aria-busy="assetsLoading">
        <div v-if="assetsLoading" class="asset-loading">
          <q-spinner color="primary" size="22px" /><span>자산을 검색하는 중입니다.</span>
        </div>
        <div v-else-if="assetsError" class="asset-empty">
          <span>{{ assetsError }}</span
          ><q-btn flat color="primary" label="다시 불러오기" @click="loadAssets" />
        </div>
        <template v-else-if="assetOptions.length">
          <q-item
            v-for="a in assetOptions"
            :key="a.id"
            tag="label"
            class="asset-option"
            :class="{ selected: hasAsset(a.id) }"
          >
            <q-item-section side
              ><q-checkbox
                :model-value="hasAsset(a.id)"
                :aria-label="`${a.name} 선택`"
                :disable="disable || (!hasAsset(a.id) && selectedAssets.length >= 100)"
                size="sm"
                @update:model-value="toggleAsset(a)"
            /></q-item-section>
            <q-item-section
              ><q-item-label class="asset-name">{{ a.assetName || a.name }}</q-item-label
              ><q-item-label caption>{{
                [a.category || '서버', a.assetName && a.name !== a.assetName ? a.name : '', a.ip]
                  .filter(Boolean)
                  .join(' · ')
              }}</q-item-label></q-item-section
            >
            <q-item-section v-if="a.status" side
              ><span class="asset-state">{{ a.status }}</span></q-item-section
            >
          </q-item>
        </template>
        <div v-else class="asset-empty">
          <q-icon name="search_off" size="25px" /><span>검색된 자산이 없습니다.</span
          ><small>자산명, 관리번호 또는 IP를 확인해 주세요.</small>
        </div>
      </div>
      <div class="selected-targets">
        <div class="selection-heading">
          <span
            >선택한 자산 <b>{{ selectedAssets.length }}</b></span
          ><q-btn
            v-if="selectedAssets.length"
            flat
            dense
            no-caps
            label="선택 해제"
            :disable="disable"
            @click="selectedAssets = []"
          />
        </div>
        <div v-if="selectedAssets.length" class="selected-chips">
          <q-chip
            v-for="a in selectedAssets"
            :key="a.id"
            removable
            :disable="disable"
            dense
            :color="a.isDeleted ? 'red-1' : 'blue-1'"
            :text-color="a.isDeleted ? 'negative' : 'primary'"
            @remove="toggleAsset(a)"
            >{{ a.name
            }}<q-tooltip>{{
              [a.category || '서버', a.ip, a.isDeleted ? '삭제된 자산' : '']
                .filter(Boolean)
                .join(' · ')
            }}</q-tooltip></q-chip
          >
        </div>
        <p v-else>위 목록에서 작업할 자산을 선택하세요.</p>
        <span v-if="selectedAssets.length >= 100" class="text-caption text-negative"
          >최대 100개까지 선택할 수 있습니다.</span
        >
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import {
  inspectionError,
  searchInspectionAssets,
  inspectionAssetCategories,
  type InspectionAssetCategory,
  type InspectionAsset,
} from 'src/services/inspection';

defineProps<{ disable?: boolean }>();
const common = defineModel<boolean>('common', { required: true });
const selectedAssets = defineModel<InspectionAsset[]>({ required: true });
const assetSearch = ref('');
const assetCategory = ref<InspectionAssetCategory | ''>('');
const categoryOptions = [
  { label: '전체 자산', value: '' },
  ...inspectionAssetCategories.map((category) => ({ label: category, value: category })),
];
const assetOptions = ref<InspectionAsset[]>([]);
const assetsLoading = ref(false);
const assetsError = ref('');
let assetRequest = 0;
const hasAsset = (id: string) => selectedAssets.value.some((a) => a.id === id);
function toggleAsset(a: InspectionAsset) {
  if (hasAsset(a.id)) selectedAssets.value = selectedAssets.value.filter((s) => s.id !== a.id);
  else if (selectedAssets.value.length < 100) selectedAssets.value = [...selectedAssets.value, a];
}
async function loadAssets() {
  const token = ++assetRequest;
  assetsLoading.value = true;
  assetsError.value = '';
  try {
    const options = await searchInspectionAssets(
      assetSearch.value || '',
      [],
      assetCategory.value || undefined,
    );
    if (token === assetRequest) assetOptions.value = options;
  } catch (e) {
    if (token === assetRequest) assetsError.value = inspectionError(e);
  } finally {
    if (token === assetRequest) assetsLoading.value = false;
  }
}
onMounted(loadAssets);
onBeforeUnmount(() => {
  ++assetRequest;
});
</script>
<style scoped>
.asset-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  gap: 8px;
}
@media (max-width: 599px) {
  .asset-search {
    grid-template-columns: minmax(0, 1fr);
  }
}
.common-choice {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 22px 0 18px;
}
.common-choice :deep(.q-toggle__label) {
  font-size: 12px;
  font-weight: 500;
}
.common-choice > span {
  font-size: 11px;
  color: #76889c;
}
.asset-results {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-top: 12px;
  max-height: 236px;
  min-height: 176px;
  overflow-y: auto;
}
.asset-option {
  padding: 12px 12px 12px 8px;
  border-bottom: 1px solid #eff3f7;
  cursor: pointer;
  min-height: 61px;
}
.asset-option:last-child {
  border: 0;
}
.asset-option.selected {
  background: #f1f6fd;
}
.asset-option:hover {
  background: #f7faff;
}
.asset-option :deep(.q-item__section--side) {
  padding-right: 7px;
}
.asset-option :deep(.q-item__label--caption) {
  color: #718399;
  font-size: 10px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.asset-name {
  font-size: 12px;
  font-weight: 500;
  color: #526a84;
  overflow-wrap: anywhere;
}
.asset-state {
  font-size: 10px;
  color: #8696a8;
  background: #f2f5f8;
  border-radius: 4px;
  padding: 2px 5px;
}
.asset-empty,
.asset-loading {
  min-height: 175px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 18px;
  font-size: 12px;
  color: #9baabc;
  text-align: center;
}
.asset-empty small {
  font-size: 10px;
}
.selected-targets {
  margin-top: 16px;
}
.selection-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #9aa7b7;
  min-height: 26px;
}
.selection-heading b {
  color: #6c8bab;
  margin-left: 4px;
}
.selection-heading .q-btn {
  font-size: 10px;
  color: #9aa7b7;
}
.selected-chips {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  max-height: 110px;
  overflow-y: auto;
}
.selected-chips .q-chip {
  font-size: 11px;
  max-width: 100%;
}
.selected-targets p {
  color: #a3aebc;
  font-size: 11px;
  margin: 8px 0 0;
}
.common-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 260px;
  color: #9badbf;
  text-align: center;
}
.common-empty strong {
  font-size: 13px;
  font-weight: 500;
  color: #7189a4;
  margin-top: 18px;
}
.common-empty p {
  font-size: 11px;
  line-height: 1.9;
  margin-top: 10px;
}

@media (max-width: 700px) {
  .asset-results {
    max-height: 205px;
    min-height: 125px;
  }
  .common-empty {
    min-height: 160px;
  }
}
</style>
