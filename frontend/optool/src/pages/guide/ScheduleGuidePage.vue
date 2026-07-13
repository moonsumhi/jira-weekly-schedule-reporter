<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">스케줄 관리 시스템 사용 가이드</div>
        <div class="text-caption text-grey-6">시나리오로 배우는 프로젝트·이슈·스프린트·주간 보고 흐름</div>
      </div>
    </div>

    <!-- 시나리오 네비 칩 -->
    <div class="row q-gutter-sm q-mb-xl" style="flex-wrap:wrap">
      <q-chip
        v-for="(sc, i) in scenarios"
        :key="i"
        clickable outline color="primary"
        @click="scrollTo(sc.id)"
      >{{ i + 1 }}. {{ sc.shortTitle }}</q-chip>
      <q-chip clickable outline color="teal" @click="scrollTo('quick-view')">내 이슈 &amp; 업무 현황</q-chip>
    </div>

    <!-- ───────────────── 시나리오 루프 ───────────────── -->
    <div v-for="(sc, si) in scenarios" :key="si" :id="sc.id" class="q-mb-xl">

      <!-- 시나리오 헤더 -->
      <q-card flat class="scenario-header q-mb-lg">
        <q-card-section class="row items-center no-wrap">
          <q-avatar size="44px" :color="sc.color" text-color="white" class="q-mr-md" style="font-size:18px;font-weight:700">
            {{ si + 1 }}
          </q-avatar>
          <div class="col">
            <div class="text-h6 text-weight-bold">{{ sc.title }}</div>
            <q-badge :color="sc.roleColor" class="q-mt-xs">{{ sc.role }}</q-badge>
          </div>
        </q-card-section>
      </q-card>

      <!-- 단계 루프 -->
      <div v-for="(step, idx) in sc.steps" :key="idx" class="q-mb-lg">
        <div class="row items-start no-wrap q-gutter-md">
          <q-avatar size="30px" color="grey-3" text-color="grey-8" style="font-size:13px;font-weight:700;flex-shrink:0;margin-top:2px">
            {{ idx + 1 }}
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">{{ step.label }}</div>
            <div class="text-body2 text-grey-7">{{ step.desc }}</div>

            <!-- 시나리오 1 목업들 -->
            <div v-if="si === 0 && idx === 1" class="mock-screen">
              <q-btn color="primary" icon="add" label="+ 조직 만들기" no-caps unelevated size="sm" />
            </div>

            <div v-if="si === 0 && idx === 2" class="mock-screen">
              <q-card flat bordered style="max-width:280px">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center justify-between">
                    <span class="text-subtitle2 text-weight-bold">데이터운영팀</span>
                    <q-badge color="primary" label="프로젝트 3개" />
                  </div>
                  <div class="text-caption text-grey-6 q-mt-xs">데이터 운영 및 플랫폼 관리</div>
                  <q-btn flat dense no-caps color="primary" icon="add" label="+ 프로젝트 추가" size="sm" class="q-mt-sm" />
                </q-card-section>
              </q-card>
            </div>

            <div v-if="si === 0 && idx === 4" class="mock-screen">
              <div class="row q-gutter-sm items-center">
                <q-badge color="purple" label="OWNER" />
                <q-badge color="teal" label="PROJECT_MANAGER" />
                <q-badge color="primary" label="MEMBER" />
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">프로젝트 초대 시 역할을 선택합니다</div>
            </div>

            <!-- 시나리오 2 목업들 -->
            <div v-if="si === 1 && idx === 1" class="mock-screen">
              <q-btn color="primary" icon="add" label="이슈 생성" no-caps unelevated size="sm" />
            </div>

            <!-- 이슈 타입 선택 목업 -->
            <div v-if="si === 1 && idx === 2" class="mock-screen">
              <div class="row q-gutter-sm" style="flex-wrap:wrap">
                <div v-for="t in issueTypes" :key="t.value" style="min-width:150px;flex:1">
                  <q-card flat bordered class="q-pa-sm">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <q-icon :name="t.icon" :color="t.color" size="16px" />
                      <span class="text-caption text-weight-bold">{{ t.label }}</span>
                    </div>
                    <div class="text-caption text-grey-6">{{ t.desc }}</div>
                  </q-card>
                </div>
              </div>
            </div>

            <!-- 폼 전체 목업 -->
            <div v-if="si === 1 && idx === 3" class="mock-screen" style="max-width:520px">
              <div class="mock-section-label q-mb-sm">기본 정보</div>
              <q-input model-value="" outlined dense label="제목 *" class="q-mb-sm" />
              <div class="row q-gutter-sm q-mb-md">
                <q-input model-value="Task" outlined dense label="타입" class="col">
                  <template #prepend><q-icon name="check_box_outline_blank" color="primary" size="16px" /></template>
                </q-input>
                <q-input model-value="보통" outlined dense label="우선순위" class="col">
                  <template #prepend><q-icon name="flag" color="grey-6" size="16px" /></template>
                </q-input>
                <q-input model-value="할 일" outlined dense label="상태" class="col" />
              </div>
              <q-separator class="q-mb-sm" />
              <div class="mock-section-label q-mb-sm">담당</div>
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="" outlined dense label="담당자" class="col">
                  <template #prepend><q-icon name="person" color="grey-6" size="16px" /></template>
                </q-input>
                <q-input model-value="홍길동" outlined dense label="보고자 (자동)" readonly class="col">
                  <template #prepend><q-icon name="person_outline" color="grey-6" size="16px" /></template>
                </q-input>
              </div>
              <div class="row q-gutter-sm q-mb-md">
                <q-input model-value="" outlined dense label="상위 Epic" class="col">
                  <template #prepend><q-icon name="bolt" color="purple" size="16px" /></template>
                </q-input>
                <q-input model-value="" outlined dense label="스토리 포인트" type="number" class="col">
                  <template #prepend><q-icon name="speed" color="grey-6" size="16px" /></template>
                </q-input>
              </div>
              <q-separator class="q-mb-sm" />
              <div class="mock-section-label q-mb-sm">일정</div>
              <div class="row q-gutter-sm">
                <q-input model-value="" outlined dense label="스프린트" class="col">
                  <template #prepend><q-icon name="loop" color="grey-6" size="16px" /></template>
                </q-input>
                <q-input model-value="" outlined dense label="시작일" type="date" stack-label class="col" />
                <q-input model-value="" outlined dense label="마감일" type="date" stack-label class="col" />
              </div>
            </div>

            <!-- 라벨·첨부파일 목업 -->
            <div v-if="si === 1 && idx === 4" class="mock-screen" style="max-width:420px">
              <div class="mock-section-label q-mb-sm">기타</div>
              <div class="row q-gutter-xs q-mb-xs">
                <q-chip dense color="blue" text-color="white" size="sm" removable>프론트엔드</q-chip>
                <q-chip dense color="orange" text-color="white" size="sm" removable>백엔드</q-chip>
                <q-chip dense color="green" text-color="white" size="sm" removable>DB</q-chip>
              </div>
              <div class="text-caption text-grey-6 q-mb-sm">↑ 라벨을 선택해 이슈를 분류합니다</div>
              <q-input model-value="" outlined dense label="설명" type="textarea" :rows="2" class="q-mb-sm" />
              <div style="border:1.5px dashed #ccc;border-radius:6px;padding:12px;text-align:center">
                <q-icon name="cloud_upload" size="22px" color="grey-5" />
                <div class="text-caption text-grey-5 q-mt-xs">파일을 끌어다 놓거나 버튼으로 첨부</div>
              </div>
            </div>

            <!-- 시나리오 3 목업들 -->
            <div v-if="si === 2 && idx === 1" class="mock-screen">
              <div style="border:2px dashed #1976d2;border-radius:8px;padding:12px">
                <div class="row items-center justify-between q-mb-sm">
                  <span class="text-subtitle2 text-weight-bold text-primary">스프린트 1 (2주)</span>
                  <q-btn color="primary" label="스프린트 시작" no-caps unelevated size="sm" />
                </div>
                <div class="text-caption text-grey-6">이슈를 이 영역으로 이동시키세요</div>
              </div>
            </div>

            <!-- 시나리오 4 목업들 -->
            <div v-if="si === 3 && idx === 1" class="mock-screen" style="overflow-x:auto">
              <div style="display:flex;gap:10px;min-width:520px">
                <div v-for="col in kanbanCols" :key="col.label" style="width:120px;flex-shrink:0">
                  <q-badge :color="col.color" :label="col.label" class="q-mb-sm full-width" style="display:block;text-align:center" />
                  <q-card v-for="card in col.cards" :key="card" flat bordered class="q-pa-xs q-mb-xs">
                    <div class="text-caption">{{ card }}</div>
                    <q-avatar size="18px" color="grey-4" text-color="grey-7" style="font-size:10px" class="q-mt-xs">U</q-avatar>
                  </q-card>
                </div>
              </div>
            </div>

            <!-- 시나리오 5 목업들 -->
            <div v-if="si === 4 && idx === 1" class="mock-screen">
              <q-btn color="primary" icon="add" label="생성 (자동 집계)" no-caps unelevated size="sm" />
            </div>

            <div v-if="si === 4 && idx === 2" class="mock-screen" style="max-width:360px">
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="2026" outlined dense label="연도" class="col" />
                <q-input model-value="28" outlined dense label="주차" class="col" />
              </div>
              <div class="text-caption text-grey-6">
                → 자동 생성: <strong>2026년 28주차 주간 보고 (07/07 ~ 07/11)</strong>
              </div>
            </div>

            <div v-if="si === 4 && idx === 3" class="mock-screen">
              <q-tabs model-value="project" dense align="left" active-color="primary">
                <q-tab name="project" label="프로젝트별" />
                <q-tab name="person" label="개인별" />
                <q-tab name="all" label="전체 업무" />
                <q-tab name="next" label="차주 계획" />
              </q-tabs>
            </div>

            <div v-if="si === 4 && idx === 5" class="mock-screen">
              <div class="row items-center q-gutter-sm">
                <q-badge color="grey-6" label="DRAFT" />
                <q-icon name="arrow_forward" color="grey-5" />
                <q-badge color="orange" label="REVIEWING" />
                <q-icon name="arrow_forward" color="grey-5" />
                <q-badge color="positive" label="CONFIRMED" />
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">초안 → 검토중 → 확정 순으로 상태를 변경합니다</div>
            </div>

          </div>
        </div>
      </div>

      <!-- 팁 배너 -->
      <q-banner v-if="sc.tip" rounded class="bg-amber-1 q-mt-sm">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9 text-body2">{{ sc.tip }}</span>
      </q-banner>
    </div>

    <!-- ───────────────── 내 이슈 & 업무 현황 섹션 ───────────────── -->
    <div id="quick-view" class="q-mb-xl">
      <q-card flat class="scenario-header q-mb-lg" style="border-left-color: #00897b">
        <q-card-section class="row items-center no-wrap">
          <q-avatar size="44px" color="teal" text-color="white" class="q-mr-md" style="font-size:18px">
            <q-icon name="dashboard" />
          </q-avatar>
          <div class="col">
            <div class="text-h6 text-weight-bold">내 이슈 &amp; 업무 현황 빠르게 보기</div>
            <q-badge color="teal" class="q-mt-xs">팀원 공통</q-badge>
          </div>
        </q-card-section>
      </q-card>

      <div class="row q-col-gutter-md">
        <div class="col-12 col-sm-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="row items-center q-mb-sm">
                <q-icon name="assignment" color="primary" class="q-mr-sm" />
                <span class="text-subtitle2 text-weight-bold">내 이슈 (대시보드)</span>
              </div>
              <div class="text-body2 text-grey-7 q-mb-sm">
                스케줄 관리 → 내 이슈에서 나와 관련된 이슈를 한눈에 확인합니다.
              </div>
              <div class="row q-gutter-xs q-mb-sm" style="pointer-events:none">
                <q-badge outline color="primary" label="담당" />
                <q-badge outline color="teal" label="참여" />
                <q-badge outline color="purple" label="보고" />
              </div>
              <div class="row q-gutter-xs" style="pointer-events:none">
                <q-badge color="orange" label="마감임박" />
                <q-badge color="negative" label="마감초과" />
              </div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="row items-center q-mb-sm">
                <q-icon name="calendar_month" color="teal" class="q-mr-sm" />
                <span class="text-subtitle2 text-weight-bold">업무 현황 (캘린더)</span>
              </div>
              <div class="text-body2 text-grey-7 q-mb-sm">
                스케줄 관리 → 업무 현황에서 팀원별 일정을 월·주 캘린더로 확인합니다.
              </div>
              <div class="row q-gutter-xs" style="pointer-events:none">
                <q-chip dense outline color="primary" label="홍길동" size="sm" />
                <q-chip dense outline color="teal" label="김영희" size="sm" />
                <q-chip dense outline color="purple" label="이철수" size="sm" />
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">상단 칩으로 담당자 필터링 가능</div>
            </q-card-section>
          </q-card>
        </div>
      </div>
    </div>

  </q-page>
