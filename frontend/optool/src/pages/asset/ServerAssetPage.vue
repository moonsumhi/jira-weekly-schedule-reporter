<template>
  <q-page class="q-pa-md">
    <!-- Header -->
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">{{ pageTitle }}</div>
      <q-space />

      <q-toggle
        v-model="includeDeleted"
        label="삭제 포함"
        dense
      />

      <q-btn
        outline
        icon="refresh"
        label="새로고침"
        :loading="loading"
        @click="load"
      />


      <q-btn outline icon="view_column" label="컬럼 상세보기" @click="openColVisDialog" />
      <q-btn outline icon="file_download" label="템플릿 다운로드" @click="downloadTemplate" />
      <q-btn outline icon="upload_file" label="Import" @click="triggerImport" />
      <q-btn
        v-if="importFailedRows.filter(r => !r.retrySuccess).length > 0"
        outline icon="error_outline" color="negative"
        :label="`실패 ${importFailedRows.filter(r => !r.retrySuccess).length}건`"
        @click="importResultTab = 'failed'; importFailDialog = true"
      />
      <q-btn
        v-if="importSkippedRows.length > 0"
        outline icon="skip_next" color="warning"
        :label="`건너뜀 ${importSkippedRows.length}건`"
        @click="importResultTab = 'skipped'; importFailDialog = true"
      />
      <q-btn
        v-if="duplicateSkippedRows.filter(r => !r.separateSaved).length > 0"
        outline icon="add_circle_outline" color="teal"
        :label="`별도 저장 ${duplicateSkippedRows.filter(r => !r.separateSaved).length}건`"
        @click="importResultTab = 'separate'; importFailDialog = true"
      />
      <q-btn outline icon="download" label="Export" :loading="exportLoading" @click="doExport" />
      <input ref="importFileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onImportFile" />

      <q-btn
        color="primary"
        icon="add"
        :label="category ? `${category} 추가` : '자산 추가'"
        @click="category ? openCreate() : (assetTypeDialog = true)"
      />
    </div>

    <q-card bordered>
      <!-- Filters -->
      <q-card-section class="row items-center q-gutter-sm">
        <q-select
          v-model="filterCol"
          :options="filterColOptions"
          option-value="key"
          option-label="label"
          emit-value
          map-options
          dense
          outlined
          clearable
          :display-value="filterCol ? (filterColOptions.find(o => o.key === filterCol)?.label ?? filterCol) : '전체 검색'"
          style="min-width: 140px;"
          @update:model-value="filter = ''"
        />
        <!-- 선택된 컬럼에 고유값이 있으면 드롭다운, 없으면 텍스트 입력 -->
        <q-select
          v-if="filterColUniqueValues.length"
          v-model="filter"
          :options="_filterColFiltered.length || filter ? _filterColFiltered : filterColUniqueValues"
          dense
          outlined
          clearable
          use-input
          input-debounce="0"
          placeholder="값 선택 또는 입력"
          class="col"
          @filter="filterColSearch"
        />
        <q-input
          v-else
          v-model="filter"
          dense
          outlined
          clearable
          debounce="200"
          placeholder="검색어 입력"
          class="col"
          @clear="filter = ''"
        />
      </q-card-section>

      <q-separator />

      <!-- Table -->
      <q-card-section class="q-pa-none">
        <q-table
          :rows="filteredRows"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="pagination"
          @update:pagination="onPagination"
          flat
          bordered
          class="sticky-header-table"
          style="height: calc(100vh - 200px)"
        >
          <!-- Custom header with sort + checkboxes -->
          <template #header="props">
            <q-tr :props="props">
              <th
                v-for="(col, idx) in props.cols"
                :key="idx"
                :class="['text-' + (col.align ?? 'left'), 'q-table__th', col.name !== 'actions' ? 'cursor-pointer select-none' : 'sticky-actions-col']"
                :style="col.headerStyle"
                @click="col.name !== 'actions' && toggleSort(col)"
              >
                <div class="row items-center no-wrap q-gutter-xs">
                  <span>{{ col.label }}</span>
                  <q-icon
                    v-if="col.name !== 'actions' && tableSortKey === getSortKey(col)"
                    :name="tableSortDesc ? 'arrow_downward' : 'arrow_upward'"
                    size="xs"
                    color="primary"
                  />
                  <q-icon
                    v-else-if="col.name !== 'actions'"
                    name="unfold_more"
                    size="xs"
                    color="grey-4"
                  />
                  <q-checkbox
                    v-if="col.name !== 'actions' && col.name !== 'assetType'"
                    :model-value="true"
                    dense
                    size="xs"
                    color="grey-6"
                    class="col-hide-checkbox"
                    @update:model-value="removeCol(col)"
                    @click.stop
                  />
                </div>
              </th>
            </q-tr>
          </template>
          <!-- Asset Type (전체 탭) -->
          <template #body-cell-assetType="props">
            <q-td :props="props" :class="{ 'cell-deleted': props.row.isDeleted }">
              <q-badge outline :color="assetTypeColor(props.row)">
                {{ (props.row.fields?.['자산유형']) || '서버' }}
              </q-badge>
            </q-td>
          </template>

          <!-- IP -->
          <template #body-cell-ip="props">
            <q-td :props="props" :class="{ 'cell-deleted': props.row.isDeleted }">
              <span class="text-mono">{{ props.row.ip }}</span>
            </q-td>
          </template>

          <!-- NAME -->
          <template #body-cell-name="props">
            <q-td :props="props" :class="{ 'cell-deleted': props.row.isDeleted }">
              <span>{{ props.row.name }}</span>
            </q-td>
          </template>

          <!-- Dynamic fields -->
          <template #body-cell-field="props">
            <q-td :props="props" :class="{ 'cell-deleted': props.row.isDeleted }">
              <!-- EOS action badge -->
              <template v-if="colKey(props.col) === EOS_STATUS_KEY">
                <template v-if="props.row.fields?.['운영체제']">
                  <q-badge :color="getField(props.row, EOS_STATUS_KEY) ? eosStatusColor(getField(props.row, EOS_STATUS_KEY)) : 'grey'" outline>
                    {{ getField(props.row, EOS_STATUS_KEY) ? eosStatusLabel(getField(props.row, EOS_STATUS_KEY)) : '확인 불가' }}
                  </q-badge>
                </template>
                <q-badge v-else color="grey" outline>확인 불가</q-badge>
              </template>

              <!-- EOL status badge -->
              <template v-else-if="colKey(props.col) === EOL_STATUS_KEY">
                <template v-if="props.row.fields?.['운영체제']">
                  <q-badge :color="getField(props.row, EOL_STATUS_KEY) ? eolStatusColor(getField(props.row, EOL_STATUS_KEY)) : 'grey'" outline>
                    {{ getField(props.row, EOL_STATUS_KEY) ? eolStatusLabel(getField(props.row, EOL_STATUS_KEY)) : '확인 불가' }}
                  </q-badge>
                </template>
                <q-badge v-else color="grey" outline>확인 불가</q-badge>
              </template>

              <!-- EOS date + soon warning -->
              <template v-else-if="colKey(props.col) === EOS_DATE_KEY">
                <span>{{ getField(props.row, EOS_DATE_KEY) || '확인 불가' }}</span>
                <q-icon
                  v-if="isDateSoon(getField(props.row, EOS_DATE_KEY), eosSoonDays)"
                  name="warning"
                  class="q-ml-xs text-warning"
                />
              </template>

              <!-- 운영체제: OS + version 함께 표시 -->
              <template v-else-if="colKey(props.col) === '운영체제'">
                <span>{{ displayValue(getField(props.row, '운영체제')) }}</span>
                <span v-if="getField(props.row, 'version')" class="text-grey-6 q-ml-xs" style="font-size: 0.85em;">
                  {{ displayValue(getField(props.row, 'version')) }}
                </span>
              </template>

              <!-- 태그 -->
              <template v-else-if="colKey(props.col) === TAGS_KEY">
                <q-chip
                  v-for="tag in (getField(props.row, TAGS_KEY) as string[] ?? []).slice(0, 2)"
                  :key="tag"
                  square dense color="primary" text-color="white" class="q-mr-xs"
                >#{{ tag }}</q-chip>
                <q-chip
                  v-if="((getField(props.row, TAGS_KEY) as string[]) ?? []).length > 2"
                  square dense color="grey-5" text-color="white" class="cursor-pointer q-mr-xs"
                >
                  +{{ ((getField(props.row, TAGS_KEY) as string[]) ?? []).length - 2 }}개 더
                  <q-popup-proxy>
                    <q-card flat bordered class="q-pa-sm" style="max-width: 300px">
                      <div class="row q-gutter-xs">
                        <q-chip
                          v-for="tag in (getField(props.row, TAGS_KEY) as string[] ?? [])"
                          :key="tag"
                          square dense color="primary" text-color="white"
                        >#{{ tag }}</q-chip>
                      </div>
                    </q-card>
                  </q-popup-proxy>
                </q-chip>
              </template>

              <!-- Normal dynamic field -->
              <template v-else>
                <span>{{ formatCell(props.col, props.value) }}</span>
              </template>
            </q-td>
          </template>

          <!-- Actions -->
          <template #body-cell-actions="props">
            <q-td :props="props" :class="{ 'cell-deleted-actions': props.row.isDeleted, 'sticky-actions-col': true }" style="padding: 4px 8px; white-space: nowrap">
              <div class="row items-center no-wrap q-gutter-xs">
                <q-btn
                  dense
                  outline
                  size="12px"
                  icon="info"
                  label="상세 보기"
                  @click="openDetailView(props.row)"
                />
                <template v-if="!props.row.isDeleted">
                  <q-btn
                    dense
                    outline
                    size="12px"
                    icon="edit"
                    label="편집"
                    @click="openRowEdit(props.row)"
                  />
                  <q-btn
                    dense
                    outline
                    size="12px"
                    icon="history"
                    label="이력"
                    @click="openHistory(props.row)"
                  />
                  <q-btn
                    dense
                    outline
                    size="12px"
                    icon="delete"
                    color="negative"
                    @click="confirmDelete(props.row)"
                  />
                </template>
                <template v-else>
                  <q-btn
                    dense
                    outline
                    size="12px"
                    icon="history"
                    label="이력"
                    @click="openHistory(props.row)"
                  />
                  <q-btn
                    dense
                    outline
                    size="12px"
                    icon="restore"
                    color="positive"
                    label="복원"
                    @click="doRestore(props.row)"
                  />
                </template>
              </div>
            </q-td>
          </template>

          <template #no-data>
            <div class="full-width row flex-center q-pa-lg text-grey-6">
              표시할 데이터가 없습니다.
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create dialog -->
    <q-dialog v-model="createDialog" @hide="createOverrideCategory = ''">
      <q-card class="server-form-card">
        <!-- 상단: 호스트명 & IP 강조 필드 -->
        <q-card-section class="q-pb-sm">
          <div class="top-field-row">
            <span class="top-field-label">호스트명<span class="req-star">*</span>:</span>
            <q-input v-model="createName" borderless dense class="top-field-input" placeholder="hostname" />
          </div>
          <div class="top-field-row q-mt-sm">
            <span class="top-field-label">IP<span class="req-star">*</span>:</span>
            <div class="col">
              <q-input v-model="createIp" borderless dense class="top-field-input" placeholder="192.168.0.1" @blur="checkDuplicateIp" />
              <div v-if="createIpError" class="text-negative text-caption q-mt-xs">{{ createIpError }}</div>
            </div>
          </div>
        </q-card-section>

        <!-- 기본 정보 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">기본 정보</span>
          </div>
          <div class="section-divider" />
        </q-card-section>

        <!-- 기본 정보 그리드 -->
        <q-card-section class="q-py-md">
          <div class="row q-col-gutter-x-lg q-col-gutter-y-md">
            <div class="col-6 form-field">
              <div class="field-label">자산명 <span class="req-star">*</span></div>
              <q-input v-model="createFields['서버명']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">구분 <span class="req-star">*</span></div>
              <q-input v-model="createFields['구분']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">자산번호 <span class="req-star">*</span></div>
              <q-input v-model="createFields['자산번호']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">RackNo. <span class="req-star">*</span></div>
              <q-input v-model="createFields['rack_no']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">Rack Unit No.</div>
              <q-input v-model="createFields['rack_unit_no']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">자산관리번호</div>
              <q-input v-model="createFields['자산관리번호']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">SN</div>
              <q-input v-model="createFields['SN']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">위치 <span class="req-star">*</span></div>
              <q-select
                v-model="createLocationSelect"
                :options="activeCreateCategory === 'DBMS' ? DBMS_LOCATION_OPTIONS : LOCATION_OPTIONS"
                borderless dense clearable class="field-input"
                @update:model-value="val => { if (val && val !== '기타') createFields['위치'] = val; else createFields['위치'] = '' }"
              />
              <q-input
                v-if="createLocationSelect === '기타'"
                v-model="createFields['위치']"
                borderless dense placeholder="위치 직접 입력" class="field-input q-mt-xs"
              />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">설명 <span class="req-star">*</span></div>
              <q-input v-model="createFields['설명']" borderless dense class="field-input" />
            </div>
          </div>
        </q-card-section>

        <!-- 운영체제 / 기종 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">{{ activeCreateCategory === 'DBMS' ? 'DBMS' : (activeCreateCategory === '네트워크' || activeCreateCategory === '정보보호시스템') ? '기종' : '운영체제' }}</span>
          </div>
          <div class="section-divider" />
          <!-- DBMS: DB 종류 + 시리즈 + 패치버전 -->
          <template v-if="activeCreateCategory === 'DBMS'">
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-4 form-field">
                <div class="field-label">DB 종류 <span class="req-star">*</span></div>
                <q-select
                  v-model="createFields['운영체제']"
                  :options="Object.keys(DBMS_TREE)"
                  borderless dense clearable class="field-input"
                  @update:model-value="() => { createDbSeries = ''; createFields['version'] = '' }"
                />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">시리즈 <span class="req-star">*</span></div>
                <q-select
                  v-if="createFields['운영체제']"
                  v-model="createDbSeries"
                  :options="Object.keys(DBMS_TREE[createFields['운영체제']] ?? {})"
                  borderless dense clearable class="field-input"
                  @update:model-value="(val) => { const p = DBMS_TREE[createFields['운영체제'] ?? '']?.[val ?? ''] ?? []; createFields['version'] = p.length ? '' : (val ?? '') }"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
              <div class="col-4 form-field">
                <div class="field-label">버전</div>
                <q-select
                  v-if="createDbSeries && (DBMS_TREE[createFields['운영체제'] ?? '']?.[createDbSeries] ?? []).length"
                  v-model="createFields['version']"
                  :options="DBMS_TREE[createFields['운영체제'] ?? '']?.[createDbSeries] ?? []"
                  borderless dense clearable class="field-input"
                />
                <div v-else-if="createDbSeries" class="field-input field-disabled">-</div>
                <div v-else class="field-input field-disabled">-</div>
              </div>
            </div>
            <div v-if="createEosStatusText" class="eos-banner q-mt-sm"
                 :class="createEosIsEos ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ createEosStatusText }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ createEosDateText }}</strong></span>
            </div>
          </template>
          <!-- 정보보호시스템: 기종 + 수량 + 제조사 -->
          <template v-else-if="activeCreateCategory === '정보보호시스템'">
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-4 form-field">
                <div class="field-label">기종 <span class="req-star">*</span></div>
                <q-input v-model="createFields['운영체제']" borderless dense class="field-input" placeholder="기종 입력" />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">수량</div>
                <q-input v-model="createFields['수량']" borderless dense class="field-input" type="number" placeholder="0" />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">제조사 <span class="req-star">*</span></div>
                <q-input v-model="createFields['제조사']" borderless dense class="field-input" placeholder="제조사 입력" />
              </div>
            </div>
            <div class="row q-col-gutter-x-md q-mt-sm">
              <div class="col-6 form-field">
                <div class="field-label">EoS 날짜 직접 입력</div>
                <q-input v-model="createManualEosDate" type="text" borderless dense class="field-input" placeholder="YYYY-MM" />
              </div>
            </div>
            <div v-if="createEosStatusText" class="eos-banner q-mt-sm"
                 :class="createEosIsEos ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ createEosStatusText }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ createEosDateText }}</strong></span>
            </div>
          </template>
          <!-- 네트워크: 자유 입력 -->
          <template v-else-if="activeCreateCategory === '네트워크'">
            <div class="row q-col-gutter-x-md q-mt-xs">
              <div class="col-12 form-field">
                <div class="field-label">기종 <span class="req-star">*</span></div>
                <q-input v-model="createFields['운영체제']" borderless dense class="field-input" placeholder="예: Cisco Nexus C93180YC-EX" />
              </div>
            </div>
            <!-- 자동 감지된 경우 -->
            <div v-if="createEosStatusText" class="eos-banner q-mt-sm"
                 :class="createEosIsEos ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ createEosStatusText }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ createEosDateText }}</strong></span>
            </div>
            <!-- 자동 감지 안 된 경우: 수동 입력 -->
            <div v-else-if="createFields['운영체제']" class="row q-col-gutter-x-md q-mt-sm">
              <div class="col-6 form-field">
                <div class="field-label">EoS 날짜 직접 입력</div>
                <q-input v-model="createManualEosDate" type="text" borderless dense class="field-input" placeholder="YYYY-MM" />
              </div>
            </div>
          </template>
          <!-- 일반: 캐스케이드 드롭다운 -->
          <template v-else>
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-3 form-field">
                <div class="field-label">OS 계열 <span class="req-star">*</span></div>
                <q-select
                  v-model="createOsFamily"
                  :options="Object.keys(OS_TREE)"
                  borderless dense clearable class="field-input"
                  @update:model-value="val => { createFields['운영체제'] = val === '기타' ? '기타' : ''; createOsMajor = ''; createFields['version'] = '' }"
                />
              </div>
              <div class="col-3 form-field">
                <div class="field-label">배포판</div>
                <div v-if="createOsFamily === '기타'" class="field-input field-disabled">기타</div>
                <q-select
                  v-else
                  v-model="createFields['운영체제']"
                  :options="osDistOptions(createOsFamily)"
                  borderless dense clearable class="field-input"
                  :disable="!createOsFamily"
                  @update:model-value="() => { createOsMajor = ''; createFields['version'] = '' }"
                />
              </div>
              <div class="col-3 form-field">
                <div class="field-label">메이저 버전</div>
                <q-select
                  v-if="createFields['운영체제'] && createOsFamily !== '기타'"
                  v-model="createOsMajor"
                  :options="osMajorOptions(createFields['운영체제'] ?? '')"
                  borderless dense clearable class="field-input"
                  @update:model-value="val => {
                    const minors = osMinorOptions(createFields['운영체제'] ?? '', val ?? '')
                    createFields['version'] = minors.length ? '' : (val ?? '')
                  }"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
              <div class="col-3 form-field">
                <div class="field-label">마이너 버전</div>
                <q-select
                  v-if="createOsMajor && osMinorOptions(createFields['운영체제'] ?? '', createOsMajor).length"
                  v-model="createFields['version']"
                  :options="osMinorOptions(createFields['운영체제'] ?? '', createOsMajor)"
                  borderless dense clearable class="field-input"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
            </div>
            <!-- EoS 자동 표시 -->
            <div v-if="createEosStatusText" class="eos-banner q-mt-sm"
                 :class="createEosIsEos ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ createEosStatusText }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ createEosDateText }}</strong></span>
            </div>
          </template>
          <div v-if="createFields[EOL_STATUS_KEY]" class="eos-banner q-mt-sm"
               :class="createFields[EOL_STATUS_KEY] === 'O' ? 'eos-banner--eos' : 'eos-banner--active'">
            <span class="eos-item"><span class="eos-item-label">EoL 여부</span><strong>{{ eolStatusLabel(createFields[EOL_STATUS_KEY]) }}</strong></span>
            <span class="eos-sep">·</span>
            <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ createFields[EOL_DATE_KEY] || '확인 불가' }}</strong></span>
          </div>
          <div class="row q-col-gutter-x-md q-mt-sm">
            <div class="col-6 form-field">
              <div class="field-label">EoL 종료 일자 직접 입력</div>
              <q-input v-model="createFields[EOL_DATE_KEY]" type="text" borderless dense class="field-input" placeholder="YYYY-MM" />
            </div>
          </div>
        </q-card-section>

        <!-- 도입 정보 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">도입 정보</span>
          </div>
          <div class="section-divider" />
          <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
            <div class="col-6 form-field">
              <div class="field-label">용도(상세)</div>
              <q-input v-model="createFields['용도']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">소속부서/사업</div>
              <q-input v-model="createFields['소속부서']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">제품명(모델명)</div>
              <q-input v-model="createFields['제품명']" borderless dense class="field-input" />
            </div>
            <div class="col-12 form-field">
              <div class="field-label">사양</div>
              <q-input v-model="createFields['사양']" borderless dense class="field-input" placeholder="예: G5217 3GHz 8C*2 RAM128GB 960GB" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입사업</div>
              <q-input v-model="createFields['도입사업']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">납품회사</div>
              <q-input v-model="createFields['납품회사']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">담당자</div>
              <q-input v-model="createFields['담당자']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입가격</div>
              <q-input v-model="createFields['도입가격']" borderless dense class="field-input" type="number" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입일자(취득일자)</div>
              <q-input v-model="createFields['도입일자']" borderless dense class="field-input" :type="('date' as any)" />
            </div>
          </div>
        </q-card-section>

        <!-- 기타 정보 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">기타 정보</span>
          </div>
          <div class="section-divider" />
          <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
            <div class="col-4 form-field">
              <div class="field-label">ISMS-P 대상 여부</div>
              <q-select
                v-model="createFields[ISMS_P_KEY]"
                :options="ismsPOptions"
                borderless dense emit-value map-options
                clearable
                class="field-input"
              />
            </div>
            <div class="col form-field">
              <div class="field-label">ISMS-P 비고</div>
              <q-input v-model="createFields['ISMS-P비고']" borderless dense class="field-input" />
            </div>
            <template v-if="activeCreateCategory === '서버' || !activeCreateCategory">
              <div class="col-4 form-field">
                <div class="field-label">VADA 설치여부</div>
                <q-select
                  v-model="createFields[VADA_KEY]"
                  :options="vadaOptions"
                  borderless dense emit-value map-options
                  clearable
                  class="field-input"
                />
              </div>
              <div class="col form-field">
                <div class="field-label">VADA 비고</div>
                <q-input v-model="createFields['VADA비고']" borderless dense class="field-input" />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">백신 여부</div>
                <q-select
                  v-model="createFields[ANTIVIRUS_KEY]"
                  :options="antivirusOptions"
                  borderless dense emit-value map-options
                  clearable
                  class="field-input"
                />
              </div>
              <div class="col form-field">
                <div class="field-label">백신 비고</div>
                <q-input v-model="createFields['백신비고']" borderless dense class="field-input" />
              </div>
            </template>
            <div class="col-12 form-field">
              <div class="field-label">비고</div>
              <q-input v-model="createFields['비고']" borderless dense class="field-input" />
            </div>
            <div class="col-12 form-field q-mt-xs">
              <div class="field-label">태그</div>
              <q-select
                v-model="createTags"
                use-input use-chips multiple
                hide-dropdown-icon
                input-debounce="0"
                new-value-mode="add-unique"
                borderless dense class="field-input"
                placeholder="#태그 입력 후 Enter"
              />
            </div>
          </div>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" v-close-popup class="q-mr-sm" />
          <q-btn
            class="create-btn"
            label="생성"
            :loading="actingType === 'create'"
            @click="doCreate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit base (ip/name) dialog -->
    <q-dialog v-model="editBaseDialog">
      <q-card style="width: 520px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">기본 정보 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            {{ editingBaseKey === 'ip' ? 'IP' : 'HostName' }} 수정
          </div>

          <q-input
            v-model="editBaseValue"
            outlined
            dense
            :label="editingBaseKey === 'ip' ? 'IP' : 'HostName'"
            class="q-mt-md"
          />
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="저장"
            :loading="actingType === 'editBase' && actingId === (selectedRow ? String(selectedRow.id) : null)"
            @click="doEditBase"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit field dialog -->
    <q-dialog v-model="editFieldDialog">
      <q-card style="width: 560px; max-width: 95vw;">
        <q-card-section>
          <div class="text-h6">필드 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Key: <b>{{ editFieldKey }}</b>
          </div>

          <!-- 수령일 / 변경일 -->
          <template v-if="editFieldKey === '수령일' || editFieldKey === '변경일'">
            <q-input
              v-model="editFieldText"
              :type="('date' as any)"
              outlined dense
              :label="editFieldKey"
              class="q-mt-md"
            />
          </template>

          <!-- 변경사항 -->
          <template v-else-if="editFieldKey === '변경사항'">
            <q-select
              v-model="editFieldText"
              :options="CHANGE_TYPE_OPTIONS"
              outlined dense emit-value map-options
              label="변경사항(신규/변경/폐기)"
              class="q-mt-md"
            />
          </template>

          <!-- VADA 설치 여부 -->
          <template v-else-if="editFieldKey === VADA_KEY">
            <q-select
              v-model="editFieldText"
              :options="vadaOptions"
              outlined dense emit-value map-options
              label="VADA 설치 여부"
              class="q-mt-md"
            />
          </template>

          <!-- 백신 여부 -->
          <template v-else-if="editFieldKey === ANTIVIRUS_KEY">
            <q-select
              v-model="editFieldText"
              :options="antivirusOptions"
              outlined dense emit-value map-options
              label="백신 여부"
              class="q-mt-md"
            />
          </template>

          <!-- ISMS-P 대상 여부 -->
          <template v-else-if="editFieldKey === ISMS_P_KEY">
            <q-select
              v-model="editFieldText"
              :options="ismsPOptions"
              outlined dense emit-value map-options
              label="ISMS-P 대상 여부"
              class="q-mt-md"
            />
          </template>

          <!-- 위치 드롭다운 -->
          <template v-else-if="editFieldKey === '위치'">
            <q-select
              v-model="editFieldLocationSelect"
              :options="LOCATION_OPTIONS"
              outlined dense clearable label="위치 선택"
              class="q-mt-md"
              @update:model-value="val => { if (val && val !== '기타') editFieldText = val; else editFieldText = '' }"
            />
            <q-input
              v-if="editFieldLocationSelect === '기타'"
              v-model="editFieldText"
              outlined dense label="위치 직접 입력"
              class="q-mt-sm" placeholder="위치를 입력하세요"
            />
          </template>

          <!-- 운영체제 cascading (Version도 통합) -->
          <template v-else-if="editFieldKey === '운영체제'">
            <q-select
              v-model="editFieldOsFamily"
              :options="Object.keys(OS_TREE)"
              outlined dense clearable label="OS 계열"
              class="q-mt-md"
              @update:model-value="editFieldText = ''; editFieldMajor = ''; editFieldVersionText = ''"
            />
            <q-select
              v-if="editFieldOsFamily"
              v-model="editFieldText"
              :options="osDistOptions(editFieldOsFamily)"
              outlined dense clearable label="배포판"
              class="q-mt-sm"
              @update:model-value="() => { editFieldMajor = ''; editFieldVersionText = '' }"
            />
            <template v-if="editFieldText && editFieldOsFamily !== '기타'">
              <q-select
                v-model="editFieldMajor"
                :options="osMajorOptions(editFieldText)"
                outlined dense clearable label="메이저 버전"
                class="q-mt-sm"
                @update:model-value="val => {
                  const minors = osMinorOptions(editFieldText, val ?? '')
                  editFieldVersionText = minors.length ? '' : (val ?? '')
                }"
              />
              <q-select
                v-if="editFieldMajor && osMinorOptions(editFieldText, editFieldMajor).length"
                v-model="editFieldVersionText"
                :options="osMinorOptions(editFieldText, editFieldMajor)"
                outlined dense clearable label="마이너 버전"
                class="q-mt-sm"
              />
            </template>
          </template>

          <!-- others: textarea for flexible -->
          <template v-else>
            <q-input
              v-model="editFieldText"
              type="textarea"
              outlined
              autogrow
              label="값"
              class="q-mt-md"
              hint="문자/숫자/boolean/JSON 모두 가능 (JSON은 그대로 입력)"
            />
          </template>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn
            color="primary"
            label="저장"
            :loading="actingType === 'editField' && actingId === (selectedRow ? String(selectedRow.id) : null)"
            @click="doEditField"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Export 컬럼 선택 다이얼로그 -->

    <!-- History drawer -->
    <q-drawer
      v-model="historyOpen"
      side="right"
      bordered
      overlay
      :width="420"
    >
      <div class="q-pa-md">
        <div class="row items-center q-gutter-sm">
          <div class="text-h6">변경 이력</div>
          <q-space />
          <q-btn flat dense icon="close" @click="historyOpen = false" />
        </div>

        <div v-if="historyTarget" class="q-mt-sm text-caption text-grey-7">
          <div><b>IP</b>: {{ historyTarget.ip }}</div>
          <div><b>Name</b>: {{ historyTarget.name }}</div>
          <div><b>ID</b>: {{ historyTarget.id }}</div>
        </div>

        <q-separator class="q-my-md" />

        <q-inner-loading :showing="historyLoading">
          <q-spinner size="32px" />
        </q-inner-loading>

        <q-list v-if="!historyLoading">
          <q-item v-for="h in historyItems" :key="h.id" clickable>
            <q-item-section>
              <q-item-label>
                <q-badge
                  :color="historyBadgeColor(h.action)"
                  outline
                  class="q-mr-sm"
                >
                  {{ h.action }}
                </q-badge>
                <span class="text-caption">
                  {{ formatKst(h.changedAt) }}
                </span>
              </q-item-label>
              <q-item-label caption>
                by {{ h.changedBy }}
              </q-item-label>

              <div v-if="h.diff?.length" class="q-mt-sm">
                <div class="text-caption text-grey-7 q-mb-xs">Changes</div>
                <div
                  v-for="d in h.diff.slice(0, 6)"
                  :key="d.path"
                  class="text-body2"
                >
                  <span class="text-grey-8">{{ d.path }}</span>
                  <span class="text-grey-6">: </span>
                  <span class="text-grey-9">{{ displayValue(d.before) }}</span>
                  <span class="text-grey-6"> → </span>
                  <span class="text-grey-9">{{ displayValue(d.after) }}</span>
                </div>
                <div v-if="h.diff.length > 6" class="text-caption text-grey-6 q-mt-xs">
                  +{{ h.diff.length - 6 }} more…
                </div>
              </div>
            </q-item-section>
          </q-item>

          <div v-if="historyItems.length === 0" class="text-grey-6 q-pa-md">
            이력이 없습니다.
          </div>
        </q-list>
      </div>
    </q-drawer>

    <!-- Row edit dialog -->
    <q-dialog v-model="rowEditDialog">
      <q-card class="server-form-card" v-if="rowEditTarget">
        <!-- 상단: 호스트명 & IP -->
        <q-card-section class="q-pb-sm row items-center">
          <div class="col">
            <div class="top-field-row">
              <span class="top-field-label">호스트명:</span>
              <q-input v-model="rowEditValues['__name__']" borderless dense class="top-field-input" />
            </div>
            <div class="top-field-row q-mt-sm">
              <span class="top-field-label">IP:</span>
              <q-input v-model="rowEditValues['__ip__']" borderless dense class="top-field-input" />
            </div>
          </div>
          <q-btn flat dense round icon="close" v-close-popup class="q-ml-md self-start" />
        </q-card-section>

        <!-- 기본 정보 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">기본 정보</span>
          </div>
          <div class="section-divider" />
        </q-card-section>
        <q-card-section class="q-py-md">
          <div class="row q-col-gutter-x-lg q-col-gutter-y-md">
            <div class="col-6 form-field">
              <div class="field-label">자산명</div>
              <q-input v-model="rowEditValues['서버명']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">구분</div>
              <q-input v-model="rowEditValues['구분']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">자산번호</div>
              <q-input v-model="rowEditValues['자산번호']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">RackNo.</div>
              <q-input v-model="rowEditValues['rack_no']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">Rack Unit No.</div>
              <q-input v-model="rowEditValues['rack_unit_no']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">자산관리번호</div>
              <q-input v-model="rowEditValues['자산관리번호']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">SN</div>
              <q-input v-model="rowEditValues['SN']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">위치</div>
              <q-select
                v-model="rowEditLocationSelect"
                :options="LOCATION_OPTIONS"
                dense borderless clearable class="field-input"
                @update:model-value="val => { if (val && val !== '기타') rowEditValues['위치'] = val; else rowEditValues['위치'] = '' }"
              />
              <q-input
                v-if="rowEditLocationSelect === '기타'"
                v-model="rowEditValues['위치']"
                dense borderless placeholder="위치 직접 입력" class="field-input q-mt-xs"
              />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">설명</div>
              <q-input v-model="rowEditValues['설명']" borderless dense class="field-input" />
            </div>
          </div>
        </q-card-section>

        <!-- 운영체제 / 기종 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">{{ (rowEditTarget?.fields?.['자산유형'] || category) === 'DBMS' ? 'DBMS' : ['네트워크', '정보보호시스템'].includes((rowEditTarget?.fields?.['자산유형'] || category) as string) ? '기종' : '운영체제' }}</span>
          </div>
          <div class="section-divider" />
          <!-- DBMS: DB 종류 + 시리즈 + 버전 cascade -->
          <template v-if="(rowEditTarget?.fields?.['자산유형'] || category) === 'DBMS'">
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-4 form-field">
                <div class="field-label">DB 종류</div>
                <q-select
                  v-model="rowEditValues['운영체제']"
                  :options="Object.keys(DBMS_TREE)"
                  dense borderless clearable class="field-input"
                  @update:model-value="() => { rowEditDbSeries = ''; rowEditValues['version'] = '' }"
                />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">시리즈</div>
                <q-select
                  v-if="rowEditValues['운영체제']"
                  v-model="rowEditDbSeries"
                  :options="Object.keys(DBMS_TREE[rowEditValues['운영체제']] ?? {})"
                  dense borderless clearable class="field-input"
                  @update:model-value="(val) => { const p = DBMS_TREE[rowEditValues['운영체제'] ?? '']?.[val ?? ''] ?? []; rowEditValues['version'] = p.length ? '' : (val ?? '') }"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
              <div class="col-4 form-field">
                <div class="field-label">버전</div>
                <q-select
                  v-if="rowEditDbSeries && (DBMS_TREE[rowEditValues['운영체제'] ?? '']?.[rowEditDbSeries] ?? []).length"
                  v-model="rowEditValues['version']"
                  :options="DBMS_TREE[rowEditValues['운영체제'] ?? '']?.[rowEditDbSeries] ?? []"
                  dense borderless clearable class="field-input"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
            </div>
            <div v-if="rowEditValues[EOS_STATUS_KEY]" class="eos-banner q-mt-sm"
                 :class="rowEditValues[EOS_STATUS_KEY] === 'EOS' ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ eosStatusLabel(rowEditValues[EOS_STATUS_KEY]) }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ rowEditValues[EOS_DATE_KEY] || '확인 불가' }}</strong></span>
            </div>
          </template>
          <!-- 네트워크 / 정보보호시스템: 자유 입력 -->
          <template v-else-if="['네트워크', '정보보호시스템'].includes((rowEditTarget?.fields?.['자산유형'] || category) as string)">
            <div class="row q-col-gutter-x-md q-mt-xs">
              <div class="col-12 form-field">
                <div class="field-label">기종</div>
                <q-input v-model="rowEditValues['운영체제']" borderless dense class="field-input" placeholder="예: Cisco Nexus C93180YC-EX" />
              </div>
            </div>
            <!-- 자동 감지된 경우 -->
            <div v-if="rowEditValues[EOS_STATUS_KEY] && !rowEditManualEosDate" class="eos-banner q-mt-sm"
                 :class="rowEditValues[EOS_STATUS_KEY] === 'EOS' ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ eosStatusLabel(rowEditValues[EOS_STATUS_KEY]) }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ rowEditValues[EOS_DATE_KEY] || '확인 불가' }}</strong></span>
            </div>
            <!-- 자동 감지 안 된 경우: 수동 입력 -->
            <div v-else-if="rowEditValues['운영체제']" class="row q-col-gutter-x-md q-mt-sm">
              <div class="col-6 form-field">
                <div class="field-label">EoS 날짜 직접 입력</div>
                <q-input v-model="rowEditManualEosDate" type="text" borderless dense class="field-input" placeholder="YYYY-MM" />
              </div>
              <div v-if="rowEditManualEosDate" class="col-12">
                <div class="eos-banner q-mt-xs"
                     :class="rowEditValues[EOS_STATUS_KEY] === 'EOS' ? 'eos-banner--eos' : 'eos-banner--active'">
                  <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ eosStatusLabel(rowEditValues[EOS_STATUS_KEY]) }}</strong></span>
                  <span class="eos-sep">·</span>
                  <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ rowEditValues[EOS_DATE_KEY] || '확인 불가' }}</strong></span>
                </div>
              </div>
            </div>
          </template>
          <!-- 일반: 캐스케이드 드롭다운 -->
          <template v-else>
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-3 form-field">
                <div class="field-label">OS 계열</div>
                <q-select
                  v-model="rowEditOsFamily"
                  :options="Object.keys(OS_TREE)"
                  dense borderless clearable class="field-input"
                  @update:model-value="val => {
                    if (val === '기타') { rowEditValues['운영체제'] = '기타'; rowEditMajor = ''; rowEditValues['version'] = ''; return }
                    const curDist = rowEditValues['운영체제'] ?? ''
                    if (!val || !osDistOptions(val).includes(curDist)) { rowEditValues['운영체제'] = ''; rowEditMajor = ''; rowEditValues['version'] = '' }
                    else { rowEditMajor = detectOsMajor(curDist, rowEditValues['version'] ?? '') }
                  }"
                />
              </div>
              <div class="col-3 form-field">
                <div class="field-label">배포판</div>
                <div v-if="rowEditOsFamily === '기타'" class="field-input field-disabled">기타</div>
                <q-select
                  v-else-if="rowEditOsFamily"
                  v-model="rowEditValues['운영체제']"
                  :options="osDistOptions(rowEditOsFamily)"
                  dense borderless clearable class="field-input"
                  @update:model-value="() => { rowEditMajor = ''; rowEditValues['version'] = '' }"
                />
                <q-input
                  v-else-if="rowEditValues['운영체제']"
                  v-model="rowEditValues['운영체제']"
                  borderless dense class="field-input"
                  placeholder="OS 직접 입력"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
              <div class="col-3 form-field">
                <div class="field-label">메이저 버전</div>
                <q-select
                  v-if="rowEditValues['운영체제'] && rowEditOsFamily !== '기타'"
                  v-model="rowEditMajor"
                  :options="osMajorOptions(rowEditValues['운영체제'] ?? '')"
                  dense borderless clearable class="field-input"
                  @update:model-value="val => {
                    const minors = osMinorOptions(rowEditValues['운영체제'] ?? '', val ?? '')
                    rowEditValues['version'] = minors.length ? '' : (val ?? '')
                  }"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
              <div class="col-3 form-field">
                <div class="field-label">마이너 버전</div>
                <q-select
                  v-if="rowEditMajor && osMinorOptions(rowEditValues['운영체제'] ?? '', rowEditMajor).length"
                  v-model="rowEditValues['version']"
                  :options="osMinorOptions(rowEditValues['운영체제'] ?? '', rowEditMajor)"
                  dense borderless clearable class="field-input"
                />
                <div v-else class="field-input field-disabled">-</div>
              </div>
            </div>
            <!-- EoS 자동 표시 -->
            <div v-if="rowEditValues[EOS_STATUS_KEY]" class="eos-banner q-mt-sm"
                 :class="rowEditValues[EOS_STATUS_KEY] === 'EOS' ? 'eos-banner--eos' : 'eos-banner--active'">
              <span class="eos-item"><span class="eos-item-label">EoS 여부</span><strong>{{ eosStatusLabel(rowEditValues[EOS_STATUS_KEY]) }}</strong></span>
              <span class="eos-sep">·</span>
              <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ rowEditValues[EOS_DATE_KEY] || '확인 불가' }}</strong></span>
            </div>
          </template>
          <div v-if="rowEditValues[EOL_STATUS_KEY]" class="eos-banner q-mt-sm"
               :class="rowEditValues[EOL_STATUS_KEY] === 'O' ? 'eos-banner--eos' : 'eos-banner--active'">
            <span class="eos-item"><span class="eos-item-label">EoL 여부</span><strong>{{ eolStatusLabel(rowEditValues[EOL_STATUS_KEY]) }}</strong></span>
            <span class="eos-sep">·</span>
            <span class="eos-item"><span class="eos-item-label">종료 일자</span><strong>{{ rowEditValues[EOL_DATE_KEY] || '확인 불가' }}</strong></span>
          </div>
          <div class="row q-col-gutter-x-md q-mt-sm">
            <div class="col-6 form-field">
              <div class="field-label">EoL 종료 일자 직접 입력</div>
              <q-input v-model="rowEditValues[EOL_DATE_KEY]" type="text" borderless dense class="field-input" placeholder="YYYY-MM" />
            </div>
          </div>
        </q-card-section>

        <!-- 도입 정보 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">도입 정보</span>
          </div>
          <div class="section-divider" />
          <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
            <div class="col-6 form-field">
              <div class="field-label">용도(상세)</div>
              <q-input v-model="rowEditValues['용도']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">소속부서/사업</div>
              <q-input v-model="rowEditValues['소속부서']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">제품명(모델명)</div>
              <q-input v-model="rowEditValues['제품명']" borderless dense class="field-input" />
            </div>
            <div class="col-12 form-field">
              <div class="field-label">사양</div>
              <q-input v-model="rowEditValues['사양']" borderless dense class="field-input" placeholder="예: G5217 3GHz 8C*2 RAM128GB 960GB" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입사업</div>
              <q-input v-model="rowEditValues['도입사업']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">납품회사</div>
              <q-input v-model="rowEditValues['납품회사']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">담당자</div>
              <q-input v-model="rowEditValues['담당자']" borderless dense class="field-input" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입가격</div>
              <q-input v-model="rowEditValues['도입가격']" borderless dense class="field-input" type="number" />
            </div>
            <div class="col-6 form-field">
              <div class="field-label">도입일자(취득일자)</div>
              <q-input v-model="rowEditValues['도입일자']" borderless dense class="field-input" :type="('date' as any)" />
            </div>
          </div>
        </q-card-section>

        <!-- 기타 정보 섹션 -->
        <q-card-section class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">기타 정보</span>
          </div>
          <div class="section-divider" />
          <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
            <div class="col-4 form-field">
              <div class="field-label">ISMS-P 대상 여부</div>
              <q-select
                v-model="rowEditValues[ISMS_P_KEY]"
                :options="ismsPOptions"
                borderless dense emit-value map-options
                clearable
                class="field-input"
              />
            </div>
            <div class="col form-field">
              <div class="field-label">ISMS-P 비고</div>
              <q-input v-model="rowEditValues['ISMS-P비고']" borderless dense class="field-input" />
            </div>
            <template v-if="!rowEditTarget?.fields?.['자산유형'] || rowEditTarget?.fields?.['자산유형'] === '서버'">
              <div class="col-4 form-field">
                <div class="field-label">VADA 설치여부</div>
                <q-select
                  v-model="rowEditValues[VADA_KEY]"
                  :options="vadaOptions"
                  borderless dense emit-value map-options
                  clearable
                  class="field-input"
                />
              </div>
              <div class="col form-field">
                <div class="field-label">VADA 비고</div>
                <q-input v-model="rowEditValues['VADA비고']" borderless dense class="field-input" />
              </div>
              <div class="col-4 form-field">
                <div class="field-label">백신 여부</div>
                <q-select
                  v-model="rowEditValues[ANTIVIRUS_KEY]"
                  :options="antivirusOptions"
                  borderless dense emit-value map-options
                  clearable
                  class="field-input"
                />
              </div>
              <div class="col form-field">
                <div class="field-label">백신 비고</div>
                <q-input v-model="rowEditValues['백신비고']" borderless dense class="field-input" />
              </div>
            </template>
            <div class="col-12 form-field">
              <div class="field-label">비고</div>
              <q-input v-model="rowEditValues['비고']" borderless dense class="field-input" />
            </div>
            <div class="col-12 form-field q-mt-xs">
              <div class="field-label">태그</div>
              <q-select
                v-model="rowEditTags"
                use-input use-chips multiple
                hide-dropdown-icon
                input-debounce="0"
                new-value-mode="add-unique"
                borderless dense class="field-input"
                placeholder="#태그 입력 후 Enter"
              />
            </div>
          </div>
        </q-card-section>

        <!-- 추가 필드 섹션 (커스텀/임포트 필드) -->
        <q-card-section v-if="rowEditExtraFields.length" class="q-py-sm">
          <div class="section-title-row">
            <span class="section-title">추가 필드</span>
          </div>
          <div class="section-divider" />
          <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
            <div v-for="k in rowEditExtraFields" :key="k" class="col-6 form-field">
              <div class="field-label">{{ fieldLabel(k) }}</div>
              <q-input :model-value="rowEditValues[k] ?? ''" @update:model-value="v => { rowEditValues[k] = String(v) }" borderless dense class="field-input" />
            </div>
          </div>
        </q-card-section>

        <q-separator />
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" v-close-popup class="q-mr-sm" />
          <q-btn class="create-btn" label="저장" :loading="rowEditSaving" @click="doRowEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Detail view dialog -->
    <q-dialog v-model="detailDialog">
      <q-card class="server-form-card" v-if="detailTarget" style="max-height: 90vh; display: flex; flex-direction: column;">
        <!-- 상단: 호스트명 & IP -->
        <q-card-section class="q-pb-sm row items-center" style="flex-shrink: 0;">
          <div class="col">
            <div class="top-field-row">
              <span class="top-field-label">호스트명:</span>
              <span class="top-field-value">{{ detailTarget.name }}</span>
            </div>
            <div class="top-field-row q-mt-sm">
              <span class="top-field-label">IP:</span>
              <span class="top-field-value">{{ detailTarget.ip }}</span>
            </div>
          </div>
          <q-btn flat dense round icon="close" v-close-popup class="q-ml-md self-start" />
        </q-card-section>

        <div class="col scroll" style="min-height: 0; overflow-y: auto;">
          <!-- 기본 정보 -->
          <q-card-section class="q-py-sm">
            <div class="section-title-row">
              <span class="section-title">기본 정보</span>
            </div>
            <div class="section-divider" />
          </q-card-section>
          <q-card-section class="q-py-md">
            <div class="row q-col-gutter-x-lg q-col-gutter-y-md">
              <div class="col-6 form-field">
                <div class="field-label">자산명</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['서버명']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">구분</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['구분']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">자산번호</div>
                <div class="detail-value">{{ displayValue(detailTarget.assetNo ?? detailTarget.fields?.['자산번호']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">RackNo.</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['rack_no']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">Rack Unit No.</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['rack_unit_no']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">자산관리번호</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['자산관리번호']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">SN</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['SN']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">위치</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['위치']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">설명</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['설명']) }}</div>
              </div>
            </div>
          </q-card-section>

          <!-- 운영체제 / 기종 -->
          <q-card-section class="q-py-sm">
            <div class="section-title-row">
              <span class="section-title">{{ detailTarget.fields?.['자산유형'] === 'DBMS' ? 'DBMS' : ['네트워크', '정보보호시스템'].includes(detailTarget.fields?.['자산유형'] as string) ? '기종' : '운영체제' }}</span>
            </div>
            <div class="section-divider" />
            <!-- 네트워크 / 정보보호시스템: 기종 텍스트만 표시 -->
            <div v-if="['네트워크', '정보보호시스템'].includes(detailTarget.fields?.['자산유형'] as string)" class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-12 form-field">
                <div class="field-label">기종</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['운영체제']) }}</div>
              </div>
            </div>
            <!-- DBMS: DB 종류 + 버전 + EoS -->
            <template v-else-if="detailTarget.fields?.['자산유형'] === 'DBMS'">
              <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
                <div class="col-4 form-field">
                  <div class="field-label">DB 종류</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['운영체제']) }}</div>
                </div>
                <div class="col form-field">
                  <div class="field-label">버전</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['version']) }}</div>
                </div>
              </div>
              <div class="row q-col-gutter-x-md q-mt-sm">
                <div class="col-4 form-field">
                  <div class="field-label">EoS 여부</div>
                  <div class="detail-value">
                    <template v-if="detailTarget.fields?.['운영체제']">
                      <q-badge :color="detailTarget.fields?.[EOS_STATUS_KEY] ? eosStatusColor(detailTarget.fields?.[EOS_STATUS_KEY]) : 'grey'" outline>
                        {{ detailTarget.fields?.[EOS_STATUS_KEY] ? eosStatusLabel(detailTarget.fields?.[EOS_STATUS_KEY]) : '확인 불가' }}
                      </q-badge>
                    </template>
                    <q-badge v-else color="grey" outline>확인 불가</q-badge>
                  </div>
                </div>
                <div class="col form-field">
                  <div class="field-label">EoS 종료 일자</div>
                  <div class="detail-value">{{ detailTarget.fields?.[EOS_DATE_KEY] || '확인 불가' }}</div>
                </div>
              </div>
            </template>
            <!-- 일반: OS + EoS 정보 -->
            <template v-else>
              <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
                <div class="col-4 form-field">
                  <div class="field-label">배포판</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['운영체제']) }}</div>
                </div>
                <div class="col form-field">
                  <div class="field-label">버전</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['version']) }}</div>
                </div>
              </div>
              <div class="row q-col-gutter-x-md q-mt-sm">
                <div class="col-4 form-field">
                  <div class="field-label">EoS 여부</div>
                  <div class="detail-value">
                    <template v-if="detailTarget.fields?.['운영체제']">
                      <q-badge :color="detailTarget.fields?.[EOS_STATUS_KEY] ? eosStatusColor(detailTarget.fields?.[EOS_STATUS_KEY]) : 'grey'" outline>
                        {{ detailTarget.fields?.[EOS_STATUS_KEY] ? eosStatusLabel(detailTarget.fields?.[EOS_STATUS_KEY]) : '확인 불가' }}
                      </q-badge>
                    </template>
                    <q-badge v-else color="grey" outline>확인 불가</q-badge>
                  </div>
                </div>
                <div class="col form-field">
                  <div class="field-label">EoS 종료 일자</div>
                  <div class="detail-value">{{ detailTarget.fields?.[EOS_DATE_KEY] || '확인 불가' }}</div>
                </div>
              </div>
            </template>
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-4 form-field">
                <div class="field-label">EoL 여부</div>
                <div class="detail-value">
                  <q-badge v-if="detailTarget.fields?.[EOL_STATUS_KEY]" :color="eolStatusColor(detailTarget.fields?.[EOL_STATUS_KEY])" outline>
                    {{ eolStatusLabel(detailTarget.fields?.[EOL_STATUS_KEY]) }}
                  </q-badge>
                  <span v-else>-</span>
                </div>
              </div>
              <div class="col form-field">
                <div class="field-label">EoL 종료 일자</div>
                <div class="detail-value">{{ detailTarget.fields?.[EOL_DATE_KEY] || '-' }}</div>
              </div>
            </div>
          </q-card-section>

          <!-- 도입 정보 -->
          <q-card-section class="q-py-sm">
            <div class="section-title-row">
              <span class="section-title">도입 정보</span>
            </div>
            <div class="section-divider" />
            <div class="row q-col-gutter-x-md q-col-gutter-y-md q-mt-xs">
              <div class="col-6 form-field">
                <div class="field-label">용도(상세)</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['용도']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">소속부서/사업</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['소속부서']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">제품명(모델명)</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['제품명']) }}</div>
              </div>
              <div class="col-12 form-field">
                <div class="field-label">사양</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['사양']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">도입사업</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['도입사업']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">납품회사</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['납품회사']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">담당자</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['담당자']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">도입가격</div>
                <div class="detail-value">{{ displayPrice(detailTarget.fields?.['도입가격']) }}</div>
              </div>
              <div class="col-6 form-field">
                <div class="field-label">도입일자(취득일자)</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['도입일자']) }}</div>
              </div>
            </div>
          </q-card-section>

          <!-- 기타 정보 -->
          <q-card-section class="q-py-sm">
            <div class="section-title-row">
              <span class="section-title">기타 정보</span>
            </div>
            <div class="section-divider" />
            <div class="row q-col-gutter-x-md q-mt-xs">
              <div class="col-4 form-field">
                <div class="field-label">ISMS-P 대상 여부</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.[ISMS_P_KEY]) }}</div>
              </div>
              <div class="col form-field">
                <div class="field-label">ISMS-P 비고</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['ISMS-P비고']) }}</div>
              </div>
            </div>
            <template v-if="!detailTarget.fields?.['자산유형'] || detailTarget.fields?.['자산유형'] === '서버'">
              <div class="row q-col-gutter-x-md q-mt-sm">
                <div class="col-4 form-field">
                  <div class="field-label">백신 여부</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.[ANTIVIRUS_KEY]) }}</div>
                </div>
                <div class="col form-field">
                  <div class="field-label">백신 비고</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['백신비고']) }}</div>
                </div>
              </div>
              <div class="row q-col-gutter-x-md q-mt-sm">
                <div class="col-4 form-field">
                  <div class="field-label">VADA 설치여부</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.[VADA_KEY]) }}</div>
                </div>
                <div class="col form-field">
                  <div class="field-label">VADA 비고</div>
                  <div class="detail-value">{{ displayValue(detailTarget.fields?.['VADA비고']) }}</div>
                </div>
              </div>
            </template>
            <div class="row q-col-gutter-x-md q-mt-sm">
              <div class="col-12 form-field">
                <div class="field-label">비고</div>
                <div class="detail-value">{{ displayValue(detailTarget.fields?.['비고']) }}</div>
              </div>
            </div>
          </q-card-section>

        </div>

        <q-separator style="flex-shrink: 0;" />
        <!-- 하단: 태그(왼쪽) + 버튼(오른쪽) -->
        <div class="row items-center q-px-md q-py-sm" style="flex-shrink: 0;">
          <div class="row q-gutter-xs flex-wrap col">
            <q-chip
              v-for="tag in (detailTarget.fields?.[TAGS_KEY] as string[] ?? [])"
              :key="tag"
              square dense
              color="grey-3" text-color="grey-8"
              class="detail-tag-chip"
              style="font-size: 11px; height: 20px; padding: 0 6px;"
            >#{{ tag }}</q-chip>
          </div>
          <div class="row q-gutter-xs" style="flex-shrink:0">
            <q-btn flat label="닫기" v-close-popup />
            <q-btn v-if="!detailTarget?.isDeleted" class="create-btn" icon="edit" label="편집" @click="detailDialog = false; openRowEdit(detailTarget!)" />
          </div>
        </div>
      </q-card>
    </q-dialog>

    <!-- 삭제 확인 다이얼로그 -->
    <q-dialog v-model="deleteDialog" persistent>
      <q-card style="min-width: 400px;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6 text-negative">삭제 확인</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section v-if="deleteTarget">
          <div class="text-body2 q-mb-md">
            <span class="text-weight-bold">{{ deleteTarget.ip }}</span> /
            <span class="text-weight-bold">{{ deleteTarget.name }}</span>
            을(를) 삭제합니다.
          </div>
          <div class="field-label q-mb-xs">삭제 사유 (선택)</div>
          <q-input
            v-model="deleteReason"
            type="textarea"
            outlined
            dense
            rows="3"
            placeholder="삭제 사유를 입력하세요"
          />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="negative" label="삭제" :loading="actingType === 'delete'" @click="doDelete(deleteTarget!)" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 컬럼 상세보기 다이얼로그 -->
    <q-dialog v-model="colVisDialog">
      <q-card style="min-width:460px; max-width:560px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">컬럼 표시 설정</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <!-- 프리셋 영역 -->
        <q-card-section class="q-pt-sm q-pb-xs">
          <div class="text-caption text-grey-7 q-mb-xs">저장된 프리셋</div>
          <div v-if="colPresets.length === 0" class="text-caption text-grey-5">저장된 프리셋이 없습니다.</div>
          <div v-else class="row q-gutter-xs flex-wrap">
            <q-chip
              v-for="p in colPresets"
              :key="p.name"
              clickable
              color="blue-1"
              text-color="blue-9"
              @click="applyPreset(p)"
            >
              {{ p.name }}
              <q-btn flat round dense icon="close" size="xs" color="grey-6" class="q-ml-xs" @click.stop="deletePreset(p.name)" />
            </q-chip>
          </div>
          <div class="row q-gutter-sm q-mt-sm items-center">
            <q-input v-model="newPresetName" outlined dense label="프리셋 이름" style="flex:1" @keyup.enter="savePreset" />
            <q-btn color="primary" label="현재 설정 저장" unelevated @click="savePreset" :disable="!newPresetName.trim()" />
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section style="max-height:360px; overflow-y:auto">
          <div class="text-caption text-grey-7 q-mb-xs">드래그로 순서 변경 / 체크로 표시 여부 설정</div>
          <draggable v-model="tempColItems" item-key="key" handle=".drag-handle">
            <template #item="{ element }">
              <div class="row items-center q-py-xs col-item">
                <q-icon name="drag_indicator" class="drag-handle cursor-grab text-grey-5 q-mr-xs" size="18px" />
                <q-checkbox v-model="element.visible" :label="element.label" dense />
              </div>
            </template>
          </draggable>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="전체 선택" @click="tempColItems.forEach(c => c.visible = true)" />
          <q-btn flat label="전체 해제" @click="tempColItems.forEach(c => c.visible = false)" />
          <q-btn color="primary" label="적용" @click="applyColVis" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 자산 유형 선택 다이얼로그 (전체 탭에서 자산 추가) -->
    <q-dialog v-model="assetTypeDialog">
      <q-card style="min-width:320px">
        <q-card-section>
          <div class="text-h6">자산 유형 선택</div>
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="selectedAssetType"
            :options="pendingImport ? ['전체 (Excel 기준)', '서버', '네트워크', 'DBMS', '정보보호시스템', 'VMware'] : ['서버', '네트워크', 'DBMS', '정보보호시스템', 'VMware']"
            outlined dense label="유형 선택"
          />
          <div v-if="pendingImport && selectedAssetType === '전체 (Excel 기준)'" class="text-caption text-grey q-mt-xs">
            Excel 파일의 자산유형 컬럼값을 그대로 사용합니다
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="확인" :disable="!selectedAssetType" @click="onAssetTypeConfirm" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Import 비밀번호 다이얼로그 -->
    <q-dialog v-model="importPasswordDialog" persistent>
      <q-card style="min-width:320px">
        <q-card-section>
          <div class="text-h6">파일 비밀번호 입력</div>
          <div class="text-caption text-grey q-mt-xs">선택한 파일이 암호로 보호되어 있습니다.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="importPassword"
            :type="importPasswordVisible ? 'text' : 'password'"
            outlined dense autofocus
            label="비밀번호"
            @keyup.enter="importPassword && onImportPasswordConfirm()"
          >
            <template #append>
              <q-icon
                :name="importPasswordVisible ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="importPasswordVisible = !importPasswordVisible"
              />
            </template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="importPasswordDialog = false; importPassword = ''" />
          <q-btn color="primary" label="확인" :disable="!importPassword" @click="onImportPasswordConfirm" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Import 결과 다이얼로그 (실패 / 건너뜀) -->
    <q-dialog v-model="importFailDialog" persistent>
      <q-card style="min-width: min(900px, 92vw); max-height: 80vh; display: flex; flex-direction: column;">
        <q-card-section class="row items-center q-pb-sm" style="flex-shrink:0">
          <q-icon name="assignment_late" color="warning" size="sm" class="q-mr-sm" />
          <div class="text-h6">Import 처리 결과</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <!-- 탭 -->
        <q-tabs v-model="importResultTab" dense align="left" class="q-px-md" style="flex-shrink:0">
          <q-tab name="failed" icon="error_outline" label="실패">
            <q-badge v-if="importFailedRows.filter(r => !r.retrySuccess).length" color="negative" floating>
              {{ importFailedRows.filter(r => !r.retrySuccess).length }}
            </q-badge>
          </q-tab>
          <q-tab name="skipped" icon="skip_next" label="건너뜀">
            <q-badge v-if="importSkippedRows.length" color="grey-6" floating>
              {{ importSkippedRows.length }}
            </q-badge>
          </q-tab>
          <q-tab name="separate" icon="add_circle_outline" label="별도 저장">
            <q-badge v-if="duplicateSkippedRows.length" color="teal" floating>
              {{ duplicateSkippedRows.length }}
            </q-badge>
          </q-tab>
        </q-tabs>

        <q-separator style="flex-shrink:0" />

        <div style="flex:1; overflow-y:auto;">
          <!-- 실패 탭 -->
          <q-tab-panels v-model="importResultTab" animated>
            <q-tab-panel name="failed" class="q-pa-none">
              <div v-if="importFailedRows.length === 0" class="q-pa-md text-grey-6 text-center">실패 항목이 없습니다.</div>
              <div v-else class="text-caption text-grey-6 q-px-md q-pt-sm q-pb-xs">
                Import 중 오류가 발생한 항목입니다. 수정하거나 재시도할 수 있습니다.
              </div>
              <q-list separator>
                <q-item
                  v-for="(row, idx) in importFailedRows"
                  :key="idx"
                  class="q-pa-sm"
                  :class="row.retrySuccess ? 'bg-green-1' : ''"
                >
                  <!-- 읽기 모드 -->
                  <template v-if="failEditIdx !== idx">
                    <q-item-section>
                      <div class="row items-center q-gutter-xs flex-wrap">
                        <q-badge color="grey-5" :label="`${row.rowIndex}행`" />
                        <q-badge :color="row.isNew ? 'blue' : 'orange'" :label="row.isNew ? '신규' : '업데이트'" />
                        <span class="text-mono text-weight-medium">{{ row.ip }}</span>
                        <span class="text-grey-7 q-ml-xs">{{ row.name }}</span>
                        <q-badge v-if="!row.retrySuccess" color="negative" outline class="q-ml-sm">{{ row.error }}</q-badge>
                        <q-badge v-else color="positive" label="성공" class="q-ml-sm" />
                      </div>
                      <!-- 충돌 레코드 비교표 -->
                      <template v-if="!row.retrySuccess && row.conflictWith">
                        <div class="text-caption text-blue-grey-7 q-mt-sm q-mb-xs">겹치는 기존 레코드 비교</div>
                        <table class="conflict-diff-table">
                          <thead><tr><th>필드</th><th>기존 값</th><th>Import 값</th></tr></thead>
                          <tbody>
                            <tr :class="row.conflictWith.ip !== row.ip ? 'diff-row' : ''">
                              <td>IP</td><td>{{ row.conflictWith.ip || '—' }}</td><td>{{ row.ip || '—' }}</td>
                            </tr>
                            <tr :class="row.conflictWith.name !== row.name ? 'diff-row' : ''">
                              <td>HostName</td><td>{{ row.conflictWith.name || '—' }}</td><td>{{ row.name || '—' }}</td>
                            </tr>
                            <tr
                              v-for="k in [...new Set([...Object.keys(row.conflictWith.fields ?? {}), ...Object.keys(row.fields)])]"
                              :key="k"
                              :class="String(row.conflictWith.fields?.[k] ?? '') !== String(row.fields[k] ?? '') ? 'diff-row' : ''"
                            >
                              <td>{{ fieldLabel(k) }}</td>
                              <td>{{ row.conflictWith.fields?.[k] ?? '—' }}</td>
                              <td>{{ row.fields[k] ?? '—' }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </template>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div v-if="!row.retrySuccess" class="column q-gutter-xs">
                        <q-btn v-if="row.conflictWith" dense unelevated color="orange-8" size="sm" icon="save" label="강제 저장" :loading="row.retrying" @click="forceApplyFailed(idx)" />
                        <q-btn dense flat size="sm" icon="edit" label="수정" @click="openFailEdit(idx)" />
                        <q-btn dense flat size="sm" icon="refresh" label="재시도" :loading="row.retrying" @click="retryFailRow(idx)" />
                      </div>
                      <q-icon v-else name="check_circle" color="positive" size="sm" />
                    </q-item-section>
                  </template>

                  <!-- 편집 모드 -->
                  <template v-else>
                    <q-item-section>
                      <div class="row q-gutter-sm q-mb-sm">
                        <q-input v-model="failEditForm.ip" label="IP" dense outlined style="min-width:150px" />
                        <q-input v-model="failEditForm.name" label="HostName" dense outlined style="min-width:150px" />
                      </div>
                      <div class="row q-gutter-sm flex-wrap">
                        <q-input
                          v-for="k in Object.keys(failEditForm.fields)"
                          :key="k"
                          v-model="failEditForm.fields[k]"
                          :label="fieldLabel(k)"
                          dense outlined style="min-width:140px; flex: 1 1 140px"
                        />
                      </div>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div class="column q-gutter-xs">
                        <q-btn dense unelevated color="primary" size="sm" icon="refresh" label="저장 후 재시도" :loading="failEditSaving" @click="saveAndRetry(idx)" />
                        <q-btn dense flat size="sm" icon="close" label="취소" @click="failEditIdx = -1" />
                      </div>
                    </q-item-section>
                  </template>
                </q-item>
              </q-list>
            </q-tab-panel>

            <!-- 건너뜀 탭 -->
            <q-tab-panel name="skipped" class="q-pa-none">
              <div v-if="importSkippedRows.length === 0" class="q-pa-md text-grey-6 text-center">건너뜀 항목이 없습니다.</div>
              <div v-else class="text-caption text-grey-6 q-px-md q-pt-sm q-pb-xs">
                필수 값이 없어 건너뛰어진 항목입니다. 수정 후 재시도할 수 있습니다.
              </div>
              <q-list separator>
                <q-item
                  v-for="(row, idx) in importSkippedRows"
                  :key="idx"
                  class="q-pa-sm"
                  :class="row.retrySuccess ? 'bg-green-1' : ''"
                >
                  <!-- 읽기 모드 -->
                  <template v-if="skipEditIdx !== idx">
                    <q-item-section>
                      <!-- 행 번호 + IP + HostName -->
                      <div class="row items-center q-gutter-xs flex-wrap q-mb-xs">
                        <q-badge color="grey-5" :label="`${row.rowIndex}행`" />
                        <span v-if="row.ip" class="text-mono text-weight-medium">{{ row.ip }}</span>
                        <span v-else class="text-grey-5 text-italic text-caption">IP 없음</span>
                        <span v-if="row.name" class="text-grey-7">{{ row.name }}</span>
                        <q-badge v-if="row.retrySuccess" color="positive" label="성공" />
                      </div>
                      <!-- 상세 이유 -->
                      <div v-if="!row.retrySuccess" class="row items-start q-gutter-xs">
                        <q-icon name="info" color="warning" size="14px" class="q-mt-xs" style="flex-shrink:0" />
                        <span class="text-caption text-orange-9">{{ row.reason }}</span>
                      </div>
                      <!-- 충돌 레코드 비교표 -->
                      <template v-if="!row.retrySuccess && row.conflictWith">
                        <div class="text-caption text-blue-grey-7 q-mt-sm q-mb-xs">겹치는 기존 레코드 비교</div>
                        <table class="conflict-diff-table">
                          <thead><tr><th>필드</th><th>기존 값</th><th>Import 값</th></tr></thead>
                          <tbody>
                            <tr v-if="row.ip || row.conflictWith.ip" :class="row.conflictWith.ip !== row.ip ? 'diff-row' : ''">
                              <td>IP</td><td>{{ row.conflictWith.ip || '—' }}</td><td>{{ row.ip || '—' }}</td>
                            </tr>
                            <tr :class="row.conflictWith.name !== row.name ? 'diff-row' : ''">
                              <td>HostName</td><td>{{ row.conflictWith.name || '—' }}</td><td>{{ row.name || '—' }}</td>
                            </tr>
                            <tr
                              v-for="k in [...new Set([...Object.keys(row.conflictWith.fields ?? {}), ...Object.keys(row.rawData).filter(k2 => k2 !== 'ip' && k2 !== 'name')])]"
                              :key="k"
                              :class="String(row.conflictWith.fields?.[k] ?? '') !== String(row.rawData[k] ?? '') ? 'diff-row' : ''"
                            >
                              <td>{{ fieldLabel(k) }}</td>
                              <td>{{ row.conflictWith.fields?.[k] ?? '—' }}</td>
                              <td>{{ row.rawData[k] ?? '—' }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </template>
                      <!-- 원본 데이터 (충돌 없을 때만) -->
                      <div v-if="!row.retrySuccess && !row.conflictWith && Object.keys(row.rawData).length > 0" class="q-mt-xs row q-gutter-xs flex-wrap">
                        <q-chip
                          v-for="(val, key) in row.rawData"
                          :key="key"
                          dense square size="sm" color="grey-2" text-color="grey-8"
                        >
                          <span class="text-weight-medium q-mr-xs">{{ fieldLabel(String(key)) }}:</span>{{ val }}
                        </q-chip>
                      </div>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div v-if="!row.retrySuccess" class="column q-gutter-xs">
                        <q-btn v-if="row.conflictWith" dense unelevated color="orange-8" size="sm" icon="save" label="강제 저장" :loading="row.retrying" @click="forceApplySkip(idx)" />
                        <q-btn dense flat size="sm" icon="edit" label="수정" @click="openSkipEdit(idx)" />
                        <q-btn dense flat size="sm" icon="refresh" label="재시도" :loading="row.retrying" @click="retrySkipRow(idx)" />
                      </div>
                      <q-icon v-else name="check_circle" color="positive" size="sm" />
                    </q-item-section>
                  </template>

                  <!-- 편집 모드 -->
                  <template v-else>
                    <q-item-section>
                      <div class="row q-gutter-sm q-mb-sm">
                        <q-input v-model="skipEditForm.ip" label="IP" dense outlined style="min-width:150px" />
                        <q-input v-model="skipEditForm.name" label="HostName" dense outlined style="min-width:150px" />
                      </div>
                      <div class="row q-gutter-sm flex-wrap">
                        <q-input
                          v-for="k in Object.keys(skipEditForm.fields)"
                          :key="k"
                          v-model="skipEditForm.fields[k]"
                          :label="fieldLabel(String(k))"
                          dense outlined style="min-width:140px; flex: 1 1 140px"
                        />
                      </div>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div class="column q-gutter-xs">
                        <q-btn dense unelevated color="primary" size="sm" icon="refresh" label="저장 후 재시도" :loading="skipEditSaving" @click="saveAndRetrySkip(idx)" />
                        <q-btn dense flat size="sm" icon="close" label="취소" @click="skipEditIdx = -1" />
                      </div>
                    </q-item-section>
                  </template>
                </q-item>
              </q-list>
            </q-tab-panel>

            <!-- 별도 저장 탭 -->
            <q-tab-panel name="separate" class="q-pa-none">
              <div v-if="duplicateSkippedRows.length === 0" class="q-pa-md text-grey-6 text-center">별도 저장할 중복 항목이 없습니다.</div>
              <div v-else class="text-caption text-grey-6 q-px-md q-pt-sm q-pb-xs">
                중복으로 건너뛰어진 항목을 새 레코드로 별도 저장합니다. 자산번호가 겹치면 비워두거나 수정 후 저장하세요.
              </div>
              <q-list separator>
                <q-item
                  v-for="(row, idx) in duplicateSkippedRows"
                  :key="idx"
                  class="q-pa-sm"
                  :class="row.separateSaved ? 'bg-green-1' : ''"
                >
                  <template v-if="separateEditIdx !== idx">
                    <q-item-section>
                      <div class="row items-center q-gutter-xs flex-wrap q-mb-xs">
                        <q-badge color="grey-5" :label="`${row.rowIndex}행`" />
                        <span v-if="row.ip" class="text-mono text-weight-medium">{{ row.ip }}</span>
                        <span v-else class="text-grey-5 text-italic text-caption">IP 없음</span>
                        <span v-if="row.name" class="text-grey-7">{{ row.name }}</span>
                        <q-badge v-if="row.separateSaved" color="positive" label="저장됨" />
                        <q-badge v-if="row.separateError" color="negative" outline :label="row.separateError" />
                      </div>
                      <div class="row items-start q-gutter-xs q-mb-xs">
                        <q-icon name="info" color="grey-5" size="14px" class="q-mt-xs" style="flex-shrink:0" />
                        <span class="text-caption text-grey-7">{{ row.reason }}</span>
                      </div>
                      <!-- 원본 데이터 칩 -->
                      <div class="row q-gutter-xs flex-wrap">
                        <q-chip
                          v-for="(val, key) in row.rawData"
                          :key="key"
                          dense square size="sm" color="grey-2" text-color="grey-8"
                        >
                          <span class="text-weight-medium q-mr-xs">{{ fieldLabel(String(key)) }}:</span>{{ val }}
                        </q-chip>
                      </div>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div v-if="!row.separateSaved" class="column q-gutter-xs">
                        <q-btn dense unelevated color="teal" size="sm" icon="add_circle_outline" label="별도 저장" :loading="row.separateSaving" @click="saveDuplicateAsNew(idx)" />
                        <q-btn dense flat size="sm" icon="edit" label="수정 후 저장" @click="openSeparateEdit(idx)" />
                      </div>
                      <q-icon v-else name="check_circle" color="positive" size="sm" />
                    </q-item-section>
                  </template>

                  <!-- 편집 모드 -->
                  <template v-else>
                    <q-item-section>
                      <div class="row q-gutter-sm q-mb-sm">
                        <q-input v-model="separateEditForm.ip" label="IP" dense outlined style="min-width:150px" />
                        <q-input v-model="separateEditForm.name" label="HostName" dense outlined style="min-width:150px" />
                      </div>
                      <div class="row q-gutter-sm flex-wrap">
                        <q-input
                          v-for="k in Object.keys(separateEditForm.fields)"
                          :key="k"
                          v-model="separateEditForm.fields[k]"
                          :label="fieldLabel(k)"
                          dense outlined style="min-width:140px; flex: 1 1 140px"
                        />
                      </div>
                    </q-item-section>
                    <q-item-section side style="align-self:flex-start; padding-top:4px">
                      <div class="column q-gutter-xs">
                        <q-btn dense unelevated color="teal" size="sm" icon="add_circle_outline" label="별도 저장" :loading="row.separateSaving" @click="saveSeparateEdit(idx)" />
                        <q-btn dense flat size="sm" icon="close" label="취소" @click="separateEditIdx = -1" />
                      </div>
                    </q-item-section>
                  </template>
                </q-item>
              </q-list>
            </q-tab-panel>
          </q-tab-panels>
        </div>

        <q-separator style="flex-shrink:0" />
        <q-card-actions align="right" style="flex-shrink:0">
          <q-btn
            v-if="importResultTab === 'failed' && importFailedRows.length > 0"
            flat icon="refresh" label="전체 재시도"
            :loading="retryingAll"
            :disable="importFailedRows.every(r => r.retrySuccess)"
            @click="retryAllFailed"
          />
          <q-btn flat label="닫기" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as XLSX from 'xlsx'
import { useQuasar, type QTableProps } from 'quasar'
import draggable from 'vuedraggable'
import { api } from 'boot/axios'

import type { ServerAsset, AssetHistory, FieldsMap, FieldValue, EosActionStatus } from 'src/types/assets'
import { EOS_STATUS_KEY, EOS_DATE_KEY } from 'src/types/assets'
import { fetchEosMap } from 'src/services/eosData'
import { OS_TREE } from 'src/constants/osVersions'
import { DBMS_TREE } from 'src/constants/dbmsVersions'
import {
  detectOsFamily, resolveDistName, osDistOptions, osMajorOptions, osMinorOptions, detectOsMajor,
  getAutoEos, getNetworkEos,
} from 'src/services/eosDetection'

import { listServers, createServer, patchServer, deleteServer, restoreServer, getServerHistory } from 'src/services/assets'
import { eolStatusColor, eolStatusLabel, getAutoEol } from 'src/services/eolData'

const VADA_KEY = 'vada_installed' as const
const ANTIVIRUS_KEY = 'antivirus_installed' as const
const ISMS_P_KEY = 'isms_p_target' as const
const TAGS_KEY = 'tags' as const
const EOL_STATUS_KEY = 'eol_status' as const
const EOL_DATE_KEY = 'eol_date' as const
const vadaOptions = [
  { label: 'O', value: 'O' },
  { label: 'X', value: 'X' },
]
const antivirusOptions = [
  { label: 'O', value: 'O' },
  { label: 'X', value: 'X' },
]
const ismsPOptions = [
  { label: 'O', value: 'O' },
  { label: 'X', value: 'X' },
]

import { getErrorMessage } from 'src/utils/http/error'
import { displayValue } from 'src/utils/format/value'

function displayPrice(v: unknown): string {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (!isNaN(n)) return n.toLocaleString()
  return String(v as string | number | boolean)
}

function formatCell(col: unknown, value: unknown): string {
  const c = col as { format?: (v: unknown) => string }
  return c.format ? c.format(value) : displayValue(value)
}
import { parseSmartValue } from 'src/utils/parse/smartValue'
import { formatKst, isDateSoon } from 'src/utils/time/kst'
import { eosStatusColor, eosStatusLabel, normalizeEosStatus } from 'src/utils/rules/eos'
import { historyBadgeColor } from 'src/utils/ui/badges'

const $q = useQuasar()
const route = useRoute()

const category = computed(() => (route.query.category as string) || '')
const pageTitle = computed(() => category.value ? `${category.value} 자산 관리` : '전체 자산 관리')

watch(category, () => { void load() })

const eosSoonDays = 90

// 표준 필드 키 순서 정의 (데이터에 없어도 표시 순서 보장)
const PREFERRED_FIELD_KEYS = [
  'rack_no',
  'rack_unit_no',
  '구분',
  '자산번호',
  '자산관리번호',
  'SN',
  '서버명',
  '설명',
  '운영체제',
  'version',
  '제조사',
  '수량',
  '용도',
  '소속부서',
  '위치',
  EOS_STATUS_KEY,
  EOS_DATE_KEY,
  EOL_STATUS_KEY,
  EOL_DATE_KEY,
  ISMS_P_KEY,
  'ISMS-P비고',
  VADA_KEY,
  'VADA비고',
  ANTIVIRUS_KEY,
  '백신비고',
  '제품명',
  '사양',
  '도입사업',
  '납품회사',
  '담당자',
  '도입가격',
  '도입일자',
  '수령일',
  '변경일',
  '변경사항',
  '비고',
]

// 필드 키 → 표시 레이블 매핑
function fieldLabel(key: string): string {
  if (key === '운영체제' && ['네트워크', '정보보호시스템'].includes(category.value)) return '기종'
  return FIELD_LABEL_MAP[key] ?? key
}

const FIELD_LABEL_MAP: Record<string, string> = {
  rack_no: 'RackNo.',
  rack_unit_no: 'Rack Unit No.',
  '구분': '중분류(구분)',
  '자산번호': '자산번호',
  '자산관리번호': '자산관리번호',
  'SN': 'SN',
  '서버명': '자산명',
  '설명': '설명',
  '운영체제': '운영체제',
  version: 'Version',
  '제조사': '제조사',
  '수량': '수량',
  '용도': '용도(상세)',
  '소속부서': '소속부서/사업',
  '위치': '위치',
  [EOS_STATUS_KEY]: 'EoS 여부',
  [EOS_DATE_KEY]: 'EoS 기간',
  [EOL_STATUS_KEY]: 'EoL 여부',
  [EOL_DATE_KEY]: 'EoL 종료 일자',
  [ISMS_P_KEY]: 'ISMS-P 대상 여부',
  'ISMS-P비고': 'ISMS-P 비고',
  [VADA_KEY]: 'VADA 설치여부',
  'VADA비고': 'VADA 비고',
  [ANTIVIRUS_KEY]: '백신 여부',
  '백신비고': '백신 비고',
  '제품명': '제품명(모델명)',
  '사양': '사양',
  '도입사업': '도입사업',
  '납품회사': '납품회사',
  '담당자': '담당자',
  '도입가격': '도입가격',
  '도입일자': '도입일자(취득일자)',
  '수령일': '수령일',
  '변경일': '변경일',
  '변경사항': '변경사항(신규/변경/폐기)',
  [TAGS_KEY]: '태그',
  '비고': '비고',
}

const CHANGE_TYPE_OPTIONS = [
  { label: '신규', value: '신규' },
  { label: '변경', value: '변경' },
  { label: '폐기', value: '폐기' },
]

const loading = ref(false)
const rows = ref<ServerAsset[]>([])
const includeDeleted = ref(false)

watch(includeDeleted, () => { void load() })

const filter = ref('')
const filterCol = ref<string | null>(null)
const tableSortKey = ref('ip')
const tableSortDesc = ref(false)

function getSortKey(col: { name: string; [k: string]: unknown }): string {
  if (col.name === 'ip') return 'ip'
  if (col.name === 'name') return 'name'
  if (col.name === 'assetType') return '__assetType__'
  return (col.fieldKey as string | undefined) ?? col.name
}

function toggleSort(col: { name: string; [k: string]: unknown }) {
  const key = getSortKey(col)
  if (tableSortKey.value === key) {
    tableSortDesc.value = !tableSortDesc.value
  } else {
    tableSortKey.value = key
    tableSortDesc.value = false
  }
}

function getSortVal(row: ServerAsset, key: string): string {
  if (key === 'ip') return row.ip
  if (key === 'name') return row.name
  if (key === 'assetId') return row.assetId ?? ''
  if (key === '__assetType__') return (row.fields?.['자산유형'] as string) || '서버'
  if (key === 'createdAt') return row.createdAt ?? ''
  const v = row.fields?.[key]
  if (Array.isArray(v)) return (v as string[]).join(',')
  return displayValue(v)
}

// 검색 대상 컬럼 옵션 — IP, HostName + 현재 보이는 동적 필드
const filterColOptions = computed(() => [
  { key: '__ip__',   label: 'IP' },
  { key: '__name__', label: 'HostName' },
  ...COLUMN_DISPLAY_ORDER
    .filter((k) => k !== '__ip__' && k !== '__name__')
    .map((k) => ({ key: k as string, label: fieldLabel(k as string) })),
])

// 선택된 컬럼의 고유값 목록 (50개 이하일 때만 드롭다운 표시)
const _filterColAllValues = computed<string[]>(() => {
  const col = filterCol.value
  if (!col) return []
  const set = new Set<string>()
  for (const r of rows.value) {
    if (col === '__ip__') {
      if (r.ip) set.add(r.ip)
    } else if (col === '__name__') {
      if (r.name) set.add(r.name)
    } else if (col === TAGS_KEY) {
      // 태그는 배열 — 개별 태그를 각각 옵션으로
      const tags = r.fields?.[TAGS_KEY]
      if (Array.isArray(tags)) (tags as string[]).forEach(t => t && set.add(t))
    } else {
      const raw = displayValue(r.fields?.[col])
      if (raw && raw !== '-') set.add(raw)
    }
  }
  return Array.from(set).sort()
})

const filterColUniqueValues = computed<string[]>(() =>
  _filterColAllValues.value.length > 0 && _filterColAllValues.value.length <= 50
    ? _filterColAllValues.value
    : []
)

const _filterColFiltered = ref<string[]>([])

function filterColSearch(val: string, update: (fn: () => void) => void) {
  update(() => {
    const q = val.toLowerCase()
    _filterColFiltered.value = q
      ? _filterColAllValues.value.filter((v) => v.toLowerCase().includes(q))
      : _filterColAllValues.value
  })
}

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  page: 1,
  rowsPerPage: 10,
  sortBy: null,
  descending: false,
})

