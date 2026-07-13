<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">SR 사용 가이드</div>
        <div class="text-caption text-grey-6">시나리오로 배우는 SR 접수·확인·처리 흐름</div>
      </div>
    </div>

    <!-- 시나리오 탭 네비 -->
    <q-tabs v-model="activeScenario" align="left" dense class="q-mb-xl"
      active-color="primary" indicator-color="primary">
      <q-tab name="submit" icon="send"          label="SR 접수하기" />
      <q-tab name="track"  icon="manage_search" label="진행 상황 확인" />
      <q-tab name="manage" icon="support_agent" label="SR 검토 · 처리" />
    </q-tabs>

    <!-- ═══════════════════════════════════════════════════════
         시나리오 1: SR 접수하기 (요청자)
    ═══════════════════════════════════════════════════════ -->
    <div v-show="activeScenario === 'submit'">

      <q-card flat bordered class="scenario-header q-mb-xl">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="primary" text-color="white" class="text-weight-bold q-mr-md">1</q-avatar>
          <div class="col">
            <div class="text-h6 text-weight-bold">처음으로 SR을 접수하고 싶어요</div>
            <q-badge color="blue-2" text-color="blue-9" label="요청자" />
          </div>
        </q-card-section>
      </q-card>

      <!-- ── Step 1 : 메뉴 이동 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">좌측 메뉴 [SR] → [SR 접수]를 클릭합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">접수 폼은 <strong>4단계 스텝</strong>으로 구성됩니다. 단계마다 [다음 단계] 버튼으로 진행하세요.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 4단계 스텝</div>
              <div class="row q-gutter-sm" style="pointer-events:none">
                <q-chip v-for="s in steps4" :key="s.name" dense :color="s.done ? 'primary' : 'grey-3'"
                  :text-color="s.done ? 'white' : 'grey-7'" :icon="s.icon">{{ s.name }}</q-chip>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 2 : 요청 유형 선택 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">요청 유형을 선택합니다 (Step 1)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              업무 성격에 맞는 유형을 고르면 해당 유형에 맞는 추가 입력 항목이 3단계에 나타납니다.
              유형을 잘못 선택했다면 2단계에서 [유형 변경] 버튼으로 되돌아올 수 있습니다.
            </div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 유형 선택 카드</div>
              <div class="type-grid" style="pointer-events:none">
                <div v-for="t in typeCards" :key="t.value" class="type-mock-card">
                  <q-icon :name="t.icon" size="22px" color="grey-5" />
                  <div class="text-caption text-weight-bold q-mt-xs">{{ t.label }}</div>
                  <div class="text-caption text-grey-6" style="font-size:0.7rem">{{ t.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 3 : 기본 정보 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">기본 정보를 입력합니다 (Step 2)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              <strong>별표(*) 항목은 필수</strong>입니다. 중요도·긴급 여부는 담당자 배정 우선순위에 영향을 줍니다.
            </div>
            <div class="mock-screen" style="max-width:520px">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 기본 정보 입력 폼</div>
              <div class="column q-gutter-sm" style="pointer-events:none">
                <q-input model-value="" outlined dense label="요청 제목 *" placeholder="한 줄로 요약해주세요." />
                <div class="row q-col-gutter-sm">
                  <div class="col">
                    <q-input model-value="" outlined dense label="요청 부서 *" />
                  </div>
                  <div class="col">
                    <q-input model-value="" outlined dense label="대상 시스템 *" placeholder="어떤 시스템에 대한 요청인지" />
                  </div>
                </div>
                <q-input model-value="" outlined dense label="요청 배경 (선택)" type="textarea" :rows="2"
                  placeholder="이 요청이 발생하게 된 배경이나 상황을 설명해주세요." />
                <div class="row q-col-gutter-sm items-center">
                  <div class="col">
                    <q-input model-value="" outlined dense label="희망 완료일" type="date" stack-label />
                  </div>
                  <div class="col">
                    <q-input model-value="보통" outlined dense label="중요도" />
                  </div>
                  <div class="col-auto self-center">
                    <div class="row items-center q-gutter-xs">
                      <q-toggle :model-value="false" color="negative" dense />
                      <span class="text-caption text-grey-7">긴급 요청</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="q-mt-sm">
              <div class="text-caption text-weight-bold q-mb-xs">중요도 옵션</div>
              <div class="row q-gutter-xs" style="pointer-events:none">
                <q-badge color="red-7"    label="최고 (CRITICAL)" />
                <q-badge color="orange-7" label="높음 (HIGH)" />
                <q-badge color="blue-6"   label="보통 (MEDIUM)" />
                <q-badge color="grey-5"   label="낮음 (LOW)" />
              </div>
            </div>
            <q-banner rounded class="bg-orange-1 q-mt-sm" style="pointer-events:none">
              <template #avatar><q-icon name="warning_amber" color="orange-8" /></template>
              <span class="text-orange-9 text-body2">긴급 요청 토글을 켜면 <strong>긴급 사유 입력란</strong>이 나타납니다. 사유를 반드시 입력해야 접수할 수 있습니다.</span>
            </q-banner>
          </div>
        </div>
      </div>

      <!-- ── Step 4 : 유형별 추가 정보 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">유형별 추가 정보를 입력합니다 (Step 3)</div>
            <div class="text-body2 text-grey-7 q-mb-md">
              선택한 유형에 따라 다른 항목이 표시됩니다. 에디터 필드에서는 <strong>Ctrl+V로 이미지를 바로 붙여넣을</strong> 수 있습니다.
            </div>

            <div class="q-mb-md">
              <div class="text-caption text-weight-bold text-grey-7 q-mb-xs">유형별 주요 입력 항목 예시</div>
              <q-list dense bordered class="rounded-borders" style="pointer-events:none">
                <q-item v-for="ex in typeExamples" :key="ex.type" class="q-py-sm">
                  <q-item-section avatar style="min-width:32px">
                    <q-icon :name="ex.icon" :color="ex.color" size="18px" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{ ex.label }}</q-item-label>
                    <q-item-label caption class="text-grey-6">{{ ex.fields }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>

            <q-banner rounded class="bg-blue-1" style="pointer-events:none">
              <template #avatar><q-icon name="info" color="blue-7" /></template>
              <span class="text-blue-9 text-body2">추가 항목이 없는 유형(기타 등)은 이 단계를 자동으로 건너뜁니다.</span>
            </q-banner>
          </div>
        </div>
      </div>

      <!-- ── Step 5 : 첨부 및 제출 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">5</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">첨부파일을 추가하고 제출합니다 (Step 4)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              추가 첨부파일(최대 <strong>20MB</strong>), 비고를 입력한 뒤 제출 전 요약을 확인하고 [접수하기]를 누르세요.
              허용 형식: PDF, HWP, DOCX, XLSX, PPTX, ZIP, JPG, PNG, GIF
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 제출 버튼 영역</div>
              <div class="row q-gutter-sm">
                <q-btn color="primary"  no-caps icon="send" label="접수하기" unelevated />
                <q-btn outline color="grey-6" no-caps icon="save" label="임시저장" />
                <q-btn flat color="grey-7" no-caps label="이전" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 임시저장 흐름 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="grey-5" text-color="white" class="step-num">
            <q-icon name="save" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">임시저장 활용 방법</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              [임시저장]을 누르면 작성 중인 내용이 저장됩니다. 다시 [SR 접수] 메뉴에 들어오면 상단에 배너가 표시되며, 칩을 클릭해 이어서 작성할 수 있습니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 임시저장 배너</div>
              <q-banner rounded class="bg-blue-1">
                <template #avatar><q-icon name="restore_page" color="blue-7" /></template>
                <div class="text-weight-medium text-blue-9">작성 중인 임시저장 SR이 있습니다.</div>
                <div class="text-caption text-blue-7 q-mt-xs">불러와서 이어서 작성할 수 있습니다.</div>
                <div class="q-mt-sm">
                  <q-chip dense icon="edit_note" color="blue-2" text-color="blue-10">DB 조회 속도 개선 요청
                    <span class="q-ml-xs text-blue-6" style="font-size:0.72rem">2026-07-10</span>
                  </q-chip>
                </div>
              </q-banner>
            </div>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">임시저장은 여러 개 저장할 수 있습니다. 배너에 나타나는 칩을 클릭해 원하는 임시저장을 불러오세요.</span>
      </q-banner>

    </div>

    <!-- ═══════════════════════════════════════════════════════
         시나리오 2: 내 SR 진행 상황 확인 (요청자)
    ═══════════════════════════════════════════════════════ -->
    <div v-show="activeScenario === 'track'">

      <q-card flat bordered class="scenario-header q-mb-xl">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="teal" text-color="white" class="text-weight-bold q-mr-md">2</q-avatar>
          <div class="col">
            <div class="text-h6 text-weight-bold">내 SR 진행 상황을 확인하고 싶어요</div>
            <q-badge color="teal-2" text-color="teal-9" label="요청자" />
          </div>
        </q-card-section>
      </q-card>

      <!-- ── Step 1 : 내 SR 목록 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">메뉴 [SR] → [내 SR 목록]을 클릭합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              내가 접수한 SR이 최신순으로 표시됩니다. 상단의 상태 탭과 검색창을 이용해 원하는 SR을 빠르게 찾을 수 있습니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 상태 탭 필터</div>
              <div class="row q-gutter-xs q-mb-sm">
                <q-chip v-for="tab in myTabs" :key="tab.key" dense clickable
                  :color="tab.key === 'all' ? tab.color : 'grey-3'"
                  :text-color="tab.key === 'all' ? 'white' : 'grey-7'">
                  {{ tab.label }}
                  <span v-if="tab.count" class="q-ml-xs" style="font-size:0.72rem">{{ tab.count }}</span>
                </q-chip>
              </div>
              <q-input model-value="" outlined dense placeholder="제목 · 시스템 · SR번호 검색" style="max-width:280px">
                <template #prepend><q-icon name="search" size="18px" color="grey-5" /></template>
              </q-input>
            </div>
            <div class="text-caption text-grey-7 q-mt-sm">
              <strong>탭 구성:</strong> 전체 / 임시저장 / 진행 중(접수~처리중) / 확인 요청(처리완료·요청자 확인 대기) / 완료(최종완료) / 반려·취소
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 2 : SR 카드 읽기 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR 카드에서 현황을 한눈에 확인합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              각 SR 행에는 SR 번호, 제목, 유형, 대상 시스템, 현재 상태, 담당자, 희망 완료일이 표시됩니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — SR 목록 행</div>
              <div class="sr-mock-row">
                <div style="width:4px;background:#ff9800;align-self:stretch;border-radius:2px;flex-shrink:0" />
                <div class="col q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <span class="text-caption text-grey-5">SR-2026-0042</span>
                    <q-badge color="red"      label="긴급" style="font-size:0.65rem" />
                    <q-badge color="negative" label="지연" style="font-size:0.65rem" />
                  </div>
                  <div class="text-body2 text-weight-medium q-mb-xs">월별 정산 오류 수정 요청</div>
                  <div class="row items-center q-gutter-xs">
                    <q-icon name="bug_report" size="13px" color="grey-5" />
                    <span class="text-caption text-grey-6">오류 수정 · 정산 시스템</span>
                  </div>
                </div>
                <div class="text-right q-pa-sm">
                  <q-chip color="blue-7" text-color="white" dense size="xs">처리 중</q-chip>
                  <div class="text-caption text-grey-5 q-mt-xs">담당: 홍길동</div>
                  <div class="text-caption text-negative text-weight-medium">완료 희망 2026-07-10</div>
                </div>
              </div>
            </div>
            <div class="q-mt-sm">
              <div class="text-caption text-weight-bold q-mb-xs">색상 의미</div>
              <div class="row q-gutter-xs" style="pointer-events:none">
                <div class="row items-center q-gutter-xs">
                  <div style="width:6px;height:20px;background:#ef5350;border-radius:2px" />
                  <span class="text-caption text-grey-7">최고 우선순위</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <div style="width:6px;height:20px;background:#ff9800;border-radius:2px" />
                  <span class="text-caption text-grey-7">높음</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <div style="width:6px;height:20px;background:#42a5f5;border-radius:2px" />
                  <span class="text-caption text-grey-7">보통</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <div style="width:6px;height:20px;background:#bdbdbd;border-radius:2px" />
                  <span class="text-caption text-grey-7">낮음</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 3 : 상태 흐름 이해 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">상태 흐름을 이해합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              SR은 아래 흐름으로 진행됩니다. 보류·반려·취소는 중간에 분기될 수 있습니다.
            </div>
            <div class="mock-screen" style="pointer-events:none;overflow-x:auto">
              <div class="row items-center q-gutter-xs" style="flex-wrap:nowrap;min-width:560px">
                <q-badge color="grey-6"   label="접수" />
                <q-icon name="arrow_forward" color="grey-4" size="14px" />
                <q-badge color="blue-6"   label="검토 중" />
                <q-icon name="arrow_forward" color="grey-4" size="14px" />
                <q-badge color="teal"     label="처리 중" />
                <q-icon name="arrow_forward" color="grey-4" size="14px" />
                <q-badge color="purple"   label="처리 완료" />
                <q-icon name="arrow_forward" color="grey-4" size="14px" />
                <q-badge color="orange"   label="확인 중" />
                <q-icon name="arrow_forward" color="grey-4" size="14px" />
                <q-badge color="positive" label="최종 완료" />
              </div>
              <div class="row q-gutter-sm q-mt-sm">
                <div class="row items-center q-gutter-xs">
                  <q-badge color="brown"    label="보류" />
                  <span class="text-caption text-grey-6">추가 정보 확인 또는 대기</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-badge color="negative" label="반려" />
                  <span class="text-caption text-grey-6">검토 단계에서 거절</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-badge color="grey-6"   label="취소" />
                  <span class="text-caption text-grey-6">요청자가 직접 취소</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 4 : SR 상세 4탭 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR을 클릭하면 상세 화면이 열립니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              상세 화면은 <strong>4개 탭</strong>으로 구성됩니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 상세 탭 구성</div>
              <div class="row q-gutter-xs">
                <q-badge color="primary" label="요청 내용" />
                <q-badge color="teal"    label="처리/증적" />
                <q-badge color="orange"  label="댓글/문의" />
                <q-badge color="grey-6"  label="이력" />
              </div>
            </div>
            <q-list dense class="q-mt-sm" style="pointer-events:none">
              <q-item v-for="tab in detailTabs" :key="tab.name" class="q-px-none">
                <q-item-section avatar style="min-width:28px">
                  <q-icon :name="tab.icon" :color="tab.color" size="16px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium" style="font-size:0.85rem">{{ tab.name }}</q-item-label>
                  <q-item-label caption class="text-grey-6">{{ tab.desc }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </div>
      </div>

      <!-- ── Step 5 : 댓글 기능 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">5</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">[댓글/문의] 탭에서 담당자와 소통합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              처리 과정에서 추가 정보가 필요하거나 진행 상황을 확인하고 싶을 때 댓글로 문의하세요.
            </div>
            <div class="mock-screen" style="max-width:480px;pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 댓글 입력 영역</div>
              <q-input model-value="" outlined dense type="textarea" :rows="2"
                placeholder="댓글을 입력하세요... (이미지 붙여넣기 가능)" />
              <div class="row items-center q-mt-xs q-gutter-sm">
                <q-btn flat dense size="xs" icon="attach_file" color="grey-7" label="파일 첨부" />
              </div>
            </div>
            <div class="text-caption text-grey-7 q-mt-sm">
              댓글 입력란에 <strong>Ctrl+V로 이미지를 바로 붙여넣기</strong>할 수 있습니다. 파일 첨부 버튼으로 문서·이미지를 첨부할 수도 있습니다.
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 6 : 최종 확인 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="positive" text-color="white" class="step-num">6</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">처리 완료 후 [최종 확인]을 눌러 SR을 닫습니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              담당자가 처리를 완료하면 상태가 <strong>확인 중</strong>으로 바뀝니다.
              요청자가 처리 내용을 확인하고 [최종 확인] 버튼을 눌러야 SR이 <strong>최종 완료</strong>로 닫힙니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 액션 버튼</div>
              <div class="row q-gutter-sm">
                <q-btn color="positive" no-caps icon="check_circle" label="최종 확인" unelevated size="sm" />
                <q-btn color="amber-8" outline no-caps icon="edit" label="SR 수정" size="sm" />
                <q-btn color="negative" outline no-caps icon="cancel" label="취소" size="sm" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── SR 취소 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="grey-5" text-color="white" class="step-num">
            <q-icon name="cancel" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR을 취소하려면?</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              목록에서 행 우측의 <strong>취소 아이콘</strong>을 클릭하거나, 상세 화면 상단의 [취소] 버튼을 누르면 됩니다.
              최종 완료·반려·이미 취소된 SR은 취소할 수 없습니다.
            </div>
            <q-banner rounded class="bg-grey-2" style="pointer-events:none">
              <template #avatar><q-icon name="info" color="grey-6" /></template>
              <span class="text-grey-8">취소 다이얼로그가 열리면 <strong>취소 사유</strong>를 입력해야 확인 버튼이 활성화됩니다.</span>
            </q-banner>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">우측 요약 패널에서 담당자, D-Day, 접수일을 한눈에 확인할 수 있어요. 최근 상태 변경 이력도 3건까지 표시됩니다.</span>
      </q-banner>

    </div>

    <!-- ═══════════════════════════════════════════════════════
         시나리오 3: SR 검토 · 처리 (운영팀)
    ═══════════════════════════════════════════════════════ -->
    <div v-show="activeScenario === 'manage'">

      <q-card flat bordered class="scenario-header q-mb-xl">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="deep-purple" text-color="white" class="text-weight-bold q-mr-md">3</q-avatar>
          <div class="col">
            <div class="text-h6 text-weight-bold">SR을 검토하고 처리해야 해요</div>
            <q-badge color="deep-purple-2" text-color="deep-purple-9" label="운영팀 (sr_operator / sr_manager)" />
          </div>
        </q-card-section>
      </q-card>

      <!-- ── Step 1 : SR 관리 진입 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">메뉴 [SR] → [SR 관리]를 클릭합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              SR 관리 화면에 진입하면 맨 위에 <strong>통계 카드 8개</strong>가 표시됩니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 통계 카드</div>
              <div class="row q-col-gutter-sm">
                <div v-for="sc in statCards" :key="sc.label" class="col-6 col-sm-3">
                  <q-card flat bordered class="text-center q-pa-sm">
                    <div class="text-h5 text-weight-bold" :class="`text-${sc.color}`">{{ sc.value }}</div>
                    <div class="text-caption text-grey-6">{{ sc.label }}</div>
                  </q-card>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 2 : 상태 탭 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">상태 탭으로 SR을 분류해서 봅니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              10개 탭으로 상태별 SR을 관리합니다. <strong>⏰ 지연</strong> 탭은 희망 완료일이 지났지만 아직 처리되지 않은 SR을 모아 보여줍니다.
            </div>
            <div class="mock-screen" style="pointer-events:none;overflow-x:auto">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 상태 탭</div>
              <div class="row q-gutter-xs" style="flex-wrap:nowrap;min-width:640px">
                <q-btn v-for="tab in manageTabs" :key="tab" flat dense no-caps size="sm"
                  :color="tab === '전체' ? 'primary' : 'grey-7'" :label="tab" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 3 : 필터 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">필터로 원하는 SR을 빠르게 찾습니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              여러 조건을 동시에 설정하고 [조회] 버튼을 누릅니다. [초기화] 버튼으로 한 번에 초기화할 수 있습니다.
            </div>
            <div class="mock-screen" style="pointer-events:none;max-width:560px">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 필터 영역</div>
              <div class="row q-col-gutter-sm q-mb-sm">
                <div class="col-6">
                  <q-input model-value="" outlined dense label="요청 부서" />
                </div>
                <div class="col-6">
                  <q-input model-value="" outlined dense label="요청자" />
                </div>
                <div class="col-6">
                  <q-input model-value="" outlined dense label="요청 유형" />
                </div>
                <div class="col-6">
                  <q-input model-value="" outlined dense label="관련 시스템" />
                </div>
                <div class="col-6">
                  <q-input model-value="" outlined dense label="중요도" />
                </div>
              </div>
              <div class="row items-center q-gutter-md">
                <div class="row items-center q-gutter-xs">
                  <q-toggle model-value="false" color="negative" dense size="sm" />
                  <span class="text-caption text-grey-7">긴급</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-toggle model-value="false" color="primary" dense size="sm" />
                  <span class="text-caption text-grey-7">내 배정</span>
                </div>
                <q-btn color="primary" icon="search" label="조회" unelevated size="sm" no-caps />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 4 : 검토 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR을 열어 [검토] 버튼을 클릭합니다 (sr_manager)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              접수·검토중·추가확인 상태의 SR에서 [검토] 버튼이 나타납니다. 검토 결과를 선택하고 의견을 입력합니다.
            </div>
            <div class="mock-screen" style="max-width:460px;pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 검토 다이얼로그</div>
              <div class="q-mb-sm">
                <div class="text-caption text-grey-6 q-mb-xs">검토 결과 *</div>
                <div class="row q-gutter-xs">
                  <q-badge color="teal"     label="승인 (APPROVED)" />
                  <q-badge color="negative" label="반려 (REJECTED)" />
                  <q-badge color="brown"    label="보류 (ON_HOLD)" />
                  <q-badge color="amber-7"  label="추가 확인 요청" />
                </div>
              </div>
              <q-input model-value="" outlined dense label="검토 의견" type="textarea" :rows="2" />
            </div>
            <div class="text-caption text-grey-7 q-mt-sm">
              <strong>반려</strong> 선택 시 반려 사유, <strong>보류</strong> 선택 시 보류 사유, <strong>추가 확인 요청</strong> 선택 시 확인 내용 입력란이 추가로 나타납니다.
            </div>
          </div>
        </div>
      </div>

      <!-- ── Step 5 : 담당자 배정 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="cyan-7" text-color="white" class="step-num">5</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">승인 후 [담당자 배정]을 클릭합니다 (sr_manager)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              승인된 SR에 담당자를 배정하고 처리 기간을 설정합니다. 예상 공수는 <strong>시작일·완료일 기준으로 주말을 제외하고 자동 계산</strong>됩니다.
              배포 필요 여부, 보안 검토 필요 여부도 함께 설정합니다.
            </div>
            <div class="mock-screen" style="max-width:460px;pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 담당자 배정 다이얼로그</div>
              <q-input model-value="" outlined dense label="담당자 *" placeholder="이름으로 검색" class="q-mb-sm" />
              <div class="row q-gutter-sm q-mb-sm">
                <q-input model-value="" outlined dense label="처리 예정 시작일" type="date" class="col" />
                <q-input model-value="" outlined dense label="처리 예정 완료일" type="date" class="col" />
              </div>
              <q-input model-value="5일" outlined dense label="예상 공수 (자동 계산, 주말 제외)" readonly bg-color="grey-1" class="q-mb-sm" />
              <div class="row q-gutter-xl">
                <div class="row items-center q-gutter-xs">
                  <q-toggle model-value="false" color="orange-7" dense size="sm" />
                  <span class="text-caption">배포 필요</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-toggle model-value="false" color="red-7" dense size="sm" />
                  <span class="text-caption">보안 검토 필요</span>
                </div>
              </div>
            </div>
            <q-banner rounded class="bg-indigo-1 q-mt-sm" style="pointer-events:none">
              <template #avatar><q-icon name="link" color="indigo-7" /></template>
              <span class="text-indigo-9 text-body2">SR 기본 프로젝트가 설정되어 있으면, 담당자 배정 시 스케줄 관리 시스템에 이슈가 자동으로 등록됩니다.</span>
            </q-banner>
          </div>
        </div>
      </div>

      <!-- ── Step 6 : 처리 완료 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="blue-7" text-color="white" class="step-num">6</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">[상태 변경] → 처리 완료를 선택합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              처리를 마치면 [상태 변경] 버튼을 눌러 <strong>처리 완료</strong>를 선택합니다.
              처리 결과를 입력하고, 배포 완료 여부와 배포 일시도 기록합니다.
            </div>
            <div class="mock-screen" style="max-width:440px;pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 처리 완료 입력</div>
              <q-input model-value="처리 완료" outlined dense label="변경할 상태 *" class="q-mb-sm" />
              <q-input model-value="" outlined dense label="처리 결과 *" type="textarea" :rows="3"
                placeholder="처리 결과를 입력하세요." class="q-mb-sm" />
              <div class="row items-center q-gutter-xs">
                <q-toggle model-value="true" color="positive" dense size="sm" />
                <span class="text-caption">배포 완료</span>
                <q-input model-value="2026-07-13T14:00" outlined dense label="배포 일시" type="datetime-local"
                  class="q-ml-sm" style="flex:1" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 내부 메모 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="grey-6" text-color="white" class="step-num">
            <q-icon name="lock" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">운영팀끼리 내부 메모를 남길 수 있습니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              댓글/문의 탭에서 <strong>[내부 메모]</strong> 체크박스를 켜고 댓글을 등록하면, 운영팀에게만 보이는 메모가 됩니다.
              요청자에게는 표시되지 않습니다.
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — 내부 메모 체크박스</div>
              <div class="row items-center q-gutter-sm">
                <q-checkbox model-value="true" label="내부 메모 (운영팀에만 공개)" size="xs" color="grey-7" dense />
              </div>
              <div class="q-mt-sm">
                <div class="row items-center q-gutter-xs">
                  <q-avatar size="26px" color="grey-5" text-color="white" style="font-size:0.75rem">홍</q-avatar>
                  <span class="text-weight-medium" style="font-size:0.9rem">홍길동</span>
                  <q-badge color="grey-5" label="내부 메모" size="xs" />
                  <span class="text-caption text-grey-5 q-ml-auto">2026-07-13 14:32</span>
                </div>
                <div class="q-mt-xs q-ml-lg q-pa-sm bg-grey-2 rounded-borders text-caption text-grey-8">
                  DB 팀 확인 필요. 별도 채널로 공유 예정.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Excel ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="positive" text-color="white" class="step-num">
            <q-icon name="download" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">Excel로 SR 목록을 내보냅니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              SR 관리 페이지 우측 상단의 <strong>[Excel]</strong> 버튼을 클릭하면 현재 탭·필터 기준으로 <code>SR_목록.xlsx</code> 파일이 다운로드됩니다.
              SR 상세 화면에서는 해당 SR 한 건을 Excel로 내보낼 수 있습니다 (관리자 전용).
            </div>
            <div class="mock-screen" style="pointer-events:none">
              <div class="text-caption text-grey-5 q-mb-sm">화면 예시 — Excel 버튼</div>
              <q-btn outline color="green-7" icon="download" label="Excel" no-caps unelevated />
            </div>
          </div>
        </div>
      </div>

      <!-- ── SR 기본 프로젝트 ── -->
      <div class="step-row q-mb-xl">
        <div class="row items-start q-gutter-md no-wrap">
          <q-avatar size="32px" color="indigo-7" text-color="white" class="step-num">
            <q-icon name="settings" size="16px" />
          </q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR 기본 프로젝트를 설정합니다 (관리자)</div>
            <div class="text-body2 text-grey-7 q-mb-sm">
              관리자는 SR 관리 페이지의 <strong>[SR 기본 프로젝트]</strong> 버튼으로 담당자 배정 시 스케줄 관리 이슈가 자동 등록될 기본 프로젝트를 설정할 수 있습니다.
            </div>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">⏰ 지연 탭을 매일 확인해 기한이 지난 SR을 우선 처리하세요. 내 배정 토글을 켜면 내가 담당한 SR만 볼 수 있습니다.</span>
      </q-banner>

    </div>

  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeScenario = ref('submit')

const steps4 = [
  { name: '유형 선택',   icon: 'category',      done: true },
  { name: '기본 정보',   icon: 'edit_note',      done: false },
  { name: '추가 정보',   icon: 'playlist_add',   done: false },
  { name: '첨부 및 제출',icon: 'check_circle',   done: false },
]

const typeCards = [
  { value: 'IMPROVEMENT',  label: '기능 개선',     icon: 'tune',       desc: '불편한 기능 개선 요청' },
  { value: 'BUG_FIX',      label: '오류 수정',     icon: 'bug_report', desc: '오류·비정상 동작 신고' },
  { value: 'DATA_REQUEST',  label: '데이터 요청',   icon: 'storage',    desc: '데이터 추출·제공' },
  { value: 'PERMISSION',    label: '권한 요청',     icon: 'lock_open',  desc: '시스템 접근 권한 신청' },
  { value: 'CONFIG_CHANGE', label: '설정 변경',     icon: 'settings',   desc: '시스템·서버 설정 변경' },
  { value: 'SERVER_INFRA',  label: '서버/인프라',   icon: 'dns',        desc: '서버 작업·인프라 요청' },
  { value: 'SECURITY',      label: '보안 조치',     icon: 'security',   desc: '취약점 조치·보안 점검' },
  { value: 'ETC',           label: '기타',          icon: 'more_horiz', desc: '위 항목에 해당하지 않는 요청' },
]

const typeExamples = [
  { type: 'BUG_FIX',      icon: 'bug_report', color: 'red-7',    label: '오류 수정',    fields: '오류 발생 화면, 발생 일시, 오류 내용, 재현 절차 (에디터), 기대 동작, 실제 동작, 사용자 환경' },
  { type: 'DATA_REQUEST',  icon: 'storage',    color: 'purple-7', label: '데이터 요청',  fields: '요청 목적, 요청 항목 (에디터), 기간(시작/종료), 대상 조건, 개인정보·민감정보 포함 여부, 제공 형식(CSV/Excel/SQL/API), 제공 방식, 승인자' },
  { type: 'PERMISSION',    icon: 'lock_open',  color: 'teal-7',   label: '권한 요청',    fields: '권한 대상자, 요청 권한, 요청 사유 (에디터), 권한 사용 기간, 만료일, 승인자, 기존 권한 여부(신규/변경/회수)' },
  { type: 'CONFIG_CHANGE', icon: 'settings',   color: 'orange-8', label: '설정 변경',    fields: '설정 대상, 현재 설정값, 변경 요청값, 변경 사유, 영향 범위, 적용 희망 일시, 서비스 중단 여부, 롤백 방안' },
  { type: 'SERVER_INFRA',  icon: 'dns',        color: 'indigo-7', label: '서버/인프라', fields: '대상 서버/시스템, 요청 작업 유형(생성/재기동/디스크증설/방화벽 등), 요청 상세, 작업 희망 일시, 서비스 영향 여부, 사전 백업 필요 여부' },
  { type: 'SECURITY',      icon: 'security',   color: 'deep-orange-8', label: '보안 조치', fields: '보안 요청 유형, 취약점/보안 이슈 (에디터), 위험도(상/중/하), 조치 요청 내용, 조치 기한, 증적 필요 여부' },
]

const myTabs = [
  { key: 'all',     label: '전체',      color: 'grey-7',   count: 8 },
  { key: 'draft',   label: '임시저장',  color: 'grey-6',   count: 1 },
  { key: 'active',  label: '진행 중',   color: 'blue-7',   count: 3 },
  { key: 'pending', label: '확인 요청', color: 'amber-8',  count: 1 },
  { key: 'done',    label: '완료',      color: 'positive', count: 2 },
  { key: 'ended',   label: '반려/취소', color: 'grey-5',   count: 1 },
]

const detailTabs = [
  { name: '요청 내용',  icon: 'description',          color: 'primary', desc: '접수 시 입력한 유형별 상세 내용, 비고, 추가 첨부파일' },
  { name: '처리/증적',  icon: 'engineering',           color: 'teal',    desc: '검토 결과(승인/반려/보류/추가확인), 담당자·예상공수·처리기간, 배포 여부, 처리 결과, 연결된 스케줄 관리 이슈' },
  { name: '댓글/문의',  icon: 'chat_bubble_outline',  color: 'orange',  desc: '요청자-담당자 소통 공간. 파일 첨부, Ctrl+V 이미지, 내부 메모(운영팀 전용)' },
  { name: '이력',       icon: 'history',               color: 'grey-6',  desc: '상태 변경, 필드 수정 등 모든 변경 이력이 시간 순서대로 자동 기록' },
]

const statCards = [
  { label: '전체',        value: 42,  color: 'primary'  },
  { label: '진행 중',     value: 18,  color: 'blue-8'   },
  { label: '완료',        value: 15,  color: 'positive' },
  { label: '지연',        value: 3,   color: 'negative' },
  { label: '보류',        value: 2,   color: 'brown'    },
  { label: '반려',        value: 1,   color: 'red-8'    },
  { label: '긴급',        value: 5,   color: 'red'      },
  { label: '평균처리(일)', value: '4.2', color: 'grey-7' },
]

const manageTabs = ['전체', '접수', '검토 중', '처리 중', '처리 완료', '확인 중', '최종 완료', '보류', '반려', '⏰ 지연']
</script>

<style scoped>
.scenario-header {
  border-left: 4px solid var(--q-primary);
  background: #f0f4ff;
}
.step-row {
  padding-left: 4px;
}
.step-num {
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
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
.type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
@media (max-width: 600px) {
  .type-grid { grid-template-columns: repeat(2, 1fr); }
}
.type-mock-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 6px;
  border: 1.5px solid rgba(0,0,0,0.1);
  border-radius: 8px;
  background: #fafafa;
  text-align: center;
}
.sr-mock-row {
  display: flex;
  align-items: center;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 6px;
  overflow: hidden;
}
</style>
