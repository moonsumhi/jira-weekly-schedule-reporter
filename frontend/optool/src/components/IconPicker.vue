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
      <q-card style="min-width: 520px; max-width: 600px">
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
import { ref, computed } from 'vue'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>()

const open = ref(false)
const search = ref('')

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
]

const filteredIcons = computed(() => {
  if (!search.value) return icons
  const q = search.value.toLowerCase()
  return icons.filter((i) => i.label.includes(q) || i.cls.includes(q))
})

function select(cls: string) {
  emit('update:modelValue', cls)
  open.value = false
}
</script>
