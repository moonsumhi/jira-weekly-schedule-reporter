<template>
  <!-- 화면 전용 툴바 -->
  <div class="screen-toolbar">
    <button class="btn-back" @click="router.back()">← 돌아가기</button>
    <span v-if="report" class="toolbar-title">{{ report.title }}</span>
    <button class="btn-print" @click="triggerPrint()">🖨 인쇄 / PDF 저장</button>
  </div>
  <div v-if="isPreview" class="preview-banner">미리보기 모드 — 실제 인쇄 시 상단 툴바는 출력되지 않습니다.</div>

  <div v-if="loading" class="loading-wrap">
    <span>보고서 불러오는 중...</span>
  </div>

  <div v-if="report" id="report-doc">

    <!-- ━━━━ 문서 헤더 ━━━━ -->
    <div class="doc-header">
      <div class="doc-org">{{ report.department ?? '데이터운영팀' }}</div>
      <div class="doc-title">주 간 업 무 보 고 서</div>
      <div class="doc-period">{{ report.reportYear }}년 제 {{ report.reportWeek }}주차 &nbsp;·&nbsp; {{ fmt(report.startDate) }} ~ {{ fmt(report.endDate) }}</div>
    </div>

    <!-- ━━━━ 보고 개요 ━━━━ -->
    <table class="meta-table">
      <tbody>
        <tr>
          <th>보고기간</th>
          <td>{{ fmt(report.startDate) }} ~ {{ fmt(report.endDate) }}</td>
          <th>작성일</th>
          <td>{{ today }}</td>
        </tr>
        <tr>
          <th>부서</th>
          <td>{{ report.department ?? '데이터운영팀' }}</td>
          <th>보고 상태</th>
          <td>{{ STATUS_KO[report.status] ?? report.status }}{{ report.confirmedAt ? ' (' + fmt(report.confirmedAt) + ' 확정)' : '' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ 업무 현황 요약 ━━━━ -->
    <div class="section-heading">▪ 업무 현황 요약</div>
    <table class="summary-table">
      <thead>
        <tr>
          <th>총 업무</th>
          <th>완료</th>
          <th>진행 중</th>
          <th>지연</th>
          <th>완료율</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="sum-total">{{ report.stats.total }}건</td>
          <td class="sum-done">{{ report.stats.completed }}건</td>
          <td class="sum-prog">{{ report.stats.inProgress }}건</td>
          <td class="sum-delay">{{ report.stats.delayed }}건</td>
          <td class="sum-rate">{{ report.stats.completionRate }}%</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ 개인별 업무 일정 (캘린더) ━━━━ -->
    <div class="section-heading">▪ 개인별 업무 일정</div>
    <div class="gantt-legend">
      <span class="gl gl-done">완료</span>
      <span class="gl gl-prog">진행 중</span>
      <span class="gl gl-delay">지연</span>
      <span class="gl gl-todo">계획/미시작</span>
    </div>
    <table class="gantt-table">
      <thead>
        <tr>
          <th class="gantt-name-th">담당자 / 업무</th>
          <th v-for="d in ganttDays" :key="d.iso"
            :class="['gantt-day-th', d.isWeekend ? 'g-weekend' : '', d.inReport ? 'g-in-report' : '']">
            <div class="gantt-day-name">{{ d.dayName }}</div>
            <div class="gantt-day-date">{{ d.mmdd }}</div>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="pb in ganttPersons" :key="pb.userId">
          <tr class="gantt-person-row">
            <td :colspan="ganttDays.length + 1">
              {{ pb.userName }}
              <span class="gantt-person-stats">완료 {{ pb.doneCount }} · 진행 {{ pb.progCount }} · 지연 {{ pb.delayCount }}</span>
            </td>
          </tr>
          <tr v-for="item in pb.items" :key="item.issueId" class="gantt-task-row">
            <td class="gantt-task-label" :title="item.title">{{ item.title }}</td>
            <td v-for="d in ganttDays" :key="d.iso"
              :class="['gantt-day-cell', ganttCellClass(item, d.iso)]"></td>
          </tr>
        </template>
        <tr v-if="!ganttPersons.length">
          <td :colspan="ganttDays.length + 1" class="gantt-empty">집계된 업무가 없습니다.</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅰ. 주요 안건 ━━━━ -->
    <div class="section-heading">Ⅰ. 주요 안건 <span class="cnt">({{ agendaItems.length }}건)</span></div>
    <div v-if="!agendaItems.length" class="empty-row">해당 없음</div>
    <table v-else class="doc-table">
      <colgroup>
        <col style="width:30px" /><col style="width:88px" /><col style="width:72px" /><col /><col style="width:60px" />
      </colgroup>
      <thead><tr><th>No</th><th>카테고리</th><th>진행 상태</th><th>안건 내용</th><th>담당자</th></tr></thead>
      <tbody>
        <tr v-for="(item, i) in agendaItems" :key="item.id">
          <td class="c">{{ i + 1 }}</td>
          <td class="c">{{ item.category ?? '-' }}</td>
          <td class="c">
            <span :class="['badge', agendaStatusBadge(item.agendaStatus)]">{{ item.agendaStatus ?? '-' }}</span>
          </td>
          <td>
            <div class="cell-title">{{ item.title }}</div>
            <div v-if="item.content" class="cell-sub">{{ item.content }}</div>
          </td>
          <td class="c">{{ item.owner ?? '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅱ. 특이사항 및 리스크 ━━━━ -->
    <div class="section-heading">Ⅱ. 특이사항 및 리스크 <span class="cnt">({{ riskItems.length }}건)</span></div>
    <div v-if="!riskItems.length" class="empty-row">해당 없음</div>
    <table v-else class="doc-table">
      <colgroup>
        <col style="width:30px" /><col style="width:72px" /><col style="width:48px" /><col /><col style="width:120px" /><col style="width:60px" />
      </colgroup>
      <thead><tr><th>No</th><th>유형</th><th>영향도</th><th>내용</th><th>대응 방안</th><th>담당자</th></tr></thead>
      <tbody>
        <tr v-for="(item, i) in riskItems" :key="item.id">
          <td class="c">{{ i + 1 }}</td>
          <td class="c">{{ item.itemType ?? '-' }}</td>
          <td class="c">
            <span :class="['badge', impactBadge(item.impact)]">{{ item.impact ?? '-' }}</span>
          </td>
          <td>
            <div class="cell-title">{{ item.title }}</div>
            <div v-if="item.content" class="cell-sub">{{ item.content }}</div>
          </td>
          <td class="cell-sub">{{ item.actionPlan ?? '-' }}</td>
          <td class="c">{{ item.owner ?? '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅲ. 결정 필요 사항 ━━━━ -->
    <div class="section-heading">Ⅲ. 결정 필요 사항 <span class="cnt">({{ decisionItems.length }}건)</span></div>
    <div v-if="!decisionItems.length" class="empty-row">해당 없음</div>
    <template v-else>
      <div v-for="(item, i) in decisionItems" :key="item.id" class="decision-block">
        <div class="decision-title">{{ i + 1 }}. {{ item.title }}</div>
        <table class="decision-detail">
          <tbody>
            <tr v-if="item.background">
              <th>배경</th><td>{{ item.background }}</td>
            </tr>
            <tr v-if="item.options">
              <th>선택지</th><td style="white-space:pre-line">{{ item.options }}</td>
            </tr>
            <tr v-if="item.requestedDecision">
              <th>요청 결정</th><td class="req-decision">{{ item.requestedDecision }}</td>
            </tr>
            <tr>
              <th>담당 / 희망일</th>
              <td>{{ item.owner ?? '-' }}{{ item.desiredDate ? ' · 희망 결정일 ' + fmt(item.desiredDate) : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ━━━━ Ⅳ. 금주 완료 업무 ━━━━ -->
    <div class="section-heading">Ⅳ. 금주 완료 업무 <span class="cnt">({{ completedItems.length }}건)</span></div>
    <div v-if="!completedItems.length" class="empty-row">해당 없음</div>
    <table v-else class="doc-table">
      <colgroup>
        <col style="width:30px" /><col style="width:96px" /><col /><col style="width:60px" /><col style="width:68px" />
      </colgroup>
      <thead><tr><th>No</th><th>이슈 번호</th><th>업무명</th><th>담당자</th><th>마감일</th></tr></thead>
      <tbody>
        <tr v-for="(item, i) in completedItems" :key="item.issueId">
          <td class="c">{{ i + 1 }}</td>
          <td class="c issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
          <td>{{ item.title }}</td>
          <td class="c">{{ item.assigneeName ?? '-' }}</td>
          <td class="c">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅴ. 진행 중 업무 ━━━━ -->
    <div class="section-heading">Ⅴ. 진행 중 업무 <span class="cnt">({{ inProgressItems.length }}건)</span></div>
    <div v-if="!inProgressItems.length" class="empty-row">해당 없음</div>
    <table v-else class="doc-table">
      <colgroup>
        <col style="width:30px" /><col style="width:96px" /><col /><col style="width:60px" /><col style="width:44px" /><col style="width:68px" />
      </colgroup>
      <thead><tr><th>No</th><th>이슈 번호</th><th>업무명</th><th>담당자</th><th>지연</th><th>마감일</th></tr></thead>
      <tbody>
        <tr v-for="(item, i) in inProgressItems" :key="item.issueId" :class="{ 'row-delay': item.isDelayed }">
          <td class="c">{{ i + 1 }}</td>
          <td class="c issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
          <td>{{ item.title }}</td>
          <td class="c">{{ item.assigneeName ?? '-' }}</td>
          <td class="c">{{ item.isDelayed ? '지연' : '' }}</td>
          <td class="c">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅵ. 차주 계획 ━━━━ -->
    <div class="section-heading">Ⅵ. 차주 계획 <span class="cnt">({{ report.upcomingItems.length }}건)</span></div>
    <div v-if="!report.upcomingItems.length" class="empty-row">해당 없음</div>
    <table v-else class="doc-table">
      <colgroup>
        <col style="width:30px" /><col style="width:96px" /><col /><col style="width:60px" /><col style="width:68px" />
      </colgroup>
      <thead><tr><th>No</th><th>이슈 번호</th><th>업무명</th><th>담당자</th><th>마감일</th></tr></thead>
      <tbody>
        <tr v-for="(item, i) in report.upcomingItems" :key="item.issueId">
          <td class="c">{{ i + 1 }}</td>
          <td class="c issue-key">{{ item.projectName }}-{{ item.issueNumber }}</td>
          <td>{{ item.title }}</td>
          <td class="c">{{ item.assigneeName ?? '-' }}</td>
          <td class="c">{{ item.dueDate ? fmt(item.dueDate) : '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- ━━━━ Ⅶ. SR 현황 ━━━━ -->
    <div class="section-heading">Ⅶ. SR(서비스 요청) 현황</div>
    <template v-if="report?.srSummary">
      <!-- 상태별 요약 -->
      <table class="summary-table sr-summary-table">
        <thead>
          <tr>
            <th>이번 주 신규</th>
            <th>이번 주 완료</th>
            <th>미접수 (검토 대기)</th>
            <th>처리 중 전체</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="sum-prog">{{ report.srSummary.totalNew }}건</td>
            <td class="sum-done">{{ report.srSummary.totalCompleted }}건</td>
            <td class="sum-delay">{{ report.srSummary.pendingItems.length }}건</td>
            <td class="sum-total">{{ report.srSummary.totalOpen }}건</td>
          </tr>
        </tbody>
      </table>

      <!-- 상태별 분포 -->
      <div v-if="Object.keys(report.srSummary.byStatus).length" class="sr-by-status">
        <span v-for="(cnt, lbl) in report.srSummary.byStatus" :key="lbl" class="sr-status-badge">
          {{ lbl }}: {{ cnt }}건
        </span>
      </div>

      <!-- 이번 주 신규 접수 -->
      <div class="sr-sub-heading">▸ 이번 주 신규 접수 ({{ report.srSummary.totalNew }}건)</div>
      <div v-if="!report.srSummary.newThisWeek.length" class="empty-row">해당 없음</div>
      <table v-else class="doc-table">
        <colgroup><col style="width:30px"/><col style="width:80px"/><col/><col style="width:90px"/><col style="width:72px"/><col style="width:60px"/></colgroup>
        <thead><tr><th>No</th><th>SR 번호</th><th>제목</th><th>유형</th><th>요청자</th><th>담당자</th></tr></thead>
        <tbody>
          <tr v-for="(sr, i) in report.srSummary.newThisWeek" :key="sr.srNo">
            <td class="c">{{ i + 1 }}</td>
            <td class="c issue-key">{{ sr.srNo }}</td>
            <td>{{ sr.title }}<span v-if="sr.isUrgent" class="badge badge-red" style="margin-left:4px">긴급</span></td>
            <td class="c">{{ sr.requestTypeLabel }}</td>
            <td class="c">{{ sr.requesterName }}</td>
            <td class="c">{{ sr.assigneeName ?? '-' }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 미접수 (SUBMITTED) -->
      <div class="sr-sub-heading">▸ 미접수 — 검토 대기 중 ({{ report.srSummary.pendingItems.length }}건)</div>
      <div v-if="!report.srSummary.pendingItems.length" class="empty-row">해당 없음</div>
      <table v-else class="doc-table">
        <colgroup><col style="width:30px"/><col style="width:80px"/><col/><col style="width:90px"/><col style="width:72px"/><col style="width:72px"/></colgroup>
        <thead><tr><th>No</th><th>SR 번호</th><th>제목</th><th>유형</th><th>요청자</th><th>접수일</th></tr></thead>
        <tbody>
          <tr v-for="(sr, i) in report.srSummary.pendingItems" :key="sr.srNo">
            <td class="c">{{ i + 1 }}</td>
            <td class="c issue-key">{{ sr.srNo }}</td>
            <td>{{ sr.title }}<span v-if="sr.isUrgent" class="badge badge-red" style="margin-left:4px">긴급</span></td>
            <td class="c">{{ sr.requestTypeLabel }}</td>
            <td class="c">{{ sr.requesterName }}</td>
            <td class="c">{{ fmt(sr.createdAt) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 처리 중 전체 -->
      <div class="sr-sub-heading">▸ 처리 중 전체 ({{ report.srSummary.totalOpen }}건)</div>
      <div v-if="!report.srSummary.openItems.length" class="empty-row">해당 없음</div>
      <table v-else class="doc-table">
        <colgroup><col style="width:30px"/><col style="width:80px"/><col/><col style="width:72px"/><col style="width:72px"/><col style="width:60px"/></colgroup>
        <thead><tr><th>No</th><th>SR 번호</th><th>제목</th><th>상태</th><th>요청자</th><th>담당자</th></tr></thead>
        <tbody>
          <tr v-for="(sr, i) in report.srSummary.openItems" :key="sr.srNo">
            <td class="c">{{ i + 1 }}</td>
            <td class="c issue-key">{{ sr.srNo }}</td>
            <td>{{ sr.title }}<span v-if="sr.isUrgent" class="badge badge-red" style="margin-left:4px">긴급</span></td>
            <td class="c">{{ sr.statusLabel }}</td>
            <td class="c">{{ sr.requesterName }}</td>
            <td class="c">{{ sr.assigneeName ?? '-' }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 이번 주 완료 -->
      <div class="sr-sub-heading">▸ 이번 주 완료 처리 ({{ report.srSummary.totalCompleted }}건)</div>
      <div v-if="!report.srSummary.completedThisWeek.length" class="empty-row">해당 없음</div>
      <table v-else class="doc-table">
        <colgroup><col style="width:30px"/><col style="width:80px"/><col/><col style="width:90px"/><col style="width:72px"/><col style="width:60px"/></colgroup>
        <thead><tr><th>No</th><th>SR 번호</th><th>제목</th><th>유형</th><th>요청자</th><th>담당자</th></tr></thead>
        <tbody>
          <tr v-for="(sr, i) in report.srSummary.completedThisWeek" :key="sr.srNo">
            <td class="c">{{ i + 1 }}</td>
            <td class="c issue-key">{{ sr.srNo }}</td>
            <td>{{ sr.title }}</td>
            <td class="c">{{ sr.requestTypeLabel }}</td>
            <td class="c">{{ sr.requesterName }}</td>
            <td class="c">{{ sr.assigneeName ?? '-' }}</td>
          </tr>
        </tbody>
      </table>
    </template>
    <div v-else class="empty-row">SR 데이터 없음 (재집계 필요)</div>

    <!-- ━━━━ 관리자 코멘트 ━━━━ -->
    <template v-if="report?.adminComment">
      <div class="section-heading">▪ 관리자 코멘트</div>
      <div class="comment-box">{{ report.adminComment }}</div>
    </template>

    <!-- ━━━━ 문서 하단 ━━━━ -->
    <div class="doc-footer">
      <span>출력일: {{ today }}</span>
      <span>{{ report?.department ?? '데이터운영팀' }} 주간보고 시스템</span>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getWeeklyReport, type WeeklyReport, type WorkItem } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const route      = useRoute()
const router     = useRouter()
const reportId   = route.params.id as string
const isPreview  = route.query.preview === 'true'
const loading    = ref(true)
const report     = ref<WeeklyReport | null>(null)

const STATUS_KO: Record<string, string> = { DRAFT: '초안', REVIEWING: '검토중', CONFIRMED: '확정' }
const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })

function fmt(d: string | null | undefined) { return d ? d.slice(0, 10) : '' }

const agendaItems   = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'MAIN_AGENDA'       && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))
const riskItems     = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'ISSUE_RISK'        && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))
const decisionItems = computed(() => (report.value?.manualItems ?? []).filter(i => i.section === 'DECISION_REQUIRED' && i.includeInReport).sort((a, b) => a.sortOrder - b.sortOrder))
const completedItems  = computed(() => (report.value?.allItems ?? []).filter(i => i.status === 'DONE'))
const inProgressItems = computed(() => (report.value?.allItems ?? []).filter(i => ['IN_PROGRESS', 'IN_REVIEW', 'TODO', 'BACKLOG'].includes(i.status)))

// ── 개인별 업무 일정 (Gantt) ─────────────────────────────────────────
const ganttDays = computed(() => {
  if (!report.value) return []
  const reportStart = report.value.startDate.slice(0, 10)
  const reportEnd   = report.value.endDate.slice(0, 10)
  const from = new Date(reportStart)
  from.setDate(from.getDate() - 3)
  const to = new Date(reportEnd)
  to.setDate(to.getDate() + 10)
  const days: { iso: string; dayName: string; mmdd: string; isWeekend: boolean; inReport: boolean }[] = []
  const cur = new Date(from)
  while (cur <= to) {
    const iso = cur.toISOString().slice(0, 10)
    const dow = cur.getDay()
    days.push({
      iso,
      dayName: ['일','월','화','수','목','금','토'][dow]!,
      mmdd: `${cur.getMonth() + 1}/${cur.getDate()}`,
      isWeekend: dow === 0 || dow === 6,
      inReport: iso >= reportStart && iso <= reportEnd,
    })
    cur.setDate(cur.getDate() + 1)
  }
  return days
})

const ganttPersons = computed(() => {
  if (!report.value) return []
  return report.value.byPerson
    .filter(p => p.completed.length || p.inProgress.length || p.delayed.length || p.upcoming.length)
    .map(p => ({
      userId:     p.userId,
      userName:   p.userName,
      doneCount:  p.completed.length,
      progCount:  p.inProgress.length,
      delayCount: p.delayed.length,
      items: (() => {
        const seen = new Set<string>()
        return [...p.delayed, ...p.inProgress, ...p.completed, ...p.upcoming]
          .filter(item => { if (seen.has(item.issueId)) return false; seen.add(item.issueId); return true })
      })(),
    }))
})

function ganttCellClass(item: WorkItem, dayIso: string): string {
  const fallback = report.value!.startDate.slice(0, 10)
  const s = (item.startDate ?? fallback).slice(0, 10)
  const e = (item.dueDate   ?? item.startDate ?? fallback).slice(0, 10)
  if (dayIso < s || dayIso > e) return ''
  if (item.isDelayed)                                           return 'gc-delay'
  if (item.status === 'DONE')                                   return 'gc-done'
  if (item.status === 'IN_PROGRESS' || item.status === 'IN_REVIEW') return 'gc-prog'
  return 'gc-todo'
}

function agendaStatusBadge(s?: string | null) {
  return { 예정: 'badge-blue', 진행중: 'badge-orange', 완료: 'badge-green', 지연: 'badge-red', 보류: 'badge-grey' }[s ?? ''] ?? 'badge-grey'
}
function impactBadge(s?: string | null) {
  return { 높음: 'badge-red', 보통: 'badge-orange', 낮음: 'badge-green' }[s ?? ''] ?? 'badge-grey'
}

function triggerPrint() { window.print() }

function onAfterPrint() { void router.back() }

onMounted(async () => {
  if (!isPreview) window.addEventListener('afterprint', onAfterPrint)
  try {
    report.value = await getWeeklyReport(reportId)
    if (!isPreview) {
      await new Promise(r => setTimeout(r, 300))
      window.print()
    }
  } catch (e) {
    alert(getErrorMessage(e, '보고서를 불러오지 못했습니다.'))
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('afterprint', onAfterPrint)
})
</script>

<style>
@page {
  size: A4 portrait;
  margin: 20mm 18mm 16mm 18mm;
}

@media print {
  html, body { background: white !important; margin: 0; padding: 0; }
  .screen-toolbar, .loading-wrap { display: none !important; }
}
</style>

<style scoped>
/* ═══════════════════════════════════════
   화면 툴바
═══════════════════════════════════════ */
.screen-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 13px;
  gap: 12px;
}
.toolbar-title { flex: 1; text-align: center; font-weight: 600; }
.btn-back  { background: none; border: 1px solid #475569; color: #cbd5e1; padding: 5px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-print { background: #3b82f6; border: none; color: white; padding: 6px 18px; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600; }
.loading-wrap { text-align: center; padding: 80px; color: #666; font-size: 14px; }
.preview-banner {
  background: #fef9c3;
  color: #854d0e;
  font-size: 12px;
  text-align: center;
  padding: 6px;
  border-bottom: 1px solid #fde68a;
}

@media print {
  .screen-toolbar, .loading-wrap, .preview-banner { display: none; }
}

/* ═══════════════════════════════════════
   문서 공통
═══════════════════════════════════════ */
#report-doc {
  font-family: '맑은 고딕', 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  font-size: 9.5pt;
  color: #111;
  background: white;
  max-width: 740px;
  margin: 0 auto;
  padding: 24px 20px 20px;
  line-height: 1.5;
}

@media print {
  #report-doc { max-width: 100%; padding: 0; }
}

/* ═══════════════════════════════════════
   문서 헤더
═══════════════════════════════════════ */
.doc-header {
  text-align: center;
  border-bottom: 2.5px solid #111;
  padding-bottom: 14px;
  margin-bottom: 10px;
}
.doc-org {
  font-size: 10pt;
  color: #444;
  margin-bottom: 6px;
  letter-spacing: 1px;
}
.doc-title {
  font-size: 20pt;
  font-weight: 700;
  letter-spacing: 6px;
  color: #111;
  margin-bottom: 8px;
}
.doc-period {
  font-size: 9.5pt;
  color: #555;
  letter-spacing: 0.5px;
}

/* ═══════════════════════════════════════
   보고 개요 메타 테이블
═══════════════════════════════════════ */
.meta-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 14px;
  font-size: 9pt;
}
.meta-table th {
  background: #f1f5f9;
  border: 1px solid #94a3b8;
  padding: 5px 10px;
  font-weight: 700;
  white-space: nowrap;
  width: 72px;
  color: #334155;
}
.meta-table td {
  border: 1px solid #94a3b8;
  padding: 5px 10px;
  color: #1e293b;
}

/* ═══════════════════════════════════════
   업무 현황 요약 테이블
═══════════════════════════════════════ */
.summary-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 18px;
  font-size: 10pt;
  text-align: center;
}
.summary-table th {
  border: 1px solid #475569;
  background: #1e293b;
  color: white;
  padding: 6px;
  font-weight: 700;
}
.summary-table td {
  border: 1px solid #94a3b8;
  padding: 8px;
  font-weight: 700;
  font-size: 12pt;
}
.sum-total { color: #111; }
.sum-done  { color: #15803d; }
.sum-prog  { color: #1d4ed8; }
.sum-delay { color: #b91c1c; }
.sum-rate  { color: #0369a1; }

/* ═══════════════════════════════════════
   빈 섹션
═══════════════════════════════════════ */
.empty-row {
  font-size: 8.5pt;
  color: #94a3b8;
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 2px;
  margin-bottom: 4px;
  font-style: italic;
}

/* ═══════════════════════════════════════
   섹션 헤딩
═══════════════════════════════════════ */
.section-heading {
  font-size: 10.5pt;
  font-weight: 700;
  color: #111;
  border-bottom: 1.5px solid #334155;
  padding: 4px 0 4px 2px;
  margin: 18px 0 8px;
  page-break-after: avoid;
}
.cnt {
  font-weight: 400;
  font-size: 9pt;
  color: #555;
  margin-left: 4px;
}

/* ═══════════════════════════════════════
   일반 표 (업무 목록)
═══════════════════════════════════════ */
.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5pt;
  margin-bottom: 4px;
}
.doc-table th {
  background: #334155;
  color: white;
  border: 1px solid #1e293b;
  padding: 5px 6px;
  text-align: center;
  font-weight: 600;
  white-space: nowrap;
}
.doc-table td {
  border: 1px solid #94a3b8;
  padding: 5px 6px;
  vertical-align: top;
  color: #1e293b;
}
.doc-table tr:nth-child(even) td { background: #f8fafc; }
.doc-table .c { text-align: center; }
.row-delay td { background: #fef2f2 !important; }

.cell-title { font-weight: 600; }
.cell-sub   { color: #475569; font-size: 8pt; margin-top: 2px; white-space: pre-wrap; }
.issue-key  { font-weight: 600; color: #1d4ed8; font-size: 8pt; }

/* ═══════════════════════════════════════
   뱃지 (상태/영향도)
═══════════════════════════════════════ */
.badge {
  display: inline-block;
  font-size: 7.5pt;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 2px;
}
.badge-blue   { background: #dbeafe; color: #1e40af; }
.badge-orange { background: #fed7aa; color: #9a3412; }
.badge-green  { background: #bbf7d0; color: #14532d; }
.badge-red    { background: #fee2e2; color: #991b1b; }
.badge-grey   { background: #e2e8f0; color: #475569; }

/* ═══════════════════════════════════════
   결정 필요 사항
═══════════════════════════════════════ */
.decision-block {
  border: 1px solid #94a3b8;
  border-radius: 2px;
  margin-bottom: 10px;
  page-break-inside: avoid;
}
.decision-title {
  background: #f1f5f9;
  font-weight: 700;
  font-size: 9.5pt;
  padding: 6px 10px;
  border-bottom: 1px solid #94a3b8;
}
.decision-detail {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5pt;
}
.decision-detail th {
  background: #f8fafc;
  border-right: 1px solid #cbd5e1;
  border-bottom: 1px solid #e2e8f0;
  padding: 5px 10px;
  font-weight: 600;
  width: 80px;
  vertical-align: top;
  color: #334155;
  white-space: nowrap;
}
.decision-detail td {
  border-bottom: 1px solid #e2e8f0;
  padding: 5px 10px;
  color: #1e293b;
  line-height: 1.6;
}
.decision-detail tr:last-child th,
.decision-detail tr:last-child td { border-bottom: none; }
.req-decision { font-weight: 600; color: #7c3aed; }

/* ═══════════════════════════════════════
   SR 현황
═══════════════════════════════════════ */
.sr-summary-table { margin-bottom: 8px; }
.sr-by-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.sr-status-badge {
  font-size: 7.5pt;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  padding: 2px 7px;
  color: #334155;
}
.sr-sub-heading {
  font-size: 9pt;
  font-weight: 700;
  color: #334155;
  margin: 10px 0 5px;
  padding-left: 4px;
}

/* ═══════════════════════════════════════
   관리자 코멘트
═══════════════════════════════════════ */
.comment-box {
  border: 1px solid #94a3b8;
  border-left: 4px solid #334155;
  padding: 8px 12px;
  background: #f8fafc;
  font-size: 9pt;
  line-height: 1.8;
  white-space: pre-wrap;
  color: #1e293b;
}

/* ═══════════════════════════════════════
   개인별 업무 일정 (Gantt)
═══════════════════════════════════════ */
.gantt-legend {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 7.5pt;
  align-items: center;
}
.gl {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.gl::before {
  content: '';
  display: inline-block;
  width: 16px;
  height: 10px;
  border-radius: 1px;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gl-done::before  { background: #15803d; }
.gl-prog::before  { background: #1d4ed8; }
.gl-delay::before { background: #b91c1c; }
.gl-todo::before  { background: #94a3b8; }

.gantt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 7pt;
  margin-bottom: 16px;
  table-layout: fixed;
}
.gantt-name-th {
  background: #1e293b;
  color: white;
  border: 1px solid #0f172a;
  padding: 4px 6px;
  text-align: left;
  font-weight: 600;
  width: 130px;
  white-space: nowrap;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gantt-day-th {
  background: #475569;
  color: white;
  border: 1px solid #0f172a;
  padding: 2px 1px;
  text-align: center;
  line-height: 1.3;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gantt-day-th.g-weekend  { background: #64748b; }
.gantt-day-th.g-in-report { background: #1e3a8a; }
.gantt-day-name { font-size: 6.5pt; font-weight: 700; }
.gantt-day-date { font-size: 5.5pt; opacity: 0.9; }

.gantt-person-row td {
  background: #e2e8f0;
  border: 1px solid #94a3b8;
  border-top: 2px solid #334155;
  padding: 3px 8px;
  font-weight: 700;
  font-size: 8pt;
  color: #1e293b;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gantt-person-stats {
  font-weight: 400;
  font-size: 6.5pt;
  color: #64748b;
  margin-left: 8px;
}

.gantt-task-row { height: 16px; }
.gantt-task-label {
  border: 1px solid #e2e8f0;
  border-right: 2px solid #94a3b8;
  padding: 2px 4px 2px 8px;
  font-size: 6.5pt;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #f8fafc;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gantt-day-cell {
  border: 1px solid #e2e8f0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.gc-done  { background: #15803d; }
.gc-prog  { background: #1d4ed8; }
.gc-delay { background: #b91c1c; }
.gc-todo  { background: #94a3b8; }
.gantt-empty {
  padding: 8px;
  color: #94a3b8;
  font-style: italic;
  text-align: center;
  font-size: 8pt;
}

/* ═══════════════════════════════════════
   문서 하단
═══════════════════════════════════════ */
.doc-footer {
  margin-top: 24px;
  padding-top: 6px;
  border-top: 1px solid #cbd5e1;
  display: flex;
  justify-content: space-between;
  font-size: 7.5pt;
  color: #94a3b8;
}
</style>
