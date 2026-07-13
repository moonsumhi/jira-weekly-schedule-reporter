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
          <div class="text-subtitle2 text-weight-bold q-mb-sm">SR 처리 단계</div>
          <div class="row items-center q-mb-md" style="flex-wrap:wrap;gap:4px">
            <template v-for="(s, i) in srFlow" :key="s.label">
              <q-chip :color="s.color" text-color="white" dense class="text-weight-bold">{{ s.label }}</q-chip>
              <q-icon v-if="i < srFlow.length - 1" name="chevron_right" color="grey-4" />
            </template>
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

            <q-timeline-entry title="3단계 · 첨부 파일 추가 (선택)" icon="attach_file" color="grey-5">
              <div class="text-body2 q-mb-sm">참고 자료나 오류 화면 캡처를 첨부하면 담당자가 더 빨리 처리할 수 있습니다.</div>
              <div class="mockup-box">
                <q-icon name="cloud_upload" color="grey-4" size="32px" />
                <div class="text-caption text-grey-5 q-mt-xs">파일을 여기에 끌어다 놓거나 클릭하여 선택</div>
                <div class="text-caption text-grey-4" style="font-size:11px">최대 50MB · 이미지, PDF, Excel 등 지원</div>
              </div>
            </q-timeline-entry>

            <q-timeline-entry title="4단계 · 제출 또는 임시저장" icon="send" color="teal">
              <div class="row q-gutter-sm">
                <q-btn unelevated color="primary" icon="send" label="접수하기" no-caps style="pointer-events:none" />
                <q-btn outline color="grey-7" icon="save" label="임시저장" no-caps style="pointer-events:none" />
              </div>
              <div class="text-caption text-grey-6 q-mt-sm">임시저장 후 나중에 접속하면 이어서 작성할 수 있습니다. 임시저장 SR은 접수 전까지 목록에 나타나지 않습니다.</div>
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

          <q-banner rounded class="bg-green-1">
            <template #avatar><q-icon name="check_circle" color="green-7" /></template>
            <span class="text-green-9 text-body2">처리가 완료되면 담당자가 알림을 보내줍니다. <strong>[최종 확인]</strong> 버튼을 눌러 SR을 닫으세요. 수정이 필요하면 댓글로 요청하세요.</span>
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
  { label: '접수',    color: 'grey-6' },
  { label: '검토 중', color: 'blue' },
  { label: '처리 중', color: 'orange' },
  { label: '처리 완료', color: 'teal' },
  { label: '확인 중', color: 'purple' },
  { label: '최종 완료', color: 'positive' },
]

const srTypes = [
  { label: '시스템 문의', color: 'blue-6' },
  { label: '오류 신고',   color: 'red-6' },
  { label: '데이터 요청', color: 'teal-6' },
  { label: '권한 요청',   color: 'purple-6' },
  { label: '기타',        color: 'grey-6' },
]

const srFields = [
  { icon: 'title',       label: '제목',        required: true,  desc: '요청 내용을 한 줄로 요약합니다.' },
  { icon: 'notes',       label: '상세 내용',   required: true,  desc: '무엇을, 언제, 왜 필요한지 구체적으로 적습니다.' },
  { icon: 'computer',    label: '관련 시스템', required: false, desc: '어떤 시스템과 관련된 요청인지 선택합니다.' },
  { icon: 'event',       label: '희망 처리일', required: false, desc: '언제까지 처리가 필요한지 알려주세요.' },
  { icon: 'bolt',        label: '긴급 여부',   required: false, desc: '긴급 처리가 필요한 경우 체크합니다.' },
]

const myListTabs = [
  { label: '전체', color: 'grey-6',    active: true  },
  { label: '접수', color: 'grey-5',    active: false },
  { label: '처리 중', color: 'orange', active: false },
  { label: '완료', color: 'positive',  active: false },
]

const sampleCards = [
  { srNo: 'SR-2026-0001', title: '운영DB 쿼리 성능 개선 요청',   status: '처리 중', color: 'orange',   urgent: false },
  { srNo: 'SR-2026-0002', title: '배치 작업 오류 확인 및 수정',  status: '접수',    color: 'grey-6',  urgent: true  },
  { srNo: 'SR-2026-0003', title: '신규 사용자 계정 생성 요청',   status: '완료',    color: 'positive', urgent: false },
]

