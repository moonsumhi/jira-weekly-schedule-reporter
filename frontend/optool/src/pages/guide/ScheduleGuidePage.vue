<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">스케줄 관리 시스템 사용 가이드</div>
        <div class="text-caption text-grey-6">시나리오로 배우는 조직·프로젝트·이슈·스프린트·주간 보고 흐름</div>
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

            <!-- ═══ 시나리오 0: 새 프로젝트 시작 ═══ -->

            <!-- 0-0: 조직 목록 -->
            <div v-if="si === 0 && idx === 0" class="mock-screen">
              <div class="row q-gutter-sm">
                <q-card flat bordered style="min-width:200px">
                  <q-card-section class="q-pa-sm">
                    <div class="row items-center q-gutter-sm">
                      <q-avatar size="36px" color="primary" text-color="white" style="font-size:14px;font-weight:700">데</q-avatar>
                      <div>
                        <div class="text-body2 text-weight-bold">데이터운영팀</div>
                        <div class="text-caption text-grey-5">data-ops · 프로젝트 3개</div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>
                <q-card flat bordered style="min-width:200px">
                  <q-card-section class="q-pa-sm">
                    <div class="row items-center q-gutter-sm">
                      <q-avatar size="36px" color="teal" text-color="white" style="font-size:14px;font-weight:700">인</q-avatar>
                      <div>
                        <div class="text-body2 text-weight-bold">인프라팀</div>
                        <div class="text-caption text-grey-5">infra · 프로젝트 1개</div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>
              </div>
            </div>

            <!-- 0-1: 조직 생성 폼 -->
            <div v-if="si === 0 && idx === 1" class="mock-screen" style="max-width:380px">
              <div class="mock-section-label q-mb-sm">조직 만들기</div>
              <q-input model-value="데이터운영팀" outlined dense label="조직 이름 *" class="q-mb-sm" />
              <q-input model-value="data-ops" outlined dense label="Slug * (영문 소문자, 숫자, 하이픈)" hint="이름에서 자동 생성됩니다" />
              <div class="row justify-end q-mt-md">
                <q-btn color="primary" label="만들기" no-caps unelevated size="sm" />
              </div>
            </div>

            <!-- 0-2: 프로젝트 생성 폼 -->
            <div v-if="si === 0 && idx === 2" class="mock-screen" style="max-width:420px">
              <div class="mock-section-label q-mb-sm">새 프로젝트</div>
              <q-input model-value="데이터 파이프라인 개선" outlined dense label="프로젝트 이름 *" class="q-mb-sm" />
              <q-input model-value="DATA" outlined dense label="프로젝트 키 * (2~10자, 대문자 영문·숫자)" hint="이슈 키 접두사: DATA-1, DATA-2 …" class="q-mb-sm" />
              <q-input model-value="" outlined dense label="설명" type="textarea" :rows="2" />
            </div>

            <!-- 0-3: 프로젝트 키 예시 -->
            <div v-if="si === 0 && idx === 3" class="mock-screen">
              <div class="row items-center q-gutter-xs q-mb-xs">
                <q-chip dense color="primary" text-color="white" size="sm">DATA-1</q-chip>
                <q-chip dense color="primary" text-color="white" size="sm">DATA-2</q-chip>
                <q-chip dense color="primary" text-color="white" size="sm">DATA-3</q-chip>
              </div>
              <div class="text-caption text-grey-6">키를 "DATA"로 설정했을 때 생성되는 이슈 번호 예시</div>
            </div>

            <!-- 0-4: 프로젝트 멤버 역할 4종 -->
            <div v-if="si === 0 && idx === 4" class="mock-screen">
              <div class="column q-gutter-xs">
                <div class="row items-center q-gutter-sm">
                  <q-badge color="deep-orange" label="ADMIN" style="min-width:140px;text-align:center" />
                  <span class="text-caption text-grey-7">프로젝트 설정, 멤버 관리, 삭제 권한 포함</span>
                </div>
                <div class="row items-center q-gutter-sm">
                  <q-badge color="teal" label="PROJECT_MANAGER" style="min-width:140px;text-align:center" />
                  <span class="text-caption text-grey-7">스프린트 생성·시작·종료, 이슈 전체 관리</span>
                </div>
                <div class="row items-center q-gutter-sm">
                  <q-badge color="primary" label="DEVELOPER" style="min-width:140px;text-align:center" />
                  <span class="text-caption text-grey-7">이슈 생성·편집·상태 변경</span>
                </div>
                <div class="row items-center q-gutter-sm">
                  <q-badge color="grey-6" label="VIEWER" style="min-width:140px;text-align:center" />
                  <span class="text-caption text-grey-7">읽기 전용 (생성·편집 불가)</span>
                </div>
              </div>
            </div>

            <!-- 0-5: 라벨 관리 -->
            <div v-if="si === 0 && idx === 5" class="mock-screen">
              <div class="mock-section-label q-mb-sm">프로젝트 라벨 관리</div>
              <div class="row q-gutter-xs q-mb-xs">
                <q-chip dense color="blue" text-color="white" size="sm">프론트엔드</q-chip>
                <q-chip dense color="green" text-color="white" size="sm">백엔드</q-chip>
                <q-chip dense color="orange" text-color="white" size="sm">DB</q-chip>
                <q-chip dense color="purple" text-color="white" size="sm">인프라</q-chip>
              </div>
              <div class="text-caption text-grey-6">라벨은 이슈에 지정해 분류·필터링에 활용합니다</div>
            </div>

            <!-- ═══ 시나리오 1: 이슈 생성·배정 ═══ -->

            <!-- 1-1: 이슈 생성 버튼 -->
            <div v-if="si === 1 && idx === 1" class="mock-screen">
              <q-btn color="primary" icon="add" label="이슈 생성" no-caps unelevated size="sm" />
              <div class="text-caption text-grey-6 q-mt-xs">보드, 백로그, 프로젝트 개요 화면 어디서든 클릭할 수 있습니다</div>
            </div>

            <!-- 1-2: 이슈 타입 5종 -->
            <div v-if="si === 1 && idx === 2" class="mock-screen">
              <div class="row q-gutter-sm" style="flex-wrap:wrap">
                <div v-for="t in issueTypes" :key="t.value" style="min-width:130px;flex:1">
                  <q-card flat bordered class="q-pa-sm">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <q-icon :name="t.icon" :color="t.color" size="16px" />
                      <span class="text-caption text-weight-bold">{{ t.label }}</span>
                    </div>
                    <div class="text-caption text-grey-6">{{ t.desc }}</div>
                  </q-card>
                </div>
              </div>
              <div class="text-caption text-grey-6 q-mt-sm">Sub-task는 이슈 생성 폼이 아닌 이슈 상세 다이얼로그의 하위 작업 섹션에서 추가합니다.</div>
            </div>

            <!-- 1-3: 기본 정보 폼 -->
            <div v-if="si === 1 && idx === 3" class="mock-screen" style="max-width:520px">
              <div class="mock-section-label q-mb-sm">기본 정보</div>
              <q-input model-value="사용자 권한 관리 API 개발" outlined dense label="제목 *" class="q-mb-sm" />
              <div class="row q-gutter-sm">
                <q-input model-value="Task" outlined dense label="타입" class="col" readonly>
                  <template #prepend><q-icon name="check_box_outline_blank" color="primary" size="16px" /></template>
                </q-input>
                <q-input model-value="보통" outlined dense label="우선순위" class="col" readonly>
                  <template #prepend><q-icon name="flag" color="orange" size="16px" /></template>
                </q-input>
                <q-input model-value="백로그" outlined dense label="상태" class="col" readonly />
              </div>
            </div>

            <!-- 1-4: 담당·일정 폼 -->
            <div v-if="si === 1 && idx === 4" class="mock-screen" style="max-width:520px">
              <div class="mock-section-label q-mb-sm">담당</div>
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="홍길동" outlined dense label="담당자" class="col" readonly>
                  <template #prepend><q-icon name="person" color="grey-6" size="16px" /></template>
                </q-input>
                <q-input model-value="김관리 (자동)" outlined dense label="보고자" class="col" readonly>
                  <template #prepend><q-icon name="person_outline" color="grey-6" size="16px" /></template>
                </q-input>
              </div>
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="DATA-1 사용자 관리 Epic" outlined dense label="상위 Epic" class="col" readonly>
                  <template #prepend><q-icon name="bolt" color="purple" size="16px" /></template>
                </q-input>
                <q-input model-value="3" outlined dense label="스토리 포인트" class="col" readonly>
                  <template #prepend><q-icon name="speed" color="grey-6" size="16px" /></template>
                </q-input>
              </div>
              <div class="mock-section-label q-mb-sm q-mt-sm">일정</div>
              <div class="row q-gutter-sm">
                <q-input model-value="스프린트 1" outlined dense label="스프린트" class="col" readonly>
                  <template #prepend><q-icon name="loop" color="grey-6" size="16px" /></template>
                </q-input>
                <q-input model-value="2026-07-14" outlined dense label="시작일" stack-label class="col" readonly />
                <q-input model-value="2026-07-25" outlined dense label="마감일" stack-label class="col" readonly />
              </div>
            </div>

            <!-- 1-5: 라벨·설명·첨부 -->
            <div v-if="si === 1 && idx === 5" class="mock-screen" style="max-width:440px">
              <div class="mock-section-label q-mb-sm">기타</div>
              <div class="row q-gutter-xs q-mb-sm">
                <q-chip dense color="blue" text-color="white" size="sm" removable>백엔드</q-chip>
                <q-chip dense color="green" text-color="white" size="sm" removable>DB</q-chip>
                <q-btn flat dense icon="add" size="xs" color="grey-5" label="라벨" no-caps />
              </div>
              <q-input model-value="사용자 CRUD API 및 권한 체계 설계. Swagger 문서 포함." outlined dense label="설명" type="textarea" :rows="2" class="q-mb-sm" />
              <div style="border:1.5px dashed #ccc;border-radius:6px;padding:10px;text-align:center">
                <q-icon name="cloud_upload" size="20px" color="grey-5" />
                <div class="text-caption text-grey-5 q-mt-xs">파일 드래그 앤 드롭 또는 클릭하여 첨부 (최대 20MB)</div>
              </div>
            </div>

            <!-- ═══ 시나리오 2: 이슈 상세 관리 ═══ -->

            <!-- 2-0: 이슈 상세 헤더 -->
            <div v-if="si === 2 && idx === 0" class="mock-screen" style="max-width:560px">
              <div class="row items-center q-gutter-xs q-mb-sm">
                <q-icon name="check_box_outline_blank" color="primary" size="16px" />
                <span class="text-caption text-grey-5">DATA-12</span>
                <q-badge color="primary" label="진행 중" />
                <q-space />
                <q-btn flat dense icon="open_in_new" size="xs" color="teal" label="연결된 SR" no-caps />
                <q-btn flat round dense icon="close" size="sm" />
              </div>
              <div class="text-subtitle2 text-weight-bold q-mb-sm">사용자 권한 관리 API 개발</div>
              <q-separator />
              <div class="row q-gutter-sm q-mt-xs">
                <q-btn flat dense size="sm" no-caps label="상세" color="primary" icon="description" />
                <q-btn flat dense size="sm" no-caps label="변경 이력" color="grey-6" icon="history" />
              </div>
            </div>

            <!-- 2-1: 인라인 편집 -->
            <div v-if="si === 2 && idx === 1" class="mock-screen" style="max-width:480px">
              <div class="text-caption text-grey-5 q-mb-xs">제목을 클릭하면 편집 모드로 전환됩니다</div>
              <div style="border:2px solid #1976d2;border-radius:4px;padding:6px 10px;font-size:14px;font-weight:600;background:white">
                사용자 권한 관리 API 개발
              </div>
              <div class="text-caption text-grey-5 q-mt-xs">제목: Enter 또는 다른 곳 클릭(blur) 시 자동 저장 · 설명: 마크다운 에디터에서 [저장] 버튼 클릭</div>
            </div>

            <!-- 2-2: 사이드바 속성 -->
            <div v-if="si === 2 && idx === 2" class="mock-screen" style="max-width:260px">
              <div class="mock-section-label q-mb-xs">속성 (우측 사이드바)</div>
              <div class="column q-gutter-xs">
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">상태</span>
                  <q-badge color="primary" label="진행 중" />
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">타입</span>
                  <div class="row items-center q-gutter-xs">
                    <q-icon name="check_box_outline_blank" color="primary" size="14px" />
                    <span class="text-caption">Task</span>
                  </div>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">우선순위</span>
                  <div class="row items-center q-gutter-xs">
                    <q-icon name="flag" color="orange" size="14px" />
                    <span class="text-caption">보통</span>
                  </div>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">담당자</span>
                  <span class="text-caption">홍길동</span>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">스프린트</span>
                  <span class="text-caption">스프린트 1</span>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">마감일</span>
                  <span class="text-caption text-warning text-weight-bold">2026-07-25 D-11</span>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">스토리 포인트</span>
                  <span class="text-caption">3</span>
                </div>
                <div class="row items-center justify-between">
                  <span class="text-caption text-grey-5" style="min-width:80px">라벨</span>
                  <q-chip dense color="blue" text-color="white" size="xs">백엔드</q-chip>
                </div>
              </div>
            </div>

            <!-- 2-3: 하위 작업 -->
            <div v-if="si === 2 && idx === 3" class="mock-screen" style="max-width:420px">
              <div class="mock-section-label q-mb-xs">하위 작업</div>
              <div class="column q-gutter-xs q-mb-sm">
                <div class="row items-center q-gutter-sm bg-grey-1 q-pa-xs rounded-borders">
                  <q-icon name="check_circle" color="positive" size="16px" />
                  <span class="text-body2" style="text-decoration:line-through;color:#9e9e9e">DB 스키마 설계</span>
                </div>
                <div class="row items-center q-gutter-sm bg-grey-1 q-pa-xs rounded-borders">
                  <q-icon name="radio_button_unchecked" color="grey-4" size="16px" />
                  <span class="text-body2">API 엔드포인트 구현</span>
                </div>
                <div class="row items-center q-gutter-sm bg-grey-1 q-pa-xs rounded-borders">
                  <q-icon name="radio_button_unchecked" color="grey-4" size="16px" />
                  <span class="text-body2">Swagger 문서 작성</span>
                </div>
              </div>
              <q-input model-value="" outlined dense label="+ 하위 작업 인라인 추가…" />
              <div class="text-caption text-grey-5 q-mt-xs">드래그로 순서 변경 가능 · Epic·Sub-task에는 이 섹션이 없습니다</div>
            </div>

            <!-- 2-4: 댓글 -->
            <div v-if="si === 2 && idx === 4" class="mock-screen" style="max-width:480px">
              <div class="mock-section-label q-mb-xs">댓글</div>
              <q-card flat bordered class="q-pa-sm q-mb-xs">
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <q-avatar size="20px" color="primary" text-color="white" style="font-size:10px">홍</q-avatar>
                  <span class="text-caption text-weight-bold">홍길동</span>
                  <span class="text-caption text-grey-5">2026-07-14 10:32</span>
                </div>
                <div class="text-body2 q-mb-xs">DB 스키마 완성했습니다. API 구현 시작할게요.</div>
                <div class="row q-gutter-xs">
                  <q-btn flat dense size="xs" no-caps label="답글" color="grey-6" icon="reply" />
                  <q-btn flat dense size="xs" no-caps label="파일 첨부" color="grey-6" icon="attach_file" />
                </div>
              </q-card>
              <div class="text-caption text-grey-5">Ctrl+V로 클립보드 이미지 바로 붙여넣기 지원</div>
            </div>

            <!-- 2-5: 변경 이력 탭 -->
            <div v-if="si === 2 && idx === 5" class="mock-screen" style="max-width:480px">
              <div class="mock-section-label q-mb-xs">변경 이력 탭</div>
              <div class="column q-gutter-xs">
                <div class="row items-start q-gutter-sm">
                  <q-avatar size="20px" color="primary" text-color="white" style="font-size:10px">홍</q-avatar>
                  <div>
                    <span class="text-caption text-weight-medium">홍길동</span>
                    <span class="text-caption text-grey-5"> · 상태 변경 </span>
                    <q-badge color="grey-5" label="할 일" size="xs" />
                    <q-icon name="arrow_forward" size="12px" color="grey-5" class="q-mx-xs" />
                    <q-badge color="primary" label="진행 중" size="xs" />
                    <div class="text-caption text-grey-5">2026-07-14 09:00</div>
                  </div>
                </div>
                <div class="row items-start q-gutter-sm">
                  <q-avatar size="20px" color="orange" text-color="white" style="font-size:10px">김</q-avatar>
                  <div>
                    <span class="text-caption text-weight-medium">김관리</span>
                    <span class="text-caption text-grey-5"> · 담당자 배정 → 홍길동</span>
                    <div class="text-caption text-grey-5">2026-07-13 17:30</div>
                  </div>
                </div>
                <div class="row items-start q-gutter-sm">
                  <q-avatar size="20px" color="teal" text-color="white" style="font-size:10px">홍</q-avatar>
                  <div>
                    <span class="text-caption text-weight-medium">홍길동</span>
                    <span class="text-caption text-grey-5"> · 댓글 등록</span>
                    <div class="text-caption text-grey-5">2026-07-14 10:32</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ═══ 시나리오 3: 백로그 관리 ═══ -->

            <!-- 3-1: 트리 구조 목업 -->
            <div v-if="si === 3 && idx === 1" class="mock-screen" style="max-width:540px;font-size:12px">
              <div class="row items-center q-gutter-xs q-py-xs q-px-sm q-mb-xs" style="background:rgba(103,58,183,0.08);border-radius:4px">
                <q-icon name="chevron_right" color="grey-5" size="14px" />
                <q-icon name="bolt" color="purple" size="14px" />
                <span class="text-weight-bold" style="color:#673ab7">DATA-1</span>
                <span style="color:#673ab7"> 사용자 관리 Epic</span>
                <q-badge color="purple" label="Epic" size="xs" class="q-ml-xs" />
              </div>
              <div class="q-pl-lg">
                <div class="row items-center q-gutter-xs q-py-xs">
                  <q-icon name="expand_more" color="grey-5" size="14px" />
                  <q-icon name="menu_book" color="green" size="14px" />
                  <span>DATA-5 로그인 기능 구현</span>
                  <q-badge color="primary" label="진행 중" size="xs" />
                </div>
                <div class="q-pl-lg">
                  <div class="row items-center q-gutter-xs q-py-xs text-grey-6">
                    <q-icon name="subdirectory_arrow_right" color="grey-4" size="14px" />
                    <q-icon name="subdirectory_arrow_right" color="grey-4" size="12px" />
                    <span>DATA-6 OAuth 연동</span>
                    <q-badge color="grey-5" label="할 일" size="xs" />
                  </div>
                </div>
                <div class="row items-center q-gutter-xs q-py-xs">
                  <q-icon name="chevron_right" color="grey-5" size="14px" />
                  <q-icon name="check_box_outline_blank" color="primary" size="14px" />
                  <span>DATA-12 권한 관리 API</span>
                  <q-badge color="primary" label="진행 중" size="xs" />
                </div>
              </div>
              <q-separator class="q-my-xs" />
              <div class="text-caption text-grey-5 q-pl-xs q-mb-xs" style="font-style:italic">에픽 없음</div>
              <div class="q-pl-md">
                <div class="row items-center q-gutter-xs q-py-xs">
                  <q-icon name="chevron_right" color="grey-5" size="14px" />
                  <q-icon name="check_box_outline_blank" color="primary" size="14px" />
                  <span>DATA-15 서버 모니터링 대시보드 개선</span>
                  <q-badge color="grey-4" label="백로그" size="xs" />
                </div>
              </div>
            </div>

            <!-- 3-2: 필터 바 -->
            <div v-if="si === 3 && idx === 2" class="mock-screen" style="max-width:560px">
              <div class="row q-gutter-sm items-center" style="flex-wrap:wrap">
                <q-input model-value="권한" outlined dense label="제목 검색" style="min-width:120px" readonly>
                  <template #prepend><q-icon name="search" size="16px" /></template>
                </q-input>
                <q-input model-value="진행 중" outlined dense label="상태" style="min-width:90px" readonly />
                <q-input model-value="보통" outlined dense label="우선순위" style="min-width:90px" readonly />
                <q-input model-value="Task" outlined dense label="유형" style="min-width:90px" readonly />
                <q-input model-value="홍길동" outlined dense label="담당자" style="min-width:90px" readonly />
                <q-btn flat dense icon="clear" size="sm" label="초기화" color="grey-6" no-caps />
              </div>
            </div>

            <!-- 3-3: 펼치기/접기 버튼 -->
            <div v-if="si === 3 && idx === 3" class="mock-screen">
              <div class="row q-gutter-sm items-center">
                <q-btn flat dense no-caps size="sm" icon="unfold_more" label="모두 펼치기" color="grey-7" />
                <q-btn flat dense no-caps size="sm" icon="unfold_less" label="모두 접기" color="grey-7" />
                <q-badge color="grey-5" label="전체 15건" />
              </div>
            </div>

            <!-- ═══ 시나리오 4: 스프린트 계획 ═══ -->

            <!-- 4-1: 스프린트 생성 폼 -->
            <div v-if="si === 4 && idx === 1" class="mock-screen" style="max-width:400px">
              <div class="mock-section-label q-mb-sm">스프린트 만들기</div>
              <q-input model-value="스프린트 3" outlined dense label="이름 *" class="q-mb-sm" />
              <q-input model-value="사용자 관리 API 완성 및 배포 준비" outlined dense label="목표" type="textarea" :rows="2" class="q-mb-sm" />
              <div class="row q-gutter-sm">
                <q-input model-value="2026-07-14" outlined dense label="시작일" stack-label class="col" readonly />
                <q-input model-value="2026-07-27" outlined dense label="종료일" stack-label class="col" readonly />
              </div>
            </div>

            <!-- 4-2: 스프린트 상태 흐름 -->
            <div v-if="si === 4 && idx === 2" class="mock-screen">
              <div class="row items-center q-gutter-sm" style="flex-wrap:wrap">
                <q-card flat bordered class="q-pa-sm text-center">
                  <q-badge color="grey-6" label="예정 (PLANNED)" />
                  <div class="text-caption text-grey-5 q-mt-xs">생성 직후</div>
                </q-card>
                <q-icon name="arrow_forward" color="grey-5" />
                <q-card flat bordered class="q-pa-sm text-center">
                  <q-badge color="positive" label="진행 중 (ACTIVE)" />
                  <div class="text-caption text-grey-5 q-mt-xs">[스프린트 시작] 클릭</div>
                </q-card>
                <q-icon name="arrow_forward" color="grey-5" />
                <q-card flat bordered class="q-pa-sm text-center">
                  <q-badge color="blue" label="완료 (COMPLETED)" />
                  <div class="text-caption text-grey-5 q-mt-xs">[스프린트 종료] 클릭</div>
                </q-card>
              </div>
            </div>

            <!-- 4-4: 시작/종료 버튼 -->
            <div v-if="si === 4 && idx === 4" class="mock-screen">
              <div class="row q-gutter-sm items-center q-mb-xs">
                <q-btn color="positive" icon="play_arrow" label="스프린트 시작" no-caps unelevated size="sm" />
                <span class="text-caption text-grey-5">→ ACTIVE 전환, 보드에서 관리 시작</span>
              </div>
              <div class="row q-gutter-sm items-center">
                <q-btn color="blue" icon="stop" label="스프린트 종료" no-caps unelevated size="sm" />
                <span class="text-caption text-grey-5">→ 미완료 이슈는 자동으로 백로그로 이동</span>
              </div>
            </div>

            <!-- ═══ 시나리오 5: 보드 진행 관리 ═══ -->

            <!-- 5-1: 칸반 5열 -->
            <div v-if="si === 5 && idx === 1" class="mock-screen" style="overflow-x:auto">
              <div style="display:flex;gap:8px;min-width:580px">
                <div v-for="col in kanbanCols" :key="col.label" style="width:108px;flex-shrink:0">
                  <q-badge :color="col.color" :label="col.label" class="q-mb-sm full-width" style="display:block;text-align:center" />
                  <q-card v-for="card in col.cards" :key="card" flat bordered class="q-pa-xs q-mb-xs">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <q-icon name="check_box_outline_blank" color="primary" size="12px" />
                      <span class="text-caption text-grey-5">DATA-5</span>
                    </div>
                    <div class="text-caption" style="line-height:1.3;font-size:11px">{{ card }}</div>
                    <q-avatar size="16px" color="primary" text-color="white" style="font-size:9px;margin-top:4px">홍</q-avatar>
                  </q-card>
                </div>
              </div>
            </div>

            <!-- 5-2: 드래그 확인 다이얼로그 -->
            <div v-if="si === 5 && idx === 2" class="mock-screen" style="max-width:360px">
              <q-card flat bordered class="q-pa-sm">
                <div class="text-subtitle2 text-weight-bold q-mb-xs">상태 변경 확인</div>
                <div class="text-body2 text-grey-7 q-mb-sm">
                  <strong>로그인 기능 구현</strong>의 상태를<br>
                  <q-badge color="primary" label="진행 중" />
                  <q-icon name="arrow_forward" size="14px" color="grey-5" class="q-mx-xs" />
                  <q-badge color="orange" label="검토 중" />
                  (으)로 변경하시겠습니까?
                </div>
                <div class="row q-gutter-sm justify-end">
                  <q-btn flat label="취소" size="sm" no-caps />
                  <q-btn color="primary" label="확인" size="sm" no-caps />
                </div>
              </q-card>
            </div>

            <!-- 5-3: 스프린트 필터 -->
            <div v-if="si === 5 && idx === 3" class="mock-screen">
              <div class="row items-center q-gutter-sm">
                <q-input model-value="스프린트 1" outlined dense label="스프린트 선택" style="max-width:200px" readonly>
                  <template #append><q-icon name="arrow_drop_down" /></template>
                </q-input>
                <span class="text-caption text-grey-5">"전체" 선택 시 스프린트에 관계없이 모든 이슈 표시</span>
              </div>
            </div>

            <!-- 5-4: 상태 칩 열 on/off -->
            <div v-if="si === 5 && idx === 4" class="mock-screen">
              <div class="row q-gutter-xs q-mb-xs">
                <q-chip dense clickable color="grey-4" text-color="white" size="sm">백로그</q-chip>
                <q-chip dense clickable color="blue-grey" text-color="white" size="sm">할 일</q-chip>
                <q-chip dense clickable color="primary" text-color="white" size="sm">진행 중</q-chip>
                <q-chip dense clickable outline color="orange" size="sm" style="opacity:0.5">검토 중 (숨김)</q-chip>
                <q-chip dense clickable color="positive" text-color="white" size="sm">완료</q-chip>
              </div>
              <div class="text-caption text-grey-5">칩 클릭으로 해당 열 표시/숨김 전환 · 흐린 칩 = 현재 숨김 상태</div>
            </div>

            <!-- ═══ 시나리오 6: 주간 보고 작성 ═══ -->

            <!-- 6-1: 생성 다이얼로그 -->
            <div v-if="si === 6 && idx === 1" class="mock-screen" style="max-width:420px">
              <div class="mock-section-label q-mb-sm">주간 보고 생성</div>
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="2026" outlined dense label="연도 *" type="number" class="col" readonly />
                <q-input model-value="29" outlined dense label="주차 *" type="number" class="col" readonly />
              </div>
              <div class="text-caption text-grey-6 q-mb-sm">기간: 2026-07-13 ~ 2026-07-19 (자동 계산)</div>
              <q-input model-value="2026년 29주차 주간 보고" outlined dense label="제목 *" class="q-mb-sm" />
              <q-input model-value="데이터운영팀" outlined dense label="부서" class="q-mb-md" />
              <div class="row justify-end">
                <q-btn color="primary" icon="auto_awesome" label="생성 (자동 집계)" no-caps unelevated size="sm" />
              </div>
            </div>

            <!-- 6-2: 통계 카드 -->
            <div v-if="si === 6 && idx === 2" class="mock-screen">
              <div class="row q-gutter-sm">
                <q-card flat bordered class="text-center q-pa-sm" style="min-width:72px">
                  <div class="text-h6 text-weight-bold text-grey-8">24</div>
                  <div class="text-caption text-grey-6">총 업무</div>
                </q-card>
                <q-card flat bordered class="text-center q-pa-sm" style="min-width:72px">
                  <div class="text-h6 text-weight-bold text-positive">18</div>
                  <div class="text-caption text-grey-6">완료</div>
                </q-card>
                <q-card flat bordered class="text-center q-pa-sm" style="min-width:72px">
                  <div class="text-h6 text-weight-bold text-primary">4</div>
                  <div class="text-caption text-grey-6">진행 중</div>
                </q-card>
                <q-card flat bordered class="text-center q-pa-sm" style="min-width:72px">
                  <div class="text-h6 text-weight-bold text-negative">2</div>
                  <div class="text-caption text-grey-6">지연</div>
                </q-card>
                <q-card flat bordered class="text-center q-pa-sm" style="min-width:72px">
                  <div class="text-h6 text-weight-bold text-teal">75%</div>
                  <div class="text-caption text-grey-6">완료율</div>
                </q-card>
              </div>
            </div>

            <!-- 6-3: 4개 탭 -->
            <div v-if="si === 6 && idx === 3" class="mock-screen">
              <q-tabs model-value="project" dense align="left" active-color="primary">
                <q-tab name="project"  label="프로젝트별" />
                <q-tab name="person"   label="개인별" />
                <q-tab name="all"      label="전체 업무" />
                <q-tab name="upcoming" label="차주 계획" />
              </q-tabs>
              <q-separator />
              <div class="text-caption text-grey-6 q-mt-xs q-pa-xs">
                프로젝트별·개인별 탭은 완료 ✅ / 진행 중 🔄 / 지연 ⚠ / 차주 계획 📌 순으로 접이식 목록 표시
              </div>
            </div>

            <!-- 6-4: 수기 항목 3섹션 -->
            <div v-if="si === 6 && idx === 4" class="mock-screen" style="max-width:500px">
              <div class="column q-gutter-sm">
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="task_alt" color="blue" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">주요 안건</span>
                    <q-badge color="blue" label="2" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="blue" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">카테고리, 상태(예정/진행중/완료 등), 제목, 내용, 담당자 입력</div>
                </q-card>
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="warning_amber" color="orange" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">특이사항 및 리스크</span>
                    <q-badge color="orange" label="1" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="orange" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">유형, 영향도(높음/보통/낮음), 내용, 대응 방안 입력</div>
                </q-card>
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="gavel" color="purple" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">결정 필요 사항</span>
                    <q-badge color="purple" label="0" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="purple" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">배경, 선택지, 요청 내용, 희망 결정일 입력</div>
                </q-card>
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="hub" color="cyan" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">네트워크</span>
                    <q-badge color="cyan" label="1" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="cyan" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">네트워크 관련 작업·이슈 내용 입력 (마크다운 에디터)</div>
                </q-card>
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="campaign" color="teal" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">공지사항</span>
                    <q-badge color="teal" label="1" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="teal" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">팀 공지·전달 사항 입력</div>
                </q-card>
                <q-card flat bordered class="q-pa-sm">
                  <div class="row items-center q-mb-xs">
                    <q-icon name="event_available" color="indigo" size="16px" class="q-mr-xs" />
                    <span class="text-caption text-weight-bold">복무 현황</span>
                    <q-badge color="indigo" label="2" class="q-ml-sm" />
                    <q-space />
                    <q-btn flat dense icon="add" label="추가" size="xs" color="indigo" no-caps />
                  </div>
                  <div class="text-caption text-grey-6">휴가·출장 등 복무 정보 입력 · 테이블 형태로 표시</div>
                </q-card>
              </div>
            </div>

            <!-- 6-5: 포함/제외 토글 -->
            <div v-if="si === 6 && idx === 5" class="mock-screen" style="max-width:420px">
              <div class="column q-gutter-xs">
                <div class="row items-center q-gutter-sm q-pa-xs" style="background:#f5f5f5;border-radius:4px">
                  <q-icon name="check_circle" color="positive" size="16px" />
                  <span class="text-body2">서버 증설 검토 안건</span>
                  <q-badge color="blue-2" text-color="blue-9" label="일정" size="xs" />
                  <span class="text-caption text-grey-5 q-ml-auto">보고서 포함</span>
                </div>
                <div class="row items-center q-gutter-sm q-pa-xs" style="border-radius:4px;opacity:0.4">
                  <q-icon name="radio_button_unchecked" color="grey-4" size="16px" />
                  <span class="text-body2">내부 팀 회의록</span>
                  <span class="text-caption text-grey-5 q-ml-auto">보고서 제외</span>
                </div>
              </div>
              <div class="text-caption text-grey-5 q-mt-xs">아이콘 클릭으로 포함/제외 전환 · 흐릿한 항목은 PDF·미리보기에서 숨겨집니다</div>
            </div>

            <!-- 6-6: 상태 변경 흐름 -->
            <div v-if="si === 6 && idx === 6" class="mock-screen">
              <div class="row items-center q-gutter-sm" style="flex-wrap:wrap">
                <div class="column items-center">
                  <q-badge color="grey-6" label="초안 (DRAFT)" />
                  <q-btn flat dense size="xs" no-caps label="[검토 완료]" color="orange" class="q-mt-xs" />
                </div>
                <q-icon name="arrow_forward" color="grey-5" />
                <div class="column items-center">
                  <q-badge color="orange" label="검토중 (REVIEWING)" />
                  <q-btn flat dense size="xs" no-caps label="[보고 확정]" color="positive" class="q-mt-xs" />
                </div>
                <q-icon name="arrow_forward" color="grey-5" />
                <div class="column items-center">
                  <q-badge color="positive" label="확정 (CONFIRMED)" />
                  <q-btn flat dense size="xs" no-caps label="[확정 해제]" color="grey-7" class="q-mt-xs" />
                </div>
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">확정 상태에서는 수기 항목 추가·삭제가 잠깁니다 · [확정 해제]로 검토중으로 되돌릴 수 있습니다</div>
            </div>

            <!-- 6-7: 재집계·미리보기·PDF·Excel 버튼 -->
            <div v-if="si === 6 && idx === 7" class="mock-screen">
              <div class="row q-gutter-sm q-mb-xs">
                <q-btn flat icon="refresh" label="재집계" color="teal" no-caps size="sm" />
                <q-btn flat icon="preview" label="미리보기" color="primary" no-caps size="sm" />
                <q-btn flat icon="picture_as_pdf" label="PDF 출력" color="deep-orange" no-caps size="sm" />
                <q-btn flat icon="download" label="Excel" color="positive" no-caps size="sm" />
              </div>
              <div class="text-caption text-grey-6">[재집계]는 초안 상태에서만 활성화 · [목록 Excel]은 주간 보고 목록 화면에서도 제공</div>
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

    <!-- ───────────────── 내 이슈 & 업무 현황 ───────────────── -->
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

        <!-- 내 이슈 (대시보드) -->
        <div class="col-12 col-sm-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="row items-center q-mb-sm">
                <q-icon name="assignment" color="primary" class="q-mr-sm" size="20px" />
                <span class="text-subtitle2 text-weight-bold">내 이슈 (대시보드)</span>
              </div>
              <div class="text-body2 text-grey-7 q-mb-sm">
                스케줄 관리 → 내 이슈에서 나와 관련된 이슈를 한눈에 봅니다.
                제목 또는 이슈 키(예: DATA-12)로 검색하고,
                <strong>담당 중 / 내가 만든 / 프로젝트 현황</strong> 3개 접이식 섹션으로 구분됩니다.
              </div>
              <div class="column q-gutter-xs q-mb-sm" style="pointer-events:none">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="check_box_outline_blank" color="primary" size="14px" />
                  <span class="text-caption text-grey-5" style="min-width:70px">DATA-12</span>
                  <span class="text-caption col ellipsis">사용자 권한 관리 API 개발</span>
                  <q-badge color="primary" label="진행 중" size="xs" />
                  <span class="text-caption text-warning text-weight-bold">D-11</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon name="menu_book" color="green" size="14px" />
                  <span class="text-caption text-grey-5" style="min-width:70px">DATA-5</span>
                  <span class="text-caption col ellipsis">로그인 기능 구현</span>
                  <q-badge color="positive" label="완료" size="xs" />
                  <span class="text-caption text-negative text-weight-bold">D+2</span>
                </div>
              </div>
              <div class="text-caption text-grey-6">D+N = 마감 초과(빨강) · D-Day = 당일(노랑) · D-N = 여유(회색)</div>
            </q-card-section>
          </q-card>
        </div>

        <!-- 업무 현황 (캘린더) -->
        <div class="col-12 col-sm-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="row items-center q-mb-sm">
                <q-icon name="calendar_month" color="teal" class="q-mr-sm" size="20px" />
                <span class="text-subtitle2 text-weight-bold">업무 현황 (캘린더)</span>
              </div>
              <div class="text-body2 text-grey-7 q-mb-sm">
                스케줄 관리 → 업무 현황에서 팀 전체의 Task·Sub-task 일정을 월/주 캘린더로 확인합니다.
                각 이벤트는 담당자별 고유 색상으로 표시됩니다.
              </div>
              <div class="column q-gutter-xs q-mb-sm" style="pointer-events:none">
                <div class="row items-center q-gutter-xs">
                  <span class="text-caption text-grey-5">담당자 필터:</span>
                  <q-chip dense clickable color="primary" text-color="white" size="sm">홍길동</q-chip>
                  <q-chip dense clickable outline color="teal" size="sm">김영희</q-chip>
                  <q-chip dense clickable outline color="purple" size="sm">이철수</q-chip>
                </div>
                <div class="text-caption text-grey-5">복수 선택 가능 · [전체] 칩으로 전체 보기 전환</div>
                <div class="text-caption text-grey-5">이벤트 클릭 → 이슈 상세 편집 다이얼로그가 열려 상태·담당자·마감일을 바로 수정 가능</div>
                <div class="text-caption text-grey-5">우상단에서 월(Month) / 주(Week) 보기 전환 가능</div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- 마감일 색상 가이드 -->
        <div class="col-12">
          <q-card flat bordered>
            <q-card-section class="q-py-sm">
              <div class="text-subtitle2 text-weight-bold q-mb-sm">마감일 표시 기준</div>
              <div class="row q-gutter-md" style="pointer-events:none">
                <div class="row items-center q-gutter-xs">
                  <span class="text-caption text-negative text-weight-bold">D+3</span>
                  <span class="text-caption text-grey-6">마감 3일 초과 (빨강)</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <span class="text-caption text-warning text-weight-bold">D-Day</span>
                  <span class="text-caption text-grey-6">오늘이 마감일 (노랑)</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <span class="text-caption text-grey-6 text-weight-bold">D-12</span>
                  <span class="text-caption text-grey-6">아직 12일 여유 (회색)</span>
                </div>
              </div>
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
        desc: '좌측 메뉴에서 스케줄 관리 → 조직을 클릭합니다. 현재 등록된 조직이 카드 형태(이름 첫 글자 아바타, 이름, Slug, 소속 프로젝트 수)로 표시됩니다. 조직이 없으면 빈 목록이 나타납니다.',
      },
      {
        label: '[조직 만들기] 클릭 → 이름·Slug 입력',
        desc: '우측 상단의 [조직 만들기] 버튼을 눌러 조직 이름(필수)을 입력합니다. Slug는 이름을 기반으로 자동 생성되며 영문 소문자·숫자·하이픈만 사용 가능합니다. 조직 관리자(ADMIN)만 삭제 권한을 가집니다.',
      },
      {
        label: '조직 카드 클릭 → [프로젝트 추가]',
        desc: '생성된 조직 카드를 클릭하면 조직 상세 페이지가 열립니다. 상단의 [프로젝트 추가] 버튼으로 새 프로젝트를 만듭니다. 프로젝트 이름(필수), 키(필수), 설명(선택)을 입력하고 저장합니다. 프로젝트 목록에는 내가 멤버로 등록된 프로젝트만 표시됩니다.',
      },
      {
        label: '프로젝트 키 — 신중하게 설정',
        desc: '프로젝트 키는 이슈 번호의 접두사가 됩니다 (키 DATA → 이슈 DATA-1, DATA-2…). 영문 대문자 2~10자로 구성되며 저장 후에는 변경이 불가능합니다. 팀과 합의 후 간결하게 설정하세요 (예: OPS, INFRA, DATA).',
      },
      {
        label: '멤버 탭 → [멤버 추가] → 역할 지정',
        desc: '프로젝트 상세의 [멤버] 탭에서 팀원을 추가하고 역할을 지정합니다. 역할은 ADMIN(전체 권한), PROJECT_MANAGER(스프린트·이슈 관리), DEVELOPER(이슈 생성·편집), VIEWER(읽기 전용) 4종입니다. 역할은 이후 변경 가능합니다.',
      },
      {
        label: '[설정] 탭 → 라벨 관리 · 프로젝트 삭제',
        desc: '프로젝트 상세의 [설정] 탭에서 이슈 분류용 라벨(이름+색상)을 추가합니다. 생성한 라벨은 이슈 생성·편집 시 선택할 수 있습니다. 하단 위험 영역에서 프로젝트 삭제도 가능합니다 (ADMIN만 가능).',
      },
    ],
    tip: '프로젝트 키는 한 번 설정하면 바꿀 수 없습니다. 영문 대문자로 짧고 직관적으로 설정하세요 (예: OPS, DATA, FE).',
  },
  {
    id: 'sc-issue',
    shortTitle: '이슈 생성·배정',
    title: '이슈를 만들고 팀원에게 배정하고 싶어요',
    role: '팀원 · PM',
    roleColor: 'primary',
    color: 'primary',
    steps: [
      {
        label: '보드 또는 백로그 탭 진입',
        desc: '프로젝트 상세 화면에서 [보드] 또는 [백로그] 탭을 클릭합니다. 또는 프로젝트 개요 화면의 바로가기 버튼(보드/백로그/스프린트)으로 이동할 수 있습니다.',
      },
      {
        label: '[이슈 생성] 버튼 클릭',
        desc: '화면 우측 상단의 [이슈 생성] 버튼을 클릭하면 생성 다이얼로그가 열립니다. 다이얼로그는 기본 정보, 담당, 일정, 기타 4개 섹션으로 구성됩니다.',
      },
      {
        label: '이슈 타입 선택 — Epic · Story · Task',
        desc: 'Epic은 큰 업무 묶음(상위 단위), Story는 사용자 관점의 기능 단위, Task는 구체적 작업 단위입니다. 일반 업무는 Task로 시작하세요. Sub-task는 생성 폼이 아닌 이슈 상세 다이얼로그의 하위 작업 섹션에서 추가합니다.',
      },
      {
        label: '기본 정보 입력 — 제목(필수), 타입, 우선순위, 상태',
        desc: '제목은 필수입니다. 우선순위는 최고(HIGHEST) / 높음(HIGH) / 보통(MEDIUM) / 낮음(LOW) / 최저(LOWEST) 5단계입니다. 초기 상태는 기본값으로 백로그(BACKLOG)가 설정됩니다.',
      },
      {
        label: '담당·일정 입력 — 담당자, 스프린트, 시작일·마감일',
        desc: '담당자를 지정하면 해당 팀원의 내 이슈 화면과 업무 현황 캘린더에 표시됩니다. 보고자는 현재 로그인한 사용자로 자동 설정됩니다. Story·Task에는 상위 Epic과 스토리 포인트를 추가로 설정할 수 있습니다.',
      },
      {
        label: '라벨·설명·첨부파일 추가 (선택)',
        desc: '설정 탭에서 만들어둔 라벨을 선택해 이슈를 분류합니다. 설명란은 마크다운 에디터로 서식 있는 텍스트와 Ctrl+V 이미지 붙여넣기를 지원합니다. 참고 자료는 드래그 앤 드롭 또는 버튼으로 첨부합니다.',
      },
      {
        label: '[이슈 추가] 클릭 → 백로그에서 확인',
        desc: '저장하면 이슈가 선택한 스프린트 또는 백로그에 추가됩니다. 백로그 탭에서 해당 이슈가 Epic 계층 아래에 나타나는지 확인하세요.',
      },
    ],
    tip: 'Epic → Story → Task 계층을 활용하면 업무 범위와 진행 상태를 한눈에 파악할 수 있습니다. 단순 업무는 Task 하나로 시작해도 충분합니다.',
  },
  {
    id: 'sc-issue-detail',
    shortTitle: '이슈 상세 관리',
    title: '이슈 진행 상황을 업데이트하고 싶어요',
    role: '팀원',
    roleColor: 'blue',
    color: 'blue',
    steps: [
      {
        label: '이슈 클릭 → 전체 화면 다이얼로그',
        desc: '보드 카드, 백로그 행, 대시보드 목록 어디서든 이슈를 클릭하면 전체 화면(maximized) 다이얼로그가 열립니다. 상단에 이슈 타입 아이콘, 키 번호, 제목, 현재 상태 배지, 연결된 SR 바로가기(SR 연동 시)가 표시됩니다.',
      },
      {
        label: '제목·설명 인라인 편집',
        desc: '제목을 클릭하면 편집 모드로 전환되고 Enter 키 또는 포커스 이동(blur) 시 자동 저장됩니다. 설명을 클릭하면 마크다운 에디터가 열립니다. 서식 있는 텍스트 작성과 Ctrl+V 이미지 붙여넣기를 지원하며, [저장] 버튼으로 저장합니다.',
      },
      {
        label: '우측 사이드바에서 속성 수정',
        desc: '우측 사이드바에서 상태, 타입, 우선순위, 담당자, 보고자, 스프린트, 상위 Epic, 스토리 포인트, 시작일, 마감일, 라벨을 수정합니다. 각 항목을 클릭하면 드롭다운 또는 날짜 선택기가 열립니다.',
      },
      {
        label: '하위 작업 추가·완료·정렬',
        desc: 'Story, Task 이슈에서 하위 작업(체크리스트)을 관리합니다. 체크박스 클릭으로 완료 여부를 토글하고, 드래그로 순서를 변경하며, 하단 인라인 폼으로 새 항목을 추가합니다. Epic과 Sub-task 이슈에는 이 섹션이 없습니다.',
      },
      {
        label: '댓글 작성·답글·파일 첨부·@멘션',
        desc: '댓글 섹션에서 팀원과 소통합니다. 댓글에 [답글] 버튼으로 스레드형 답변을 달거나, [파일 첨부]로 자료를 올릴 수 있습니다. Ctrl+V로 클립보드 이미지를 바로 붙여넣는 기능도 지원합니다. @를 입력하면 팀원을 멘션할 수 있으며, 멘션된 사용자에게 인앱 알림(상단 종 아이콘)이 발송됩니다.',
      },
      {
        label: '[변경 이력] 탭 → 전체 변경 확인',
        desc: '이슈 상세 상단의 [변경 이력] 탭을 클릭하면 제목, 상태, 담당자, 우선순위, 마감일 등 모든 필드 변경 이력과 댓글 등록·삭제 기록이 시간 역순으로 나열됩니다.',
      },
    ],
    tip: '이슈 상세 다이얼로그에서 하위 작업 항목을 클릭하면 드릴다운 네비게이션으로 해당 이슈 상세로 이동합니다. 헤더의 브레드크럼으로 상위 이슈로 돌아올 수 있습니다.',
  },
  {
    id: 'sc-backlog',
    shortTitle: '백로그 관리',
    title: '백로그에서 이슈 목록을 정리하고 싶어요',
    role: 'PM · 팀원',
    roleColor: 'purple',
    color: 'purple',
    steps: [
      {
        label: '프로젝트 상세 > [백로그] 탭 클릭',
        desc: '프로젝트 상세 화면의 바로가기 버튼 또는 [백로그] 탭을 클릭합니다. 프로젝트의 모든 이슈(스프린트 배정 여부 무관)가 계층 구조(트리뷰)로 표시됩니다.',
      },
      {
        label: 'Epic → Story/Task → Sub-task 트리 구조 확인',
        desc: 'Epic은 보라색 배경으로 강조됩니다. Epic 하위에 Story/Task가 들여쓰기로 위치하고, 다시 그 하위에 Sub-task가 표시됩니다. 상위 Epic이 없는 이슈는 "에픽 없음" 구분선 아래에 별도 표시됩니다.',
      },
      {
        label: '필터로 원하는 이슈만 보기',
        desc: '상단 필터 영역에서 제목 검색(이슈 키 번호 포함), 상태, 우선순위, 이슈 유형(Epic/Story/Task/Sub-task), 담당자, 마감일 기간(시작~종료 날짜 범위)을 동시에 필터링할 수 있습니다. 설정한 필터는 새로고침해도 유지됩니다. [초기화] 버튼으로 모든 필터를 한 번에 해제합니다.',
      },
      {
        label: '[모두 펼치기] / [모두 접기] 활용',
        desc: '상단의 [모두 펼치기]로 Epic 하위 이슈를 전부 펼치거나, [모두 접기]로 Epic 행만 남깁니다. 이슈 수 배지로 현재 필터 결과 건수를 확인할 수 있습니다.',
      },
      {
        label: '서브태스크 드래그로 순서 조정',
        desc: 'Task 하위의 Sub-task는 드래그로 순서를 바꿀 수 있습니다. 변경한 순서는 이슈 상세 다이얼로그의 하위 작업 목록에도 동일하게 반영됩니다.',
      },
    ],
    tip: '백로그에서 이슈 행의 [상태] 배지를 클릭하거나 이슈 상세를 열어 스프린트를 지정할 수 있습니다. 스프린트 배정 후 보드에서 진행 상태를 관리하세요.',
  },
  {
    id: 'sc-sprint',
    shortTitle: '스프린트 계획',
    title: '스프린트를 계획하고 운영하고 싶어요',
    role: 'PM',
    roleColor: 'teal',
    color: 'teal',
    steps: [
      {
        label: '프로젝트 상세 > [스프린트] 탭 클릭',
        desc: '프로젝트 상세의 [스프린트] 탭을 클릭하면 생성된 스프린트 카드 목록이 표시됩니다. 각 카드에는 상태 배지, 이름, 목표, 이슈 수, 기간이 나타납니다.',
      },
      {
        label: '[스프린트 만들기] 클릭 → 이름·목표·기간 입력',
        desc: '이름(필수), 목표(선택, textarea), 시작일, 종료일을 입력합니다. 생성된 스프린트는 예정(PLANNED) 상태로 시작합니다. [수정] 버튼으로 이름·목표·기간은 언제든 변경 가능합니다.',
      },
      {
        label: '스프린트 상태 흐름 이해',
        desc: '스프린트 상태는 예정(PLANNED) → 진행 중(ACTIVE) → 완료(COMPLETED) 순으로 진행됩니다. 동시에 활성(ACTIVE) 상태인 스프린트를 하나만 유지하는 것을 권장합니다.',
      },
      {
        label: '이슈를 스프린트에 배치',
        desc: '이슈 생성 시 스프린트를 직접 지정하거나, 이슈 상세 다이얼로그 사이드바의 [스프린트] 필드를 클릭해 배치합니다. 이슈는 여러 스프린트 중 하나에만 배정됩니다.',
      },
      {
        label: '[스프린트 시작] / [스프린트 종료]',
        desc: '이슈 준비가 완료되면 [스프린트 시작]을 클릭해 ACTIVE 상태로 전환합니다. 종료 시 [스프린트 종료]를 클릭하면 COMPLETED로 변경되고, 미완료 이슈는 자동으로 백로그로 이동됩니다.',
      },
    ],
    tip: '스프린트 삭제 시 소속 이슈는 모두 백로그로 이동됩니다. 실수로 삭제하더라도 이슈는 보존되므로 걱정하지 마세요.',
  },
  {
    id: 'sc-board',
    shortTitle: '보드 진행 관리',
    title: '보드에서 진행 상황을 관리하고 싶어요',
    role: '팀원',
    roleColor: 'blue',
    color: 'blue',
    steps: [
      {
        label: '프로젝트 상세 > [보드] 탭 클릭',
        desc: '프로젝트 상세 화면의 바로가기 버튼 또는 [보드] 탭을 클릭합니다. 활성(ACTIVE) 스프린트의 이슈가 칸반 형식으로 표시됩니다.',
      },
      {
        label: '5열 칸반 구성 확인',
        desc: '이슈는 상태에 따라 5개 열로 분류됩니다: 백로그(BACKLOG), 할 일(TODO), 진행 중(IN_PROGRESS), 검토 중(IN_REVIEW), 완료(DONE). 카드에는 타입 아이콘, 우선순위 아이콘, 이슈 키 번호, 담당자 아바타, 하위 작업 목록이 표시됩니다.',
      },
      {
        label: '카드 드래그 또는 클릭 → 상태 변경',
        desc: '카드를 다른 열로 드래그하면 상태 변경 확인 다이얼로그가 나타납니다. 확인 후 상태가 변경됩니다. 또는 카드를 클릭해 이슈 상세를 열고 우측 사이드바의 [상태] 드롭다운으로 직접 변경할 수 있습니다.',
      },
      {
        label: '스프린트·마감일 필터로 보기 범위 조절',
        desc: '보드 상단의 스프린트 선택 드롭다운에서 특정 스프린트 또는 [전체]를 선택합니다. 전체 선택 시 스프린트 배정 여부에 관계없이 모든 이슈가 표시됩니다. 마감일 기간 필터로 특정 날짜 범위의 이슈만 추려 볼 수도 있습니다.',
      },
      {
        label: '상태 칩으로 특정 열 숨기기·표시',
        desc: '보드 상단의 상태 칩을 클릭하면 해당 열을 숨기거나 다시 표시할 수 있습니다. 특정 상태에만 집중하고 싶을 때 유용합니다. 상단 제목 clamp 토글로 카드를 2줄 요약 모드로 전환할 수도 있습니다.',
      },
    ],
    tip: '카드 제목이 길 때 [전체 보기 ↔ 2줄 요약] 토글로 표시 방식을 전환할 수 있습니다. 이슈가 많을 때는 2줄 요약 모드를 활용해 더 많은 카드를 한 화면에서 확인하세요.',
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
        desc: '좌측 메뉴에서 스케줄 관리 → 주간 보고를 클릭합니다. pm 권한이 있는 팀원 누구나 보고서를 열람할 수 있습니다. 기존 보고서 목록(주차, 기간, 제목, 상태, 업무 현황 배지, 완료율 바)이 표시됩니다. 연도·주차 필터로 검색할 수 있으며, [목록 Excel]로 보고서 목록을 다운로드할 수 있습니다.',
      },
      {
        label: '[새 보고서 생성] 클릭 → 연도·주차·제목·부서 입력 (관리자 전용)',
        desc: '새 보고서 생성은 관리자만 가능합니다. 버튼을 누르면 다이얼로그가 열리고, 연도와 주차를 입력하면 보고서 제목(예: 2026년 29주차 주간 보고)과 기간이 자동으로 생성됩니다. 부서명은 선택 항목입니다. [생성]을 누르면 해당 기간의 이슈가 자동으로 집계됩니다.',
      },
      {
        label: '통계 카드에서 전체 현황 파악',
        desc: '보고서 상세 화면 상단의 통계 카드에서 총 업무, 완료, 진행 중, 지연, 완료율(%)을 한눈에 확인합니다. 관리자 코멘트가 있으면 우측 카드로 함께 표시됩니다.',
      },
      {
        label: '4개 탭에서 집계 결과 검토',
        desc: '프로젝트별(완료/진행중/지연/차주계획 접이식), 개인별(담당자 기준 집계), 전체 업무(테이블, 페이지당 20건), 차주 계획(다음 주 예정 이슈 테이블) 탭으로 나눠 검토합니다.',
      },
      {
        label: '수기 항목 직접 추가 — 6개 섹션',
        desc: '자동 집계 외에 주요 안건(카테고리·상태 포함), 특이사항 및 리스크(유형·영향도·대응 방안 포함), 결정 필요 사항(배경·선택지·희망 결정일 포함), 네트워크, 공지사항, 복무 현황 6개 섹션에 항목을 직접 추가할 수 있습니다. 내용 입력 필드는 마크다운 에디터로 Ctrl+V 이미지 붙여넣기를 지원하며, 복무 현황은 테이블 형태로 표시됩니다.',
      },
      {
        label: '포함/제외 아이콘으로 보고서 구성 조정',
        desc: '수기 항목 좌측의 체크 아이콘을 클릭하면 해당 항목의 보고서 포함 여부를 전환합니다. 제외된 항목은 흐릿하게 표시(opacity 낮음)되며 미리보기·PDF에 포함되지 않습니다.',
      },
      {
        label: '상태 변경: 초안 → 검토중 → 확정',
        desc: '내용 검토 후 [검토 완료] 버튼으로 검토중(REVIEWING)으로 전환하고, [보고 확정]으로 최종 확정(CONFIRMED)합니다. 확정 상태에서는 수기 항목 추가·삭제가 잠깁니다. [확정 해제]로 다시 검토중으로 되돌릴 수 있습니다.',
      },
      {
        label: '[재집계] · [미리보기] · [PDF 출력] · [Excel]',
        desc: '초안 상태에서 [재집계]를 누르면 이슈를 최신 데이터로 다시 불러옵니다. [미리보기]로 인쇄 레이아웃을 확인하고, [PDF 출력]으로 브라우저 인쇄 기능을 이용해 PDF를 저장합니다. [Excel]로 보고서 데이터를 .xlsx 파일로 다운로드합니다.',
      },
      {
        label: 'PDF 출력물 구성 이해',
        desc: 'PDF는 업무 현황 요약 → 개인별 업무 일정(간트차트, 담당자·프로젝트별 그룹) → 주요 안건 → 특이사항 및 리스크 → 결정 필요 사항 → 네트워크 → 공지사항 → 복무 현황 → 금주 완료 업무 → 진행 중 업무 → 차주 계획 → SR 현황(처리 중 SR은 담당자별 요약 매트릭스) 순으로 구성됩니다. 완료·진행 중·차주 계획 업무는 담당자별로 그룹핑되며, Sub-task가 있는 Task는 중복을 피하기 위해 Sub-task만 표시됩니다.',
      },
    ],
    tip: '보고서 제출 직전에 [재집계]를 한 번 눌러 최신 이슈 상태를 반영하세요. 집계 후 수기 항목과 관리자 코멘트를 추가하는 순서로 작성하면 효율적입니다. 월간 보고 메뉴도 같은 방식으로 월 단위 보고서를 제공합니다.',
  },
]

const issueTypes = [
  { value: 'EPIC',     label: 'Epic',     icon: 'bolt',                    color: 'purple',  desc: '큰 업무 묶음. Story·Task의 상위 단위' },
  { value: 'STORY',    label: 'Story',    icon: 'menu_book',               color: 'green',   desc: '사용자 관점의 기능 단위' },
  { value: 'TASK',     label: 'Task',     icon: 'check_box_outline_blank', color: 'primary', desc: '구체적인 작업 단위 (일반 업무)' },
  { value: 'SUB_TASK', label: 'Sub-task', icon: 'subdirectory_arrow_right', color: 'grey-7', desc: 'Task·Story의 세부 작업 (이슈 상세에서 추가)' },
]

const kanbanCols = [
  { label: '백로그',  color: 'grey-4',    cards: ['레거시 코드 정리'] },
  { label: '할 일',   color: 'blue-grey', cards: ['로그인 개선'] },
  { label: '진행 중', color: 'primary',   cards: ['API 연동', '쿼리 최적화'] },
  { label: '검토 중', color: 'orange',    cards: ['배포 스크립트'] },
  { label: '완료',    color: 'positive',  cards: ['기획 문서 작성'] },
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