function onPagination(p: NonNullable<QTableProps['pagination']>) {
  pagination.value = { ...p, sortBy: null, descending: false }
}

function getField(row: ServerAsset, key: string): FieldValue | undefined {
  return row.fields?.[key]
}


type ColumnWithFieldKey = {
  name: string
  label: string
  fieldKey?: string
}

function colKey(col: unknown): string {
  if (typeof col === 'object' && col !== null) {
    const c = col as ColumnWithFieldKey
    return c.fieldKey ?? c.label
  }
  return ''
}

// 컬럼 표시 순서 — '__ip__'/'__name__'은 IP/HostName 고정 컬럼 위치 마커
const COLUMN_DISPLAY_ORDER = [
  'rack_no', 'rack_unit_no', '구분', '자산번호', '자산관리번호', 'SN', '__ip__', '__name__', '서버명', '설명', '운영체제', 'version', '제조사', '수량', '용도', '소속부서', '위치',
  EOS_STATUS_KEY, EOS_DATE_KEY, EOL_STATUS_KEY, EOL_DATE_KEY, ISMS_P_KEY, 'ISMS-P비고', VADA_KEY, 'VADA비고', ANTIVIRUS_KEY, '백신비고', '제품명', '사양', '도입사업', '납품회사', '담당자', '도입가격', '도입일자', '수령일', '변경일', '변경사항', TAGS_KEY, '비고',
] as const

