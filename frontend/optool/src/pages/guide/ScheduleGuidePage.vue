<template>
  <q-page class="q-pa-md">

    <div class="row items-center q-mb-lg">
      <q-btn flat round dense icon="arrow_back" class="q-mr-sm" @click="$router.back()" />
      <div>
        <div class="text-h5 text-weight-bold">PM 시스템 사용 가이드</div>
        <div class="text-caption text-grey-6">조직·프로젝트·이슈·스프린트·보드·주간 보고 전체 기능 안내</div>
      </div>
    </div>

    <div class="row q-col-gutter-md">

      <!-- 목차 -->
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

        <!-- ① PM 시스템이란? -->
        <div :id="sections[0]!.id" class="guide-section">
          <div class="section-title"><q-icon name="info" color="primary" class="q-mr-sm" />PM 시스템이란?</div>

          <q-card flat bordered class="q-mb-md">
            <q-card-section>
              <div class="text-body1 text-weight-medium q-mb-sm">
                팀의 조직·프로젝트·이슈·스프린트·보드·주간 보고를 통합 관리하는
                <span class="text-primary text-weight-bold">프로젝트 관리 플랫폼</span>입니다.
              </div>
              <div class="text-body2 text-grey-8 q-mb-md">
                조직 단위로 프로젝트를 만들고, 프로젝트 안에서 이슈를 생성·관리합니다.
                스프린트로 반복 주기를 계획하고, 칸반 보드로 실시간 진행 상황을 파악할 수 있습니다.
              </div>
              <div class="row q-col-gutter-sm">
                <div v-for="m in overviewModules" :key="m.label" class="col-6 col-sm-4 col-md-3">
                  <q-card flat class="q-pa-sm text-center" :style="`background:${m.bg}`">
                    <q-icon :name="m.icon" :color="m.color" size="28px" class="q-mb-xs" />
                    <div class="text-caption text-weight-bold">{{ m.label }}</div>
                  </q-card>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- ② 내 이슈 (대시보드) -->
        <div :id="sections[1]!.id" class="guide-section">
          <div class="section-title"><q-icon name="dashboard" color="primary" class="q-mr-sm" />내 이슈 (대시보드)</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>PM → 내 이슈</strong>를 클릭하면 나와 관련된 이슈를 한눈에 확인할 수 있습니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">그룹 필터 버튼</div>
          <div class="row q-gutter-sm q-mb-md">
            <q-btn v-for="g in dashGroups" :key="g" flat dense no-caps :label="g"
              color="grey-7" style="pointer-events:none" />
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">섹션 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="ds in dashSections" :key="ds.title" class="col-12 col-sm-4">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-badge :color="ds.color" :label="ds.title" />
                  </div>
                  <div class="text-caption text-grey-7">{{ ds.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">이슈 목록 컬럼</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="col in dashColumns" :key="col" outline color="primary" size="sm">{{ col }}</q-chip>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">마감일 표시 방식</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="d in dueDateDisplay" :key="d.label" class="row items-center q-gutter-xs">
              <q-badge :color="d.color" :label="d.label" />
              <span class="text-caption text-grey-7">{{ d.desc }}</span>
            </div>
          </div>

          <q-banner rounded class="bg-blue-1">
            <template #avatar><q-icon name="info" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">이슈를 클릭하면 상세 다이얼로그가 열려 수정·삭제·댓글·첨부파일을 처리할 수 있습니다.</span>
          </q-banner>
        </div>

        <!-- ③ 조직 관리 -->
        <div :id="sections[2]!.id" class="guide-section">
          <div class="section-title"><q-icon name="business" color="teal" class="q-mr-sm" />조직 관리</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            조직은 여러 프로젝트를 묶는 상위 단위입니다. 메뉴에서 <strong>PM → 조직</strong>을 클릭합니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">조직 목록 화면</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="row in orgListFeatures" :key="row.feature">
              <q-item-section avatar style="min-width:120px">
                <q-chip dense color="grey-2" text-color="grey-8" size="sm">{{ row.feature }}</q-chip>
              </q-item-section>
              <q-item-section class="text-caption text-grey-7">{{ row.desc }}</q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">조직 만들기 입력 필드</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="f in orgCreateFields" :key="f.label" class="col-12 col-sm-6">
              <q-card flat bordered class="q-pa-sm">
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <span class="text-caption text-weight-bold">{{ f.label }}</span>
                  <q-badge color="negative" label="필수" style="font-size:10px" />
                </div>
                <div class="text-caption text-grey-7">{{ f.desc }}</div>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">조직 상세 화면</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="row in orgDetailFeatures" :key="row.feature">
              <q-item-section avatar style="min-width:120px">
                <q-chip dense color="grey-2" text-color="grey-8" size="sm">{{ row.feature }}</q-chip>
              </q-item-section>
              <q-item-section class="text-caption text-grey-7">{{ row.desc }}</q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">멤버 역할</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="r in orgRoles" :key="r.role" class="row items-center q-gutter-xs">
              <q-badge :color="r.color" :label="r.role" />
              <span class="text-caption text-grey-7">{{ r.desc }}</span>
            </div>
          </div>

          <q-banner rounded class="bg-amber-1">
            <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
            <span class="text-amber-9 text-body2">조직 삭제 및 멤버 관리(추가·역할 변경·제거)는 <strong>시스템 관리자</strong>만 가능합니다.</span>
          </q-banner>
        </div>

        <!-- ④ 프로젝트 -->
        <div :id="sections[3]!.id" class="guide-section">
          <div class="section-title"><q-icon name="fa-solid fa-diagram-project" color="primary" class="q-mr-sm" />프로젝트</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>PM → 프로젝트</strong>를 클릭하면 전체 프로젝트 목록이 표시됩니다.
            각 카드에서 보드·백로그로 바로 이동할 수 있습니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">새 프로젝트 생성 필드</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="f in projectCreateFields" :key="f.label" class="col-12 col-sm-6">
              <q-card flat bordered class="q-pa-sm">
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <span class="text-caption text-weight-bold">{{ f.label }}</span>
                  <q-badge :color="f.required ? 'negative' : 'grey-4'"
                    :text-color="f.required ? 'white' : 'grey-7'"
                    :label="f.required ? '필수' : '선택'" style="font-size:10px" />
                </div>
                <div class="text-caption text-grey-7">{{ f.desc }}</div>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">프로젝트 상세 탭</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="tab in projectTabs" :key="tab.name" class="col-12 col-sm-4">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="tab.icon" :color="tab.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ tab.name }}</span>
                  </div>
                  <div class="text-caption text-grey-7">{{ tab.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">개요 탭 — 이슈 현황 카드</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-badge v-for="s in projectIssueStatuses" :key="s.label" :color="s.color" :label="s.label" />
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">멤버 탭 — 역할</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="r in projectRoles" :key="r.role" class="row items-center q-gutter-xs">
              <q-badge :color="r.color" :label="r.role" />
              <span class="text-caption text-grey-7">{{ r.desc }}</span>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">설정 탭 기능</div>
          <q-list dense class="q-mb-md">
            <q-item v-for="s in projectSettings" :key="s" class="q-px-none">
              <q-item-section avatar style="min-width:20px"><q-icon name="check" color="positive" size="16px" /></q-item-section>
              <q-item-section class="text-body2">{{ s }}</q-item-section>
            </q-item>
          </q-list>
        </div>

        <!-- ⑤ 이슈 생성 -->
        <div :id="sections[4]!.id" class="guide-section">
          <div class="section-title"><q-icon name="add_task" color="primary" class="q-mr-sm" />이슈 생성</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            보드나 백로그 화면에서 <strong>[이슈 추가]</strong> 버튼을 클릭하면 생성 다이얼로그가 열립니다.
            4개 섹션으로 구성됩니다.
          </div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="sec in issueFormSections" :key="sec.title" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="sec.icon" :color="sec.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ sec.title }}</span>
                  </div>
                  <div class="text-caption text-grey-7">{{ sec.fields }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-sm-6">
              <div class="text-subtitle2 text-weight-bold q-mb-sm">이슈 유형</div>
              <div class="row q-gutter-xs" style="flex-wrap:wrap">
                <div v-for="t in issueTypes" :key="t.label" class="row items-center q-gutter-xs">
                  <q-icon :name="t.icon" :color="t.color" size="16px" />
                  <span class="text-caption">{{ t.label }}</span>
                </div>
              </div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-subtitle2 text-weight-bold q-mb-sm">우선순위</div>
              <div class="row q-gutter-xs" style="flex-wrap:wrap">
                <q-badge v-for="p in issuePriorities" :key="p.label" :color="p.color" :label="p.label" />
              </div>
            </div>
          </div>

          <q-banner rounded class="bg-amber-1 q-mb-md">
            <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
            <span class="text-amber-9 text-body2">
              첨부파일은 파일 버튼 클릭 또는 <strong>드래그 앤 드롭</strong>으로 추가할 수 있습니다.
              보고자는 현재 로그인한 사용자로 자동 설정됩니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑥ 보드 (칸반) -->
        <div :id="sections[5]!.id" class="guide-section">
          <div class="section-title"><q-icon name="fa-solid fa-table-columns" color="primary" class="q-mr-sm" />보드 (칸반)</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            프로젝트 상세에서 <strong>[보드]</strong> 버튼을 클릭합니다.
            이슈를 상태별 컬럼으로 시각화하고 드래그 앤 드롭으로 상태를 변경합니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">상단 컨트롤</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="ctrl in boardControls" :key="ctrl.label" class="col-12 col-sm-6">
              <q-card flat bordered class="q-pa-sm">
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <q-icon :name="ctrl.icon" color="grey-6" size="16px" />
                  <span class="text-caption text-weight-bold">{{ ctrl.label }}</span>
                </div>
                <div class="text-caption text-grey-7">{{ ctrl.desc }}</div>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">칸반 컬럼 (5개)</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-badge v-for="s in boardColumns" :key="s.label" :color="s.color" :label="s.label" />
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">이슈 카드에 표시되는 정보</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="info in boardCardInfo" :key="info" outline color="primary" size="sm">{{ info }}</q-chip>
          </div>

          <q-banner rounded class="bg-blue-1 q-mb-md">
            <template #avatar><q-icon name="info" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">
              이슈 카드를 다른 컬럼으로 드래그하면 상태 변경 확인 다이얼로그가 표시됩니다.
              이슈에 하위작업이 있는 경우 카드 하단에 하위작업 목록도 함께 표시됩니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑦ 백로그 -->
        <div :id="sections[6]!.id" class="guide-section">
          <div class="section-title"><q-icon name="fa-solid fa-list" color="primary" class="q-mr-sm" />백로그</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            프로젝트 상세에서 <strong>[백로그]</strong> 버튼을 클릭합니다.
            Epic → Story/Task/Bug → Sub-task 계층 구조로 이슈를 트리 형태로 표시합니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">필터 항목</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="f in backlogFilters" :key="f" outline color="primary" size="sm">{{ f }}</q-chip>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">트리 구조</div>
          <q-list bordered class="q-mb-md">
            <q-item v-for="row in backlogTree" :key="row.level">
              <q-item-section avatar style="min-width:100px">
                <div class="row items-center q-gutter-xs">
                  <q-icon :name="row.icon" :color="row.color" size="18px" />
                  <span class="text-caption text-weight-bold">{{ row.level }}</span>
                </div>
              </q-item-section>
              <q-item-section class="text-caption text-grey-7">{{ row.desc }}</q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">행 표시 정보</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="info in backlogRowInfo" :key="info" outline color="teal" size="sm">{{ info }}</q-chip>
          </div>

          <q-banner rounded class="bg-purple-1">
            <template #avatar><q-icon name="info" color="purple-7" /></template>
            <span class="text-purple-9 text-body2">
              Epic 행은 연보라 배경으로 구분됩니다.
              Epic·Story/Task 왼쪽의 <q-icon name="chevron_right" size="14px" /> 아이콘을 클릭하면 하위 항목을 접거나 펼칩니다.
              우측 상단 버튼으로 전체 접기/펼치기도 가능합니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑧ 스프린트 -->
        <div :id="sections[7]!.id" class="guide-section">
          <div class="section-title"><q-icon name="fa-solid fa-rotate" color="primary" class="q-mr-sm" />스프린트</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            프로젝트 상세에서 <strong>[스프린트]</strong> 버튼을 클릭합니다.
            스프린트는 반복적인 개발 주기를 나타내며, 이슈 배정 시 활용됩니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">스프린트 상태</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="s in sprintStatuses" :key="s.label" class="row items-center q-gutter-xs">
              <q-badge :color="s.color" :label="s.label" />
              <span class="text-caption text-grey-7">{{ s.desc }}</span>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">스프린트 카드 버튼</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="btn in sprintButtons" :key="btn.label" class="row items-center q-gutter-xs">
              <q-btn flat dense no-caps :icon="btn.icon" :color="btn.color" :label="btn.label"
                size="sm" style="pointer-events:none" />
              <span class="text-caption text-grey-7">{{ btn.cond }}</span>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">생성/수정 입력 필드</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="f in sprintFields" :key="f.label" class="col-12 col-sm-6">
              <q-card flat bordered class="q-pa-sm">
                <div class="row items-center q-gutter-xs q-mb-xs">
                  <span class="text-caption text-weight-bold">{{ f.label }}</span>
                  <q-badge :color="f.required ? 'negative' : 'grey-4'"
                    :text-color="f.required ? 'white' : 'grey-7'"
                    :label="f.required ? '필수' : '선택'" style="font-size:10px" />
                </div>
                <div class="text-caption text-grey-7">{{ f.desc }}</div>
              </q-card>
            </div>
          </div>

          <q-banner rounded class="bg-orange-1">
            <template #avatar><q-icon name="warning" color="orange-8" /></template>
            <span class="text-orange-9 text-body2">
              스프린트를 삭제하면 소속된 이슈는 자동으로 백로그로 이동됩니다.
              한 번에 하나의 스프린트만 <strong>진행 중(ACTIVE)</strong> 상태일 수 있습니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑨ 주간 보고 목록 -->
        <div :id="sections[8]!.id" class="guide-section">
          <div class="section-title"><q-icon name="event_note" color="primary" class="q-mr-sm" />주간 보고 목록</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>스케줄 관리 → 주간 보고</strong>를 클릭하면 생성된 모든 보고서를 볼 수 있습니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">상단 버튼</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="btn in topButtons" :key="btn.label">
              <q-btn :color="btn.color" :icon="btn.icon" :label="btn.label" no-caps unelevated style="pointer-events:none" />
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">목록 테이블 컬럼</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="col in tableColumns" :key="col.name">
              <q-item-section avatar style="min-width:90px">
                <q-chip dense color="grey-2" text-color="grey-8" size="sm">{{ col.name }}</q-chip>
              </q-item-section>
              <q-item-section class="text-caption text-grey-7">{{ col.desc }}</q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">행별 액션 아이콘</div>
          <div class="row q-gutter-sm q-mb-md">
            <q-card v-for="act in rowActions" :key="act.label" flat bordered class="q-pa-sm text-center" style="min-width:80px">
              <q-icon :name="act.icon" :color="act.color" size="22px" />
              <div class="text-caption text-grey-7 q-mt-xs">{{ act.label }}</div>
              <div class="text-caption text-grey-5" style="font-size:10px">{{ act.desc }}</div>
            </q-card>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">보고서 상태</div>
          <div class="row q-gutter-sm q-mb-md">
            <div v-for="s in reportStatuses" :key="s.label" class="row items-center q-gutter-xs">
              <q-badge :color="s.color" :label="s.label" />
              <span class="text-caption text-grey-7">{{ s.desc }}</span>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">새 보고서 생성 방법</div>
          <q-timeline color="primary">
            <q-timeline-entry title="[새 보고서 생성] 버튼 클릭" icon="add_circle" color="primary">
              <div class="text-body2">오른쪽 상단의 파란 버튼을 클릭하면 생성 다이얼로그가 열립니다.</div>
            </q-timeline-entry>
            <q-timeline-entry title="연도·주차 입력" icon="event" color="primary">
              <div class="text-body2 q-mb-sm">연도와 주차를 입력하면 기간(ISO 8601 기준 월~일)과 제목이 자동으로 채워집니다.</div>
              <div class="row q-col-gutter-sm q-mb-xs">
                <div v-for="f in createFields" :key="f.label" class="col-12 col-sm-6">
                  <q-card flat bordered class="q-pa-sm">
                    <div class="row items-center q-gutter-xs q-mb-xs">
                      <span class="text-caption text-weight-bold">{{ f.label }}</span>
                      <q-badge :color="f.required ? 'negative' : 'grey-4'"
                        :text-color="f.required ? 'white' : 'grey-7'"
                        :label="f.required ? '필수' : '자동/선택'" style="font-size:10px" />
                    </div>
                    <div class="text-caption text-grey-7">{{ f.desc }}</div>
                  </q-card>
                </div>
              </div>
            </q-timeline-entry>
            <q-timeline-entry title="[생성 (자동 집계)] 클릭" icon="sync" color="teal">
              <div class="text-body2">확인을 누르면 해당 기간에 등록된 업무를 자동으로 집계합니다. 잠시 기다리면 보고서가 목록에 추가됩니다.</div>
            </q-timeline-entry>
          </q-timeline>
        </div>

        <!-- ⑩ 주간 보고 상세 -->
        <div :id="sections[9]!.id" class="guide-section">
          <div class="section-title"><q-icon name="description" color="primary" class="q-mr-sm" />주간 보고 상세 화면</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            목록에서 <q-icon name="open_in_new" size="14px" /> 상세보기 아이콘을 클릭하면 상세 화면이 열립니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">상단 통계 카드</div>
          <div class="row q-gutter-sm q-mb-md">
            <q-card v-for="s in statCards" :key="s.label" flat bordered class="q-pa-sm text-center" style="min-width:72px">
              <div class="text-h6 text-weight-bold" :class="s.color">{{ s.example }}</div>
              <div class="text-caption text-grey-6">{{ s.label }}</div>
            </q-card>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">상태별 사용 가능한 버튼</div>
          <q-list bordered separator rounded class="q-mb-md">
            <q-item v-for="sb in statusButtons" :key="sb.status">
              <q-item-section avatar>
                <q-badge :color="sb.color" :label="sb.status" />
              </q-item-section>
              <q-item-section>
                <div class="row q-gutter-xs flex-wrap">
                  <q-btn v-for="b in sb.buttons" :key="b.label"
                    :color="b.color" :icon="b.icon" :label="b.label"
                    no-caps unelevated size="sm" style="pointer-events:none" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          <q-banner rounded class="bg-blue-1 q-mb-md">
            <template #avatar><q-icon name="info" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">[미리보기]·[PDF 출력]·[Excel]은 <strong>모든 상태</strong>에서 사용할 수 있습니다.</span>
          </q-banner>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">자동 집계 업무 — 탭 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="tab in detailTabs" :key="tab.name" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="tab.icon" :color="tab.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ tab.name }}</span>
                    <q-badge v-if="tab.cond" outline color="grey-6" :label="tab.cond" style="font-size:10px" />
                  </div>
                  <div class="text-caption text-grey-7">{{ tab.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">수기 항목 섹션 (3개)</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="sec in manualSections" :key="sec.title" class="col-12 col-sm-4">
              <q-card flat bordered class="full-height">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-icon :name="sec.icon" :color="sec.color" size="18px" />
                    <span class="text-body2 text-weight-bold">{{ sec.title }}</span>
                  </div>
                  <div class="text-caption text-grey-7 q-mb-xs">입력 필드:</div>
                  <div class="text-caption text-grey-8">{{ sec.fields }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
          <q-banner rounded class="bg-amber-1 q-mb-md">
            <template #avatar><q-icon name="lightbulb" color="amber-8" /></template>
            <span class="text-amber-9 text-body2">
              각 항목 왼쪽의 <q-icon name="check_circle" color="positive" size="14px" /> 아이콘을 클릭하면 보고서 포함 여부를 토글할 수 있습니다.
              흐리게 표시된 항목은 PDF·Excel에 포함되지 않습니다.
              <br><strong>확정(CONFIRMED) 상태에서는 수기 항목 추가·수정·삭제가 불가합니다.</strong>
            </span>
          </q-banner>
        </div>

        <!-- ⑪ PDF / 미리보기 -->
        <div :id="sections[10]!.id" class="guide-section">
          <div class="section-title"><q-icon name="picture_as_pdf" color="deep-orange" class="q-mr-sm" />PDF 출력 / 미리보기</div>

          <div class="text-body2 text-grey-7 q-mb-md">보고서 상세 화면 상단에서 미리보기 또는 PDF 출력을 선택합니다.</div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="p in pdfOptions" :key="p.btn" class="col-12 col-sm-6">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="row items-center q-gutter-sm q-mb-sm">
                    <q-btn :color="p.color" :icon="p.icon" :label="p.btn" no-caps unelevated size="sm" style="pointer-events:none" />
                  </div>
                  <div class="text-caption text-grey-7">{{ p.desc }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">PDF 출력 내용</div>
          <q-list dense class="q-mb-md">
            <q-item v-for="c in pdfContents" :key="c" class="q-px-none">
              <q-item-section avatar style="min-width:20px"><q-icon name="check" color="positive" size="16px" /></q-item-section>
              <q-item-section class="text-body2">{{ c }}</q-item-section>
            </q-item>
          </q-list>

          <q-banner rounded class="bg-blue-1">
            <template #avatar><q-icon name="lightbulb" color="blue-7" /></template>
            <span class="text-blue-9 text-body2">
              PDF에서 색상이 흰색으로 나온다면 브라우저 인쇄 설정에서 <strong>"배경 그래픽 인쇄"</strong>를 켜주세요.
              Chrome: 인쇄 대화상자 → 더보기 → 배경 그래픽 체크
            </span>
          </q-banner>
        </div>

        <!-- ⑫ 업무 현황 -->
        <div :id="sections[11]!.id" class="guide-section">
          <div class="section-title"><q-icon name="calendar_month" color="teal" class="q-mr-sm" />업무 현황 (캘린더)</div>

          <div class="text-body2 text-grey-7 q-mb-md">
            메뉴에서 <strong>스케줄 관리 → 업무 현황</strong>을 클릭하면 팀 전체 업무를 캘린더로 볼 수 있습니다.
            <strong>TASK · 하위작업(SUB_TASK)</strong> 유형의 이슈만 표시됩니다.
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">담당자 필터</div>
          <q-card flat bordered class="q-mb-md">
            <q-card-section class="q-py-sm">
              <div class="row items-center q-gutter-xs" style="flex-wrap:wrap">
                <span class="text-caption text-grey-5">담당자</span>
                <q-chip dense color="primary" text-color="white" size="sm">전체</q-chip>
                <q-chip v-for="p in sampleAssignees" :key="p.name"
                  dense outline size="sm" :style="`border-color:${p.color};color:${p.color}`">
                  <q-avatar :style="`background:${p.color};color:#fff;font-size:10px`" size="18px">{{ p.name.charAt(0) }}</q-avatar>
                  {{ p.name }}
                </q-chip>
              </div>
            </q-card-section>
          </q-card>
          <q-list dense class="q-mb-md">
            <q-item v-for="t in filterTips" :key="t.label" class="q-px-none">
              <q-item-section avatar style="min-width:20px"><q-icon name="info" color="primary" size="14px" /></q-item-section>
              <q-item-section class="text-caption text-grey-8"><strong>{{ t.label }}:</strong> {{ t.desc }}</q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">캘린더 뷰 구성</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div v-for="v in calViews" :key="v.name" class="col-12 col-sm-4">
              <q-card flat bordered class="text-center q-pa-md">
                <q-icon :name="v.icon" :color="v.color" size="28px" class="q-mb-xs" />
                <div class="text-body2 text-weight-bold q-mb-xs">{{ v.name }}</div>
                <div class="text-caption text-grey-6">{{ v.desc }}</div>
              </q-card>
            </div>
          </div>

          <div class="text-subtitle2 text-weight-bold q-mb-sm">이벤트 클릭 시 팝업 표시 정보</div>
          <div class="row q-gutter-xs q-mb-md" style="flex-wrap:wrap">
            <q-chip v-for="info in popupInfo" :key="info" outline color="teal" size="sm">{{ info }}</q-chip>
          </div>
          <q-banner rounded class="bg-orange-1 q-mb-md">
            <template #avatar><q-icon name="warning" color="orange-8" /></template>
            <span class="text-orange-9 text-body2">마감일이 오늘 이전이고 완료(DONE)가 아닌 업무는 마감일이 <strong>빨간색 + ⚠ 아이콘</strong>으로 표시됩니다.</span>
          </q-banner>

          <q-banner rounded class="bg-teal-1">
            <template #avatar><q-icon name="info" color="teal-7" /></template>
            <span class="text-teal-9 text-body2">
              담당자 필터 변경 시 API를 재호출하지 않고 <strong>로컬에서 즉시 필터링</strong>됩니다.
              기간(월/주)을 이동할 때만 새 데이터를 불러옵니다.
            </span>
          </q-banner>
        </div>

        <!-- ⑬ FAQ -->
        <div :id="sections[12]!.id" class="guide-section">
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

const active = ref('pm-overview')

const sections = [
  { id: 'pm-overview',    label: 'PM 시스템이란?',      icon: 'info' },
  { id: 'dashboard',      label: '내 이슈 (대시보드)',   icon: 'dashboard' },
  { id: 'organizations',  label: '조직 관리',            icon: 'business' },
  { id: 'projects',       label: '프로젝트',             icon: 'folder_open' },
  { id: 'issue-form',     label: '이슈 생성',            icon: 'add_task' },
  { id: 'board',          label: '보드 (칸반)',           icon: 'view_kanban' },
  { id: 'backlog',        label: '백로그',               icon: 'list_alt' },
  { id: 'sprints',        label: '스프린트',             icon: 'loop' },
  { id: 'report-list',    label: '주간 보고 목록',       icon: 'event_note' },
  { id: 'report-detail',  label: '주간 보고 상세',       icon: 'description' },
  { id: 'pdf-print',      label: 'PDF 출력',             icon: 'picture_as_pdf' },
  { id: 'work-status',    label: '업무 현황 캘린더',     icon: 'calendar_month' },
  { id: 'pm-faq',         label: '자주 묻는 질문',       icon: 'quiz' },
]

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function onScroll() {
  for (const sec of [...sections].reverse()) {
    const el = document.getElementById(sec.id)
    if (el && el.getBoundingClientRect().top <= 120) { active.value = sec.id; return }
  }
}
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

// ── 데이터 ──────────────────────────────────────────────────────────────────

const overviewModules = [
  { icon: 'business',             color: 'teal',       bg: '#F0FDFA', label: '조직' },
  { icon: 'folder_open',          color: 'primary',    bg: '#EFF6FF', label: '프로젝트' },
  { icon: 'add_task',             color: 'indigo',     bg: '#EEF2FF', label: '이슈' },
  { icon: 'loop',                 color: 'orange',     bg: '#FFF7ED', label: '스프린트' },
  { icon: 'view_kanban',          color: 'purple',     bg: '#F5F3FF', label: '보드' },
  { icon: 'list_alt',             color: 'blue-grey',  bg: '#F0F4F8', label: '백로그' },
  { icon: 'event_note',           color: 'deep-orange',bg: '#FFF7ED', label: '주간 보고' },
  { icon: 'calendar_month',       color: 'green',      bg: '#F0FDF4', label: '업무 현황' },
]

// 대시보드
const dashGroups = ['전체', '담당 중', '내가 만든']

const dashSections = [
  { title: '담당 중',    color: 'primary', desc: '내가 담당자(assignee)로 배정된 이슈 목록' },
  { title: '내가 만든',  color: 'teal',    desc: '내가 생성한(reporter) 이슈 목록' },
  { title: '프로젝트 현황', color: 'grey-6', desc: '전체 프로젝트별 상태 건수 카드' },
]

const dashColumns = ['유형 아이콘', '키 (프로젝트키-번호)', '요약 (제목)', '우선순위', '상태', '담당자', '마감일']

const dueDateDisplay = [
  { label: 'D-Day',    color: 'warning',  desc: '오늘 마감' },
  { label: 'D-N',      color: 'grey-6',   desc: 'N일 남음' },
  { label: 'D+N',      color: 'negative', desc: 'N일 초과(빨간색 강조)' },
  { label: '-',        color: 'grey-4',   desc: '마감일 없음' },
]

// 조직
const orgListFeatures = [
  { feature: '조직 카드',  desc: '이름, slug, 생성일이 표시됩니다. 카드를 클릭하면 상세 화면으로 이동합니다.' },
  { feature: '조직 만들기', desc: '조직 이름 입력 시 slug가 자동 생성됩니다. slug는 영문 소문자·숫자·하이픈만 허용합니다.' },
  { feature: '삭제',      desc: '시스템 관리자만 카드 우측 하단의 삭제 버튼이 표시됩니다.' },
]

const orgCreateFields = [
  { label: '조직 이름', desc: '화면에 표시될 조직 이름입니다.' },
  { label: 'Slug',     desc: '영문 소문자·숫자·하이픈만 허용. 이름 입력 시 자동 생성됩니다.' },
]

const orgDetailFeatures = [
  { feature: '프로젝트 목록', desc: '조직 내 프로젝트 카드 목록. 클릭 시 프로젝트 상세로 이동합니다.' },
  { feature: '새 프로젝트',  desc: '이름, 키(대문자 영문 2~10자), 설명을 입력해 프로젝트를 생성합니다.' },
  { feature: '멤버 목록',    desc: '조직 멤버를 역할과 함께 표시합니다.' },
  { feature: '멤버 추가',    desc: '사용자 선택 + 역할(ADMIN/MEMBER) 지정. 관리자 전용.' },
  { feature: '이름 수정',    desc: '조직 이름을 변경합니다. 관리자 전용.' },
]

const orgRoles = [
  { role: 'ADMIN',  color: 'deep-orange', desc: '조직 전체 관리 권한' },
  { role: 'MEMBER', color: 'grey-6',      desc: '조직 소속 일반 멤버' },
]

// 프로젝트
const projectCreateFields = [
  { label: '조직',         required: true,  desc: '프로젝트가 속할 조직을 선택합니다.' },
  { label: '프로젝트 이름', required: true,  desc: '화면에 표시될 프로젝트 이름입니다.' },
  { label: '키',           required: true,  desc: '대문자 영문·숫자, 2~10자 (예: PROJ). 이슈 번호 접두사로 사용됩니다.' },
  { label: '설명',         required: false, desc: '프로젝트에 대한 간단한 설명입니다.' },
]

const projectTabs = [
  { name: '개요',  icon: 'info',     color: 'primary',   desc: '이슈 현황 카드·분포 바·프로젝트 정보·활성 스프린트 표시' },
  { name: '멤버',  icon: 'group',    color: 'teal',      desc: '프로젝트 멤버 목록, 역할 변경, 멤버 추가/제거' },
  { name: '설정',  icon: 'settings', color: 'grey-6',    desc: '기본 정보 수정, 라벨 관리, 프로젝트 삭제(관리자 전용)' },
]

const projectIssueStatuses = [
  { label: '백로그',  color: 'grey-5' },
  { label: '할 일',   color: 'blue-4' },
  { label: '진행 중', color: 'orange-6' },
  { label: '검토 중', color: 'purple-5' },
  { label: '완료',    color: 'green-6' },
]

const projectRoles = [
  { role: 'ADMIN',           color: 'primary',    desc: '프로젝트 전체 관리' },
  { role: 'PROJECT_MANAGER', color: 'teal',       desc: 'PM 권한' },
  { role: 'DEVELOPER',       color: 'grey-7',     desc: '개발자 권한' },
  { role: 'VIEWER',          color: 'grey-5',     desc: '읽기 전용' },
]

const projectSettings = [
  '프로젝트 이름·설명 수정',
  '라벨 추가·수정·삭제 (이슈에 태그로 사용)',
  '프로젝트 삭제 — 모든 이슈·스프린트·댓글이 영구 삭제됩니다 (관리자 전용)',
]

// 이슈 생성
const issueFormSections = [
  {
    title: '기본 정보', icon: 'article', color: 'primary',
    fields: '제목(필수), 타입(Epic/Story/Task), 우선순위(최고~최저), 상태',
  },
  {
    title: '담당', icon: 'person', color: 'teal',
    fields: '담당자, 보고자(자동), 상위 Epic(EPIC 제외 시), 스토리 포인트',
  },
  {
    title: '일정', icon: 'calendar_today', color: 'orange',
    fields: '스프린트 선택, 시작일, 마감일',
  },
  {
    title: '기타', icon: 'more_horiz', color: 'grey-6',
    fields: '라벨(다중 선택), 설명, 첨부파일(드래그앤드롭 지원)',
  },
]

const issueTypes = [
  { label: 'Epic',    icon: 'bolt',                     color: 'purple' },
  { label: 'Story',   icon: 'menu_book',                color: 'green' },
  { label: 'Task',    icon: 'check_box_outline_blank',  color: 'primary' },
]

const issuePriorities = [
  { label: '최고', color: 'red-9' }, { label: '높음', color: 'orange' },
  { label: '보통', color: 'grey-6' }, { label: '낮음', color: 'blue-3' }, { label: '최저', color: 'blue-2' },
]

// 보드
const boardControls = [
  { icon: 'loop',         label: '스프린트 선택',    desc: '드롭다운으로 특정 스프린트의 이슈만 표시합니다. 활성 스프린트가 있으면 자동 선택됩니다.' },
  { icon: 'short_text',   label: '제목 보기 토글',   desc: '제목 전체 보기 / 2줄 요약 모드를 전환합니다.' },
  { icon: 'radio_button_checked', label: '상태 칩 필터', desc: '칸반 컬럼을 개별로 표시/숨김 처리합니다. (최소 1개 유지)' },
  { icon: 'add',          label: '이슈 추가',        desc: '선택된 스프린트로 이슈를 생성합니다.' },
]

const boardColumns = [
  { label: '백로그', color: 'grey-5' }, { label: '할 일', color: 'blue-4' },
  { label: '진행 중', color: 'orange-6' }, { label: '검토 중', color: 'purple-5' }, { label: '완료', color: 'green-6' },
]

const boardCardInfo = ['유형 아이콘', '우선순위 아이콘', '이슈번호', '담당자', '제목', '하위작업 목록(있는 경우)']

// 백로그
const backlogFilters = ['이슈 제목 검색', '상태', '우선순위', '유형', '담당자', '필터 초기화']

const backlogTree = [
  { level: 'Epic',        icon: 'bolt',                     color: 'purple',  desc: '최상위 단위. 클릭하면 하위 Story/Task/Bug 목록이 접히거나 펼쳐집니다.' },
  { level: 'Story/Task/Bug', icon: 'check_box_outline_blank', color: 'primary', desc: 'Epic 하위 이슈. 클릭하면 Sub-task 목록을 토글합니다.' },
  { level: 'Sub-task',    icon: 'radio_button_checked',     color: 'teal',    desc: 'Story/Task의 하위 작업 단위.' },
]

const backlogRowInfo = ['유형 아이콘', '이슈키 (프로젝트키-번호)', '제목', '상태', '우선순위', '에픽명(있는 경우)', '담당자']

// 스프린트
const sprintStatuses = [
  { label: '예정',    color: 'grey',     desc: '아직 시작하지 않은 스프린트' },
  { label: '진행 중', color: 'positive', desc: '현재 진행 중인 스프린트' },
  { label: '완료',    color: 'blue',     desc: '종료된 스프린트' },
]

const sprintButtons = [
  { icon: 'play_arrow', color: 'positive', label: '시작',  cond: '예정 상태에서만 표시' },
  { icon: 'stop',       color: 'warning',  label: '종료',  cond: '진행 중 상태에서만 표시' },
  { icon: 'edit',       color: 'grey-6',   label: '수정',  cond: '모든 상태' },
  { icon: 'delete',     color: 'negative', label: '삭제',  cond: '모든 상태 (이슈는 백로그 이동)' },
]

const sprintFields = [
  { label: '이름',  required: true,  desc: '스프린트 이름입니다.' },
  { label: '목표',  required: false, desc: '스프린트 목표를 입력합니다.' },
  { label: '시작일', required: false, desc: '스프린트 시작 날짜입니다.' },
  { label: '종료일', required: false, desc: '스프린트 종료 날짜입니다.' },
]

// 주간 보고
const topButtons = [
  { icon: 'download', label: '목록 Excel', color: 'positive' },
  { icon: 'add',      label: '새 보고서 생성', color: 'primary' },
]

const tableColumns = [
  { name: '주차',      desc: '연도 + 주차 번호 (예: 2026년 28주차)' },
  { name: '기간',      desc: '보고서 기간 (시작일 ~ 종료일)' },
  { name: '제목',      desc: '보고서 제목 (자동 생성 또는 직접 입력)' },
  { name: '상태',      desc: '초안 / 검토중 / 확정' },
  { name: '업무 현황', desc: '전체·완료·진행·지연 건수 뱃지' },
  { name: '완료율',    desc: '완료 건수 / 전체 건수 (프로그레스 바 + %)' },
  { name: '작성자',    desc: '보고서를 생성한 사람' },
  { name: '액션',      desc: '상세보기·수정·재집계·Excel·삭제 아이콘' },
]

const rowActions = [
  { icon: 'open_in_new', color: 'primary',  label: '상세보기', desc: '상세 화면으로 이동' },
  { icon: 'edit',        color: 'grey-7',   label: '수정',     desc: '제목·부서·코멘트 수정' },
  { icon: 'refresh',     color: 'teal',     label: '재집계',   desc: '목록에서 즉시 재집계' },
  { icon: 'download',    color: 'positive', label: 'Excel',   desc: '보고서 1건 Excel 다운' },
  { icon: 'delete',      color: 'negative', label: '삭제',     desc: '보고서 삭제' },
]

const reportStatuses = [
  { label: '초안',   color: 'grey-6',   desc: '작성 중. 재집계·수정 가능' },
  { label: '검토중', color: 'orange',   desc: '검토 단계. 수기 항목 추가 가능' },
  { label: '확정',   color: 'positive', desc: '최종 확정. 수기 항목 수정 불가' },
]

const createFields = [
  { label: '연도',  required: true,  desc: '보고서가 속하는 연도를 입력합니다.' },
  { label: '주차',  required: true,  desc: '보고서 주차를 입력합니다.' },
  { label: '기간',  required: false, desc: '연도·주차를 입력하면 ISO 8601 기준으로 자동 계산됩니다.' },
  { label: '제목',  required: true,  desc: '"N년 N주차 주간 보고" 형식으로 자동 생성됩니다. 직접 수정 가능합니다.' },
  { label: '부서',  required: false, desc: '보고서에 표시할 부서명을 입력합니다.' },
]

const statCards = [
  { label: '총 업무', example: '12', color: 'text-grey-8' },
  { label: '완료',    example: '7',  color: 'text-positive' },
  { label: '진행 중', example: '4',  color: 'text-primary' },
  { label: '지연',    example: '1',  color: 'text-negative' },
  { label: '완료율',  example: '58%',color: 'text-teal' },
]

const statusButtons = [
  {
    status: '초안 (DRAFT)', color: 'grey-6',
    buttons: [
      { label: '재집계',    icon: 'refresh',      color: 'teal' },
      { label: '검토 완료', icon: 'rate_review',  color: 'orange' },
    ],
  },
  {
    status: '검토중 (REVIEWING)', color: 'orange',
    buttons: [
      { label: '보고 확정', icon: 'check_circle', color: 'positive' },
    ],
  },
  {
    status: '확정 (CONFIRMED)', color: 'positive',
    buttons: [
      { label: '확정 해제', icon: 'lock_open', color: 'grey-7' },
    ],
  },
]

const detailTabs = [
  {
    icon: 'folder_open', color: 'primary', name: '프로젝트별', cond: '',
    desc: '프로젝트 단위로 펼침(expansion-item). 각 프로젝트 안에서 완료·진행중·지연·차주계획으로 구분해 이슈 목록을 표시합니다.',
  },
  {
    icon: 'person', color: 'teal', name: '개인별', cond: '',
    desc: '담당자 단위로 펼침(expansion-item). 각 담당자 안에서 완료·진행중·지연·차주계획으로 구분해 이슈 목록을 표시합니다.',
  },
  {
    icon: 'list_alt', color: 'indigo', name: '전체 업무', cond: '',
    desc: '번호·업무명·담당자·우선순위·상태·마감일 컬럼의 테이블로 전체 이슈를 한눈에 봅니다.',
  },
  {
    icon: 'event_upcoming', color: 'grey-6', name: '차주 계획', cond: '차주 이슈 있을 때만',
    desc: '다음 주 예정 업무 목록 테이블입니다. 차주 계획이 없으면 탭이 표시되지 않습니다.',
  },
]

const manualSections = [
  {
    icon: 'task_alt', color: 'blue', title: '주요 안건',
    fields: '제목, 카테고리, 진행상태(예정·진행중·완료·지연·보류), 내용, 담당자',
  },
  {
    icon: 'warning_amber', color: 'orange', title: '특이사항 및 리스크',
    fields: '제목, 유형(itemType), 영향도(낮음·보통·높음), 내용, 대응(actionPlan)',
  },
  {
    icon: 'gavel', color: 'purple', title: '결정 필요 사항',
    fields: '제목, 배경, 선택지, 요청 내용, 희망 결정일',
  },
]

const pdfOptions = [
  {
    btn: '미리보기', icon: 'preview', color: 'primary',
    desc: '인쇄용 레이아웃을 새 탭에서 미리 확인합니다. 자동 인쇄가 실행되지 않으므로 먼저 확인하는 용도로 사용하세요.',
  },
  {
    btn: 'PDF 출력', icon: 'picture_as_pdf', color: 'deep-orange',
    desc: '인쇄용 페이지를 열고 브라우저 인쇄 대화상자를 자동으로 실행합니다. "PDF로 저장"을 선택하면 PDF 파일로 저장됩니다.',
  },
]

const pdfContents = [
  '개인별 업무 간트 차트 (완료·진행·지연·예정 색상 구분)',
  '주요 안건 (포함 체크된 항목만)',
  '특이사항 및 리스크 (포함 체크된 항목만)',
  '결정 필요 사항 (포함 체크된 항목만)',
  '관리자 코멘트 (입력된 경우)',
]

// 업무 현황
const sampleAssignees = [
  { name: '김민준', color: '#1976d2' },
  { name: '이서연', color: '#388e3c' },
  { name: '박도현', color: '#7b1fa2' },
]

const filterTips = [
  { label: '[전체] 클릭',    desc: '모든 담당자의 업무를 표시합니다. 선택된 담당자가 있을 때 클릭하면 선택이 해제됩니다.' },
  { label: '담당자 칩 클릭', desc: '해당 담당자만 표시합니다. 여러 명을 클릭하면 다중 선택됩니다. "N명 선택" 문구가 표시됩니다.' },
  { label: '담당자 색상',    desc: '각 담당자는 고유한 색상(10가지 팔레트)으로 구분됩니다. 캘린더 이벤트와 동일한 색상입니다.' },
]

const calViews = [
  { icon: 'calendar_view_month', color: 'primary', name: '월 보기',   desc: '한 달치 업무를 달력으로 봅니다. (기본 뷰)' },
  { icon: 'calendar_view_week',  color: 'teal',    name: '주 보기',   desc: '한 주치 업무를 상세히 봅니다.' },
  { icon: 'navigate_next',       color: 'grey-6',  name: '기간 이동', desc: 'prev·next 버튼 또는 [오늘] 버튼으로 이동합니다.' },
]

const popupInfo = ['이슈 유형 아이콘', '프로젝트키-번호', '상태 뱃지', '업무 제목', '우선순위', '프로젝트명', '담당자(아바타)', '시작일', '마감일']

const faqs = [
  { q: '조직과 프로젝트의 차이는 무엇인가요?',           a: '조직은 여러 프로젝트를 묶는 상위 단위입니다. 예를 들어 "데이터운영팀"이라는 조직 아래 "신규 시스템 구축", "서비스 운영" 같은 프로젝트를 만들 수 있습니다.' },
  { q: '이슈 키(예: PROJ-5)는 어떻게 생성되나요?',      a: '프로젝트 생성 시 설정한 키(예: PROJ)를 접두사로, 이슈 생성 순서에 따라 번호가 자동으로 부여됩니다.' },
  { q: '백로그와 보드의 차이는 무엇인가요?',             a: '백로그는 Epic→Task→Sub-task 계층 트리 목록으로 전체 이슈를 관리합니다. 보드는 같은 이슈를 상태별 칸반 컬럼으로 표시하여 진행 흐름을 파악하기 편리합니다.' },
  { q: '스프린트에 이슈를 배정하려면?',                  a: '이슈 생성 시 "일정" 섹션에서 스프린트를 선택하거나, 기존 이슈 상세에서 스프린트 필드를 수정하면 됩니다.' },
  { q: '보고서를 생성했는데 업무가 아무것도 안 나와요.', a: '해당 기간에 등록된 이슈가 없거나 이슈의 시작일·마감일 설정이 맞지 않을 수 있습니다. 상세 화면의 [재집계] 버튼을 눌러보고, 그래도 안 나오면 이슈 날짜를 확인해주세요.' },
  { q: '재집계는 언제 가능한가요?',                      a: '보고서 상태가 초안(DRAFT)일 때만 [재집계] 버튼이 활성화됩니다. 검토중·확정 상태에서는 재집계할 수 없습니다. 확정 해제 후 재집계하세요.' },
  { q: '수기 항목을 추가했는데 PDF에 안 나와요.',        a: '항목 왼쪽의 동그라미 아이콘이 흰색이면 보고서에서 제외된 상태입니다. 클릭해서 초록색 체크 아이콘으로 바꾸면 포함됩니다.' },
  { q: '업무 현황 캘린더에서 일부 업무가 안 보여요.',    a: '캘린더에는 TASK·SUB_TASK 유형이면서 시작일 또는 마감일이 있는 이슈만 표시됩니다. 날짜가 없는 이슈는 캘린더에 나타나지 않습니다.' },
  { q: 'PDF 출력 시 색상이 흰색으로 나와요.',           a: '브라우저 인쇄 설정에서 "배경 그래픽 인쇄" 옵션을 켜주세요. Chrome: 인쇄 대화상자 → 더보기 → 배경 그래픽 체크박스 활성화.' },
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
</style>
