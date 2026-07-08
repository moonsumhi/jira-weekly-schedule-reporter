<template>
  <!-- 인쇄 전용 툴바 (인쇄 시 숨겨짐) -->
  <div class="no-print print-toolbar">
    <q-btn flat icon="arrow_back" label="돌아가기" no-caps @click="$router.back()" />
    <q-space />
    <span v-if="report" class="text-subtitle2 text-grey-7">{{ report.title }}</span>
    <q-space />
    <q-btn color="primary" icon="print" label="PDF로 저장 / 인쇄" no-caps unelevated @click="print" />
  </div>

  <!-- 로딩 -->
  <div v-if="loading" class="no-print flex flex-center" style="height:80vh">
    <q-spinner size="48px" color="primary" />
  </div>

  <!-- 출력 본문 -->
  <div v-if="report" class="print-root">

    <!-- ══════════ 페이지 헤더 ══════════ -->
    <div class="report-header">
      <div class="report-title">{{ report.title }}</div>
      <div class="report-meta">
        <span>{{ report.reportYear }}년 {{ report.reportWeek }}주차</span>
        <span class="meta-sep">·</span>
        <span>{{ fmt(report.startDate) }} ~ {{ fmt(report.endDate) }}</span>
        <template v-if="report.department">
          <span class="meta-sep">·</span>
          <span>{{ report.department }}</span>
        </template>
        <span class="meta-sep">·</span>
        <span>{{ STATUS_KO[report.status] ?? report.status }}</span>
        <template v-if="report.confirmedAt">
          <span class="meta-sep">·</span>
          <span>확정일: {{ fmt(report.confirmedAt) }}</span>
        </template>
      </div>
    </div>

    <!-- ══════════ 업무 현황 요약 ══════════ -->
    <div class="section-box">
      <div class="section-title-row">
        <span class="section-number">◼</span>
        <span class="section-title">업무 현황 요약</span>
      </div>
      <div class="stats-row">
        <div class="stat-cell">
          <div class="stat-value">{{ report.stats.total }}</div>
          <div class="stat-label">총 업무</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-cell highlight-done">
          <div class="stat-value">{{ report.stats.completed }}</div>
          <div class="stat-label">완료</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-cell highlight-prog">
          <div class="stat-value">{{ report.stats.inProgress }}</div>
          <div class="stat-label">진행 중</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-cell highlight-delay">
          <div class="stat-value">{{ report.stats.delayed }}</div>
          <div class="stat-label">지연</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-cell highlight-rate">
          <div class="stat-value">{{ report.stats.completionRate }}%</div>
          <div class="stat-label">완료율</div>
        </div>
      </div>
    </div>

    <!-- ══════════ 주요 안건 ══════════ -->
    <template v-if="agendaItems.length">
      <div class="section-box">
        <div class="section-title-row">
          <span class="section-number">1.</span>
          <span class="section-title">주요 안건</span>
          <span class="section-count">{{ agendaItems.length }}건</span>
        </div>
        <table class="item-table">
          <colgroup>
            <col style="width:28px" />
            <col style="width:90px" />
            <col style="width:80px" />
            <col />
            <col style="width:64px" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th>
              <th>카테고리</th>
              <th>진행 상태</th>
              <th>내용</th>
              <th>담당자</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in agendaItems" :key="item.id">
              <td class="text-center num-cell">{{ i + 1 }}</td>
              <td class="text-center"><span v-if="item.category" class="tag tag-blue">{{ item.category }}</span></td>
              <td class="text-center"><span v-if="item.agendaStatus" :class="agendaStatusClass(item.agendaStatus)" class="tag">{{ item.agendaStatus }}</span></td>
              <td>
                <div class="item-title">{{ item.title }}</div>
                <div v-if="item.content" class="item-content">{{ item.content }}</div>
              </td>
              <td class="text-center owner-cell">{{ item.owner ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ══════════ 특이사항 및 리스크 ══════════ -->
    <template v-if="riskItems.length">
      <div class="section-box avoid-break">
        <div class="section-title-row">
          <span class="section-number">2.</span>
          <span class="section-title">특이사항 및 리스크</span>
          <span class="section-count">{{ riskItems.length }}건</span>
        </div>
        <table class="item-table">
          <colgroup>
            <col style="width:28px" />
            <col style="width:76px" />
            <col style="width:52px" />
            <col />
            <col style="width:130px" />
            <col style="width:64px" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th>
              <th>유형</th>
              <th>영향도</th>
              <th>내용</th>
              <th>대응 방안</th>
              <th>담당자</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in riskItems" :key="item.id">
              <td class="text-center num-cell">{{ i + 1 }}</td>
              <td class="text-center"><span v-if="item.itemType" class="tag tag-purple">{{ item.itemType }}</span></td>
              <td class="text-center"><span v-if="item.impact" :class="impactClass(item.impact)" class="tag">{{ item.impact }}</span></td>
              <td>
                <div class="item-title">{{ item.title }}</div>
                <div v-if="item.content" class="item-content">{{ item.content }}</div>
              </td>
              <td class="item-content">{{ item.actionPlan ?? '-' }}</td>
              <td class="text-center owner-cell">{{ item.owner ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ══════════ 결정 필요 사항 ══════════ -->
    <template v-if="decisionItems.length">
      <div class="section-box">
        <div class="section-title-row">
          <span class="section-number">3.</span>
          <span class="section-title">결정 필요 사항</span>
          <span class="section-count">{{ decisionItems.length }}건</span>
        </div>
        <div v-for="(item, i) in decisionItems" :key="item.id" class="decision-item" :class="{ 'decision-item-last': i === decisionItems.length - 1 }">
          <div class="decision-num">{{ i + 1 }}</div>
          <div class="decision-body">
            <div class="item-title">{{ item.title }}</div>
            <div v-if="item.background" class="decision-field">
              <span class="decision-field-label">배경</span>
              <span>{{ item.background }}</span>
            </div>
            <div v-if="item.options" class="decision-field">
              <span class="decision-field-label">선택지</span>
              <span style="white-space: pre-line">{{ item.options }}</span>
            </div>
            <div v-if="item.requestedDecision" class="decision-field highlight-decision">
              <span class="decision-field-label">요청 결정</span>
              <span>{{ item.requestedDecision }}</span>
            </div>
            <div class="decision-footer">
              <span v-if="item.desiredDate">희망 결정일: {{ fmt(item.desiredDate) }}</span>
              <span v-if="item.owner" :class="{ 'q-ml-md': item.desiredDate }">담당자: {{ item.owner }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ══════════ 자동 집계 업무 ══════════ -->
    <!-- 금주 완료 업무 -->
    <template v-if="completedItems.length">
      <div class="section-box">
        <div class="section-title-row">
          <span class="section-number">4.</span>
          <span class="section-title">금주 완료 업무</span>
          <span class="section-count">{{ completedItems.length }}건</span>
        </div>
        <table class="item-table">
          <colgroup>
            <col style="width:28px" />
            <col style="width:100px" />
            <col />
            <col style="width:72px" />
            <col style="width:68px" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th>
              <th>이슈 번호</th>
              <th>업무명</th>
              <th>담당자</th>
              <th>마감일</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in completedItems" :key="item.issueId">
              <td class="text-center num-cell">{{ i + 1 }}</td>
              <td class="text-center issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
              <td>
                <div class="item-title">{{ item.title }}</div>
              </td>
              <td class="text-center owner-cell">{{ item.assigneeName ?? '-' }}</td>
              <td class="text-center date-cell">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 진행 중 업무 -->
    <template v-if="inProgressItems.length">
      <div class="section-box">
        <div class="section-title-row">
          <span class="section-number">5.</span>
          <span class="section-title">진행 중 업무</span>
          <span class="section-count">{{ inProgressItems.length }}건</span>
        </div>
        <table class="item-table">
          <colgroup>
            <col style="width:28px" />
            <col style="width:100px" />
            <col />
            <col style="width:72px" />
            <col style="width:52px" />
            <col style="width:68px" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th>
              <th>이슈 번호</th>
              <th>업무명</th>
              <th>담당자</th>
              <th>지연</th>
              <th>마감일</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in inProgressItems" :key="item.issueId" :class="{ 'row-delayed': item.isDelayed }">
              <td class="text-center num-cell">{{ i + 1 }}</td>
              <td class="text-center issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
              <td><div class="item-title">{{ item.title }}</div></td>
              <td class="text-center owner-cell">{{ item.assigneeName ?? '-' }}</td>
              <td class="text-center">{{ item.isDelayed ? '⚠' : '' }}</td>
              <td class="text-center date-cell">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 차주 계획 -->
    <template v-if="report.upcomingItems.length">
      <div class="section-box">
        <div class="section-title-row">
          <span class="section-number">6.</span>
          <span class="section-title">차주 계획</span>
          <span class="section-count">{{ report.upcomingItems.length }}건</span>
        </div>
        <table class="item-table">
          <colgroup>
            <col style="width:28px" />
            <col style="width:100px" />
            <col />
            <col style="width:72px" />
            <col style="width:68px" />
          </colgroup>
          <thead>
            <tr>
              <th>No.</th>
              <th>이슈 번호</th>
              <th>업무명</th>
              <th>담당자</th>
              <th>마감일</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in report.upcomingItems" :key="item.issueId">
              <td class="text-center num-cell">{{ i + 1 }}</td>
              <td class="text-center issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
              <td><div class="item-title">{{ item.title }}</div></td>
              <td class="text-center owner-cell">{{ item.assigneeName ?? '-' }}</td>
              <td class="text-center date-cell">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 관리자 코멘트 -->
    <div v-if="report.adminComment" class="section-box">
      <div class="section-title-row">
        <span class="section-number">◼</span>
        <span class="section-title">관리자 코멘트</span>
      </div>
      <div class="admin-comment">{{ report.adminComment }}</div>
    </div>

    <!-- 출력 푸터 -->
    <div class="print-footer">
      출력일: {{ today }} · {{ report.department ?? '' }} 주간보고 시스템
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify } from 'quasar'
import { getWeeklyReport, type WeeklyReport, type ManualItem } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const reportId = route.params.id as string
const loading = ref(true)
const report  = ref<WeeklyReport | null>(null)

const STATUS_KO: Record<string, string> = { DRAFT: '초안', REVIEWING: '검토중', CONFIRMED: '확정' }

const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })

function fmt(d: string | null | undefined): string {
  if (!d) return ''
  return d.slice(0, 10)
}

const agendaItems   = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'MAIN_AGENDA'      && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))
const riskItems     = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'ISSUE_RISK'       && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))
const decisionItems = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'DECISION_REQUIRED' && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))

