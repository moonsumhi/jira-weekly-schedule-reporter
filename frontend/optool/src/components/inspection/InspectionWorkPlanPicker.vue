<template>
  <div class="inspection-plan-picker">
    <q-input
      v-model="search"
      outlined
      dense
      clearable
      :label="`${documentLabel} 검색`"
      placeholder="작업명 또는 문서 종류"
      :disable="disable"
      debounce="250"
    >
      <template #prepend><q-icon name="search" size="19px" /></template>
      <template #append><q-spinner v-if="loading" size="18px" /></template>
    </q-input>
    <q-checkbox
      v-if="props.assetIds.length"
      v-model="relatedOnly"
      dense
      :label="`선택한 자산의 ${shortLabel}만 보기`"
      class="plan-related"
      :disable="disable"
    />
    <div v-if="error" class="plan-error" role="alert">
      {{ error }}<q-btn flat dense label="다시 불러오기" @click="load" />
    </div>
    <ul v-else class="plan-options" :aria-busy="loading">
      <li v-for="plan in options" :key="plan.id">
        <button
          type="button"
          :disabled="
            disable ||
            chosen(plan.id) ||
            props.disabledIds.includes(plan.id) ||
            selected.length >= props.maxSelection ||
            loading
          "
          @click="add(plan)"
        >
          <div>
            <b>{{ plan.title }}</b
            ><span
              >{{ plan.templateTitle
              }}<template v-if="plan.workDate"> · {{ plan.workDate.slice(0, 10) }}</template></span
            >
            <small v-if="plan.linkedAssets.length">{{
              plan.linkedAssets.map((a) => a.name).join(' · ')
            }}</small>
            <small v-if="props.disabledIds.includes(plan.id)">이미 추가됨</small>
          </div>
          <q-icon :name="chosen(plan.id) ? 'check' : 'add'" size="18px" />
        </button>
      </li>
      <li v-if="!loading && !options.length" class="plan-empty">일치하는 {{ documentLabel }}가 없습니다.</li>
      <li v-if="loading && !options.length" class="plan-empty">{{ documentLabel }}를 불러오는 중입니다.</li>
    </ul>
    <p v-if="hasMore && !error" class="plan-more">
      검색 결과가 더 있습니다. 작업명을 입력해 범위를 좁혀 주세요.
    </p>
    <div v-if="selected.length" class="selected-plans">
      <div class="selected-heading">
        {{ props.maxSelection === 1 ? `선택한 ${documentLabel}` : `연결할 ${shortLabel}` }}
        <b>{{ selected.length }}개</b>
      </div>
      <div v-for="plan in selected" :key="plan.id" class="selected-plan">
        <div class="selected-plan-heading">
          <button
            type="button"
            class="selected-plan-title"
            :disabled="plan.unavailable || disable"
            @click="
              preview = plan;
              previewOpen = true;
            "
          >
            {{ displayWorkPlan(plan).title }}
          </button>
          <q-btn
            flat
            round
            dense
            size="sm"
            icon="close"
            :aria-label="`${displayWorkPlan(plan).title} 연결 해제`"
            :disable="disable"
            @click="remove(plan.id)"
          />
        </div>
        <span class="selected-plan-meta">{{
          plan.unavailable ? '원본 문서를 확인할 수 없습니다.' : displayWorkPlan(plan).templateTitle
        }}</span>
        <q-btn
          v-if="allowApplyAssets && availableAssets(plan).length"
          flat
          dense
          no-caps
          color="primary"
          class="plan-apply-assets"
          :label="`${shortLabel}의 연결 자산 가져오기`"
          :disable="disable"
          @click="emit('assets', availableAssets(plan))"
        />
      </div>
    </div>
    <p v-if="props.maxSelection > 1 && selected.length >= props.maxSelection" class="plan-more">
      {{ shortLabel }}는 최대 {{ props.maxSelection }}개까지 연결할 수 있습니다.
    </p>
  </div>
  <WorkDocumentEntryDialog
    v-if="preview && previewOpen"
    v-model="previewOpen"
    :entry-id="preview.id"
    :title="preview.templateTitle"
    :back-label="`${shortLabel} 선택으로 돌아가기`"
    @saved="load"
  />
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { inspectionError, type InspectionAsset } from 'src/services/inspection';
import {
  displayWorkPlan,
  searchInspectionWorkDocuments,
  type InspectionDocumentKind,
  type InspectionWorkPlan,
} from 'src/services/inspectionWorkPlans';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';
const props = withDefaults(
  defineProps<{
    disable?: boolean;
    assetIds?: string[];
    allowApplyAssets?: boolean;
    maxSelection?: number;
    disabledIds?: string[];
    kind?: InspectionDocumentKind;
  }>(),
  { assetIds: () => [], maxSelection: 20, disabledIds: () => [], kind: 'PLAN' },
);
const documentLabel = computed(() => props.kind === 'RESULT' ? '작업결과서' : '작업계획서');
const shortLabel = computed(() => props.kind === 'RESULT' ? '결과서' : '계획서');
const selected = defineModel<InspectionWorkPlan[]>({ required: true });
const emit = defineEmits<{ assets: [assets: InspectionAsset[]] }>();
const search = ref<string | null>(''),
  relatedOnly = ref(false),
  options = ref<InspectionWorkPlan[]>([]);
