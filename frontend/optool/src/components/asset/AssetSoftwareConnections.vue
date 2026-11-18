<template>
  <section class="software-connections q-mt-lg" :aria-busy="loading || !!savingId">
    <div class="software-header q-mb-sm">
      <h3>연결된 소프트웨어<span v-if="!loading && !error" class="software-count">{{ items.length }}</span></h3>
      <div class="row items-center no-wrap">
        <q-btn flat round dense icon="refresh" :loading="loading" :disable="busy" aria-label="연결된 소프트웨어 새로고침" @click="load" />
        <q-btn v-if="canManage && !adding" flat dense no-caps class="software-add" icon="add" label="소프트웨어 연결"
          :disable="busy || loading || !!error" @click="startAdding" />
      </div>
    </div>
    <q-form v-if="adding && canManage" class="software-picker q-mb-md" @submit="connectSelected">
      <q-select ref="picker" v-model="selected" outlined dense use-input clearable :input-debounce="250"
        :options="options" :option-label="softwareName" :option-disable="isConnected" :disable="busy"
        label="연결할 소프트웨어" placeholder="제품명·관리명·자산번호 검색" class="software-select"
        @filter="filterSoftware" @filter-abort="cancelSearch">
        <template #option="scope">
          <q-item v-bind="scope.itemProps">
            <q-item-section>
              <q-item-label>{{ softwareName(scope.opt) }}</q-item-label>
              <q-item-label caption>{{ softwareDetails(scope.opt) }}</q-item-label>
            </q-item-section>
            <q-item-section v-if="isConnected(scope.opt)" side><span class="text-caption">연결됨</span></q-item-section>
          </q-item>
        </template>
        <template #no-option>
          <q-item><q-item-section class="text-caption" :class="searchError ? 'text-negative' : 'text-grey-7'">
            {{ searchError || '검색 결과가 없습니다. 다른 제품명·관리명·자산번호로 검색해 주세요.' }}
          </q-item-section></q-item>
        </template>
        <template #after-options>
          <q-item v-if="options.length === 100"><q-item-section class="text-caption">최대 100개까지 표시됩니다. 검색어를 입력해 범위를 좁혀 주세요.</q-item-section></q-item>
        </template>
      </q-select>
      <div class="software-picker-actions">
        <q-btn flat no-caps label="취소" :disable="!!savingId" @click="cancelAdding" />
        <q-btn unelevated no-caps color="primary" label="연결" type="submit" :loading="!!savingId" :disable="busy || !selected || isConnected(selected)" />
      </div>
    </q-form>
    <p v-if="mutationError" class="text-negative text-caption" role="alert">{{ mutationError }}</p>
    <div v-if="error" class="text-negative q-mb-sm" role="alert">
      {{ error }} <q-btn flat dense label="다시 불러오기" @click="load" />
    </div>
    <q-linear-progress v-else-if="loading" indeterminate aria-label="연결된 소프트웨어 불러오는 중" />
    <q-list v-else-if="items.length" separator class="software-list">
      <q-item v-for="item in items" :key="item.id">
        <q-item-section>
          <button type="button" class="software-open" :disabled="busy" @click="openSoftware(item)">
            <span class="software-name">{{ softwareName(item) }}<q-icon name="chevron_right" size="16px" /></span>
            <span class="software-description">{{ softwareDetails(item) }}</span>
          </button>
        </q-item-section>
        <q-item-section v-if="canManage" side>
          <q-btn flat dense no-caps label="연결 해제" :aria-label="`${softwareName(item)} 연결 해제`"
            :disable="busy || loading" :loading="savingId === item.id" @click="changeLink(item, false)" />
        </q-item-section>
      </q-item>
    </q-list>
    <p v-else class="software-empty">연결된 소프트웨어가 없습니다.</p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { QSelect, useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAuthStore } from 'src/stores/auth'