const myListTips = [
  { icon: 'filter_list',  label: '상태 탭 필터',  desc: '전체 / 접수 / 처리 중 / 완료 탭을 클릭하면 해당 상태의 SR만 표시됩니다.' },
  { icon: 'search',       label: '빠른 검색',      desc: '제목, 시스템명, SR 번호로 검색할 수 있습니다.' },
  { icon: 'bolt',         label: '긴급 SR 표시',   desc: '긴급 표시된 SR은 주황색 번개 아이콘으로 구분됩니다.' },
  { icon: 'add_circle',   label: '새 SR 접수',     desc: '오른쪽 상단 [SR 접수] 버튼으로 바로 새 요청을 할 수 있습니다.' },
]

const detailParts = [
  { icon: 'linear_scale', color: 'primary',  title: '진행 상태 표시줄', desc: '화면 상단에 현재 처리 단계가 강조되어 있습니다. 단계가 진행될수록 자동으로 업데이트됩니다.' },
  { icon: 'info',         color: 'teal',     title: 'SR 기본 정보',     desc: '요청 제목, 유형, 관련 시스템, 담당자, 접수일 등 기본 정보를 확인합니다.' },
  { icon: 'forum',        color: 'orange',   title: '댓글 / 소통',       desc: '담당자와 요청자가 댓글로 소통할 수 있습니다. 파일 첨부도 가능합니다.' },
  { icon: 'history',      color: 'purple',   title: '처리 이력',         desc: '상태 변경, 담당자 변경 등 모든 이력이 시간 순서대로 자동 기록됩니다.' },
]

const manageParts = [
  { num: '1', color: 'primary', title: '신규 SR 확인',    desc: '접수 탭에서 새로 들어온 SR을 확인합니다.' },
  { num: '2', color: 'orange',  title: '검토 및 배정',    desc: '담당자를 지정하고 상태를 "검토 중"으로 변경합니다.' },
  { num: '3', color: 'teal',    title: '처리 및 완료',    desc: '처리 완료 후 상태를 "처리 완료"로 변경합니다.' },
  { num: '4', color: 'positive',title: '지연 SR 모니터링', desc: '⏰ 지연 탭에서 기한 초과 SR을 집중 관리합니다.' },
]

const manageFeats = [
  { icon: 'person_add',  color: 'primary',  label: '담당자 배정',    desc: 'SR별로 처리 담당자를 지정하거나 변경할 수 있습니다.' },
  { icon: 'swap_horiz',  color: 'orange',   label: '상태 변경',      desc: 'SR 상태를 단계별로 변경하고 요청자에게 알립니다.' },
  { icon: 'timer_off',   color: 'negative', label: '지연 SR 관리',   desc: '처리 기한이 지난 SR을 별도 탭에서 확인하고 신속히 처리합니다.' },
  { icon: 'download',    color: 'positive', label: 'Excel 내보내기', desc: '전체 SR 목록을 Excel로 다운로드하여 보고에 활용합니다.' },
]

const faqs = [
  { q: 'SR을 접수하고 나서 수정할 수 있나요?',             a: '네! 접수(SUBMITTED) 상태일 때는 요청자가 직접 수정할 수 있습니다. 검토 중 이후 상태에서는 담당자에게 댓글로 수정 요청을 해주세요.' },
  { q: '처리 현황은 어떻게 확인하나요?',                   a: '내 SR 목록에서 해당 SR을 클릭하면 현재 처리 단계를 확인할 수 있습니다. 상태 변경 시 시스템 알림이 발송됩니다.' },
  { q: '긴급 SR은 어떻게 표시하나요?',                    a: 'SR 접수 시 "긴급" 체크박스를 선택하면 목록에서 번개 아이콘으로 표시되어 담당자가 우선 처리할 수 있습니다.' },
  { q: 'SR이 반려되면 어떻게 하나요?',                    a: '반려 사유를 확인하고 내용을 수정하여 다시 접수할 수 있습니다. 반려 사유는 댓글 또는 이력에 기록됩니다.' },
  { q: '임시저장한 SR은 어디서 찾나요?',                   a: 'SR 접수 화면에 다시 들어가면 임시저장된 SR 목록이 상단에 표시됩니다. 클릭하면 이어서 작성할 수 있습니다.' },
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
