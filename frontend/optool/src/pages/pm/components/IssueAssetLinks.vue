<template>
  <div class="issue-asset-links">
    <ServerAssetLinks v-if="linked.length" :model-value="linked" :search-assets="searchAssets" hint=""
      @navigate="emit('navigate')" />
    <q-btn flat dense no-caps color="grey-7" :icon="linked.length ? 'edit' : 'dns'"
      :label="linked.length ? '서버 변경' : '작업 대상 서버 연결'" @click="startEdit" />
    <q-dialog :model-value="open" @update:model-value="close">
      <q-card class="issue-assets-editor">
        <q-card-section class="row items-center q-pb-sm">
          <strong>작업 대상 서버</strong><q-space /><q-btn flat round dense icon="close" aria-label="서버 연결 닫기" :disable="saving" @click="close" />
        </q-card-section>
        <q-card-section class="q-pt-none">
          <ServerAssetLinks v-model="selected" editing :search-assets="searchAssets" :disable="saving"
            label="작업 대상 서버 (선택)" hint="연결한 서버의 운영 이력에 이슈가 표시됩니다. 선택을 모두 해제하면 연결이 해제됩니다." />
          <div v-if="error" class="text-negative text-caption" role="alert">{{ error }}</div>
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" :disable="saving" @click="close" />
          <q-btn color="primary" label="저장" :loading="saving" :disable="!changed" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import ServerAssetLinks from 'src/components/ServerAssetLinks.vue'
import { searchIssueAssets, updateIssue, type Issue } from 'src/services/pm/issue'
import type { ServerAssetLink } from 'src/services/assetLinks'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{ issue: Issue }>()
const emit = defineEmits<{ saved: [issue: Issue]; navigate: [] }>()
const $q = useQuasar()
const linked = computed(() => props.issue.linkedAssets || [])
const selected = ref<ServerAssetLink[]>([]), open = ref(false), saving = ref(false), error = ref('')
const ids = (assets: ServerAssetLink[]) => JSON.stringify(assets.map(asset => asset.id).sort())
const initial = ref('[]'), changed = computed(() => ids(selected.value) !== initial.value)
const searchAssets = (search: string) => searchIssueAssets(props.issue.projectId, search)
let request = 0
function startEdit() {
  selected.value = [...linked.value]; initial.value = ids(selected.value); error.value = ''; open.value = true
}
function close() {
  if (saving.value) return
  if (!changed.value) { open.value = false; return }
  $q.dialog({ title: '서버 연결 변경 중', message: '변경 내용을 저장하지 않고 닫으시겠습니까?',
    cancel: { label: '계속 수정', flat: true }, ok: { label: '닫기', color: 'negative' } }).onOk(() => { open.value = false })
}
async function save() {
  if (saving.value || !changed.value) return
  const token = ++request
  saving.value = true; error.value = ''
  try {
    const updated = await updateIssue(props.issue.projectId, props.issue.id, { asset_ids: selected.value.map(asset => asset.id) })
    if (token !== request) return
    emit('saved', updated); open.value = false
    $q.notify({ type: 'positive', message: '작업 대상 서버를 저장했습니다.' })
  } catch (e) {
    if (token === request) error.value = getErrorMessage(e, '서버 연결을 저장하지 못했습니다.')
  } finally { if (token === request) saving.value = false }
}
watch(() => props.issue.id, () => { ++request; open.value = false; saving.value = false })
onBeforeUnmount(() => { ++request })
</script>
<style scoped>
.issue-asset-links { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin: 8px 0 16px; }
.issue-asset-links > .server-asset-links { margin: 0; max-width: 100%; }
.issue-asset-links > .q-btn { font-size: 12px; }
.issue-assets-editor { width: 560px; max-width: calc(100vw - 32px); max-height: 85vh; overflow: auto; }
</style>