</template>

<script setup lang="ts">

interface Step {
  label: string
  desc: string
}

interface Scenario {
  id: string
  shortTitle: string
  title: string
  role: string
  roleColor: string
  color: string
  steps: Step[]
  tip?: string
}

const scenarios: Scenario[] = [
  {
    id: 'sc-project',
    shortTitle: '프로젝트 시작',
    title: '새 프로젝트를 시작하고 싶어요',
    role: '관리자 · PM',
    roleColor: 'purple',
    color: 'primary',
    steps: [
      {
        label: '스케줄 관리 > 조직 클릭',
        desc: '좌측 메뉴에서 스케줄 관리 → 조직을 클릭하면 현재 등록된 조직 목록이 표시됩니다.',
      },
      {
        label: '[+ 조직 만들기] 클릭',
        desc: '버튼을 누르고 조직 이름과 설명을 입력한 뒤 저장합니다.',
      },
      {
        label: '조직 클릭 → [+ 프로젝트 추가]',
        desc: '생성된 조직 카드를 클릭하면 조직 상세 화면이 열립니다. [+ 프로젝트 추가] 버튼으로 새 프로젝트를 만드세요.',
      },
      {
        label: '프로젝트 이름 · 설명 · 키 입력',
        desc: '프로젝트 키는 이슈 번호 접두사로 사용됩니다 (예: 키가 PROJ이면 이슈가 PROJ-1, PROJ-2 형태로 생성). 저장 후 변경 불가하므로 신중하게 설정하세요.',
      },
      {
        label: '멤버 탭 → [+ 멤버 초대] → 역할 설정',
        desc: '프로젝트 상세의 멤버 탭에서 팀원을 초대하고 역할을 지정합니다.',
      },
    ],
    tip: '프로젝트 키는 한번 설정하면 변경할 수 없어요. 영문 대문자로 간결하게 설정하세요 (예: OPS, INFRA, DATA).',
  },
  {
    id: 'sc-issue',
    shortTitle: '이슈 생성 · 배정',
    title: '이슈를 만들고 팀원에게 배정하고 싶어요',
    role: '팀원 · PM',
    roleColor: 'primary',
    color: 'primary',
    steps: [
      {
        label: '스케줄 관리 > 프로젝트 > 프로젝트 선택',
        desc: '스케줄 관리 → 프로젝트 메뉴에서 작업할 프로젝트를 클릭해 진입합니다.',
      },
      {
        label: '[이슈 생성] 버튼 클릭',
        desc: '프로젝트 상세 화면 우측 상단의 [이슈 생성] 버튼을 클릭하면 생성 다이얼로그가 열립니다.',
      },
      {
        label: '이슈 타입 선택 — Epic / Story / Task',
        desc: '업무 규모와 성격에 따라 타입을 고릅니다. 일반 단위 작업은 Task, 사용자 기능 단위는 Story, 큰 업무 묶음은 Epic을 사용하세요.',
      },
      {
        label: '기본 정보 · 담당 · 일정 입력',
        desc: '제목은 필수입니다. 담당자·보고자·상위 Epic·스토리 포인트, 스프린트·시작일·마감일을 설정하면 팀원이 내 이슈 화면에서 바로 확인할 수 있습니다.',
      },
      {
        label: '라벨 · 설명 · 첨부파일 추가 (선택)',
        desc: '라벨로 이슈를 분류하고, 설명란에 상세 내용을 입력합니다. 파일은 드래그 앤 드롭으로 첨부할 수 있습니다.',
      },
      {
        label: '[이슈 추가] 클릭 → 백로그에서 확인',
        desc: '저장하면 이슈가 백로그(또는 선택한 스프린트)에 추가됩니다. 백로그 탭에서 새 이슈를 확인하고 스프린트로 이동시킬 수 있습니다.',
      },
    ],
    tip: 'Epic → Story → Task 순서로 계층 구조를 만들어 작업을 체계적으로 관리할 수 있어요. 일반 업무는 Task 하나로 시작해도 충분합니다.',
  },
  {
    id: 'sc-sprint',
    shortTitle: '스프린트 계획',
    title: '스프린트를 계획하고 시작하고 싶어요',
    role: 'PM',
    roleColor: 'teal',
    color: 'teal',
    steps: [
      {
        label: '프로젝트 > [백로그] 탭 클릭',
        desc: '프로젝트 상세에서 백로그 탭을 클릭하면 전체 이슈 목록과 스프린트 컨테이너를 볼 수 있습니다.',
      },
      {
        label: '[+ 스프린트 만들기] 클릭 → 이름 · 기간 입력',
        desc: '스프린트 이름과 시작일·종료일을 입력합니다. 스프린트 컨테이너가 생성되어 이슈를 담을 준비가 됩니다.',
      },
      {
        label: '백로그 이슈를 스프린트로 이동',
        desc: '백로그의 이슈를 드래그하거나, 이슈 우측 메뉴에서 "스프린트로 이동"을 선택해 해당 스프린트에 추가합니다.',
      },
      {
        label: '[스프린트 시작] 클릭',
        desc: '이슈 배치가 완료되면 [스프린트 시작] 버튼을 눌러 스프린트를 활성화합니다. 이제 보드에서 이슈를 관리할 수 있습니다.',
      },
    ],
    tip: '진행 중인 스프린트는 하나만 유지하는 것을 권장합니다. 스프린트가 끝나면 [스프린트 종료] 버튼으로 마무리하세요.',
  },
  {
    id: 'sc-board',
    shortTitle: '보드로 진행 관리',
    title: '보드에서 진행 상황을 관리하고 싶어요',
    role: '팀원',
    roleColor: 'blue',
    color: 'blue',
    steps: [
      {
        label: '프로젝트 > [보드] 탭 클릭',
        desc: '보드 탭을 클릭하면 현재 진행 중인 스프린트의 이슈가 칸반 형식으로 표시됩니다.',
      },
      {
        label: '칸반 열 구성 확인',
        desc: '이슈는 상태에 따라 열로 분류됩니다. 아래는 보드에 표시되는 열 구성입니다.',
      },
      {
        label: '이슈 카드 클릭 → 상태 변경',
        desc: '이슈 카드를 클릭하면 상세 다이얼로그가 열립니다. 상태 드롭다운에서 현재 단계를 변경하거나 카드를 다른 열로 드래그할 수 있습니다.',
      },
      {
        label: '댓글 · 첨부파일 추가',
        desc: '이슈 상세 다이얼로그의 댓글 탭에서 팀원과 소통하고, 파일을 첨부할 수 있습니다.',
      },
    ],
    tip: '보드는 현재 진행 중인 스프린트의 이슈만 표시됩니다. 백로그 이슈를 보려면 백로그 탭을 이용하세요.',
  },
  {
    id: 'sc-report',
    shortTitle: '주간 보고 작성',
    title: '주간 보고서를 만들고 싶어요',
    role: 'PM',
    roleColor: 'deep-orange',
    color: 'deep-orange',
    steps: [
      {
        label: '스케줄 관리 > 주간 보고 클릭',
        desc: '좌측 메뉴에서 스케줄 관리 → 주간 보고를 클릭하면 보고서 목록이 표시됩니다.',
      },
      {
        label: '[생성 (자동 집계)] 버튼 클릭',
        desc: '버튼을 누르면 연도와 주차를 입력하는 다이얼로그가 열립니다.',
      },
      {
        label: '연도 · 주차 입력 → [생성] 클릭',
        desc: '연도와 주차를 입력하면 보고서 제목과 기간이 자동으로 생성됩니다. [생성]을 누르면 등록된 이슈가 자동으로 집계됩니다.',
      },
      {
        label: '생성된 보고서 클릭 → 4개 탭에서 내용 확인',
        desc: '보고서 상세에서 프로젝트별·개인별·전체 업무·차주 계획 탭으로 내용을 확인합니다.',
      },
      {
        label: '수기 항목 추가 (선택)',
        desc: '주요 안건, 특이사항·리스크, 결정 필요 사항은 직접 입력할 수 있습니다. 확정 상태가 되면 추가할 수 없습니다.',
      },
      {
        label: '상태 변경: 초안 → 검토중 → 확정',
        desc: '검토가 끝나면 순서대로 상태를 변경합니다. 확정 후에는 내용 수정이 제한됩니다.',
      },
      {
        label: '[PDF 출력] 클릭 → 저장',
        desc: '[PDF 출력] 버튼을 누르면 인쇄용 레이아웃 페이지가 새 탭으로 열립니다. 브라우저 인쇄 기능으로 PDF를 저장하세요.',
      },
    ],
    tip: '초안 상태에서 [재집계] 버튼을 누르면 이슈를 최신 데이터로 다시 불러옵니다. 보고 직전에 한 번 눌러주세요.',
  },
]

const issueTypes = [
  { value: 'EPIC',  label: 'Epic',  icon: 'bolt',                    color: 'purple',  desc: '큰 업무 묶음. Story·Task의 상위 단위' },
  { value: 'STORY', label: 'Story', icon: 'menu_book',               color: 'green',   desc: '사용자 관점의 기능 단위' },
  { value: 'TASK',  label: 'Task',  icon: 'check_box_outline_blank',  color: 'primary', desc: '구체적인 작업 단위 (일반 업무)' },
]

const kanbanCols = [
  { label: '할 일', color: 'grey-6', cards: ['로그인 페이지 개선'] },
  { label: '진행중', color: 'primary', cards: ['API 연동', '쿼리 최적화'] },
  { label: '완료', color: 'positive', cards: ['배포 스크립트'] },
  { label: '보류', color: 'warning', cards: ['레거시 제거'] },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.scenario-header {
  border-left: 4px solid var(--q-primary);
  background: #f0f4ff;
}
.mock-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9e9e9e;
}
.mock-screen {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 10px;
  pointer-events: none;
  user-select: none;
}
</style>
