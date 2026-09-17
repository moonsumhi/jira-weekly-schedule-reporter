<template>
  <div class="result-identity">
    <router-link
      v-if="row.asset && !row.asset.isDeleted && canViewAsset"
      class="server-name asset-name"
      :to="{ path: '/asset/list', query: { category: '서버', assetId: row.asset.id } }"
      >{{ row.name }}</router-link
    >
    <span v-else class="server-name">{{ row.name }}</span>
    <div class="server-ip">{{ row.ip || 'IP 미등록' }}</div>
    <div class="server-context">
      <span v-if="row.regular" class="regular-label">정기 점검</span>
      <span v-if="row.asset && row.asset.name !== row.name">등록 자산 · {{ row.asset.name }}</span>
      <span v-if="row.record && !row.asset" class="unlinked-label">자산 미연결</span>
      <button
        v-if="row.record && (!row.asset || row.record.mappingState === 'manual')"
        type="button"
        class="mapping-link"
        :disabled="busy"
        @click="emit('mapping', row.record)"
      >
        {{ !canWrite ? '연결 확인' : row.asset ? '연결 변경' : '자산 연결' }}
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import type { ResourceResultRow } from 'src/utils/inspectionResources';
import type { ResourceServer } from 'src/services/inspectionReports';
defineProps<{ row: ResourceResultRow; canViewAsset: boolean; canWrite: boolean; busy: boolean }>();
const emit = defineEmits<{ mapping: [record: ResourceServer] }>();
</script>
<style scoped>
.result-identity {
  min-width: 0;
}
.server-name {
  font-weight: 650;
  color: #24334a;
  text-decoration: none;
  overflow-wrap: anywhere;
}
a.server-name {
  color: var(--q-primary);
}
a.server-name:hover {
  text-decoration: underline;
}
.server-ip {
  font-size: 12px;
  color: #64748b;
  white-space: pre-line;
  margin-top: 4px;
}
.server-context {
  display: flex;
  align-items: center;
  gap: 6px 8px;
  flex-wrap: wrap;
  font-size: 11px;
  color: #64748b;
  margin-top: 7px;
}
.regular-label {
  border: 1px solid #dbe3ed;
  border-radius: 4px;
  padding: 1px 5px;
  line-height: 1.5;
}
.unlinked-label {
  color: #93611e;
}
.mapping-link {
  font: inherit;
  background: none;
  border: 0;
  padding: 0;
  color: var(--q-primary);
  cursor: pointer;
}
.mapping-link:hover {
  text-decoration: underline;
}
.mapping-link:disabled {
  opacity: 0.5;
  cursor: default;
}
.mapping-link:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 3px;
}
</style>
