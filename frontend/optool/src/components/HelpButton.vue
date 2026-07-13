<template>
  <q-btn
    round flat dense
    icon="help_outline"
    color="grey-6"
    size="sm"
    @click="open = true"
  >
    <q-tooltip>사용 방법</q-tooltip>
  </q-btn>

  <q-dialog v-model="open" position="right" :maximized="false">
    <q-card style="width:380px;max-width:95vw;height:100vh;border-radius:0;display:flex;flex-direction:column">

      <!-- 헤더 -->
      <q-card-section class="row items-center no-wrap q-pb-sm" style="background:#1e293b;color:white">
        <q-icon name="help_outline" size="22px" class="q-mr-sm" />
        <div class="col">
          <div class="text-subtitle1 text-weight-bold">{{ HELP[feature]?.title ?? '사용 방법' }}</div>
          <div class="text-caption" style="opacity:.75">빠른 가이드</div>
        </div>
        <q-btn flat round dense icon="close" color="white" @click="open = false" />
      </q-card-section>

      <q-separator />

      <!-- 내용 -->
      <q-scroll-area class="col">
        <q-card-section class="q-pa-md">

          <!-- 한 줄 설명 -->
          <div class="text-body2 text-grey-8 q-mb-md" style="line-height:1.7">
            {{ HELP[feature]?.summary }}
          </div>

          <!-- 단계별 안내 -->
          <div class="text-caption text-weight-bold text-grey-5 q-mb-sm">📋 주요 기능</div>
          <q-list dense>
            <q-item v-for="(step, i) in HELP[feature]?.steps ?? []" :key="i" class="q-px-none">
              <q-item-section avatar style="min-width:32px">
                <q-avatar size="24px" :color="step.color ?? 'primary'" text-color="white" style="font-size:11px;font-weight:700">
                  {{ i + 1 }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2 text-weight-medium">{{ step.label }}</q-item-label>
                <q-item-label caption class="text-grey-6" style="line-height:1.5">{{ step.desc }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <!-- 팁 -->
          <q-banner v-if="HELP[feature]?.tip" rounded class="bg-amber-1 q-mt-md" style="font-size:13px">
            <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
            <span class="text-amber-9">{{ HELP[feature]?.tip }}</span>
          </q-banner>

        </q-card-section>
      </q-scroll-area>

      <!-- 하단 전체 가이드 링크 -->
      <q-separator />
      <q-card-section class="q-py-sm q-px-md">
        <q-btn
          unelevated color="primary" class="full-width" no-caps
          icon="menu_book" label="전체 가이드에서 자세히 보기"
          :to="guidePath"
          @click="open = false"
        />
      </q-card-section>

    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  feature: string
  guidePath: string
}>()

const open = ref(false)

interface HelpStep { label: string; desc: string; color?: string }
interface HelpContent {
  title: string
  summary: string
  steps: HelpStep[]
  tip?: string
}

const HELP: Record<string, HelpContent> = {

  // ── SR ──────────────────────────────────────────────────────────────
  'sr-new': {
    title: 'SR 접수',
    summary: '데이터운영팀에 업무를 요청하는 화면입니다. 4단계를 따라가면 누구나 쉽게 접수할 수 있어요.',
    steps: [
      { label: '1단계: 요청 유형 선택', desc: '개선 요청, 오류 신고, 데이터 요청, 권한 요청, 설정 변경, 서버/인프라, 보안 요청, 기타 중 선택합니다.', color: 'primary' },
      { label: '2단계: 기본 정보 입력', desc: '요청 제목(필수), 요청 부서(필수), 대상 시스템(필수), 요청 배경, 희망 완료일, 중요도, 긴급 여부를 입력합니다.', color: 'primary' },
      { label: '3단계: 유형별 추가 정보', desc: '선택한 유형에 따라 다른 입력 필드가 나타납니다. 에디터 필드에서는 Ctrl+V로 이미지 붙여넣기가 가능합니다.', color: 'primary' },
      { label: '4단계: 첨부 및 제출', desc: '참고 자료를 첨부(최대 20MB)하고 [접수하기]를 누릅니다. 나중에 이어 작성하려면 [임시저장]을 누르세요.', color: 'teal' },
    ],
    tip: '임시저장 후 다시 접수 화면에 들어오면 상단 배너에서 이어서 작성할 수 있어요!',
  },

  'sr-my': {
    title: '내 SR 목록',
    summary: '내가 접수한 SR의 현재 진행 상태를 한눈에 볼 수 있습니다.',
    steps: [
      { label: '탭으로 필터', desc: '전체 / 임시저장 / 진행중 / 확인요청 / 완료 / 반려·취소 탭에서 원하는 SR만 골라볼 수 있습니다.', color: 'primary' },
      { label: 'SR 검색', desc: '제목·관련 시스템명·SR 번호로 빠르게 검색할 수 있습니다.', color: 'primary' },
      { label: 'SR 클릭 → 상세 확인', desc: '카드를 클릭하면 처리 현황, 담당자, 댓글을 볼 수 있습니다.', color: 'primary' },
      { label: 'SR 취소', desc: '완료/취소/반려 상태가 아닌 SR에서 취소 버튼이 표시됩니다. 취소 사유를 입력해야 합니다.', color: 'orange' },
    ],
    tip: '긴급 SR은 번개 아이콘, 기한 초과 SR은 지연 뱃지로 표시됩니다.',
  },

  'sr-manage': {
    title: 'SR 관리',
    summary: '접수된 모든 SR을 담당자가 검토·배정·처리하는 화면입니다. (운영팀 전용)',
    steps: [
      { label: '10개 탭으로 상태 관리', desc: '접수·검토중·처리중·처리완료·확인중·최종완료·보류·반려·지연 탭으로 SR을 분류해 봅니다.', color: 'primary' },
      { label: '통계 카드 8개', desc: '전체/진행중/완료/지연/보류/반려/긴급/평균처리일을 카드로 한눈에 확인합니다.', color: 'teal' },
      { label: '⏰ 지연 탭', desc: '희망 완료일이 지났으나 처리되지 않은 SR을 별도 탭에서 집중 관리합니다.', color: 'negative' },
      { label: 'Excel 내보내기', desc: '현재 탭·필터 기준으로 SR_목록.xlsx 파일을 다운로드할 수 있습니다.', color: 'positive' },
    ],
    tip: '필터(요청부서·요청자·유형·시스템·중요도·긴급·내 배정)를 조합해 원하는 SR만 빠르게 찾을 수 있어요.',
  },

  'sr-detail': {
    title: 'SR 상세',
    summary: 'SR의 요청 내용, 처리 증적, 댓글, 이력을 4개 탭으로 확인하고 소통합니다.',
    steps: [
      { label: '요청내용 탭', desc: '접수 시 입력한 유형별 상세 내용과 첨부파일을 확인합니다.', color: 'primary' },
      { label: '처리/증적 탭', desc: '검토 결과(승인/반려/보류), 담당자 배정 정보, 처리 완료 내용을 확인합니다.', color: 'teal' },
      { label: '댓글/문의 탭', desc: '요청자와 담당자가 댓글로 소통합니다. 파일 첨부와 이미지 붙여넣기(Ctrl+V)도 가능합니다.', color: 'orange' },
      { label: '이력 탭', desc: '상태 변경, 담당자 변경 등 모든 이력이 자동으로 기록됩니다.', color: 'grey-6' },
    ],
    tip: '처리 완료 후 요청자가 [최종 확인] 버튼을 눌러야 SR이 완전히 닫힙니다.',
  },

  // ── 스케줄 관리 ──────────────────────────────────────────────────────
  'weekly-report': {
    title: '주간 보고',
    summary: '팀의 주간 업무를 스케줄 관리 시스템에서 자동으로 취합하여 보고서를 생성하고 관리합니다.',
    steps: [
      { label: '보고서 생성', desc: '[생성 (자동 집계)] 버튼 클릭 후 연도·주차를 입력하면 제목과 기간이 자동 생성되고 등록된 업무가 집계됩니다.', color: 'primary' },
      { label: '보고서 클릭 → 상세', desc: '생성된 보고서를 클릭하면 프로젝트별·개인별·전체업무·차주계획 탭으로 현황을 확인합니다.', color: 'primary' },
      { label: '상태 관리', desc: '초안(DRAFT) → 검토중(REVIEWING) → 확정(CONFIRMED) 순으로 보고서 상태를 변경합니다.', color: 'orange' },
      { label: 'PDF / Excel 출력', desc: '[미리보기] 또는 [PDF 출력] 버튼으로 인쇄용 페이지를 열고, [Excel]로 데이터를 다운로드합니다.', color: 'teal' },
    ],
    tip: '초안 상태에서 [재집계] 버튼을 누르면 최신 업무를 다시 불러옵니다.',
  },

  'weekly-report-detail': {
    title: '주간 보고 상세',
    summary: '자동 집계된 업무(4개 탭)와 수기 항목(3개 섹션)을 함께 관리하는 상세 화면입니다.',
    steps: [
      { label: '프로젝트별 탭', desc: '프로젝트 기준으로 완료/진행중/지연 업무를 접이식으로 확인합니다.', color: 'primary' },
      { label: '개인별 탭', desc: '담당자 기준으로 완료/진행중/지연/예정 업무를 확인합니다.', color: 'primary' },
      { label: '수기 항목 추가', desc: '주요 안건 / 특이사항 및 리스크 / 결정 필요 사항을 직접 입력할 수 있습니다. 확정 상태에서는 추가 불가합니다.', color: 'orange' },
      { label: '미리보기 / PDF 출력', desc: '[미리보기]로 인쇄 레이아웃을 먼저 확인하고, [PDF 출력]으로 저장하세요.', color: 'deep-orange' },
    ],
    tip: '수기 항목에서 체크 아이콘을 클릭하면 보고서 포함/제외를 토글할 수 있습니다.',
  },

  'work-status': {
    title: '업무 현황',
    summary: '담당자별 업무 일정을 월/주 캘린더 형식으로 한눈에 볼 수 있습니다.',
    steps: [
      { label: '담당자 필터', desc: '상단 칩을 클릭하여 특정 담당자의 업무만 볼 수 있습니다. 다중 선택도 됩니다.', color: 'primary' },
      { label: '월/주 보기 전환', desc: '캘린더 우측 상단에서 월 보기와 주 보기를 전환할 수 있습니다.', color: 'primary' },
      { label: '이벤트 클릭 → 상세', desc: '캘린더의 업무를 클릭하면 이슈 번호, 마감일, 담당자 정보를 볼 수 있습니다.', color: 'primary' },
      { label: '기간 이동', desc: '이전/다음 버튼으로 원하는 기간을 탐색할 수 있습니다.', color: 'grey-6' },
    ],
    tip: '담당자마다 다른 색상으로 표시되어 누구의 업무인지 쉽게 구분할 수 있어요.',
  },
}
</script>
