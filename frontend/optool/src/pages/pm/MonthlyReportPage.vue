<template>
  <q-page class="monthly-page">
    <div class="monthly-shell">

    <template v-if="!isDetail">
    <!-- 헤더 -->
    <div class="monthly-list-header">
      <div>
        <div class="monthly-eyebrow">스케줄 관리 <span> / </span> 보고서</div>
        <h1>월간 보고</h1>
        <p>한 달의 업무 실적과 주요 현황을 확인합니다.</p>
      </div>
      <div class="monthly-header-actions">
        <q-btn outline icon="download" label="목록 Excel" color="blue-grey-8" no-caps @click="downloadList" />
        <q-btn unelevated color="primary" icon="add" label="새 보고서 생성" no-caps @click="openCreate" />
      </div>
    </div>

    <q-card v-if="canUseFeedback && myFeedback.length" flat bordered class="q-mb-md">
      <q-card-section><div class="text-subtitle1 text-weight-bold">내가 작성할 피드백</div><div class="text-caption text-grey-7">메모를 선택해 보고 내용을 작성하세요. 작성 완료하면 해당 월 주요 안건에 자동으로 반영됩니다.</div></q-card-section>
      <q-list separator><q-item v-for="item in myFeedback" :key="item.id" clickable
        :to="{ path: `/pm/monthly-report/${item.targetReportId}`, query: { feedback: item.id } }">
        <q-item-section><q-item-label>{{ item.title }}</q-item-label><q-item-label caption>{{ feedbackStatus[item.status] }}{{ item.dueDate ? ` · 기한 ${item.dueDate}` : '' }}</q-item-label></q-item-section>
        <q-item-section side><span class="text-primary text-caption">내용 작성 <q-icon name="arrow_forward" /></span></q-item-section>
      </q-item></q-list>
    </q-card>

    <!-- 필터 -->
    <q-card flat bordered class="monthly-filter q-mb-md">
      <q-card-section class="q-py-sm">
        <div class="row q-col-gutter-sm items-center">
          <div class="col-auto monthly-filter-label"><q-icon name="tune" size="18px" /> 조회 기간</div>
          <div class="col-auto">
            <q-select v-model="filter.year" :options="yearOptions" label="연도" dense outlined
              emit-value map-options clearable style="min-width:100px" @update:model-value="load" />
          </div>
          <div class="col-auto">
            <q-select v-model="filter.month" :options="monthOptions" label="월" dense outlined
              emit-value map-options clearable style="min-width:90px" @update:model-value="load" />
          </div>
          <div class="col-auto">
            <q-btn flat round dense icon="refresh" aria-label="목록 새로고침" @click="load" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- 목록 -->
    <q-card flat bordered class="monthly-list-card">
      <div class="monthly-list-title"><div><strong>보고서 목록</strong><span>총 {{ reports.length }}건</span></div></div>
      <q-table :rows="reports" :columns="columns" row-key="id" flat :loading="loading" class="monthly-table"
        no-data-label="보고서가 없습니다." :pagination="{ rowsPerPage: 15 }">
        <template #body-cell-period="props">
          <q-td :props="props" class="text-caption text-grey-7">
            <span class="monthly-period">{{ props.row.reportYear }}.{{ String(props.row.reportMonth).padStart(2, '0') }}</span>
          </q-td>
        </template>
        <template #body-cell-title="props">
          <q-td :props="props"><button type="button" class="monthly-report-link" @click="openDetail(props.row)">{{ props.row.title }}</button><div v-if="props.row.department" class="monthly-report-department">{{ props.row.department }}</div></q-td>
        </template>
        <template #body-cell-stats="props">
          <q-td :props="props">
            <div class="monthly-list-stats">
              <span>전체 <b>{{ props.row.stats.total }}</b></span>
              <span>완료 <b>{{ props.row.stats.completed }}</b></span>
              <span>진행 <b>{{ props.row.stats.inProgress }}</b></span>
              <span v-if="props.row.stats.delayed" class="monthly-list-delay">지연 <b>{{ props.row.stats.delayed }}</b></span>
            </div>
          </q-td>
        </template>
        <template #body-cell-rate="props">
          <q-td :props="props">
            <div class="row items-center q-gutter-xs">
              <q-linear-progress :value="props.row.stats.completionRate / 100"
                color="positive" track-color="grey-3" style="width:60px;height:6px;border-radius:4px" />
              <span class="text-caption text-weight-bold">{{ props.row.stats.completionRate }}%</span>
            </div>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props"><span :class="['monthly-status', `monthly-status--${String(props.row.status).toLowerCase()}`]">{{ REPORT_STATUS_KO[props.row.status] ?? props.row.status }}</span></q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" class="q-gutter-xs">
            <q-btn flat dense icon="open_in_new" size="sm" color="primary" title="상세 보기" aria-label="상세 보기" @click="openDetail(props.row)" />
            <q-btn v-if="props.row.status !== 'CONFIRMED'" flat dense icon="edit" size="sm" color="grey-7" aria-label="보고서 수정" @click="openEdit(props.row)" />
            <q-btn v-if="props.row.status !== 'CONFIRMED'" flat dense icon="refresh" size="sm" color="teal" title="이슈 재집계"
              :loading="refreshingId === props.row.id" @click="doRefresh(props.row)" />
            <q-btn flat dense icon="download" size="sm" color="positive" aria-label="보고서 Excel 다운로드" @click="downloadDetail(props.row.id)" />
            <q-btn v-if="props.row.status !== 'CONFIRMED'" flat dense icon="delete" size="sm" color="negative" aria-label="보고서 삭제" @click="confirmDelete(props.row)" />
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- 생성 다이얼로그 -->
    <q-dialog v-model="createDialog.open" no-backdrop-dismiss no-route-dismiss>
      <q-card style="width:480px; max-width:96vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">월간 보고 생성</div>
          <q-space /><q-btn flat round dense icon="close" @click="createDialog.open = false" />
        </q-card-section>
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-gutter-sm">
          <div class="text-caption text-grey-7 q-mb-sm">
            연월을 입력하면 해당 월의 이슈 데이터가 자동으로 집계됩니다.
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input v-model.number="createForm.report_year" label="연도 *" type="number" outlined dense @update:model-value="syncCreateTitle" />
            </div>
            <div class="col-6">
              <q-select v-model="createForm.report_month" :options="monthOptions" label="월 *"
                outlined dense emit-value map-options @update:model-value="syncCreateTitle" />
            </div>
            <div class="col-12">
              <q-input v-model="createForm.title" label="제목 *" outlined dense />
            </div>
            <div class="col-12">
              <q-input v-model="createForm.department" label="부서" outlined dense />
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" no-caps @click="createDialog.open = false" />
          <q-btn color="primary" label="생성 (자동 집계)" :loading="createDialog.loading" no-caps @click="submitCreate" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    </template>

    <!-- 보고서 상세 페이지 -->
    <template v-else>
      <q-inner-loading :showing="detailLoading" />
      <div v-if="detailDialog.report" class="monthly-detail">
        <div class="monthly-detail-topline">
          <q-btn flat dense no-caps icon="arrow_back" label="보고서 목록" class="monthly-back" @click="goToList" />
          <span class="monthly-eyebrow">스케줄 관리 <span> / </span> 월간 보고</span>
        </div>
        <header class="monthly-hero">
          <div class="monthly-hero-main">
            <div class="monthly-hero-kicker"><span>{{ detailDialog.report.reportYear }}년 {{ detailDialog.report.reportMonth }}월</span><span :class="['monthly-status', `monthly-status--${detailDialog.report.status.toLowerCase()}`]">{{ REPORT_STATUS_KO[detailDialog.report.status] }}</span></div>
            <h1>{{ detailDialog.report.title }}</h1>
            <div class="monthly-meta"><span><q-icon name="business" /> {{ detailDialog.report.department || '부서 미지정' }}</span><span><q-icon name="person_outline" /> {{ detailDialog.report.createdByName || '작성자 미지정' }}</span><span><q-icon name="update" /> 마지막 집계 {{ detailDialog.report.aggregatedAt ? fmtDatetimeKst(detailDialog.report.aggregatedAt) : '기록 없음' }}<template v-if="detailDialog.report.aggregatedByName"> · {{ detailDialog.report.aggregatedByName }}</template></span></div>
          </div>
          <div class="monthly-hero-actions">
            <q-btn v-if="canUseFeedback" outline color="blue-grey-8" icon="forum" :label="`${detailDialog.report.reportMonth}월 피드백 메모`" no-caps @click="feedbackOpen = true" />
            <q-btn v-if="detailDialog.report.status !== 'CONFIRMED'" outline color="blue-grey-8" icon="edit" label="수정" no-caps @click="openEdit(detailDialog.report)" />
            <q-btn outline color="blue-grey-8" icon="download" label="Excel" no-caps @click="downloadDetail(detailDialog.report.id)" />
            <q-btn v-if="detailDialog.report.status === 'DRAFT'" unelevated color="primary" icon="rate_review" label="검토 완료" no-caps :loading="changingStatus" @click="changeStatus('REVIEWING')" />
            <q-btn v-if="detailDialog.report.status === 'REVIEWING'" unelevated color="primary" icon="check_circle" label="보고 확정" no-caps :loading="changingStatus" @click="changeStatus('CONFIRMED')" />
            <q-btn v-if="detailDialog.report.status === 'CONFIRMED'" outline color="blue-grey-8" icon="lock_open" label="확정 해제" no-caps :loading="changingStatus" @click="changeStatus('REVIEWING')" />
          </div>
        </header>

        <nav class="monthly-section-nav" aria-label="월간 보고 섹션">
          <button type="button" @click="scrollToSection('monthly-agenda')">주요 안건</button><button type="button" @click="scrollToSection('monthly-risks')">특이사항 및 리스크</button><button type="button" @click="scrollToSection('monthly-decisions')">결정 필요 사항</button>
          <button type="button" @click="scrollToSection('monthly-operations')">서버 점검</button><button type="button" @click="scrollToSection('monthly-work')">업무 현황</button>
        </nav>

        <MonthlyHighlights :report="detailDialog.report" @saved="detailDialog.report = $event" />

        <section id="monthly-operations" class="monthly-surface monthly-insight-card">
          <div class="monthly-section-heading">
            <div><span class="monthly-section-kicker">자동 집계</span><h2>서버 점검</h2></div>
            <q-btn v-if="detailDialog.report.status === 'DRAFT' || detailDialog.report.status === 'REVIEWING'"
              flat dense icon="refresh" label="재집계" size="sm" color="teal" no-caps
              :loading="refreshingId === detailDialog.report.id" @click="doRefresh(detailDialog.report)">
              <q-tooltip>업무 현황과 서버 점검을 함께 재집계합니다.</q-tooltip>
            </q-btn>
          </div>
          <div class="text-caption text-grey-6 q-mb-xs">해당 월의 확정된 서버 점검 결과서를 자동 집계합니다. 부서별로 필터링하지 않습니다.</div>
          <template v-if="detailDialog.report.operationalSummary">
            <div v-if="detailDialog.report.operationalSummary.inspectionReports === null" class="text-caption text-grey-6 q-mt-sm">서버 점검 현황은 서버 점검 메뉴 권한이 필요합니다.</div>
            <div v-else-if="!detailDialog.report.operationalSummary.inspectionReports.length" class="text-caption text-grey-6 q-mt-sm">확정된 해당 월 서버 점검 결과서가 없습니다.</div>
            <div v-for="inspection in detailDialog.report.operationalSummary.inspectionReports" :key="inspection.id" class="text-body2 q-mt-sm">
              <router-link :to="{ path: `/inspection/monthly-reports/${inspection.id}`, query: { kind: 'RESULT' } }">{{ inspection.title }}</router-link>: 작업 완료 {{ inspection.done }}/{{ inspection.planned }}건 · 미완료 {{ inspection.pending }}건 · 이월 {{ inspection.rolled }}건 · 위험 {{ inspection.danger }}대 · 주의 {{ inspection.warning }}대
            </div>
            <div v-if="detailDialog.report.operationalSummary.inspectionReports?.length" class="text-caption text-grey-6 q-mt-xs">결과서의 점검 범위가 겹칠 수 있어 수치를 합산하지 않습니다.</div>
          </template>
          <div v-else class="text-caption text-grey-6">집계된 서버 점검 현황이 없습니다. 재집계 후 확인할 수 있습니다.</div>
        </section>

        <div id="monthly-work" class="monthly-work">
        <AutoWorkPanel v-slot="{ expanded, toggle }" label="업무 현황">
        <q-card-section class="row items-center q-py-sm q-px-md">
          <div class="text-subtitle1 text-weight-bold">업무 현황</div>
          <q-badge color="grey-5" :label="`총 ${detailDialog.report.stats.total}건`" class="q-ml-sm" />
          <q-space />
          <q-btn v-if="detailDialog.report.status === 'DRAFT' || detailDialog.report.status === 'REVIEWING'"
            flat dense icon="refresh" label="재집계" size="sm" color="teal" no-caps
            :loading="refreshingId === detailDialog.report.id" @click="doRefresh(detailDialog.report)" />
          <q-btn flat dense :icon="expanded ? 'fullscreen_exit' : 'fullscreen'"
            :label="expanded ? '전체화면 종료' : '전체화면'" :aria-label="expanded ? '업무 현황 전체화면 종료' : '업무 현황 전체화면 보기'"
            :aria-pressed="expanded" size="sm" no-caps @click="toggle" />
        </q-card-section>
        <q-separator />
        <q-tabs v-model="detailTab" dense align="left" class="q-px-md">
          <q-tab name="project" label="프로젝트별" />
          <q-tab name="person"  label="개인별" />
          <q-tab name="all"     label="전체 업무" />
          <q-tab v-if="detailDialog.report.upcomingItems.length" name="upcoming" label="차월 계획" />
        </q-tabs>
        <q-separator />

        <q-card-section style="max-height:60vh;overflow-y:auto" class="q-pa-md auto-work-scroll">
          <div class="monthly-data-note"><q-icon name="info_outline" size="16px" /> 해당 월의 완료 이력과 월말 상태 기준입니다. 이력이 없거나 삭제된 업무와 이후 변경된 일정은 정확히 복원되지 않을 수 있습니다.</div>
          <q-tab-panels v-model="detailTab" animated>

            <!-- 프로젝트별 -->
            <q-tab-panel name="project" class="q-pa-none">
              <div v-if="!detailDialog.report.byProject.length" class="text-grey-5 text-center q-pa-lg">
                집계된 업무가 없습니다.
              </div>
              <q-expansion-item v-for="(pb, i) in detailDialog.report.byProject" :key="pb.projectId"
                default-opened :label="pb.projectName"
                :caption="`${pb.orgName ?? ''} · 완료 ${pb.stats.completed}/${pb.stats.total} · ${pb.stats.completionRate}%`"
                class="q-mb-sm" :header-class="`${headerBg(i)} ${headerText(i)} text-weight-bold`">
                <q-card flat>
                  <q-card-section class="q-pa-sm">
                    <div class="text-caption text-grey-6 q-mb-xs">시작일순 · 시작일이 없으면 마감일 기준</div>
                    <div v-for="item in projectTimeline(pb)" :key="item.issueId"
                      class="row items-center q-gutter-xs q-mb-xs q-pa-xs bg-grey-1 rounded-borders cursor-pointer issue-row"
                      @click="openIssueDetail(item.issueId)">
                      <span class="text-caption text-grey-6" style="min-width:90px">{{ item.projectName }}-{{ item.issueNumber }}</span>
                      <div class="col issue-row-title"><span class="text-body2 ellipsis">{{ item.title }}</span><q-badge v-if="item.isDelayed" outline color="negative" label="지연" class="issue-delay-badge" /></div>
                      <span v-if="item.assigneeName" class="text-caption text-grey-7">{{ item.assigneeName }}</span>
                      <q-badge v-if="pb.upcoming.some(next => next.issueId === item.issueId)" outline color="primary" label="차월 계획" />
                      <q-badge :color="PRIORITY_COLOR[item.priority]" :label="PRIORITY_KO[item.priority]" />
                      <q-badge color="grey-5" :label="STATUS_KO[item.status] ?? item.status" />
                      <span class="text-caption text-grey-6">{{ fmtDateKst(item.startDate) }} ~ {{ fmtDateKst(item.dueDate) }}</span>
                    </div>
                    <div v-if="!projectTimeline(pb).length"
                      class="text-grey-5 text-caption">업무 없음</div>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-tab-panel>

            <!-- 개인별 -->
            <q-tab-panel name="person" class="q-pa-none">
              <div v-if="!detailDialog.report.byPerson.length" class="text-grey-5 text-center q-pa-lg">
                집계된 업무가 없습니다.
              </div>
              <q-expansion-item v-for="(pb, i) in detailDialog.report.byPerson" :key="pb.userId"
                default-opened :label="pb.userName"
                :caption="pb.stats.total ? `완료 ${pb.stats.completed}/${pb.stats.total} · ${pb.stats.completionRate}%` : '이번 달 업무 없음'"
                class="q-mb-sm" :header-class="`${headerBg(i)} ${headerText(i)} text-weight-bold`">
                <q-card flat>
                  <q-card-section class="q-pa-sm">
                    <template v-for="sec in breakdown(pb)" :key="sec.label">
                      <div class="q-mb-sm">
                        <div class="text-caption text-weight-bold q-mb-xs" :class="`text-${sec.color}`">{{ sec.label }}</div>
                        <div v-if="sec.items.length">
                          <div v-for="item in sec.items" :key="item.issueId"
                            class="row items-center q-gutter-xs q-mb-xs q-pa-xs bg-grey-1 rounded-borders cursor-pointer issue-row"
                            @click="openIssueDetail(item.issueId)">
                            <span class="text-caption text-grey-6" style="min-width:90px">{{ item.projectName }}-{{ item.issueNumber }}</span>
                            <div class="col issue-row-title"><span class="text-body2 ellipsis">{{ item.title }}</span><q-badge v-if="item.isDelayed" outline color="negative" label="지연" class="issue-delay-badge" /></div>
                            <q-badge :color="PRIORITY_COLOR[item.priority]" :label="PRIORITY_KO[item.priority]" />
                            <q-badge color="grey-5" :label="STATUS_KO[item.status] ?? item.status" />
                            <span v-if="item.dueDate" class="text-caption text-grey-6">{{ fmtDateKst(item.dueDate) }}</span>
                          </div>
                        </div>
                        <div v-else class="text-caption text-grey-5 q-pl-sm">없음</div>
                      </div>
                    </template>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-tab-panel>

            <!-- 전체 업무 -->
            <q-tab-panel name="all" class="q-pa-none">
              <div v-if="!detailDialog.report.allItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="detailDialog.report.allItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음"
                @row-click="(_, row) => openIssueDetail(row.issueId)">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">
                    {{ props.row.projectName }}-{{ props.row.issueNumber }}
                  </q-td>
                </template>
                <template #body-cell-title="props"><q-td :props="props">{{ props.row.title }} <q-badge v-if="props.row.isDelayed" outline color="negative" label="지연" class="q-ml-sm" /></q-td></template>
                <template #body-cell-priority="props">
                  <q-td :props="props">
                    <q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" />
                  </q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge color="grey-5"
                      :label="STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

            <!-- 차월 계획 -->
            <q-tab-panel name="upcoming" class="q-pa-none">
              <div v-if="!detailDialog.report.upcomingItems.length" class="text-grey-5 text-center q-pa-lg">업무 없음</div>
              <q-table v-else :rows="detailDialog.report.upcomingItems" :columns="workItemCols"
                flat dense row-key="issueId" :pagination="{ rowsPerPage: 20 }" no-data-label="업무 없음"
                @row-click="(_, row) => openIssueDetail(row.issueId)">
                <template #body-cell-num="props">
                  <q-td :props="props" class="text-caption text-grey-6">
                    {{ props.row.projectName }}-{{ props.row.issueNumber }}
                  </q-td>
                </template>
                <template #body-cell-title="props"><q-td :props="props">{{ props.row.title }} <q-badge v-if="props.row.isDelayed" outline color="negative" label="지연" class="q-ml-sm" /></q-td></template>
                <template #body-cell-priority="props">
                  <q-td :props="props">
                    <q-badge :color="PRIORITY_COLOR[props.row.priority]" :label="PRIORITY_KO[props.row.priority]" />
                  </q-td>
                </template>
                <template #body-cell-status="props">
                  <q-td :props="props">
                    <q-badge color="grey-5"
                      :label="STATUS_KO[props.row.status] ?? props.row.status" />
                  </q-td>
                </template>
              </q-table>
            </q-tab-panel>

          </q-tab-panels>

        </q-card-section>
        </AutoWorkPanel>
        </div>

        <!-- 관리자 코멘트 -->
        <section v-if="detailDialog.report.adminComment" class="monthly-surface monthly-admin-note">
          <div>
            <div class="monthly-section-heading"><div><span class="monthly-section-kicker">참고</span><h2>관리자 코멘트</h2></div><q-icon name="chat_bubble_outline" size="20px" /></div>
            <div class="text-body2 q-pa-sm bg-grey-1 rounded-borders" style="white-space:pre-wrap">
              {{ detailDialog.report.adminComment }}
            </div>
          </div>
        </section>

      </div>
      <div v-else-if="!detailLoading" class="monthly-unavailable"><q-icon name="description" size="32px" /><p>보고서를 불러오지 못했습니다.</p><q-btn outline color="primary" label="보고서 목록" no-caps @click="goToList" /></div>
      <q-dialog v-model="feedbackOpen" persistent :maximized="$q.screen.width <= 800" @hide="clearFeedbackQuery">
        <MonthlyFeedback v-if="feedbackOpen && detailDialog.report && canUseFeedback" :report="detailDialog.report" @changed="reloadDetail" @close="feedbackOpen = false" @report="showFeedbackReport" />
      </q-dialog>
    </template>

    <q-dialog v-model="editDialog.open" no-backdrop-dismiss no-route-dismiss>
      <q-card style="width:480px; max-width:96vw">
        <q-card-section class="row items-center q-pb-none"><div class="text-h6">보고서 수정</div><q-space /><q-btn flat round dense icon="close" aria-label="닫기" @click="editDialog.open = false" /></q-card-section>
        <q-separator class="q-mt-sm" />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="editForm.title" label="제목" outlined dense />
          <q-input v-model="editForm.department" label="부서" outlined dense />
          <q-input v-model="editForm.admin_comment" label="관리자 코멘트" outlined dense type="textarea" rows="4" hint="이슈 집계 외에 관리자가 추가할 내용을 입력하세요." />
        </q-card-section>
        <q-separator /><q-card-actions align="right" class="q-pa-md"><q-btn flat label="취소" no-caps @click="editDialog.open = false" /><q-btn color="primary" label="저장" :loading="editDialog.loading" no-caps @click="submitEdit" /></q-card-actions>
      </q-card>
    </q-dialog>
    <IssueDetailDialog v-if="issueDialog.open && issueDialog.issue" v-model="issueDialog.open"
      :project-id="issueDialog.issue.projectId" :issue="issueDialog.issue" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Notify, Dialog } from 'quasar'
