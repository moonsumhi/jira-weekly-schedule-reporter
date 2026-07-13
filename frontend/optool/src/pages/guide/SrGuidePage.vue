<template>
  <q-page class="q-pa-md">

    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">📋 SR(서비스 요청) 사용 가이드</div>
        <div class="text-caption text-grey-6">데이터운영팀에 업무를 요청하고 처리하는 방법을 설명합니다.</div>
      </div>
    </div>

    <div class="row q-col-gutter-md">

      <!-- 목차 (왼쪽 고정) -->
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

        <!-- ① SR이란? -->
        <div :id="sections[0]!.id" class="guide-section">
          <div class="section-title"><q-icon name="info" color="primary" class="q-mr-sm" />SR(서비스 요청)이란?</div>

          <q-card flat bordered class="q-mb-md">
            <q-card-section>
              <div class="text-body1 text-weight-medium q-mb-sm">SR은 <span class="text-primary text-weight-bold">Service Request</span>의 약자로, 데이터운영팀에 업무를 공식적으로 요청하는 시스템입니다.</div>
              <div class="text-body2 text-grey-8 q-mb-md">이메일이나 구두로 요청하는 대신 SR 시스템을 사용하면 요청 내용이 체계적으로 기록되고 처리 과정을 실시간으로 확인할 수 있습니다.</div>
              <div class="row q-col-gutter-sm">
                <div v-for="item in srBenefits" :key="item.label" class="col-6 col-sm-3">
                  <q-card flat class="text-center q-pa-md bg-grey-1 rounded-borders">
                    <q-icon :name="item.icon" :color="item.color" size="32px" class="q-mb-sm" />
                    <div class="text-caption text-weight-bold">{{ item.label }}</div>
                    <div class="text-caption text-grey-6" style="font-size:11px">{{ item.desc }}</div>
                  </q-card>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- SR 상태 흐름 -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm">SR 처리 단계 (정상 흐름)</div>
          <div class="row items-center q-mb-sm" style="flex-wrap:wrap;gap:4px">
            <template v-for="(s, i) in srFlow" :key="s.label">
              <q-chip :color="s.color" text-color="white" dense class="text-weight-bold">{{ s.label }}</q-chip>
              <q-icon v-if="i < srFlow.length - 1" name="chevron_right" color="grey-4" />
            </template>
          </div>
          <div class="row items-center q-mb-md" style="flex-wrap:wrap;gap:4px">
            <span class="text-caption text-grey-5 q-mr-xs">분기 상태:</span>
            <q-chip v-for="s in srBranchFlow" :key="s.label" :color="s.color" text-color="white" dense>{{ s.label }}</q-chip>
          </div>
          <q-banner rounded class="bg-blue-1 q-mb-md">
            <template #avatar><q-icon name="info" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">처리 완료 후 <strong>요청자가 직접 "최종 확인"</strong>을 눌러야 SR이 완전히 닫힙니다. 확인 전까지는 담당자가 추가 작업을 할 수 있습니다.</span>
          </q-banner>
        </div>

        <!-- ② SR 접수하기 -->
        <div :id="sections[1]!.id" class="guide-section">
          <div class="section-title"><q-icon name="add_circle" color="primary" class="q-mr-sm" />SR 접수하기</div>

          <div class="text-body2 text-grey-7 q-mb-md">메뉴에서 <strong>SR → SR 접수</strong>를 클릭하거나, 내 SR 목록에서 [SR 접수] 버튼을 눌러 시작합니다.</div>

          <!-- 단계별 -->
          <q-timeline color="primary">
            <q-timeline-entry title="1단계 · 요청 유형 선택" icon="category" color="primary">
              <div class="text-body2 q-mb-sm">어떤 종류의 요청인지 먼저 선택합니다.</div>
              <div class="row q-col-gutter-xs q-mb-sm">
                <div v-for="t in srTypes" :key="t.label" class="col-auto">
                  <q-chip :color="t.color" text-color="white" icon="label" dense>{{ t.label }}</q-chip>
                </div>
              </div>
              <q-banner rounded class="bg-amber-1" style="font-size:13px">
                <template #avatar><q-icon name="lightbulb" color="amber-7" size="18px" /></template>
                유형을 잘 모르겠으면 <strong>"기타"</strong>를 선택해도 괜찮습니다. 담당자가 적절한 유형으로 변경해 줍니다.
              </q-banner>
            </q-timeline-entry>

            <q-timeline-entry title="2단계 · 기본 정보 입력" icon="edit_note" color="primary">
              <div class="row q-col-gutter-sm">
                <div v-for="field in srFields" :key="field.label" class="col-12 col-sm-6">
                  <q-card flat bordered class="q-pa-sm">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <q-icon :name="field.icon" color="primary" size="16px" />
                      <span class="text-caption text-weight-bold">{{ field.label }}</span>
                      <q-badge v-if="field.required" color="negative" label="필수" style="font-size:10px" />
                      <q-badge v-else color="grey-4" text-color="grey-7" label="선택" style="font-size:10px" />
                    </div>
                    <div class="text-caption text-grey-7">{{ field.desc }}</div>
                  </q-card>
                </div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry title="3단계 · 유형별 추가 정보 입력" icon="dynamic_form" color="primary">
              <div class="text-body2 q-mb-sm">1단계에서 선택한 유형에 따라 입력 항목이 달라집니다. 각 유형별 주요 필드 예시:</div>
              <q-card flat bordered class="q-pa-sm q-mb-sm">
                <div class="text-caption text-weight-bold q-mb-xs">유형별 필수 필드 예시</div>
                <div class="row q-gutter-xs" style="flex-wrap:wrap">
                  <div v-for="tf in typeFieldExamples" :key="tf.type" class="col-12 col-sm-6 q-mb-xs">
                    <q-chip :color="tf.color" text-color="white" dense size="sm">{{ tf.type }}</q-chip>
                    <div class="text-caption text-grey-7 q-mt-xs">{{ tf.fields }}</div>
                  </div>
                </div>
              </q-card>
              <q-banner rounded class="bg-blue-1" style="font-size:13px">
                <template #avatar><q-icon name="info" color="blue-7" size="18px" /></template>
                리치 텍스트 에디터를 사용하는 필드에서는 이미지를 <strong>Ctrl+V</strong>로 붙여넣기 할 수 있습니다.
              </q-banner>
            </q-timeline-entry>

            <q-timeline-entry title="4단계 · 첨부 파일 및 제출" icon="send" color="teal">
              <div class="text-body2 q-mb-sm">참고 자료나 오류 화면 캡처를 첨부할 수 있습니다. (최대 20MB, pdf/hwp/docx/xlsx/pptx/zip/jpg/png/gif 지원)</div>
              <div class="row q-gutter-sm q-mb-sm">
                <q-btn unelevated color="primary" icon="send" label="접수하기" no-caps style="pointer-events:none" />
                <q-btn outline color="grey-7" icon="save" label="임시저장" no-caps style="pointer-events:none" />
              </div>
              <div class="text-caption text-grey-6">임시저장 후 나중에 접속하면 이어서 작성할 수 있습니다. SR 접수 화면 진입 시 임시저장 목록이 상단에 표시됩니다.</div>
            </q-timeline-entry>
          </q-timeline>
        </div>

        <!-- ③ 내 SR 확인 -->
        <div :id="sections[2]!.id" class="guide-section">
          <div class="section-title"><q-icon name="list_alt" color="primary" class="q-mr-sm" />내 SR 목록 확인하기</div>

          <div class="text-body2 text-grey-7 q-mb-md">메뉴에서 <strong>SR → 내 SR</strong>을 클릭하면 내가 요청한 모든 SR을 볼 수 있습니다.</div>

          <!-- 목록 화면 모형 -->
          <q-card flat bordered class="q-mb-md">
            <q-card-section class="bg-grey-1 q-pa-sm">
              <div class="text-caption text-weight-bold text-grey-6 q-mb-sm">📱 내 SR 목록 화면</div>
              <div class="row q-gutter-xs q-mb-sm" style="flex-wrap:wrap">
                <q-chip v-for="tab in myListTabs" :key="tab.label"
                  :color="tab.active ? tab.color : 'grey-3'"
                  :text-color="tab.active ? 'white' : 'grey-7'"
                  dense size="sm">{{ tab.label }}</q-chip>
              </div>
              <q-card flat bordered v-for="card in sampleCards" :key="card.srNo" class="q-mb-xs q-pa-sm">
                <div class="row items-center q-gutter-sm">
                  <q-chip :color="card.color" text-color="white" dense size="sm" square>{{ card.status }}</q-chip>
                  <span class="text-caption text-grey-6">{{ card.srNo }}</span>
                  <span class="text-body2 col ellipsis">{{ card.title }}</span>
                  <q-icon v-if="card.urgent" name="bolt" color="orange" size="16px" />
                </div>
              </q-card>
            </q-card-section>
          </q-card>

          <q-list>
            <q-item v-for="tip in myListTips" :key="tip.label" class="q-px-none">
              <q-item-section avatar style="min-width:32px">
                <q-icon :name="tip.icon" color="primary" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2 text-weight-medium">{{ tip.label }}</q-item-label>
                <q-item-label caption class="text-grey-6">{{ tip.desc }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <!-- ④ SR 상세 화면 -->
        <div :id="sections[3]!.id" class="guide-section">
          <div class="section-title"><q-icon name="description" color="primary" class="q-mr-sm" />SR 상세 화면</div>

          <div class="text-body2 text-grey-7 q-mb-md">목록에서 SR을 클릭하면 상세 화면이 열립니다. 여기서 진행 상황을 확인하고 담당자와 소통할 수 있습니다.</div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">탭 구성 (4개)</div>
          <div class="row q-col-gutter-md q-mb-md">
            <div v-for="detail in detailParts" :key="detail.title" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="row items-center q-gutter-sm q-mb-sm">
                    <q-icon :name="detail.icon" :color="detail.color" size="22px" />
                    <span class="text-subtitle2 text-weight-bold">{{ detail.title }}</span>
                  </div>
                  <div class="text-body2 text-grey-8">{{ detail.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">우측 요약 패널 (항상 표시)</div>
          <q-card flat bordered class="q-mb-md">
            <q-card-section>
              <q-list dense>
                <q-item v-for="item in detailSidePanelItems" :key="item" class="q-px-none" style="min-height:28px">
                  <q-item-section avatar style="min-width:24px"><q-icon name="arrow_right" color="grey-5" size="16px" /></q-item-section>
                  <q-item-section class="text-body2 text-grey-8">{{ item }}</q-item-section>
                </q-item>
              </q-list>
              <div class="text-caption text-grey-5 q-mt-sm">희망 완료일은 D-Day 형식으로 표시되며, 3일 이하이면 주황색, 기한 초과이면 빨간색으로 강조됩니다.</div>
            </q-card-section>
          </q-card>

          <q-banner rounded class="bg-green-1">
            <template #avatar><q-icon name="check_circle" color="green-7" /></template>
            <span class="text-green-9 text-body2">처리가 완료되면 담당자가 상태를 "처리 완료"로 변경합니다. 요청자가 <strong>[최종 확인]</strong> 버튼을 눌러야 SR이 완전히 닫힙니다.</span>
          </q-banner>
        </div>

        <!-- ⑤ SR 관리 (담당자용) -->
        <div :id="sections[4]!.id" class="guide-section">
          <div class="section-title"><q-icon name="manage_accounts" color="deep-orange" class="q-mr-sm" />SR 관리 <span class="text-caption text-grey-5">(담당자용)</span></div>

          <q-banner rounded class="bg-orange-1 q-mb-md">
            <template #avatar><q-icon name="admin_panel_settings" color="orange-8" /></template>
            <span class="text-orange-9 text-body2">이 기능은 데이터운영팀 담당자 전용입니다. SR 관리 권한이 있는 계정에서만 보입니다.</span>
          </q-banner>

          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="step in manageParts" :key="step.title" class="col-12 col-sm-6">
              <q-card flat bordered>
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-avatar :color="step.color" text-color="white" size="28px" style="font-size:13px;font-weight:700">{{ step.num }}</q-avatar>
                    <span class="text-body2 text-weight-bold">{{ step.title }}</span>
                  </div>
                  <div class="text-caption text-grey-7">{{ step.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">담당자 주요 기능</div>
          <q-list bordered separator rounded>
            <q-item v-for="feat in manageFeats" :key="feat.label">
              <q-item-section avatar>
                <q-icon :name="feat.icon" :color="feat.color" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2 text-weight-medium">{{ feat.label }}</q-item-label>
                <q-item-label caption>{{ feat.desc }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <!-- 자주 묻는 질문 -->
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

const active = ref('what-is-sr')

const sections = [
  { id: 'what-is-sr',  label: 'SR이란?',         icon: 'info' },
  { id: 'sr-submit',   label: 'SR 접수하기',      icon: 'add_circle' },
  { id: 'sr-my',       label: '내 SR 확인',        icon: 'list_alt' },
  { id: 'sr-detail',   label: 'SR 상세 화면',      icon: 'description' },
  { id: 'sr-manage',   label: 'SR 관리 (담당자)',  icon: 'manage_accounts' },
  { id: 'sr-faq',      label: '자주 묻는 질문',    icon: 'quiz' },
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
const srBenefits = [
  { icon: 'track_changes', color: 'primary',  label: '진행 추적',   desc: '처리 단계를 실시간 확인' },
  { icon: 'history',       color: 'teal',     label: '이력 관리',   desc: '모든 변경 자동 기록' },
  { icon: 'forum',         color: 'orange',   label: '소통',         desc: '댓글로 빠른 의사소통' },
  { icon: 'analytics',     color: 'purple',   label: '통계',         desc: '처리 현황 통계 제공' },
]

const srFlow = [
  { label: '접수',       color: 'grey-6'   },
  { label: '검토 중',    color: 'blue'     },
  { label: '추가 확인',  color: 'orange'   },
  { label: '승인',       color: 'cyan-7'   },
  { label: '배정',       color: 'indigo'   },
  { label: '처리 중',    color: 'primary'  },
  { label: '처리 완료',  color: 'teal'     },
  { label: '확인 중',    color: 'purple'   },
  { label: '최종 완료',  color: 'positive' },
]

const srBranchFlow = [
  { label: '보류',   color: 'grey-7'    },
  { label: '반려',   color: 'negative'  },
  { label: '취소',   color: 'grey-5'    },
]

const srTypes = [
  { label: '개선 요청',   color: 'blue-6'    },
  { label: '오류 신고',   color: 'red-6'     },
  { label: '데이터 요청', color: 'teal-6'    },
  { label: '권한 요청',   color: 'purple-6'  },
  { label: '설정 변경',   color: 'orange-7'  },
  { label: '서버/인프라', color: 'brown-6'   },
  { label: '보안 요청',   color: 'deep-orange-7' },
  { label: '기타',        color: 'grey-6'    },
]

const srFields = [
  { icon: 'title',       label: '요청 제목',    required: true,  desc: '요청 내용을 한 줄로 요약합니다.' },
  { icon: 'business',    label: '요청 부서',    required: true,  desc: '요청자의 소속 부서를 입력합니다.' },
  { icon: 'computer',    label: '대상 시스템',  required: true,  desc: '어떤 시스템에 대한 요청인지 입력합니다.' },
  { icon: 'notes',       label: '요청 배경',    required: false, desc: '왜 이 요청이 필요한지 배경을 설명합니다.' },
  { icon: 'event',       label: '희망 완료일',  required: false, desc: '언제까지 처리가 필요한지 알려주세요.' },
  { icon: 'flag',        label: '중요도',       required: false, desc: '기본값은 MEDIUM(중간)이며 선택 변경 가능합니다.' },
  { icon: 'bolt',        label: '긴급 여부',    required: false, desc: '긴급 토글 활성화 시 긴급 사유 입력이 필수입니다.' },
]

const myListTabs = [
  { label: '전체',     color: 'grey-6',   active: true  },
  { label: '임시저장', color: 'grey-5',   active: false },
  { label: '진행 중',  color: 'primary',  active: false },
  { label: '확인 요청',color: 'orange',   active: false },
  { label: '완료',     color: 'positive', active: false },
  { label: '반려/취소',color: 'negative', active: false },
]

const sampleCards = [
  { srNo: 'SR-2026-0001', title: '운영DB 쿼리 성능 개선 요청',   status: '처리 중', color: 'orange',   urgent: false },
  { srNo: 'SR-2026-0002', title: '배치 작업 오류 확인 및 수정',  status: '접수',    color: 'grey-6',  urgent: true  },
  { srNo: 'SR-2026-0003', title: '신규 사용자 계정 생성 요청',   status: '완료',    color: 'positive', urgent: false },
]

const myListTips = [
  { icon: 'filter_list',  label: '상태 탭 필터',   desc: '전체/임시저장/진행중/확인요청/완료/반려취소 탭으로 SR을 분류해 볼 수 있습니다. 건수가 있는 탭만 표시됩니다.' },
  { icon: 'search',       label: '빠른 검색',       desc: '제목, 관련 시스템명, SR 번호로 검색할 수 있습니다.' },
  { icon: 'bolt',         label: '긴급/지연 뱃지',  desc: '긴급 SR은 주황색 번개 아이콘, 기한 초과 SR은 지연 뱃지로 표시됩니다.' },
  { icon: 'cancel',       label: 'SR 취소',         desc: '완료/취소/반려 상태가 아닌 SR에서 취소 버튼이 활성화됩니다. 취소 시 사유를 입력해야 합니다.' },
  { icon: 'add_circle',   label: '새 SR 접수',      desc: '오른쪽 상단 [SR 접수] 버튼으로 바로 새 요청을 할 수 있습니다.' },
]

const detailParts = [
  { icon: 'description',  color: 'primary',  title: '요청 내용 탭',   desc: '접수 시 입력한 유형별 상세 내용, 첨부파일, 비고 등을 확인합니다.' },
  { icon: 'engineering',  color: 'teal',     title: '처리/증적 탭',   desc: '검토 결과(승인/반려/보류), 담당자 배정 정보, 처리 완료 내용을 확인합니다. 연결된 PM 이슈도 여기서 표시됩니다.' },
  { icon: 'forum',        color: 'orange',   title: '댓글/문의 탭',   desc: '요청자와 담당자가 댓글로 소통합니다. 파일 첨부와 이미지 붙여넣기(Ctrl+V)도 가능합니다. 운영팀은 내부 메모 작성도 가능합니다.' },
  { icon: 'history',      color: 'purple',   title: '이력 탭',         desc: '상태 변경, 담당자 변경 등 모든 이력이 시간 순서대로 자동 기록됩니다.' },
]

const detailSidePanelItems = [
  '요청자 / 부서 / 이메일',
  '대상 시스템',
  '우선순위 / 긴급 여부',
  '접수일 / 희망 완료일 (D-Day 표시)',
  '담당자 / 처리 예정일',
  '최근 이력 최대 3건',
]

const manageParts = [
  { num: '1', color: 'primary',  title: '신규 SR 확인',      desc: '접수(SUBMITTED) 탭에서 새로 들어온 SR을 확인합니다.' },
  { num: '2', color: 'blue',     title: '검토',               desc: 'SR 상세에서 [검토] 버튼으로 결과(승인/반려/보류/추가확인)를 선택합니다.' },
  { num: '3', color: 'indigo',   title: '담당자 배정',        desc: '승인 후 [담당자 배정]에서 담당자, 처리 예정 기간, 배포·보안 검토 여부를 설정합니다.' },
  { num: '4', color: 'teal',     title: '처리 및 완료',       desc: '처리 완료 후 상태를 "처리 완료"로 변경합니다. 요청자가 확인하면 최종 완료됩니다.' },
  { num: '5', color: 'negative', title: '지연 SR 모니터링',   desc: '⏰ 지연 탭에서 기한 초과 SR을 별도로 모아서 확인합니다.' },
  { num: '6', color: 'grey-7',   title: 'Excel 다운로드',     desc: '현재 탭·필터 기준으로 SR 목록을 SR_목록.xlsx 파일로 다운로드합니다.' },
]

const manageFeats = [
  { icon: 'dashboard',    color: 'primary',  label: '통계 카드 (8개)', desc: '전체/진행중/완료/지연/보류/반려/긴급/평균처리(일) 현황을 한눈에 확인합니다.' },
  { icon: 'filter_list',  color: 'teal',     label: '다양한 필터',     desc: '요청부서, 요청자, 요청유형, 관련시스템, 중요도, 긴급 여부, 내 배정 필터를 사용합니다.' },
  { icon: 'person_add',   color: 'blue',     label: '담당자 배정',     desc: '승인 후 배정 다이얼로그에서 처리 기간과 예상 공수(주말 제외 자동 계산)를 설정합니다.' },
  { icon: 'swap_horiz',   color: 'orange',   label: '상태 변경',       desc: '운영팀(sr_operator/sr_manager)은 CLOSED·REJECTED·DRAFT를 제외한 상태를 변경할 수 있습니다.' },
  { icon: 'timer_off',    color: 'negative', label: '⏰ 지연 탭',      desc: '희망 완료일이 지났으나 처리되지 않은 SR을 별도 탭에서 빠르게 확인합니다.' },
  { icon: 'settings',     color: 'grey-7',   label: 'SR 기본 프로젝트 설정 (관리자)', desc: '담당자 배정 시 PM 이슈가 자동 등록될 기본 프로젝트를 설정합니다.' },
]

const typeFieldExamples = [
  { type: '개선 요청',   color: 'blue-6',    fields: '현재문제점, 개선요청내용(에디터), 기대효과, 관련화면/메뉴' },
  { type: '오류 신고',   color: 'red-6',     fields: '오류발생화면, 발생일시, 오류내용, 재현절차(에디터)' },
  { type: '데이터 요청', color: 'teal-6',    fields: '목적, 항목(에디터), 기간, 개인정보포함여부, 제공형식' },
  { type: '권한 요청',   color: 'purple-6',  fields: '대상자, 요청권한, 사유(에디터), 기간(상시/임시/특정기간)' },
  { type: '설정 변경',   color: 'orange-7',  fields: '설정대상, 현재값, 요청값, 변경사유, 서비스중단여부' },
  { type: '서버/인프라', color: 'brown-6',   fields: '대상서버, 작업유형, 요청상세(에디터), 서비스영향여부' },
  { type: '보안 요청',   color: 'deep-orange-7', fields: '보안요청유형, 취약점/보안이슈(에디터), 위험도, 조치기한' },
  { type: '기타',        color: 'grey-6',    fields: '요청상세내용(에디터) 만 입력하면 됩니다.' },
]

const faqs = [
  { q: 'SR을 접수하고 나서 수정할 수 있나요?',         a: '최종 완료(CLOSED) 상태가 아닌 경우 요청자가 직접 수정할 수 있습니다. SR 상세 화면에서 [SR 수정] 버튼을 누르면 내용 수정 화면으로 이동합니다.' },
  { q: '긴급 SR은 어떻게 표시하나요?',                a: 'SR 접수 2단계에서 긴급 토글을 활성화하면 됩니다. 긴급 시 긴급 사유 입력이 필수입니다. 목록에서는 번개 아이콘으로 표시됩니다.' },
  { q: '임시저장한 SR은 어디서 찾나요?',               a: 'SR 접수 화면에 다시 들어가면 상단에 임시저장 목록이 배너로 표시됩니다. 클릭하면 이어서 작성할 수 있습니다. 또는 내 SR 목록의 "임시저장" 탭에서도 확인할 수 있습니다.' },
  { q: 'SR이 반려/보류되면 어떻게 하나요?',            a: '처리/증적 탭에서 반려 사유 또는 보류 사유를 확인할 수 있습니다. 내용을 수정하여 다시 접수하거나, 담당자에게 댓글로 문의하세요.' },
  { q: '담당자 배정은 언제 되나요?',                   a: '검토 결과가 "승인"으로 처리된 후 담당자가 배정됩니다. 배정 시 처리 예정 기간과 예상 공수(주말 제외 자동 계산)가 설정됩니다.' },
  { q: '추가 확인 요청을 받았어요.',                   a: '담당자가 요청 내용을 확인하는 중 추가 정보가 필요한 상태입니다. 댓글/문의 탭에서 담당자 질문을 확인하고 답변해주세요.' },
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
  padding: 24px;
  text-align: center;
  background: #f8fafc;
}
</style>
