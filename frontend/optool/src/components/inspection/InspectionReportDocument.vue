<template>
  <article class="report-paper">
    <header class="paper-cover" id="report-overview">
      <div class="cover-top">
        <span class="document-label">정기 서버 점검</span
        ><span class="document-state" :class="{ final: report.state === 'FINAL' }"
          >{{ report.state === 'FINAL' ? '확정본' : '초안' }} · {{ report.revision }}차</span
        >
      </div>
      <h1>{{ report.title }}</h1>
      <p class="cover-purpose">{{ report.purpose || '점검 목적이 작성되지 않았습니다.' }}</p>
      <dl class="cover-meta">
        <div>
          <dt>{{ isPlan ? '점검 예정일' : '점검일' }}</dt>
          <dd>
            {{ report.inspectionDate
            }}<span v-if="isPlan && report.plannedTime"> · {{ report.plannedTime }}</span>
          </dd>
        </div>
        <div>
          <dt>작성자</dt>
          <dd>{{ report.createdBy }}</dd>
        </div>
        <div>
          <dt>{{ report.state === 'FINAL' ? '확정 일시' : '데이터 조회 일시' }}</dt>
          <dd>{{ reportTime(report.finalizedAt || report.snapshot.capturedAt) }}</dd>
        </div>
      </dl>
      <div v-if="!isPlan" class="summary-grid">
        <div>
          <span>자원 점검 서버</span><strong>{{ stats.servers }}<small>대</small></strong
          ><em>보고서에 포함된 서버</em>
        </div>
        <div>
          <span>주의 · 위험</span
          ><strong :class="{ 'has-risk': stats.warning + stats.danger > 0 }"
            >{{ stats.warning + stats.danger }}<small>대</small></strong
          ><em>주의 {{ stats.warning }} · 위험 {{ stats.danger }}</em>
        </div>
        <div>
          <span>월간 작업 완료</span
          ><strong
            >{{ stats.done }}<small>/ {{ stats.planned }}건</small></strong
          ><em>미완료 {{ stats.pending }} · 이월 {{ stats.rolled }} · 제외 {{ stats.excluded }}</em>
        </div>
        <div>
          <span>작업 완료율</span
          ><strong
            >{{ stats.completionRate == null ? '—' : stats.completionRate
            }}<small v-if="stats.completionRate != null">%</small></strong
          ><em>{{
            stats.completionRate == null ? '집계할 작업 없음' : '제외한 작업은 집계하지 않음'
          }}</em>
        </div>
      </div>
      <div v-if="isPlan" class="summary-grid">
        <div>
          <span>자원 점검 대상</span
          ><strong>{{ report.snapshot.resourceTargets?.length || 0 }}<small>대</small></strong
          ><em>정기 점검 대상 서버</em>
        </div>
        <div>
          <span>월간 작업</span><strong>{{ stats.planned }}<small>건</small></strong
          ><em>등록된 작업 계획</em>
        </div>
        <div>
          <span>작업 대상 자산</span><strong>{{ plannedAssetCount }}<small>개</small></strong
          ><em>월간 작업에 연결된 자산</em>
        </div>
        <div>
          <span>참여 예정자</span
          ><strong>{{ report.participants?.length || 0 }}<small>명</small></strong
          ><em>점검 참여자 및 담당자</em>
        </div>
      </div>
      <div
        v-if="!isPlan || editable || report.overview"
        class="opinion-box"
        :class="{ 'screen-only': isPlan && !report.overview }"
      >
        <div class="section-title">
          <h2>{{ isPlan ? '사전 준비 및 유의사항' : '종합 의견' }}</h2>
          <q-btn
            v-if="editable"
            flat
            dense
            no-caps
            icon="edit_note"
            :label="isPlan ? '수정' : '의견 작성'"
            class="screen-only"
            color="primary"
            @click="emit('edit')"
          />
        </div>
        <p :class="{ placeholder: !report.overview }" class="prose">
          {{
            report.overview ||
            (isPlan
              ? '사전 준비, 서비스 중단 여부 등 필요한 내용을 작성해 주세요.'
              : '주요 점검 결과와 조치 내용을 작성해 주세요.')
          }}
        </p>
      </div>
      <p v-if="report.snapshot.historicalReconstruction" class="reconstruction-note">
        <q-icon name="history" /> 과거 월의 보고서입니다.
        {{ reportTime(report.snapshot.capturedAt) }}에 조회한 데이터로 작성되어 당시 내용과 다를 수
        있습니다.
      </p>
    </header>

    <section
      v-if="editable || report.participants?.length"
      id="report-participants"
      class="paper-section"
    >
      <div class="section-title">
        <div>
          <h2>
            참여자 및 역할
            <span class="participant-count">{{ report.participants?.length || 0 }}명</span>
          </h2>
        </div>
        <q-btn
          v-if="editable"
          flat
          dense
          no-caps
          icon="group_add"
          label="참여자 관리"
          class="screen-only"
          color="primary"
          @click="emit('participants')"
        />
      </div>
      <p v-if="!report.participants?.length" class="quiet-empty">
        ‘참여자 관리’에서 점검 참여자와 역할을 등록해 주세요.
      </p>
      <div v-for="person in participantsWithWork" :key="person.userId" class="participant-record">
        <div class="participant-record-person">
          <span class="participant-avatar" aria-hidden="true">{{ person.name.slice(0, 1) }}</span>
          <div>
            <b>{{ person.name }}</b
            ><span v-if="person.team" class="cell-sub">{{ person.team }}</span>
          </div>
        </div>
        <div class="participant-record-work">
          <div class="participant-roles">
            <span v-for="role in person.roles" :key="role.value">{{ role.label }}</span>
          </div>
          <p v-if="person.workSummary" class="prose">{{ person.workSummary }}</p>
          <p v-else-if="!person.work.length" class="prose placeholder">
            {{ isPlan ? '담당 업무 미작성' : '수행 업무 미작성' }}
          </p>
          <div v-if="person.work.length" class="participant-task-list">
            <span class="cell-sub">관련 월간 작업</span>
            <div v-for="task in person.work" :key="task.issueId">
              <button
                v-if="participantTask(task.issueId) && !participantTask(task.issueId)?.issueDeleted"
                class="participant-task-link screen-only"
                @click="openParticipantTask(task.issueId)"
              >
                {{ task.key }} · {{ task.title }}
              </button>
              <span v-else class="screen-only"
                >{{ task.key }} · {{ task.title
                }}<small v-if="!participantTask(task.issueId)"> · 이전 연결 작업</small></span
              >
              <span class="print-only"
                >{{ task.key }} · {{ task.title
                }}<small v-if="!participantTask(task.issueId)"> · 이전 연결 작업</small></span
              >
            </div>
          </div>
        </div>
      </div>
    </section>

    <InspectionPlanSections
      v-if="isPlan"
      :report="report"
      :editable="editable"
      @edit="emit('edit')"
      @issue="emit('issue', $event)"
    />
    <section v-if="!isPlan" id="report-resources" class="paper-section">
      <div class="section-title">
        <div>
          <div class="section-number">01</div>
          <h2>자원 사용량 및 조치 내역</h2>
        </div>
        <span v-if="report.snapshot.servers.length" class="section-count"
          >확인 필요 {{ resourceFindings.length }}대</span
        >
      </div>
      <p class="section-description">
        {{
          isPlan
            ? '정기 자원 점검 대상 · 월간 작업'
            : report.snapshot.source
              ? `${report.snapshot.source.reportDate} 점검 시점의 측정값`
              : '선택한 월의 점검 데이터가 없습니다.'
        }}<template v-if="report.snapshot.comparison">
          · 비교 {{ report.snapshot.comparison.reportDate }}</template
        >
      </p>
      <template v-if="report.snapshot.servers.length">
        <div class="resource-summary">
          <p>
            전체 {{ report.snapshot.servers.length }}대 ·
            <strong>확인 필요 {{ resourceFindings.length }}대</strong> · 특이사항 없음
            {{ resourceClearCount }}대
          </p>
          <q-btn
            v-if="resourceClearCount"
            flat
            dense
            no-caps
            color="primary"
            class="screen-only"
            :label="
              showAllResources ? '나머지 서버 접기' : `나머지 서버 ${resourceClearCount}대 보기`
            "
            :icon-right="showAllResources ? 'expand_less' : 'expand_more'"
            :aria-expanded="showAllResources"
            aria-controls="report-all-resources"
            @click="showAllResources = !showAllResources"
          />
        </div>
        <table v-if="resourceFindings.length" class="resource-review-table">
          <thead>
            <tr>
              <th>서버 / IP</th>
              <th>확인 사항</th>
              <th>조치 내역</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in resourceFindings" :key="row.server.key">
              <td>
                <button class="server-name screen-only" @click="emit('server', row.server)">
                  {{ row.server.asset?.name || row.server.hostName }}
                </button>
                <b class="print-only">{{ row.server.asset?.name || row.server.hostName }}</b>
                <div class="cell-sub">{{ row.server.ip || 'IP 없음' }}</div>
              </td>
              <td>
                <div v-for="item in row.metrics" :key="item.kind" class="resource-review-metric">
                  <div class="resource-review-reading">
                    <b>{{ item.label }}</b>
                    <strong
                      v-if="item.metric.value != null"
                      class="metric-value"
                      :class="item.level"
                    >
                      {{ percent(item.metric.value) }}
                    </strong>
                    <span class="finding-label" :class="item.level">{{
                      item.level === 'danger'
                        ? '위험'
                        : item.level === 'warning'
                          ? '주의'
                          : '측정값 없음'
                    }}</span>
                    <span
                      v-if="item.metric.value != null && item.metric.delta != null"
                      class="resource-review-delta"
                    >
                      {{ delta(item.metric.delta) }}
                    </span>
                  </div>
                  <div v-if="item.metric.value != null" class="cell-sub">
                    {{ measurementBasis(item.metric)
                    }}{{ item.metric.path ? ` · ${item.metric.path}` : '' }}
                  </div>
                </div>
                <div v-if="row.findings.length" class="resource-other-findings">
                  <p v-for="(finding, i) in row.findings" :key="i" :class="finding.level">
                    {{ finding.label }}
                  </p>
                </div>
                <p v-if="!row.metrics.length && !row.findings.length" class="resource-pending-note">
                  {{ row.server.action ? '진행 중인 조치 확인' : '점검표의 조치 사항 확인' }}
                </p>
              </td>
              <td class="resource-action-cell">
                <span class="mobile-action-label">조치 내역</span>
                <InspectionReportAction
                  :action="row.server.action"
                  :action-items="row.server.actionItems"
                  :host-name="row.server.hostName"
                  :editable="editable"
                  @edit="emit('action', { rowKey: row.server.key, hostName: row.server.hostName })"
                />
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else-if="!pendingUnmatchedActions.length" class="resource-all-clear quiet-empty">
          확인이 필요한 항목이 없습니다.
        </p>
        <p class="table-footnote">
          {{ report.snapshot.thresholds.warning }}% 이상 주의 ·
          {{ report.snapshot.thresholds.danger }}% 이상 위험 · 측정값이 없는 항목도 표시합니다.
        </p>
        <div
          v-if="showAllResources && resourceClearCount"
          id="report-all-resources"
          class="resource-table-wrap screen-only"
        >
          <table class="resource-table">
            <thead>
              <tr>
                <th>서버 / IP</th>
                <th>CPU</th>
                <th>RAM</th>
                <th>디스크 최대</th>
                <th>확인 사항</th>
                <th>조치 내역</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="server in otherResourceServers" :key="server.key">
                <td>
                  <button class="server-name screen-only" @click="emit('server', server)">
                    {{ server.asset?.name || server.hostName }}</button
                  ><b class="print-only">{{ server.asset?.name || server.hostName }}</b>
                  <div class="cell-sub">{{ server.ip || 'IP 없음' }}</div>
                  <div
                    v-if="server.asset && server.asset.name !== server.hostName"
                    class="cell-sub"
                  >
                    원본 {{ server.hostName }}
                  </div>
                  <div v-if="!server.asset" class="mapping-note">자산 연결 미확인</div>
                </td>
                <td v-for="kind in metricKinds" :key="kind">
                  <div class="metric-value" :class="metricClass(server[kind].value)">
                    {{ percent(server[kind].value) }}
                  </div>
                  <div class="metric-track" aria-hidden="true">
                    <span
                      :class="metricClass(server[kind].value)"
                      :style="{ width: `${server[kind].value || 0}%` }"
                    />
                  </div>
                  <div class="cell-sub">
                    {{ measurementBasis(server[kind])
                    }}{{ server[kind].path ? ` · ${server[kind].path}` : '' }}
                  </div>
                  <div class="metric-delta">{{ delta(server[kind].delta) }}</div>
                </td>
                <td>
                  <span class="finding-label" :class="server.level">{{
                    server.level === 'danger'
                      ? '위험'
                      : server.level === 'warning'
                        ? '주의'
                        : metricKinds.every((k) => server[k].value == null)
                          ? '측정값 없음'
                          : '사용량 양호'
                  }}</span>
                  <div v-if="server.level !== 'none'" class="cell-sub">
                    {{ server.findings.map((f) => f.label).join(' · ') }}
                  </div>
                  <div
                    v-else-if="metricKinds.some((k) => server[k].value == null)"
                    class="cell-sub"
                  >
                    일부 측정값 없음
                  </div>
                </td>
                <td>
                  <InspectionReportAction
                    v-if="editable || server.action || inspectionActionNote(server.actionItems)"
                    :action="server.action"
                    :action-items="server.actionItems"
                    :host-name="server.hostName"
                    :editable="editable"
                    @edit="emit('action', { rowKey: server.key, hostName: server.hostName })"
                  />
                  <span v-else class="cell-sub">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="document-empty">
        <q-icon name="insert_chart_outlined" size="28px" /><span>점검 데이터 없음</span>
        <p>자원 점검에서 데이터를 업로드한 뒤 ‘최신 내용 불러오기’를 눌러 주세요.</p>
      </div>
      <div v-if="pendingUnmatchedActions.length" class="unmatched-actions">
        <h3>
          대상 서버 확인이 필요한 조치 <span>{{ pendingUnmatchedActions.length }}건</span>
        </h3>
        <p class="cell-sub">
          점검 데이터에서 대상 서버를 찾을 수 없거나 호스트명이 중복된 미완료 조치입니다.
        </p>
        <div v-for="action in pendingUnmatchedActions" :key="action.id" class="unmatched-action">
          <b>{{ action.hostName }}</b>
          <InspectionReportAction
            :action="action"
            :host-name="action.hostName"
            :editable="editable"
            @edit="emit('action', { actionId: action.id, hostName: action.hostName })"
          />
        </div>
      </div>
      <div v-if="report.snapshot.missingAssetResources.length" class="missing-resources">
        <b>점검 데이터가 없는 작업 대상 서버</b>
        <p>{{ report.snapshot.missingAssetResources.map((a) => a.name).join(' · ') }}</p>
      </div>
    </section>

    <InspectionPlanComparison v-if="!isPlan" :report="report" />
    <section v-if="!isPlan" id="report-tasks" class="paper-section">
      <div class="section-title">
        <div>
          <div class="section-number">02</div>
          <h2>월간 작업 결과</h2>
        </div>
        <span class="section-count">{{ stats.planned }}건</span>
      </div>
      <p class="section-description">
        {{ formatInspectionMonth(report.month) }}에 등록된 점검 작업입니다. 여러 자산에 연결된
        작업도 1건으로 집계합니다.
      </p>
      <div v-if="!stats.planned" class="quiet-empty">해당 월에 등록된 점검 작업이 없습니다.</div>
      <div v-for="group in taskGroups" :key="group.label" class="task-report-group">
        <h3>
          {{ group.label }} <span>{{ group.tasks.length }}</span>
        </h3>
        <div v-for="task in group.tasks" :key="task.issueId" class="report-task">
          <div class="report-task-heading">
            <div>
              <button
                class="issue-link screen-only"
                :disabled="task.issueDeleted"
                @click="emit('issue', task)"
              >
                {{ task.issue.key }}</button
              ><span class="print-only issue-key-print">{{ task.issue.key }}</span
              ><b>{{ task.issue.title }}</b>
            </div>
            <span
              class="task-label"
              :class="{ done: task.state === 'ACTIVE' && task.issue.status === 'DONE' }"
              >{{ inspectionStatusLabel(task) }}</span
            >
          </div>
          <div class="report-task-meta">
            <span>{{ task.common ? '공통 작업' : task.assets.map((a) => a.name).join(' · ') }}</span
            ><span>담당 {{ task.issue.assigneeName }}</span
            ><span
              >계획 {{ task.plannedStart?.slice(0, 10) || '미정' }} ~
              {{ task.plannedEnd?.slice(0, 10) || '미정' }}</span
            >
          </div>
          <div class="task-documents">
            <InspectionWorkPlanLinks :plans="taskPlans(task)" back-label="점검 결과서로 돌아가기" />
            <InspectionWorkPlanLinks :plans="task.result?.workResults" kind="RESULT" back-label="점검 결과서로 돌아가기" />
          </div>
          <div class="task-result-copy">
            <p v-if="task.result?.content || !hasInspectionResult(task)" class="prose" :class="{ placeholder: !task.result?.content }">
              {{ task.result?.content || '작업 결과 미작성' }}
            </p>
            <div v-if="editable" class="task-edit-actions screen-only">
              <q-btn
                flat
                dense
                no-caps
                label="수정"
                color="primary"
                icon="edit"
                :aria-label="`${task.issue.title} 월간 작업 결과 수정`"
                @click="emit('result', task)"
              />
            </div>
          </div>
          <p v-if="task.result?.performedOn" class="cell-sub">
            작업일 {{ task.result.performedOn }} · 결과 작성 {{ task.result.updatedBy }} ·
            {{ reportTime(task.result.updatedAt) }}
          </p>
          <div v-if="task.result?.followUp?.trim()" class="task-followup">
            <b>추가 작업 계획</b>
            <p class="prose">{{ task.result.followUp }}</p>
          </div>
          <p v-if="task.reason" class="task-reason">
            {{
              task.state === 'ROLLED'
                ? `${task.toMonth} 이월`
                : task.state === 'EXCLUDED'
                  ? '제외 사유'
                  : '등록 사유'
            }}
            · {{ task.reason }}
          </p>
        </div>
      </div>
    </section>

    <section
      v-if="editable || notes.length"
      id="report-followup"
      class="paper-section"
      :class="{ 'screen-only': !notes.length }"
    >
      <div class="section-title">
        <div>
          <div class="section-number">03</div>
          <h2>{{ noteLabel }}</h2>
        </div>
        <q-btn
          v-if="editable"
          flat
          round
          dense
          color="primary"
          icon="add"
          :aria-label="`${noteLabel} 추가`"
          class="screen-only"
          @click="emit('notes')"
          ><q-tooltip>{{ noteLabel }} 추가</q-tooltip></q-btn
        >
      </div>
      <ol v-if="notes.length" class="additional-notes">
        <li v-for="(note, index) in notes" :key="note.id" class="additional-note">
          <div class="note-row">
            <p class="prose">{{ note.content }}</p>
            <div v-if="editable" class="note-actions screen-only">
              <q-btn
                flat
                dense
                no-caps
                color="primary"
                icon="edit"
                label="수정"
                :aria-label="`${noteLabel} ${index + 1} 수정`"
                @click="emit('notes', note)"
              />
              <q-btn
                flat
                dense
                no-caps
                color="grey-7"
                icon="delete_outline"
                label="삭제"
                :aria-label="`${noteLabel} ${index + 1} 삭제`"
                @click="emit('delete-note', note)"
              />
            </div>
          </div>
        </li>
      </ol>
      <p v-else class="quiet-empty">등록된 항목이 없습니다.</p>
    </section>

    <section
      v-if="!isPlan && report.includeAppendix"
      id="report-appendix"
      class="paper-section appendix-section"
    >
      <div class="appendix-heading">
        <div>
          <div class="section-number">부록</div>
          <h2>
            서버별 상세 점검표
            <span class="appendix-count">{{ report.snapshot.servers.length }}대</span>
          </h2>
        </div>
        <q-select
          v-if="report.snapshot.servers.length > 1"
          v-model="appendixServer"
          :options="appendixOptions"
          label="서버 바로가기"
          outlined
          dense
          emit-value
          map-options
          class="appendix-jump screen-only"
          @update:model-value="jumpToAppendixServer"
        />
      </div>
      <p v-if="report.snapshot.source" class="section-description">
        측정일 {{ report.snapshot.source.reportDate }}
        <template v-if="report.snapshot.comparison">
          · 비교일 {{ report.snapshot.comparison.reportDate }}</template
        >
      </p>
      <p v-if="!report.snapshot.servers.length" class="quiet-empty">
        상세 점검표에 표시할 서버 데이터가 없습니다.
      </p>
      <InspectionReportServerSheet
        v-for="(server, index) in report.snapshot.servers"
        :key="server.key"
        :server="server"
        :index="index"
        :thresholds="report.snapshot.thresholds"
        :editable="editable"
        @action="emit('action', { rowKey: server.key, hostName: server.hostName })"
      />
      <div v-if="report.snapshot.unmatchedActions.length" class="unmatched-actions">
        <h3>대상 서버를 확인할 수 없는 조치</h3>
        <div
          v-for="action in report.snapshot.unmatchedActions"
          :key="action.id"
          class="unmatched-action"
        >
          <b>{{ action.hostName }}</b>
          <InspectionReportAction
            :action="action"
            :host-name="action.hostName"
            :editable="editable"
            @edit="emit('action', { actionId: action.id, hostName: action.hostName })"
          />
        </div>
      </div>
    </section>
    <footer class="document-footer">
      <p>
        <b>자료 출처</b>
        {{
          isPlan
            ? '정기 자원 점검 대상 · 월간 작업'
            : report.snapshot.source
              ? `${report.snapshot.source.title} · ${report.snapshot.source.reportDate} · 업로드 ${reportTime(report.snapshot.source.uploadedAt)}`
              : '점검 데이터 없음'
        }}
      </p>
      <p>
        집계 {{ reportTime(report.snapshot.capturedAt) }} ·
        {{ report.state === 'FINAL' ? `${report.finalizedBy} 확정` : '작성 중인 초안' }} ·
        {{ report.revision }}차
      </p>
    </footer>
  </article>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { participantWork } from 'src/utils/inspectionParticipants';
