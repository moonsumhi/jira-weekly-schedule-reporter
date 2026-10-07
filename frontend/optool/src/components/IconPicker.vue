<template>
  <div>
    <!-- 현재 선택된 아이콘 미리보기 + 열기 버튼 -->
    <div class="row items-center q-gutter-sm">
      <q-btn
        outline
        color="grey-7"
        style="min-width: 120px"
        @click="open = true"
      >
        <q-icon :name="modelValue || 'fa-solid fa-folder'" size="sm" class="q-mr-sm" />
        아이콘 선택
      </q-btn>
      <span v-if="modelValue" class="text-caption text-grey">{{ modelValue }}</span>
    </div>

    <!-- 아이콘 피커 다이얼로그 -->
    <q-dialog v-model="open">
      <q-card style="width: 760px; max-width: calc(100vw - 32px)">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">아이콘 선택</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <q-input
            v-model="search"
            placeholder="아이콘 검색..."
            dense
            outlined
            clearable
            class="q-mb-md"
          >
            <template #prepend>
              <q-icon name="search" />
            </template>
          </q-input>

          <q-scroll-area style="height: 360px">
            <div class="row q-gutter-xs">
              <q-btn
                v-for="icon in filteredIcons"
                :key="icon.cls"
                flat
                dense
                :color="modelValue === icon.cls ? 'primary' : 'grey-7'"
                :class="modelValue === icon.cls ? 'bg-blue-1' : ''"
                style="width: 52px; height: 52px"
                @click="select(icon.cls)"
              >
                <div class="column items-center">
                  <q-icon :name="icon.cls" size="sm" />
                </div>
                <q-tooltip>{{ icon.label }}</q-tooltip>
              </q-btn>
            </div>
            <div v-if="filteredIcons.length === 0" class="text-center text-grey q-pa-lg">
              검색 결과가 없습니다
            </div>
          </q-scroll-area>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>()

const open = ref(false)
const search = ref('')

function closeOnEscape(event: KeyboardEvent) {
  if (!open.value || event.key !== 'Escape') return
  event.preventDefault()
  event.stopPropagation()
  event.stopImmediatePropagation()
  open.value = false
}

watch(open, (isOpen) => {
  if (isOpen) document.addEventListener('keydown', closeOnEscape, true)
  else document.removeEventListener('keydown', closeOnEscape, true)
})

onBeforeUnmount(() => document.removeEventListener('keydown', closeOnEscape, true))

