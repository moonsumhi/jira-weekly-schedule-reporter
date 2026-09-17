<template>
  <q-dialog v-model="open" aria-labelledby="report-review-title" class="screen-only">
    <q-card class="report-review-dialog">
      <header class="review-heading">
        <div>
          <span class="review-eyebrow"><q-icon name="info_outline" size="18px" /> 확인 안내</span>
          <h2 id="report-review-title">누락·미완료 항목</h2>
          <p>{{ report.title }}</p>
        </div>
        <q-btn flat round dense icon="close" aria-label="확인 안내 닫기" v-close-popup />
      </header>
      <div class="review-body">
        <ul class="review-items">
          <li v-for="item in report.snapshot.warnings" :key="item.code">
            <span>{{ item.label }}</span>
            <strong v-if="item.code !== 'no_source'">{{ item.count }}건</strong>
          </li>
        </ul>
        <section v-if="notes.length" class="review-plan">
          <h3>추가 확인 사항</h3>
          <ol>
            <li v-for="note in notes" :key="note.id">{{ note.content }}</li>
          </ol>
        </section>
      </div>
      <footer>
        <q-btn
          v-if="editable"
          flat
          no-caps
          color="primary"
          label="추가 확인 사항 보기"
          @click="edit"
        />
        <q-space />
        <q-btn unelevated color="primary" label="확인" v-close-popup />
      </footer>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { reportNotes, type InspectionReport } from 'src/services/inspectionReports';
const props = defineProps<{ report: InspectionReport; editable: boolean }>();
const notes = computed(() => reportNotes(props.report));
const open = defineModel<boolean>({ required: true });
const emit = defineEmits<{ edit: [] }>();
function edit() {
  open.value = false;
  emit('edit');
}
</script>

<style scoped>
.report-review-dialog {
  width: 540px;
  max-width: calc(100vw - 32px);
  max-height: calc(100dvh - 48px);
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  color: #34465c;
}
.review-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 24px 24px 18px;
  flex-shrink: 0;
}
.review-eyebrow {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #967542;
  font-size: 12px;
}
h2 {
  margin: 12px 0 8px;
  font-size: 21px;
  font-weight: 650;
  line-height: 1.4;
}
.review-heading p {
  font-size: 12px;
  color: #7b8898;
  margin: 0;
  overflow-wrap: anywhere;
}
.review-body {
  padding: 0 24px 24px;
  overflow-y: auto;
}
.review-items {
  list-style: none;
  padding: 4px 16px;
  margin: 0;
  background: #faf8f3;
  border: 1px solid #ece5d6;
  border-radius: 8px;
}
.review-items li {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 0;
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.review-items li + li {
  border-top: 1px solid #ece5d6;
}
.review-items strong {
  color: #8b6c39;
  white-space: nowrap;
}
.review-plan {
  margin-top: 20px;
}
.review-plan h3 {
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 8px;
}
.review-plan ol {
  margin: 0;
  padding-left: 20px;
}
.review-plan li {
  font-size: 12px;
  color: #778596;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0;
}
footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid #e9edf2;
  flex-shrink: 0;
}
@media (max-width: 599px) {
  .review-heading {
    padding: 20px 18px 16px;
  }
  .review-body {
    padding: 0 18px 20px;
  }
  footer {
    padding: 12px 18px;
  }
  footer .q-btn {
    min-height: 44px;
    font-size: 12px;
  }
}
</style>