import { api } from 'boot/axios'
import {
  listMonthlyReports, getMonthlyReport, createMonthlyReport, updateMonthlyReport,
  deleteMonthlyReport, refreshMonthlyReport, changeMonthlyReportStatus,
  type MonthlyReport, type MonthlyReportCreate,
  type ReportStatus, type WorkItem, type ProjectBreakdown, type PersonBreakdown,
} from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'
import { fmtDateKst, fmtDatetimeKst } from 'src/utils/time/kst'
import { projectTimeline } from 'src/utils/reportProjectOrder'
import MonthlyHighlights from './components/MonthlyHighlights.vue'
import MonthlyFeedback from './components/MonthlyFeedback.vue'
import { listMyFeedback, listFeedback, type MonthlyFeedback as FeedbackItem } from 'src/services/pm/monthlyFeedback'
import { useAuthStore } from 'src/stores/auth'
import AutoWorkPanel from './components/AutoWorkPanel.vue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getLinkedIssue, type Issue } from 'src/services/pm/issue'

// ── 레이블 맵 ─────────────────────────────────────────────────────────
const STATUS_KO: Record<string, string> = {
  BACKLOG: '백로그', TODO: '할 일', IN_PROGRESS: '진행 중', IMPLEMENTED: '완료', DONE: '완료',
}
const REPORT_STATUS_KO: Record<string, string> = { DRAFT: '초안', REVIEWING: '검토중', CONFIRMED: '확정' }
const PRIORITY_KO: Record<string, string> = {
  LOWEST: '최하', LOW: '낮음', MEDIUM: '중간', HIGH: '높음', HIGHEST: '최고',
}
const PRIORITY_COLOR: Record<string, string> = {
  LOWEST: 'grey', LOW: 'blue-grey', MEDIUM: 'orange', HIGH: 'deep-orange', HIGHEST: 'red',
}
const PALETTE = ['blue', 'teal', 'purple', 'orange', 'green', 'deep-orange', 'indigo', 'cyan', 'pink', 'amber']
function headerBg(i: number) { return `bg-${PALETTE[i % PALETTE.length]}-1` }
function headerText(i: number) { return `text-${PALETTE[i % PALETTE.length]}-9` }