const icons = [
  // 폴더/파일
  { cls: 'fa-solid fa-folder', label: '폴더' },
  { cls: 'fa-solid fa-folder-open', label: '폴더(열림)' },
  { cls: 'fa-solid fa-file', label: '파일' },
  { cls: 'fa-solid fa-file-lines', label: '문서' },
  { cls: 'fa-solid fa-file-alt', label: '파일(텍스트)' },
  { cls: 'fa-solid fa-clipboard', label: '클립보드' },
  { cls: 'fa-solid fa-clipboard-list', label: '클립보드 목록' },
  // 공지/알림
  { cls: 'fa-solid fa-bell', label: '알림' },
  { cls: 'fa-solid fa-bullhorn', label: '공지' },
  { cls: 'fa-solid fa-flag', label: '플래그' },
  { cls: 'fa-solid fa-bookmark', label: '북마크' },
  { cls: 'fa-solid fa-star', label: '별' },
  { cls: 'fa-solid fa-heart', label: '하트' },
  { cls: 'fa-solid fa-tag', label: '태그' },
  // 사람/팀
  { cls: 'fa-solid fa-user', label: '사용자' },
  { cls: 'fa-solid fa-users', label: '팀' },
  { cls: 'fa-solid fa-user-tie', label: '관리자' },
  { cls: 'fa-solid fa-user-gear', label: '사용자 설정' },
  { cls: 'fa-solid fa-id-card', label: 'ID카드' },
  { cls: 'fa-solid fa-address-book', label: '주소록' },
  // 작업/업무
  { cls: 'fa-solid fa-briefcase', label: '작업' },
  { cls: 'fa-solid fa-list-check', label: '체크리스트' },
  { cls: 'fa-solid fa-list', label: '목록' },
  { cls: 'fa-solid fa-table-list', label: '테이블 목록' },
  { cls: 'fa-solid fa-pen-to-square', label: '편집' },
  { cls: 'fa-solid fa-pencil', label: '연필' },
  { cls: 'fa-solid fa-pen', label: '펜' },
  { cls: 'fa-solid fa-check', label: '체크' },
  { cls: 'fa-solid fa-check-double', label: '더블 체크' },
  // 시간/일정
  { cls: 'fa-solid fa-calendar', label: '달력' },
  { cls: 'fa-solid fa-calendar-days', label: '달력(상세)' },
  { cls: 'fa-solid fa-calendar-check', label: '일정 완료' },
  { cls: 'fa-solid fa-clock', label: '시계' },
  { cls: 'fa-solid fa-history', label: '히스토리' },
  { cls: 'fa-solid fa-rotate-left', label: '되돌리기' },
  // 인프라/서버
  { cls: 'fa-solid fa-server', label: '서버' },
  { cls: 'fa-solid fa-database', label: '데이터베이스' },
  { cls: 'fa-solid fa-network-wired', label: '네트워크' },
  { cls: 'fa-solid fa-desktop', label: '데스크탑' },
  { cls: 'fa-solid fa-laptop', label: '노트북' },
  { cls: 'fa-solid fa-computer', label: '컴퓨터' },
  { cls: 'fa-solid fa-hard-drive', label: '하드드라이브' },
  { cls: 'fa-solid fa-microchip', label: '마이크로칩' },
  // 분석/리포트
  { cls: 'fa-solid fa-chart-bar', label: '막대차트' },
  { cls: 'fa-solid fa-chart-line', label: '선차트' },
  { cls: 'fa-solid fa-chart-pie', label: '파이차트' },
  { cls: 'fa-solid fa-chart-area', label: '영역차트' },
  { cls: 'fa-solid fa-table', label: '테이블' },
  { cls: 'fa-solid fa-magnifying-glass', label: '검색' },
  { cls: 'fa-solid fa-magnifying-glass-chart', label: '분석' },
  // 커뮤니케이션
  { cls: 'fa-solid fa-envelope', label: '이메일' },
  { cls: 'fa-solid fa-paper-plane', label: '전송' },
  { cls: 'fa-solid fa-comment', label: '댓글' },
  { cls: 'fa-solid fa-comments', label: '채팅' },
  { cls: 'fa-solid fa-message', label: '메시지' },
  { cls: 'fa-solid fa-inbox', label: '받은함' },
  // 개발/IT
  { cls: 'fa-solid fa-code', label: '코드' },
  { cls: 'fa-solid fa-terminal', label: '터미널' },
  { cls: 'fa-solid fa-bug', label: '버그' },
  { cls: 'fa-solid fa-robot', label: '로봇' },
  { cls: 'fa-solid fa-gears', label: '기어' },
  { cls: 'fa-solid fa-gear', label: '설정' },
  { cls: 'fa-solid fa-wrench', label: '렌치' },
  { cls: 'fa-solid fa-screwdriver-wrench', label: '도구' },
  { cls: 'fa-solid fa-hammer', label: '해머' },
  { cls: 'fa-brands fa-jira', label: 'Jira' },
  { cls: 'fa-brands fa-github', label: 'GitHub' },
  { cls: 'fa-brands fa-slack', label: 'Slack' },
  // 보안
  { cls: 'fa-solid fa-shield', label: '보안' },
  { cls: 'fa-solid fa-shield-halved', label: '보안(반)' },
  { cls: 'fa-solid fa-lock', label: '잠금' },
  { cls: 'fa-solid fa-unlock', label: '잠금해제' },
  { cls: 'fa-solid fa-key', label: '키' },
  { cls: 'fa-solid fa-user-lock', label: '사용자 잠금' },
  // 기타
  { cls: 'fa-solid fa-house', label: '홈' },
  { cls: 'fa-solid fa-link', label: '링크' },
  { cls: 'fa-solid fa-globe', label: '글로벌' },
  { cls: 'fa-solid fa-location-dot', label: '위치' },
  { cls: 'fa-solid fa-map', label: '지도' },
  { cls: 'fa-solid fa-box', label: '박스' },
  { cls: 'fa-solid fa-boxes-stacked', label: '박스 스택' },
  { cls: 'fa-solid fa-archive', label: '아카이브' },
  { cls: 'fa-solid fa-download', label: '다운로드' },
  { cls: 'fa-solid fa-upload', label: '업로드' },
  { cls: 'fa-solid fa-print', label: '인쇄' },
  { cls: 'fa-solid fa-qrcode', label: 'QR코드' },
  { cls: 'fa-solid fa-sitemap', label: '사이트맵' },
  { cls: 'fa-solid fa-circle-info', label: '정보' },
  { cls: 'fa-solid fa-triangle-exclamation', label: '경고' },
  { cls: 'fa-solid fa-circle-check', label: '완료' },
  { cls: 'fa-solid fa-circle-xmark', label: '취소' },
  // 문서/자료
  { cls: 'fa-solid fa-folder-plus', label: '폴더 추가' },
  { cls: 'fa-solid fa-folder-minus', label: '폴더 제거' },
  { cls: 'fa-solid fa-folder-tree', label: '폴더 구조' },
  { cls: 'fa-solid fa-folder-closed', label: '닫힌 폴더' },
  { cls: 'fa-solid fa-file-circle-check', label: '확인된 파일' },
  { cls: 'fa-solid fa-file-circle-plus', label: '새 파일' },
  { cls: 'fa-solid fa-file-pdf', label: 'PDF 문서' },
  { cls: 'fa-solid fa-file-word', label: 'Word 문서' },
  { cls: 'fa-solid fa-file-excel', label: 'Excel 문서' },
  { cls: 'fa-solid fa-file-powerpoint', label: 'PowerPoint 문서' },
  { cls: 'fa-solid fa-file-image', label: '이미지 파일' },
  { cls: 'fa-solid fa-file-code', label: '코드 파일' },
  { cls: 'fa-solid fa-file-zipper', label: '압축 파일' },
  { cls: 'fa-solid fa-file-arrow-down', label: '파일 다운로드' },
  { cls: 'fa-solid fa-book', label: '책' },
  { cls: 'fa-solid fa-book-open', label: '열린 책' },
  { cls: 'fa-solid fa-book-bookmark', label: '자료 북마크' },
  // 업무/프로젝트
  { cls: 'fa-solid fa-clipboard-check', label: '작업 확인' },
  { cls: 'fa-solid fa-clipboard-question', label: '확인 요청' },
  { cls: 'fa-solid fa-clipboard-user', label: '담당 작업' },
  { cls: 'fa-solid fa-square-check', label: '체크 항목' },
  { cls: 'fa-solid fa-list-ol', label: '번호 목록' },
  { cls: 'fa-solid fa-list-ul', label: '글머리 목록' },
  { cls: 'fa-solid fa-diagram-project', label: '프로젝트 흐름' },
  { cls: 'fa-solid fa-arrow-rotate-right', label: '다시 실행' },
  { cls: 'fa-solid fa-arrows-rotate', label: '동기화' },
  { cls: 'fa-solid fa-calendar-plus', label: '일정 추가' },
  { cls: 'fa-solid fa-calendar-minus', label: '일정 제거' },
  { cls: 'fa-solid fa-calendar-day', label: '일별 일정' },
  { cls: 'fa-solid fa-calendar-week', label: '주간 일정' },
  { cls: 'fa-solid fa-calendar-xmark', label: '취소된 일정' },
  { cls: 'fa-solid fa-stopwatch', label: '스톱워치' },
  { cls: 'fa-solid fa-hourglass-half', label: '진행 시간' },
  // 사람/조직
  { cls: 'fa-solid fa-user-plus', label: '사용자 추가' },
  { cls: 'fa-solid fa-user-minus', label: '사용자 제거' },
  { cls: 'fa-solid fa-user-check', label: '사용자 확인' },
  { cls: 'fa-solid fa-user-shield', label: '보안 담당자' },
  { cls: 'fa-solid fa-user-clock', label: '근무자' },
  { cls: 'fa-solid fa-users-gear', label: '팀 설정' },
  { cls: 'fa-solid fa-people-group', label: '조직' },
  { cls: 'fa-solid fa-address-card', label: '연락처 카드' },
  { cls: 'fa-solid fa-building', label: '회사' },
  { cls: 'fa-solid fa-building-columns', label: '기관' },
  { cls: 'fa-solid fa-graduation-cap', label: '교육' },
  // 인프라/운영
  { cls: 'fa-solid fa-cloud', label: '클라우드' },
  { cls: 'fa-solid fa-cloud-arrow-up', label: '클라우드 업로드' },
  { cls: 'fa-solid fa-cloud-arrow-down', label: '클라우드 다운로드' },
  { cls: 'fa-solid fa-cloud-bolt', label: '클라우드 서비스' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-cube|0 0 64 64', label: '3D 등각 큐브' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-cubes|0 0 64 64', label: '3D 큐브 묶음' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-package|0 0 64 64', label: '3D 패키지' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-server|0 0 64 64', label: '3D 서버' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-database|0 0 64 64', label: '3D 데이터베이스' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-network|0 0 64 64', label: '3D 네트워크' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-building|0 0 64 64', label: '3D 건물' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-monitor|0 0 64 64', label: '3D 모니터' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-laptop|0 0 64 64', label: '3D 노트북' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-folder|0 0 64 64', label: '3D 폴더' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-document|0 0 64 64', label: '3D 문서' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-shield|0 0 64 64', label: '3D 보안 방패' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-lock|0 0 64 64', label: '3D 자물쇠' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-calendar|0 0 64 64', label: '3D 달력' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-home|0 0 64 64', label: '3D 홈' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-cloud|0 0 64 64', label: '3D 클라우드' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-mail|0 0 64 64', label: '3D 메일' },
  { cls: 'svguse:/icons/menu-3d.svg#iso-warning|0 0 64 64', label: '3D 경고' },
  { cls: 'fa-solid fa-cube', label: '구성 요소' },
  { cls: 'fa-solid fa-cubes', label: '구성 요소 모음' },
  { cls: 'fa-solid fa-cubes-stacked', label: '겹친 큐브 아이콘' },
  { cls: 'fa-solid fa-shapes', label: '도형 모음' },
  { cls: 'fa-solid fa-dice-d6', label: '다면체 주사위 아이콘' },
  { cls: 'fa-solid fa-dice-d20', label: '다면체 주사위' },
  { cls: 'fa-solid fa-draw-polygon', label: '다각형 도구' },
  { cls: 'fa-solid fa-vector-square', label: '벡터 도형' },
  { cls: 'fa-solid fa-ethernet', label: '유선 네트워크' },
  { cls: 'fa-solid fa-tower-broadcast', label: '방송/신호' },
  { cls: 'fa-solid fa-wifi', label: '무선 네트워크' },
  { cls: 'fa-solid fa-power-off', label: '서비스 전원' },
  { cls: 'fa-solid fa-plug', label: '연결' },
  { cls: 'fa-solid fa-code-branch', label: '브랜치' },
  { cls: 'fa-solid fa-boxes-packing', label: '패키지' },
  { cls: 'fa-solid fa-gauge-high', label: '상태 계기판' },
  { cls: 'fa-solid fa-signal', label: '신호 상태' },
  { cls: 'fa-solid fa-bolt', label: '긴급 작업' },
  { cls: 'fa-solid fa-fire', label: '장애/긴급' },
  // 분석/지원
  { cls: 'fa-solid fa-chart-simple', label: '간단 차트' },
  { cls: 'fa-solid fa-chart-column', label: '세로 막대 차트' },
  { cls: 'fa-solid fa-chart-gantt', label: '간트 차트' },
  { cls: 'fa-solid fa-arrow-trend-up', label: '상승 추세' },
  { cls: 'fa-solid fa-arrow-trend-down', label: '하락 추세' },
  { cls: 'fa-solid fa-filter', label: '필터' },
  { cls: 'fa-solid fa-sliders', label: '조건 설정' },
  { cls: 'fa-solid fa-magnifying-glass-plus', label: '확대 검색' },
  { cls: 'fa-solid fa-magnifying-glass-minus', label: '상세 검색' },
  { cls: 'fa-solid fa-ranking-star', label: '순위' },
  { cls: 'fa-solid fa-headset', label: '고객 지원' },
  { cls: 'fa-solid fa-phone', label: '전화' },
  { cls: 'fa-solid fa-phone-volume', label: '통화 지원' },
  { cls: 'fa-solid fa-ticket', label: '요청 티켓' },
  { cls: 'fa-solid fa-life-ring', label: '도움말' },
  { cls: 'fa-solid fa-lightbulb', label: '아이디어' },
  { cls: 'fa-solid fa-thumbs-up', label: '긍정' },
  { cls: 'fa-solid fa-thumbs-down', label: '부정' },
  { cls: 'fa-solid fa-eye', label: '보기' },
  { cls: 'fa-solid fa-eye-slash', label: '숨기기' },
  { cls: 'fa-solid fa-paperclip', label: '첨부 파일' },
  { cls: 'fa-solid fa-share-nodes', label: '공유' },
  { cls: 'fa-solid fa-arrow-up-right-from-square', label: '새 창에서 열기' },
  { cls: 'fa-solid fa-map-location-dot', label: '위치 정보' },
  { cls: 'fa-solid fa-location-crosshairs', label: '대상 위치' },
  { cls: 'fa-solid fa-route', label: '경로' },
  { cls: 'fa-solid fa-compass', label: '안내' },
  { cls: 'fa-solid fa-circle-exclamation', label: '주의 필요' },
  { cls: 'fa-solid fa-circle-question', label: '질문' },
  { cls: 'fa-solid fa-circle-pause', label: '일시 중지' },
  { cls: 'fa-solid fa-circle-play', label: '시작' },
  { cls: 'fa-solid fa-circle-stop', label: '중지' },
  { cls: 'fa-solid fa-ban', label: '차단' },
  { cls: 'fa-solid fa-shield-heart', label: '보호' },
  { cls: 'fa-solid fa-bug-slash', label: '오류 해결' },
  { cls: 'fa-solid fa-rocket', label: '배포' },
  { cls: 'fa-solid fa-trophy', label: '성과' },
  { cls: 'fa-solid fa-award', label: '우수 사례' },
  { cls: 'fa-solid fa-coins', label: '비용' },
  { cls: 'fa-solid fa-receipt', label: '정산 내역' },
  { cls: 'fa-solid fa-calculator', label: '계산' },
  { cls: 'fa-solid fa-scale-balanced', label: '정책/기준' },
]

const filteredIcons = computed(() => {
  if (!search.value) return icons
  const q = search.value.toLowerCase()
  return icons.filter((i) => i.label.toLowerCase().includes(q) || i.cls.includes(q))
})

function select(cls: string) {
  emit('update:modelValue', cls)
  open.value = false
}
</script>
