<template>
  <q-dialog
    :model-value="modelValue"
    :persistent="saving"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="targets-dialog">
      <q-card-section class="row items-center">
        <div>
          <div class="text-h6">정기 점검 서버</div>
          <div class="text-caption text-grey-7">
            매월 점검할 서버를 자산 목록에서 선택해 주세요.
          </div>
        </div>
        <q-space /><q-btn
          flat
          round
          dense
          icon="close"
          aria-label="닫기"
          :disable="saving"
          v-close-popup
        />
      </q-card-section>
      <q-separator />
      <q-card-section>
        <div v-if="loading" class="text-center q-pa-lg">
          <q-spinner color="primary" size="28px" />
        </div>
        <q-banner v-if="error" role="alert" rounded class="bg-red-1 text-negative q-mb-md"
          >{{ error }}
          <template v-if="!ready || conflict" #action
            ><q-btn flat label="다시 불러오기" @click="load"
          /></template>
        </q-banner>
        <template v-if="ready">
          <q-select
            :model-value="null"
            class="target-picker"
            outlined
            dense
            use-input
            hide-selected
            input-debounce="200"
            :options="options"
            :option-label="assetLabel"
            :option-disable="(a) => selected.some((s) => s.id === a.id)"
            label="등록 자산에서 서버 검색"
            :disable="saving || conflict"
            @filter="filterAssets"
            @update:model-value="add"
          >
            <template #option="scope"
              ><q-item v-bind="scope.itemProps"
                ><q-item-section>
                  <q-item-label>{{ scope.opt.name || scope.opt.assetName }}</q-item-label>
                  <q-item-label caption>{{
                    scope.opt.ip || 'IP 미등록'
                  }}</q-item-label> </q-item-section
                ><q-item-section v-if="selected.some((s) => s.id === scope.opt.id)" side
                  >선택됨</q-item-section
                ></q-item
              ></template
            >
            <template #no-option
              ><q-item
                ><q-item-section class="text-grey-7">검색 결과가 없습니다.</q-item-section></q-item
              ></template
            >
          </q-select>
          <div class="text-caption text-grey-7 q-mt-md q-mb-xs">
            선택한 서버 {{ selected.length }}대
          </div>
          <q-list class="selected-targets" separator>
            <q-item v-for="asset in selected" :key="asset.id">
              <q-item-section
                ><q-item-label
                  >{{ asset.name || asset.assetName }}
                  <span v-if="asset.isDeleted" class="text-negative text-caption"
                    >삭제된 자산</span
                  ></q-item-label
                ><q-item-label caption>{{ asset.ip || 'IP 미등록' }}</q-item-label></q-item-section
              >
              <q-item-section side
                ><q-btn
                  flat
                  round
                  dense
                  icon="close"
                  :aria-label="`${asset.name} 대상에서 제외`"
                  :disable="saving || conflict"
                  @click="selected = selected.filter((a) => a.id !== asset.id)"
              /></q-item-section>
            </q-item>
          </q-list>
          <div v-if="!selected.length" class="text-center text-grey-7 q-pa-lg">
            정기 점검할 서버를 선택해 주세요.
          </div>
        </template>
      </q-card-section>
      <q-separator />
      <q-card-actions align="right" class="q-pa-md"
        ><q-btn flat label="취소" :disable="saving" v-close-popup /><q-btn
          unelevated
          color="primary"
          label="선택한 서버 저장"
          :loading="saving"
          :disable="!ready || conflict || selected.some((a) => a.isDeleted)"
          @click="save"
      /></q-card-actions>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import {
  inspectionError,
  searchInspectionAssets,
  type InspectionAsset,
} from 'src/services/inspection';
import { getResourceTargets, saveResourceTargets } from 'src/services/inspectionResources';
defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void; (e: 'saved'): void }>();
const selected = ref<InspectionAsset[]>([]),
  options = ref<InspectionAsset[]>([]);
const loading = ref(true),
  ready = ref(false),
  saving = ref(false),
  conflict = ref(false),
  error = ref('');
let version = 0,
  searchGeneration = 0,
  active = true;
const assetLabel = (a: InspectionAsset) => `${a.name || a.assetName} · ${a.ip || 'IP 미등록'}`;
async function load() {
  loading.value = true;
  ready.value = false;
  error.value = '';
  try {
    const data = await getResourceTargets();
    selected.value = data.assets;
    version = data.version;
    ready.value = true;
    conflict.value = false;
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    loading.value = false;
  }
}
async function filterAssets(value: string, update: (fn: () => void) => void) {
  const generation = ++searchGeneration;
  try {
    const data = await searchInspectionAssets(value, [], '서버');
    if (active && generation === searchGeneration)
      update(() => {
        options.value = data;
      });
  } catch (e) {
    if (active && generation === searchGeneration) {
      update(() => {
        options.value = [];
      });
      error.value = inspectionError(e);
    }
  }
}
function add(asset: InspectionAsset | null) {
  if (!asset || selected.value.some((a) => a.id === asset.id)) return;
  if (selected.value.length >= 500) {
    error.value = '점검 대상은 최대 500대까지 선택할 수 있습니다.';
    return;
  }
  selected.value.push(asset);
}
async function save() {
  saving.value = true;
  error.value = '';
  try {
    await saveResourceTargets(
      version,
      selected.value.map((a) => a.id),
    );
    emit('saved');
    emit('update:modelValue', false);
  } catch (e) {
    error.value = inspectionError(e);
    conflict.value = (e as { response?: { status: number } }).response?.status === 409;
  } finally {
    saving.value = false;
  }
}
onMounted(() => {
  void load();
});
onBeforeUnmount(() => {
  active = false;
  searchGeneration++;
});
</script>
<style scoped>
.targets-dialog {
  width: 580px;
  max-width: calc(100vw - 32px);
}
.selected-targets {
  max-height: 45vh;
  overflow-y: auto;
}
</style>