// ── 상태 ──────────────────────────────────────────────────────────────
const now = new Date()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canUseFeedback = computed(() => !!auth.me && (auth.me.isAdmin || auth.me.team === '데이터운영팀'))
const feedbackOpen = ref(false)
const myFeedback = ref<FeedbackItem[]>([])
const feedbackStatus: Record<FeedbackItem['status'], string> = { REQUESTED: '작성 대기', WRITING: '작성 중', SUBMITTED: '작성 완료 필요', APPLYING: '반영 확인 필요', APPLIED: '반영 완료', CANCELLED: '요청 취소' }
const isDetail = computed(() => typeof route.params.id === 'string' && !!route.params.id)
const reports = ref<MonthlyReport[]>([])
const loading = ref(false)
const detailLoading = ref(false)
const refreshingId = ref<string | null>(null)
const changingStatus = ref(false)
const detailTab = ref('project')
const issueDialog = ref<{ open: boolean; issue: Issue | null }>({ open: false, issue: null })

async function openIssueDetail(issueId: string) {
  try {
    const issue = await getLinkedIssue(issueId)
    issueDialog.value = { open: true, issue }
  } catch {
    Notify.create({ type: 'negative', message: '이슈 정보를 불러오지 못했습니다.' })
  }
}

const filter = ref<{ year: number | null; month: number | null }>({
  year: now.getFullYear(), month: null,
})

