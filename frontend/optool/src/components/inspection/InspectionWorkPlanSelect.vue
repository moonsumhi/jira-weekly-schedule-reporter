<template>
  <div class="inspection-plan-select">
    <q-select
      v-model="selected"
      :options="options"
      :option-label="planLabel"
      :option-disable="(plan: InspectionWorkPlan) => disabledIds.includes(plan.id)"
      use-input
      fill-input
      hide-selected
      clearable
      outlined
      dense
      input-debounce="250"
      label="작업계획서"
      placeholder="작업명 또는 문서 종류로 검색"
      :disable="disable"
      :loading="loading"
      :error="!!selected && disabledIds.includes(selected.id)"
      error-message="이번 달에 이미 추가된 작업계획서입니다."
      hide-bottom-space
      @filter="filterPlans"
    >
      <template #prepend><q-icon name="description" size="19px" /></template>
      <template #option="scope">
        <q-item v-bind="scope.itemProps" class="plan-select-option">
          <q-item-section>
            <q-item-label>{{ scope.opt.title }}</q-item-label>
            <q-item-label caption>{{ planMeta(scope.opt) }}</q-item-label>
            <q-item-label v-if="scope.opt.linkedAssets.length" caption>
              {{
                scope.opt.linkedAssets
                  .map((asset: InspectionWorkPlan['linkedAssets'][number]) => asset.name)
                  .join(' · ')
              }}
            </q-item-label>
          </q-item-section>
          <q-item-section v-if="disabledIds.includes(scope.opt.id)" side>
            <span class="text-caption">이미 추가됨</span>
          </q-item-section>
        </q-item>
      </template>
      <template #no-option>
        <q-item>
          <q-item-section class="text-grey-7">
            {{ error || '일치하는 작업계획서가 없습니다.' }}
            <q-btn
              v-if="error"
              flat
              dense
              no-caps
              color="primary"
              label="다시 불러오기"
              @click="filterPlans(lastSearch, (callback) => callback())"
            />
          </q-item-section>
        </q-item>
      </template>
      <template #after-options>
        <div v-if="hasMore && !error" class="plan-select-more">
          검색 결과가 더 있습니다. 작업명을 입력해 주세요.
        </div>
      </template>
    </q-select>
    <div v-if="selected" class="plan-selected-details">
      <span>{{ planMeta(displayWorkPlan(selected)) }}</span>
      <q-btn
        flat
        dense
        no-caps
        color="primary"
        label="내용 보기"
        icon="open_in_new"
        :disable="disable || selected.unavailable"
        @click="
          preview = selected;
          previewOpen = true;
        "
      />
    </div>
  </div>
  <WorkDocumentEntryDialog
    v-if="preview && previewOpen"
    v-model="previewOpen"
    :entry-id="preview.id"
    :title="preview.templateTitle"
    back-label="점검 작업 추가로 돌아가기"
  />
</template>
<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';
import { inspectionError } from 'src/services/inspection';
import {
  displayWorkPlan,
  searchInspectionWorkPlans,
  type InspectionWorkPlan,
} from 'src/services/inspectionWorkPlans';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';

defineProps<{ disable: boolean; disabledIds: string[] }>();
const selected = defineModel<InspectionWorkPlan | null>({ required: true });
const options = ref<InspectionWorkPlan[]>([]),
  loading = ref(false),
  error = ref(''),
  hasMore = ref(false);
const lastSearch = ref(''),
  preview = ref<InspectionWorkPlan | null>(null),
  previewOpen = ref(false);
const planLabel = (plan: InspectionWorkPlan | null) => (plan ? displayWorkPlan(plan).title : '');
const planMeta = (plan: InspectionWorkPlan) =>
  [plan.templateTitle, plan.workDate?.slice(0, 10)].filter(Boolean).join(' · ');
let request = 0;
async function filterPlans(search: string, update: (callback: () => void) => void) {
  const token = ++request;
  lastSearch.value = search;
  loading.value = true;
  error.value = '';
  try {
    const result = await searchInspectionWorkPlans(search);
    if (token !== request) return;
    update(() => {
      options.value = result.items;
      hasMore.value = result.hasMore;
    });
  } catch (e) {
    if (token !== request) return;
    error.value = inspectionError(e);
    update(() => {
      options.value = [];
      hasMore.value = false;
    });
  } finally {
    if (token === request) loading.value = false;
  }
}
onBeforeUnmount(() => {
  ++request;
});
</script>
<style scoped>
.inspection-plan-select {
  min-width: 0;
}
.plan-selected-details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 8px;
}
.plan-selected-details > span {
  font-size: 11px;
  color: #78899b;
  overflow-wrap: anywhere;
}
.plan-selected-details .q-btn {
  font-size: 12px;
}
.plan-select-option {
  max-width: 560px;
}
.plan-select-option :deep(.q-item__label) {
  white-space: normal;
  overflow-wrap: anywhere;
  line-height: 1.6 !important;
}
.plan-select-more {
  padding: 10px 16px;
  font-size: 12px;
  color: #78899b;
}
</style>
