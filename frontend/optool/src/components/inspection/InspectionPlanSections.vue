<template>
  <section id="report-resources" class="plan-section">
    <header class="plan-heading">
      <div>
        <span>01</span>
        <h2>자원 점검 계획</h2>
      </div>
      <b>{{ targets.length }}대</b>
    </header>
    <div class="check-list">
      <div class="check-heading">
        <h3>확인할 항목</h3>
        <q-btn
          v-if="editable"
          flat
          dense
          color="primary"
          icon="edit"
          label="수정"
          class="screen-only"
          @click="emit('edit')"
        />
      </div>
      <ul v-if="checks.length">
        <li v-for="(check, index) in checks" :key="index">{{ check }}</li>
      </ul>
      <p v-else class="muted">점검 항목이 작성되지 않았습니다.</p>
    </div>
    <table v-if="targets.length" class="target-table">
      <thead>
        <tr>
          <th>대상 서버</th>
          <th>IP 주소</th>
          <th>자산명</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="asset in targets" :key="asset.id">
          <td>
            <router-link
              v-if="canOpenAsset && !asset.isDeleted"
              :to="{ path: '/asset/list', query: { category: '서버', assetId: asset.id } }"
              target="_blank"
              class="screen-only"
              >{{ asset.name }}</router-link
            ><b :class="{ 'print-only': canOpenAsset && !asset.isDeleted }">{{ asset.name }}</b
            ><small v-if="asset.isDeleted">삭제된 자산</small>
          </td>
          <td>{{ asset.ip || '—' }}</td>
          <td>{{ asset.assetName || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="muted">등록된 정기 자원 점검 대상이 없습니다.</p>
  </section>
  <section id="report-tasks" class="plan-section">
    <header class="plan-heading">
      <div>
        <span>02</span>
        <h2>월간 작업 계획</h2>
      </div>
      <b>{{ report.snapshot.tasks.length }}건</b>
    </header>
    <p v-if="!report.snapshot.tasks.length" class="muted">등록된 월간 작업이 없습니다.</p>
    <article
      v-for="(task, index) in report.snapshot.tasks"
      :key="task.issueId"
      class="planned-task"
    >
      <div class="task-heading">
        <span class="task-number">{{ String(index + 1).padStart(2, '0') }}</span>
        <div>
          <small>{{ task.issue.key }}</small
          ><button
            v-if="!task.issueDeleted"
            class="task-title screen-only"
            @click="emit('issue', task)"
          >
            {{ task.issue.title }}
          </button>
          <h3 :class="{ 'print-only': !task.issueDeleted }">{{ task.issue.title }}</h3>
        </div>
      </div>
      <dl>
        <div>
          <dt>대상 자산</dt>
          <dd>
            {{ task.common ? '전체 공통' : task.assets.map((a) => a.name).join(' · ') || '미정' }}
          </dd>
        </div>
        <div>
          <dt>담당자</dt>
          <dd>{{ task.issue.assigneeName || '미정' }}</dd>
        </div>
        <div>
          <dt>예정일</dt>
          <dd>
            {{ plannedDate(task)
            }}<span v-if="!task.plannedStart && !task.plannedEnd && report.plannedTime">
              · {{ report.plannedTime }}</span
            >
          </dd>
        </div>
      </dl>
      <InspectionWorkPlanLinks :plans="task.workPlans" back-label="점검 계획서로 돌아가기" />
    </article>
  </section>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from 'stores/auth';
import type { InspectionReport, ReportTask } from 'src/services/inspectionReports';
import InspectionWorkPlanLinks from './InspectionWorkPlanLinks.vue';
const props = defineProps<{ report: InspectionReport; editable: boolean }>();
const emit = defineEmits<{ edit: []; issue: [task: ReportTask] }>();
const auth = useAuthStore();
const canOpenAsset = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('asset'));
const targets = computed(() => props.report.snapshot.resourceTargets || []);
const checks = computed(() =>
  (props.report.resourceChecks || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean),
);
function plannedDate(task: ReportTask) {
  const start = task.plannedStart?.slice(0, 10),
    end = task.plannedEnd?.slice(0, 10);
  return start && end && start !== end
    ? `${start} ~ ${end}`
    : start || end || props.report.inspectionDate;
}
</script>
<style scoped>
.plan-section {
  padding: 32px 42px;
  border-top: 1px solid #dce4ed;
  scroll-margin-top: 150px;
}
.plan-heading,
.check-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.plan-heading {
  margin-bottom: 20px;
}
.plan-heading span {
  font-size: 11px;
  color: #7389a2;
  letter-spacing: 1px;
}
.plan-heading h2 {
  margin: 4px 0 0;
  font-size: 19px;
  font-weight: 700;
  line-height: 1.5;
}
.plan-heading > b {
  color: #657a93;
  font-size: 13px;
  font-weight: 500;
}
.check-list {
  background: #f5f8fb;
  border-radius: 8px;
  padding: 18px 22px;
  margin-bottom: 22px;
}
h3 {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  font-weight: 650;
}
ul {
  margin: 10px 0 0;
  padding-left: 19px;
  font-size: 13px;
  line-height: 1.9;
}
.target-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}
.target-table th {
  color: #62748b;
  background: #f5f7fa;
  text-align: left;
  font-weight: 600;
}
.target-table td,
.target-table th {
  padding: 12px;
  border-bottom: 1px solid #e6ebf1;
  overflow-wrap: anywhere;
}
.target-table a {
  color: #375f8a;
  text-decoration: none;
  font-weight: 600;
}
.target-table small {
  display: block;
  color: #95613d;
}
.planned-task {
  padding: 22px 0;
  border-bottom: 1px solid #e6ebf1;
  break-inside: avoid;
}
.planned-task:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.task-heading {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.task-number {
  background: #edf2f7;
  color: #5c7593;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 11px;
  flex-shrink: 0;
}
.task-heading small {
  display: block;
  font-size: 10px;
  color: #75869b;
  margin-bottom: 3px;
}
.task-title {
  display: block;
  color: #294c75;
  background: none;
  border: 0;
  padding: 0;
  text-align: left;
  font: inherit;
  font-size: 15px;
  line-height: 1.6;
  font-weight: 650;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.task-title:hover {
  text-decoration: underline;
}
dl {
  margin: 16px 0 0 45px;
  font-size: 12px;
  line-height: 1.8;
}
dl > div {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  gap: 12px;
  margin: 5px 0;
}
dt {
  color: #79889b;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.muted {
  font-size: 12px;
  color: #7c8b9b;
  line-height: 1.8;
}
.print-only {
  display: none;
}
@media (max-width: 700px) {
  .plan-section {
    padding: 26px 20px;
  }
  .check-list {
    padding: 14px;
  }
  .target-table th,
  .target-table td {
    padding: 10px 7px;
    font-size: 11px;
  }
  dl {
    margin-left: 0;
  }
}
@media print {
  .screen-only {
    display: none !important;
  }
  .print-only {
    display: block !important;
  }
  .plan-section {
    padding: 20px 0;
  }
  .plan-heading {
    margin-bottom: 14px;
    break-after: avoid;
  }
  .check-list {
    padding: 12px 16px;
    margin-bottom: 14px;
    break-inside: avoid;
    break-after: avoid;
  }
  .planned-task {
    padding: 14px 0;
  }
  .target-table th,
  .target-table td {
    padding: 9px 10px;
  }
  .target-table {
    break-inside: avoid;
  }
  dl {
    margin-top: 10px;
  }
  dl > div {
    margin: 3px 0;
  }
  thead {
    display: table-header-group;
  }
  tr {
    break-inside: avoid;
  }
}
</style>
