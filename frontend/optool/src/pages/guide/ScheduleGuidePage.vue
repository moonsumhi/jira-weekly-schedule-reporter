<template>
  <q-page class="q-pa-md">

    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">📅 스케줄 관리 사용 가이드</div>
        <div class="text-caption text-grey-6">주간 보고 생성·관리, 업무 현황 캘린더 사용 방법을 설명합니다.</div>
      </div>
    </div>

    <div class="row q-col-gutter-md">

      <!-- 목차 -->
      <div class="col-12 col-md-3">
        <q-card flat bordered class="sticky-toc">
          <q-card-section class="q-py-sm q-px-md">
            <div class="text-caption text-weight-bold text-grey-6 q-mb-sm">목차</div>
            <q-list dense>
              <q-item v-for="sec in sections" :key="sec.id" clickable @click="scrollTo(sec.id)"
                :class="active === sec.id ? 'bg-primary-1 text-primary' : ''"
                class="rounded-borders q-mb-xs" style="min-height:36px">
                <q-item-section avatar style="min-width:28px">
                  <q-icon :name="sec.icon" :color="active === sec.id ? 'primary' : 'grey-5'" size="16px" />
                </q-item-section>
                <q-item-section class="text-caption text-weight-medium">{{ sec.label }}</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- 본문 -->
      <div class="col-12 col-md-9">

        <!-- ① 스케줄 관리란? -->
        <div :id="sections[0]!.id" class="guide-section">
          <div class="section-title"><q-icon name="info" color="primary" class="q-mr-sm" />스케줄 관리란?</div>

          <q-card flat bordered class="q-mb-md">
            <q-card-section>
              <div class="text-body1 text-weight-medium q-mb-sm">
                PM 시스템에 등록된 업무를 자동으로 취합하는 <span class="text-primary text-weight-bold">업무 보고 관리 시스템</span>입니다.
              </div>
              <div class="text-body2 text-grey-8 q-mb-md">
                팀원별 이슈를 자동으로 집계하여 주간 보고서를 생성하고, 업무 일정을 캘린더로 시각화합니다.
                매번 엑셀을 직접 정리하지 않아도 됩니다.
              </div>
              <div class="row q-col-gutter-sm">
                <div v-for="m in modules" :key="m.label" class="col-12 col-sm-4">
                  <q-card flat class="q-pa-md text-center" :style="`background:${m.bg}`">
                    <q-icon :name="m.icon" :color="m.color" size="32px" class="q-mb-sm" />
                    <div class="text-body2 text-weight-bold q-mb-xs">{{ m.label }}</div>
                    <div class="text-caption text-grey-7">{{ m.desc }}</div>
                  </q-card>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- ② 주간 보고 목록 -->
        <div :id="sections[1]!.id" class="guide-section">
          <div class="section-title"><q-icon name="event_note" color="primary" class="q-mr-sm" />주간 보고 목록</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>스케줄 관리 → 주간 보고</strong>를 클릭하면 생성된 모든 보고서를 볼 수 있습니다.
          </div>

          <!-- 상단 버튼 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">상단 버튼</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="btn in topButtons" :key="btn.label">
              <q-btn :color="btn.color" :icon="btn.icon" :label="btn.label" no-caps unelevated style="pointer-events:none" />
            </div>
          </div>

          <!-- 필터 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">목록 필터</div>
          <div class="row q-gutter-sm q-mb-md items-center">
            <q-select model-value="2026년" :options="[]" label="연도" dense outlined style="min-width:100px;pointer-events:none" />
            <q-input model-value="" label="주차" type="number" dense outlined style="min-width:80px;pointer-events:none" />
            <div class="text-caption text-grey-6">연도·주차를 선택하면 해당 기간의 보고서만 표시됩니다.</div>
          </div>

          <!-- 테이블 컬럼 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">목록 테이블 컬럼</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="col in tableColumns" :key="col.name">
              <q-item-section avatar style="min-width:90px">
                <q-chip dense color="grey-2" text-color="grey-8" size="sm">{{ col.name }}</q-chip>
              </q-item-section>
              <q-item-section class="text-caption text-grey-7">{{ col.desc }}</q-item-section>
            </q-item>
          </q-list>

          <!-- 행 액션 아이콘 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">행별 액션 아이콘</div>
          <div class="row q-gutter-sm q-mb-md">
            <q-card v-for="act in rowActions" :key="act.label" flat bordered class="q-pa-sm text-center" style="min-width:80px">
              <q-icon :name="act.icon" :color="act.color" size="22px" />
              <div class="text-caption text-grey-7 q-mt-xs">{{ act.label }}</div>
              <div class="text-caption text-grey-5" style="font-size:10px">{{ act.desc }}</div>
            </q-card>
          </div>

          <!-- 보고서 상태 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">보고서 상태</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="s in reportStatuses" :key="s.label" class="row items-center q-gutter-xs">
              <q-badge :color="s.color" :label="s.label" />
              <span class="text-caption text-grey-7">{{ s.desc }}</span>
            </div>
          </div>

          <!-- 새 보고서 생성 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">새 보고서 생성 방법</div>
          <q-timeline color="primary">
            <q-timeline-entry title="[새 보고서 생성] 버튼 클릭" icon="add_circle" color="primary">
              <div class="text-body2">오른쪽 상단의 파란 버튼을 클릭하면 생성 다이얼로그가 열립니다.</div>
            </q-timeline-entry>
            <q-timeline-entry title="연도·주차 입력" icon="event" color="primary">
              <div class="text-body2 q-mb-sm">연도와 주차를 입력하면 기간(ISO 8601 기준 월~일)과 제목이 자동으로 채워집니다.</div>
              <div class="row q-col-gutter-sm q-mb-xs">
                <div v-for="f in createFields" :key="f.label" class="col-12 col-sm-6">
                  <q-card flat bordered class="q-pa-sm">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <span class="text-caption text-weight-bold">{{ f.label }}</span>
                      <q-badge v-if="f.required" color="negative" label="필수" style="font-size:10px" />
                      <q-badge v-else color="grey-4" text-color="grey-7" label="자동/선택" style="font-size:10px" />
                    </div>
                    <div class="text-caption text-grey-7">{{ f.desc }}</div>
                  </q-card>
                </div>
              </div>
            </q-timeline-entry>
            <q-timeline-entry title="[생성 (자동 집계)] 클릭" icon="sync" color="teal">
              <div class="text-body2">확인을 누르면 해당 기간에 등록된 업무를 자동으로 집계합니다. 잠시 기다리면 보고서가 목록에 추가됩니다.</div>
            </q-timeline-entry>
          </q-timeline>
        </div>

        <!-- ③ 주간 보고 상세 -->
        <div :id="sections[2]!.id" class="guide-section">
          <div class="section-title"><q-icon name="description" color="primary" class="q-mr-sm" />주간 보고 상세 화면</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            목록에서 <q-icon name="open_in_new" size="14px" /> 상세보기 아이콘을 클릭하면 상세 화면이 열립니다.
          </div>

          <!-- 통계 카드 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">상단 통계 카드</div>
          <div class="row q-gutter-sm q-mb-md">
            <q-card v-for="s in statCards" :key="s.label" flat bordered class="q-pa-sm text-center" style="min-width:72px">
              <div class="text-h6 text-weight-bold" :class="s.color">{{ s.example }}</div>
              <div class="text-caption text-grey-6">{{ s.label }}</div>
            </q-card>
          </div>

          <!-- 상태별 버튼 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">상태별 사용 가능한 버튼</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="sb in statusButtons" :key="sb.status">
              <q-item-section avatar>
                <q-badge :color="sb.color" :label="sb.status" />
              </q-item-section>
              <q-item-section>
                <div class="row q-gutter-xs flex-wrap">
                  <q-btn v-for="b in sb.buttons" :key="b.label"
                    :color="b.color" :icon="b.icon" :label="b.label"
                    no-caps unelevated size="sm" style="pointer-events:none" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          <q-banner rounded class="bg-blue-1 q-mb-md">
            <template #avatar><q-icon name="info" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">[미리보기]·[PDF 출력]·[Excel]은 <strong>모든 상태</strong>에서 사용할 수 있습니다.</span>
          </q-banner>

          <!-- 자동 집계 탭 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">자동 집계 업무 — 탭 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="tab in detailTabs" :key="tab.name" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="tab.icon" :color="tab.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ tab.name }}</span>
                    <q-badge v-if="tab.cond" outline color="grey-6" :label="tab.cond" style="font-size:10px" />
                  </div>
                  <div class="text-caption text-grey-7">{{ tab.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- 업무 구분 색상 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">프로젝트별·개인별 탭 내 업무 구분</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="b in breakdown" :key="b.label" class="row items-center q-gutter-xs">
              <q-icon :name="b.icon" :color="b.color" size="16px" />
              <span class="text-caption text-weight-bold" :class="`text-${b.color}`">{{ b.label }}</span>
            </div>
          </div>

          <!-- 전체 업무 탭 컬럼 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">전체 업무 / 차주 계획 탭 테이블 컬럼</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="col in workItemCols" :key="col" outline color="primary" size="sm">{{ col }}</q-chip>
          </div>

          <!-- 이슈 상태/우선순위 -->
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-sm-6">
              <div class="text-subtitle2 text-weight-bold q-mb-sm">이슈 상태</div>
              <div class="row q-gutter-xs" style="flex-wrap:wrap">
                <q-badge v-for="s in issueStatuses" :key="s.label" color="grey-5" :label="s.label" />
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">마감일 초과 + 미완료 → <q-badge color="negative" label="지연" /> 표시</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-subtitle2 text-weight-bold q-mb-sm">우선순위</div>
              <div class="row q-gutter-xs" style="flex-wrap:wrap">
                <q-badge v-for="p in priorities" :key="p.label" :color="p.color" :label="p.label" />
              </div>
            </div>
          </div>

          <!-- 수기 항목 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">수기 항목 섹션 (3개)</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="sec in manualSections" :key="sec.title" class="col-12 col-sm-4">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="sec.icon" :color="sec.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ sec.title }}</span>
                  </div>
                  <div class="text-caption text-grey-7 q-mb-xs">입력 필드:</div>
                  <div class="text-caption text-grey-8">{{ sec.fields }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
          <q-banner rounded class="bg-amber-1 q-mb-md">
            <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
            <span class="text-amber-9 text-body2">
              각 항목 왼쪽의 <q-icon name="check_circle" color="positive" size="14px" /> 아이콘을 클릭하면 보고서 포함 여부를 토글할 수 있습니다.
              흐리게 표시된 항목은 PDF·Excel에 포함되지 않습니다.
              <br><strong>확정(CONFIRMED) 상태에서는 수기 항목 추가·수정·삭제가 불가합니다.</strong>
            </span>
          </q-banner>
        </div>

        <!-- ④ PDF / 미리보기 -->
        <div :id="sections[3]!.id" class="guide-section">
          <div class="section-title"><q-icon name="picture_as_pdf" color="deep-orange" class="q-mr-sm" />PDF 출력 / 미리보기</div>

          <div class="text-body2 text-grey-7 q-mb-md">보고서 상세 화면 상단에서 미리보기 또는 PDF 출력을 선택합니다.</div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="p in pdfOptions" :key="p.btn" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="row items-center q-gutter-sm q-mb-sm">
                    <q-btn :color="p.color" :icon="p.icon" :label="p.btn" no-caps unelevated size="sm" style="pointer-events:none" />
                  </div>
                  <div class="text-caption text-grey-7">{{ p.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">PDF 출력 내용</div>
          <q-list dense class="q-mb-md">
            <q-item v-for="c in pdfContents" :key="c" class="q-px-none">
              <q-item-section avatar style="min-width:20px"><q-icon name="check" color="positive" size="16px" /></q-item-section>
              <q-item-section class="text-body2">{{ c }}</q-item-section>
            </q-item>
          </q-list>

          <q-banner rounded class="bg-blue-1">
            <template #avatar><q-icon name="lightbulb" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">
              PDF에서 색상이 흰색으로 나온다면 브라우저 인쇄 설정에서 <strong>"배경 그래픽 인쇄"</strong>를 켜주세요.
              Chrome: 인쇄 대화상자 → 더보기 → 배경 그래픽 체크
            </span>
          </q-banner>
        </div>

        <!-- ⑤ 업무 현황 -->
        <div :id="sections[4]!.id" class="guide-section">
          <div class="section-title"><q-icon name="calendar_month" color="teal" class="q-mr-sm" />업무 현황 (캘린더)</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>스케줄 관리 → 업무 현황</strong>을 클릭하면 팀 전체 업무를 캘린더로 볼 수 있습니다.
            <strong>TASK · 하위작업(SUB_TASK)</strong> 유형의 이슈만 표시됩니다.
          </div>

          <!-- 담당자 필터 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">담당자 필터</div>
          <q-card flat bordered class="q-mb-md">
            <q-card-section class="q-py-sm">
              <div class="row items-center q-gutter-xs" style="flex-wrap:wrap">
                <span class="text-caption text-grey-5">담당자</span>
                <q-chip dense color="primary" text-color="white" size="sm">전체</q-chip>
                <q-chip v-for="p in sampleAssignees" :key="p.name"
                  dense outline size="sm" :style="`border-color:${p.color};color:${p.color}`">
                  <q-avatar :style="`background:${p.color};color:#fff;font-size:10px`" size="18px">{{ p.name.charAt(0) }}</q-avatar>
                  {{ p.name }}
                </q-chip>
              </div>
            </q-card-section>
          </q-card>
          <q-list dense class="q-mb-md">
            <q-item v-for="t in filterTips" :key="t.label" class="q-px-none">
              <q-item-section avatar style="min-width:20px"><q-icon name="info" color="primary" size="14px" /></q-item-section>
              <q-item-section class="text-caption text-grey-8"><strong>{{ t.label }}:</strong> {{ t.desc }}</q-item-section>
            </q-item>
          </q-list>

          <!-- 캘린더 뷰 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">캘린더 뷰 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="v in calViews" :key="v.name" class="col-12 col-sm-4">
              <q-card flat bordered class="text-center q-pa-md">
                <q-icon :name="v.icon" :color="v.color" size="28px" class="q-mb-xs" />
                <div class="text-body2 text-weight-bold q-mb-xs">{{ v.name }}</div>
                <div class="text-caption text-grey-6">{{ v.desc }}</div>
              </q-card>
            </div>
          </div>

          <!-- 이벤트 클릭 팝업 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">이벤트 클릭 시 팝업 표시 정보</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="info in popupInfo" :key="info" outline color="teal" size="sm">{{ info }}</q-chip>
          </div>
          <q-banner rounded class="bg-orange-1 q-mb-md">
            <template #avatar><q-icon name="warning" color="orange-8" /></template>
            <span class="text-orange-9 text-body2">마감일이 오늘 이전이고 완료(DONE)가 아닌 업무는 마감일이 <strong>빨간색 + ⚠ 아이콘</strong>으로 표시됩니다.</span>
          </q-banner>

          <q-banner rounded class="bg-teal-1">
            <template #avatar><q-icon name="info" color="teal-7" /></template>
            <span class="text-teal-9 text-body2">
              담당자 필터 변경 시 API를 재호출하지 않고 <strong>로컬에서 즉시 필터링</strong>됩니다.
              기간(월/주)을 이동할 때만 새 데이터를 불러옵니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑥ FAQ -->
        <div :id="sections[5]!.id" class="guide-section">
          <div class="section-title"><q-icon name="quiz" color="purple" class="q-mr-sm" />자주 묻는 질문 (FAQ)</div>
          <q-expansion-item v-for="faq in faqs" :key="faq.q"
            :label="faq.q" expand-separator
            header-class="text-body2 text-weight-medium"
            class="q-mb-xs rounded-borders" style="border:1px solid #e0e0e0">
            <q-card flat>
              <q-card-section class="text-body2 text-grey-8" style="line-height:1.8">{{ faq.a }}</q-card-section>
            </q-card>
          </q-expansion-item>
        </div>

      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const active = ref('what-is-schedule')

const sections = [
  { id: 'what-is-schedule', label: '스케줄 관리란?',   icon: 'info' },
  { id: 'report-list',      label: '주간 보고 목록',    icon: 'event_note' },
  { id: 'report-detail',    label: '주간 보고 상세',    icon: 'description' },
  { id: 'pdf-print',        label: 'PDF 출력',          icon: 'picture_as_pdf' },
  { id: 'work-status',      label: '업무 현황 캘린더',  icon: 'calendar_month' },
  { id: 'schedule-faq',     label: '자주 묻는 질문',    icon: 'quiz' },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function onScroll() {
  for (const sec of [...sections].reverse()) {
    const el = document.getElementById(sec.id)
    if (el && el.getBoundingClientRect().top <= 120) { active.value = sec.id; return }
  }
}
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

// ── 데이터 ───────────────────────────────────────────────────────────────
const modules = [
  { icon: 'event_note',     color: 'primary',    bg: '#EFF6FF', label: '주간 보고',  desc: 'PM 업무 자동 취합 보고서' },
  { icon: 'calendar_month', color: 'teal',       bg: '#F0FDFA', label: '업무 현황',  desc: '팀 전체 일정 캘린더 조회' },
  { icon: 'picture_as_pdf', color: 'deep-orange',bg: '#FFF7ED', label: 'PDF 출력',   desc: '인쇄용 보고서 생성' },
]

const topButtons = [
  { icon: 'download', label: '목록 Excel', color: 'positive' },
  { icon: 'add',      label: '새 보고서 생성', color: 'primary' },
]

const tableColumns = [
  { name: '주차',    desc: '연도 + 주차 번호 (예: 2026년 28주차)' },
  { name: '기간',    desc: '보고서 기간 (시작일 ~ 종료일)' },
  { name: '제목',    desc: '보고서 제목 (자동 생성 또는 직접 입력)' },
  { name: '상태',    desc: '초안 / 검토중 / 확정' },
  { name: '업무 현황', desc: '전체·완료·진행·지연 건수 뱃지' },
  { name: '완료율',  desc: '완료 건수 / 전체 건수 (프로그레스 바 + %)' },
  { name: '작성자',  desc: '보고서를 생성한 사람' },
  { name: '액션',    desc: '상세보기·수정·재집계·Excel·삭제 아이콘' },
]

const rowActions = [
  { icon: 'open_in_new', color: 'primary',  label: '상세보기', desc: '상세 화면으로 이동' },
  { icon: 'edit',        color: 'grey-7',   label: '수정',     desc: '제목·부서·코멘트 수정' },
  { icon: 'refresh',     color: 'teal',     label: '재집계',   desc: '목록에서 즉시 재집계' },
  { icon: 'download',    color: 'positive', label: 'Excel',   desc: '보고서 1건 Excel 다운' },
  { icon: 'delete',      color: 'negative', label: '삭제',     desc: '보고서 삭제' },
]

const reportStatuses = [
  { label: '초안',   color: 'grey-6',   desc: '작성 중. 재집계·수정 가능' },
  { label: '검토중', color: 'orange',   desc: '검토 단계. 수기 항목 추가 가능' },
  { label: '확정',   color: 'positive', desc: '최종 확정. 수기 항목 수정 불가' },
]

const createFields = [
  { label: '연도',  required: true,  desc: '보고서가 속하는 연도를 입력합니다.' },
  { label: '주차',  required: true,  desc: '보고서 주차를 입력합니다.' },
  { label: '기간',  required: false, desc: '연도·주차를 입력하면 ISO 8601 기준으로 자동 계산됩니다.' },
  { label: '제목',  required: true,  desc: '"N년 N주차 주간 보고" 형식으로 자동 생성됩니다. 직접 수정 가능합니다.' },
  { label: '부서',  required: false, desc: '보고서에 표시할 부서명을 입력합니다.' },
]

const statCards = [
  { label: '총 업무', example: '12', color: 'text-grey-8' },
  { label: '완료',   example: '7',  color: 'text-positive' },
  { label: '진행 중', example: '4', color: 'text-primary' },
  { label: '지연',   example: '1',  color: 'text-negative' },
  { label: '완료율', example: '58%',color: 'text-teal' },
]

const statusButtons = [
  {
    status: '초안 (DRAFT)', color: 'grey-6',
    buttons: [
      { label: '재집계',   icon: 'refresh',      color: 'teal' },
      { label: '검토 완료', icon: 'rate_review',  color: 'orange' },
    ],
  },
  {
    status: '검토중 (REVIEWING)', color: 'orange',
    buttons: [
      { label: '보고 확정',  icon: 'check_circle', color: 'positive' },
    ],
  },
  {
    status: '확정 (CONFIRMED)', color: 'positive',
    buttons: [
      { label: '확정 해제', icon: 'lock_open', color: 'grey-7' },
    ],
  },
]

const detailTabs = [
  {
    icon: 'folder_open', color: 'primary', name: '프로젝트별', cond: '',
    desc: '프로젝트 단위로 펼침(expansion-item). 각 프로젝트 안에서 완료·진행중·지연·차주계획으로 구분해 이슈 목록을 표시합니다.',
  },
  {
    icon: 'person', color: 'teal', name: '개인별', cond: '',
    desc: '담당자 단위로 펼침(expansion-item). 각 담당자 안에서 완료·진행중·지연·차주계획으로 구분해 이슈 목록을 표시합니다.',
  },
  {
    icon: 'list_alt', color: 'indigo', name: '전체 업무', cond: '',
    desc: '번호·업무명·담당자·우선순위·상태·마감일 컬럼의 테이블로 전체 이슈를 한눈에 봅니다.',
  },
  {
    icon: 'event_upcoming', color: 'grey-6', name: '차주 계획', cond: '차주 이슈 있을 때만',
    desc: '다음 주 예정 업무 목록 테이블입니다. 차주 계획이 없으면 탭이 표시되지 않습니다.',
  },
]

const breakdown = [
  { icon: 'check_circle', color: 'positive', label: '✅ 완료' },
  { icon: 'autorenew',    color: 'primary',  label: '🔄 진행 중' },
  { icon: 'warning',      color: 'negative', label: '⚠ 지연' },
  { icon: 'push_pin',     color: 'grey-7',   label: '📌 차주 계획' },
]

const workItemCols = ['번호', '업무명', '담당자', '우선순위', '상태', '마감일']

const issueStatuses = [
  { label: '백로그' }, { label: '할 일' }, { label: '진행 중' }, { label: '검토 중' }, { label: '완료' },
]

const priorities = [
  { label: '최하', color: 'grey' }, { label: '낮음', color: 'blue-grey' },
  { label: '중간', color: 'orange' }, { label: '높음', color: 'deep-orange' }, { label: '최고', color: 'red' },
]

const manualSections = [
  {
    icon: 'task_alt', color: 'blue', title: '주요 안건',
    fields: '제목, 카테고리, 진행상태(예정·진행중·완료·지연·보류), 내용, 담당자',
  },
  {
    icon: 'warning_amber', color: 'orange', title: '특이사항 및 리스크',
    fields: '제목, 유형(itemType), 영향도(낮음·보통·높음), 내용, 대응(actionPlan)',
  },
  {
    icon: 'gavel', color: 'purple', title: '결정 필요 사항',
    fields: '제목, 배경, 선택지, 요청 내용, 희망 결정일',
  },
]

const pdfOptions = [
  {
    btn: '미리보기', icon: 'preview', color: 'primary',
    desc: '인쇄용 레이아웃을 새 탭에서 미리 확인합니다. 자동 인쇄가 실행되지 않으므로 먼저 확인하는 용도로 사용하세요.',
  },
  {
    btn: 'PDF 출력', icon: 'picture_as_pdf', color: 'deep-orange',
    desc: '인쇄용 페이지를 열고 브라우저 인쇄 대화상자를 자동으로 실행합니다. "PDF로 저장"을 선택하면 PDF 파일로 저장됩니다.',
  },
]

const pdfContents = [
  '개인별 업무 간트 차트 (완료·진행·지연·예정 색상 구분)',
  '주요 안건 (포함 체크된 항목만)',
  '특이사항 및 리스크 (포함 체크된 항목만)',
  '결정 필요 사항 (포함 체크된 항목만)',
  '관리자 코멘트 (입력된 경우)',
]

const sampleAssignees = [
  { name: '김민준', color: '#1976d2' },
  { name: '이서연', color: '#388e3c' },
  { name: '박도현', color: '#7b1fa2' },
]

const filterTips = [
  { label: '[전체] 클릭',   desc: '모든 담당자의 업무를 표시합니다. 선택된 담당자가 있을 때 클릭하면 선택이 해제됩니다.' },
  { label: '담당자 칩 클릭', desc: '해당 담당자만 표시합니다. 여러 명을 클릭하면 다중 선택됩니다. "N명 선택" 문구가 표시됩니다.' },
  { label: '담당자 색상',   desc: '각 담당자는 고유한 색상(10가지 팔레트)으로 구분됩니다. 캘린더 이벤트와 동일한 색상입니다.' },
]

const calViews = [
  { icon: 'calendar_view_month', color: 'primary', name: '월 보기',   desc: '한 달치 업무를 달력으로 봅니다. (기본 뷰)' },
  { icon: 'calendar_view_week',  color: 'teal',    name: '주 보기',   desc: '한 주치 업무를 상세히 봅니다.' },
  { icon: 'navigate_next',       color: 'grey-6',  name: '기간 이동', desc: 'prev·next 버튼 또는 [오늘] 버튼으로 이동합니다.' },
]

const popupInfo = ['이슈 유형 아이콘', '프로젝트키-번호', '상태 뱃지', '업무 제목', '우선순위', '프로젝트명', '담당자(아바타)', '시작일', '마감일']

const faqs = [
  { q: '보고서를 생성했는데 업무가 아무것도 안 나와요.',  a: '해당 기간에 등록된 이슈가 없거나 스프린트 날짜 설정이 맞지 않을 수 있습니다. 상세 화면의 [재집계] 버튼을 눌러보고, 그래도 안 나오면 이슈의 시작일·마감일을 확인해주세요.' },
  { q: '재집계는 언제 가능한가요?',                      a: '보고서 상태가 초안(DRAFT)일 때만 [재집계] 버튼이 활성화됩니다. 검토중·확정 상태에서는 재집계할 수 없습니다. 확정 해제 후 재집계하세요.' },
  { q: '수기 항목을 추가했는데 PDF에 안 나와요.',          a: '항목 왼쪽의 동그라미 아이콘이 흰색이면 보고서에서 제외된 상태입니다. 클릭해서 초록색 체크 아이콘으로 바꾸면 포함됩니다.' },
  { q: '확정 상태에서 수기 항목을 수정하고 싶어요.',       a: '[확정 해제] 버튼으로 검토중 상태로 되돌린 후 수정하세요. 수정 후 다시 [보고 확정]을 누르면 됩니다.' },
  { q: '업무 현황 캘린더에서 일부 업무가 안 보여요.',      a: '캘린더에는 TASK·SUB_TASK 유형이면서 시작일 또는 마감일이 있는 이슈만 표시됩니다. 날짜가 없는 이슈는 캘린더에 나타나지 않습니다.' },
  { q: 'PDF 출력 시 색상이 흰색으로 나와요.',             a: '브라우저 인쇄 설정에서 "배경 그래픽 인쇄" 옵션을 켜주세요. Chrome: 인쇄 대화상자 → 더보기 → 배경 그래픽 체크박스 활성화.' },
  { q: '목록 Excel과 상세 Excel은 어떻게 다른가요?',       a: '목록 Excel(상단 [목록 Excel] 버튼)은 현재 필터 기준의 보고서 목록 전체를 다운로드합니다. 상세 Excel(행의 다운로드 아이콘)은 해당 보고서 1건의 상세 업무 데이터를 다운로드합니다.' },
]
</script>

<style scoped>
.guide-section {
  margin-bottom: 48px;
  scroll-margin-top: 80px;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
  display: flex;
  align-items: center;
}
.sticky-toc {
  position: sticky;
  top: 80px;
}
</style>
