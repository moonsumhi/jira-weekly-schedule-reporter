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
    summary: '데이터운영팀에 업무를 요청하는 화면입니다. 단계별 입력만 따라가면 누구나 쉽게 접수할 수 있어요.',
    steps: [
      { label: '요청 유형 선택', desc: '시스템 문의, 오류 신고, 데이터 요청 등 유형을 먼저 고릅니다.', color: 'primary' },
      { label: '기본 정보 입력', desc: '제목, 요청 내용, 관련 시스템, 희망 처리일을 입력합니다.', color: 'primary' },
      { label: '첨부 파일 (선택)', desc: '참고 자료나 화면 캡처를 첨부할 수 있습니다.', color: 'grey-6' },
      { label: '제출 또는 임시저장', desc: '나중에 이어 작성하려면 임시저장을 누르세요.', color: 'teal' },
    ],
    tip: '임시저장 후 나중에 다시 접속하면 이어서 작성할 수 있어요!',
  },

  'sr-my': {
    title: '내 SR 목록',
    summary: '내가 접수한 SR의 현재 진행 상태를 한눈에 볼 수 있습니다.',
    steps: [
      { label: '상태 탭으로 필터', desc: '전체 / 접수 / 처리중 / 완료 탭을 클릭해서 원하는 SR만 골라볼 수 있습니다.', color: 'primary' },
      { label: 'SR 검색', desc: '제목·시스템명·SR번호로 빠르게 검색할 수 있습니다.', color: 'primary' },
      { label: 'SR 클릭 → 상세 확인', desc: '카드를 클릭하면 처리 현황, 담당자, 댓글을 볼 수 있습니다.', color: 'primary' },
      { label: '새 SR 접수', desc: '오른쪽 상단의 [SR 접수] 버튼으로 새 요청을 할 수 있습니다.', color: 'teal' },
    ],
    tip: '긴급 SR은 주황색 번개 아이콘으로 표시됩니다.',
  },

  'sr-manage': {
    title: 'SR 관리',
    summary: '접수된 모든 SR을 담당자가 검토·배정·처리하는 화면입니다.',
    steps: [
      { label: '상태별 탭 확인', desc: '접수 → 검토 중 → 처리 중 → 완료 순서로 SR이 진행됩니다.', color: 'primary' },
      { label: 'SR 클릭 → 상세/처리', desc: 'SR 상세 화면에서 담당자 배정 및 상태를 변경합니다.', color: 'primary' },
      { label: '지연 탭 확인', desc: '처리 기한이 지난 SR은 ⏰ 지연 탭에서 한눈에 확인합니다.', color: 'negative' },
      { label: 'Excel 내보내기', desc: '전체 SR 목록을 Excel 파일로 다운로드할 수 있습니다.', color: 'positive' },
    ],
    tip: '통계 카드에서 전체 현황(접수/처리중/완료/지연)을 한눈에 볼 수 있어요.',
  },

  'sr-detail': {
    title: 'SR 상세',
    summary: 'SR의 상세 내용, 처리 이력, 담당자 소통 내용을 모두 볼 수 있습니다.',
    steps: [
      { label: '상태 흐름 확인', desc: '상단 스텝바에서 현재 처리 단계를 시각적으로 확인할 수 있습니다.', color: 'primary' },
      { label: '댓글로 소통', desc: '담당자·요청자 모두 댓글로 의견을 주고받을 수 있습니다. 파일 첨부도 가능합니다.', color: 'primary' },
      { label: '처리 이력 확인', desc: '상태 변경, 담당자 변경 등 모든 이력이 자동으로 기록됩니다.', color: 'grey-6' },
      { label: 'SR 수정/취소', desc: '접수 상태일 때 요청자가 직접 내용을 수정하거나 취소할 수 있습니다.', color: 'orange' },
    ],
    tip: '처리 완료 후 요청자가 "최종 확인" 버튼을 눌러야 SR이 완전히 닫힙니다.',
  },

  // ── 스케줄 관리 ──────────────────────────────────────────────────────
  'weekly-report': {
    title: '주간 보고',
    summary: '팀의 주간 업무를 자동으로 취합하여 보고서를 생성하고 관리합니다.',
    steps: [
      { label: '새 보고서 생성', desc: '[새 보고서 생성] 버튼을 눌러 연도·주차·기간을 입력하면 자동으로 업무가 집계됩니다.', color: 'primary' },
      { label: '보고서 클릭 → 상세', desc: '생성된 보고서를 클릭하면 프로젝트별·개인별 업무 현황을 확인합니다.', color: 'primary' },
      { label: '상태 관리', desc: '초안 → 검토중 → 확정 순서로 보고서 상태를 변경합니다.', color: 'orange' },
      { label: 'PDF 출력 / Excel', desc: '확정된 보고서를 PDF나 Excel로 내보낼 수 있습니다.', color: 'teal' },
    ],
    tip: '재집계 버튼을 누르면 최신 업무 현황을 다시 불러옵니다.',
  },

  'weekly-report-detail': {
    title: '주간 보고 상세',
    summary: '자동 집계된 업무와 수기 항목을 함께 관리하는 상세 화면입니다.',
    steps: [
      { label: '프로젝트별 / 개인별 탭', desc: '탭을 전환하면 프로젝트 기준 또는 담당자 기준으로 업무를 볼 수 있습니다.', color: 'primary' },
      { label: '개인별 탭 = 일정 캘린더', desc: '개인별 탭에서 담당자의 업무를 캘린더로 보여줍니다. 완료/진행/지연을 색으로 구분합니다.', color: 'primary' },
      { label: '수기 항목 추가', desc: '주요 안건, 리스크, 결정 필요 사항을 직접 입력할 수 있습니다.', color: 'orange' },
      { label: '미리보기 / PDF 출력', desc: '미리보기로 인쇄 레이아웃을 먼저 확인하고 PDF로 저장하세요.', color: 'deep-orange' },
    ],
    tip: '개인별 탭의 캘린더에서 이벤트를 클릭하면 업무 상세 정보를 볼 수 있어요.',
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