// 컬럼 선택 다이얼로그
const COL_OPTIONS = [
  ...COLUMN_DISPLAY_ORDER.map((k) => {
    if (k === '__ip__') return { key: '__ip__', label: 'IP' }
    if (k === '__name__') return { key: '__name__', label: 'HostName' }
    return { key: k as string, label: fieldLabel(k) }
  }),
  { key: 'createdAt', label: '작성일' },
]

const CATEGORY_DEFAULT_COLS: Record<string, string[]> = {}
const DEFAULT_COL_KEYS = ['__ip__', '__name__', '자산번호', EOS_STATUS_KEY]

function loadColKeys(cat: string): string[] {
  try {
    const saved = localStorage.getItem(`asset-col-vis:${cat}`)
    if (saved) return JSON.parse(saved) as string[]
  } catch { /* ignore */ }
  return [...(CATEGORY_DEFAULT_COLS[cat] ?? DEFAULT_COL_KEYS)]
}

function saveColKeys(cat: string, keys: string[]) {
  try { localStorage.setItem(`asset-col-vis:${cat}`, JSON.stringify(keys)) } catch { /* ignore */ }
}

interface ColItem { key: string; label: string; visible: boolean }

function buildColItems(visibleKeys: string[]): ColItem[] {
  const visSet = new Set(visibleKeys)
  // 선택된 컬럼을 지정된 순서대로, 나머지는 뒤에
  const ordered = visibleKeys
    .filter((k) => COL_OPTIONS.find((c) => c.key === k))
    .map((k) => {
      const opt = COL_OPTIONS.find((c) => c.key === k)!
      return { key: k, label: opt.label, visible: true }
    })
  const rest = COL_OPTIONS
    .filter((c) => !visSet.has(c.key))
    .map((c) => ({ key: c.key, label: c.label, visible: false }))
  return [...ordered, ...rest]
}

