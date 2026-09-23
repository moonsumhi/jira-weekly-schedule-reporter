<template>
  <q-page class="work-guide-page q-pa-md">
    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">작업 관리 사용 가이드</div>
        <div class="text-caption text-grey-6">작업계획서·작업결과서 등록, Import, 수정 방법</div>
      </div>
    </div>

    <q-card flat bordered class="intro-card q-mb-lg">
      <q-card-section class="row items-center q-col-gutter-lg">
        <div class="col-auto">
          <q-avatar size="56px" color="primary" text-color="white" icon="description" />
        </div>
        <div class="col">
          <div class="text-h6 text-weight-bold">문서를 한 곳에서 관리하세요</div>
          <div class="text-body2 text-grey-7 q-mt-xs">
            문서 유형을 선택하고 새로 작성하거나 기존 HWP·Word 파일을 가져올 수 있습니다.
            Import 후에는 매핑 결과를 확인한 다음 상세 화면에서 양식 그대로 수정합니다.
          </div>
        </div>
        <div class="col-auto">
          <q-btn unelevated color="primary" icon="folder_open" label="작업 관리 열기" to="/job/forms" />
        </div>
      </q-card-section>
    </q-card>

    <div class="row q-col-gutter-md q-mb-lg">
      <div v-for="(item, index) in quickSteps" :key="item.title" class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="quick-card full-height">
          <q-card-section>
            <q-avatar size="32px" color="blue-1" text-color="primary" class="text-weight-bold q-mb-sm">
              {{ index + 1 }}
            </q-avatar>
            <div class="text-subtitle2 text-weight-bold">{{ item.title }}</div>
            <div class="text-body2 text-grey-7 q-mt-xs">{{ item.description }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="text-h6 text-weight-bold q-mb-md">단계별 사용 방법</div>
    <q-list bordered separator class="rounded-borders guide-list">
      <q-expansion-item
        v-for="(section, index) in guideSections"
        :key="section.title"
        :default-opened="index === 0"
        expand-separator
        header-class="guide-section-header"
      >
        <template #header>
          <q-item-section avatar>
            <q-avatar size="32px" color="primary" text-color="white" class="text-weight-bold">
              {{ index + 1 }}
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-subtitle1 text-weight-bold">{{ section.title }}</q-item-label>
            <q-item-label caption>{{ section.summary }}</q-item-label>
          </q-item-section>
        </template>

        <q-card flat>
          <q-card-section class="q-pt-none q-pb-lg">
            <div class="row q-col-gutter-md">
              <div v-for="detail in section.details" :key="detail.title" class="col-12 col-md-6">
                <div class="detail-card">
                  <div class="row items-center no-wrap q-mb-xs">
                    <q-icon :name="detail.icon" color="primary" size="20px" class="q-mr-sm" />
                    <div class="text-subtitle2 text-weight-medium">{{ detail.title }}</div>
                  </div>
                  <div class="text-body2 text-grey-7" style="line-height:1.7">{{ detail.description }}</div>
                </div>
              </div>
            </div>
            <q-banner v-if="section.tip" rounded class="bg-amber-1 q-mt-md text-amber-9">
              <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
              {{ section.tip }}
            </q-banner>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>

    <q-card flat bordered class="q-mt-lg help-card">
      <q-card-section class="row items-start q-col-gutter-md">
        <div class="col-auto"><q-icon name="help_outline" color="primary" size="28px" /></div>
        <div class="col">
          <div class="text-subtitle1 text-weight-bold">Import 결과가 예상과 다를 때</div>
          <div class="text-body2 text-grey-7 q-mt-xs" style="line-height:1.7">
            에러 메시지에 표시된 템플릿 위치를 먼저 확인하세요. 원본 표의 열 이름과 현재 템플릿의 항목 이름이 다르면
            매핑되지 않을 수 있습니다. 매핑되지 않은 원본 내용은 가져온 추가 내용에서 확인한 뒤 해당 템플릿 항목에 입력하고 저장합니다.
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
interface QuickStep {
  title: string
  description: string
}

interface GuideDetail {
  title: string
  description: string
  icon: string
}

interface GuideSection {
  title: string
  summary: string
  details: GuideDetail[]
  tip?: string
}

const quickSteps: QuickStep[] = [
  { title: '유형 선택', description: '전체 또는 작업계획서·작업결과서 탭을 선택합니다.' },
  { title: '작성 또는 Import', description: '새 파일을 작성하거나 원본 문서를 가져옵니다.' },
  { title: '매핑 확인', description: '비어 있는 템플릿 항목과 추가 내용을 확인합니다.' },
  { title: '상세에서 수정', description: '문서 양식 그대로 수정하고 저장합니다.' },
]

const guideSections: GuideSection[] = [
  {
    title: '문서 유형을 선택합니다',
    summary: '상단 탭에서 관리할 문서 종류를 빠르게 전환합니다.',
    details: [
      { title: '전체', description: '모든 작업 문서를 한 목록에서 확인합니다. 전체 화면에서 파일 추가나 Import를 시작하면 적용할 템플릿을 선택합니다.', icon: 'view_list' },
      { title: '작업계획서·작업결과서', description: '문서 유형별 목록과 해당 유형의 템플릿 항목을 확인합니다. 목록의 상세 버튼으로 문서를 엽니다.', icon: 'description' },
    ],
  },
  {
    title: '새 문서를 작성합니다',
    summary: '파일 추가 버튼으로 템플릿 기반 문서를 만듭니다.',
    details: [
      { title: '파일 추가', description: '파일 추가를 누르고 사용할 템플릿을 고릅니다. 필수 항목을 채운 뒤 저장하면 작업 문서가 목록에 등록됩니다.', icon: 'add_box' },
      { title: '글과 이미지 입력', description: '에디터가 있는 항목은 글과 이미지를 같은 칸에 함께 넣을 수 있습니다. 이미지를 복사한 뒤 Ctrl+V로 붙여넣거나 드래그해 추가합니다.', icon: 'image' },
      { title: '표와 중첩 내용', description: '표 안의 글·이미지도 같은 에디터에서 입력합니다. 내용이 길어지면 줄바꿈되어 표시됩니다.', icon: 'table_chart' },
    ],
    tip: '작성 중 실수했을 때는 Ctrl+Z로 직전 입력을 되돌릴 수 있습니다.',
  },
  {
    title: '원본 파일을 Import합니다',
    summary: '기존 문서의 내용을 템플릿 항목에 자동으로 배치합니다.',
    details: [
      { title: '지원 파일', description: 'Import 버튼에서 HWP·HWPX·Word 파일을 선택합니다. 전체 화면에서는 먼저 대상 템플릿을 선택합니다.', icon: 'upload_file' },
      { title: '자동 매핑', description: '원본의 섹션·열 이름을 템플릿 항목과 비교해 가능한 값부터 배치합니다. 이름이나 표 구조가 다르면 일부 내용이 추가 영역으로 남을 수 있습니다.', icon: 'sync_alt' },
      { title: '처리 시간', description: '표와 이미지가 많은 문서는 내용 추출과 이미지 저장 과정 때문에 일반 문서보다 시간이 더 걸릴 수 있습니다.', icon: 'hourglass_top' },
    ],
  },
  {
    title: 'Import 결과를 확인합니다',
    summary: '누락된 템플릿 항목과 원본에서 남은 내용을 함께 확인합니다.',
    details: [
      { title: '에러 메시지', description: '매핑에 실패한 경우 에러 메시지 버튼에서 템플릿의 위치를 확인합니다. 예: 작업 결과 > 작업 전 항목이 비어 있습니다.', icon: 'error_outline' },
      { title: '가져온 추가 내용', description: '템플릿에 바로 연결하지 못한 원본 글이나 표를 확인하는 영역입니다. 내용을 복사해 알맞은 템플릿 항목에 입력합니다.', icon: 'content_paste_search' },
      { title: '저장 전 점검', description: '추가 내용과 에러 메시지를 확인하고 필요한 값을 문서 양식에 옮긴 뒤 저장합니다.', icon: 'fact_check' },
    ],
    tip: '작업 결과는 작업 전·작업 후처럼 구분된 항목을 각각 확인해야 합니다.',
  },
  {
    title: '상세 화면에서 수정하고 내려받습니다',
    summary: '목록에서 상세를 연 다음 문서 형태의 수정 화면으로 이동합니다.',
    details: [
      { title: '상세 → 수정', description: '목록에서 상세를 열고 수정 버튼을 누릅니다. 문서 양식의 섹션과 표를 보면서 내용을 편집할 수 있습니다.', icon: 'edit_document' },
      { title: '변경 취소', description: '수정 중 닫기나 뒤로가기를 누르면 저장되지 않은 변경 여부를 확인할 수 있습니다. 필요하면 Ctrl+Z로 입력을 되돌립니다.', icon: 'undo' },
      { title: '다운로드', description: '상세 화면에서 Markdown 보기, 원본 파일 다운로드, 수정본 HWP 내보내기를 사용할 수 있습니다.', icon: 'download' },
    ],
  },
]
</script>

<style scoped>
.intro-card {
  background: linear-gradient(135deg, #f2f6ff 0%, #ffffff 70%);
  border-color: #d9e3f5;
}

.quick-card,
.detail-card,
.help-card {
  border-color: #e2e8f0;
}

.quick-card {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.quick-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(30, 64, 175, 0.08);
}

.guide-list {
  overflow: visible;
}

:deep(.guide-section-header) {
  min-height: 76px;
  padding-top: 12px;
  padding-bottom: 12px;
  scroll-margin-top: 16px;
}

:deep(.guide-section-header .q-item__section--main) {
  min-width: 0;
  white-space: normal;
}

:deep(.guide-section-header .q-item__label) {
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
  line-height: 1.45;
}

.detail-card {
  height: 100%;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafbfc;
}
</style>