const yearOptions = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)
  .map(y => ({ label: `${y}년`, value: y }))
const monthOptions = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}월`, value: i + 1 }))

// ── 테이블 컬럼 ───────────────────────────────────────────────────────
const columns = [
  { name: 'period',  label: '기간',      field: (r: MonthlyReport) => r.reportYear * 100 + r.reportMonth, align: 'left' as const, sortable: true },
  { name: 'title',   label: '제목',      field: 'title',       align: 'left'   as const, sortable: true },
  { name: 'stats',   label: '업무 현황', field: 'stats',       align: 'left'   as const },
  { name: 'rate',    label: '완료율',    field: (r: MonthlyReport) => r.stats.completionRate, align: 'left' as const, sortable: true },
  { name: 'status',  label: '상태',      field: 'status', align: 'center' as const },
  { name: 'createdByName', label: '작성자', field: 'createdByName', align: 'left' as const },
  { name: 'actions', label: '',          field: 'id',          align: 'center' as const },
]

const workItemCols = [
  { name: 'num',      label: '번호',    field: 'issueNumber',  align: 'left'   as const },
  { name: 'title',    label: '업무명',  field: 'title',        align: 'left'   as const },
  { name: 'assignee', label: '담당자',  field: 'assigneeName', align: 'left'   as const },
  { name: 'priority', label: '우선순위',field: 'priority',     align: 'center' as const },
  { name: 'status',   label: '상태',    field: 'status',       align: 'center' as const },
  { name: 'due',      label: '마감일',  field: (r: WorkItem) => fmtDateKst(r.dueDate), align: 'center' as const },
]

function breakdown(pb: ProjectBreakdown | PersonBreakdown) {
  return [
    { label: '✅ 완료',     items: pb.completed,  color: 'positive' },
    { label: '🔄 진행 중',  items: pb.inProgress, color: 'primary'  },
    { label: '📌 차월 계획', items: pb.upcoming,   color: 'grey-7'   },
  ]
}

// ── 생성 ──────────────────────────────────────────────────────────────
const createDialog = ref({ open: false, loading: false })
const createForm = ref<MonthlyReportCreate>({
  report_year: now.getFullYear(), report_month: now.getMonth() + 1,
  title: '', department: '',
})
let generatedTitle = ''

function openCreate() {
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  createForm.value = {
    report_year: year, report_month: month,
    title: `${year}년 ${month}월 월간 보고`,
    department: '',
  }
  generatedTitle = createForm.value.title
  createDialog.value = { open: true, loading: false }
}

function syncCreateTitle() {
  if (createForm.value.title === generatedTitle && createForm.value.report_year && createForm.value.report_month) {
    generatedTitle = `${createForm.value.report_year}년 ${createForm.value.report_month}월 월간 보고`
    createForm.value.title = generatedTitle
  }
}

async function submitCreate() {
  if (!Number.isInteger(createForm.value.report_year) || createForm.value.report_year < 1 || createForm.value.report_year > 9999 || !Number.isInteger(createForm.value.report_month) || createForm.value.report_month < 1 || createForm.value.report_month > 12) {
    Notify.create({ type: 'warning', message: '유효한 연도와 월을 입력해주세요.' })
    return
  }
  if (!createForm.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }
  createDialog.value.loading = true
  try {
    await createMonthlyReport(createForm.value)
    Notify.create({ type: 'positive', message: '보고서가 생성되었습니다.' })
    createDialog.value.open = false
    await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '생성 실패') })
  } finally {
    createDialog.value.loading = false
  }
}

// ── 수정 ──────────────────────────────────────────────────────────────
const editDialog = ref({ open: false, loading: false, editId: '' })
const editForm = ref({ title: '', department: '', admin_comment: '' })

function openEdit(r: MonthlyReport) {
  editForm.value = {
    title: r.title, department: r.department ?? '',
    admin_comment: r.adminComment ?? '',
  }
  editDialog.value = { open: true, loading: false, editId: r.id }
}

async function submitEdit() {
  if (!editForm.value.title.trim()) {
    Notify.create({ type: 'warning', message: '제목을 입력해주세요.' })
    return
  }
  editDialog.value.loading = true
  try {
    const updated = await updateMonthlyReport(editDialog.value.editId, {
      title: editForm.value.title.trim(),
      department: editForm.value.department,
      admin_comment: editForm.value.admin_comment,
    })
    Notify.create({ type: 'positive', message: '저장되었습니다.' })
    editDialog.value.open = false
    if (isDetail.value && detailDialog.value.report?.id === updated.id) detailDialog.value.report = updated
    else await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    editDialog.value.loading = false
  }
}

// ── 재집계 ────────────────────────────────────────────────────────────
async function doRefresh(r: MonthlyReport) {
  refreshingId.value = r.id
  try {
    const updated = await refreshMonthlyReport(r.id)
    Notify.create({ type: 'positive', message: '업무 현황과 서버 점검을 재집계했습니다.' })
    if (isDetail.value && detailDialog.value.report?.id === r.id) detailDialog.value.report = updated
    else await load()
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '재집계 실패') })
  } finally {
    refreshingId.value = null
  }
}

// ── 상세 ──────────────────────────────────────────────────────────────
const detailDialog = ref<{ report: MonthlyReport | null }>({ report: null })

function openDetail(r: MonthlyReport) {
  void router.push(`/pm/monthly-report/${r.id}`)
}

function goToList() { void router.push('/pm/monthly-report') }
function scrollToSection(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
function showFeedbackReport() {
  feedbackOpen.value = false
  scrollToSection('monthly-agenda')
}
function clearFeedbackQuery() {
  if (!route.query.feedback) return
  const query = { ...route.query }
  delete query.feedback
  void router.replace({ query })
}
watch(() => [route.params.id, route.query.feedback], ([id, feedback]) => {
  feedbackOpen.value = typeof id === 'string' && typeof feedback === 'string' && !!feedback
}, { immediate: true })

async function reloadDetail() {
  const id = detailDialog.value.report?.id
  if (!id) return
  try { const report = await getMonthlyReport(id); if (route.params.id === id) detailDialog.value.report = report }
  catch (e) { Notify.create({ type: 'negative', message: getErrorMessage(e, '보고서를 다시 불러오지 못했습니다.') }) }
}

async function changeStatus(status: ReportStatus) {
  if (!detailDialog.value.report) return
  const reportId = detailDialog.value.report.id
  if (status === 'CONFIRMED' && canUseFeedback.value) {
    try {
      const pending = (await listFeedback(reportId)).filter(item => item.targetReportId === reportId && !['APPLIED', 'CANCELLED'].includes(item.status))
      if (pending.length) {
        const confirmed = await new Promise<boolean>(resolve => {
          Dialog.create({ title: '미완료 피드백', message: `아직 반영되지 않은 피드백 ${pending.length}건이 있습니다. 보고서를 확정하시겠습니까?`, cancel: true }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false))
        })
        if (!confirmed || route.params.id !== reportId) return
      }
    } catch (e) { Notify.create({ type: 'negative', message: getErrorMessage(e, '피드백 상태를 확인하지 못했습니다.') }); return }
  }
  changingStatus.value = true
  try {
    const updated = await changeMonthlyReportStatus(reportId, status)
    if (route.params.id === reportId) detailDialog.value.report = updated
    Notify.create({ type: 'positive', message: '보고서 상태가 변경되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '상태 변경 실패') })
  } finally {
    changingStatus.value = false
  }
}

// ── 삭제 ──────────────────────────────────────────────────────────────
function confirmDelete(r: MonthlyReport) {
  Dialog.create({
    title: '삭제 확인', message: `"${r.title}"을(를) 삭제하시겠습니까?`,
    cancel: true, noBackdropDismiss: true, noRouteDismiss: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteMonthlyReport(r.id)
        Notify.create({ type: 'positive', message: '삭제되었습니다.' })
        await load()
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}

// ── Excel ──────────────────────────────────────────────────────────────
function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function downloadList() {
  try {
    const params: Record<string, number> = {}
    if (filter.value.year)  params.year  = filter.value.year
    if (filter.value.month) params.month = filter.value.month
    const res = await api.get('/pm/monthly-reports/export/list', { params, responseType: 'blob' })
    triggerDownload(res.data as Blob, `월간보고목록_${filter.value.year ?? '전체'}년.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