const completedItems   = computed(() => (report.value?.allItems ?? []).filter(i => i.status === 'DONE'))
const inProgressItems  = computed(() => (report.value?.allItems ?? []).filter(i => ['IN_PROGRESS', 'IN_REVIEW', 'TODO', 'BACKLOG'].includes(i.status)))

function agendaStatusClass(s: string) {
  return { 예정: 'tag-blue', 진행중: 'tag-orange', 완료: 'tag-green', 지연: 'tag-red', 보류: 'tag-grey' }[s] ?? 'tag-grey'
}
function impactClass(s: string) {
  return { 높음: 'tag-red', 보통: 'tag-orange', 낮음: 'tag-green' }[s] ?? 'tag-grey'
}

function print() {
  window.print()
}

onMounted(async () => {
  try {
    report.value = await getWeeklyReport(reportId)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '보고서 로드 실패') })
  } finally {
    loading.value = false
  }
})
</script>

<style>
/* ── 인쇄 페이지 설정 ─────────────────────────────────── */
@page {
  size: A4;
  margin: 18mm 16mm 14mm 16mm;
}

@media print {
  html, body { background: white !important; }
  .q-layout, .q-page-container, .q-page { padding: 0 !important; margin: 0 !important; background: white !important; }
  .no-print { display: none !important; }
  .print-root { padding: 0 !important; }
}
</style>

