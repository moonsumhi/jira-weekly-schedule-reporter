<template>
  <ServerAssetLinks v-model="assets" class="work-document-assets" :editing="!!editing" :disable="!!disable"
    :search-assets="searchWorkDocumentAssets" hint="등록된 서버를 연결하면 자산 상세의 운영 이력에서 이 문서를 확인할 수 있습니다."
    @navigate="emit('navigate')" />
</template>
<script setup lang="ts">
import ServerAssetLinks from './ServerAssetLinks.vue'
import { searchWorkDocumentAssets, type WorkDocumentAsset } from 'src/services/formEntries'
defineProps<{ editing?: boolean; disable?: boolean }>()
const assets = defineModel<WorkDocumentAsset[]>({ required: true })
const emit = defineEmits<{ navigate: [] }>()
</script>
