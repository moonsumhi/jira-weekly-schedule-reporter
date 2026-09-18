<template>
  <section v-if="plan && comparison" id="report-plan" class="plan-comparison">
    <header>
      <div>
        <span class="eyebrow">계획 대비 수행 현황</span>
        <h2>{{ plan.title }}</h2>
        <p>
          {{ plan.revision }}차 확정본 · 예정일 {{ plan.inspectionDate
          }}<span v-if="plan.plannedTime"> · {{ plan.plannedTime }}</span>
        </p>
      </div>
      <router-link
        :to="`/inspection/monthly-reports/${plan.id}`"
        target="_blank"
        class="screen-only"
        >계획서 보기 <q-icon name="open_in_new" size="14px"
      /></router-link>
    </header>
    <p v-if="plan.inspectionDate !== report.inspectionDate" class="date-change">
      점검일 변경 · {{ plan.inspectionDate }} → {{ report.inspectionDate }}
    </p>
    <div class="comparison-counts">
      <div>
        <span>계획한 작업</span><b>{{ comparison.planned }}건</b>
      </div>
      <div>
        <span>완료</span><b>{{ comparison.completed }}건</b>
      </div>
      <div>
        <span>미완료 · 미실시 · 이월</span
        ><b>{{ comparison.pending + comparison.omitted + comparison.rolled }}건</b>
      </div>
      <div>
        <span>추가 작업</span><b>{{ comparison.added }}건</b>
      </div>
    </div>
    <div v-if="comparison.changes.length" class="changes">
      <div
        v-for="row in comparison.changes"
        :key="`${row.task.month}:${row.task.issueId}`"
        class="changed-work"
      >
        <div class="change-heading">
          <b>{{ row.task.issue.title }}</b
          ><span>{{
            row.added
              ? '추가 작업'
              : row.status === '미실시' || row.status === '이월'
                ? row.status
                : '계획 변경'
          }}</span>
        </div>
        <p v-if="row.changes.length">{{ row.changes.join(' · ') }}</p>
        <dl v-if="row.planned && row.changes.length">
          <div>
            <dt>계획</dt>
            <dd>{{ describe(row.planned) }}</dd>
          </div>
          <div v-if="row.actual">
            <dt>현재</dt>
            <dd>{{ describe(row.actual) }}</dd>
          </div>
        </dl>
        <p v-if="row.actual?.reason">{{ row.actual.reason }}</p>
        <p v-else-if="!row.actual">결과서에 해당 작업의 수행 기록이 없습니다.</p>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import type { InspectionReport, ReportTask } from 'src/services/inspectionReports';
import { inspectionPlanComparison } from 'src/utils/inspectionPlanComparison';
const props = defineProps<{ report: InspectionReport }>();
const plan = computed(() => props.report.snapshot.plan);
const comparison = computed(() => inspectionPlanComparison(props.report.snapshot));
function describe(task: ReportTask) {
  const start = task.plannedStart?.slice(0, 10),
    end = task.plannedEnd?.slice(0, 10);
  const date = start && end && start !== end ? `${start} ~ ${end}` : start || end || '점검 예정일';
  return [
    task.issue.title,
    task.issue.assigneeName || '담당 미정',
    task.common ? '전체 공통' : task.assets.map((a) => a.name).join(', ') || '대상 미정',
    date,
  ].join(' · ');
}
</script>
<style scoped>
.plan-comparison {
  margin: 32px 42px;
  padding: 24px;
  border: 1px solid #dae4ef;
  border-radius: 10px;
  background: #fbfcfe;
  scroll-margin-top: 150px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.eyebrow {
  color: #627d9c;
  font-size: 11px;
  font-weight: 600;
}
h2 {
  font-size: 16px;
  line-height: 1.5;
  margin: 6px 0;
  font-weight: 650;
}
p {
  font-size: 12px;
  line-height: 1.8;
  margin: 5px 0 0;
  color: #76869a;
}
a {
  white-space: nowrap;
  font-size: 11px;
  color: #456b91;
  text-decoration: none;
}
.comparison-counts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 22px;
}
.comparison-counts span {
  display: block;
  color: #76869a;
  font-size: 10px;
}
.comparison-counts b {
  display: block;
  font-size: 20px;
  font-weight: 650;
  margin-top: 5px;
}
.changes {
  border-top: 1px solid #e1e8f0;
  margin-top: 20px;
  padding-top: 8px;
}
.changed-work {
  padding: 14px 0;
  break-inside: avoid;
}
.change-heading {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.change-heading b {
  font-size: 13px;
  overflow-wrap: anywhere;
}
.change-heading span {
  flex-shrink: 0;
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 4px;
  background: #edf2f8;
  color: #5a7697;
}
dl {
  font-size: 11px;
  line-height: 1.8;
  margin: 8px 0 0;
}
dl > div {
  display: flex;
  gap: 12px;
  margin-top: 3px;
}
dt {
  color: #8492a4;
  flex-shrink: 0;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
}
@media (max-width: 700px) {
  .plan-comparison {
    margin: 26px 20px;
    padding: 16px;
  }
  header {
    flex-direction: column;
    gap: 8px;
  }
  .comparison-counts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media print {
  .plan-comparison {
    margin: 24px 0;
    padding: 16px;
  }
  .comparison-counts {
    margin-top: 14px;
    break-inside: avoid;
    break-after: avoid;
  }
  .changes {
    margin-top: 14px;
    padding-top: 4px;
  }
  .changed-work {
    padding: 10px 0;
  }
  .screen-only {
    display: none !important;
  }
  header {
    break-after: avoid;
  }
}
</style>
