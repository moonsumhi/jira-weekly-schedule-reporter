<template>
  <div>
    <div v-if="error" class="text-negative q-mb-sm" role="alert">
      {{ error }} <q-btn flat dense label="다시 불러오기" @click="resolve" />
    </div>
    <AssetLinks v-show="!loading && !error" v-model="assets" :editing="editing" :expanded="!!expanded" :form-style="!!formStyle" :disable="disabled || loading || !!error"
      :label="software ? '연결 서버 (선택)' : '사용하는 서버·자산'" :search-assets="search"
      :fixed-category="software ? '서버' : ''" :asset-noun="software ? '서버' : '자산'"
      :empty-text="software ? '연결된 서버 없음 · 편집에서 나중에 서버를 연결할 수 있습니다.' : '연결된 자산이 없습니다. 편집에서 사용하는 서버·자산을 추가하세요.'"
      :hint="software ? '서버를 연결하지 않아도 등록할 수 있습니다. 여러 서버를 선택하거나, 나중에 연결·해제할 수 있습니다.' : '자산명·관리번호·IP로 검색하세요. 필요하면 자산 유형을 선택해 범위를 좁힐 수 있습니다.'" />
    <q-linear-progress v-if="loading" indeterminate aria-label="연결 자산 불러오는 중" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { api } from 'boot/axios'
import AssetLinks from 'src/components/AssetLinks.vue'
import type { AssetCategory, AssetLink } from 'src/services/assetLinks'
import { detailList } from 'src/utils/assetTypeDetails'
import { getErrorMessage } from 'src/utils/http/error'
const props = defineProps<{ modelValue?: string; editing: boolean; software?: boolean; ownId?: string; disabled?: boolean; expanded?: boolean; formStyle?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const loaded = ref<AssetLink[]>([]), loading = ref(false), error = ref('')
let request = 0
const assets = computed({
  get: () => loaded.value,
  set: (value: AssetLink[]) => { loaded.value = value; emit('update:modelValue', JSON.stringify(value.map(a => a.id))) },
})
async function resolve() {
  const token = ++request
  const ids = detailList(props.modelValue)
  error.value = ''
  if (!ids.length) { loaded.value = []; loading.value = false; return }
  loading.value = true
  try {
    const { data } = await api.post<AssetLink[]>('/assets/linked-assets/resolve', { asset_ids: ids })
    if (request === token) loaded.value = data
  } catch (e) { if (request === token) error.value = getErrorMessage(e, '연결 자산을 불러오지 못했습니다.') }
  finally { if (request === token) loading.value = false }
}
async function search(search: string, category?: AssetCategory) {
  const { data } = await api.get<AssetLink[]>('/assets/linked-assets/search', { params: { search, category } })
  return data.filter(asset => asset.id !== props.ownId)
}
watch(() => props.modelValue, value => {
  // Picker selections already have their display data. Reloading here would
  // disable and close the menu after each selection in a multi-select.
  const ids = detailList(value)
  if (!loading.value && !error.value && ids.join(',') === loaded.value.map(asset => asset.id).join(',')) return
  void resolve()
}, { immediate: true })
onBeforeUnmount(() => { ++request })
</script>
