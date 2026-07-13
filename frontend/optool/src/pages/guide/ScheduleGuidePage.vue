<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">📅 스케줄 관리 사용 가이드</div>
        <div class="text-caption text-grey-6">주간 보고 생성, 업무 일정 관리, 현황 확인 방법을 설명합니다.</div>
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
              <div class="text-body1 text-weight-medium q-mb-sm">Jira와 연동된 <span class="text-primary text-weight-bold">자동 업무 취합 시스템</span>입니다.</div>
              <div class="text-body2 text-grey-8 q-mb-md">
                팀원별 Jira 이슈를 자동으로 가져와 주간 보고서를 생성하고, 업무 일정을 캘린더로 시각화합니다.
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

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-sm-6">
              <q-banner rounded class="bg-blue-1">
                <template #avatar><q-icon name="sync" color="blue-7" /></template>
                <span class="text-blue-9 text-body2">Jira에서 업무 정보를 <strong>자동 동기화</strong>합니다. 담당자가 Jira에 업무를 입력하면 보고서에 자동 반영됩니다.</span>
              </q-banner>
            </div>
            <div class="col-12 col-sm-6">
              <q-banner rounded class="bg-green-1">
                <template #avatar><q-icon name="picture_as_pdf" color="green-7" /></template>
                <span class="text-green-9 text-body2">보고서를 <strong>PDF·Excel</strong>로 내보내어 회의 자료나 보고 자료로 바로 활용할 수 있습니다.</span>
              </q-banner>
            </div>
          </div>
        </div>

        <!-- ② 주간 보고 목록 -->
        <div :id="sections[1]!.id" class="guide-section">
          <div class="section-title"><q-icon name="event_note" color="primary" class="q-mr-sm" />주간 보고 목록</div>

          <div class="text-body2 text-grey-7 q-mb-md">메뉴에서 <strong>스케줄 관리 → 주간 보고</strong>를 클릭하면 생성된 모든 보고서를 볼 수 있습니다.</div>

          <!-- 목록 모형 -->
          <q-card flat bordered class="q-mb-md">
            <q-card-section class="bg-grey-1 q-pa-sm">
              <div class="text-caption text-weight-bold text-grey-6 q-mb-sm">📱 주간 보고 목록 화면</div>
              <div class="row justify-between items-center q-mb-sm">
                <q-input model-value="" outlined dense placeholder="보고서 검색..." class="col-6" style="pointer-events:none">
                  <template #prepend><q-icon name="search" /></template>
                </q-input>
                <q-btn unelevated color="primary" icon="add" label="새 보고서 생성" no-caps size="sm" style="pointer-events:none" />
              </div>
              <q-card flat bordered v-for="card in reportCards" :key="card.week" class="q-mb-xs q-pa-sm">
                <div class="row items-center q-gutter-sm">
                  <q-chip :color="card.color" text-color="white" dense size="sm" square>{{ card.status }}</q-chip>
                  <div class="col">
                    <div class="text-body2 text-weight-medium">{{ card.title }}</div>
                    <div class="text-caption text-grey-6">{{ card.period }}</div>
                  </div>
                  <q-btn flat round dense icon="picture_as_pdf" color="grey-5" size="sm" style="pointer-events:none" />
                </div>
              </q-card>
            </q-card-section>
          </q-card>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">새 보고서 생성 방법</div>
          <q-timeline color="primary">
            <q-timeline-entry title="[새 보고서 생성] 버튼 클릭" icon="add_circle" color="primary">
              <div class="text-body2">오른쪽 상단의 파란 버튼을 클릭합니다.</div>
            </q-timeline-entry>
            <q-timeline-entry title="연도·주차·기간 입력" icon="event" color="primary">
              <div class="text-body2 q-mb-sm">주차와 기간(월요일~금요일)을 설정합니다.</div>
              <div class="mockup-box" style="padding:12px">
                <div class="row q-gutter-sm">
                  <q-chip outline color="primary" size="sm">2026년</q-chip>
                  <q-chip outline color="primary" size="sm">28주차</q-chip>
                  <q-chip outline color="grey" size="sm">2026-07-07 ~ 2026-07-11</q-chip>
                </div>
              </div>
            </q-timeline-entry>
            <q-timeline-entry title="자동 집계 실행" icon="sync" color="teal">
              <div class="text-body2">확인을 누르면 Jira에서 해당 기간의 업무를 자동으로 가져옵니다. 잠시 기다리면 보고서가 생성됩니다.</div>
            </q-timeline-entry>
          </q-timeline>
        </div>

        <!-- ③ 주간 보고 상세 -->
        <div :id="sections[2]!.id" class="guide-section">
          <div class="section-title"><q-icon name="description" color="primary" class="q-mr-sm" />주간 보고 상세 화면</div>

          <div class="text-body2 text-grey-7 q-mb-md">보고서를 클릭하면 상세 화면이 열립니다. 자동 집계된 업무와 수기 항목을 함께 관리합니다.</div>

          <!-- 탭 구조 설명 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">화면 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="tab in detailTabs" :key="tab.name" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-sm q-mb-xs">
                    <q-icon :name="tab.icon" :color="tab.color" size="20px" />
                    <span class="text-body2 text-weight-bold">{{ tab.name }}</span>
                  </div>
                  <div class="text-caption text-grey-7">{{ tab.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- 개인별 탭 간트 설명 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">
            <q-icon name="view_timeline" color="primary" class="q-mr-xs" />개인별 업무 일정 (간트 차트)
          </div>
          <q-card flat bordered class="q-mb-md">
            <q-card-section>
              <div class="text-body2 text-grey-8 q-mb-sm">개인별 탭에서는 담당자별 업무를 <strong>간트 차트</strong> 형식으로 보여줍니다. 누가 어떤 업무를 언제 하고 있는지 한눈에 파악할 수 있습니다.</div>
              <!-- 간트 범례 모형 -->
              <div class="row q-gutter-sm q-mb-sm" style="flex-wrap:wrap">
                <div v-for="legend in ganttLegend" :key="legend.label" class="row items-center q-gutter-xs">
                  <div :style="`width:32px;height:14px;background:${legend.color};border-radius:3px`"></div>
                  <span class="text-caption">{{ legend.label }}</span>
                </div>
              </div>
              <!-- 간트 미니 모형 -->
              <div style="overflow-x:auto">
                <table class="mini-gantt">
                  <thead>
                    <tr>
                      <th class="mg-name">담당자 / 업무</th>
                      <th v-for="d in miniDays" :key="d" class="mg-day">{{ d }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="p in miniPersons" :key="p.name">
                      <tr class="mg-person-row">
                        <td :colspan="miniDays.length + 1" class="text-caption text-weight-bold">{{ p.name }}</td>
                      </tr>
                      <tr v-for="task in p.tasks" :key="task.name">
                        <td class="mg-task-name text-caption">{{ task.name }}</td>
                        <td v-for="(d, di) in miniDays" :key="d"
                          :style="`background:${task.cells[di] ?? 'transparent'};border-radius:${getCellRadius(task.cells, di)}`">
                        </td>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </div>
            </q-card-section>
          </q-card>

          <!-- 수기 항목 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm"><q-icon name="edit" color="orange" class="q-mr-xs" />수기 항목 입력</div>
          <div class="row q-col-gutter-sm">
            <div v-for="manual in manualSections" :key="manual.title" class="col-12 col-sm-4">
              <q-card flat bordered class="text-center q-pa-md">
                <q-icon :name="manual.icon" :color="manual.color" size="28px" class="q-mb-xs" />
                <div class="text-body2 text-weight-bold q-mb-xs">{{ manual.title }}</div>
                <div class="text-caption text-grey-6">{{ manual.desc }}</div>
              </q-card>
            </div>
          </div>
        </div>

        <!-- ④ PDF 출력 -->
        <div :id="sections[3]!.id" class="guide-section">
          <div class="section-title"><q-icon name="picture_as_pdf" color="deep-orange" class="q-mr-sm" />PDF 출력 / 미리보기</div>

          <div class="text-body2 text-grey-7 q-mb-md">보고서를 인쇄 전용 레이아웃으로 미리 확인하고 PDF로 저장할 수 있습니다.</div>

          <q-stepper v-model="pdfStep" color="primary" animated flat class="q-mb-md" style="border:1px solid #e2e8f0;border-radius:8px">
            <q-step :name="1" title="미리보기 버튼" icon="preview" :done="pdfStep > 1">
              보고서 상세 화면 상단의 <strong>[미리보기]</strong> 버튼을 클릭합니다.
            </q-step>
            <q-step :name="2" title="레이아웃 확인" icon="visibility" :done="pdfStep > 2">
              인쇄용 페이지가 열립니다. 개인별 업무 간트 차트와 주요 안건이 모두 포함됩니다.
            </q-step>
            <q-step :name="3" title="인쇄 / PDF 저장" icon="print" :done="pdfStep > 3">
              브라우저의 <strong>인쇄(Ctrl+P / ⌘+P)</strong> 기능을 사용하거나 인쇄 버튼을 클릭합니다. 인쇄 대상으로 <strong>"PDF로 저장"</strong>을 선택하세요.
            </q-step>
          </q-stepper>
          <div class="row q-gutter-sm justify-center">
            <q-btn flat dense size="sm" @click="pdfStep = Math.max(1, pdfStep - 1)" label="이전" />
            <q-btn flat dense size="sm" color="primary" @click="pdfStep = Math.min(3, pdfStep + 1)" label="다음 단계 보기" />
          </div>

          <q-banner rounded class="bg-blue-1 q-mt-md">
            <template #avatar><q-icon name="lightbulb" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">
              PDF에서 색상이 흰색으로 나온다면 브라우저 인쇄 설정에서 <strong>"배경 그래픽 인쇄"</strong>를 켜주세요.
              Chrome: 인쇄 → 더보기 → 배경 그래픽 체크
            </span>
          </q-banner>
        </div>

        <!-- ⑤ 업무 현황 -->
        <div :id="sections[4]!.id" class="guide-section">
          <div class="section-title"><q-icon name="calendar_month" color="teal" class="q-mr-sm" />업무 현황 (캘린더)</div>

          <div class="text-body2 text-grey-7 q-mb-md">메뉴에서 <strong>스케줄 관리 → 업무 현황</strong>을 클릭하면 팀 전체 업무를 캘린더로 볼 수 있습니다.</div>

          <div class="row q-col-gutter-md q-mb-md">
            <div v-for="feat in workStatusFeats" :key="feat.title" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="row items-center q-gutter-sm q-mb-sm">
                    <q-icon :name="feat.icon" :color="feat.color" size="22px" />
                    <span class="text-body2 text-weight-bold">{{ feat.title }}</span>
                  </div>
                  <div class="text-caption text-grey-7">{{ feat.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- 담당자 색상 예시 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">담당자별 색상 구분</div>
          <div class="row q-gutter-sm q-mb-md" style="flex-wrap:wrap">
            <div v-for="p in personColors" :key="p.name" class="row items-center q-gutter-xs">
              <q-avatar :color="p.color" text-color="white" size="28px" style="font-size:11px">{{ p.initial }}</q-avatar>
              <span class="text-caption">{{ p.name }}</span>
            </div>
          </div>

          <q-banner rounded class="bg-teal-1">
            <template #avatar><q-icon name="touch_app" color="teal-7" /></template>
            <span class="text-teal-9 text-body2">캘린더에서 업무 바를 클릭하면 이슈 번호, 마감일, 상태 등 상세 정보를 팝업으로 볼 수 있습니다.</span>
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
const pdfStep = ref(1)

const sections = [
  { id: 'what-is-schedule', label: '스케줄 관리란?',  icon: 'info' },
  { id: 'report-list',      label: '주간 보고 목록',   icon: 'event_note' },
  { id: 'report-detail',    label: '주간 보고 상세',   icon: 'description' },
  { id: 'pdf-print',        label: 'PDF 출력',         icon: 'picture_as_pdf' },
  { id: 'work-status',      label: '업무 현황 캘린더', icon: 'calendar_month' },
  { id: 'schedule-faq',     label: '자주 묻는 질문',   icon: 'quiz' },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function onScroll() {
  for (const sec of [...sections].reverse()) {
    const el = document.getElementById(sec.id)
    if (el && el.getBoundingClientRect().top <= 120) {
      active.value = sec.id
      return
    }
  }
}
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

// ── 데이터 ──────────────────────────────────────────────────────────
const modules = [
  { icon: 'event_note', color: 'primary', bg: '#EFF6FF', label: '주간 보고',     desc: 'Jira 업무 자동 취합 보고서' },
  { icon: 'calendar_month', color: 'teal', bg: '#F0FDFA', label: '업무 현황',    desc: '팀 전체 일정 캘린더 조회' },
  { icon: 'picture_as_pdf', color: 'deep-orange', bg: '#FFF7ED', label: 'PDF 출력', desc: '인쇄용 보고서 생성' },
]

const reportCards = [
  { week: 28, title: '2026년 28주차 주간보고', period: '2026-07-07 ~ 2026-07-11', status: '초안',   color: 'grey-6' },
  { week: 27, title: '2026년 27주차 주간보고', period: '2026-06-30 ~ 2026-07-04', status: '확정',   color: 'positive' },
  { week: 26, title: '2026년 26주차 주간보고', period: '2026-06-23 ~ 2026-06-27', status: '검토중', color: 'orange' },
]

const detailTabs = [
  { icon: 'folder',         color: 'primary',    name: '프로젝트별 탭', desc: '프로젝트 기준으로 완료/진행/지연 업무를 확인합니다.' },
  { icon: 'person',         color: 'teal',       name: '개인별 탭',     desc: '담당자별 업무 현황을 간트 차트로 시각화합니다.' },
  { icon: 'edit',           color: 'orange',     name: '수기 항목',     desc: '자동 집계에 없는 항목을 직접 입력합니다.' },
  { icon: 'history',        color: 'grey-6',     name: '수정 이력',     desc: '보고서 수정 이력을 확인합니다.' },
]

const ganttLegend = [
  { label: '완료',   color: '#15803d' },
  { label: '진행 중', color: '#1d4ed8' },
  { label: '지연',   color: '#b91c1c' },
  { label: '예정',   color: '#94a3b8' },
]

const G = '#15803d'; const B = '#1d4ed8'; const R = '#b91c1c'; const S = '#94a3b8'
const miniDays = ['7/7', '7/8', '7/9', '7/10', '7/11', '7/14', '7/15']
const miniPersons = [
  {
    name: '김민준',
    tasks: [
      { name: '대시보드 위젯', cells: [G, G, G, '', '', '', ''] },
      { name: 'PDF 스타일 개선', cells: ['', '', B, B, B, B, ''] },
      { name: '메뉴 권한 제어', cells: [R, R, R, '', '', '', ''] },
      { name: 'SR 다운로드', cells: ['', '', '', '', '', S, S] },
    ],
  },
  {
    name: '이서연',
    tasks: [
      { name: 'SR 상태 흐름', cells: [G, G, '', '', '', '', ''] },
      { name: 'PM 보드 UI', cells: ['', '', B, B, B, '', ''] },
      { name: '월간보고 취합', cells: [R, R, R, R, '', '', ''] },
    ],
  },
]

function getCellRadius(cells: (string|undefined)[], i: number): string {
  const cur = cells[i]
  if (!cur) return '0'
  const prev = cells[i - 1]
  const next = cells[i + 1]
  const l = !prev || prev !== cur ? '4px' : '0'
  const r = !next || next !== cur ? '4px' : '0'
  return `${l} ${r} ${r} ${l}`
}

const manualSections = [
  { icon: 'push_pin',      color: 'primary',    title: '주요 안건',        desc: '이번 주 주요 이슈와 결정사항' },
  { icon: 'warning',       color: 'negative',   title: '이슈 / 리스크',    desc: '발생한 문제와 대응 방안' },
  { icon: 'gavel',         color: 'orange',     title: '결정 필요 사항',   desc: '승인이나 의사결정이 필요한 항목' },
]

const workStatusFeats = [
  { icon: 'filter_list',    color: 'primary',    title: '담당자 필터',   desc: '상단 칩을 클릭해서 특정 담당자만 보거나 여러 명을 선택할 수 있습니다.' },
  { icon: 'view_week',      color: 'teal',       title: '월/주 보기 전환', desc: '오른쪽 상단 버튼으로 월별 캘린더와 주별 캘린더를 전환합니다.' },
  { icon: 'touch_app',      color: 'orange',     title: '이벤트 클릭',   desc: '업무 바를 클릭하면 이슈 번호, 담당자, 마감일 상세 정보를 팝업으로 볼 수 있습니다.' },
  { icon: 'chevron_left',   color: 'grey-6',     title: '기간 이동',     desc: '이전/다음 화살표로 원하는 날짜로 이동합니다. 오늘 버튼으로 현재 날짜로 돌아옵니다.' },
]

const personColors = [
  { name: '김민준', color: 'blue',    initial: '김' },
  { name: '이서연', color: 'teal',    initial: '이' },
  { name: '박도현', color: 'purple',  initial: '박' },
  { name: '최지우', color: 'orange',  initial: '최' },
]

const faqs = [
  { q: '보고서를 생성했는데 업무가 아무것도 안 나와요.',          a: 'Jira에 해당 기간의 이슈가 없거나, 스프린트 날짜 설정이 맞지 않을 수 있습니다. 상세 화면의 [재집계] 버튼을 눌러보고, 그래도 안 나오면 Jira 이슈의 시작일/마감일을 확인해주세요.' },
  { q: '이미 생성한 보고서의 기간을 변경할 수 있나요?',           a: '확정 전(초안/검토 중) 상태에서는 기간을 수정하고 재집계할 수 있습니다. 확정 상태에서는 관리자에게 문의하세요.' },
  { q: 'PDF 출력 시 색상이 흰색으로 나와요.',                    a: '브라우저 인쇄 설정에서 "배경 그래픽 인쇄" 옵션을 켜주세요. Chrome 기준: 인쇄 대화상자 → 더보기 → 배경 그래픽 체크박스 활성화.' },
  { q: '업무 현황 캘린더에서 내 업무만 보려면?',                  a: '상단의 담당자 필터 칩에서 내 이름만 선택하면 됩니다. 선택을 해제하면 전체 팀의 업무가 다시 표시됩니다.' },
  { q: '간트 차트에서 지연 업무는 어떻게 표시되나요?',            a: '마감일이 지났으나 완료되지 않은 업무는 빨간색(■ 지연)으로 표시됩니다. 같은 업무가 진행 중이더라도 지연이면 빨간색으로 우선 표시됩니다.' },
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
.mockup-box {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}
.mini-gantt {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
}
.mini-gantt th, .mini-gantt td {
  border: 1px solid #e2e8f0;
  padding: 3px 6px;
  white-space: nowrap;
}
.mini-gantt .mg-name { width: 130px; background: #f1f5f9; font-weight: 600; }
.mini-gantt .mg-day  { width: 44px; text-align: center; background: #f8fafc; font-weight: 600; }
.mini-gantt .mg-task-name { max-width: 130px; overflow: hidden; text-overflow: ellipsis; }
.mini-gantt .mg-person-row td { background: #e2e8f0; color: #334155; padding: 4px 8px; }
.mini-gantt td[style*='background'] { border: none; }
</style>