import { searchSoftware, setServerSoftwareLink } from 'src/services/assets'
import type { ServerAsset } from 'src/types/assets'
import { getErrorMessage } from 'src/utils/http/error'
const props = defineProps<{ assetId: string; category: string; disabled?: boolean; assetDeleted?: boolean }>()
const emit = defineEmits<{ navigate: []; updated: [software: ServerAsset] }>()
const router = useRouter(), auth = useAuthStore(), $q = useQuasar()
const items = ref<ServerAsset[]>([]), loading = ref(false), error = ref('')
const adding = ref(false), selected = ref<ServerAsset | null>(null), options = ref<ServerAsset[]>([])
const savingId = ref(''), mutationError = ref(''), searchError = ref('')
const picker = ref<QSelect>()
const canManage = computed(() => !props.assetDeleted && !!(auth.me?.isAdmin || auth.me?.permissions?.includes('asset')))
const busy = computed(() => !!props.disabled || !!savingId.value)
let request = 0, searchRequest = 0, context = 0
function fieldText(value: unknown) { return typeof value === 'string' || typeof value === 'number' ? String(value) : '' }
function softwareName(item: ServerAsset | null) { return item?.name || fieldText(item?.fields['서버명']) || fieldText(item?.fields['운영체제']) || '소프트웨어' }
function softwareDetails(item: ServerAsset) {
  return [item.fields['운영체제'], item.fields['version'], item.fields['에디션'], item.assetNo || item.fields['자산번호']].map(fieldText).filter(Boolean).join(' · ')
}
function isConnected(item: ServerAsset) { return items.value.some(existing => existing.id === item.id) }
async function load() {
  if (savingId.value) return
  const token = ++request
  loading.value = true; error.value = ''; mutationError.value = ''
  try {
    const { data } = await api.get<ServerAsset[]>(`/assets/${props.assetId}/software`, { params: { category: props.category } })
    if (token === request) items.value = data
  } catch (e) { if (token === request) error.value = getErrorMessage(e, '연결된 소프트웨어를 불러오지 못했습니다.') }
  finally { if (token === request) loading.value = false }
}
async function startAdding() {
  adding.value = true; mutationError.value = ''
  await nextTick()
  picker.value?.focus()
  picker.value?.showPopup()
}
function cancelSearch() { ++searchRequest }
function cancelAdding() {
  adding.value = false; selected.value = null; searchError.value = ''; mutationError.value = ''
  ++searchRequest
}
async function filterSoftware(value: string, update: (fn: () => void) => void) {
  const token = ++searchRequest
  searchError.value = ''
  try {
    const result = await searchSoftware(value)
    if (token === searchRequest) update(() => { options.value = result })
  } catch (e) {
    if (token === searchRequest) update(() => {
      options.value = []
      searchError.value = getErrorMessage(e, '소프트웨어를 검색하지 못했습니다. 검색어를 다시 입력해 주세요.')
    })
  }
}
function connectSelected() { if (selected.value) void changeLink(selected.value, true) }
async function changeLink(item: ServerAsset, linked: boolean) {
  if (busy.value || loading.value || !canManage.value) return
  const token = context
  savingId.value = item.id; mutationError.value = ''
  try {
    const software = await setServerSoftwareLink(props.assetId, item.id, linked, props.category)
    emit('updated', software)
    if (token !== context) return
    items.value = items.value.filter(existing => existing.id !== software.id)
    if (linked) items.value = [...items.value, software].sort((a, b) => softwareName(a).localeCompare(softwareName(b), 'ko'))
    cancelAdding()
    $q.notify({ type: 'positive', message: linked ? '소프트웨어가 연결되었습니다.' : '소프트웨어 연결이 해제되었습니다.' })
  } catch (e) {
    if (token === context) mutationError.value = getErrorMessage(e, '소프트웨어 연결을 변경하지 못했습니다. 다시 시도해 주세요.')
  } finally { if (token === context) savingId.value = '' }
}
function openSoftware(item: ServerAsset) {
  if (busy.value) return
  emit('navigate')
  void router.push({ path: '/asset/list', query: { category: '소프트웨어', assetId: item.id } })
}
watch(() => [props.assetId, props.category], () => {
  ++context; items.value = []; savingId.value = ''; cancelAdding(); void load()
}, { immediate: true })
onBeforeUnmount(() => { ++request; ++searchRequest; ++context })
</script>

<style scoped>
.software-connections { padding-top: 20px; border-top: 1px solid var(--bo-border, #e4e7ec); }
.software-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
h3 { margin: 0; font-size: 14px; line-height: 1.5; font-weight: 650; }
.software-add, .software-count { color: var(--bo-accent-ink, var(--q-primary)); }
.software-count { margin-left: 8px; font-variant-numeric: tabular-nums; }
.software-empty, .software-description { font-size: 12px; line-height: 1.7; color: var(--bo-muted, #667085); }
.software-empty { padding: 16px 0; }
.software-picker { display: flex; align-items: start; gap: 8px; flex-wrap: wrap; }
.software-select { flex: 1 1 240px; min-width: 0; }
.software-picker-actions { display: flex; gap: 4px; margin-left: auto; }
.software-open { display: block; width: 100%; padding: 0; border: 0; border-radius: 4px; background: transparent; color: inherit; font: inherit; text-align: left; cursor: pointer; overflow-wrap: anywhere; }
.software-open:hover .software-name { color: var(--bo-accent-ink, var(--q-primary)); }
.software-open:focus-visible { outline: 2px solid var(--bo-accent-ink, var(--q-primary)); outline-offset: 4px; }
.software-open:disabled { opacity: .6; cursor: default; }
.software-name { display: block; font-weight: 550; }
.software-description { display: block; margin-top: 4px; }
.software-list .q-item { padding: 12px 0; }
:global(.body--dark) .software-connections { --bo-border: #3b4554; --bo-muted: #b7c0cd; }
</style>
