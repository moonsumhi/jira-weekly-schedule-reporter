<template>
  <AssetLinks v-model="assets" class="work-document-assets" :editing="!!editing" :disable="!!disable"
    :search-assets="searchWorkDocumentAssets" hint="자산을 연결하면 해당 자산의 운영 이력에서 이 문서를 확인할 수 있습니다."
    @navigate="emit('navigate')" />
</template>
<script setup lang="ts">
import AssetLinks from './AssetLinks.vue'
import { searchWorkDocumentAssets, type WorkDocumentAsset } from 'src/services/formEntries'
defineProps<{ editing?: boolean; disable?: boolean }>()
const assets = defineModel<WorkDocumentAsset[]>({ required: true })
const emit = defineEmits<{ navigate: [] }>()
</script>