<style scoped>
/* ── 툴바 (화면 전용) ──────────────────────────────────── */
.print-toolbar {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  gap: 8px;
}

/* ── 출력 루트 ────────────────────────────────────────── */
.print-root {
  font-family: 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  font-size: 9pt;
  color: #1a1a1a;
  padding: 0 20px 20px;
  max-width: 860px;
  margin: 0 auto;
  background: white;
}

/* ── 헤더 ─────────────────────────────────────────────── */
.report-header {
  border-top: 3px solid #1a56db;
  border-bottom: 1px solid #ccc;
  padding: 14px 0 10px;
  margin-bottom: 14px;
}
.report-title {
  font-size: 16pt;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 6px;
}
.report-meta {
  font-size: 9pt;
  color: #555;
}
.meta-sep {
  margin: 0 6px;
  color: #bbb;
}

/* ── 섹션 박스 ───────────────────────────────────────── */
.section-box {
  margin-bottom: 16px;
  page-break-inside: avoid;
}
.section-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #1a56db;
  color: white;
  padding: 5px 10px;
  border-radius: 3px 3px 0 0;
  font-size: 9.5pt;
}
.section-number {
  font-weight: 700;
  min-width: 20px;
}
.section-title {
  font-weight: 700;
  flex: 1;
}
.section-count {
  font-size: 8pt;
  opacity: 0.85;
}

