<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">SR 사용 가이드</div>
        <div class="text-caption text-grey-6">시나리오로 배우는 SR 접수·처리 흐름</div>
      </div>
    </div>

    <!-- 시나리오 탭 네비 -->
    <q-tabs v-model="activeScenario" align="left" dense class="q-mb-lg" active-color="primary" indicator-color="primary">
      <q-tab name="submit" icon="send" label="SR 접수하기" />
      <q-tab name="track" icon="manage_search" label="진행 상황 확인" />
      <q-tab name="manage" icon="support_agent" label="SR 검토·처리" />
    </q-tabs>

    <!-- ───────────────────────────────────────────────────
         시나리오 1: SR 접수하기
    ─────────────────────────────────────────────────────── -->
    <div v-show="activeScenario === 'submit'">

      <q-card flat bordered class="scenario-header q-mb-lg">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="primary" text-color="white" class="text-weight-bold">1</q-avatar>
          <div class="col q-ml-md">
            <div class="text-h6 text-weight-bold">처음으로 SR을 접수하고 싶어요</div>
            <q-badge color="blue-2" text-color="blue-9" label="요청자" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Step 1 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">좌측 메뉴에서 [SR 접수]를 클릭합니다</div>
            <div class="text-body2 text-grey-7">SR 메뉴 아래 [SR 접수]를 눌러 접수 폼으로 이동하세요.</div>
          </div>
        </div>
      </div>

      <!-- Step 2 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">요청 유형을 선택합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">업무 성격에 맞는 유형을 고르면 그에 맞는 입력 항목이 나타납니다.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div class="row q-gutter-sm" style="pointer-events:none">
                <q-btn outline color="blue" size="sm" no-caps label="개선 요청" />
                <q-btn outline color="red" size="sm" no-caps label="오류 신고" />
                <q-btn outline color="teal" size="sm" no-caps label="데이터 요청" />
                <q-btn outline color="orange" size="sm" no-caps label="권한 요청" />
                <q-btn outline color="purple" size="sm" no-caps label="설정 변경" />
                <q-btn outline color="grey-7" size="sm" no-caps label="서버/인프라" />
                <q-btn outline color="deep-orange" size="sm" no-caps label="보안 요청" />
                <q-btn outline color="grey-6" size="sm" no-caps label="기타" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="primary" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">기본 정보를 입력합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">별표(*) 항목은 필수입니다. 에디터 필드에서는 Ctrl+V로 이미지를 붙여넣을 수 있어요.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div class="column q-gutter-sm" style="pointer-events:none;max-width:420px">
                <q-input outlined dense model-value="" placeholder="요청 제목 *" />
                <q-input outlined dense model-value="" placeholder="요청 부서 *" />
                <q-input outlined dense model-value="" placeholder="대상 시스템 *" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">첨부파일을 추가하고 제출합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">참고 자료(최대 20MB)를 첨부한 뒤 [접수하기]를 누르세요. 지금 바로 제출하기 어렵다면 [임시저장]을 눌러두세요.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div class="row q-gutter-sm" style="pointer-events:none">
                <q-btn color="primary" no-caps label="접수하기" icon="send" />
                <q-btn flat color="grey-7" no-caps label="임시저장" icon="save" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">임시저장 후 다시 접수 화면에 들어오면 상단 배너에서 이어서 작성할 수 있어요!</span>
      </q-banner>

    </div>

    <!-- ───────────────────────────────────────────────────
         시나리오 2: 진행 상황 확인
    ─────────────────────────────────────────────────────── -->
    <div v-show="activeScenario === 'track'">

      <q-card flat bordered class="scenario-header q-mb-lg">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="teal" text-color="white" class="text-weight-bold">2</q-avatar>
          <div class="col q-ml-md">
            <div class="text-h6 text-weight-bold">내 SR 진행 상황을 확인하고 싶어요</div>
            <q-badge color="teal-2" text-color="teal-9" label="요청자" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Step 1 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">좌측 메뉴에서 [내 SR]을 클릭합니다</div>
            <div class="text-body2 text-grey-7">내가 접수한 SR 목록이 카드 형태로 표시됩니다.</div>
          </div>
        </div>
      </div>

      <!-- Step 2 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">상태 탭으로 원하는 SR만 골라봅니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">탭을 클릭하면 해당 상태의 SR만 필터링됩니다. 제목·시스템명·SR 번호로 검색도 가능합니다.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div style="pointer-events:none">
                <div class="row q-gutter-xs">
                  <q-btn flat dense no-caps size="sm" color="grey-7" label="전체" />
                  <q-btn flat dense no-caps size="sm" color="grey-5" label="임시저장" />
                  <q-btn flat dense no-caps size="sm" color="primary" label="진행중" />
                  <q-btn flat dense no-caps size="sm" color="orange" label="확인요청" />
                  <q-btn flat dense no-caps size="sm" color="positive" label="완료" />
                  <q-btn flat dense no-caps size="sm" color="negative" label="반려·취소" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="teal" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR 카드를 클릭해 상세 내용을 확인합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">상세 화면은 4개 탭으로 구성됩니다.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">상세 화면 탭 구성</div>
              <div class="row q-gutter-sm" style="pointer-events:none">
                <div class="column items-center q-gutter-xs">
                  <q-badge color="primary" label="요청내용" />
                  <div class="text-caption text-grey-6">접수 시 입력한 내용</div>
                </div>
                <div class="column items-center q-gutter-xs">
                  <q-badge color="teal" label="처리·증적" />
                  <div class="text-caption text-grey-6">승인·배정·완료 결과</div>
                </div>
                <div class="column items-center q-gutter-xs">
                  <q-badge color="orange" label="댓글·문의" />
                  <div class="text-caption text-grey-6">담당자와 소통</div>
                </div>
                <div class="column items-center q-gutter-xs">
                  <q-badge color="grey-6" label="이력" />
                  <div class="text-caption text-grey-6">상태 변경 기록</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="positive" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">처리 완료 후 [최종 확인]을 클릭합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">담당자가 처리를 마치면 SR 상태가 [확인요청]으로 바뀝니다. 요청자가 직접 [최종 확인]을 눌러야 SR이 완전히 닫힙니다.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div style="pointer-events:none">
                <q-btn color="positive" no-caps label="최종 확인" icon="check_circle" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">긴급 SR에는 번개 아이콘, 기한이 초과된 SR에는 [지연] 뱃지가 카드에 표시됩니다.</span>
      </q-banner>

    </div>

    <!-- ───────────────────────────────────────────────────
         시나리오 3: SR 검토·처리
    ─────────────────────────────────────────────────────── -->
    <div v-show="activeScenario === 'manage'">

      <q-card flat bordered class="scenario-header q-mb-lg">
        <q-card-section class="row items-center">
          <q-avatar size="40px" color="deep-purple" text-color="white" class="text-weight-bold">3</q-avatar>
          <div class="col q-ml-md">
            <div class="text-h6 text-weight-bold">SR을 검토하고 처리해야 해요</div>
            <q-badge color="deep-purple-2" text-color="deep-purple-9" label="운영팀 (sr_operator / sr_manager)" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Step 1 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">1</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">좌측 메뉴에서 [SR 관리]를 클릭합니다</div>
            <div class="text-body2 text-grey-7">접수된 모든 SR과 통계 현황을 한눈에 볼 수 있습니다.</div>
          </div>
        </div>
      </div>

      <!-- Step 2 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">2</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">통계 카드로 현황을 파악합니다</div>
            <div class="text-body2 text-grey-7 q-mb-sm">상단 통계 카드 8개에서 전체 현황을 빠르게 파악하세요.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-xs">화면 예시</div>
              <div class="row q-gutter-sm" style="pointer-events:none">
                <q-card flat bordered style="min-width:80px">
                  <q-card-section class="q-pa-sm text-center">
                    <q-icon name="inbox" color="primary" size="20px" />
                    <div class="text-caption">전체</div>
                    <div class="text-h6 text-weight-bold text-primary">24</div>
                  </q-card-section>
                </q-card>
                <q-card flat bordered style="min-width:80px">
                  <q-card-section class="q-pa-sm text-center">
                    <q-icon name="pending" color="orange" size="20px" />
                    <div class="text-caption">진행중</div>
                    <div class="text-h6 text-weight-bold text-orange">8</div>
                  </q-card-section>
                </q-card>
                <q-card flat bordered style="min-width:80px">
                  <q-card-section class="q-pa-sm text-center">
                    <q-icon name="check_circle" color="positive" size="20px" />
                    <div class="text-caption">완료</div>
                    <div class="text-h6 text-weight-bold text-positive">12</div>
                  </q-card-section>
                </q-card>
                <q-card flat bordered style="min-width:80px">
                  <q-card-section class="q-pa-sm text-center">
                    <q-icon name="schedule" color="negative" size="20px" />
                    <div class="text-caption">지연</div>
                    <div class="text-h6 text-weight-bold text-negative">4</div>
                  </q-card-section>
                </q-card>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">3</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">[접수] 탭에서 새 SR을 열어 검토합니다</div>
            <div class="text-body2 text-grey-7">SR을 클릭하면 상세 화면이 열립니다. 요청 내용을 확인하고 [승인] 또는 [반려]를 선택하세요. 반려 시에는 반드시 사유를 입력해야 합니다.</div>
          </div>
        </div>
      </div>

      <!-- Step 4 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">4</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">승인 후 담당자를 배정하고 처리 기간을 설정합니다</div>
            <div class="text-body2 text-grey-7">배정 다이얼로그에서 담당자와 처리 시작일·완료 예정일을 지정합니다. 예상 공수(주말 제외)가 자동으로 계산됩니다.</div>
          </div>
        </div>
      </div>

      <!-- Step 5 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="deep-purple" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">5</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">처리를 완료하고 요청자에게 확인을 요청합니다</div>
            <div class="text-body2 text-grey-7">처리 내용(증적)을 입력하고 상태를 [처리완료]로 변경하면 요청자에게 확인 요청 알림이 전송됩니다.</div>
          </div>
        </div>
      </div>

      <!-- Step 6: 상태 흐름 -->
      <div class="step-row q-mb-lg">
        <div class="row items-start q-gutter-md">
          <q-avatar size="32px" color="grey-6" text-color="white" class="step-num text-caption text-weight-bold flex-shrink-0">6</q-avatar>
          <div class="col">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">SR 상태 흐름 전체 보기</div>
            <div class="text-body2 text-grey-7 q-mb-sm">SR은 아래 순서로 상태가 변경되며, 보류·반려·취소로 분기될 수 있습니다.</div>
            <div class="mock-screen">
              <div class="text-caption text-grey-5 q-mb-sm">상태 흐름</div>
              <div class="row items-center q-gutter-xs flex-wrap" style="pointer-events:none">
                <q-badge color="blue-3" text-color="blue-9" label="접수" />
                <q-icon name="arrow_forward" color="grey-5" size="14px" />
                <q-badge color="orange-3" text-color="orange-9" label="검토중" />
                <q-icon name="arrow_forward" color="grey-5" size="14px" />
                <q-badge color="primary" text-color="white" label="처리중" />
                <q-icon name="arrow_forward" color="grey-5" size="14px" />
                <q-badge color="teal-3" text-color="teal-9" label="처리완료" />
                <q-icon name="arrow_forward" color="grey-5" size="14px" />
                <q-badge color="deep-orange-3" text-color="deep-orange-9" label="확인중" />
                <q-icon name="arrow_forward" color="grey-5" size="14px" />
                <q-badge color="positive" text-color="white" label="최종완료" />
              </div>
              <div class="row q-gutter-sm q-mt-sm" style="pointer-events:none">
                <q-badge color="grey-4" text-color="grey-8" label="보류 (일시 중단)" />
                <q-badge color="red-3" text-color="red-9" label="반려 (승인 거부)" />
                <q-badge color="grey-6" text-color="white" label="취소 (요청자 취소)" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <q-banner rounded class="bg-amber-1">
        <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
        <span class="text-amber-9">[지연] 탭에서 희망 완료일이 초과된 SR을 별도로 모아 집중 관리할 수 있어요. 필터(요청부서·유형·중요도·긴급·내 배정)를 활용하면 원하는 SR을 빠르게 찾을 수 있습니다.</span>
      </q-banner>

    </div>

  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeScenario = ref('submit')
</script>

<style scoped>
.scenario-header {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.step-row {
  padding-left: 8px;
  border-left: 3px solid #e0e0e0;
  margin-left: 16px;
}

.step-num {
  flex-shrink: 0;
}

.mock-screen {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 8px;
  pointer-events: none;
}
</style>