const visibleColKeys = ref<string[]>(loadColKeys(category.value))
const colVisDialog = ref(false)
const tempColKeys = ref<string[]>([...visibleColKeys.value])
const tempColItems = ref<ColItem[]>(buildColItems(visibleColKeys.value))

function assetTypeColor(row: ServerAsset): string {
  const t = (row.fields?.['자산유형'] as string) || '서버'
  if (t === '서버') return 'blue'
  if (t === '네트워크') return 'teal'
  if (t === 'DBMS') return 'deep-purple'
  if (t === '정보보호시스템') return 'orange'
  if (t === 'VMware') return 'green'
  return 'grey'
}

function removeCol(col: { name: string; fieldKey?: string }) {
  const key = col.name === 'ip' ? '__ip__' : col.name === 'name' ? '__name__' : (col as { fieldKey?: string }).fieldKey ?? col.name
  visibleColKeys.value = visibleColKeys.value.filter((k) => k !== key)
}

function openColVisDialog() {
  tempColItems.value = buildColItems(visibleColKeys.value)
  tempColKeys.value = [...visibleColKeys.value]
  loadPresets()
  newPresetName.value = ''
  colVisDialog.value = true
}

function applyColVis() {
  const keys = tempColItems.value.filter((c) => c.visible).map((c) => c.key)
  visibleColKeys.value = keys
  tempColKeys.value = keys
  saveColKeys(category.value, keys)
  colVisDialog.value = false
}

