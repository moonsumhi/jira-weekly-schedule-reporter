<template>
  <div class="report-action">
    <span
      class="action-state"
      :class="action ? (action.isResolved ? 'resolved' : 'pending') : 'empty'"
    >
      {{ action ? (action.isResolved ? '조치 완료' : '조치 중') : '조치 미등록' }}
    </span>
    <q-btn
      v-if="editable"
      flat
      dense
      no-caps
      color="primary"
      icon="edit"
      size="sm"
      :label="action ? '조치 수정' : '조치 작성'"
      :aria-label="`${hostName} ${action ? '조치 수정' : '조치 작성'}`"
      class="action-edit screen-only"
      @click="emit('edit')"
    />
    <p v-if="sourceNote" class="source-note"><span>점검표 기록</span>{{ sourceNote }}</p>
    <p v-if="action?.memo" class="action-memo">{{ action.memo }}</p>
    <p v-else-if="!sourceNote && !action?.images.length" class="action-empty">
      등록된 조치 내용이 없습니다.
    </p>
    <div v-if="action?.images.length" class="evidence-images">
      <button
        v-for="(img, i) in action.images"
        :key="i"
        type="button"
        class="evidence-image"
        :aria-label="`${hostName} 조치 증빙 ${i + 1} 크게 보기`"
        @click="
          previewImage = img;
          previewOpen = true;
        "
      >
        <img :src="img" :alt="`${hostName} 조치 증빙 ${i + 1}`" />
      </button>
    </div>
    <p v-if="action" class="action-author">
      {{
        [action.actor, action.updatedAt ? reportTime(action.updatedAt) : '']
          .filter(Boolean)
          .join(' · ')
      }}
    </p>
  </div>
  <InspectionImagePreview
    v-model="previewOpen"
    :src="previewImage"
    :title="`${hostName} · 조치 증빙`"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { reportTime, type ReportAction } from 'src/services/inspectionReports';
import { inspectionActionNote } from 'src/utils/inspectionReportResources';
import InspectionImagePreview from './InspectionImagePreview.vue';

const props = defineProps<{
  action?: ReportAction | null;
  actionItems?: string;
  hostName: string;
  editable?: boolean;
}>();
const emit = defineEmits<{ edit: [] }>();
const sourceNote = computed(() => inspectionActionNote(props.actionItems));
const previewImage = ref('');
const previewOpen = ref(false);
</script>

<style scoped>
.report-action {
  min-width: 0;
  font-size: 12px;
  line-height: 1.8;
}
.action-state {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 4px;
}
.action-edit {
  margin-left: 8px;
}
.action-state.pending {
  color: #986c2f;
  background: #fbf4e8;
}
.action-state.resolved {
  color: #477866;
  background: #eef6f1;
}
.action-state.empty {
  color: #7b8999;
  background: #f2f4f7;
}
.action-memo,
.source-note {
  margin: 9px 0 0;
  color: #52657a;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.source-note > span {
  display: block;
  color: #8190a0;
  font-size: 10px;
}
.action-author,
.action-empty {
  color: #7e8c9c;
  font-size: 10px;
  margin: 9px 0 0;
  overflow-wrap: anywhere;
}
.evidence-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.evidence-image {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 140px;
  max-width: 100%;
  height: 110px;
  padding: 5px;
  background: #fff;
  border: 1px solid #e6eaf0;
  border-radius: 4px;
  cursor: zoom-in;
}
.evidence-image:hover {
  border-color: #7c9dbb;
}
.evidence-image:focus-visible {
  outline: 2px solid #397ac1;
  outline-offset: 2px;
}
.evidence-images img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}
@media print {
  .action-edit {
    display: none !important;
  }
  .action-state {
    print-color-adjust: exact;
  }
  .action-memo,
  .source-note {
    orphans: 3;
    widows: 3;
  }
  .evidence-image {
    display: block;
    width: auto;
    height: auto;
    padding: 0;
    border: 0;
    background: none;
    break-inside: avoid;
  }
  .evidence-images img {
    break-inside: avoid;
    max-height: 150mm;
    width: auto;
    max-width: 100%;
  }
}
</style>
