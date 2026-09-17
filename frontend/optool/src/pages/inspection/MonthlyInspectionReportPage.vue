<template>
  <q-page class="monthly-report-page">
    <div class="report-shell">
      <header class="report-toolbar screen-only">
        <div class="toolbar-left">
          <q-btn
            flat
            round
            dense
            icon="arrow_back"
            :to="
              report
                ? {
                    path: '/inspection/monthly-reports',
                    query: { month: report.month, kind: report.kind || 'RESULT' },
                  }
                : { path: '/inspection/tasks', query: { month } }
            "
            :aria-label="report ? '보고서 목록' : '월간 작업으로 돌아가기'"
          />
          <div>
            <div class="toolbar-eyebrow">
              서버 점검 / {{ report ? formatInspectionMonth(report.month) : '월간 작업' }}
            </div>
            <h1>점검 {{ documentLabel }}</h1>
          </div>
        </div>
        <div v-if="report" class="toolbar-actions">
          <span class="save-status">{{
            report.state === 'FINAL'
              ? `확정된 ${documentLabel}`
              : `저장됨 · ${shortTime(report.updatedAt)}`
          }}</span>
          <div v-if="editable || canWrite" class="report-primary-actions">
            <template v-if="editable">
              <q-btn
                unelevated
                no-caps
                color="primary"
                icon="edit_note"
                :label="`${documentLabel} 내용 수정`"
                class="report-edit-button"
                :disable="busy || loading"
                @click="openEdit"
              />
              <q-btn
                outline
                no-caps
                color="primary"
                :label="`${documentLabel} 확정`"
                :disable="busy || loading"
                @click="finalizeOpen = true"
              />
            </template>
            <q-btn
              v-else
              unelevated
              color="primary"
              icon="edit_note"
              label="수정본 작성"
              :loading="busy"
              :disable="loading"
              @click="makeRevision"
            />
          </div>
          <div class="report-secondary-actions">
            <q-btn
              v-if="report.snapshot.warnings.length"
              flat
              no-caps
              icon="info_outline"
              label="확인할 항목"
              :disable="busy || loading"
              @click="reviewOpen = true"
            />
            <q-btn
              v-if="editable"
              flat
              no-caps
              icon="refresh"
              label="최신 내용 불러오기"
              :disable="busy || loading"
              @click="sourceOpen = true"
            />
            <q-btn
              flat
              no-caps
              icon="print"
              label="인쇄 / PDF"
              :loading="printing"
              :disable="busy || loading"
              @click="printReport"
            />
          </div>
        </div>
        <q-btn
          v-else-if="canWrite"
          unelevated
          color="primary"
          icon="add"
          :label="`${documentLabel} 작성`"
          :disable="loading || !!error"
          @click="sourceOpen = true"
        />
      </header>
      <q-banner v-if="error" class="error-banner screen-only" role="alert"
        >{{ error }}<template #action><q-btn flat label="다시 불러오기" @click="load" /></template
      ></q-banner>
      <div v-if="loading" class="report-loading">
        <q-spinner color="primary" size="30px" />
        <p>보고서를 불러오는 중입니다.</p>
      </div>
      <template v-else-if="report">
        <div class="report-workspace">
          <aside class="report-outline screen-only">
            <div class="outline-status">
              <q-icon
                :name="report.state === 'FINAL' ? 'verified' : 'edit_document'"
                :color="report.state === 'FINAL' ? 'teal-6' : 'blue-grey-5'"
                size="22px"
              />
              <div>
                <b
                  >{{ report.state === 'FINAL' ? '확정본' : '초안' }}
                  <span>{{ report.revision }}차</span></b
                ><small>{{ formatInspectionMonth(report.month) }}</small>
              </div>
            </div>
            <nav aria-label="보고서 목차">
              <button v-for="s in sections" :key="s.id" @click="jump(s.id)">
                <span>{{ s.no }}</span
                >{{ s.label }}</button
              ><button v-if="!isPlan && report.includeAppendix" @click="jump('report-appendix')">
                <span>＋</span>서버별 상세 점검표
              </button>
            </nav>
            <div v-if="editable && !isPlan" class="outline-editor">
              <q-toggle
                :model-value="report.includeAppendix"
                label="상세 점검표 포함"
                size="sm"
                :disable="busy"
                @update:model-value="toggleAppendix"
              />
            </div>
            <div v-if="report.state === 'FINAL'" class="outline-note">
              <q-icon name="lock_outline" />
              <p>확정된 보고서는 수정할 수 없습니다. 수정하려면 ‘수정본 작성’을 선택해 주세요.</p>
            </div>
          </aside>
          <InspectionReportDocument
            :report="report"
            :editable="editable && !busy"
            @edit="openEdit"
            @participants="participantsOpen = true"
            @result="openResult"
            @notes="openNote"
            @delete-note="deleteNote"
            @action="openAction"
            @issue="openIssue"
            @server="
              selectedServer = $event;
              serverOpen = true;
            "
          />
        </div>
      </template>
      <template v-else-if="!error">
        <q-tabs
          :model-value="kind"
          dense
          align="left"
          active-color="primary"
          indicator-color="primary"
          class="document-kind-tabs"
          @update:model-value="changeKind"
        >
          <q-tab name="PLAN" label="점검 계획서" no-caps /><q-tab
            name="RESULT"
            label="점검 결과서"
            no-caps
          />
        </q-tabs>
        <section class="report-list-header">
          <div>
            <h2>월별 점검 {{ documentLabel }}</h2>
            <p>
              {{
                isPlan
                  ? '점검 대상과 예정된 작업, 참여자별 담당 업무를 정리합니다.'
                  : '자원 사용량, 조치 내역, 월간 작업 결과를 확인합니다.'
              }}
            </p>
          </div>
          <InspectionMonthPicker :model-value="month" @update:model-value="changeMonth" />
        </section>
        <div v-if="reports.length" class="report-cards">
          <button
            v-for="item in reports"
            :key="item.id"
            class="report-card"
            @click="goReport(item.id)"
          >
            <div class="report-card-icon"><q-icon name="description" size="26px" /></div>
            <div class="report-card-copy">
              <div class="card-state" :class="{ final: item.state === 'FINAL' }">
                {{ item.state === 'FINAL' ? '확정' : '초안' }} <span>{{ item.revision }}차</span>
              </div>
              <h3>{{ item.title }}</h3>
              <p>점검{{ isPlan ? ' 예정일' : '일' }} {{ item.inspectionDate }}</p>
              <small>{{ item.createdBy }} · {{ reportTime(item.updatedAt) }}</small>
            </div>
            <q-icon name="description" size="17px" class="report-card-open" />
          </button>
        </div>
        <section v-else class="report-empty">
          <div class="empty-document" aria-hidden="true">
            <div class="mock-line short" />
            <div class="mock-title" />
            <div class="mock-stats"><i /><i /><i /></div>
            <div class="mock-line" />
            <div class="mock-line" />
            <div class="mock-line short" />
            <span><q-icon name="check" size="20px" /></span>
          </div>
          <h3>{{ formatInspectionMonth(month) }} 점검 {{ documentLabel }}가 없습니다.</h3>
          <p>
            {{
              isPlan
                ? '정기 점검 대상과 월간 작업으로 계획서 초안을 만들 수 있습니다.'
                : '점검 데이터와 월간 작업으로 결과서 초안을 만들 수 있습니다.'
            }}
          </p>
          <q-btn
            v-if="canWrite"
            unelevated
            color="primary"
            icon="add"
            :label="`${documentLabel} 작성`"
            @click="sourceOpen = true"
          />
          <p v-else>내부망에서 보고서를 작성할 수 있습니다.</p>
        </section>
        <div class="report-list-note">
          <q-icon name="lock_outline" /><span
            >서버 점검 권한이 있는 사용자는 보고서를 조회하고 초안을 수정할 수 있습니다.</span
          >
        </div>
      </template>
    </div>
    <ReportReviewDialog
      v-if="report"
      v-model="reviewOpen"
      :report="report"
      :editable="editable && !busy && !loading"
      @edit="jump('report-followup')"
    />
    <ReportParticipantsDialog
      v-if="report"
      v-model="participantsOpen"
      :report="report"
      @saved="onSaved"
    />
    <ReportSourceDialog
      v-model="sourceOpen"
      :month="report?.month || month"
      :kind="kind"
      :report="report"
      @saved="onSaved"
    />
    <InspectionResultDialog
      v-if="report"
      v-model="resultOpen"
      :task="resultTask"
      :report-id="report.id"
      :readonly="!editable"
      @saved="resultSaved"
    />
    <ReportActionDialog
      v-if="report"
      v-model="actionOpen"
      :report="report"
      :target="actionTarget"
      @saved="actionSaved"
    />
    <ReportNotesDialog
      v-if="report"
      v-model="notesOpen"
      :report="report"
      :note="selectedNote"
      @saved="onSaved"
    />
    <WorkDocumentEntryDialog
      v-if="sourcePlan"
      v-model="sourcePlanOpen"
      :entry-id="sourcePlan.id"
      :title="sourcePlan.templateTitle"
      :back-label="`점검 ${documentLabel}로 돌아가기`"
    />
    <IssueDetailDialog
      v-if="selectedIssue"
      v-model="issueOpen"
      :issue="selectedIssue"
      :project-id="selectedIssue.projectId"
    />
    <q-dialog v-model="editOpen" persistent
      ><q-card class="report-edit-dialog"
        ><q-card-section class="dialog-heading"
          ><div>
            <div class="toolbar-eyebrow">점검 {{ documentLabel }} · 개요</div>
            <h2>{{ documentLabel }} 내용 수정</h2>
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="보고서 편집 닫기"
            :disable="editBusy"
            @click="closeEdit" /></q-card-section
        ><q-card-section class="dialog-fields"
          ><q-input
            v-model="form.title"
            outlined
            dense
            :label="`${documentLabel} 제목`"
            maxlength="200"
            :disable="editBusy"
          /><q-input
            v-model="form.inspection_date"
            outlined
            dense
            type="date"
            stack-label
            :label="isPlan ? '점검 예정일' : '점검일'"
            :disable="editBusy"
          /><q-input
            v-if="isPlan"
            v-model="form.planned_time"
            outlined
            dense
            label="예정 시간 (선택)"
            placeholder="예: 10:00 ~ 12:00"
            maxlength="100"
            :disable="editBusy"
          />
          <q-input
            v-if="isPlan"
            v-model="form.resource_checks"
            outlined
            type="textarea"
            autogrow
            label="자원 점검 항목"
            placeholder="항목별로 한 줄씩 작성해 주세요."
            maxlength="3000"
            :disable="editBusy"
          />
          <q-input
            v-model="form.purpose"
            outlined
            label="점검 목적"
            type="textarea"
            autogrow
            maxlength="3000"
            :disable="editBusy"
          /><q-input
            v-model="form.overview"
            outlined
            :label="isPlan ? '사전 준비 및 유의사항 (선택)' : '종합 의견'"
            type="textarea"
            autogrow
            maxlength="10000"
            :placeholder="
              isPlan
                ? '사전 준비, 서비스 중단 여부 등 필요한 내용을 입력해 주세요.'
                : '주요 점검 결과와 조치 내용, 추가로 확인할 사항을 입력해 주세요.'
            "
            :disable="editBusy"
          /><q-checkbox
            v-if="!isPlan"
            v-model="form.include_appendix"
            label="서버별 상세 점검 기록을 부록에 포함"
            size="sm"
            :disable="editBusy"
          /><q-banner
            v-if="editError"
            class="bg-red-1 text-negative rounded-borders"
            role="alert"
            >{{ editError }}</q-banner
          ></q-card-section
        ><q-card-actions align="right" class="q-pa-lg q-pt-sm"
          ><q-btn flat label="취소" :disable="editBusy" @click="closeEdit" /><q-btn
            unelevated
            color="primary"
            label="초안 저장"
            :loading="editBusy"
            @click="saveEdit" /></q-card-actions></q-card
    ></q-dialog>
    <q-dialog v-model="finalizeOpen" persistent
      ><q-card class="report-finalize-dialog"
        ><q-card-section class="dialog-heading"
          ><div>
            <div class="toolbar-eyebrow">마지막 확인</div>
            <h2>{{ documentLabel }} 확정</h2>
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="확정 검토 닫기"
            :disable="busy"
            @click="finalizeOpen = false" /></q-card-section
        ><q-card-section class="q-pt-none"
          ><p class="dialog-help">
            현재 내용을 확정하면 이 보고서는 수정할 수 없습니다. 이후에는 수정본을 작성할 수
            있습니다.
          </p>
          <div v-if="report?.snapshot.warnings.length" class="finalize-warnings">
            <b>확인이 필요한 항목</b>
            <div v-for="w in report.snapshot.warnings" :key="w.code">
              <span>{{ w.label }}</span
              ><strong>{{ w.count }}</strong>
            </div>
          </div>
          <ol v-if="additionalNotes.length" class="finalize-limitations">
            <li v-for="note in additionalNotes" :key="note.id">{{ note.content }}</li>
          </ol>
          <q-banner
            v-if="finalizeError"
            class="bg-red-1 text-negative rounded-borders q-mt-md"
            role="alert"
            >{{ finalizeError }}</q-banner
          ></q-card-section
        ><q-card-actions align="right" class="q-pa-lg q-pt-sm"
          ><q-btn flat label="계속 작성" :disable="busy" @click="finalizeOpen = false" /><q-btn
            unelevated
            color="primary"
            icon="check"
            :label="`${documentLabel} 확정`"
            :loading="busy"
            @click="finalize" /></q-card-actions></q-card
    ></q-dialog>
    <q-dialog v-model="serverOpen"
      ><q-card v-if="selectedServer" class="server-record-dialog"
        ><q-card-section class="dialog-heading"
          ><div>
            <div class="toolbar-eyebrow">보고서에 포함된 서버 점검 결과</div>
            <h2>{{ selectedServer.hostName }}</h2>
            <p class="dialog-help">{{ selectedServer.ip }}</p>
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            aria-label="서버 점검 결과 닫기"
            v-close-popup /></q-card-section
        ><q-card-section class="q-pt-none"
          ><div class="server-record-stats">
            <div v-for="k in metricKinds" :key="k">
              <span>{{ k === 'disk' ? '디스크' : k.toUpperCase() }}</span
              ><b>{{ percent(selectedServer[k].value) }}</b
              ><small>{{ measurementBasis(selectedServer[k]) }} {{ selectedServer[k].path }}</small>
            </div>
          </div>
          <p v-if="selectedServer.detail.overallComment" class="record-prose">
            {{ selectedServer.detail.overallComment }}
          </p>
          <div v-if="selectedServer.detail.disks?.length" class="q-mt-lg">
            <b class="text-caption">파일시스템별 사용량</b>
            <div v-for="(d, i) in selectedServer.detail.disks" :key="i" class="server-record-row">
              <span>{{ d.filesystem }}</span
              ><b>{{ d.pct || '—' }}</b>
            </div>
          </div>
          <p v-if="!selectedServer.asset" class="dialog-help">
            등록된 자산과 연결되지 않은 서버입니다.
          </p>
          <q-btn
            v-else-if="canViewAssets"
            flat
            no-caps
            color="primary"
            icon="dns"
            :label="`연결 자산 · ${selectedServer.asset.name}`"
            :to="{
              path: '/asset/list',
              query: { category: '서버', assetId: selectedServer.asset.id },
            }"
            target="_blank"
            class="q-mt-md"
          />
          <p class="dialog-help q-mt-md">
            ‘상세 점검표 포함’을 선택하면 서버별 점검 항목을 보고서에 추가할 수 있습니다.
          </p></q-card-section
        ></q-card
      ></q-dialog
    >
  </q-page>
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router';
import { measurementBasis } from 'src/utils/inspectionMeasurements';
import { useQuasar } from 'quasar';
import { useAuthStore } from 'stores/auth';
import {
  formatInspectionMonth,
  inspectionError,
  thisMonth,
  type InspectionTask,
} from 'src/services/inspection';
import {
  editReport,
  finalizeReport,
  getReport,
  getReportTask,
  listReports,
  percent,
  reportTime,
  reportNotes,
  saveReportNotes,
  type ReportNote,
  type ReportKind,
  reviseReport,
  syncReportResults,
  type InspectionReport,
  type ReportEdit,
  type ReportSummary,
  type ReportTask,
  type ResourceServer,
  type ReportActionTarget,
} from 'src/services/inspectionReports';
import { getIssue, type Issue } from 'src/services/pm/issue';
import InspectionMonthPicker from 'src/components/inspection/InspectionMonthPicker.vue';
import InspectionReportDocument from 'src/components/inspection/InspectionReportDocument.vue';
import ReportSourceDialog from 'src/components/inspection/ReportSourceDialog.vue';
import ReportParticipantsDialog from 'src/components/inspection/ReportParticipantsDialog.vue';
import ReportReviewDialog from 'src/components/inspection/ReportReviewDialog.vue';
import InspectionResultDialog from 'src/components/inspection/InspectionResultDialog.vue';
import ReportActionDialog from 'src/components/inspection/ReportActionDialog.vue';
import ReportNotesDialog from 'src/components/inspection/ReportNotesDialog.vue';
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';
import type { InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
const route = useRoute(),
  router = useRouter(),
  $q = useQuasar(),
  auth = useAuthStore();
const report = ref<InspectionReport | null>(null),
  reports = ref<ReportSummary[]>([]),
  month = ref(thisMonth());
const loading = ref(false),
  busy = ref(false),
  printing = ref(false),
  error = ref('');
const sourceOpen = ref(false),
  reviewOpen = ref(false),
  participantsOpen = ref(false),
  editOpen = ref(false),
  finalizeOpen = ref(false),
  finalizeError = ref(''),
  editError = ref(''),
  editBusy = ref(false);
const resultOpen = ref(false),
  notesOpen = ref(false),
  selectedNote = ref<ReportNote | null>(null),
  actionOpen = ref(false),
  actionTarget = ref<ReportActionTarget | null>(null),
  resultTask = ref<InspectionTask | null>(null),
  selectedIssue = ref<Issue | null>(null),
  issueOpen = ref(false),
  selectedServer = ref<ResourceServer | null>(null),
  serverOpen = ref(false);
const sourcePlan = ref<InspectionWorkPlan | null>(null),
  sourcePlanOpen = ref(false);
const kind = computed<ReportKind>(
  () => report.value?.kind || (route.query.kind === 'PLAN' ? 'PLAN' : 'RESULT'),
);
const isPlan = computed(() => kind.value === 'PLAN');
const documentLabel = computed(() => (isPlan.value ? '계획서' : '결과서'));
const canWrite = computed(() => auth.me?.isInternal !== false);
const canViewAssets = computed(() => auth.me?.isAdmin || auth.me?.permissions?.includes('asset'));
const editable = computed(() => report.value?.state === 'DRAFT' && canWrite.value);
const additionalNotes = computed(() => (report.value ? reportNotes(report.value) : []));
const form = ref<ReportEdit>({
    title: '',
    inspection_date: '',
    purpose: '',
    overview: '',
    include_appendix: false,
  }),
  formInitial = ref('');
const metricKinds = ['cpu', 'ram', 'disk'] as const;
const sections = computed(() =>
  [
    { id: 'report-overview', no: '·', label: '점검 개요' },
    { id: 'report-participants', no: '·', label: '참여자 및 역할' },
    {
      id: 'report-resources',
      no: '01',
      label: isPlan.value ? '자원 점검 계획' : '자원 사용량 및 조치 내역',
    },
    ...(report.value?.snapshot.plan
      ? [{ id: 'report-plan', no: '·', label: '계획 대비 수행 현황' }]
      : []),
    { id: 'report-tasks', no: '02', label: isPlan.value ? '월간 작업 계획' : '월간 작업 결과' },
    { id: 'report-followup', no: '03', label: isPlan.value ? '추가 안내' : '추가 확인 사항' },
  ].filter(
    (s) =>
      (s.id !== 'report-participants' || editable.value || report.value?.participants?.length) &&
      (s.id !== 'report-followup' || editable.value || additionalNotes.value.length),
  ),
);
let generation = 0,
  oldTitle = '';
let printStyle: HTMLStyleElement | null = null;
const shortTime = (v: string) =>
  new Date(v).toLocaleTimeString('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
  });
