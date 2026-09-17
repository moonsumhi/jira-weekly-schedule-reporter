<template>
  <li
    class="task-row"
    :class="{ 'task-row--done': done, 'task-row--closed': task.state !== 'ACTIVE' }"
  >
    <div class="task-main">
      <q-btn
        flat
        round
        dense
        class="complete-button"
        :class="{ 'is-complete': done }"
        :icon="
          task.state === 'ROLLED'
            ? 'forward'
            : task.state === 'EXCLUDED'
              ? 'remove_circle_outline'
              : done
                ? 'check_circle'
                : 'radio_button_unchecked'
        "
        :aria-label="`${task.issue.title}: ${done ? '할 일로 되돌리기' : '완료로 표시'}`"
        :disable="!editable || busy"
        :loading="busy"
        @click="emit('status', done ? 'TODO' : 'DONE')"
      >
        <q-tooltip>{{
          editable ? (done ? '할 일로 되돌리기' : '완료로 표시') : '지난 점검 기록'
        }}</q-tooltip>
      </q-btn>
      <div class="task-copy">
        <button class="task-title" :disabled="task.issueDeleted" @click="emit('open')">
          {{ task.issue.title }}
        </button>
        <div class="task-meta">
          <span class="issue-key">{{ task.issue.key }}</span>
          <button class="result-link" @click="emit('result')">
            {{ task.result?.content ? '결과 보기' : '결과 작성' }}
          </button>
          <span v-if="task.issueDeleted" class="text-negative">{{
            task.sourceType === 'WORK_PLAN' ? '삭제된 작업계획서' : '삭제된 이슈'
          }}</span>
          <span v-else-if="task.state === 'ROLLED'"
            >{{ shortMonth(task.toMonth) }} 점검으로 이월</span
          >
          <span v-else-if="task.state === 'EXCLUDED'">점검 대상에서 제외</span>
          <span v-else-if="task.overdue">{{ shortMonth(task.month) }} 미완료 작업</span>
          <span v-else-if="task.fromMonth">{{ shortMonth(task.fromMonth) }}에서 이월</span>
        </div>
        <div v-if="task.reason" class="task-reason">{{ task.reason }}</div>
        <InspectionWorkPlanLinks :plans="task.workPlans" @updated="emit('work-plans-updated')" />
      </div>
    </div>
    <div class="task-assets">
      <span v-if="task.common" class="common-label"
        ><q-icon name="layers" size="15px" /> 공통 작업</span
      >
      <template v-else>
        <div v-for="a in task.assets.slice(0, 1)" :key="a.id" class="asset-summary">
          <q-icon name="dns" size="15px" />
          <div>
            <router-link v-if="!a.isDeleted && canViewAssets" :to="assetLink(a)">{{
              displayAsset(a).name
            }}</router-link
            ><span v-else>{{ displayAsset(a).name }}</span>
            <div class="asset-ip">
              {{ displayAsset(a).ip }}<span v-if="a.isDeleted"> · 삭제됨</span>
            </div>
          </div>
        </div>
        <q-btn
          v-if="task.assets.length > 1"
          flat
          dense
          no-caps
          class="asset-more"
          :label="`외 ${task.assets.length - 1}대`"
          :aria-label="`${task.issue.title} 대상 서버 정보`"
        >
          <q-menu
            ><q-list class="asset-popover">
              <q-item-label header>대상 서버 {{ task.assets.length }}대</q-item-label>
              <q-item
                v-for="a in task.assets"
                :key="a.id"
                :clickable="!a.isDeleted && canViewAssets"
                :to="!a.isDeleted && canViewAssets ? assetLink(a) : undefined"
              >
                <q-item-section avatar><q-icon name="dns" color="blue-grey-5" /></q-item-section>
                <q-item-section
                  ><q-item-label
                    >{{ displayAsset(a).name }}
                    <span v-if="a.isDeleted" class="text-negative">(삭제됨)</span></q-item-label
                  >
                  <q-item-label caption
                    >{{ displayAsset(a).assetName }} · {{ displayAsset(a).ip }}</q-item-label
                  >
                  <q-item-label
                    v-if="a.current && (a.current.name !== a.name || a.current.ip !== a.ip)"
                    caption
                    >등록 당시 {{ a.name }} · {{ a.ip }} / 현재 {{ a.current.name }} ·
                    {{ a.current.ip }}</q-item-label
                  >
                </q-item-section>
              </q-item>
            </q-list></q-menu
          >
        </q-btn>
      </template>
    </div>
    <div class="task-assignee">
      <span class="assignee-avatar" :class="{ 'is-unassigned': !task.issue.assigneeId }">{{
        task.issue.assigneeId ? task.issue.assigneeName.slice(0, 1) : '—'
      }}</span
      ><span>{{ task.issue.assigneeName }}</span>
    </div>
    <div class="task-status">
      <q-btn
        unelevated
        dense
        no-caps
        class="status-button"
        :class="`status-${task.state === 'ACTIVE' ? task.issue.status.toLowerCase() : 'archived'}`"
        :label="
          task.state === 'ROLLED'
            ? '이월됨'
            : task.state === 'EXCLUDED'
              ? '제외됨'
              : STATUS_LABEL[task.issue.status]
        "
        :disable="!editable || busy"
        :aria-label="`${task.issue.title} 상태 변경`"
        :icon-right="editable ? 'expand_more' : undefined"
      >
        <q-menu
          ><q-list style="min-width: 160px">
            <q-item
              v-for="status in ISSUE_STATUSES"
              :key="status"
              clickable
              v-close-popup
              :active="task.issue.status === status"
              @click="emit('status', status)"
            >
              <q-item-section>{{ STATUS_LABEL[status] }}</q-item-section
              ><q-item-section v-if="status === task.issue.status" side
                ><q-icon name="check" size="16px"
              /></q-item-section>
            </q-item> </q-list
        ></q-menu>
      </q-btn>
    </div>
    <div class="task-actions">
      <q-btn
        v-if="task.state === 'ACTIVE'"
        flat
        round
        dense
        icon="more_horiz"
        :aria-label="`${task.issue.title} 작업 관리`"
        :disable="busy"
      >
        <q-menu
          ><q-list style="min-width: 190px">
            <q-item
              v-if="canLinkPlans && editable && task.sourceType !== 'WORK_PLAN'"
              clickable
              v-close-popup
              @click="emit('work-plans')"
            >
              <q-item-section avatar><q-icon name="description" size="18px" /></q-item-section>
              <q-item-section>작업계획서 연결</q-item-section>
            </q-item>
            <q-item v-if="!pastCompleted" clickable v-close-popup @click="emit('targets')"
              ><q-item-section avatar><q-icon name="dns" size="18px" /></q-item-section
              ><q-item-section>{{
                task.sourceType === 'WORK_PLAN' ? '점검 작업 수정' : '대상 서버 변경'
              }}</q-item-section></q-item
            >
            <q-item
              v-if="!done && !task.issueDeleted"
              clickable
              v-close-popup
              @click="emit('rollover')"
              ><q-item-section avatar><q-icon name="event_repeat" size="18px" /></q-item-section
              ><q-item-section>작업 이월</q-item-section></q-item
            >
            <q-separator /><q-item clickable v-close-popup @click="emit('exclude')"
              ><q-item-section avatar
                ><q-icon name="remove_circle_outline" size="18px" /></q-item-section
              ><q-item-section>점검 대상에서 제외</q-item-section></q-item
            >
          </q-list></q-menu
        >
      </q-btn>
    </div>
  </li>
