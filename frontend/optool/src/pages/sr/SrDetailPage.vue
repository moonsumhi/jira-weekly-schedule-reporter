<template>
  <q-page padding class="sr-detail-page">

    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner size="3rem" color="primary" />
    </div>

    <template v-else-if="sr">

      <!-- ── 헤더 ── -->
      <div class="q-mb-sm">
        <div class="row items-center q-mb-xs">
          <q-btn flat dense round icon="arrow_back" size="sm" @click="$router.back()" class="q-mr-xs" />
          <span class="text-caption text-grey-5 q-mr-xs">{{ sr.srNo }}</span>
          <span class="text-caption text-grey-4">·</span>
          <span class="text-caption text-grey-5 q-ml-xs">{{ fmtDateTime(sr.createdAt) }} 접수</span>
          <q-space />
          <!-- 이전/다음 이동 (목록에서 온 경우) -->
          <template v-if="listIds.length > 1">
            <q-btn flat dense round icon="chevron_left" size="sm" color="grey-6"
              :disable="!prevId" @click="prevId && goToSR(prevId)">
              <q-tooltip>이전 SR</q-tooltip>
            </q-btn>
            <span class="text-caption text-grey-5 q-mx-xs">{{ listIndex + 1 }} / {{ listIds.length }}</span>
            <q-btn flat dense round icon="chevron_right" size="sm" color="grey-6"
              :disable="!nextId" @click="nextId && goToSR(nextId)" class="q-mr-xs">
              <q-tooltip>다음 SR</q-tooltip>
            </q-btn>
          </template>
          <HelpButton feature="sr-detail" guide-path="/pm/sr/guide" />
        </div>
        <div class="text-h5 text-weight-bold q-mb-sm">{{ sr.title }}</div>
        <div class="row items-center q-gutter-xs flex-wrap">
          <q-chip dense size="sm" :color="typeChipColor(sr.requestType)" text-color="white" class="q-ml-none">
            <q-icon :name="typeIcon(sr.requestType)" size="12px" class="q-mr-xs" />
            {{ requestTypeLabel(sr.requestType) }}
          </q-chip>
          <q-chip dense size="sm" :color="statusColor(sr.status)" text-color="white">
            {{ statusLabel(sr.status) }}
          </q-chip>
          <q-chip dense size="sm" :color="priorityChipColor(sr.priority)" text-color="white">
            {{ priorityLabel(sr.priority) }}
          </q-chip>
          <q-chip v-if="dDay !== null" dense size="sm" :color="dDayColor" text-color="white">
            {{ dDayLabel }}
          </q-chip>
          <q-badge v-if="sr.isUrgent" color="red" label="긴급" />
          <q-badge v-if="sr.isDelayed" color="negative" label="지연" />
        </div>
      </div>

      <!-- ── 액션 버튼 ── -->
      <div v-if="actionButtons.length" class="row q-gutter-xs q-mb-md items-center">
        <q-btn
          v-for="btn in actionButtons" :key="btn.key"
          :color="btn.color" :outline="btn.outline"
          :icon="btn.icon" :label="btn.label"
          size="sm" unelevated
          :loading="actionLoading && activeAction === btn.key"
          @click="btn.action()"
        />
        <q-space />
        <q-btn v-if="isAdminUser" flat round icon="download" color="grey-6" size="sm" @click="downloadDetail">
          <q-tooltip>Excel 다운로드</q-tooltip>
        </q-btn>
      </div>

      <!-- ── 본문 2컬럼 ── -->
      <div class="row q-col-gutter-md">

        <!-- 좌측 탭 영역 -->
        <div class="col-12 col-lg-8">
          <q-card flat bordered>
            <q-tabs v-model="activeTab" dense align="left" indicator-color="primary"
              class="text-grey-7 bg-grey-1" active-color="primary" active-bg-color="white">
              <q-tab name="content" icon="description" label="요청 내용" no-caps />
              <q-tab name="process" icon="engineering" label="처리/증적" no-caps />
              <q-tab name="comments" icon="chat_bubble_outline" label="댓글/문의" no-caps>
                <q-badge v-if="comments.length" :label="String(comments.length)"
                  color="primary" floating />
              </q-tab>
              <q-tab name="history" icon="history" label="이력" no-caps />
            </q-tabs>
            <q-separator />

            <q-tab-panels v-model="activeTab" animated>

              <!-- ── 탭1: 요청 내용 ── -->
              <q-tab-panel name="content" class="q-pa-lg q-gutter-lg">

                <!-- 기본 요청 정보 -->
                <div>
                  <div class="tab-section-title q-mb-sm">기본 요청 정보</div>
                  <div class="q-gutter-sm">
                    <div v-if="sr.relatedSystem" class="info-row">
                      <span class="info-row__label">대상 시스템</span>
                      <span class="info-row__value">{{ sr.relatedSystem }}</span>
                    </div>
                    <div v-if="sr.background">
                      <div class="content-label q-mb-xs">요청 배경</div>
                      <div class="content-text pre-wrap bg-grey-1 q-pa-sm rounded-borders">{{ sr.background }}</div>
                    </div>
                  </div>
                </div>

                <!-- 유형별 상세 -->
                <div>
                  <div class="tab-section-title q-mb-sm">
                    <q-icon :name="typeIcon(sr.requestType)" size="15px" color="primary" class="q-mr-xs" />
                    {{ requestTypeLabel(sr.requestType) }} 상세
                  </div>

                  <!-- BUG_FIX -->
                  <template v-if="sr.requestType === 'BUG_FIX'">
                    <div class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">오류 발생 화면</div>
                          <div class="content-text">{{ sr.typeDetail?.errorScreen || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">발생 일시</div>
                          <div class="content-date">
                            <q-icon name="schedule" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDateTime(sr.typeDetail?.occurredAt ?? null) }}
                          </div>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.errorMessage">
                        <div class="content-label">오류 내용</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.errorMessage }}</div>
                      </div>
                      <div v-if="sr.description">
                        <div class="content-label">재현 절차</div>
                        <div class="content-html" v-html="sr.description" />
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">기대 동작</div>
                          <div class="compare-box compare-box--expected pre-wrap">{{ sr.typeDetail?.expectedResult || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">실제 동작</div>
                          <div class="compare-box compare-box--actual pre-wrap">{{ sr.typeDetail?.actualResult || '-' }}</div>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.userEnvironment">
                        <div class="content-label">사용자 환경</div>
                        <div class="content-text">{{ sr.typeDetail.userEnvironment }}</div>
                      </div>
                    </div>
                  </template>

                  <!-- CONFIG_CHANGE -->
                  <template v-else-if="sr.requestType === 'CONFIG_CHANGE'">
                    <div class="q-gutter-sm">
                      <div class="info-row">
                        <span class="info-row__label">설정 대상</span>
                        <span class="info-row__value">{{ sr.typeDetail?.configTarget || '-' }}</span>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">현재 설정값</div>
                          <div class="compare-box compare-box--before pre-wrap">{{ sr.typeDetail?.currentValue || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">변경 요청값</div>
                          <div class="compare-box compare-box--after pre-wrap">{{ sr.typeDetail?.requestedValue || '-' }}</div>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.changeReason">
                        <div class="content-label">변경 사유</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.changeReason }}</div>
                      </div>
                      <div v-if="sr.typeDetail?.impactScope">
                        <div class="content-label">영향 범위</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.impactScope }}</div>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">적용 희망 일시</div>
                          <div class="content-date">
                            <q-icon name="schedule" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDateTime(sr.typeDetail?.applyDatetime ?? null) }}
                          </div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">서비스 중단 여부</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('CONFIG_CHANGE', 'serviceInterruption', sr.typeDetail?.serviceInterruption ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.rollbackPlan">
                        <div class="content-label">롤백 방안</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.rollbackPlan }}</div>
                      </div>
                      <div v-if="sr.typeDetail?.verificationMethod">
                        <div class="content-label">검증 방법</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.verificationMethod }}</div>
                      </div>
                    </div>
                  </template>

                  <!-- DATA_REQUEST -->
                  <template v-else-if="sr.requestType === 'DATA_REQUEST'">
                    <div class="q-gutter-sm">
                      <div v-if="sr.typeDetail?.dataPurpose">
                        <div class="content-label">요청 목적</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.dataPurpose }}</div>
                      </div>
                      <div v-if="sr.description">
                        <div class="content-label">요청 데이터 항목</div>
                        <div class="content-html" v-html="sr.description" />
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">데이터 기간 (시작)</div>
                          <div class="content-date">
                            <q-icon name="event" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDate(sr.typeDetail?.dataPeriodFrom ?? null) }}
                          </div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">데이터 기간 (종료)</div>
                          <div class="content-date">
                            <q-icon name="event" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDate(sr.typeDetail?.dataPeriodTo ?? null) }}
                          </div>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.dataCondition">
                        <div class="content-label">대상 조건</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.dataCondition }}</div>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">제공 형식</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('DATA_REQUEST', 'deliveryFormat', sr.typeDetail?.deliveryFormat ?? null) }}
                          </q-chip>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">제공 방식</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('DATA_REQUEST', 'deliveryMethod', sr.typeDetail?.deliveryMethod ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <!-- 민감 정보 배지 -->
                      <div class="row q-gutter-sm items-center q-mt-xs">
                        <q-chip dense size="sm" class="q-ml-none"
                          :color="sr.typeDetail?.containsPersonalInfo === 'yes' ? 'red-2' : 'grey-2'"
                          :text-color="sr.typeDetail?.containsPersonalInfo === 'yes' ? 'red-9' : 'grey-7'">
                          <q-icon name="person" size="12px" class="q-mr-xs" />
                          개인정보 {{ fieldSelectLabel('DATA_REQUEST', 'containsPersonalInfo', sr.typeDetail?.containsPersonalInfo ?? null) }}
                        </q-chip>
                        <q-chip dense size="sm"
                          :color="sr.typeDetail?.containsSensitiveInfo === 'yes' ? 'orange-2' : 'grey-2'"
                          :text-color="sr.typeDetail?.containsSensitiveInfo === 'yes' ? 'orange-9' : 'grey-7'">
                          <q-icon name="warning" size="12px" class="q-mr-xs" />
                          민감정보 {{ fieldSelectLabel('DATA_REQUEST', 'containsSensitiveInfo', sr.typeDetail?.containsSensitiveInfo ?? null) }}
                        </q-chip>
                      </div>
                      <div v-if="sr.typeDetail?.approver" class="info-row">
                        <span class="info-row__label">승인자</span>
                        <span class="info-row__value">{{ sr.typeDetail.approver }}</span>
                      </div>
                      <div v-if="sr.typeDetail?.retentionDate">
                        <div class="content-label">보관/파기 예정일</div>
                        <div class="content-date">
                          <q-icon name="event" size="13px" color="blue-5" class="q-mr-xs" />
                          {{ fmtDate(sr.typeDetail.retentionDate) }}
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- PERMISSION -->
                  <template v-else-if="sr.requestType === 'PERMISSION'">
                    <div class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">권한 대상자</div>
                          <div class="content-text text-weight-medium">{{ sr.typeDetail?.targetUser || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">요청 권한</div>
                          <div class="content-text text-weight-medium">{{ sr.typeDetail?.requestedPermission || '-' }}</div>
                        </div>
                      </div>
                      <div v-if="sr.description">
                        <div class="content-label">요청 사유</div>
                        <div class="content-html" v-html="sr.description" />
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">권한 사용 기간</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('PERMISSION', 'permissionDuration', sr.typeDetail?.permissionDuration ?? null) }}
                          </q-chip>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div v-if="sr.typeDetail?.permissionExpiry">
                            <div class="content-label">만료일</div>
                            <div class="content-date">
                              <q-icon name="event" size="13px" color="blue-5" class="q-mr-xs" />
                              {{ fmtDate(sr.typeDetail.permissionExpiry) }}
                              <span v-if="permissionExpiryDDay !== null" class="q-ml-xs text-caption"
                                :class="permissionExpiryDDay !== null && permissionExpiryDDay <= 7 ? 'text-negative text-weight-bold' : 'text-grey-5'">
                                ({{ permissionExpiryDDay >= 0 ? 'D-' + permissionExpiryDDay : 'D+' + Math.abs(permissionExpiryDDay) }})
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">승인자</div>
                          <div class="content-text">{{ sr.typeDetail?.approver || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6" v-if="sr.typeDetail?.existingPermission">
                          <div class="content-label">기존 권한 여부</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('PERMISSION', 'existingPermission', sr.typeDetail.existingPermission) }}
                          </q-chip>
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- SERVER_INFRA -->
                  <template v-else-if="sr.requestType === 'SERVER_INFRA'">
                    <div class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">대상 서버/시스템</div>
                          <div class="content-text text-weight-medium">{{ sr.typeDetail?.targetServer || '-' }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">요청 작업 유형</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('SERVER_INFRA', 'workType', sr.typeDetail?.workType ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <div v-if="sr.description">
                        <div class="content-label">요청 상세</div>
                        <div class="content-html" v-html="sr.description" />
                      </div>
                      <div v-if="sr.typeDetail?.resourceInfo">
                        <div class="content-label">리소스 정보</div>
                        <div class="content-text pre-wrap resource-box">{{ sr.typeDetail.resourceInfo }}</div>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">작업 희망 일시</div>
                          <div class="content-date">
                            <q-icon name="schedule" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDateTime(sr.typeDetail?.workDatetime ?? null) }}
                          </div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">서비스 영향 여부</div>
                          <q-chip dense size="sm" class="q-ml-none q-my-none"
                            :color="serviceImpactColor(sr.typeDetail?.serviceImpact ?? null)"
                            text-color="white">
                            {{ fieldSelectLabel('SERVER_INFRA', 'serviceImpact', sr.typeDetail?.serviceImpact ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.backupRequired">
                        <div class="content-label">사전 백업 필요</div>
                        <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                          {{ fieldSelectLabel('SERVER_INFRA', 'backupRequired', sr.typeDetail.backupRequired) }}
                        </q-chip>
                      </div>
                      <div v-if="sr.typeDetail?.verificationMethod">
                        <div class="content-label">작업 후 확인 방법</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.verificationMethod }}</div>
                      </div>
                    </div>
                  </template>

                  <!-- SECURITY -->
                  <template v-else-if="sr.requestType === 'SECURITY'">
                    <div class="q-gutter-sm">
                      <div class="row q-col-gutter-md">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">보안 요청 유형</div>
                          <q-chip dense size="sm" color="blue-1" text-color="blue-9" class="q-ml-none q-my-none">
                            {{ fieldSelectLabel('SECURITY', 'securityRequestType', sr.typeDetail?.securityRequestType ?? null) }}
                          </q-chip>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">위험도</div>
                          <q-chip dense size="sm" class="q-ml-none q-my-none"
                            :color="riskLevelColor(sr.typeDetail?.riskLevel ?? null)" text-color="white">
                            {{ fieldSelectLabel('SECURITY', 'riskLevel', sr.typeDetail?.riskLevel ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <div v-if="sr.description">
                        <div class="content-label">취약점 또는 보안 이슈</div>
                        <div class="content-html" v-html="sr.description" />
                      </div>
                      <div v-if="sr.typeDetail?.requestedAction">
                        <div class="content-label">조치 요청 내용</div>
                        <div class="content-text pre-wrap">{{ sr.typeDetail.requestedAction }}</div>
                      </div>
                      <div class="row q-col-gutter-sm">
                        <div class="col-12 col-sm-6">
                          <div class="content-label">조치 기한</div>
                          <div class="content-date">
                            <q-icon name="event" size="13px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDate(sr.typeDetail?.actionDeadline ?? null) }}
                          </div>
                        </div>
                        <div class="col-12 col-sm-6">
                          <div class="content-label">증적 필요 여부</div>
                          <q-chip dense size="sm" class="q-ml-none q-my-none"
                            :color="sr.typeDetail?.evidenceRequired === 'yes' ? 'orange-2' : 'grey-2'"
                            :text-color="sr.typeDetail?.evidenceRequired === 'yes' ? 'orange-9' : 'grey-7'">
                            {{ fieldSelectLabel('SECURITY', 'evidenceRequired', sr.typeDetail?.evidenceRequired ?? null) }}
                          </q-chip>
                        </div>
                      </div>
                      <div v-if="sr.typeDetail?.diagnosisStandard" class="info-row">
                        <span class="info-row__label">진단 기준</span>
                        <span class="info-row__value">{{ sr.typeDetail.diagnosisStandard }}</span>
                      </div>
                      <div v-if="sr.typeDetail?.evidenceFormat" class="info-row">
                        <span class="info-row__label">증적 양식</span>
                        <span class="info-row__value">{{ sr.typeDetail.evidenceFormat }}</span>
                      </div>
                    </div>
                  </template>

                  <!-- IMPROVEMENT / ETC / 기타 (generic) -->
                  <template v-else>
                    <div class="row q-col-gutter-md">
                      <template v-for="field in currentSRTypeFields" :key="field.key">
                        <div v-if="field.type === 'editor' || fieldValue(field) != null"
                          :class="field.half ? 'col-12 col-sm-6' : 'col-12'">
                          <div class="content-label q-mb-xs">{{ field.label }}</div>
                          <div v-if="field.type === 'editor'" class="content-html" v-html="sr.description" />
                          <div v-else-if="field.type === 'date'" class="content-date">
                            <q-icon name="event" size="14px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDate(fieldValue(field)) }}
                          </div>
                          <div v-else-if="field.type === 'datetime'" class="content-date">
                            <q-icon name="schedule" size="14px" color="blue-5" class="q-mr-xs" />
                            {{ fmtDateTime(fieldValue(field)) }}
                          </div>
                          <q-chip v-else-if="field.type === 'select'"
                            dense size="sm" color="blue-1" text-color="blue-9" class="q-my-none q-ml-none">
                            {{ selectLabel(field, fieldValue(field)) }}
                          </q-chip>
                          <div v-else class="content-text pre-wrap">{{ fieldValue(field) }}</div>
                        </div>
                      </template>
                    </div>
                  </template>
                </div>

                <!-- 비고 -->
                <div v-if="sr.note">
                  <div class="content-label q-mb-xs">비고</div>
                  <div class="content-text pre-wrap">{{ sr.note }}</div>
                </div>

                <!-- 추가 첨부파일 -->
                <div v-if="extraAttachments.length">
                  <div class="tab-section-title q-mb-sm">첨부파일</div>
                  <q-list dense bordered class="rounded-borders">
                    <q-item v-for="att in extraAttachments" :key="att.fileId"
                      clickable tag="a" :href="att.url" target="_blank">
                      <q-item-section avatar>
                        <q-icon :name="fileIcon(att.contentType)" color="blue-6" size="20px" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-primary" style="font-size:0.85rem">{{ att.originalName }}</q-item-label>
                        <q-item-label caption>{{ fmtSize(att.size) }}</q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-icon name="open_in_new" color="grey-4" size="16px" />
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>

              </q-tab-panel>

              <!-- ── 탭2: 처리/증적 ── -->
              <q-tab-panel name="process" class="q-pa-lg q-gutter-lg">

                <!-- 연결된 스케줄 관리 이슈 배너 -->
                <q-banner v-if="sr.convertedIssueId && sr.convertedProjectId" class="bg-indigo-1 rounded-borders q-mb-sm" dense>
                  <template #avatar><q-icon name="link" color="indigo-7" /></template>
                  <span class="text-indigo-9 text-weight-medium">연결된 스케줄 관리 이슈</span>
                  <q-btn flat dense size="sm" color="indigo-7" icon="open_in_new"
                    label="이슈 바로가기" class="q-ml-sm"
                    @click="$router.push(`/pm/projects/${sr.convertedProjectId}/backlog`)" />
                </q-banner>

                <div v-if="!sr.assigneeId && !sr.reviewResult" class="text-center text-grey-5 q-py-xl">
                  <q-icon name="pending_actions" size="3rem" class="q-mb-sm" /><br />
                  아직 처리 정보가 없습니다.
                </div>

                <template v-else>
                  <!-- 검토 정보 -->
                  <div v-if="sr.reviewResult">
                    <div class="tab-section-title q-mb-sm">검토 정보</div>
                    <q-card flat class="bg-grey-1 rounded-borders">
                      <q-card-section class="q-gutter-sm">
                        <div class="row q-col-gutter-md">
                          <div class="col-6">
                            <div class="content-label">검토 결과</div>
                            <q-chip dense size="sm"
                              :color="reviewResultColor(sr.reviewResult)" text-color="white" class="q-ml-none">
                              {{ reviewResultLabel(sr.reviewResult) }}
                            </q-chip>
                          </div>
                          <div class="col-6">
                            <div class="content-label">검토자 · 검토 일시</div>
                            <div class="content-text">{{ sr.reviewerUserName || '-' }} · {{ fmtDateTime(sr.reviewedAt) }}</div>
                          </div>
                        </div>
                        <div v-if="sr.reviewComment">
                          <div class="content-label">검토 의견</div>
                          <div class="content-text pre-wrap">{{ sr.reviewComment }}</div>
                        </div>
                        <q-banner v-if="sr.rejectReason" class="bg-red-1 text-negative rounded-borders" dense>
                          <template #avatar><q-icon name="block" color="negative" /></template>
                          <strong>반려 사유:</strong> {{ sr.rejectReason }}
                        </q-banner>
                        <q-banner v-if="sr.holdReason" class="bg-amber-1 text-amber-9 rounded-borders" dense>
                          <template #avatar><q-icon name="pause_circle" color="amber-8" /></template>
                          <strong>보류 사유:</strong> {{ sr.holdReason }}
                        </q-banner>
                        <q-banner v-if="sr.pendingInfoContent" class="bg-blue-1 text-blue-9 rounded-borders" dense>
                          <template #avatar><q-icon name="help_outline" color="blue-7" /></template>
                          <strong>추가 확인 요청:</strong> {{ sr.pendingInfoContent }}
                        </q-banner>
                      </q-card-section>
                    </q-card>
                  </div>

                  <!-- 처리 정보 -->
                  <div v-if="sr.assigneeId">
                    <div class="tab-section-title q-mb-sm">처리 정보</div>
                    <q-card flat class="bg-grey-1 rounded-borders">
                      <q-card-section>
                        <div class="row q-col-gutter-md">
                          <div class="col-12 col-sm-6">
                            <div class="content-label">담당자</div>
                            <div class="content-text text-weight-medium">{{ sr.assigneeName }}</div>
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">예상 공수</div>
                            <div class="content-text">{{ sr.estimatedEffort || '-' }}</div>
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">처리 예정 기간</div>
                            <div class="content-text">
                              {{ fmtDate(sr.plannedStartDate) }}
                              <template v-if="sr.plannedStartDate && sr.plannedDueDate"> ~ </template>
                              <span :class="sr.isDelayed ? 'text-negative text-weight-medium' : ''">
                                {{ fmtDate(sr.plannedDueDate) }}
                              </span>
                            </div>
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">실제 완료일</div>
                            <div class="content-text" :class="sr.actualCompletedAt ? 'text-positive' : ''">
                              {{ fmtDate(sr.actualCompletedAt) }}
                            </div>
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">배포 필요</div>
                            <q-badge :color="sr.deploymentRequired ? 'orange-7' : 'grey-4'"
                              :text-color="sr.deploymentRequired ? 'white' : 'grey-7'"
                              :label="sr.deploymentRequired ? '배포 필요' : '해당 없음'" />
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">보안 검토 필요</div>
                            <q-badge :color="sr.securityReviewRequired ? 'red-7' : 'grey-4'"
                              :text-color="sr.securityReviewRequired ? 'white' : 'grey-7'"
                              :label="sr.securityReviewRequired ? '보안 검토 필요' : '해당 없음'" />
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">배포</div>
                            <q-badge :color="sr.deployed ? 'positive' : 'grey-4'"
                              :text-color="sr.deployed ? 'white' : 'grey-7'"
                              :label="sr.deployed ? `배포 완료 (${fmtDate(sr.deployedAt)})` : '미배포'" />
                          </div>
                          <div class="col-12 col-sm-6">
                            <div class="content-label">요청자 확인</div>
                            <q-badge :color="sr.requesterConfirmed ? 'positive' : 'grey-4'"
                              :text-color="sr.requesterConfirmed ? 'white' : 'grey-7'"
                              :label="sr.requesterConfirmed ? '확인 완료' : '미확인'" />
                          </div>
                        </div>
                        <div v-if="sr.processResult" class="q-mt-md">
                          <div class="content-label">처리 결과</div>
                          <div class="content-text pre-wrap">{{ sr.processResult }}</div>
                        </div>
                      </q-card-section>
                    </q-card>
                  </div>
                </template>

              </q-tab-panel>

              <!-- ── 탭3: 댓글/문의 ── -->
              <q-tab-panel name="comments" class="q-pa-lg">

                <div v-if="!comments.length" class="text-center text-grey-5 q-py-xl">
                  <q-icon name="chat" size="3rem" class="q-mb-sm" /><br />아직 댓글이 없습니다.
                </div>

                <div v-for="c in comments" :key="c.id" class="comment-item q-mb-md">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-avatar size="28px" :color="c.isInternal ? 'grey-5' : 'primary'" text-color="white"
                      style="font-size:0.76rem">{{ c.writerName.charAt(0) }}</q-avatar>
                    <span class="text-weight-medium" style="font-size:0.9rem">{{ c.writerName }}</span>
                    <q-badge v-if="c.isInternal" color="grey-5" label="내부 메모" size="xs" />
                    <span class="text-caption text-grey-5 q-ml-auto">{{ fmtDateTime(c.createdAt) }}</span>
                  </div>
                  <div class="comment-bubble q-ml-lg"
                    :class="c.isInternal ? 'comment-bubble--internal' : 'comment-bubble--user'">
                    <div v-if="c.content" class="q-mb-xs">{{ c.content }}</div>
                    <!-- 첨부파일 -->
                    <div v-if="c.attachments?.length" class="column q-gutter-xs q-mt-xs">
                      <template v-for="att in c.attachments" :key="att.fileId">
                        <!-- 이미지 -->
                        <div v-if="att.contentType?.startsWith('image/')">
                          <a :href="att.url" target="_blank">
                            <img :src="att.url" :alt="att.originalName"
                              style="max-width:100%;max-height:320px;border-radius:6px;display:block;cursor:pointer" />
                          </a>
                          <div class="text-caption text-grey-5 q-mt-xs">{{ att.originalName }}</div>
                        </div>
                        <!-- 일반 파일 -->
                        <div v-else
                          class="row items-center q-gutter-xs comment-file-link no-wrap cursor-pointer"
                          @click="downloadFile(att.url, att.originalName)">
                          <q-icon name="attach_file" size="14px" color="grey-6" />
                          <span class="text-caption ellipsis">{{ att.originalName }}</span>
                          <span class="text-caption text-grey-5" style="white-space:nowrap;flex-shrink:0">
                            ({{ formatFileSize(att.size) }})
                          </span>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>

                <q-separator class="q-my-md" />

                <!-- 첨부 미리보기 -->
                <div v-if="commentFiles.length" class="q-mb-sm">
                  <!-- 이미지 썸네일 -->
                  <div v-if="commentFiles.some(it => it.previewUrl)" class="row wrap q-gutter-sm q-mb-xs">
                    <div v-for="(it, i) in commentFiles.filter(it => it.previewUrl)" :key="i" class="relative-position">
                      <img :src="it.previewUrl!" style="height:80px;max-width:160px;border-radius:6px;object-fit:cover;display:block" />
                      <q-btn round dense flat size="xs" icon="close"
                        style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.45);color:#fff"
                        @click="removeCommentFile(commentFiles.indexOf(it))" />
                    </div>
                  </div>
                  <!-- 일반 파일 칩 -->
                  <div v-if="commentFiles.some(it => !it.previewUrl)" class="row wrap q-gutter-xs">
                    <q-chip
                      v-for="(it, i) in commentFiles.filter(it => !it.previewUrl)" :key="i"
                      dense removable size="sm" color="blue-1" text-color="blue-9" icon="attach_file"
                      @remove="removeCommentFile(commentFiles.indexOf(it))"
                    >{{ it.file.name }}</q-chip>
                  </div>
                </div>

                <div class="row q-col-gutter-sm items-end">
                  <div class="col">
                    <q-input v-model="newComment" placeholder="댓글을 입력하세요... (이미지 붙여넣기 가능)" outlined dense
                      type="textarea" rows="3" @paste="onCommentPaste" />
                    <div class="row items-center q-mt-xs q-gutter-sm">
                      <q-checkbox v-if="isOperatorUser" v-model="newCommentInternal"
                        label="내부 메모 (운영팀에만 공개)" size="xs" color="grey-7" dense />
                      <q-btn flat dense size="xs" icon="attach_file" color="grey-7" label="파일 첨부"
                        @click="commentFileInput?.click()" />
                    </div>
                  </div>
                  <div class="col-auto">
                    <q-btn unelevated color="primary" label="등록" size="sm"
                      @click="submitComment" :loading="commenting" />
                  </div>
                </div>
                <input ref="commentFileInput" type="file" multiple style="display:none"
                  accept="image/*,.pdf,.xls,.xlsx,.doc,.docx,.txt,.csv,.zip"
                  @change="onCommentFileChange" />

              </q-tab-panel>

              <!-- ── 탭4: 이력 ── -->
              <q-tab-panel name="history" class="q-pa-lg">
                <div v-if="!statusHistory.length" class="text-center text-grey-5 q-py-xl">
                  <q-icon name="history" size="3rem" class="q-mb-sm" /><br />이력이 없습니다.
                </div>
                <q-timeline color="primary" dense>
                  <q-timeline-entry
                    v-for="h in statusHistory" :key="h.id"
                    :icon="h.actionType === 'STATUS_CHANGE' ? 'swap_horiz' : 'edit_note'"
                    :color="h.actionType === 'STATUS_CHANGE' ? 'primary' : 'amber-8'"
                    :subtitle="fmtDateTime(h.changedAt)"
                  >
                    <template #title>
                      <!-- 상태 변경 -->
                      <template v-if="h.actionType === 'STATUS_CHANGE'">
                        <div class="row items-center q-gutter-xs">
                          <q-badge v-if="h.beforeValue" :label="statusLabel(h.beforeValue)"
                            color="grey-3" text-color="dark" />
                          <q-icon v-if="h.beforeValue" name="east" size="xs" color="grey-5" />
                          <q-badge :label="statusLabel(h.afterValue ?? '')"
                            :color="statusColor(h.afterValue ?? '')" text-color="white" />
                        </div>
                      </template>
                      <!-- 필드 변경 -->
                      <template v-else>
                        <span class="text-weight-medium text-amber-9">
                          {{ fieldChangeLabel(h.actionType) }} 수정
                        </span>
                      </template>
                    </template>
                    <div class="text-caption text-grey-6">{{ h.changedBy }}</div>
                    <!-- 필드 변경 이전/이후 값 -->
                    <template v-if="h.actionType !== 'STATUS_CHANGE'">
                      <div class="q-mt-xs" style="font-size:0.78rem">
                        <span class="text-grey-5">이전: </span>
                        <span class="text-grey-7">{{ truncate(h.beforeValue) }}</span>
                      </div>
                      <div style="font-size:0.78rem">
                        <span class="text-grey-5">이후: </span>
                        <span class="text-dark">{{ truncate(h.afterValue) }}</span>
                      </div>
                    </template>
                  </q-timeline-entry>
                </q-timeline>
              </q-tab-panel>

            </q-tab-panels>
          </q-card>
        </div>

        <!-- ── 우측 요약 패널 ── -->
        <div class="col-12 col-lg-4">
          <q-card flat bordered class="summary-panel">
            <div class="section-header">
              <q-icon name="summarize" size="15px" />요청 요약
            </div>
            <q-separator />
            <q-list dense>
              <q-item>
                <q-item-section side class="side-label">요청자</q-item-section>
                <q-item-section class="text-weight-medium">{{ sr.requesterName }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section side class="side-label">부서</q-item-section>
                <q-item-section>{{ sr.requesterDepartment }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section side class="side-label">이메일</q-item-section>
                <q-item-section class="text-caption text-grey-7" style="word-break:break-all">{{ sr.requesterEmail }}</q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item>
                <q-item-section side class="side-label">대상 시스템</q-item-section>
                <q-item-section>{{ sr.relatedSystem || '-' }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section side class="side-label">우선순위</q-item-section>
                <q-item-section>
                  <q-badge :color="priorityChipColor(sr.priority)" :label="priorityLabel(sr.priority)" outline />
                </q-item-section>
              </q-item>
              <q-item v-if="sr.isUrgent">
                <q-item-section side class="side-label">긴급</q-item-section>
                <q-item-section>
                  <q-badge color="red" label="긴급" />
                  <div v-if="sr.urgentReason" class="text-caption text-grey-6 q-mt-xs">{{ sr.urgentReason }}</div>
                </q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item>
                <q-item-section side class="side-label">접수일</q-item-section>
                <q-item-section>{{ fmtDate(sr.createdAt) }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section side class="side-label">희망 완료일</q-item-section>
                <q-item-section>
                  <span :class="sr.isDelayed ? 'text-negative text-weight-medium' : ''">
                    {{ fmtDate(sr.desiredDueDate) }}
                  </span>
                  <span v-if="dDay !== null" class="q-ml-xs text-caption"
                    :class="dDay <= 3 ? 'text-negative text-weight-bold' : 'text-grey-5'">
                    ({{ dDayLabel }})
                  </span>
                </q-item-section>
              </q-item>
              <q-item v-if="sr.desiredDeployDate">
                <q-item-section side class="side-label">희망 배포일</q-item-section>
                <q-item-section>{{ fmtDate(sr.desiredDeployDate) }}</q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item>
                <q-item-section side class="side-label">담당자</q-item-section>
                <q-item-section>{{ sr.assigneeName || '-' }}</q-item-section>
              </q-item>
              <q-item v-if="sr.plannedDueDate">
                <q-item-section side class="side-label">처리 예정</q-item-section>
                <q-item-section :class="sr.isDelayed ? 'text-negative text-weight-medium' : ''">
                  {{ fmtDate(sr.plannedDueDate) }}
                </q-item-section>
              </q-item>
              <q-item v-if="sr.reviewerName">
                <q-item-section side class="side-label">검수 담당</q-item-section>
                <q-item-section>{{ sr.reviewerName }}</q-item-section>
              </q-item>
              <q-separator class="q-my-xs" />
              <q-item>
                <q-item-section side class="side-label">첨부파일</q-item-section>
                <q-item-section>
                  <span v-if="sr.attachments?.length">{{ sr.attachments.length }}개</span>
                  <span v-else class="text-grey-5">없음</span>
                </q-item-section>
              </q-item>
            </q-list>

            <template v-if="statusHistory.some(h => h.actionType === 'STATUS_CHANGE')">
              <q-separator />
              <div class="section-header" style="font-size:0.78rem">
                <q-icon name="update" size="14px" />최근 이력
              </div>
              <q-card-section class="q-pt-xs q-pb-sm">
                <div v-for="h in [...statusHistory].filter(h => h.actionType === 'STATUS_CHANGE').reverse().slice(0, 3)" :key="h.id" class="q-mb-xs">
                  <q-badge :label="statusLabel(h.afterValue ?? '')"
                    :color="statusColor(h.afterValue ?? '')" text-color="white" class="q-mr-xs" />
                  <span class="text-caption text-grey-5">{{ fmtDateTime(h.changedAt) }}</span>
                </div>
              </q-card-section>
            </template>
          </q-card>
        </div>

      </div>
    </template>

    <!-- ── 다이얼로그 ── -->

    <!-- 취소 -->
    <q-dialog v-model="cancelDialog">
      <q-card class="dialog-card">
        <div class="dialog-header dialog-header--negative">
          <div class="dialog-header__title">SR 취소</div>
          <div class="dialog-header__sub">{{ sr?.srNo }}</div>
        </div>
        <q-card-section class="dialog-body">
          <div class="field-label">취소 사유 <span class="required">*</span></div>
          <q-input v-model="cancelReason" outlined type="textarea" rows="4"
            placeholder="취소 사유를 입력하세요." hide-bottom-space />
        </q-card-section>
        <div class="dialog-footer">
          <q-btn flat label="닫기" v-close-popup color="grey-7" />
          <q-btn color="negative" unelevated label="취소 확인" @click="doCancel" :loading="actionLoading" />
        </div>
      </q-card>
    </q-dialog>

    <!-- 검토 -->
    <q-dialog v-model="reviewDialog" persistent>
      <q-card class="dialog-card" style="min-width:520px">
        <div class="dialog-header dialog-header--teal">
          <div class="dialog-header__title">SR 검토</div>
          <div class="dialog-header__sub">{{ sr?.srNo }}</div>
        </div>
        <q-card-section class="dialog-body">

          <div class="field-label">검토 결과 <span class="required">*</span></div>
          <q-select v-model="reviewForm.result" outlined
            :options="reviewResultOptions" emit-value map-options
            placeholder="결과를 선택하세요" hide-bottom-space class="q-mb-md" />

          <div class="field-label">검토 의견</div>
          <q-input v-model="reviewForm.comment" outlined type="textarea" rows="3"
            placeholder="검토 의견을 입력하세요." hide-bottom-space class="q-mb-md" />

          <template v-if="reviewForm.result === 'REJECTED'">
            <div class="field-label text-negative">반려 사유 <span class="required">*</span></div>
            <q-input v-model="reviewForm.rejectReason" outlined type="textarea" rows="2"
              placeholder="반려 사유를 입력하세요." bg-color="red-1" hide-bottom-space class="q-mb-md" />
          </template>

          <template v-if="reviewForm.result === 'ON_HOLD'">
            <div class="field-label text-amber-9">보류 사유 <span class="required">*</span></div>
            <q-input v-model="reviewForm.holdReason" outlined type="textarea" rows="2"
              placeholder="보류 사유를 입력하세요." bg-color="amber-1" hide-bottom-space class="q-mb-md" />
          </template>

          <template v-if="reviewForm.result === 'PENDING_INFO'">
            <div class="field-label text-blue-8">추가 확인 요청 내용 <span class="required">*</span></div>
            <q-input v-model="reviewForm.pendingInfoContent" outlined type="textarea" rows="2"
              placeholder="확인이 필요한 내용을 입력하세요." bg-color="blue-1" hide-bottom-space class="q-mb-md" />
          </template>


        </q-card-section>
        <div class="dialog-footer">
          <q-btn flat label="취소" v-close-popup color="grey-7" />
          <q-btn color="teal" unelevated label="검토 등록" @click="doReview" :loading="actionLoading" />
        </div>
      </q-card>
    </q-dialog>

    <!-- 담당자 배정 -->
    <q-dialog v-model="assignDialog">
      <q-card class="dialog-card">
        <div class="dialog-header dialog-header--cyan">
          <div class="dialog-header__title">담당자 배정</div>
          <div class="dialog-header__sub">{{ sr?.srNo }}</div>
        </div>
        <q-card-section class="dialog-body">

          <div class="field-label">담당자 <span class="required">*</span></div>
          <q-select v-model="assignSelectedUser" outlined
            :options="userOptions" option-label="name"
            use-input fill-input hide-selected input-debounce="0" @filter="filterUserOptions" clearable
            placeholder="이름으로 검색" hide-bottom-space class="q-mb-md">
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section avatar>
                  <q-avatar size="28px" color="primary" text-color="white" style="font-size:0.76rem">{{ scope.opt.name.charAt(0) }}</q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ scope.opt.name }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.email }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
            <template #no-option><q-item><q-item-section class="text-grey-5">검색 결과 없음</q-item-section></q-item></template>
          </q-select>

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-6">
              <div class="field-label">처리 예정 시작일</div>
              <q-input v-model="assignForm.plannedStartDate" outlined type="date" hide-bottom-space />
            </div>
            <div class="col-6">
              <div class="field-label">처리 예정 완료일</div>
              <q-input v-model="assignForm.plannedDueDate" outlined type="date" hide-bottom-space />
            </div>
          </div>

          <div class="field-label">예상 공수 <span style="font-size:11px;color:#aaa;font-weight:400">(시작일·완료일 기준 자동 계산, 주말 제외)</span></div>
          <q-input v-model="assignForm.estimatedEffort" outlined readonly
            placeholder="시작일과 완료일을 입력하면 자동 계산됩니다" hide-bottom-space class="q-mb-md" bg-color="grey-1" />

          <div class="row q-gutter-xl q-mt-xs">
            <q-toggle v-model="assignForm.deploymentRequired" color="orange-7" size="sm">
              <template #default><span class="text-body2 q-ml-xs">배포 필요</span></template>
            </q-toggle>
            <q-toggle v-model="assignForm.securityReviewRequired" color="red-7" size="sm">
              <template #default><span class="text-body2 q-ml-xs">보안 검토 필요</span></template>
            </q-toggle>
          </div>

        </q-card-section>
        <div class="dialog-footer">
          <q-btn flat label="취소" v-close-popup color="grey-7" />
          <q-btn color="cyan-7" unelevated label="배정 확인" @click="doAssign" :loading="actionLoading" />
        </div>
      </q-card>
    </q-dialog>

    <!-- 상태 변경 -->
    <q-dialog v-model="statusDialog">
      <q-card class="dialog-card">
        <div class="dialog-header dialog-header--blue">
          <div class="dialog-header__title">상태 변경</div>
          <div class="dialog-header__sub">{{ sr?.srNo }}</div>
        </div>
        <q-card-section class="dialog-body">

          <div class="field-label">변경할 상태 <span class="required">*</span></div>
          <q-select v-model="statusForm.status" outlined
            :options="availableStatusOptions" emit-value map-options
            placeholder="상태를 선택하세요" hide-bottom-space class="q-mb-md" />

          <template v-if="needsReason">
            <div class="field-label">사유 <span class="required">*</span></div>
            <q-input v-model="statusForm.reason" outlined type="textarea" rows="2"
              placeholder="사유를 입력하세요." hide-bottom-space class="q-mb-md" />
          </template>

          <template v-if="statusForm.status === 'COMPLETED'">
            <div class="field-label">처리 결과 <span class="required">*</span></div>
            <q-input v-model="statusForm.processResult" outlined type="textarea" rows="3"
              placeholder="처리 결과를 입력하세요." hide-bottom-space class="q-mb-md" />

            <q-toggle v-model="statusForm.deployed" color="positive" size="sm" class="q-mb-sm">
              <template #default><span class="text-body2 q-ml-xs">배포 완료</span></template>
            </q-toggle>

            <template v-if="statusForm.deployed">
              <div class="field-label">배포 일시</div>
              <q-input v-model="statusForm.deployedAt" outlined type="datetime-local" hide-bottom-space />
            </template>
          </template>

        </q-card-section>
        <div class="dialog-footer">
          <q-btn flat label="취소" v-close-popup color="grey-7" />
          <q-btn color="blue-7" unelevated label="변경 확인" @click="doStatusChange" :loading="actionLoading" />
        </div>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useAuthStore } from 'src/stores/auth'
import {
  getSR, getAdminSR, listComments, listHistory, addComment, uploadSRAttachment,
  cancelSR, reviewSR, assignSR, changeSRStatus,
  SR_STATUS_LABEL, SR_STATUS_COLOR, SR_PRIORITY_LABEL,
  REQUEST_TYPE_LABEL,
  type SR, type SRComment, type SRHistory, type SRStatus, type ReviewResult, type SRAttachment,
} from 'src/services/sr'
import { SR_TYPE_FIELDS } from 'src/services/sr-type-fields'
import type { SRTypeField } from 'src/services/sr-type-fields'
import { listPmUsers, type PmUser } from 'src/services/pm/users'
import { formatKst } from 'src/utils/time/kst'

// ── 상수 ────────────────────────────────────────────────────────────

const REVIEW_RESULT_LABEL: Record<string, string> = {
  APPROVED: '승인', REJECTED: '반려', ON_HOLD: '보류', PENDING_INFO: '추가 확인 요청',
}
const REVIEW_RESULT_COLOR: Record<string, string> = {
  APPROVED: 'teal', REJECTED: 'negative', ON_HOLD: 'brown', PENDING_INFO: 'amber-7',
}
const TYPE_ICON: Record<string, string> = {
  IMPROVEMENT: 'tune', BUG_FIX: 'bug_report', DATA_REQUEST: 'storage',
  PERMISSION: 'lock_open', CONFIG_CHANGE: 'settings', SERVER_INFRA: 'dns',
  SECURITY: 'security', ETC: 'more_horiz',
}
const TYPE_CHIP_COLOR: Record<string, string> = {
  IMPROVEMENT: 'blue-7', BUG_FIX: 'red-7', DATA_REQUEST: 'purple-7',
  PERMISSION: 'teal-7', CONFIG_CHANGE: 'orange-8', SERVER_INFRA: 'indigo-7',
  SECURITY: 'deep-orange-8', ETC: 'grey-7',
}

// ── refs / store ────────────────────────────────────────────────────

const $q         = useQuasar()
const route      = useRoute()
const router     = useRouter()
const authStore  = useAuthStore()
const srId       = route.params.id as string

// 목록에서 넘어온 순서 (이전/다음 이동용)
const listIds    = JSON.parse(sessionStorage.getItem('sr-list-ids') || '[]') as string[]
const listIndex  = computed(() => listIds.indexOf(srId))
const prevId     = computed(() => listIndex.value > 0 ? listIds[listIndex.value - 1] : null)
const nextId     = computed(() => listIndex.value < listIds.length - 1 ? listIds[listIndex.value + 1] : null)

function goToSR(id: string) {
  void router.push(`/pm/sr/${id}`)
}

const loading        = ref(true)
const sr             = ref<SR | null>(null)
const comments       = ref<SRComment[]>([])
const statusHistory  = ref<SRHistory[]>([])
const activeTab      = ref('content')
const newComment     = ref('')
const newCommentInternal = ref(false)
const commenting     = ref(false)
type CommentFileItem = { file: File; previewUrl: string | null }
const commentFiles   = ref<CommentFileItem[]>([])
const commentFileInput = ref<HTMLInputElement | null>(null)
const actionLoading  = ref(false)
const activeAction   = ref<string | null>(null)
const cancelDialog   = ref(false)
const reviewDialog   = ref(false)
const assignDialog   = ref(false)
const statusDialog   = ref(false)
const cancelReason   = ref('')

const reviewForm = ref({
  result: null as string | null, comment: '', rejectReason: '', holdReason: '',
  pendingInfoContent: '',
})
const assignForm = ref({
  plannedStartDate: null as string | null, plannedDueDate: null as string | null,
  estimatedEffort: '', deploymentRequired: false, securityReviewRequired: false,
})

watch(
  () => [assignForm.value.plannedStartDate, assignForm.value.plannedDueDate],
  ([start, end]) => {
    if (start && end) {
      let count = 0
      const cur = new Date(start)
      const last = new Date(end)
      while (cur <= last) {
        const day = cur.getDay()
        if (day !== 0 && day !== 6) count++
        cur.setDate(cur.getDate() + 1)
      }
      if (count > 0) assignForm.value.estimatedEffort = `${count}일`
    }
  }
)

// 사용자 선택 (담당자 배정 / 검토 다이얼로그 공유)
const allUsers       = ref<PmUser[]>([])
const userOptions    = ref<PmUser[]>([])
const assignSelectedUser = ref<PmUser | null>(null)
const reviewSelectedUser = ref<PmUser | null>(null)
const statusForm = ref({
  status: null as string | null, reason: '', processResult: '',
  deployed: false, deployedAt: null as string | null,
})

// ── 권한 computed ────────────────────────────────────────────────────

const isAdminUser    = computed(() => authStore.me?.isAdmin || false)
const isOperatorUser = computed(() => {
  const p = authStore.me?.permissions || []
  return authStore.me?.isAdmin || p.includes('sr_operator') || p.includes('sr_manager')
})
const isManagerUser  = computed(() => {
  const p = authStore.me?.permissions || []
  return authStore.me?.isAdmin || p.includes('sr_manager')
})
const isMyRequest    = computed(() => sr.value && String(authStore.me?.id) === sr.value.requesterId)

// ── D-Day computed ────────────────────────────────────────────────────

const dDay = computed((): number | null => {
  if (!sr.value?.desiredDueDate) return null
  const due   = new Date(sr.value.desiredDueDate)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  return Math.ceil((due.getTime() - today.getTime()) / 86400000)
})
const dDayLabel = computed(() => {
  if (dDay.value === null) return ''
  if (dDay.value === 0) return 'D-Day'
  return dDay.value > 0 ? `D-${dDay.value}` : `D+${Math.abs(dDay.value)}`
})
const dDayColor = computed(() => {
  if (dDay.value === null) return 'grey'
  if (dDay.value <= 0) return 'negative'
  if (dDay.value <= 3) return 'orange-8'
  return 'grey-6'
})

// 권한 만료 D-Day (PERMISSION 유형)
const permissionExpiryDDay = computed((): number | null => {
  const expiry = sr.value?.typeDetail?.permissionExpiry as string | null | undefined
  if (!expiry) return null
  const due   = new Date(expiry)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  return Math.ceil((due.getTime() - today.getTime()) / 86400000)
})

// ── 액션 버튼 computed ────────────────────────────────────────────────

const actionButtons = computed(() => {
  if (!sr.value) return []
  const s = sr.value.status
  const btns: { key: string; label: string; color: string; outline?: boolean; icon: string; action: () => void }[] = []

  if (isMyRequest.value) {
    if (s !== 'CLOSED') {
      btns.push({ key: 'edit', label: 'SR 수정', color: 'amber-8', icon: 'edit', action: () => { void router.push(`/pm/sr/${sr.value!.id}/edit`) } })
    }
    if (!['CLOSED', 'CANCELLED', 'REJECTED'].includes(s)) {
      btns.push({ key: 'cancel', label: '취소', color: 'negative', outline: true, icon: 'cancel', action: () => { cancelDialog.value = true } })
    }
  }

  if (isManagerUser.value) {
    if (['SUBMITTED', 'REVIEWING', 'PENDING_INFO'].includes(s)) {
      btns.push({ key: 'review', label: '검토', color: 'teal', icon: 'rate_review', action: () => {
        reviewForm.value = { result: null, comment: '', rejectReason: '', holdReason: '', pendingInfoContent: '' }
        reviewSelectedUser.value = null
        reviewDialog.value = true
      } })
    }
    if (s === 'APPROVED') {
      btns.push({ key: 'assign', label: '담당자 배정', color: 'cyan-7', icon: 'person_add', action: () => { openAssignDialog(false) } })
    }
    if (s === 'IN_PROGRESS') {
      btns.push({ key: 'assign', label: '담당자 변경', color: 'cyan-7', outline: true, icon: 'person_add', action: () => { openAssignDialog(true) } })
    }
  }

  if (isOperatorUser.value && !['CLOSED', 'REJECTED', 'DRAFT'].includes(s)) {
    btns.push({ key: 'status', label: '상태 변경', color: 'blue-7', icon: 'swap_horiz', action: () => { statusDialog.value = true } })
  }

  return btns
})

// ── 기타 computed ─────────────────────────────────────────────────────

const reviewResultOptions    = Object.entries(REVIEW_RESULT_LABEL).map(([value, label]) => ({ value, label }))
const availableStatusOptions = computed(() =>
  ['SUBMITTED', 'REVIEWING', 'PENDING_INFO', 'APPROVED', 'REJECTED', 'ASSIGNED', 'IN_PROGRESS',
   'COMPLETED', 'CONFIRMING', 'CLOSED', 'ON_HOLD', 'CANCELLED']
    .map(s => ({ value: s, label: statusLabel(s) }))
)
const needsReason = computed(() => ['REJECTED', 'ON_HOLD', 'CANCELLED'].includes(statusForm.value.status || ''))

const currentSRTypeFields = computed((): SRTypeField[] => {
  if (!sr.value) return []
  return SR_TYPE_FIELDS[sr.value.requestType] ?? []
})

const extraAttachments = computed(() => {
  if (!sr.value) return []
  const desc = sr.value.description || ''
  return sr.value.attachments.filter(a => !desc.includes(a.url))
})

// ── 헬퍼 함수 ────────────────────────────────────────────────────────

function filterUserOptions(val: string, update: (fn: () => void) => void) {
  update(() => {
    if (!val.trim()) {
      userOptions.value = allUsers.value
    } else {
      const q = val.toLowerCase()
      userOptions.value = allUsers.value.filter(u =>
        u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      )
    }
  })
}

function typeIcon(t: string)         { return TYPE_ICON[t] ?? 'help_outline' }
function typeChipColor(t: string)    { return TYPE_CHIP_COLOR[t] ?? 'grey-7' }
function statusLabel(s: string)      { return (SR_STATUS_LABEL    as Record<string,string>)[s] ?? s }
function statusColor(s: string)      { return (SR_STATUS_COLOR    as Record<string,string>)[s] ?? 'grey' }
function priorityLabel(s: string)    { return (SR_PRIORITY_LABEL  as Record<string,string>)[s] ?? s }
function requestTypeLabel(s: string) { return (REQUEST_TYPE_LABEL as Record<string,string>)[s] ?? s }
function reviewResultLabel(r: string | null) { if (!r) return null; return REVIEW_RESULT_LABEL[r] ?? r }
function reviewResultColor(r: string | null) { if (!r) return 'grey'; return REVIEW_RESULT_COLOR[r] ?? 'grey' }

function priorityChipColor(p: string) {
  const m: Record<string, string> = { CRITICAL: 'red-7', HIGH: 'orange-7', MEDIUM: 'blue-6', LOW: 'grey-5' }
  return m[p] ?? 'grey-5'
}

function riskLevelColor(v: string | null) {
  if (v === 'high') return 'red-7'
  if (v === 'medium') return 'orange-7'
  return 'green-7'
}

function serviceImpactColor(v: string | null) {
  if (v === 'stop') return 'red-7'
  if (v === 'delay') return 'orange-7'
  return 'positive'
}

function fieldValue(field: SRTypeField): string | null {
  if (!sr.value) return null
  return (sr.value.typeDetail?.[field.key] as string | null | undefined) ?? null
}

function selectLabel(field: SRTypeField, value: string | null): string {
  if (!value || !field.options) return value ?? '-'
  return field.options.find(o => o.value === value)?.label ?? value
}

function fieldSelectLabel(typeName: string, fieldKey: string, value: string | null): string {
  if (!value) return '-'
  const field = (SR_TYPE_FIELDS[typeName] ?? []).find(f => f.key === fieldKey)
  if (!field?.options) return value
  return field.options.find(o => o.value === value)?.label ?? value
}

function fileIcon(ct: string) {
  if (ct.startsWith('image/')) return 'image'
  if (ct.includes('pdf')) return 'picture_as_pdf'
  if (ct.includes('spreadsheet') || ct.includes('excel')) return 'table_chart'
  if (ct.includes('zip') || ct.includes('compressed')) return 'folder_zip'
  return 'insert_drive_file'
}

function fmtDate(d: string | null | undefined)     { return d ? d.substring(0, 10) : '-' }
function fmtDateTime(d: string | null | undefined) { return d ? formatKst(d) : '-' }

const FIELD_LABELS: Record<string, string> = {
  title:               '제목',
  description:         '요청 내용',
  background:          '배경',
  purpose:             '목적',
  desired_due_date:    '희망 완료일',
  desired_deploy_date: '희망 배포일',
  priority:            '우선순위',
  impact_scope:        '영향 범위',
  is_urgent:           '긴급 여부',
  urgent_reason:       '긴급 사유',
  related_system:      '대상 시스템',
  related_menu:        '관련 메뉴',
  related_url:         '관련 URL',
  completion_criteria: '완료 기준',
  note:                '비고',
}
function fieldChangeLabel(actionType: string): string {
  const key = actionType.replace('FIELD_CHANGE:', '')
  return FIELD_LABELS[key] ?? key
}
function truncate(val: string | null | undefined, max = 120): string {
  if (!val || val === 'None') return '-'
  const plain = val.replace(/<[^>]+>/g, '').trim()
  return plain.length > max ? plain.slice(0, max) + '…' : plain
}
function fmtSize(b: number) {
  if (b < 1024)    return `${b}B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)}KB`
  return `${(b / 1048576).toFixed(1)}MB`
}

async function downloadDetail() {
  try {
    const res = await api.get(`/admin/schedule/service-requests/${srId}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SR_${srId}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    $q.notify({ type: 'negative', message: 'Excel 다운로드에 실패했습니다.' })
  }
}

// ── API 호출 ──────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  const id = route.params.id as string
  try {
    sr.value            = isOperatorUser.value ? await getAdminSR(id) : await getSR(id)
    comments.value      = await listComments(id)
    statusHistory.value = await listHistory(id)
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '데이터를 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

function makeItem(file: File): CommentFileItem {
  return { file, previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null }
}

function onCommentPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const newItems: CommentFileItem[] = []
  for (const item of Array.from(items)) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const raw = item.getAsFile()
      if (raw) {
        const named = new File([raw], `paste-${Date.now()}.${item.type.split('/')[1] || 'png'}`, { type: item.type })
        newItems.push(makeItem(named))
      }
    }
  }
  if (newItems.length > 0) {
    e.preventDefault()
    commentFiles.value = [...commentFiles.value, ...newItems]
  }
}

function onCommentFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  commentFiles.value = [...commentFiles.value, ...Array.from(input.files).map(makeItem)]
  input.value = ''
}

function removeCommentFile(idx: number) {
  const item = commentFiles.value[idx]
  if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl)
  commentFiles.value = commentFiles.value.filter((_, i) => i !== idx)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

async function downloadFile(url: string, filename: string) {
  try {
    const token = useAuthStore().token
    const resp = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) throw new Error(`${resp.status}`)
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    $q.notify({ type: 'negative', message: '파일 다운로드에 실패했습니다.' })
  }
}

async function submitComment() {
  if (!newComment.value.trim() && commentFiles.value.length === 0) return
  commenting.value = true
  try {
    let uploaded: SRAttachment[] = []
    if (commentFiles.value.length > 0) {
      uploaded = await Promise.all(commentFiles.value.map(item => uploadSRAttachment(item.file)))
    }
    await addComment(srId, newComment.value, newCommentInternal.value, uploaded)
    newComment.value         = ''
    newCommentInternal.value = false
    commentFiles.value.forEach(item => { if (item.previewUrl) URL.revokeObjectURL(item.previewUrl) })
    commentFiles.value       = []
    comments.value           = await listComments(srId)
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '댓글 등록 실패' })
  } finally { commenting.value = false }
}

async function doCancel() {
  if (!cancelReason.value.trim()) return
  actionLoading.value = true; activeAction.value = 'cancel'
  try {
    await cancelSR(srId, cancelReason.value)
    $q.notify({ type: 'positive', message: 'SR이 취소되었습니다.' })
    cancelDialog.value = false; void load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '처리 실패' })
  } finally { actionLoading.value = false; activeAction.value = null }
}

async function doReview() {
  if (!reviewForm.value.result) return
  actionLoading.value = true; activeAction.value = 'review'
  try {
    await reviewSR(srId, {
      result:               reviewForm.value.result as ReviewResult,
      comment:              reviewForm.value.comment || undefined,
      reject_reason:        reviewForm.value.rejectReason || undefined,
      hold_reason:          reviewForm.value.holdReason || undefined,
      pending_info_content: reviewForm.value.pendingInfoContent || undefined,
    })
    $q.notify({ type: 'positive', message: '검토가 등록되었습니다.' })
    reviewDialog.value = false; void load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '처리 실패' })
  } finally { actionLoading.value = false; activeAction.value = null }
}

async function doAssign() {
  if (!assignSelectedUser.value) {
    $q.notify({ type: 'warning', message: '담당자를 선택해주세요.' }); return
  }
  actionLoading.value = true; activeAction.value = 'assign'
  try {
    await assignSR(srId, {
      assignee_id:              assignSelectedUser.value.id,
      assignee_name:            assignSelectedUser.value.name,
      planned_start_date:       assignForm.value.plannedStartDate,
      planned_due_date:         assignForm.value.plannedDueDate,
      estimated_effort:         assignForm.value.estimatedEffort || undefined,
      deployment_required:      assignForm.value.deploymentRequired,
      security_review_required: assignForm.value.securityReviewRequired,
    })
    $q.notify({ type: 'positive', message: '담당자가 배정되었습니다.' })
    assignDialog.value = false
    assignSelectedUser.value = null
    void load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '처리 실패' })
  } finally { actionLoading.value = false; activeAction.value = null }
}

function openAssignDialog(prefill: boolean) {
  if (prefill && sr.value) {
    assignSelectedUser.value = allUsers.value.find(u => u.id === sr.value!.assigneeId) ?? null
    assignForm.value = {
      plannedStartDate:       sr.value.plannedStartDate ? sr.value.plannedStartDate.slice(0, 10) : null,
      plannedDueDate:         sr.value.plannedDueDate   ? sr.value.plannedDueDate.slice(0, 10)   : null,
      estimatedEffort:        sr.value.estimatedEffort  ?? '',
      deploymentRequired:     sr.value.deploymentRequired     ?? false,
      securityReviewRequired: sr.value.securityReviewRequired ?? false,
    }
  } else {
    assignSelectedUser.value = null
    assignForm.value = { plannedStartDate: null, plannedDueDate: null, estimatedEffort: '', deploymentRequired: false, securityReviewRequired: false }
  }
  assignDialog.value = true
}

async function doStatusChange() {
  if (!statusForm.value.status) return
  actionLoading.value = true; activeAction.value = 'status'
  try {
    await changeSRStatus(srId, {
      status:         statusForm.value.status as SRStatus,
      reason:         statusForm.value.reason || undefined,
      process_result: statusForm.value.processResult || undefined,
      deployed:       statusForm.value.deployed || undefined,
      deployed_at:    statusForm.value.deployedAt || undefined,
    })
    $q.notify({ type: 'positive', message: '상태가 변경되었습니다.' })
    statusDialog.value = false; void load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '처리 실패' })
  } finally { actionLoading.value = false; activeAction.value = null }
}

onMounted(async () => {
  void load()
  try {
    allUsers.value = await listPmUsers('데이터운영팀')
    userOptions.value = allUsers.value
  } catch { /* 사용자 목록 실패 시 무시 */ }
})

watch(() => route.params.id, (newId) => {
  if (newId) void load()
})
</script>

<style scoped>
.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 0.82rem;
  color: #555;
  padding: 10px 16px;
  background: #fafafa;
}

.tab-section-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #616161;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding-bottom: 4px;
  border-bottom: 2px solid #e0e0e0;
}

.content-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #9e9e9e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 3px;
}

.content-text  { font-size: 0.9rem; line-height: 1.65; color: #212121; }
.content-date  { display: flex; align-items: center; font-size: 0.9rem; color: #212121; }
.pre-wrap      { white-space: pre-wrap; }

.content-html { font-size: 0.9rem; line-height: 1.75; color: #212121; }
.content-html :deep(img) { max-width: 100%; border-radius: 4px; margin: 4px 0; }
.content-html :deep(a) { color: var(--q-primary); }
.content-html :deep(ul),
.content-html :deep(ol) { padding-left: 1.4em; }
.content-html :deep(blockquote) {
  border-left: 3px solid #e0e0e0;
  margin: 8px 0; padding: 4px 12px; color: #757575;
}

.info-row          { display: flex; align-items: baseline; gap: 12px; }
.info-row__label   { font-size: 0.78rem; color: #9e9e9e; min-width: 80px; flex-shrink: 0; }
.info-row__value   { font-size: 0.9rem; color: #212121; }

/* 비교 박스 (BUG_FIX, CONFIG_CHANGE) */
.compare-box {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 0.88rem;
  line-height: 1.6;
  min-height: 60px;
}
.compare-box--expected { background: #e8f5e9; border-left: 3px solid #66bb6a; color: #1b5e20; }
.compare-box--actual   { background: #fce4ec; border-left: 3px solid #ef5350; color: #b71c1c; }
.compare-box--before   { background: #fff3e0; border-left: 3px solid #ffa726; color: #e65100; }
.compare-box--after    { background: #e3f2fd; border-left: 3px solid #42a5f5; color: #0d47a1; }

.resource-box {
  background: #263238;
  color: #eceff1;
  padding: 10px 14px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.85rem;
}

/* 요약 패널 */
.summary-panel { position: sticky; top: 16px; }

.side-label { min-width: 72px; font-size: 0.75rem; color: #9e9e9e; padding-right: 4px; }

/* 다이얼로그 공통 */
.dialog-card { min-width: 440px; border-radius: 12px !important; overflow: hidden; display: flex; flex-direction: column; max-height: 90vh; }

.dialog-header {
  padding: 20px 24px 16px;
  color: white;
}
.dialog-header--negative { background: var(--q-negative); }
.dialog-header--teal     { background: #00897b; }
.dialog-header--cyan     { background: #00838f; }
.dialog-header--blue     { background: #1565c0; }
.dialog-header__title    { font-size: 1.1rem; font-weight: 700; line-height: 1.3; }
.dialog-header__sub      { font-size: 0.78rem; opacity: 0.75; margin-top: 2px; }

.dialog-body { padding: 20px 24px 4px; overflow-y: auto; flex: 1; }

.field-label {
  font-size: 0.74rem;
  font-weight: 600;
  color: #616161;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}
.required { color: var(--q-negative); }

.section-divider {
  font-size: 0.72rem;
  font-weight: 700;
  color: #9e9e9e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-top: 1px solid #e0e0e0;
  padding-top: 14px;
  margin: 16px 0 14px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 20px;
}

/* 댓글 */
.comment-item { }
.comment-bubble {
  border-radius: 0 8px 8px 8px;
  padding: 10px 14px;
  font-size: 0.88rem;
  line-height: 1.6;
  white-space: pre-wrap;
}
.comment-bubble--user     { background: #e8f1fd; border-left: 3px solid var(--q-primary); }
.comment-file-link {
  text-decoration: none;
  color: #555;
  background: rgba(0,0,0,0.04);
  border-radius: 4px;
  padding: 3px 6px;
  display: flex;
  min-width: 0;
  max-width: 100%;
}
.comment-file-link .ellipsis {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  min-width: 0;
}
.comment-file-link:hover { background: rgba(0,0,0,0.08); }
.comment-bubble--internal { background: #f5f5f5; border-left: 3px solid #bdbdbd; }
</style>