import {
  resourceReview,
  resourceMetricLevel,
  inspectionActionNote,
} from 'src/utils/inspectionReportResources';
import InspectionReportAction from './InspectionReportAction.vue';
import InspectionPlanSections from './InspectionPlanSections.vue';
import InspectionPlanComparison from './InspectionPlanComparison.vue';
import InspectionWorkPlanLinks from './InspectionWorkPlanLinks.vue';
import InspectionReportServerSheet from './InspectionReportServerSheet.vue';
import { measurementBasis } from 'src/utils/inspectionMeasurements';
import { formatInspectionMonth, inspectionStatusLabel, hasInspectionResult } from 'src/services/inspection';
import {
  percent,
  reportTime,
  reportNotes,
  type ReportNote,
  type InspectionReport,
  type ReportTask,
  type ResourceServer,
  type ReportActionTarget,
} from 'src/services/inspectionReports';
const props = defineProps<{ report: InspectionReport; editable: boolean }>();
const emit = defineEmits<{
  edit: [];
  participants: [];
  result: [task: ReportTask];
  notes: [note?: ReportNote];
  'delete-note': [note: ReportNote];
  action: [target: ReportActionTarget];
  server: [server: ResourceServer];
  issue: [task: ReportTask];
}>();
const isPlan = computed(() => props.report.kind === 'PLAN');
const taskPlans = (task: ReportTask) => {
  const plans = task.workPlan ? [task.workPlan, ...(task.workPlans || [])] : task.workPlans || [];
  return plans.filter((plan, index) => plans.findIndex((item) => item.id === plan.id) === index);
};
const noteLabel = computed(() => (isPlan.value ? '추가 안내' : '추가 확인 사항'));
const plannedAssetCount = computed(
  () => new Set(props.report.snapshot.tasks.flatMap((t) => t.assets.map((a) => a.id))).size,
);
const stats = computed(() => props.report.snapshot.stats);
const notes = computed(() => reportNotes(props.report));
const resourceFindings = computed(() => resourceReview(props.report.snapshot));
const otherResourceServers = computed(() => {
  const displayedKeys = new Set(resourceFindings.value.map((row) => row.server.key));
  return props.report.snapshot.servers.filter((server) => !displayedKeys.has(server.key));
});
const resourceClearCount = computed(() => otherResourceServers.value.length);
const pendingUnmatchedActions = computed(() =>
  props.report.snapshot.unmatchedActions.filter((action) => action.isResolved === false),
);
const showAllResources = ref(false);
const appendixServer = ref<string | null>(null);
const appendixOptions = computed(() =>
  props.report.snapshot.servers.map((server) => ({
    label: [server.hostName, server.ip].filter(Boolean).join(' · '),
    value: server.key,
  })),
);
function jumpToAppendixServer(key: string | null) {
  if (key)
    document
      .getElementById(`appendix-server-${key}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
watch(
  () => props.report.id,
  () => {
    showAllResources.value = false;
    appendixServer.value = null;
  },
);
const participantsWithWork = computed(() =>
  (props.report.participants || []).map((person) => ({
    ...person,
    work: participantWork(person),
  })),
);
const participantTaskMap = computed(
  () => new Map(props.report.snapshot.tasks.map((t) => [t.issueId, t])),
);
const participantTask = (id: string) => participantTaskMap.value.get(id);
function openParticipantTask(id: string) {
  const task = participantTask(id);
  if (task && !task.issueDeleted) emit('issue', task);
}
const metricKinds = ['cpu', 'ram', 'disk'] as const;
const taskGroups = computed(() =>
  [
    { label: '자산별 작업', tasks: props.report.snapshot.tasks.filter((t) => !t.common) },
    { label: '공통 작업', tasks: props.report.snapshot.tasks.filter((t) => t.common) },
  ].filter((g) => g.tasks.length),
);
const metricClass = (v: number | null) => resourceMetricLevel(v, props.report.snapshot.thresholds);
const delta = (v: number | null) =>
  v == null ? '비교할 값 없음' : v === 0 ? '이전과 동일' : `이전 대비 ${v > 0 ? '+' : ''}${v}%p`;
</script>
<style scoped>
.additional-notes {
  margin: 0;
  padding-left: 24px;
}
.additional-note {
  padding: 14px 0 14px 4px;
  border-bottom: 1px solid #e8edf3;
}
.additional-note:last-child {
  border-bottom: 0;
}
.additional-note::marker {
  color: #718399;
  font-weight: 600;
  font-size: 12px;
}
.note-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.note-row > .prose {
  flex: 1;
  min-width: 0;
  margin: 0;
}
.note-actions {
  display: flex;
  flex-shrink: 0;
  gap: 4px;
}
.note-actions .q-btn {
  font-size: 12px;
}
@media (max-width: 600px) {
  .note-row {
    flex-direction: column;
    gap: 6px;
  }
  .note-actions {
    align-self: flex-end;
  }
}
@media print {
  #report-followup {
    break-inside: avoid;
  }
  .additional-note {
    break-inside: avoid;
  }
}
.task-edit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}
.task-followup {
  margin-top: 14px;
  font-size: 12px;
  color: #617187;
}
.task-followup b {
  font-size: 11px;
  font-weight: 600;
}
.task-followup .prose {
  margin: 5px 0 0;
}
.additional-notes {
  margin-top: 20px;
}
.participant-count {
  color: #7b8b9c;
  font-size: 12px;
  font-weight: 400;
  margin-left: 8px;
}
.participant-record {
  display: grid;
  grid-template-columns: 145px minmax(0, 1fr);
  gap: 20px;
  padding: 22px 0;
  border-bottom: 1px solid #edf0f4;
}
.participant-record:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}
.participant-record-person {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.participant-avatar {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #608196;
  background: #f0f5f8;
  font-size: 12px;
}
.participant-record-person b {
  display: block;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.participant-record-person .cell-sub {
  display: block;
  margin-top: 3px;
}
.participant-record-work {
  min-width: 0;
}
.participant-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #517487;
}
.participant-task-list {
  margin-top: 12px;
  color: #697f93;
  font-size: 11px;
  line-height: 1.8;
  overflow-wrap: anywhere;
}
.participant-task-list > .cell-sub {
  display: block;
  margin-bottom: 4px;
}
.participant-task-list > div {
  margin-top: 3px;
}
.participant-task-link {
  background: none;
  border: 0;
  padding: 0;
  color: #5a7b96;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.participant-task-link:hover {
  text-decoration: underline;
}
@media (max-width: 700px) {
  .participant-record {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .participant-record-work {
    padding-left: 40px;
  }
}
@media print {
  .participant-record {
    grid-template-columns: 135px minmax(0, 1fr);
    gap: 16px;
    break-inside: avoid;
  }
  .participant-record-work {
    padding-left: 0;
  }
  .participant-avatar {
    print-color-adjust: exact;
  }
  .participant-task-list {
    color: #576b7c;
  }
}
.report-paper {
  background: white;
  border: 1px solid #e2e8ef;
  border-radius: 12px;
  box-shadow: 0 4px 20px #23364b06;
  color: #243449;
  min-width: 0;
  overflow: hidden;
}
.paper-cover {
  padding: 42px 42px 32px;
  scroll-margin-top: 110px;
}
.cover-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.document-label {
  color: #718b9b;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
}
.document-state {
  font-size: 11px;
  padding: 5px 10px;
  color: #857453;
  background: #f8f3e8;
  border-radius: 5px;
}
.document-state.final {
  background: #eaf5f0;
  color: #357861;
}
h1 {
  font-size: 29px;
  font-weight: 750;
  line-height: 1.4;
  letter-spacing: -1px;
  margin: 25px 0 12px;
  overflow-wrap: anywhere;
}
.cover-purpose {
  font-size: 13px;
  color: #738195;
  line-height: 1.8;
  white-space: pre-wrap;
}
.cover-meta {
  display: grid;
  grid-template-columns: 1fr 1fr 1.5fr;
  gap: 18px;
  font-size: 12px;
  margin: 26px 0 30px;
}
.cover-meta dt {
  color: #8c97a6;
  margin-bottom: 5px;
}
.cover-meta dd {
  margin: 0;
  color: #536379;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 2px solid #395e73;
  padding-top: 23px;
  gap: 15px;
}
.summary-grid > div {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.summary-grid span {
  font-size: 12px;
  color: #68798c;
}
.summary-grid strong {
  font-size: 33px;
  font-weight: 650;
  line-height: 1.2;
  letter-spacing: -1px;
}
.summary-grid small {
  font-size: 13px;
  font-weight: 400;
  margin-left: 5px;
  color: #8692a1;
  letter-spacing: 0;
}
.summary-grid em {
  font-style: normal;
  font-size: 10px;
  color: #8692a1;
  line-height: 1.7;
}
.has-risk {
  color: #b0753f;
}
.opinion-box {
  margin-top: 30px;
  padding: 20px 22px;
  border-radius: 8px;
  background: #f6f8fa;
}
.opinion-box h2 {
  font-size: 14px;
}
.opinion-box p {
  font-size: 13px;
  margin: 10px 0 0;
}
.section-title {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
h2 {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.4px;
  line-height: 1.5;
  margin: 4px 0;
}
h3 {
  font-size: 13px;
  line-height: 1.6;
  font-weight: 700;
  margin: 20px 0 10px;
}
h3 span {
  font-weight: 400;
  color: #8b97a5;
  margin-left: 5px;
}
h4 {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.5;
  margin: 8px 0;
}
.paper-section {
  padding: 30px 42px;
  border-top: 1px solid #e9edf2;
  scroll-margin-top: 110px;
}
.section-number {
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #8394a5;
  font-weight: 600;
}
.section-count {
  font-size: 12px;
  color: #8492a2;
}
.section-description {
  font-size: 12px;
  line-height: 1.8;
  color: #7f8c9c;
  margin: 10px 0 20px;
}
.resource-table-wrap {
  overflow-x: auto;
}
.resource-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 14px;
  color: #718195;
  font-size: 12px;
}
.resource-summary p {
  margin: 0;
  line-height: 1.8;
}
.resource-summary strong {
  color: #42566a;
  font-weight: 600;
}
.resource-summary .q-btn {
  font-size: 11px;
}
.resource-review-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 12px;
}
.resource-review-table th {
  padding: 10px 12px;
  background: #f5f7fa;
  color: #718195;
  font-size: 11px;
  font-weight: 500;
  text-align: left;
}
.resource-review-table th:first-child {
  width: 22%;
}
.resource-review-table th:nth-child(2) {
  width: 33%;
}
.resource-review-table td {
  padding: 16px 12px;
  border-bottom: 1px solid #edf0f3;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.resource-review-metric + .resource-review-metric {
  margin-top: 14px;
}
.resource-review-reading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
}
.resource-review-reading > b {
  min-width: 40px;
  font-weight: 500;
}
.resource-review-delta {
  color: #748295;
  font-size: 11px;
}
.resource-review-table .finding-label.missing {
  color: #977039;
}
.resource-other-findings p,
.resource-pending-note {
  margin: 0 0 6px;
  color: #986c2f;
  line-height: 1.8;
}
.resource-other-findings .danger {
  color: #bb5a53;
}
.resource-review-metric + .resource-other-findings {
  margin-top: 14px;
}
.mobile-action-label {
  display: none;
}
.unmatched-actions {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid #edf0f3;
}
.unmatched-actions h3 {
  font-size: 13px;
}
.unmatched-actions h3 span {
  color: #7e8c9c;
  font-weight: 400;
  margin-left: 8px;
}
.unmatched-action {
  display: grid;
  grid-template-columns: minmax(120px, 22%) minmax(0, 1fr);
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid #edf0f3;
}
.unmatched-action > b {
  font-size: 12px;
  overflow-wrap: anywhere;
}
.resource-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 850px;
  font-size: 12px;
  table-layout: fixed;
}
.resource-table th {
  padding: 11px 10px;
  background: #f5f7fa;
  text-align: left;
  color: #718195;
  font-size: 11px;
  font-weight: 500;
}
.resource-table th:first-child {
  width: 18%;
}
.resource-table th:last-child {
  width: 28%;
}
.resource-table td {
  padding: 15px 10px;
  vertical-align: top;
  border-bottom: 1px solid #edf0f3;
  overflow-wrap: anywhere;
}
.server-name {
  padding: 0;
  background: none;
  border: 0;
  color: #3b6384;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  text-align: left;
}
.server-name:hover,
.issue-link:hover {
  text-decoration: underline;
}
.cell-sub {
  font-size: 11px;
  line-height: 1.7;
  color: #748295;
  margin-top: 5px;
  overflow-wrap: anywhere;
}
.mapping-note {
  color: #a38d6a;
  font-size: 9px;
  margin-top: 4px;
}
.metric-value {
  font-weight: 650;
  font-size: 14px;
}
.metric-value.danger {
  color: #b95d59;
}
.metric-value.warning {
  color: #b9853d;
}
.metric-value.missing {
  color: #a6b0bc;
}
.metric-track {
  height: 3px;
  border-radius: 3px;
  background: #f0f3f6;
  margin: 7px 0;
  width: 70px;
  max-width: 100%;
}
.metric-track span {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: #9aafbc;
}
.metric-track .danger {
  background: #cd8280;
}
.metric-track .warning {
  background: #d4af72;
}
.metric-delta {
  font-size: 9px;
  color: #8795a5;
  margin-top: 6px;
}
.finding-label {
  display: inline-block;
  font-size: 10px;
  color: #738496;
}
.finding-label.warning {
  color: #ac7f37;
}
.finding-label.danger {
  color: #ba615a;
}
.table-footnote {
  font-size: 10px;
  color: #8e99a6;
  line-height: 1.9;
  margin-top: 13px;
}
.missing-resources {
  background: #faf8f2;
  padding: 13px 15px;
  border-radius: 6px;
  font-size: 11px;
  color: #8b7857;
}
.missing-resources p {
  margin: 5px 0 0;
  line-height: 1.7;
}
.document-empty {
  padding: 30px;
  background: #f8fafb;
  border-radius: 8px;
  text-align: center;
  color: #9aa7b7;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}
.document-empty p {
  margin: 0;
  font-size: 11px;
}
.quiet-empty {
  color: #94a0ae;
  font-size: 12px;
  padding: 16px 0;
  line-height: 1.8;
}
.prose {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.9;
  font-size: 13px;
  color: #586a7f;
  margin: 8px 0;
}
.prose.placeholder {
  color: #98a4b2;
}
.report-task {
  padding: 18px 0;
  border-top: 1px solid #edf0f3;
}
.report-task-heading {
  display: flex;
  justify-content: space-between;
  gap: 15px;
  align-items: baseline;
  font-size: 13px;
}
.report-task-heading > div {
  min-width: 0;
  overflow-wrap: anywhere;
}
.issue-link,
.issue-key-print {
  font: inherit;
  font-size: 10px;
  color: #8299ad;
  border: 0;
  background: none;
  padding: 0;
  margin-right: 8px;
  cursor: pointer;
}
.issue-link:disabled {
  color: #a0a8b0;
  cursor: default;
}
.task-label {
  white-space: nowrap;
  font-size: 10px;
  color: #8a7d65;
  padding: 3px 8px;
  background: #f6f3ed;
  border-radius: 4px;
}
.task-label.done {
  background: #edf5f1;
  color: #578570;
}
.report-task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 13px;
  font-size: 10px;
  color: #8b98a6;
  margin: 9px 0;
}
.task-result-copy {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.task-result-copy p {
  flex: 1;
}
.task-result-copy .q-btn {
  font-size: 11px;
  flex-shrink: 0;
}
.task-reason {
  font-size: 11px;
  color: #a08b65;
  margin: 8px 0 0;
  line-height: 1.8;
}
.reconstruction-note {
  font-size: 10px;
  color: #9b8b6b;
  line-height: 1.8;
  margin: 20px 0 0;
}
.appendix-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}
.appendix-count {
  margin-left: 6px;
  font-size: 12px;
  color: #718195;
  font-weight: 400;
}
.appendix-jump {
  width: 260px;
  max-width: 100%;
  font-size: 12px;
}
.document-footer {
  background: #fafbfd;
  border-top: 1px solid #e9edf2;
  padding: 20px 42px;
  font-size: 10px;
  line-height: 1.9;
  color: #93a0ad;
}
.document-footer p {
  margin: 3px 0;
}
.document-footer b {
  font-weight: 500;
  margin-right: 5px;
}
.print-only {
  display: none;
}
@media (max-width: 700px) {
  .resource-review-table thead {
    display: none;
  }
  .resource-review-table tr {
    display: block;
    padding: 16px 0;
    border-bottom: 1px solid #edf0f3;
  }
  .resource-review-table td {
    display: block;
    padding: 0;
    border: 0;
  }
  .resource-review-table td + td {
    margin-top: 12px;
  }
  .resource-review-table .resource-action-cell {
    padding: 12px;
    background: #f8fafc;
    border-radius: 6px;
  }
  .mobile-action-label {
    display: block;
    margin-bottom: 7px;
    color: #7e8c9c;
    font-size: 10px;
  }
  .unmatched-action {
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }
  .paper-cover,
  .paper-section {
    padding: 26px 20px;
  }
  .document-footer {
    padding: 18px 20px;
  }
  h1 {
    font-size: 23px;
  }
  .summary-grid {
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }
  .cover-meta {
    grid-template-columns: 1fr 1fr;
  }
  .cover-meta > div:nth-child(3) {
    grid-column: 1 / -1;
  }
  .cover-top {
    align-items: flex-start;
  }
  .document-label {
    font-size: 8px;
  }
  .document-state {
    font-size: 9px;
  }
  .task-result-copy {
    display: block;
  }
  .report-paper {
    border-radius: 8px;
  }
}
@media print {
  .resource-review-table thead {
    display: table-header-group;
  }
  .resource-review-table tr {
    display: table-row;
    break-inside: avoid;
  }
  .resource-review-table td {
    display: table-cell;
    padding: 12px;
    border-bottom: 1px solid #edf0f3;
  }
  .resource-review-table .resource-action-cell {
    background: none;
    border-radius: 0;
  }
  .mobile-action-label {
    display: none;
  }
  .unmatched-action {
    grid-template-columns: minmax(120px, 22%) minmax(0, 1fr);
  }
  .report-task {
    break-inside: avoid;
  }
  .resource-table-wrap {
    break-after: avoid;
  }
  .table-footnote {
    break-before: avoid;
  }
  .screen-only {
    display: none !important;
  }
  .print-only {
    display: inline;
  }
  .report-paper {
    border: 0;
    border-radius: 0;
    box-shadow: none;
    width: 100%;
    overflow: visible;
    font-size: 11px;
  }
  .paper-cover {
    padding: 12px 0 22px;
  }
  .paper-section {
    padding: 24px 0;
  }
  .cover-top,
  .summary-grid,
  .cover-meta {
    break-inside: avoid;
  }
  h1 {
    font-size: 26px;
  }
  h2,
  h3,
  .section-title,
  .section-description {
    break-after: avoid;
  }
  .resource-table-wrap {
    overflow: visible;
  }
  .resource-table {
    min-width: 0;
    table-layout: fixed;
    font-size: 10px;
  }
  .resource-table td {
    padding: 12px 7px;
  }
  .resource-table thead {
    display: table-header-group;
  }
  .resource-table tr,
  .report-task-heading {
    break-inside: avoid;
  }
  .resource-table th:first-child {
    width: 22%;
  }
  .resource-table th:last-child {
    width: 24%;
  }
  .summary-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .cover-meta {
    grid-template-columns: 1fr 1fr 1.5fr;
  }
  .cover-meta > div:nth-child(3) {
    grid-column: auto;
  }
  .metric-track {
    print-color-adjust: exact;
  }
  .paper-section,
  .report-task,
  .prose {
    orphans: 3;
    widows: 3;
  }
  .task-result-copy {
    display: block;
  }
  .document-footer {
    padding: 16px 0;
    background: white;
    break-inside: avoid;
  }
  .appendix-section {
    break-before: page;
  }
  .cell-sub,
  .table-footnote,
  .metric-delta {
    color: #657285;
  }
  .opinion-box {
    print-color-adjust: exact;
  }
}
</style>