</template>
<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from 'stores/auth';
import InspectionWorkPlanLinks from './InspectionWorkPlanLinks.vue';
import { thisMonth, type InspectionTask, type InspectionAsset } from 'src/services/inspection';
import { ISSUE_STATUSES, STATUS_LABEL, type IssueStatus } from 'src/services/pm/issue';
const props = defineProps<{ task: InspectionTask; busy: boolean; canViewAssets: boolean }>();
const emit = defineEmits<{
  (e: 'status', value: IssueStatus): void;
  (
    e: 'open' | 'targets' | 'rollover' | 'exclude' | 'result' | 'work-plans' | 'work-plans-updated',
  ): void;
}>();
const auth = useAuthStore();
const canLinkPlans = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('job'));
const done = computed(() => props.task.issue.status === 'DONE');
const pastCompleted = computed(() => props.task.month < thisMonth() && done.value);
const editable = computed(
  () => props.task.state === 'ACTIVE' && !props.task.issueDeleted && !pastCompleted.value,
);
const shortMonth = (month?: string) => (month ? `${Number(month.slice(5))}월` : '');
const displayAsset = (a: InspectionAsset) =>
  props.task.month < thisMonth() || props.task.state !== 'ACTIVE' ? a : a.current || a;
const assetLink = (a: InspectionAsset) => ({
  path: '/asset/list',
  query: { category: '서버', assetId: a.id },
});
</script>
<style scoped>
.result-link {
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  color: #52718e;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.task-row {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 170px 115px 105px 32px;
  gap: 16px;
  align-items: center;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #eef1f5;
  transition: background 0.15s;
}
.task-row:last-child {
  border-bottom: 0;
}
.task-row:hover {
  background: #fafbfd;
}
.task-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}
.complete-button {
  color: #b0bdcc;
  margin-top: -2px;
  flex-shrink: 0;
}
.complete-button:not(:disabled):hover {
  color: #25765e;
}
.complete-button.is-complete {
  color: #348569;
}
.task-copy {
  min-width: 0;
}
.task-title {
  border: none;
  background: transparent;
  padding: 0;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  color: #25364b;
  cursor: pointer;
  text-align: left;
  overflow-wrap: anywhere;
}
.task-title:hover {
  color: var(--q-primary);
  text-decoration: underline;
}
.task-title:disabled {
  color: #7a8797;
  cursor: default;
}
.task-title:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 3px;
}
.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  font-size: 11px;
  color: #748297;
  margin-top: 5px;
}
.issue-key {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.2px;
}
.task-reason {
  font-size: 12px;
  color: #7b8796;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.task-assets {
  font-size: 12px;
  color: #536478;
  min-width: 0;
}
.asset-summary {
  display: flex;
  align-items: flex-start;
  gap: 7px;
}
.asset-summary > .q-icon {
  margin-top: 2px;
  color: #8b99a9;
}
.asset-summary > div {
  min-width: 0;
  overflow-wrap: anywhere;
}
.asset-summary a {
  color: inherit;
  text-decoration: none;
}
.asset-summary a:hover {
  color: var(--q-primary);
  text-decoration: underline;
}
.asset-ip {
  color: #728197;
  font-size: 11px;
  margin-top: 2px;
}
.asset-more {
  font-size: 11px;
  color: #6a7c91;
  min-height: 22px;
  margin-left: 17px;
}
.asset-popover {
  min-width: 270px;
  max-width: 420px;
  max-height: 360px;
  overflow-y: auto;
}
.common-label {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: #8490a0;
}
.task-assignee {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #5c6b7d;
  font-size: 12px;
  min-width: 0;
  overflow-wrap: anywhere;
}
.assignee-avatar {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  background: #edf1f7;
  color: #697d95;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
}
.is-unassigned {
  background: #f3f4f6;
  color: #a0a7b1;
}
.status-button {
  border-radius: 6px;
  font-size: 11px;
  padding: 3px 9px;
  min-height: 28px;
}
.status-button :deep(.q-icon) {
  font-size: 15px;
  margin-left: 4px;
}
.status-backlog,
.status-archived {
  color: #758194;
  background: #f0f2f5;
}
.status-todo {
  color: #577095;
  background: #eef3fb;
}
.status-in_progress {
  color: #a67625;
  background: #fff6e5;
}
.status-implemented {
  color: #746299;
  background: #f3effa;
}
.status-done {
  color: #338269;
  background: #ebf6f0;
}
.task-actions {
  color: #8c99a9;
}
.task-row--closed .task-title {
  color: #7a8797;
}
@media (max-width: 1250px) {
  .task-row {
    grid-template-columns: minmax(200px, 1fr) 140px 90px 100px 28px;
    gap: 10px;
    padding: 18px;
  }
}
@media (max-width: 850px) {
  .task-row {
    grid-template-columns: 1fr auto 32px;
    gap: 12px 8px;
    padding: 18px 16px;
  }
  .task-main {
    grid-column: 1 / 3;
    grid-row: 1;
  }
  .task-actions {
    grid-column: 3;
    grid-row: 1;
    align-self: start;
  }
  .task-assets {
    position: relative;
    padding-right: 20px;
    grid-column: 1 / 3;
    grid-row: 2;
    margin-left: 44px;
  }
  .task-assignee {
    grid-column: 1;
    grid-row: 3;
    margin-left: 44px;
  }
  .task-status {
    grid-column: 2 / 4;
    grid-row: 3;
    justify-self: end;
  }
}
</style>