const loading = ref(false),
  error = ref(''),
  hasMore = ref(false);
const preview = ref<InspectionWorkPlan | null>(null),
  previewOpen = ref(false);
let request = 0;
const chosen = (id: string) => selected.value.some((plan) => plan.id === id);
const add = (plan: InspectionWorkPlan) => {
  if (
    !chosen(plan.id) &&
    !props.disabledIds.includes(plan.id) &&
    selected.value.length < props.maxSelection
  )
    selected.value = [...selected.value, plan];
};
const remove = (id: string) => {
  selected.value = selected.value.filter((plan) => plan.id !== id);
};
const availableAssets = (plan: InspectionWorkPlan): InspectionAsset[] =>
  displayWorkPlan(plan)
    .linkedAssets.filter((asset) => !asset.isDeleted)
    .map((asset) => ({ ...asset, status: '' }));
async function load() {
  const token = ++request;
  loading.value = true;
  error.value = '';
  try {
    const result = await searchInspectionWorkDocuments(
      props.kind,
      search.value || '',
      relatedOnly.value ? props.assetIds : [],
    );
    if (token !== request) return;
    options.value = result.items;
    hasMore.value = result.hasMore;
  } catch (e) {
    if (token === request) {
      error.value = inspectionError(e);
      options.value = [];
    }
  } finally {
    if (token === request) loading.value = false;
  }
}
watch(
  [search, relatedOnly, () => props.assetIds.join(','), () => props.kind],
  () => {
    void load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  ++request;
});
</script>
<style scoped>
.inspection-plan-picker {
  min-width: 0;
}
.plan-related {
  margin-top: 12px;
  font-size: 12px;
  color: #64788e;
}
.plan-options {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #e2e8ef;
  border-radius: 7px;
}
.plan-options li + li {
  border-top: 1px solid #edf0f4;
}
.plan-options button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  border: 0;
  background: none;
  color: #344e69;
  padding: 12px;
  text-align: left;
  cursor: pointer;
}
.plan-options button:hover:not(:disabled) {
  background: #f3f7fb;
}
.plan-options button:disabled {
  cursor: default;
  opacity: 0.55;
}
.plan-options b {
  display: block;
  font-size: 12px;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.plan-options span,
.plan-options small {
  display: block;
  color: #78899b;
  font-size: 11px;
  margin-top: 4px;
  overflow-wrap: anywhere;
}
.plan-empty,
.plan-error {
  padding: 14px;
  font-size: 12px;
  color: #7c8999;
}
.plan-error {
  color: #a34e46;
}
.plan-more {
  color: #7a8898;
  font-size: 11px;
  margin: 8px 0;
}
.selected-plans {
  margin-top: 18px;
}
.selected-heading {
  font-size: 12px;
  color: #536c85;
  margin-bottom: 8px;
}
.selected-heading b {
  margin-left: 6px;
}
.selected-plan {
  padding: 10px 12px;
  border: 1px solid #dce6f1;
  border-radius: 7px;
  background: #f7fafe;
  margin-top: 8px;
}
.selected-plan-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.selected-plan-title {
  border: 0;
  padding: 0;
  background: none;
  color: #38648d;
  font: inherit;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.selected-plan-title:hover:not(:disabled) {
  text-decoration: underline;
}
.selected-plan-title:disabled {
  color: #8994a2;
  cursor: default;
}
.selected-plan-meta {
  display: block;
  color: #7a8b9e;
  font-size: 11px;
}
.plan-apply-assets {
  margin-top: 6px;
  font-size: 11px;
}
</style>