// ── 컬럼 프리셋 ──────────────────────────────────────────────────────────────
interface ColPreset { name: string; keys: string[] }
const newPresetName = ref('')
const colPresets = ref<ColPreset[]>([])

function presetsStorageKey() {
  return `asset-col-presets:${category.value}`
}

function loadPresets() {
  try {
    const saved = localStorage.getItem(presetsStorageKey())
    colPresets.value = saved ? (JSON.parse(saved) as ColPreset[]) : []
  } catch { colPresets.value = [] }
}

function savePreset() {
  const name = newPresetName.value.trim()
  if (!name) return
  const keys = tempColItems.value.filter((c) => c.visible).map((c) => c.key)
  const existing = colPresets.value.findIndex((p) => p.name === name)
  const preset: ColPreset = { name, keys }
  if (existing >= 0) colPresets.value[existing] = preset
  else colPresets.value.push(preset)
  try { localStorage.setItem(presetsStorageKey(), JSON.stringify(colPresets.value)) } catch { /* ignore */ }
  newPresetName.value = ''
}

function applyPreset(p: ColPreset) {
  tempColItems.value = buildColItems(p.keys)
  tempColKeys.value = [...p.keys]
}

function deletePreset(name: string) {
  colPresets.value = colPresets.value.filter((p) => p.name !== name)
  try { localStorage.setItem(presetsStorageKey(), JSON.stringify(colPresets.value)) } catch { /* ignore */ }
}

watch(category, (cat) => {
  visibleColKeys.value = loadColKeys(cat)
  tempColItems.value = buildColItems(visibleColKeys.value)
}, { immediate: true })

const columns = computed<NonNullable<QTableProps['columns']>>(() => {
  const visSet = new Set(visibleColKeys.value)

  function makeFieldCol(k: string) {
    const base = {
      name: 'field',
      label: fieldLabel(k),
      field: (row: unknown) => {
        if (typeof row === 'object' && row !== null) {
          const r = row as ServerAsset
          if (k === '자산번호') return r.assetNo ?? r.fields?.[k]
          return r.fields?.[k]
        }
        return undefined
      },
      align: 'left' as const,
      sortable: true,
      fieldKey: k,
    }
    if (k === '도입가격') {
      return {
        ...base,
        format: (val: unknown): string => {
          if (val === null || val === undefined || val === '') return '-'
          const n = Number(val)
          if (!isNaN(n)) return n.toLocaleString()
          return String(val as string | number | boolean)
        },
      }
    }
    return base
  }

  const result: NonNullable<QTableProps['columns']> = []

  // 전체 탭에서만 자산 종류 컬럼을 맨 앞에 추가
  if (!category.value) {
    result.push({
      name: 'assetType',
      label: '자산 종류',
      field: (row: unknown) => {
        const r = row as ServerAsset
        return (r.fields?.['자산유형'] as string) || '서버'
      },
      align: 'left',
      sortable: true,
    })
  }

  for (const key of visibleColKeys.value) {
    if (key === '__ip__') {
      result.push({ name: 'ip', label: 'IP', field: 'ip', align: 'left', sortable: true })
    } else if (key === '__name__') {
      result.push({ name: 'name', label: 'HostName', field: 'name', align: 'left', sortable: true })
    } else if (key !== 'createdAt') {
      result.push(makeFieldCol(key))
    }
  }

  if (visSet.has('createdAt')) {
    result.push({
      name: 'createdAt',
      label: '작성일',
      field: (row: unknown) => (row as ServerAsset).createdAt ?? '',
      align: 'left',
      sortable: true,
      format: (val: unknown) => (val ? formatKst(val as string) : '-'),
    })
  }

  result.push({ name: 'actions', label: '', field: 'actions', align: 'right', style: 'width: 1px; white-space: nowrap', headerStyle: 'width: 1px; white-space: nowrap' })
  return result
})

const filteredRows = computed(() => {
  const q = (filter.value ?? '').trim().toLowerCase()

  return rows.value.filter((r) => {
    // 삭제된 항목 필터
    if (!includeDeleted.value && r.isDeleted) return false

    // 카테고리 필터 (서버 사이드에서 이미 필터링됨 — 클라이언트 측은 생략)

    // 텍스트 검색
    if (q) {
      let matchText = false
      const col = filterCol.value
      if (!col) {
        // 전체 컬럼 검색
        matchText =
          (r.assetId ?? '').toLowerCase().includes(q) ||
          r.ip.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q) ||
          Object.values(r.fields ?? {}).some((v) => displayValue(v).toLowerCase().includes(q))
      } else if (col === '__asset_id__') {
        matchText = (r.assetId ?? '').toLowerCase().includes(q)
      } else if (col === '__ip__') {
        matchText = r.ip.toLowerCase().includes(q)
      } else if (col === '__name__') {
        matchText = r.name.toLowerCase().includes(q)
      } else if (col === TAGS_KEY) {
        const tags = r.fields?.[TAGS_KEY]
        matchText = Array.isArray(tags)
          ? (tags as string[]).some(t => t.toLowerCase().includes(q))
          : false
      } else {
        matchText = displayValue(r.fields?.[col]).toLowerCase().includes(q)
      }
      if (!matchText) return false
    }

    return true
  }).sort((a, b) => {
    const sk = tableSortKey.value
    if (!sk) return 0
    const av = getSortVal(a, sk)
    const bv = getSortVal(b, sk)
    const cmp = av.localeCompare(bv, 'ko', { numeric: true })
    return tableSortDesc.value ? -cmp : cmp
  })
})

async function load() {
  loading.value = true
  try {
    rows.value = await listServers(includeDeleted.value, category.value || undefined)
    // DB에 eos_action_status가 없는 기존 레코드를 on-the-fly로 보완 (표시 전용, DB 미수정)
    await fetchEosMap()
    for (const row of rows.value) {
      const dist = (row.fields?.['운영체제'] as string) ?? ''
      if (!dist) continue
      const version = (row.fields?.['version'] as string) ?? ''
      const assetType = (row.fields?.['자산유형'] as string) || category.value || '서버'
      const series = Object.keys(DBMS_TREE[dist] ?? {}).find(s =>
        (DBMS_TREE[dist]?.[s] ?? []).includes(version)) ?? ''
      if (!row.fields?.[EOS_STATUS_KEY]) {
        const eos = getAutoEos(dist, version)
          ?? (series ? getAutoEos(dist, series) : null)
          ?? (['네트워크', '정보보호시스템'].includes(assetType) ? getNetworkEos(dist) : null)
        if (eos) {
          row.fields[EOS_STATUS_KEY] = eos.status
          row.fields[EOS_DATE_KEY] = eos.date
        }
      }
      if (!row.fields?.[EOL_STATUS_KEY]) {
        const eol = getAutoEol(dist, version) ?? (series ? getAutoEol(dist, series) : null)
        if (eol) {
          row.fields[EOL_STATUS_KEY] = eol.status
          row.fields[EOL_DATE_KEY] = eol.date
        }
      }
    }
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '조회 실패') })
  } finally {
    loading.value = false
  }
}

/** Create */
/** 자산 유형 선택 다이얼로그 (전체 탭) */
const assetTypeDialog = ref(false)
const selectedAssetType = ref('')
const createOverrideCategory = ref('')
const activeCreateCategory = computed(() => createOverrideCategory.value || category.value)
const pendingImport = ref(false)
const importOverrideCategory = ref('')

function onAssetTypeConfirm() {
  assetTypeDialog.value = false
  const target = selectedAssetType.value
  selectedAssetType.value = ''
  if (!target) return
  if (pendingImport.value) {
    pendingImport.value = false
    importOverrideCategory.value = target === '전체 (Excel 기준)' ? '' : target
    importFileInput.value?.click()
    return
  }
  createOverrideCategory.value = target
  openCreate()
}

const CREATE_REQUIRED_KEYS = ['구분', '자산번호', '서버명', 'rack_no', '위치', '설명'] as const
const createOsFamily = ref('')
const createOsMajor = ref('')
const createDbSeries = ref('')
const createManualEosDate = ref('')
const createLocationSelect = ref('')

const createDialog = ref(false)
const createIp = ref('')
const createIpError = ref('')

function checkDuplicateIp() {
  const ip = createIp.value.trim()
  if (!ip) { createIpError.value = ''; return }
  const assetType = createFields.value['자산유형'] || '서버'
  const dup = rows.value.some(r => {
    if (r.isDeleted || r.ip !== ip) return false
    const t = (r.fields?.['자산유형'] as string) || '서버'
    return t === assetType
  })
  createIpError.value = dup ? `이미 사용 중인 IP입니다. (${assetType})` : ''
}
const createName = ref('')
const createFields = ref<Record<string, string>>({})
const createTags = ref<string[]>([])


const LOCATION_OPTIONS = ['암빅데이터센터', '정보화팀', '정보보호팀', '기타']
const LOCATION_PRESETS = ['암빅데이터센터', '정보화팀', '정보보호팀']
const DBMS_LOCATION_OPTIONS = ['암빅데이터센터', 'Closed DMZ', '기타']

const actingId = ref<string | null>(null)
const actingType = ref<'create' | 'editBase' | 'editField' | 'delete' | null>(null)

function openCreate() {
  createIp.value = ''
  createIpError.value = ''
  createName.value = ''
  createFields.value = (activeCreateCategory.value && activeCreateCategory.value !== '서버') ? { '자산유형': activeCreateCategory.value } : {}
  createOsFamily.value = ''
  createDbSeries.value = ''
  createTags.value = []
  createManualEosDate.value = ''
  createLocationSelect.value = ''
  createEosStatusText.value = ''
  createEosDateText.value = ''
  createEosIsEos.value = false
  createDialog.value = true
}

const createEosStatusText = ref('')
const createEosDateText = ref('')
const createEosIsEos = ref(false)

watch(
  () => [createFields.value['운영체제'], createFields.value['version'], createDbSeries.value, createOsMajor.value] as const,
  async ([dist, version, series, major]) => {
    await fetchEosMap()
    createManualEosDate.value = ''
    const eos = getAutoEos(dist ?? '', version ?? '')
      ?? (series ? getAutoEos(dist ?? '', series) : null)
      ?? (['네트워크', '정보보호시스템'].includes(activeCreateCategory.value) ? getNetworkEos(dist ?? '') : null)
    if (eos) {
      createFields.value[EOS_STATUS_KEY] = eos.status
      createFields.value[EOS_DATE_KEY] = eos.date
      createEosStatusText.value = eosStatusLabel(eos.status)
      createEosDateText.value = eos.date
      createEosIsEos.value = eos.status === 'EOS'
    } else {
      createFields.value[EOS_STATUS_KEY] = ''
      createFields.value[EOS_DATE_KEY] = ''
      createEosStatusText.value = ''
      createEosDateText.value = ''
      createEosIsEos.value = false
    }
    const eol = getAutoEol(dist ?? '', version ?? '')
      ?? (major ? getAutoEol(dist ?? '', major) : null)
      ?? (series ? getAutoEol(dist ?? '', series) : null)
    if (eol) {
      createFields.value[EOL_STATUS_KEY] = eol.status
      createFields.value[EOL_DATE_KEY] = eol.date
    } else {
      createFields.value[EOL_STATUS_KEY] = ''
      createFields.value[EOL_DATE_KEY] = ''
    }
  }
)

watch(createManualEosDate, (date) => {
  if (!date) return
  const today = new Date().toISOString().slice(0, 7)
  const status: EosActionStatus = date <= today ? 'EOS' : 'ACTIVE'
  createFields.value[EOS_STATUS_KEY] = status
  createFields.value[EOS_DATE_KEY] = date
  createEosStatusText.value = eosStatusLabel(status)
  createEosDateText.value = date
  createEosIsEos.value = status === 'EOS'
})

watch(() => createFields.value[EOL_DATE_KEY], (date) => {
  if (!date || typeof date !== 'string' || !/^\d{4}-\d{2}$/.test(date)) return
  const today = new Date().toISOString().slice(0, 7)
  createFields.value[EOL_STATUS_KEY] = date <= today ? 'O' : 'X'
})

async function doCreate() {
  const ip = createIp.value.trim()
  const name = createName.value.trim()
  if (!ip) {
    $q.notify({ type: 'warning', message: 'IP는 필수입니다.' })
    return
  }
  if (!name) {
    $q.notify({ type: 'warning', message: '호스트명은 필수입니다.' })
    return
  }
  for (const k of CREATE_REQUIRED_KEYS) {
    if (!(createFields.value[k] ?? '').toString().trim()) {
      const label = fieldLabel(k)
      if (k === '위치' && createLocationSelect.value === '기타') {
        $q.notify({ type: 'warning', message: '위치(기타)를 직접 입력해주세요.' })
      } else {
        $q.notify({ type: 'warning', message: `${label}은(는) 필수입니다.` })
      }
      return
    }
  }

  // OS / 기종 / DBMS 필수 체크
  if (activeCreateCategory.value === 'DBMS') {
    if (!createFields.value['운영체제']) {
      $q.notify({ type: 'warning', message: 'DB 종류는 필수입니다.' })
      return
    }
    if (!createDbSeries.value) {
      $q.notify({ type: 'warning', message: '시리즈는 필수입니다.' })
      return
    }
  } else if (activeCreateCategory.value === '정보보호시스템') {
    if (!createFields.value['운영체제']) {
      $q.notify({ type: 'warning', message: '기종은 필수입니다.' })
      return
    }
    if (!createFields.value['제조사']) {
      $q.notify({ type: 'warning', message: '제조사는 필수입니다.' })
      return
    }
  } else if (activeCreateCategory.value === '네트워크') {
    if (!createFields.value['운영체제']) {
      $q.notify({ type: 'warning', message: '기종은 필수입니다.' })
      return
    }
  } else {
    if (!createOsFamily.value) {
      $q.notify({ type: 'warning', message: 'OS 계열은 필수입니다.' })
      return
    }
    if (!createFields.value['운영체제']) {
      $q.notify({ type: 'warning', message: '배포판은 필수입니다.' })
      return
    }
  }

  actingType.value = 'create'
  try {
    const fields: FieldsMap = {}
    for (const [k, v] of Object.entries(createFields.value)) {
      if (k === '자산번호') continue  // top-level asset_no field
      if ((v ?? '').toString().trim()) fields[k] = parseSmartValue(v)
    }
    if (createTags.value.length) fields[TAGS_KEY] = createTags.value
    // watch가 아직 실행되지 않았을 경우를 대비해 EoS/EoL 직접 계산
    const eos = getAutoEos(createFields.value['운영체제'] ?? '', createFields.value['version'] ?? '')
    if (eos) {
      fields[EOS_STATUS_KEY] = eos.status
      fields[EOS_DATE_KEY] = eos.date
    }
    const eol = getAutoEol(createFields.value['운영체제'] ?? '', createFields.value['version'] ?? '')
    if (eol) {
      fields[EOL_STATUS_KEY] = eol.status
      fields[EOL_DATE_KEY] = eol.date
    }
    // 자산유형을 초기 생성 시부터 전달 → 같은 IP·다른 자산유형 레코드 허용
    const assetNo = (createFields.value['자산번호'] ?? '').toString().trim() || null
    const patched = await createServer(ip, name, Object.keys(fields).length > 0 ? fields : undefined, assetNo, activeCreateCategory.value || undefined)
    rows.value = [patched, ...rows.value]
    createDialog.value = false
    $q.notify({ type: 'positive', message: '생성 완료' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '생성 실패') })
  } finally {
    actingType.value = null
  }
}

/** Edit base */
const editBaseDialog = ref(false)
const selectedRow = ref<ServerAsset | null>(null)
const editingBaseKey = ref<'ip' | 'name'>('name')
const editBaseValue = ref('')

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function openEditBase(row: ServerAsset, key: 'ip' | 'name') {
  selectedRow.value = row
  editingBaseKey.value = key
  editBaseValue.value = key === 'ip' ? row.ip : row.name
  editBaseDialog.value = true
}