async function load() {
  const token = ++generation;
  loading.value = true;
  error.value = '';
  report.value = null;
  reviewOpen.value = false;
  sourceOpen.value = false;
  participantsOpen.value = false;
  editOpen.value = false;
  finalizeOpen.value = false;
  resultOpen.value = false;
  notesOpen.value = false;
  actionOpen.value = false;
  serverOpen.value = false;
  issueOpen.value = false;
  month.value =
    typeof route.query.month === 'string' && /^20\d{2}-(0[1-9]|1[0-2])$/.test(route.query.month)
      ? route.query.month
      : thisMonth();
  try {
    if (typeof route.params.id === 'string' && route.params.id) {
      const doc = await getReport(route.params.id);
      if (token === generation) {
        report.value = doc;
        month.value = doc.month;
        reviewOpen.value = doc.snapshot.warnings.length > 0;
      }
    } else {
      const docs = await listReports(month.value, kind.value);
      if (token === generation) {
        reports.value = docs;
        if (route.query.open === 'latest') {
          if (docs[0]) {
            void router.replace({
              path: `/inspection/monthly-reports/${docs[0].id}`,
              query: { kind: kind.value },
            });
          } else if (canWrite.value) sourceOpen.value = true;
        }
      }
    }
  } catch (e) {
    if (token === generation) error.value = inspectionError(e);
  } finally {
    if (token === generation) loading.value = false;
  }
}
watch(
  () => [route.params.id, route.query.month, route.query.kind, route.query.open],
  () => {
    void load();
  },
  { immediate: true },
);
function changeMonth(value: string) {
  void router.push({
    path: '/inspection/monthly-reports',
    query: { month: value, kind: kind.value },
  });
}
function changeKind(value: ReportKind) {
  void router.push({
    path: '/inspection/monthly-reports',
    query: { month: month.value, kind: value },
  });
}
function goReport(id: string) {
  void router.push({ path: `/inspection/monthly-reports/${id}`, query: { kind: kind.value } });
}
function onSaved(doc: InspectionReport) {
  report.value = doc;
  error.value = '';
  if (route.params.id !== doc.id) goReport(doc.id);
}
function openNote(note?: ReportNote) {
  if (!report.value || !editable.value || busy.value) return;
  selectedNote.value = note || null;
  notesOpen.value = true;
}
function deleteNote(note: ReportNote) {
  if (!report.value || !editable.value || busy.value) return;
  const original = report.value;
  $q.dialog({
    title: isPlan.value ? '추가 안내 삭제' : '추가 확인 사항 삭제',
    message: `이 항목을 삭제할까요? ${note.content.slice(0, 120)}${note.content.length > 120 ? '…' : ''}`,
    cancel: { label: '취소', flat: true },
    ok: { label: '삭제', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void removeNote(original, note);
  });
}
async function removeNote(original: InspectionReport, note: ReportNote) {
  if (report.value?.id !== original.id || busy.value) return;
  busy.value = true;
  try {
    const updated = await saveReportNotes(
      original,
      reportNotes(original).filter((item) => item.id !== note.id),
    );
    if (report.value?.id === original.id) onSaved(updated);
    $q.notify({
      type: 'positive',
      message: isPlan.value ? '추가 안내를 삭제했습니다.' : '추가 확인 사항을 삭제했습니다.',
    });
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  } finally {
    busy.value = false;
  }
}
function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function editValues(doc: InspectionReport): ReportEdit {
  return {
    title: doc.title,
    inspection_date: doc.inspectionDate,
    purpose: doc.purpose,
    overview: doc.overview,
    include_appendix: doc.includeAppendix,
    ...(doc.kind === 'PLAN'
      ? { planned_time: doc.plannedTime || '', resource_checks: doc.resourceChecks || '' }
      : {}),
  };
}
function openEdit() {
  if (!report.value || !editable.value) return;
  form.value = editValues(report.value);
  formInitial.value = JSON.stringify(form.value);
  editError.value = '';
  editOpen.value = true;
}
function closeEdit() {
  if (editBusy.value) return;
  if (JSON.stringify(form.value) !== formInitial.value)
    $q.dialog({
      title: '저장하지 않고 닫으시겠습니까?',
      message: '저장하지 않은 의견이 있습니다.',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '닫기', color: 'negative' },
    }).onOk(() => {
      editOpen.value = false;
    });
  else editOpen.value = false;
}
async function saveEdit() {
  if (!report.value) return;
  editBusy.value = true;
  editError.value = '';
  try {
    report.value = await editReport(report.value, form.value);
    editOpen.value = false;
    $q.notify({ type: 'positive', message: '초안을 저장했습니다.' });
  } catch (e) {
    editError.value = inspectionError(e);
  } finally {
    editBusy.value = false;
  }
}
async function toggleAppendix(value: boolean) {
  if (!report.value) return;
  busy.value = true;
  try {
    report.value = await editReport(report.value, {
      ...editValues(report.value),
      include_appendix: value,
    });
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
function openAction(target: ReportActionTarget) {
  if (!editable.value || busy.value) return;
  actionTarget.value = target;
  actionOpen.value = true;
}
function actionSaved(doc: InspectionReport, warning: string) {
  onSaved(doc);
  $q.notify({
    type: warning ? 'warning' : 'positive',
    message: warning || '조치 내역을 저장했습니다.',
  });
}
async function openResult(task: ReportTask) {
  if (!report.value || !editable.value) return;
  busy.value = true;
  try {
    resultTask.value = await getReportTask(report.value.id, task);
    resultOpen.value = true;
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  } finally {
    busy.value = false;
  }
}
async function resultSaved() {
  if (!report.value) return;
  busy.value = true;
  try {
    report.value = await syncReportResults(report.value);
    $q.notify({ type: 'positive', message: '작업 결과를 저장하고 보고서에 반영했습니다.' });
  } catch (e) {
    error.value = `작업 결과는 저장됐지만 보고서에 반영되지 않았습니다. 보고서를 다시 연 뒤 ‘최신 내용 불러오기’를 눌러 주세요. ${inspectionError(e)}`;
  } finally {
    busy.value = false;
  }
}
async function openIssue(task: ReportTask) {
  if (task.issueDeleted) return;
  if (task.sourceType === 'WORK_PLAN') {
    if (!(auth.me?.isAdmin || auth.me?.permissions?.includes('job'))) {
      $q.notify({ type: 'info', message: '작업계획서를 열려면 작업 관리 권한이 필요합니다.' });
      return;
    }
    sourcePlan.value = task.workPlan || null;
    sourcePlanOpen.value = true;
    return;
  }
  try {
    selectedIssue.value = await getIssue(task.issue.projectId, task.issueId);
    issueOpen.value = true;
  } catch (e) {
    $q.notify({ type: 'negative', message: inspectionError(e) });
  }
}
async function finalize() {
  if (!report.value) return;
  busy.value = true;
  finalizeError.value = '';
  try {
    report.value = await finalizeReport(report.value);
    finalizeOpen.value = false;
    $q.notify({ type: 'positive', message: `점검 ${documentLabel.value}를 확정했습니다.` });
  } catch (e) {
    finalizeError.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
async function makeRevision() {
  if (!report.value) return;
  busy.value = true;
  try {
    const doc = await reviseReport(report.value);
    busy.value = false;
    onSaved(doc);
    $q.notify({
      type: 'info',
      message:
        doc.state === 'DRAFT'
          ? '수정할 초안을 열었습니다. 필요하면 ‘최신 내용 불러오기’로 점검 데이터를 갱신해 주세요.'
          : '이 보고서의 확정된 수정본을 열었습니다.',
    });
  } catch (e) {
    error.value = inspectionError(e);
  } finally {
    busy.value = false;
  }
}
function afterPrint() {
  printStyle?.remove();
  printStyle = null;
  document.body.classList.remove('printing-inspection-report');
  if (oldTitle) {
    document.title = oldTitle;
    oldTitle = '';
  }
}
async function printReport() {
  if (!report.value) return;
  printing.value = true;
  try {
    report.value = await getReport(report.value.id);
    await nextTick();
    await Promise.all(
      Array.from(document.querySelectorAll<HTMLImageElement>('.report-paper img')).map((img) =>
        img.decode().catch(() => undefined),
      ),
    );
    oldTitle = document.title;
    document.title = `${report.value.title} (${report.value.state === 'FINAL' ? '확정' : '초안'} · ${report.value.revision}차)`;
    beforePrint();
    window.print();
  } catch (e) {
    error.value = inspectionError(e);
    afterPrint();
  } finally {
    printing.value = false;
  }
}
function beforePrint() {
  if (!report.value) return;
  document.body.classList.add('printing-inspection-report');
  if (!printStyle) {
    printStyle = document.createElement('style');
    // Install only while printing: avoid affecting other document exports in this SPA.
    printStyle.textContent =
      '@media print { @page { size: A4 portrait; margin: 15mm 14mm 18mm; @bottom-right { content: counter(page) " / " counter(pages); font-size: 9px; color: #7c8997; } } }';
    document.head.appendChild(printStyle);
  }
}
window.addEventListener('beforeprint', beforePrint);
window.addEventListener('afterprint', afterPrint);
function protectDraft(): boolean | Promise<boolean> {
  if (!auth.isLoggedIn) return true;
  if (busy.value || editBusy.value) return false;
  if (!editOpen.value || JSON.stringify(form.value) === formInitial.value) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: '작성 중인 의견이 있습니다',
      message: '저장하지 않고 다른 화면으로 이동할까요?',
      cancel: { label: '계속 작성', flat: true },
      ok: { label: '이동', color: 'negative' },
    })
      .onOk(() => {
        editOpen.value = false;
        resolve(true);
      })
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}
onBeforeRouteLeave(protectDraft);
onBeforeRouteUpdate(protectDraft);
onBeforeUnmount(() => {
  generation++;
  window.removeEventListener('afterprint', afterPrint);
  window.removeEventListener('beforeprint', beforePrint);
  afterPrint();
});
</script>
<style scoped>
.document-kind-tabs {
  border-bottom: 1px solid #e1e7ee;
  margin-bottom: 16px;
}
.monthly-report-page {
  background: #f4f6f9;
  min-height: 100vh;
  color: #27374a;
}
.report-shell {
  max-width: 1350px;
  margin: 0 auto;
  padding: 0 32px 56px;
}
.report-toolbar {
  min-height: 100px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  position: sticky;
  top: 50px;
  z-index: 4;
  background: #f4f6f9f5;
  backdrop-filter: blur(12px);
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar-eyebrow {
  font-size: 11px;
  color: #8b97a6;
  margin-bottom: 4px;
}
h1 {
  font-size: 21px;
  line-height: 1.3;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.6px;
}
.toolbar-actions {
  display: flex;
  gap: 9px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.report-primary-actions,
.report-secondary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.report-secondary-actions {
  color: #65778a;
}
.toolbar-actions .q-btn {
  font-size: 12px;
  border-radius: 7px;
  min-height: 40px;
}
.report-edit-button {
  font-weight: 600;
}
.save-status {
  font-size: 11px;
  color: #92a0ae;
  margin-right: 6px;
}
.report-workspace {
  display: grid;
  grid-template-columns: 188px minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}
.report-outline {
  position: sticky;
  top: 160px;
  padding-top: 12px;
}
.outline-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 23px;
  border-bottom: 1px solid #e1e7ee;
}
.outline-status b {
  display: block;
  font-size: 13px;
  font-weight: 650;
}
.outline-status b span {
  font-size: 10px;
  color: #94a0ac;
  font-weight: 400;
  margin-left: 6px;
}
.outline-status small {
  display: block;
  color: #8d9baa;
  font-size: 11px;
  margin-top: 4px;
}
.report-outline nav {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 20px 0;
}
.report-outline nav button {
  background: none;
  border: none;
  text-align: left;
  font: inherit;
  font-size: 12px;
  color: #697e92;
  padding: 10px 4px;
  cursor: pointer;
  border-radius: 6px;
}
.report-outline nav button:hover {
  background: #e9eef4;
  color: #345b7b;
}
.report-outline nav button span {
  display: inline-block;
  min-width: 24px;
  font-size: 10px;
  color: #a1afbc;
}
.outline-editor {
  border-top: 1px solid #e1e7ee;
  padding-top: 16px;
  font-size: 11px;
}
.outline-note {
  margin-top: 26px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #93a0ad;
}
.outline-note .q-icon {
  margin-top: 4px;
}
.outline-note p {
  margin: 0;
  font-size: 10px;
  line-height: 1.9;
}
.report-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 36px 0 28px;
  gap: 20px;
}
h2 {
  font-size: 23px;
  font-weight: 700;
  letter-spacing: -0.7px;
  line-height: 1.4;
  margin: 0 0 10px;
}
.report-list-header p {
  font-size: 13px;
  color: #8391a3;
  margin: 0;
}
.report-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.report-card {
  display: flex;
  gap: 19px;
  border: 1px solid #e0e7ef;
  border-radius: 12px;
  padding: 26px;
  text-align: left;
  background: white;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.report-card:hover {
  border-color: #a6bccd;
  box-shadow: 0 6px 16px #26394a08;
}
.report-card-icon {
  padding: 14px;
  background: #f1f5f8;
  color: #86a0b4;
  border-radius: 10px;
  align-self: flex-start;
}
.report-card-copy {
  min-width: 0;
  flex: 1;
}
.report-card-copy h3 {
  font-size: 16px;
  line-height: 1.6;
  font-weight: 650;
  margin: 8px 0;
  overflow-wrap: anywhere;
}
.report-card-copy p {
  font-size: 12px;
  color: #8795a6;
  margin: 0 0 18px;
}
.report-card-copy small {
  font-size: 10px;
  color: #9ba7b5;
}
.card-state {
  color: #aa925f;
  font-size: 10px;
}
.card-state.final {
  color: #578f79;
}
.card-state span {
  margin-left: 8px;
  color: #a0acb9;
}
.report-card-open {
  color: #aebac7;
  margin-top: 4px;
}
.report-empty {
  text-align: center;
  border: 1px solid #e2e9f0;
  background: white;
  padding: 65px 20px 52px;
  border-radius: 14px;
}
.report-empty h3 {
  font-size: 18px;
  font-weight: 650;
  line-height: 1.6;
  margin: 24px 0 10px;
}
.report-empty p {
  color: #8a98a9;
  font-size: 13px;
  line-height: 1.9;
  margin-bottom: 26px;
}
.report-empty .q-btn {
  border-radius: 7px;
  padding: 3px 17px;
}
.empty-document {
  width: 115px;
  height: 140px;
  border: 1px solid #dbe5ed;
  border-radius: 7px;
  padding: 22px 17px;
  margin: auto;
  background: linear-gradient(160deg, white, #f7fafc);
  transform: rotate(-5deg);
  box-shadow: 8px 7px 0 #f1f5f8;
  position: relative;
}
.mock-line {
  height: 3px;
  background: #e4ebf1;
  margin-bottom: 7px;
  border-radius: 2px;
}
.mock-line.short {
  width: 60%;
}
.mock-title {
  height: 6px;
  width: 90%;
  background: #b5c8d5;
  margin: 12px 0 15px;
  border-radius: 2px;
}
.mock-stats {
  display: flex;
  gap: 6px;
  margin-bottom: 15px;
}
.mock-stats i {
  width: 21px;
  height: 19px;
  border-radius: 3px;
  background: #e3edf2;
}
.empty-document > span {
  position: absolute;
  bottom: -8px;
  right: -10px;
  background: #eff7f2;
  color: #77a48b;
  border: 4px solid white;
  border-radius: 50%;
  padding: 7px;
}
.report-list-note {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 9px;
  color: #94a2b1;
  font-size: 11px;
  margin-top: 26px;
  line-height: 1.8;
}
.report-loading {
  text-align: center;
  padding: 130px 20px;
  color: #8795a6;
  font-size: 13px;
}
.error-banner {
  background: #fff1ef;
  color: #b36a5e;
  border-radius: 8px;
  margin-bottom: 20px;
}
.report-edit-dialog {
  width: 640px;
  max-width: calc(100vw - 32px);
  border-radius: 16px;
}
.report-finalize-dialog,
.server-record-dialog {
  width: 590px;
  max-width: calc(100vw - 32px);
  border-radius: 16px;
}
.dialog-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 26px;
  gap: 15px;
}
.dialog-heading h2 {
  font-size: 20px;
  line-height: 1.5;
  margin: 6px 0 0;
}
.dialog-fields {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0 26px 20px;
}
.dialog-help {
  color: #8795a6;
  font-size: 12px;
  line-height: 1.8;
  margin: 0;
}
.report-finalize-dialog > .q-card__section:not(.dialog-heading),
.server-record-dialog > .q-card__section:not(.dialog-heading) {
  padding-left: 26px;
  padding-right: 26px;
}
.finalize-warnings {
  background: #faf7ef;
  padding: 18px;
  border-radius: 8px;
  margin-top: 22px;
  font-size: 12px;
  color: #927e59;
}
.finalize-warnings > b {
  display: block;
  margin-bottom: 12px;
}
.finalize-warnings > div {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  padding: 6px 0;
}
.finalize-limitations,
.record-prose {
  font-size: 12px;
  line-height: 1.9;
  color: #788798;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 18px 0 0;
}
.server-record-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  background: #f5f8fa;
  border-radius: 8px;
  padding: 20px;
}
.server-record-stats > div {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.server-record-stats span,
.server-record-stats small {
  font-size: 11px;
  color: #7c8d9e;
}
.server-record-stats b {
  font-size: 22px;
  color: #3e546b;
}
.server-record-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid #ecf0f4;
  font-size: 12px;
  color: #748699;
}
@media (max-width: 1150px) {
  .save-status {
    display: none;
  }
  .report-shell {
    padding: 0 22px 40px;
  }
  .report-workspace {
    grid-template-columns: 160px minmax(0, 1fr);
    gap: 20px;
  }
  .toolbar-actions .q-btn {
    font-size: 11px;
  }
}
@media (max-width: 900px) {
  .report-outline {
    display: none;
  }
  .report-workspace {
    display: block;
  }
  .report-toolbar {
    position: static;
    flex-wrap: wrap;
    padding: 20px 0;
  }
  .toolbar-actions {
    justify-content: flex-end;
    margin-left: auto;
  }
  .report-cards {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 600px) {
  .report-shell {
    padding: 0 12px 30px;
  }
  .report-toolbar {
    gap: 16px;
  }
  .toolbar-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .report-primary-actions .q-btn {
    flex: 1;
    min-height: 44px;
    font-size: 13px;
  }
  .report-secondary-actions {
    justify-content: flex-end;
  }
  .toolbar-actions .q-btn {
    padding: 6px 10px;
  }
  .report-secondary-actions .q-btn {
    font-size: 11px;
  }
  .toolbar-left {
    gap: 5px;
  }
  h1 {
    font-size: 19px;
  }
  .report-list-header {
    flex-direction: column;
    align-items: flex-start;
    margin: 20px 6px;
    gap: 20px;
  }
  .report-list-header h2 {
    font-size: 21px;
  }
  .report-list-header p {
    line-height: 1.8;
  }
  .report-card {
    padding: 20px;
    gap: 14px;
  }
  .report-card-icon {
    padding: 10px;
  }
  .report-card-copy h3 {
    font-size: 14px;
  }
  .report-empty h3 {
    font-size: 16px;
  }
  .report-empty p {
    font-size: 12px;
  }
  .report-list-note {
    align-items: flex-start;
    padding: 0 10px;
  }
  .report-list-note .q-icon {
    margin-top: 4px;
  }
}
@media print {
  .screen-only,
  .report-outline {
    display: none !important;
  }
  .monthly-report-page {
    min-height: 0 !important;
    background: white;
  }
  .report-shell {
    padding: 0;
    max-width: none;
  }
  .report-workspace {
    display: block;
  }
}
</style>
<style>
@media print {
  body.printing-inspection-report.q-body--prevent-scroll {
    position: static !important;
    top: auto !important;
    left: auto !important;
    overflow: visible !important;
  }
  body.printing-inspection-report .q-layout__section--marginal,
  body.printing-inspection-report .q-drawer,
  body.printing-inspection-report .q-notifications,
  body.printing-inspection-report .q-dialog {
    display: none !important;
  }
  body.printing-inspection-report .q-page-container {
    padding: 0 !important;
  }
  body.printing-inspection-report .q-layout {
    min-height: 0 !important;
  }
  body.printing-inspection-report {
    background: white !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
</style>