/* ── 업무 통계 ───────────────────────────────────────── */
.stats-row {
  display: flex;
  align-items: center;
  border: 1px solid #dde;
  border-top: none;
  border-radius: 0 0 3px 3px;
}
.stat-cell {
  flex: 1;
  text-align: center;
  padding: 10px 6px;
}
.stat-value {
  font-size: 15pt;
  font-weight: 700;
  color: #222;
}
.stat-label {
  font-size: 7.5pt;
  color: #777;
  margin-top: 2px;
}
.stat-divider {
  width: 1px;
  height: 40px;
  background: #dde;
}
.highlight-done  .stat-value { color: #15803d; }
.highlight-prog  .stat-value { color: #1a56db; }
.highlight-delay .stat-value { color: #dc2626; }
.highlight-rate  .stat-value { color: #0e7490; }

/* ── 테이블 ─────────────────────────────────────────── */
.item-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #dde;
  border-top: none;
  border-radius: 0 0 3px 3px;
  font-size: 8.5pt;
}
.item-table th {
  background: #f0f4ff;
  color: #334;
  font-weight: 600;
  padding: 5px 8px;
  border-bottom: 1px solid #ccd;
  border-right: 1px solid #dde;
  text-align: center;
  white-space: nowrap;
}
.item-table th:last-child { border-right: none; }
.item-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #eef;
  border-right: 1px solid #eef;
  vertical-align: top;
}
.item-table td:last-child { border-right: none; }
.item-table tr:last-child td { border-bottom: none; }
.item-table tr:nth-child(even) td { background: #fafbff; }
.row-delayed td { background: #fff8f8 !important; }

.item-title {
  font-weight: 600;
  color: #1a1a1a;
  line-height: 1.5;
}
.item-content {
  margin-top: 3px;
  color: #555;
  font-size: 8pt;
  line-height: 1.6;
  white-space: pre-wrap;
}
.num-cell   { color: #888; font-size: 7.5pt; width: 28px; }
.issue-key  { color: #1a56db; font-weight: 600; font-size: 8pt; }
.owner-cell { color: #444; font-size: 8pt; white-space: nowrap; }
.date-cell  { color: #555; font-size: 8pt; white-space: nowrap; }

/* ── 태그 ─────────────────────────────────────────────── */
.tag {
  display: inline-block;
  font-size: 7.5pt;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
  white-space: nowrap;
}
.tag-blue   { background: #dbeafe; color: #1d4ed8; }
.tag-orange { background: #ffedd5; color: #c2410c; }
.tag-green  { background: #dcfce7; color: #15803d; }
.tag-red    { background: #fee2e2; color: #b91c1c; }
.tag-purple { background: #ede9fe; color: #6d28d9; }
.tag-grey   { background: #f3f4f6; color: #6b7280; }

/* ── 결정 필요 사항 ─────────────────────────────────── */
.decision-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  border: 1px solid #dde;
  border-top: none;
  font-size: 8.5pt;
}
.decision-item-last {
  border-radius: 0 0 3px 3px;
}
.decision-num {
  min-width: 22px;
  height: 22px;
  background: #1a56db;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8pt;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}
.decision-body {
  flex: 1;
}
.decision-field {
  margin-top: 4px;
  display: flex;
  gap: 6px;
  align-items: flex-start;
  color: #444;
  line-height: 1.6;
}
.decision-field-label {
  flex-shrink: 0;
  font-weight: 600;
  color: #555;
  font-size: 7.5pt;
  background: #f0f4ff;
  padding: 1px 5px;
  border-radius: 3px;
  margin-top: 1px;
}
.highlight-decision {
  background: #fffbeb;
  padding: 4px 6px;
  border-left: 3px solid #f59e0b;
  border-radius: 0 3px 3px 0;
  margin-top: 6px;
}
.decision-footer {
  margin-top: 6px;
  font-size: 7.5pt;
  color: #888;
}

/* ── 관리자 코멘트 ─────────────────────────────────── */
.admin-comment {
  border: 1px solid #dde;
  border-top: none;
  padding: 10px 12px;
  background: #fffef0;
  font-size: 8.5pt;
  line-height: 1.7;
  white-space: pre-wrap;
  border-radius: 0 0 3px 3px;
}

/* ── 출력 푸터 ──────────────────────────────────────── */
.print-footer {
  margin-top: 20px;
  padding-top: 8px;
  border-top: 1px solid #ddd;
  font-size: 7.5pt;
  color: #aaa;
  text-align: right;
}

/* ── @media print 전용 ─────────────────────────────── */
@media print {
  .print-root {
    padding: 0;
    max-width: 100%;
  }
  .avoid-break {
    page-break-inside: avoid;
  }
  .section-box {
    page-break-inside: auto;
  }
}
</style>