async function doEditBase() {
  if (!selectedRow.value) return
  const key = editingBaseKey.value
  const val = editBaseValue.value.trim()
  if (!val) {
    $q.notify({ type: 'warning', message: '값을 입력하세요.' })
    return
  }

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'editBase'
  try {
    const rowCat = (selectedRow.value.fields?.['자산유형'] as string) || category.value || '서버'
    const updated = await patchServer(String(selectedRow.value.id), { [key]: val }, rowCat)
    rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
    editBaseDialog.value = false
    $q.notify({ type: 'positive', message: '저장됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** Edit field */
const editFieldDialog = ref(false)
const editFieldKey = ref('')
const editFieldValue = ref<EosActionStatus | null>(null)
const editFieldText = ref('')
const editFieldOsFamily = ref('')
const editFieldMajor = ref('')
const editFieldVersionText = ref('')
const editFieldLocationSelect = ref('')

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function openEditField(row: ServerAsset, key: string) {
  selectedRow.value = row
  editFieldKey.value = key

  const current = key === '자산번호' ? (row.assetNo ?? row.fields?.[key]) : row.fields?.[key]
  if (key === EOS_STATUS_KEY) {
    editFieldValue.value = normalizeEosStatus(current)
    editFieldText.value = ''
    editFieldOsFamily.value = ''
    editFieldVersionText.value = ''
  } else {
    editFieldText.value = typeof current === 'string' ? current : displayValue(current)
    editFieldValue.value = null
    if (key === '운영체제') {
      editFieldOsFamily.value = detectOsFamily(editFieldText.value)
      if (editFieldOsFamily.value && !osDistOptions(editFieldOsFamily.value).includes(editFieldText.value)) {
        editFieldOsFamily.value = ''
      }
      const ver = row.fields?.['version']
      editFieldVersionText.value = typeof ver === 'string' ? ver : ''
      editFieldMajor.value = editFieldOsFamily.value ? detectOsMajor(editFieldText.value, editFieldVersionText.value) : ''
      editFieldLocationSelect.value = ''
    } else if (key === '위치') {
      const locVal = editFieldText.value
      editFieldLocationSelect.value = LOCATION_PRESETS.includes(locVal) ? locVal : (locVal ? '기타' : '')
      editFieldOsFamily.value = ''
      editFieldVersionText.value = ''
    } else {
      editFieldOsFamily.value = ''
      editFieldVersionText.value = ''
      editFieldLocationSelect.value = ''
    }
  }

  editFieldDialog.value = true
}

async function doEditField() {
  if (!selectedRow.value) return
  const key = editFieldKey.value.trim()
  if (!key) return

  const value: FieldValue =
    key === EOS_STATUS_KEY ? (editFieldValue.value ?? null) : parseSmartValue(editFieldText.value)

  actingId.value = String(selectedRow.value.id)
  actingType.value = 'editField'
  try {
    const nextFields: FieldsMap = { ...(selectedRow.value.fields || {}) }
    if (key === '자산번호') {
      // 자산번호는 top-level asset_no로 저장
      const rowCat2 = (selectedRow.value.fields?.['자산유형'] as string) || category.value || '서버'
      const updated = await patchServer(String(selectedRow.value.id), { asset_no: (value as string) || null }, rowCat2)
      rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
      editFieldDialog.value = false
      $q.notify({ type: 'positive', message: '저장됨' })
      return
    }
    nextFields[key] = value
    if (key === '운영체제' && editFieldOsFamily.value) {
      nextFields['version'] = editFieldVersionText.value || null
      const eos = getAutoEos(editFieldText.value, editFieldVersionText.value)
      if (eos) {
        nextFields[EOS_STATUS_KEY] = eos.status
        nextFields[EOS_DATE_KEY] = eos.date
      }
    }
    const rowCat3 = (selectedRow.value.fields?.['자산유형'] as string) || category.value || '서버'
    const updated = await patchServer(String(selectedRow.value.id), { fields: nextFields }, rowCat3)
    rows.value = rows.value.map((r) => (r.id === selectedRow.value!.id ? updated : r))
    editFieldDialog.value = false
    $q.notify({ type: 'positive', message: '저장됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}


/** Delete */
const deleteDialog = ref(false)
const deleteTarget = ref<ServerAsset | null>(null)
const deleteReason = ref('')

function confirmDelete(row: ServerAsset) {
  deleteTarget.value = row
  deleteReason.value = ''
  deleteDialog.value = true
}

async function doDelete(row: ServerAsset) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    const deleted = await deleteServer(row.id, deleteReason.value.trim() || undefined, (row.fields?.['자산유형'] as string) || category.value || '서버')
    rows.value = rows.value.map((r) => (r.id === row.id ? deleted : r))
    deleteDialog.value = false
    $q.notify({ type: 'info', message: '삭제됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '삭제 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

async function doRestore(row: ServerAsset) {
  actingId.value = String(row.id)
  actingType.value = 'delete'
  try {
    const restored = await restoreServer(row.id, (row.fields?.['자산유형'] as string) || category.value || '서버')
    rows.value = rows.value.map((r) => (r.id === row.id ? restored : r))
    $q.notify({ type: 'positive', message: '복원됨' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '복원 실패') })
  } finally {
    actingId.value = null
    actingType.value = null
  }
}

/** History */
/** Detail view */
const detailDialog = ref(false)
const detailTarget = ref<ServerAsset | null>(null)

function openDetailView(row: ServerAsset) {
  detailTarget.value = row
  detailDialog.value = true
}

/** Row edit */
const rowEditDialog = ref(false)
const rowEditTarget = ref<ServerAsset | null>(null)
const rowEditValues = ref<Record<string, string>>({})
const rowEditTags = ref<string[]>([])
const rowEditSaving = ref(false)
const rowEditOsFamily = ref('')
const rowEditMajor = ref('')
const rowEditManualEosDate = ref('')
const rowEditDbSeries = ref('')
const rowEditLocationSelect = ref('')

// 편집 다이얼로그에 표시할 필드 목록 (label + key)
// 자산 유형별로 편집 폼에서 제외할 필드
const CATEGORY_EXCLUDED_FIELDS: Record<string, string[]> = {
  '서버': ['수량'],
  '네트워크': ['수량'],
  'DBMS': ['수량'],
}

const rowEditFields = computed(() => {
  if (!rowEditTarget.value) return []
  const assetType = (rowEditTarget.value.fields?.['자산유형'] as string) || '서버'
  const excluded = new Set(CATEGORY_EXCLUDED_FIELDS[assetType] ?? [])
  const result: { key: string; label: string }[] = []
  for (const key of COLUMN_DISPLAY_ORDER) {
    if (excluded.has(key as string)) continue
    if (key === '__ip__') result.push({ key: '__ip__', label: 'IP' })
    else if (key === '__name__') result.push({ key: '__name__', label: 'HostName' })
    else result.push({ key, label: fieldLabel(key) })
  }
  // 추가 필드
  const ordered = new Set(COLUMN_DISPLAY_ORDER as readonly string[])
  for (const k of Object.keys(rowEditTarget.value.fields ?? {})) {
    if (!ordered.has(k) && !excluded.has(k)) result.push({ key: k, label: fieldLabel(k) })
  }
  return result
})

// 편집 다이얼로그 템플릿에서 이미 하드코딩된 필드 키 목록
const EDIT_DIALOG_COVERED_KEYS = new Set([
  '자산유형', '서버명', '구분', '자산번호', 'rack_no', 'rack_unit_no', '자산관리번호', 'SN', '위치', '설명',
  '운영체제', 'version', EOS_STATUS_KEY, EOS_DATE_KEY, EOL_STATUS_KEY, EOL_DATE_KEY, ISMS_P_KEY, 'ISMS-P비고', VADA_KEY, 'VADA비고', ANTIVIRUS_KEY, '백신비고',
  '용도', '소속부서', '제품명', '사양', '도입사업', '납품회사', '담당자', '도입가격', '도입일자',
  '비고', TAGS_KEY,
])

// 편집 다이얼로그에 하드코딩 섹션이 없어서 별도로 렌더링해야 할 추가 필드
const rowEditExtraFields = computed(() => {
  if (!rowEditTarget.value) return []
  return Object.keys(rowEditTarget.value.fields ?? {}).filter(
    k => !EDIT_DIALOG_COVERED_KEYS.has(k)
  )
})

function openRowEdit(row: ServerAsset) {
  rowEditTarget.value = row
  const vals: Record<string, string> = {
    __ip__: row.ip,
    __name__: row.name,
  }
  for (const [k, v] of Object.entries(row.fields ?? {})) {
    if (k === TAGS_KEY) continue
    vals[k] = typeof v === 'string' ? v : displayValue(v)
  }
  // assetNo는 top-level 필드; fields에 없는 경우 대비
  if (row.assetNo != null) vals['자산번호'] = row.assetNo
  rowEditValues.value = vals
  rowEditTags.value = Array.isArray(row.fields?.[TAGS_KEY]) ? [...(row.fields?.[TAGS_KEY] as string[])] : []
  const osDist = resolveDistName((vals['운영체제'] ?? '').trim())
  if (osDist !== vals['운영체제']) vals['운영체제'] = osDist
  const detectedFamily = detectOsFamily(osDist)
  rowEditOsFamily.value = detectedFamily || (osDist === '기타' ? '기타' : '')
  if (rowEditOsFamily.value && rowEditOsFamily.value !== '기타' && !osDistOptions(rowEditOsFamily.value).includes(osDist)) {
    rowEditOsFamily.value = ''
  }
  rowEditMajor.value = rowEditOsFamily.value ? detectOsMajor(osDist, (vals['version'] ?? '').trim()) : ''
  const assetTypeVal = (row.fields?.['자산유형'] as string) || ''
  if (assetTypeVal === 'DBMS' && vals['운영체제']) {
    const dbKind = vals['운영체제'] ?? ''
    rowEditDbSeries.value = Object.keys(DBMS_TREE[dbKind] ?? {}).find(s =>
      (DBMS_TREE[dbKind]?.[s] ?? []).includes(vals['version'] ?? '')) ?? ''
  } else {
    rowEditDbSeries.value = ''
  }
  const autoEos = ['네트워크', '정보보호시스템'].includes(category.value) ? getNetworkEos(vals['운영체제'] ?? '') : null
  rowEditManualEosDate.value = (!autoEos && ['네트워크', '정보보호시스템'].includes(category.value)) ? (vals[EOS_DATE_KEY] ?? '') : ''
  const locVal = vals['위치'] ?? ''
  rowEditLocationSelect.value = LOCATION_PRESETS.includes(locVal) ? locVal : (locVal ? '기타' : '')
  rowEditDialog.value = true
}

watch(
  () => [rowEditValues.value['운영체제'], rowEditValues.value['version'], rowEditMajor.value] as const,
  async ([dist, version, major]) => {
    await fetchEosMap()
    rowEditManualEosDate.value = ''
    const eos = getAutoEos(dist ?? '', version ?? '')
      ?? (['네트워크', '정보보호시스템'].includes(category.value) ? getNetworkEos(dist ?? '') : null)
    if (eos) {
      rowEditValues.value[EOS_STATUS_KEY] = eos.status
      rowEditValues.value[EOS_DATE_KEY] = eos.date
    } else {
      rowEditValues.value[EOS_STATUS_KEY] = ''
      rowEditValues.value[EOS_DATE_KEY] = ''
    }
    const eol = getAutoEol(dist ?? '', version ?? '')
      ?? (major ? getAutoEol(dist ?? '', major) : null)
    if (eol) {
      rowEditValues.value[EOL_STATUS_KEY] = eol.status
      rowEditValues.value[EOL_DATE_KEY] = eol.date
    } else {
      rowEditValues.value[EOL_STATUS_KEY] = ''
      rowEditValues.value[EOL_DATE_KEY] = ''
    }
  }
)

watch(rowEditManualEosDate, (date) => {
  if (!date) return
  const today = new Date().toISOString().slice(0, 7)
  const status: EosActionStatus = date <= today ? 'EOS' : 'ACTIVE'
  rowEditValues.value[EOS_STATUS_KEY] = status
  rowEditValues.value[EOS_DATE_KEY] = date
})

watch(() => rowEditValues.value[EOL_DATE_KEY], (date) => {
  if (!date || typeof date !== 'string' || !/^\d{4}-\d{2}$/.test(date)) return
  const today = new Date().toISOString().slice(0, 7)
  rowEditValues.value[EOL_STATUS_KEY] = date <= today ? 'O' : 'X'
})

async function doRowEdit() {
  if (!rowEditTarget.value) return
  rowEditSaving.value = true
  try {
    const row = rowEditTarget.value
    const newIp = (rowEditValues.value['__ip__'] ?? '').trim()
    const newName = (rowEditValues.value['__name__'] ?? '').trim()

    const rowCat = ((row.fields?.['자산유형'] as string) || category.value || '서버')
    // IP/HostName 변경
    if (newIp && newIp !== row.ip) {
      await patchServer(String(row.id), { ip: newIp }, rowCat)
    }
    if (newName && newName !== row.name) {
      await patchServer(String(row.id), { name: newName }, rowCat)
    }

    // 필드 변경
    const newFields: FieldsMap = { ...(row.fields ?? {}) }
    delete newFields['자산번호']  // top-level asset_no 필드로 분리
    for (const { key } of rowEditFields.value) {
      if (key === '__ip__' || key === '__name__' || key === '자산번호') continue
      const val = (rowEditValues.value[key] ?? '').toString().trim()
      newFields[key] = val ? parseSmartValue(val) : null
    }
    newFields[TAGS_KEY] = rowEditTags.value.length ? rowEditTags.value : null
    const rowEditAssetNo = (rowEditValues.value['자산번호'] ?? '').trim() || null
    const updated = await patchServer(String(row.id), { fields: newFields, asset_no: rowEditAssetNo }, rowCat)
    // ip/name 반영
    if (newIp) updated.ip = newIp
    if (newName) updated.name = newName

    rows.value = rows.value.map((r) => (r.id === row.id ? updated : r))
    rowEditDialog.value = false
    $q.notify({ type: 'positive', message: '저장 완료' })
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '저장 실패') })
  } finally {
    rowEditSaving.value = false
  }
}

/** History */
const historyOpen = ref(false)
const historyTarget = ref<ServerAsset | null>(null)
const historyLoading = ref(false)
const historyItems = ref<AssetHistory[]>([])

async function loadHistory(assetId: string) {
  historyLoading.value = true
  try {
    const rowCat = historyTarget.value ? ((historyTarget.value.fields?.['자산유형'] as string) || category.value || '서버') : undefined
    historyItems.value = await getServerHistory(assetId, rowCat)
  } catch (err: unknown) {
    historyItems.value = []
    $q.notify({ type: 'negative', message: getErrorMessage(err, '이력 조회 실패') })
  } finally {
    historyLoading.value = false
  }
}

function openHistory(row: ServerAsset) {
  historyTarget.value = row
  historyItems.value = []
  historyOpen.value = true
  void loadHistory(row.id)
}

/** Export */
const exportLoading = ref(false)

async function doExport() {
  exportLoading.value = true
  try {
    const sourceRows = filteredRows.value
    const colOrder = COL_OPTIONS.map(o => o.key)

    // 전체 탭일 때 맨 앞에 자산 종류 추가
    const finalCols = !category.value ? ['__assetType__', ...colOrder] : colOrder

    const header = finalCols.map(k => {
      if (k === '__asset_id__') return 'Asset ID'
      if (k === '__ip__') return 'IP'
      if (k === '__name__') return 'HostName'
      if (k === '__assetType__') return '자산 종류'
      if (k === 'createdAt') return '작성일'
      return fieldLabel(k)
    })

    const dataRows = sourceRows.map(row =>
      finalCols.map(k => {
        if (k === '__asset_id__') return row.assetId ?? ''
        if (k === '__ip__') return row.ip
        if (k === '__name__') return row.name
        if (k === '__assetType__') return (row.fields?.['자산유형'] as string) || '서버'
        if (k === 'createdAt') return row.createdAt ? formatKst(row.createdAt) : ''
        const v = row.fields?.[k]
        if (v === null || v === undefined) return ''
        if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return String(v)
        return JSON.stringify(v)
      })
    )

    const ws = XLSX.utils.aoa_to_sheet([header, ...dataRows])
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '서버자산')

    const filename = `서버자산_${new Date().toISOString().slice(0, 10)}.xlsx`
    const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' }) as ArrayBuffer
    const form = new FormData()
    form.append('file', new Blob([buf]), filename)

    const res = await api.post<Blob>('/assets/encrypt-xlsx', form, {
      params: { filename },
      responseType: 'blob',
    })

    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, 'Export 실패') })
  } finally {
    exportLoading.value = false
  }
}

/** Template Download */
type TemplateCol = { key: string; label: string; sample?: string }

const CATEGORY_TEMPLATE_COLS: Record<string, TemplateCol[]> = {
  '서버': [
    { key: 'ip',            label: 'IP',                                                              sample: '192.168.1.1' },
    { key: 'name',          label: 'HostName',                                                        sample: 'web-server-01' },
    { key: '자산유형',      label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)',     sample: '' },
    { key: 'rack_no',       label: 'RackNo.',                                                         sample: 'R01' },
    { key: 'rack_unit_no',  label: 'Rack Unit No.',                                                   sample: '' },
    { key: '구분',          label: '중분류(구분)',                                                    sample: '물리' },
    { key: '자산번호',      label: '자산번호',                                                        sample: 'SV-001' },
    { key: '자산관리번호',  label: '자산관리번호',                                                    sample: '' },
    { key: 'SN',            label: 'SN',                                                              sample: '' },
    { key: '서버명',        label: '서버명 / 자산명',                                                 sample: '웹서버' },
    { key: '설명',          label: '설명',                                                            sample: '메인 웹서버' },
    { key: '운영체제',      label: '운영체제 / 배포판',                                               sample: 'Rocky Linux' },
    { key: 'version',       label: '버전',                                                            sample: '8.10' },
    { key: '제조사',        label: '제조사',                                                          sample: '' },
    { key: '용도',          label: '용도(상세)',                                                      sample: '' },
    { key: '소속부서',      label: '소속부서/사업',                                                   sample: '' },
    { key: '위치',          label: '위치',                                                            sample: '암빅데이터센터' },
    { key: EOS_STATUS_KEY,  label: 'EoS여부',                                                         sample: '' },
    { key: EOS_DATE_KEY,    label: 'EoS종료일자',                                                     sample: '' },
    { key: EOL_STATUS_KEY,  label: 'EoL여부',                                                         sample: '' },
    { key: EOL_DATE_KEY,    label: 'EoL종료일자',                                                     sample: '' },
    { key: ISMS_P_KEY,      label: 'ISMS-P대상여부',                                                  sample: 'O' },
    { key: 'ISMS-P비고',   label: 'ISMS-P비고',                                                      sample: '' },
    { key: VADA_KEY,        label: 'VADA설치여부',                                                    sample: 'O' },
    { key: 'VADA비고',      label: 'VADA비고',                                                        sample: '' },
    { key: ANTIVIRUS_KEY,   label: '백신여부',                                                        sample: 'O' },
    { key: '백신비고',       label: '백신비고',                                                        sample: '' },
    { key: '제품명',        label: '제품명(모델명)',                                                  sample: '' },
    { key: '사양',          label: '사양',                                                            sample: '' },
    { key: '도입사업',      label: '도입사업',                                                        sample: '' },
    { key: '납품회사',      label: '납품회사',                                                        sample: '' },
    { key: '담당자',        label: '담당자',                                                          sample: '' },
    { key: '도입가격',      label: '도입가격',                                                        sample: '' },
    { key: '도입일자',      label: '도입일자(취득일자)',                                              sample: '' },
    { key: '수령일',        label: '수령일',                                                          sample: '2024-01-01' },
    { key: '변경일',        label: '변경일',                                                          sample: '' },
    { key: '변경사항',      label: '변경사항',                                                        sample: '' },
    { key: TAGS_KEY,        label: '태그',                                                            sample: '' },
    { key: '비고',          label: '비고',                                                            sample: '' },
  ],
  '네트워크': [
    { key: 'ip',            label: 'IP',                                                              sample: '192.168.1.1' },
    { key: 'name',          label: 'HostName',                                                        sample: 'sw-core-01' },
    { key: '자산유형',      label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)',     sample: '' },
    { key: 'rack_no',       label: 'RackNo.',                                                         sample: 'R01' },
    { key: 'rack_unit_no',  label: 'Rack Unit No.',                                                   sample: '' },
    { key: '구분',          label: '중분류(구분)',                                                    sample: 'Switch' },
    { key: '자산번호',      label: '자산번호',                                                        sample: 'NW-001' },
    { key: '자산관리번호',  label: '자산관리번호',                                                    sample: '' },
    { key: 'SN',            label: 'SN',                                                              sample: '' },
    { key: '서버명',        label: '서버명 / 자산명',                                                 sample: '코어스위치' },
    { key: '설명',          label: '설명',                                                            sample: '' },
    { key: '운영체제',      label: '운영체제 / 기종',                                                 sample: 'Cisco Nexus C93180YC-EX' },
    { key: '제조사',        label: '제조사',                                                          sample: '' },
    { key: '용도',          label: '용도(상세)',                                                      sample: '' },
    { key: '소속부서',      label: '소속부서/사업',                                                   sample: '' },
    { key: '위치',          label: '위치',                                                            sample: '암빅데이터센터' },
    { key: EOS_STATUS_KEY,  label: 'EoS여부',                                                         sample: '' },
    { key: EOS_DATE_KEY,    label: 'EoS종료일자',                                                     sample: '' },
    { key: EOL_STATUS_KEY,  label: 'EoL여부',                                                         sample: '' },
    { key: EOL_DATE_KEY,    label: 'EoL종료일자',                                                     sample: '' },
    { key: ISMS_P_KEY,      label: 'ISMS-P대상여부',                                                  sample: 'O' },
    { key: 'ISMS-P비고',   label: 'ISMS-P비고',                                                      sample: '' },
    { key: '제품명',        label: '제품명(모델명)',                                                  sample: '' },
    { key: '사양',          label: '사양',                                                            sample: '' },
    { key: '도입사업',      label: '도입사업',                                                        sample: '' },
    { key: '납품회사',      label: '납품회사',                                                        sample: '' },
    { key: '담당자',        label: '담당자',                                                          sample: '' },
    { key: '도입가격',      label: '도입가격',                                                        sample: '' },
    { key: '도입일자',      label: '도입일자(취득일자)',                                              sample: '' },
    { key: '수령일',        label: '수령일',                                                          sample: '2024-01-01' },
    { key: '변경일',        label: '변경일',                                                          sample: '' },
    { key: '변경사항',      label: '변경사항',                                                        sample: '' },
    { key: TAGS_KEY,        label: '태그',                                                            sample: '' },
    { key: '비고',          label: '비고',                                                            sample: '' },
  ],
  'DBMS': [
    { key: 'ip',            label: 'IP',                                                              sample: '192.168.1.1' },
    { key: 'name',          label: 'HostName',                                                        sample: 'db-server-01' },
    { key: '자산유형',      label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)',     sample: '' },
    { key: 'rack_no',       label: 'RackNo.',                                                         sample: 'R01' },
    { key: 'rack_unit_no',  label: 'Rack Unit No.',                                                   sample: '' },
    { key: '구분',          label: '중분류(구분)',                                                    sample: 'DB' },
    { key: '자산번호',      label: '자산번호',                                                        sample: 'DB-001' },
    { key: '자산관리번호',  label: '자산관리번호',                                                    sample: '' },
    { key: 'SN',            label: 'SN',                                                              sample: '' },
    { key: '서버명',        label: '서버명 / 자산명',                                                 sample: 'DB서버' },
    { key: '설명',          label: '설명',                                                            sample: '' },
    { key: '운영체제',      label: '운영체제 / DB종류',                                               sample: 'MariaDB' },
    { key: 'version',       label: '버전',                                                            sample: '10.6.18' },
    { key: '제조사',        label: '제조사',                                                          sample: '' },
    { key: '용도',          label: '용도(상세)',                                                      sample: '' },
    { key: '소속부서',      label: '소속부서/사업',                                                   sample: '' },
    { key: '위치',          label: '위치',                                                            sample: '암빅데이터센터' },
    { key: EOS_STATUS_KEY,  label: 'EoS여부',                                                         sample: '' },
    { key: EOS_DATE_KEY,    label: 'EoS종료일자',                                                     sample: '' },
    { key: EOL_STATUS_KEY,  label: 'EoL여부',                                                         sample: '' },
    { key: EOL_DATE_KEY,    label: 'EoL종료일자',                                                     sample: '' },
    { key: ISMS_P_KEY,      label: 'ISMS-P대상여부',                                                  sample: 'O' },
    { key: 'ISMS-P비고',   label: 'ISMS-P비고',                                                      sample: '' },
    { key: '제품명',        label: '제품명(모델명)',                                                  sample: '' },
    { key: '사양',          label: '사양',                                                            sample: '' },
    { key: '도입사업',      label: '도입사업',                                                        sample: '' },
    { key: '납품회사',      label: '납품회사',                                                        sample: '' },
    { key: '담당자',        label: '담당자',                                                          sample: '' },
    { key: '도입가격',      label: '도입가격',                                                        sample: '' },
    { key: '도입일자',      label: '도입일자(취득일자)',                                              sample: '' },
    { key: '수령일',        label: '수령일',                                                          sample: '2024-01-01' },
    { key: '변경일',        label: '변경일',                                                          sample: '' },
    { key: '변경사항',      label: '변경사항',                                                        sample: '' },
    { key: TAGS_KEY,        label: '태그',                                                            sample: '' },
    { key: '비고',          label: '비고',                                                            sample: '' },
  ],
  '정보보호시스템': [
    { key: 'ip',            label: 'IP',                                                              sample: '192.168.1.1' },
    { key: 'name',          label: 'HostName',                                                        sample: 'sec-device-01' },
    { key: '자산유형',      label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)',     sample: '' },
    { key: 'rack_no',       label: 'RackNo.',                                                         sample: 'R01' },
    { key: 'rack_unit_no',  label: 'Rack Unit No.',                                                   sample: '' },
    { key: '구분',          label: '중분류(구분)',                                                    sample: 'F/W' },
    { key: '자산번호',      label: '자산번호',                                                        sample: 'SEC-001' },
    { key: '자산관리번호',  label: '자산관리번호',                                                    sample: '' },
    { key: 'SN',            label: 'SN',                                                              sample: '' },
    { key: '서버명',        label: '서버명 / 자산명',                                                 sample: '방화벽' },
    { key: '설명',          label: '설명',                                                            sample: '' },
    { key: '운영체제',      label: '운영체제 / 기종',                                                 sample: 'Secure Gate' },
    { key: '수량',          label: '수량',                                                            sample: '1' },
    { key: '제조사',        label: '제조사',                                                          sample: '한싹' },
    { key: '용도',          label: '용도(상세)',                                                      sample: '' },
    { key: '소속부서',      label: '소속부서/사업',                                                   sample: '' },
    { key: '위치',          label: '위치',                                                            sample: '암빅데이터센터' },
    { key: EOS_STATUS_KEY,  label: 'EoS여부',                                                         sample: '' },
    { key: EOS_DATE_KEY,    label: 'EoS종료일자',                                                     sample: '' },
    { key: EOL_STATUS_KEY,  label: 'EoL여부',                                                         sample: '' },
    { key: EOL_DATE_KEY,    label: 'EoL종료일자',                                                     sample: '' },
    { key: ISMS_P_KEY,      label: 'ISMS-P대상여부',                                                  sample: 'O' },
    { key: 'ISMS-P비고',   label: 'ISMS-P비고',                                                      sample: '' },
    { key: '제품명',        label: '제품명(모델명)',                                                  sample: '' },
    { key: '사양',          label: '사양',                                                            sample: '' },
    { key: '도입사업',      label: '도입사업',                                                        sample: '' },
    { key: '납품회사',      label: '납품회사',                                                        sample: '' },
    { key: '담당자',        label: '담당자',                                                          sample: '' },
    { key: '도입가격',      label: '도입가격',                                                        sample: '' },
    { key: '도입일자',      label: '도입일자(취득일자)',                                              sample: '' },
    { key: '수령일',        label: '수령일',                                                          sample: '2024-01-01' },
    { key: '변경일',        label: '변경일',                                                          sample: '' },
    { key: '변경사항',      label: '변경사항',                                                        sample: '' },
    { key: TAGS_KEY,        label: '태그',                                                            sample: '' },
    { key: '비고',          label: '비고',                                                            sample: '' },
  ],
  'VMware': [
    { key: 'ip',            label: 'IP',                                                              sample: '192.168.1.1' },
    { key: 'name',          label: 'HostName',                                                        sample: 'vm-host-01' },
    { key: '자산유형',      label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)',     sample: '' },
    { key: 'rack_no',       label: 'RackNo.',                                                         sample: 'R01' },
    { key: 'rack_unit_no',  label: 'Rack Unit No.',                                                   sample: '' },
    { key: '구분',          label: '중분류(구분)',                                                    sample: 'ESXi' },
    { key: '자산번호',      label: '자산번호',                                                        sample: 'VM-001' },
    { key: '자산관리번호',  label: '자산관리번호',                                                    sample: '' },
    { key: 'SN',            label: 'SN',                                                              sample: '' },
    { key: '서버명',        label: '서버명 / 자산명',                                                 sample: 'VM호스트' },
    { key: '설명',          label: '설명',                                                            sample: '' },
    { key: '운영체제',      label: '운영체제 / 버전',                                                 sample: 'ESXi 8.0' },
    { key: 'version',       label: 'Version',                                                         sample: '8.0' },
    { key: '제조사',        label: '제조사',                                                          sample: '' },
    { key: '용도',          label: '용도(상세)',                                                      sample: '' },
    { key: '소속부서',      label: '소속부서/사업',                                                   sample: '' },
    { key: '위치',          label: '위치',                                                            sample: '암빅데이터센터' },
    { key: EOS_STATUS_KEY,  label: 'EoS여부',                                                         sample: '' },
    { key: EOS_DATE_KEY,    label: 'EoS종료일자',                                                     sample: '' },
    { key: EOL_STATUS_KEY,  label: 'EoL여부',                                                         sample: '' },
    { key: EOL_DATE_KEY,    label: 'EoL종료일자',                                                     sample: '' },
    { key: ISMS_P_KEY,      label: 'ISMS-P대상여부',                                                  sample: 'O' },
    { key: 'ISMS-P비고',   label: 'ISMS-P비고',                                                      sample: '' },
    { key: '제품명',        label: '제품명(모델명)',                                                  sample: '' },
    { key: '사양',          label: '사양',                                                            sample: '' },
    { key: '도입사업',      label: '도입사업',                                                        sample: '' },
    { key: '납품회사',      label: '납품회사',                                                        sample: '' },
    { key: '담당자',        label: '담당자',                                                          sample: '' },
    { key: '도입가격',      label: '도입가격',                                                        sample: '' },
    { key: '도입일자',      label: '도입일자(취득일자)',                                              sample: '' },
    { key: '수령일',        label: '수령일',                                                          sample: '2024-01-01' },
    { key: '변경일',        label: '변경일',                                                          sample: '' },
    { key: '변경사항',      label: '변경사항',                                                        sample: '' },
    { key: TAGS_KEY,        label: '태그',                                                            sample: '' },
    { key: '비고',          label: '비고',                                                            sample: '' },
  ],
}

// 전체 탭용 — 모든 컬럼
const DEFAULT_TEMPLATE_COLS: TemplateCol[] = [
  { key: 'ip',          label: 'IP' },
  { key: 'name',        label: 'HostName' },
  { key: '자산유형',    label: '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)', sample: '' },
  ...COLUMN_DISPLAY_ORDER
    .filter(k => k !== '__ip__' && k !== '__name__')
    .map(k => {
      if (k === '운영체제') return { key: k as string, label: '운영체제 / 배포판 / 기종 / DB종류' }
      if (k === '서버명')   return { key: k as string, label: '서버명 / 자산명' }
      return { key: k as string, label: fieldLabel(k as string) }
    }),
]

function downloadTemplate() {
  const cat = category.value
  const baseCols = CATEGORY_TEMPLATE_COLS[cat] ?? DEFAULT_TEMPLATE_COLS

  // 페이지와 동일한 순서로 정렬
  const displayOrder = ['asset_id', 'ip', 'name', '자산유형', ...COLUMN_DISPLAY_ORDER.map((k) =>
    k === '__ip__' ? 'ip' : k === '__name__' ? 'name' : (k as string)
  )]
  const sorted = [...baseCols].sort((a, b) => {
    const ai = displayOrder.indexOf(a.key)
    const bi = displayOrder.indexOf(b.key)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })

  const headers = sorted.map((c) => {
    if (c.key === 'asset_id') return 'Asset ID'
    if (c.key === 'ip') return 'IP'
    if (c.key === 'name') return 'HostName'
    return c.label ?? fieldLabel(c.key)
  })

  const sample = sorted.map((c) => c.sample ?? '')
  const ws = XLSX.utils.aoa_to_sheet([headers, sample])
  const wb = XLSX.utils.book_new()
  const sheetName = cat || '전체자산'
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  XLSX.writeFile(wb, `${sheetName}_템플릿.xlsx`)
}

/** Import */
function normalizeOsName(v: string): string {
  return resolveDistName(v.trim())
}
const importFileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

interface ImportFailedRow {
  rowIndex: number
  ip: string
  name: string
  fields: Record<string, string>
  error: string
  isNew: boolean
  retrying: boolean
  retrySuccess: boolean
  conflictWith?: ServerAsset | null
}

interface ImportSkippedRow {
  rowIndex: number
  ip: string
  name: string
  reason: string
  rawData: Record<string, string>
  retrying: boolean
  retrySuccess: boolean
  conflictWith?: ServerAsset | null
  separateSaving?: boolean
  separateSaved?: boolean
  separateError?: string
}

const importFailDialog = ref(false)
const importFailedRows = ref<ImportFailedRow[]>([])
const importSkippedRows = ref<ImportSkippedRow[]>([])
const importResultTab = ref<'failed' | 'skipped' | 'separate'>('failed')
const pendingImportBuf = ref<ArrayBuffer | null>(null)
const importPasswordDialog = ref(false)
const importPassword = ref('')
const importPasswordVisible = ref(false)
const skipEditIdx = ref(-1)
const skipEditForm = ref<{ ip: string; name: string; fields: Record<string, string> }>({ ip: '', name: '', fields: {} })
const skipEditSaving = ref(false)

// 별도 저장 탭
const duplicateSkippedRows = computed(() =>
  importSkippedRows.value.filter(r => r.reason.startsWith('중복 행'))
)
const separateEditIdx = ref(-1)
const separateEditForm = ref<{ ip: string; name: string; fields: Record<string, string> }>({ ip: '', name: '', fields: {} })

function openSeparateEdit(idx: number) {
  const row = duplicateSkippedRows.value[idx]!
  const fields: Record<string, string> = {}
  for (const [k, v] of Object.entries(row.rawData)) {
    if (k !== 'ip' && k !== 'name') fields[k] = v
  }
  separateEditForm.value = { ip: row.ip, name: row.name, fields }
  separateEditIdx.value = idx
}

async function _doSaveSeparate(row: ImportSkippedRow, ip: string, name: string, fields: Record<string, string>) {
  const importAssetId = fields['asset_id'] || null
  const createFields: FieldsMap = {}
  for (const [k, v] of Object.entries(fields)) {
    if (k !== 'asset_id' && v) createFields[k] = v
  }
  const rowCat = (fields['자산유형'] || importOverrideCategory.value || category.value || '서버')
  const newServer = await createServer(ip, name || ip, Object.keys(createFields).length > 0 ? createFields : undefined, undefined, rowCat, importAssetId)
  rows.value = [newServer, ...rows.value]
  row.separateSaved = true
  row.separateError = ''
}

async function saveDuplicateAsNew(idx: number) {
  const row = duplicateSkippedRows.value[idx]!
  row.separateSaving = true
  row.separateError = ''
  try {
    const fields: Record<string, string> = {}
    for (const [k, v] of Object.entries(row.rawData)) {
      if (k !== 'ip' && k !== 'name') fields[k] = v
    }
    await _doSaveSeparate(row, row.ip, row.name, fields)
  } catch (err: unknown) {
    row.separateError = getErrorMessage(err, '저장 실패')
  } finally {
    row.separateSaving = false
  }
}

async function saveSeparateEdit(idx: number) {
  const row = duplicateSkippedRows.value[idx]!
  row.separateSaving = true
  row.separateError = ''
  try {
    await _doSaveSeparate(row, separateEditForm.value.ip, separateEditForm.value.name, separateEditForm.value.fields)
    separateEditIdx.value = -1
  } catch (err: unknown) {
    row.separateError = getErrorMessage(err, '저장 실패')
  } finally {
    row.separateSaving = false
  }
}
const failEditIdx = ref(-1)
const failEditForm = ref<{ ip: string; name: string; fields: Record<string, string> }>({ ip: '', name: '', fields: {} })
const failEditSaving = ref(false)
const retryingAll = ref(false)

function openFailEdit(idx: number) {
  const row = importFailedRows.value[idx]!
  failEditForm.value = { ip: row.ip, name: row.name, fields: { ...row.fields } }
  failEditIdx.value = idx
}

async function doImportRowRetry(row: ImportFailedRow) {
  const rowAssetType = row.fields['자산유형'] || '서버'
  const existing = rows.value.find(r => {
    const t = (r.fields?.['자산유형'] as string) || '서버'
    if (t !== rowAssetType) return false
    // IP가 있으면 IP 기준, 없으면 hostname 기준 매칭
    if (row.ip) return r.ip === row.ip
    return r.name === row.name
  })
  if (existing) {
    const nextFields = { ...(existing.fields ?? {}), ...row.fields }
    const retryAssetId = row.fields['asset_id'] || existing.assetId || null
    const patch: Record<string, unknown> = { fields: nextFields, asset_id: retryAssetId }
    if (row.name && row.name !== existing.name) patch['name'] = row.name
    const retryCat = row.fields['자산유형'] || importOverrideCategory.value || category.value || '서버'
    const updated_ = await patchServer(String(existing.id), patch as Parameters<typeof patchServer>[1], retryCat)
    rows.value = rows.value.map(r => r.id === existing.id ? updated_ : r)
  } else {
    const createF = { ...row.fields }
    const retryAssetId = row.fields['asset_id'] || null
    const retryCatNew = row.fields['자산유형'] || importOverrideCategory.value || category.value || '서버'
    const newServer = await createServer(row.ip, row.name || row.ip, Object.keys(createF).length > 0 ? createF : undefined, undefined, retryCatNew, retryAssetId)
    rows.value = [newServer, ...rows.value]
  }
}

async function retryFailRow(idx: number) {
  const row = importFailedRows.value[idx]!
  row.retrying = true
  try {
    await doImportRowRetry(row)
    row.retrySuccess = true
  } catch (err: unknown) {
    row.error = getErrorMessage(err, '재시도 실패')
  } finally {
    row.retrying = false
  }
}

async function saveAndRetry(idx: number) {
  const row = importFailedRows.value[idx]!
  row.ip = failEditForm.value.ip
  row.name = failEditForm.value.name
  row.fields = { ...failEditForm.value.fields }
  failEditIdx.value = -1
  failEditSaving.value = true
  await retryFailRow(idx)
  failEditSaving.value = false
}

async function retryAllFailed() {
  retryingAll.value = true
  for (let i = 0; i < importFailedRows.value.length; i++) {
    const row = importFailedRows.value[i]!
    if (row.retrySuccess) continue
    await retryFailRow(i)
  }
  retryingAll.value = false
}

function openSkipEdit(idx: number) {
  const row = importSkippedRows.value[idx]!
  const fields: Record<string, string> = {}
  for (const [k, v] of Object.entries(row.rawData)) {
    if (k !== 'ip' && k !== 'name') fields[k] = v
  }
  skipEditForm.value = { ip: row.ip, name: row.name, fields }
  skipEditIdx.value = idx
}

async function retrySkipRow(idx: number) {
  const row = importSkippedRows.value[idx]!
  row.retrying = true
  try {
    const fields: Record<string, string> = {}
    for (const [k, v] of Object.entries(row.rawData)) {
      if (k !== 'ip' && k !== 'name') fields[k] = v
    }
    await doImportRowRetry({ ...row, fields, isNew: !rows.value.some(r => r.ip === row.ip), error: '', retrying: false, retrySuccess: false })
    row.retrySuccess = true
  } catch (err: unknown) {
    row.reason = getErrorMessage(err, '재시도 실패')
  } finally {
    row.retrying = false
  }
}

async function saveAndRetrySkip(idx: number) {
  const row = importSkippedRows.value[idx]!
  row.ip = skipEditForm.value.ip
  row.name = skipEditForm.value.name
  // rawData를 편집된 값으로 업데이트해서 retrySkipRow에서 반영되도록
  for (const [k, v] of Object.entries(skipEditForm.value.fields)) {
    row.rawData[k] = v
  }
  skipEditIdx.value = -1
  skipEditSaving.value = true
  await retrySkipRow(idx)
  skipEditSaving.value = false
}

async function forceApplySkip(idx: number) {
  const row = importSkippedRows.value[idx]!
  row.retrying = true
  try {
    const existing = row.conflictWith
    if (!existing) { await retrySkipRow(idx); return }
    const newFields: Record<string, string> = {}
    for (const [k, v] of Object.entries(row.rawData)) {
      if (k !== 'ip' && k !== 'name') newFields[k] = v
    }
    const nextFields = { ...(existing.fields ?? {}), ...newFields }
    const skipAssetId = newFields['asset_id'] ?? existing.assetId ?? null
    const patch: Record<string, unknown> = { fields: nextFields, asset_id: skipAssetId }
    if (row.name && row.name !== existing.name) patch['name'] = row.name
    const skipCat = ((existing.fields?.['자산유형'] as string) || importOverrideCategory.value || category.value || '서버')
    const updated_ = await patchServer(String(existing.id), patch as Parameters<typeof patchServer>[1], skipCat)
    rows.value = rows.value.map(r => r.id === existing.id ? updated_ : r)
    row.retrySuccess = true
  } catch (err: unknown) {
    row.reason = getErrorMessage(err, '강제 저장 실패')
  } finally {
    row.retrying = false
  }
}

async function forceApplyFailed(idx: number) {
  const row = importFailedRows.value[idx]!
  row.retrying = true
  try {
    const existing = row.conflictWith
    if (!existing) { await retryFailRow(idx); return }
    const nextFields = { ...(existing.fields ?? {}), ...row.fields }
    const failAssetId = row.fields['asset_id'] || existing.assetId || null
    const patch: Record<string, unknown> = { fields: nextFields, asset_id: failAssetId }
    if (row.name && row.name !== existing.name) patch['name'] = row.name
    const failCat = ((existing.fields?.['자산유형'] as string) || importOverrideCategory.value || category.value || '서버')
    const updated_ = await patchServer(String(existing.id), patch as Parameters<typeof patchServer>[1], failCat)
    rows.value = rows.value.map(r => r.id === existing.id ? updated_ : r)
    row.retrySuccess = true
  } catch (err: unknown) {
    row.error = getErrorMessage(err, '강제 저장 실패')
  } finally {
    row.retrying = false
  }
}

function triggerImport() {
  importOverrideCategory.value = ''
  importFileInput.value?.click()
}


async function onImportPasswordConfirm() {
  if (!pendingImportBuf.value) return
  if (importing.value) return
  importPasswordDialog.value = false
  importing.value = true
  try {
    const blob = new Blob([pendingImportBuf.value])
    const form = new FormData()
    form.append('file', blob, 'import.xlsx')
    const res = await api.post<ArrayBuffer>(
      `/assets/decrypt-xlsx?password=${encodeURIComponent(importPassword.value)}`,
      form,
      { responseType: 'arraybuffer' },
    )
    await _runImport(res.data, '')
  } catch (err: unknown) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, '비밀번호가 올바르지 않습니다.') })
  } finally {
    importing.value = false
    importPassword.value = ''
    importPasswordVisible.value = false
  }
}

