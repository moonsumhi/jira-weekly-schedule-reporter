<template>
  <div v-if="!record.asset" class="asset-notice">
    <div>
      <span>{{ message }}</span>
      <span v-if="record.candidate" class="candidate"
        >같은 IP로 등록된 자산: {{ record.candidate.name || record.candidate.assetName }}</span
      >
    </div>
    <q-btn
      v-if="canViewAsset"
      flat
      dense
      no-caps
      color="primary"
      label="자산 확인"
      :to="assetRoute"
      target="_blank"
    />
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from 'src/stores/auth';
import type { ResourceServer } from 'src/services/inspectionReports';
const props = defineProps<{ record: ResourceServer }>();
const auth = useAuthStore();
const canViewAsset = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('asset'));
const message = computed(
  () =>
    ({
      ambiguous_hostname: '같은 호스트명이 여러 개 있습니다. 자산과 점검 데이터를 확인해 주세요.',
      hostname_mismatch: '점검 데이터와 자산의 호스트명이 다릅니다.',
      missing_hostname: '점검 데이터에 호스트명이 없습니다.',
      asset_not_found: '이 호스트명으로 등록된 자산이 없습니다.',
    })[props.record.mappingIssue || 'asset_not_found'],
);
const assetRoute = computed(() => ({
  path: '/asset/list',
  query: {
    category: '서버',
    ...(props.record.candidate ? { assetId: props.record.candidate.id } : {}),
  },
}));
</script>
<style scoped>
.asset-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  color: #8a5a1f;
  font-size: 12px;
  margin-top: 4px;
}
.candidate {
  display: block;
  color: #64748b;
}
</style>