async function downloadDetail(id: string) {
  try {
    const res = await api.get(`/pm/monthly-reports/${id}/export`, { responseType: 'blob' })
    triggerDownload(res.data as Blob, `월간보고_${id}.xlsx`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, 'Excel 다운로드 실패') })
  }
}

// ── 로드 ──────────────────────────────────────────────────────────────
async function load() {
  loading.value = true
  try {
    reports.value = await listMonthlyReports({
      ...(filter.value.year  ? { year:  filter.value.year  } : {}),
      ...(filter.value.month ? { month: filter.value.month } : {}),
    })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
}

watch([canUseFeedback, isDetail], async ([allowed, detail]) => {
  if (!allowed || detail) { myFeedback.value = []; return }
  try { myFeedback.value = await listMyFeedback() }
  catch (e) { Notify.create({ type: 'negative', message: getErrorMessage(e, '작성 요청을 불러오지 못했습니다.') }) }
}, { immediate: true })

watch(() => route.params.id, async (id, _previousId, onCleanup) => {
  let active = true
  onCleanup(() => { active = false })
  detailDialog.value.report = null
  detailTab.value = 'project'
  if (typeof id !== 'string' || !id) {
    detailLoading.value = false
    await load()
    return
  }
  detailLoading.value = true
  try {
    const report = await getMonthlyReport(id)
    if (active) detailDialog.value.report = report
  } catch (e) {
    if (active) Notify.create({ type: 'negative', message: getErrorMessage(e, '보고서를 불러오지 못했습니다.') })
  } finally {
    if (active) detailLoading.value = false
  }
}, { immediate: true })
</script>

<style scoped>
.monthly-page { min-height: 100%; padding: 28px 32px 52px; background: #f5f7f9; color: #243648; }
.monthly-shell { position: relative; width: 100%; min-height: 200px; max-width: 1500px; margin: 0 auto; }
.monthly-list-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 25px; }
.monthly-list-header h1, .monthly-hero h1 { margin: 5px 0 0; color: #172a3a; font-size: 27px; line-height: 1.3; letter-spacing: -.035em; font-weight: 750; }
.monthly-list-header p { margin: 6px 0 0; color: #738394; font-size: 13px; }
.monthly-eyebrow { color: #7d8d9c; font-size: 12px; font-weight: 600; }
.monthly-eyebrow span { margin: 0 5px; color: #c4cdd5; }
.monthly-header-actions, .monthly-hero-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.monthly-header-actions :deep(.q-btn), .monthly-hero-actions :deep(.q-btn) { min-height: 36px; border-radius: 8px; padding: 0 12px; font-size: 12px; font-weight: 600; }
.monthly-filter, .monthly-list-card, .monthly-surface { background: #fff; border: 1px solid #e1e8ef; border-radius: 14px; }
.monthly-filter-label { display: flex; align-items: center; gap: 7px; margin-right: 8px; color: #576d7d; font-size: 12px; font-weight: 700; }
.monthly-filter :deep(.q-field__control) { height: 36px; border-radius: 7px; }
.monthly-list-card { overflow: hidden; }
.monthly-list-title { padding: 20px 22px 14px; color: #213849; font-size: 15px; }
.monthly-list-title span { margin-left: 9px; color: #8a99a7; font-size: 12px; }
.monthly-table :deep(thead tr) { background: #f8fafb; }
.monthly-table :deep(th) { color: #81909e; font-size: 11px; font-weight: 700; }
.monthly-table :deep(tbody td) { height: 57px; border-color: #f0f3f5; }
.monthly-table :deep(tbody tr:hover) { background: #f8fbfc; }
.monthly-period { color: #335164; font-weight: 700; font-size: 13px; font-variant-numeric: tabular-nums; }
.monthly-report-link { max-width: 360px; padding: 0; overflow: hidden; border: 0; background: transparent; color: #244b5b; font: inherit; font-weight: 700; text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.monthly-report-link:hover { color: #168079; text-decoration: underline; }
.monthly-report-link:focus-visible { outline: 2px solid #168079; outline-offset: 3px; border-radius: 2px; }
.monthly-report-department { margin-top: 3px; color: #9aa8b3; font-size: 11px; }
.monthly-list-stats { display: flex; flex-wrap: wrap; gap: 10px; color: #8795a2; font-size: 11px; }
.monthly-list-stats b { color: #40596b; margin-left: 2px; }
.monthly-list-stats .monthly-list-delay, .monthly-list-stats .monthly-list-delay b { color: #c06459; }
.monthly-status { display: inline-flex; align-items: center; gap: 6px; padding: 4px 9px; border-radius: 6px; background: #f0f3f5; color: #637582; font-size: 11px; font-weight: 700; white-space: nowrap; }
.monthly-status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.monthly-status--reviewing { color: #a47227; background: #fff6e6; }
.monthly-status--confirmed { color: #298374; background: #e8f5f1; }
.monthly-detail-topline { display: flex; align-items: center; gap: 18px; margin: 0 0 15px; }
.monthly-back { color: #526d7d; font-size: 12px; }
.monthly-hero { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; padding: 26px 28px; border: 1px solid #dfe8ec; border-radius: 16px; background: linear-gradient(112deg, #fff 0%, #f1f8f8 100%); }
.monthly-hero-main { min-width: 0; }
.monthly-hero-kicker { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; color: #4d8d88; font-size: 12px; font-weight: 700; }
.monthly-hero h1 { overflow-wrap: anywhere; }
.monthly-meta { display: flex; flex-wrap: wrap; gap: 8px 17px; margin-top: 13px; color: #718493; font-size: 12px; }
.monthly-meta span { display: inline-flex; align-items: center; gap: 4px; }
.monthly-meta .q-icon { font-size: 16px; color: #91a4ae; }
.monthly-hero-actions { justify-content: flex-end; flex-shrink: 0; max-width: 510px; }
.monthly-section-nav { display: flex; gap: 4px; overflow-x: auto; margin: 22px 0 16px; padding-bottom: 2px; border-bottom: 1px solid #dfe6eb; }
.monthly-section-nav button { flex: 0 0 auto; padding: 9px 14px 11px; border: 0; background: transparent; color: #6e8190; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
.monthly-section-nav button:hover, .monthly-section-nav button:focus-visible { color: #197c75; background: #eaf3f2; border-radius: 7px 7px 0 0; outline: none; }
.monthly-work, .monthly-admin-note, .monthly-insight-card { scroll-margin-top: 20px; margin-bottom: 16px; }
.monthly-insight-card, .monthly-admin-note { min-width: 0; padding: 22px 24px; }
.monthly-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 13px; color: #9aaeb6; }
.monthly-section-heading h2 { margin: 3px 0 0; color: #1b3242; font-size: 16px; line-height: 1.4; font-weight: 700; }
.monthly-section-kicker { color: #75909c; font-size: 10px; font-weight: 700; letter-spacing: .1em; }
.issue-row:hover { background: #e8eaf6 !important; }
.issue-row-title { display: flex; align-items: center; gap: 6px; min-width: 0; }
.issue-row-title > .ellipsis { min-width: 0; }
.issue-delay-badge { flex-shrink: 0; }
.monthly-data-note { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 14px; color: #8998a5; font-size: 11px; line-height: 1.55; }
.monthly-data-note .q-icon { flex: 0 0 auto; }
.monthly-unavailable { margin: 30px 0; padding: 60px 20px; text-align: center; color: #7c8f9d; background: #fff; border: 1px solid #e1e8ef; border-radius: 14px; }
@media (max-width: 1000px) {
  .monthly-hero { align-items: flex-start; flex-direction: column; }
  .monthly-hero-actions { justify-content: flex-start; max-width: none; }
}
@media (max-width: 700px) {
  .monthly-page { padding: 20px 15px 40px; }
  .monthly-list-header { align-items: flex-start; flex-direction: column; gap: 14px; }
  .monthly-list-header h1, .monthly-hero h1 { font-size: 23px; }
  .monthly-filter-label { width: 100%; }
  .monthly-hero { padding: 20px; }
  .monthly-insight-card, .monthly-admin-note { padding: 18px; }
  .monthly-section-nav { margin-top: 16px; }
}
@media (max-width: 599px) {
  .issue-row-title { order: -1; flex: 0 0 calc(100% - 4px); }
}
</style>