async function onImportFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (importing.value) return
  importing.value = true
  ;(e.target as HTMLInputElement).value = ''

  try {
    const buf = await file.arrayBuffer()
    pendingImportBuf.value = buf
    await _runImport(buf, '')
  } catch (err: unknown) {
    console.error('[Import] onImportFile unhandled error:', err)
  } finally {
    importing.value = false
  }
}

function _showPasswordDialog() {
  importPassword.value = ''
  importPasswordVisible.value = false
  importPasswordDialog.value = true
}

async function _runImport(buf: ArrayBuffer, password: string) {
  importing.value = true
  try {
    await fetchEosMap()
    const wb = XLSX.read(buf, { type: 'array', cellDates: true, ...(password ? { password } : {}) })
    const ws = wb.Sheets[wb.SheetNames[0]!]
    if (!ws) throw new Error('시트를 찾을 수 없습니다.')

    const allRows = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, defval: '' })
    if (allRows.length < 2) throw new Error('데이터가 없습니다.')

    // 첫 행 = 헤더, 헤더로 컬럼 키 매핑
    const headerRow = (allRows[0] as unknown[]).map(h => String(h).trim())

    const labelToKey: Record<string, string> = {
      'IP': 'ip',
      'HostName': 'name',
      'Asset ID': 'asset_id',
      'asset_id': 'asset_id',
      '__asset_id__': 'asset_id',
      // 하위 호환 (구 템플릿 라벨)
      '배포판': '운영체제',
      'DB종류': '운영체제',
      'VADA설치여부': VADA_KEY,
      '백신여부': ANTIVIRUS_KEY,
      '백신 여부': ANTIVIRUS_KEY,
      'ISMS-P대상여부': ISMS_P_KEY,
      'ISMS-P 대상 여부': ISMS_P_KEY,
      'ISMS-P비고': 'ISMS-P비고',
      'VADA비고': 'VADA비고',
      '백신비고': '백신비고',
      'EoL여부': EOL_STATUS_KEY,
      'EoL종료일자': EOL_DATE_KEY,
      'EoS여부': EOS_STATUS_KEY,
      'EoS종료일자': EOS_DATE_KEY,
      // 합성 라벨 (key / display 형식)
      '자산유형(서버 / 네트워크 / DBMS / 정보보호시스템 / VMware)': '자산유형',
      '자산 종류': '자산유형',
      '운영체제 / 배포판': '운영체제',
      '운영체제 / 기종': '운영체제',
      '운영체제 / DB종류': '운영체제',
      '운영체제 / 버전': '운영체제',
      '운영체제 / 배포판 / 기종 / DB종류': '운영체제',
      '서버명 / 자산명': '서버명',
      '중분류(구분)': '구분',
      '용도(상세)': '용도',
      '소속부서/사업': '소속부서',
      '제품명(모델명)': '제품명',
      '도입일자(취득일자)': '도입일자',
      'Rack Unit No.': 'rack_unit_no',
      // FIELD_LABEL_MAP 역방향 (현재 라벨 → 키)
      ...Object.fromEntries(Object.entries(FIELD_LABEL_MAP).map(([k, v]) => [v, k])),
    }
    // 모든 알려진 필드키에 대해: 현재 카테고리 기준 fieldLabel() 결과 및 키 자체를 모두 매핑
    const allKnownKeys = [...PREFERRED_FIELD_KEYS, '자산유형', TAGS_KEY, VADA_KEY, 'VADA비고', ANTIVIRUS_KEY, '백신비고', ISMS_P_KEY, 'ISMS-P비고', EOS_STATUS_KEY, EOS_DATE_KEY, EOL_STATUS_KEY, EOL_DATE_KEY]
    for (const k of allKnownKeys) {
      const label = fieldLabel(k)
      if (!labelToKey[label]) labelToKey[label] = k
      if (!labelToKey[k]) labelToKey[k] = k
    }
    // 네트워크 기종은 항상 운영체제로
    labelToKey['기종'] = '운영체제'

    const colKeys = headerRow.map(h => labelToKey[h] ?? h)

    // asset_id 기준 맵 (1순위 PK 매칭)
    const assetIdIndex = colKeys.indexOf('asset_id')
    console.log('[Import] headerRow:', headerRow)
    console.log('[Import] colKeys:', colKeys)
    console.log('[Import] assetIdIndex:', assetIdIndex, '/ ipIndex will be:', colKeys.indexOf('ip'))
    const existingByAssetId = new Map(rows.value.filter(r => r.assetId).map(r => [r.assetId!, r]))
    console.log('[Import] existingByAssetId size:', existingByAssetId.size)

    // IP 기준으로 기존 서버 맵 (폴백)
    const ipIndex = colKeys.indexOf('ip')

    // ip + 자산유형 + hostname 복합키 (같은 IP라도 hostname이 다르면 별개 레코드)
    const assetTypeKey = (r: { ip: string; name: string; fields?: Record<string, unknown> | null }) =>
      `${r.ip}__${(r.fields?.['자산유형'] as string) || '서버'}__${r.name}`
    const existingByIp = new Map(rows.value.filter(r => r.ip).map(r => [assetTypeKey(r), r]))

    // hostname 기준 맵 (IP가 없는 행 매칭용)
    const assetTypeNameKey = (r: { name: string; fields?: Record<string, unknown> | null }) =>
      `${r.name}__${(r.fields?.['자산유형'] as string) || '서버'}`
    const existingByName = new Map(rows.value.filter(r => r.name).map(r => [assetTypeNameKey(r), r]))

    console.log('[Import] rows.value:', rows.value.length, '/ existingByIp keys:', existingByIp.size, '/ filteredRows:', filteredRows.value.length)

    let created = 0
    const updatedIds = new Set<string>()
    const processedKeys = new Set<string>() // 이번 import에서 이미 처리한 key 추적 (중복 감지용)
    const newFailedRows: ImportFailedRow[] = []
    const newSkippedRows: ImportSkippedRow[] = []

    for (let rowIdx = 0; rowIdx < allRows.slice(1).length; rowIdx++) {
      const rawRow = allRows.slice(1)[rowIdx]!
      const row = Array.isArray(rawRow) ? rawRow : []
      function cellStr(val: unknown, colKey?: string): string {
        if (val === null || val === undefined) return ''
        if (typeof val === 'number') {
          const s = String(val)
          // version 필드: Excel이 "8.10" 등을 숫자 8.1로 변환하는 현상 보정 (x.1 → x.10)
          // 숫자로 들어온 경우에만 적용 (문자열 "8.1"은 그대로 유지)
          if (colKey === 'version' && /^\d+\.1$/.test(s)) return s.replace(/\.1$/, '.10')
          return s
        }
        if (typeof val === 'string' || typeof val === 'boolean') return String(val)
        // cellDates: true 로 인해 Date 객체가 올 수 있음 → YYYY-MM-DD로 변환
        if (val instanceof Date && !Number.isNaN(val.getTime())) {
          const y = val.getFullYear()
          const m = String(val.getMonth() + 1).padStart(2, '0')
          const d = String(val.getDate()).padStart(2, '0')
          return `${y}-${m}-${d}`
        }
        return ''
      }

      const ip = cellStr(row[ipIndex]).trim()

      // 행 원본 데이터 수집 (건너뜀 사유 표시용)
      const rawData: Record<string, string> = {}
      colKeys.forEach((k, i) => { const v = cellStr(row[i]).trim(); if (v) rawData[k] = v })

      if (!ip) {
        const nameIdx2 = colKeys.indexOf('name')
        const hostname2 = nameIdx2 >= 0 ? cellStr(row[nameIdx2]).trim() : ''

        if (!hostname2) {
          // IP도 hostname도 없음 → asset_id로 시도, 없으면 건너뜀
          const fields2Empty: Record<string, string> = {}
          colKeys.forEach((k, i) => {
            if (k === 'ip' || k === 'name' || k === 'asset_id' || k === '__asset_id__') return
            const v = cellStr(row[i], k).trim()
            if (v) fields2Empty[k] = v
          })
          const importAssetId2Empty = assetIdIndex >= 0 ? cellStr(row[assetIdIndex]).trim() || null : null
          const existingByNo2Empty = importAssetId2Empty ? existingByAssetId.get(importAssetId2Empty) : undefined
          if (existingByNo2Empty) {
            const nextFields2Empty = { ...(existingByNo2Empty.fields ?? {}), ...fields2Empty }
            try {
              const updated2Empty = await patchServer(String(existingByNo2Empty.id), { fields: nextFields2Empty, asset_id: importAssetId2Empty ?? existingByNo2Empty.assetId ?? null } as Parameters<typeof patchServer>[1], (fields2Empty['자산유형'] || importOverrideCategory.value || category.value || '서버'))
              rows.value = rows.value.map(r => r.id === existingByNo2Empty.id ? updated2Empty : r)
              existingByAssetId.set(importAssetId2Empty!, updated2Empty)
              updatedIds.add(String(existingByNo2Empty.id))
            } catch (err: unknown) {
              newFailedRows.push({ rowIndex: rowIdx + 2, ip: '', name: '', fields: fields2Empty, error: getErrorMessage(err, '오류'), isNew: false, retrying: false, retrySuccess: false })
            }
          } else if (importAssetId2Empty) {
            // Asset ID는 있지만 기존 레코드 없음 → 신규 생성
            const createF2Empty = { ...fields2Empty }
            try {
              const newServer2Empty = await createServer('', '', Object.keys(createF2Empty).length > 0 ? createF2Empty : undefined, undefined, fields2Empty['자산유형'] || importOverrideCategory.value || category.value || '서버', importAssetId2Empty)
              rows.value = [newServer2Empty, ...rows.value]
              existingByAssetId.set(importAssetId2Empty, newServer2Empty)
              created++
            } catch (err: unknown) {
              newFailedRows.push({ rowIndex: rowIdx + 2, ip: '', name: '', fields: fields2Empty, error: getErrorMessage(err, '오류'), isNew: true, retrying: false, retrySuccess: false })
            }
          } else {
            const hasAnyData = Object.keys(rawData).some(k => k !== 'ip' && rawData[k])
            const reason = hasAnyData
              ? 'IP와 HostName이 모두 비어 있음 — 어떤 자산인지 특정할 수 없습니다.'
              : '해당 행 전체가 비어 있습니다.'
            newSkippedRows.push({ rowIndex: rowIdx + 2, ip: '', name: '', reason, rawData, retrying: false, retrySuccess: false })
          }
          continue
        }

        // IP 없고 hostname 있음 → hostname 기준으로 처리
        const fields2: Record<string, string> = {}
        colKeys.forEach((k, i) => {
          if (k === 'ip' || k === 'name' || k === 'asset_id' || k === '__asset_id__') return
          let v = cellStr(row[i], k).trim()
          if (k === EOS_DATE_KEY && /^\d{4}-\d{2}-\d{2}/.test(v)) v = v.slice(0, 7)
          if (k === '운영체제') v = normalizeOsName(v)
          if (v) fields2[k] = v
        })
        const rowAssetType2 = fields2['자산유형'] || '서버'
        if (!fields2[EOS_STATUS_KEY]) {
          const eos = getAutoEos(fields2['운영체제'] ?? '', fields2['version'] ?? '')
            ?? (['네트워크', '정보보호시스템'].includes(rowAssetType2) ? getNetworkEos(fields2['운영체제'] ?? '') : null)
          if (eos) { fields2[EOS_STATUS_KEY] = eos.status; fields2[EOS_DATE_KEY] = eos.date }
        }

        const importAssetId2 = assetIdIndex >= 0 ? cellStr(row[assetIdIndex]).trim() || null : null
        const nameKey = `${hostname2}__${rowAssetType2}`
        const isNew2 = !existingByName.has(nameKey)
        try {
          const existing2 = existingByName.get(nameKey)
          if (existing2) {
            // hostname 기준 기존 서버 업데이트
            const nextFields2 = { ...(existing2.fields ?? {}), ...fields2 }
            // 중복 행 검사: 이미 처리한 key이고 변경 사항이 없으면 생략
            if (processedKeys.has(nameKey)) {
              const curFields2 = existing2.fields ?? {}
              const noFieldChange2 = Object.entries(nextFields2).every(([k, v]) => JSON.stringify(v) === JSON.stringify(curFields2[k] ?? ''))
              if (noFieldChange2) {
                newSkippedRows.push({ rowIndex: rowIdx + 2, ip: '', name: hostname2, reason: '중복 행 — 동일한 데이터가 이미 처리됨', rawData: { ...rawData }, retrying: false, retrySuccess: false, conflictWith: existing2 })
                processedKeys.add(nameKey)
                continue
              }
            }
            const updated2 = await patchServer(String(existing2.id), { fields: nextFields2, asset_id: importAssetId2 ?? existing2.assetId ?? null } as Parameters<typeof patchServer>[1], rowAssetType2)
            rows.value = rows.value.map(r => r.id === existing2.id ? updated2 : r)
            existingByName.set(nameKey, updated2)
            updatedIds.add(String(existing2.id))
            processedKeys.add(nameKey)
          } else {
            // asset_id 기준 기존 레코드 폴백 조회
            const existingByNo2 = importAssetId2 ? existingByAssetId.get(importAssetId2) : undefined
            if (existingByNo2) {
              const nextFields2 = { ...(existingByNo2.fields ?? {}), ...fields2 }
              const updated2 = await patchServer(String(existingByNo2.id), { fields: nextFields2, asset_id: importAssetId2 ?? existingByNo2.assetId ?? null } as Parameters<typeof patchServer>[1], rowAssetType2)
              rows.value = rows.value.map(r => r.id === existingByNo2.id ? updated2 : r)
              existingByName.set(nameKey, updated2)
              existingByAssetId.set(importAssetId2!, updated2)
              updatedIds.add(String(existingByNo2.id))
              processedKeys.add(nameKey)
            } else {
              // hostname만으로 신규 생성 (IP 빈 값)
              const createF2 = { ...fields2 }
              const newServer2 = await createServer('', hostname2, Object.keys(createF2).length > 0 ? createF2 : undefined, undefined, rowAssetType2, importAssetId2)
              rows.value = [newServer2, ...rows.value]
              existingByName.set(nameKey, newServer2)
              if (importAssetId2) existingByAssetId.set(importAssetId2, newServer2)
              processedKeys.add(nameKey)
              created++
            }
          }
        } catch (rowErr2: unknown) {
          newFailedRows.push({
            rowIndex: rowIdx + 2,
            ip: '',
            name: hostname2,
            fields: { ...fields2 },
            error: getErrorMessage(rowErr2, '오류'),
            isNew: isNew2,
            retrying: false,
            retrySuccess: false,
          })
        }
        continue
      }

      const nameIdx = colKeys.indexOf('name')
      const hostname = nameIdx >= 0 ? cellStr(row[nameIdx]).trim() : ''

      // 동적 필드 수집
      const fields: Record<string, string> = {}
      colKeys.forEach((k, i) => {
        if (k === 'ip' || k === 'name' || k === 'asset_id' || k === '__asset_id__') return
        let v = cellStr(row[i], k).trim()
        // EoS 종료 일자는 YYYY-MM 형식으로 정규화
        if (k === EOS_DATE_KEY && /^\d{4}-\d{2}-\d{2}/.test(v)) v = v.slice(0, 7)
        if (k === '운영체제') v = normalizeOsName(v)
        if (v) fields[k] = v
      })

      const rowAssetType = fields['자산유형'] || '서버'

      // 운영체제 + 버전이 있으면 EoS 자동 기입 (명시된 값이 없을 때만)
      if (!fields[EOS_STATUS_KEY]) {
        const eos = getAutoEos(fields['운영체제'] ?? '', fields['version'] ?? '')
          ?? (['네트워크', '정보보호시스템'].includes(rowAssetType) ? getNetworkEos(fields['운영체제'] ?? '') : null)
        if (eos) {
          fields[EOS_STATUS_KEY] = eos.status
          fields[EOS_DATE_KEY] = eos.date
        }
      }
      const importAssetId = assetIdIndex >= 0 ? cellStr(row[assetIdIndex]).trim() || null : null
      // ip + 자산유형 + hostname 복합키 → 같은 IP라도 hostname이 다르면 별개 레코드
      const rowKey = `${ip}__${rowAssetType}__${hostname}`

      // 매칭 우선순위: 1) asset_id  2) IP+자산유형+hostname
      const existingByNo = importAssetId ? existingByAssetId.get(importAssetId) : undefined
      const ipCandidate = existingByIp.get(rowKey)
      // asset_id가 있는데 IP 매칭 레코드의 asset_id와 다르면 → 별개 레코드
      const ipMatch = ipCandidate && (!importAssetId || !ipCandidate.assetId || ipCandidate.assetId === importAssetId)
        ? ipCandidate : undefined
      const existing = existingByNo ?? ipMatch
      const matchKey = existingByNo ? `assetId:${importAssetId}` : rowKey
      const isNew = !existing
      try {
        if (existing) {
          // 기존 서버 업데이트
          const nextFields = { ...(existing.fields ?? {}), ...fields }
          // 중복 행 검사: 이미 처리한 key이고 변경 사항이 없으면 생략
          if (processedKeys.has(matchKey)) {
            const curFields = existing.fields ?? {}
            const noFieldChange = Object.entries(nextFields).every(([k, v]) => JSON.stringify(v) === JSON.stringify(curFields[k] ?? ''))
            const noNameChange = !hostname || hostname === existing.name
            if (noFieldChange && noNameChange) {
              newSkippedRows.push({ rowIndex: rowIdx + 2, ip, name: hostname, reason: '중복 행 — 동일한 데이터가 이미 처리됨', rawData: { ...rawData }, retrying: false, retrySuccess: false, conflictWith: existing })
            } else {
              newSkippedRows.push({ rowIndex: rowIdx + 2, ip, name: hostname, reason: '중복 행 — 같은 자산을 다른 행에서 이미 처리함 (데이터 상이)', rawData: { ...rawData }, retrying: false, retrySuccess: false, conflictWith: existing })
            }
            continue
          }
          const patch: Record<string, unknown> = { fields: nextFields, asset_id: importAssetId ?? existing.assetId ?? null }
          if (hostname && hostname !== existing.name) patch['name'] = hostname
          if (ip && ip !== existing.ip) patch['ip'] = ip
          const updated_ = await patchServer(String(existing.id), patch as Parameters<typeof patchServer>[1], rowAssetType)
          rows.value = rows.value.map(r => r.id === existing.id ? updated_ : r)
          existingByIp.set(rowKey, updated_)
          if (importAssetId) existingByAssetId.set(importAssetId, updated_)
          updatedIds.add(String(existing.id))
          processedKeys.add(matchKey)
        } else {
          // 신규 서버 생성 — HostName 없으면 IP를 기본값으로 사용
          const createF = { ...fields }
          const newServer = await createServer(ip, hostname || ip, Object.keys(createF).length > 0 ? createF : undefined, undefined, rowAssetType, importAssetId)
          rows.value = [newServer, ...rows.value]
          existingByIp.set(rowKey, newServer)
          if (importAssetId) existingByAssetId.set(importAssetId, newServer)
          processedKeys.add(rowKey)
          created++
        }
      } catch (rowErr: unknown) {
        const conflictWith = existingByIp.get(rowKey)
          ?? (hostname ? rows.value.find(r => r.name === hostname && !r.isDeleted) : null)
          ?? null
        newFailedRows.push({
          rowIndex: rowIdx + 2, // 엑셀 행 번호 (헤더=1, 첫 데이터=2)
          ip,
          name: hostname,
          fields: { ...fields },
          error: getErrorMessage(rowErr, '오류'),
          isNew,
          retrying: false,
          retrySuccess: false,
          conflictWith,
        })
      }
    }
    console.log('[Import] done — created:', created, '/ updatedIds.size:', updatedIds.size, '/ processedKeys.size:', processedKeys.size, '/ skipped:', newSkippedRows.length, '/ failed:', newFailedRows.length)

    if (newFailedRows.length > 0 || newSkippedRows.length > 0) {
      importFailedRows.value = newFailedRows
      importSkippedRows.value = newSkippedRows
      importResultTab.value = newFailedRows.length > 0 ? 'failed' : 'skipped'
      importFailDialog.value = true
    }

    const updated = updatedIds.size
    const skipped = newSkippedRows.length
    const totalVisible = filteredRows.value.length
    const totalAll = rows.value.length
    const filterNote = totalAll !== totalVisible
      ? ` — 필터로 인해 ${totalVisible}건 표시 중 (전체 ${totalAll}건)`
      : ''
    $q.notify({
      type: newFailedRows.length > 0 ? 'warning' : 'positive',
      message: `Import 완료: 신규 ${created}건, 업데이트 ${updated}건${skipped ? `, 건너뜀 ${skipped}건` : ''}${newFailedRows.length ? `, 실패 ${newFailedRows.length}건` : ''}${filterNote}`,
    })
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err)
    const lower = errMsg.toLowerCase()
    if (lower.includes('file is password') || (lower.includes('password') && !lower.includes('incorrect'))) {
      _showPasswordDialog()
    } else if (lower.includes('incorrect') || lower.includes('wrong')) {
      _showPasswordDialog()
      $q.notify({ type: 'negative', message: '비밀번호가 틀렸습니다.' })
    } else if (lower.includes('unsupported') || lower.includes('scheme')) {
      $q.notify({ type: 'negative', message: '지원하지 않는 암호화 방식입니다.' })
    } else {
      $q.notify({ type: 'negative', message: getErrorMessage(err, 'Import 실패') })
    }
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  void fetchEosMap()  // endoflife.date 에서 EoS 맵 로드 (백그라운드)
  void load()
})
</script>

