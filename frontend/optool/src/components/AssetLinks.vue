<template>
  <div class="asset-links">
    <template v-if="editing">
      <div class="asset-select-fields">
        <q-select v-model="assets" :options="options" multiple use-chips use-input outlined dense
          option-value="id" option-label="name" option-disable="isDeleted" input-debounce="250"
          class="asset-select-input" :label="label || '자산 선택'" placeholder="자산명, 관리번호 또는 IP 검색" :disable="disable"
          :loading="loading"
          :max-values="100" @filter="search">
          <template #prepend><q-icon name="inventory_2" size="19px" /></template>
          <template #option="scope">
            <q-item v-bind="scope.itemProps">
              <q-item-section>
                <q-item-label>{{ scope.opt.name }}</q-item-label>
                <q-item-label caption>{{ description(scope.opt) }}</q-item-label>
              </q-item-section>
            </q-item>
          </template>
          <template #selected-item="scope">
            <q-chip dense removable :disable="disable" :color="scope.opt.isDeleted ? 'grey-3' : 'blue-1'"
              @remove="scope.removeAtIndex(scope.index)">
              {{ scope.opt.name }}{{ scope.opt.isDeleted ? ' (삭제됨)' : '' }}
              <q-tooltip>{{ description(scope.opt) }}</q-tooltip>
            </q-chip>
          </template>
          <template #no-option><q-item><q-item-section class="text-grey-7">{{ error || '검색된 자산이 없습니다.' }}</q-item-section></q-item></template>
        </q-select>
        <q-select v-model="category" :options="categoryOptions" outlined dense emit-value map-options
          class="asset-category-select" label="자산 유형" :disable="disable" @update:model-value="reloadCategory" />
      </div>
      <div class="asset-link-hint" :class="{ 'text-negative': error }" role="status">
        {{ error || hint }}
      </div>
    </template>
    <q-btn v-else-if="assets.length" flat dense no-caps icon="inventory_2" icon-right="expand_more" class="linked-assets-trigger">
      <span class="ellipsis">연결 자산 · {{ assets[0]?.name }}{{ assets.length > 1 ? ` 외 ${assets.length - 1}개` : '' }}</span>
      <q-menu :anchor="$q.screen.lt.sm ? 'bottom middle' : 'bottom left'" :self="$q.screen.lt.sm ? 'top middle' : 'top left'">
        <q-list class="linked-assets-list">
          <q-item-label header>연결된 자산 {{ assets.length }}개</q-item-label>
          <q-item v-for="asset in assets" :key="asset.id" :clickable="!asset.isDeleted && canOpenAsset" @click="openAsset(asset)">
            <q-item-section><q-item-label>{{ asset.name }}</q-item-label><q-item-label caption>{{ description(asset) }}{{ asset.isDeleted ? ' · 삭제된 자산' : '' }}</q-item-label></q-item-section>
            <q-item-section v-if="!asset.isDeleted && canOpenAsset" side><q-icon name="chevron_right" size="18px" /></q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-btn>
    <span v-else class="asset-link-hint"><q-icon name="inventory_2" class="q-mr-xs" />연결된 자산 없음 · 수정 화면에서 연결할 수 있습니다.</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import { assetCategories, type AssetCategory, type AssetLink } from 'src/services/assetLinks'
import { getErrorMessage } from 'src/utils/http/error'
const props = defineProps<{ editing?: boolean; disable?: boolean; label?: string; hint: string; searchAssets: (search: string, category?: AssetCategory) => Promise<AssetLink[]> }>()
const assets = defineModel<AssetLink[]>({ required: true })
const emit = defineEmits<{ navigate: [] }>()
const router = useRouter(), auth = useAuthStore()
const canOpenAsset = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('asset'))
const options = ref<AssetLink[]>([]), error = ref(''), loading = ref(false), searchValue = ref('')
const category = ref<AssetCategory | ''>('')
const categoryOptions = [{ label: '전체 자산', value: '' }, ...assetCategories.map(value => ({ label: value, value }))]
const description = (asset: AssetLink) => [asset.category || '서버', asset.assetName !== asset.name ? asset.assetName : '', asset.ip].filter(Boolean).join(' · ')
let request = 0
async function search(value: string, update: (callback: () => void) => void) {
  const token = ++request
  searchValue.value = value; error.value = ''; loading.value = true
  try {
    const result = await props.searchAssets(value, category.value || undefined)
    if (token !== request) return
    update(() => { options.value = result })
  } catch (e) {
    if (token !== request) return
    error.value = getErrorMessage(e, '자산을 불러오지 못했습니다. 다시 검색해 주세요.')
    update(() => { options.value = [] })
  } finally { if (token === request) loading.value = false }
}
function reloadCategory() {
  options.value = []
  void search(searchValue.value, callback => callback())
}
function openAsset(asset: AssetLink) {
  if (asset.isDeleted || !canOpenAsset.value) return
  emit('navigate')
  void router.push({ path: '/asset/list', query: { category: asset.category || '서버', assetId: asset.id } })
}
onBeforeUnmount(() => { ++request })
</script>

<style scoped>
.asset-links { margin: 16px 0 24px; max-width: 640px; }
.asset-select-fields { display: flex; align-items: flex-start; gap: 8px; }
.asset-select-input { flex: 1; min-width: 0; }
.asset-category-select { flex: 0 0 150px; }
@media (max-width: 599px) {
  .asset-select-fields { flex-direction: column; }
  .asset-select-input, .asset-category-select { width: 100%; flex: auto; }
}
.asset-link-hint { color: #748093; font-size: 12px; line-height: 1.7; margin-top: 7px; }
.linked-assets-trigger { color: #4d6681; max-width: 100%; font-size: 12px; }
.linked-assets-trigger :deep(.q-btn__content) { flex-wrap: nowrap; gap: 7px; }
.linked-assets-list { min-width: 250px; max-width: calc(100vw - 32px); max-height: 300px; overflow: auto; }
.linked-assets-list .q-item__label { overflow-wrap: anywhere; }
</style>