<style scoped>
.conflict-diff-table {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
  margin-top: 2px;
}
.conflict-diff-table th,
.conflict-diff-table td {
  border: 1px solid #e0e0e0;
  padding: 3px 8px;
  white-space: nowrap;
}
.conflict-diff-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #555;
}
.conflict-diff-table .diff-row {
  background: #fff8e1;
}
.conflict-diff-table .diff-row td:first-child {
  font-weight: 600;
}
.conflict-diff-table .diff-row td:nth-child(2) {
  color: #b71c1c;
  text-decoration: line-through;
}
.conflict-diff-table .diff-row td:nth-child(3) {
  color: #1b5e20;
  font-weight: 600;
}

.sticky-header-table thead tr th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: white;
}

.sticky-actions-col {
  position: sticky;
  right: 0;
  background: white;
  box-shadow: -2px 0 4px rgba(0, 0, 0, 0.08);
}

thead .sticky-actions-col {
  z-index: 4;
}

tbody .sticky-actions-col {
  z-index: 1;
}

.doc-table {
  border-collapse: collapse;
  border: 1px solid #9e9e9e;
  font-size: 13px;
}
.doc-table th,
.doc-table td {
  border: 1px solid #9e9e9e;
}
.section-title-cell {
  background-color: #d6d6d6;
  font-weight: bold;
  text-align: center;
  padding: 5px 10px;
  font-size: 13px;
}
.label-cell {
  background-color: #f0f0f0;
  font-weight: 500;
  padding: 5px 10px;
  white-space: nowrap;
  vertical-align: middle;
  font-size: 12px;
  width: 120px;
}
.value-cell {
  background-color: #ffffff;
  padding: 5px 10px;
  vertical-align: middle;
  font-size: 13px;
}

/* ===== Server form dialog styles ===== */
.server-form-card {
  width: 660px;
  max-width: 95vw;
  border-radius: 8px;
}

/* 상단 강조 필드 (호스트명, IP) */
.top-field-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.top-field-label {
  font-size: 16px;
  color: #555;
  white-space: nowrap;
  min-width: 80px;
  flex-shrink: 0;
}
.top-field-input {
  flex: 1;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
  font-size: 16px;
}
.top-field-input :deep(.q-field__control) {
  padding: 0;
  min-height: 32px;
}
.req-star {
  color: #1976d2;
  margin-left: 1px;
}

/* 회색 구분 바 */
.gray-section-bar {
  background: #f5f5f5;
  padding: 8px 16px;
  font-size: 12px;
  color: #888;
  text-align: center;
  letter-spacing: 0.5px;
}

/* 섹션 타이틀 + 분홍 구분선 */
.section-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #444;
  white-space: nowrap;
}
.section-divider {
  border-top: 2px solid #1976d2;
  margin-bottom: 4px;
}

/* 폼 필드 (라벨 위, 언더라인 입력) */
.form-field {
  display: flex;
  flex-direction: column;
}
.field-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 2px;
  line-height: 1.2;
}
.field-input {
  border-bottom: 1px solid rgba(0, 0, 0, 0.15);
}
.field-input :deep(.q-field__control) {
  padding: 0 2px;
  min-height: 30px;
}
.field-input :deep(.q-field__native) {
  font-size: 14px;
  color: #333;
  padding: 2px 0;
}
.field-disabled {
  color: #bbb;
  font-size: 14px;
  padding: 4px 2px;
}

/* EoS 배너 */
.eos-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.eos-banner--active {
  background: #e8f5e9;
  color: #2e7d32;
}
.eos-banner--eos {
  background: #fce4ec;
  color: #c62828;
}
.eos-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.eos-item-label {
  font-size: 11px;
  opacity: 0.7;
}
.eos-sep {
  opacity: 0.4;
}

/* 상세보기 값 표시 */
.top-field-value {
  font-size: 16px;
  color: #333;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  flex: 1;
  padding: 2px 0;
}
.detail-value {
  font-size: 14px;
  color: #333;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  padding: 4px 2px;
  min-height: 28px;
}

/* 생성/저장 버튼 */
.create-btn {
  background: #1976d2;
  color: #fff;
  font-weight: 600;
  padding: 6px 28px;
  border-radius: 4px;
}
.create-btn:hover {
  background: #1565c0;
}

/* 삭제된 행 스타일 */
.cell-deleted {
  text-decoration: line-through;
  background-color: #f5f5f5 !important;
  color: rgba(0, 0, 0, 0.35) !important;
}
.cell-deleted-actions > * {
  opacity: 0.7;
}
.cell-deleted-actions {
  background-color: #f5f5f5 !important;
}
.col-item:hover {
  background: #f5f5f5;
  border-radius: 4px;
}
.cursor-grab {
  cursor: grab;
}
.cursor-grab:active {
  cursor: grabbing;
}
</style>
