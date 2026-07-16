<template>
  <q-page class="q-pa-md">
    <!-- 헤더 -->
    <div class="row items-center q-mb-lg">
      <div>
        <div class="row items-center q-gutter-x-sm">
          <span class="text-h6 text-weight-bold">{{ project?.name ?? '...' }}</span>
          <q-badge v-if="project" color="primary" :label="project.key" />
        </div>
        <div class="text-caption text-grey-5 q-mt-xs">백로그</div>
      </div>
      <q-space />
      <q-btn color="primary" unelevated icon="add" label="이슈 추가" @click="createDialog.open = true" />
    </div>

    <!-- 필터 카드 -->
    <q-card class="filter-card q-mb-md" bordered>
      <div class="q-px-md q-pt-md q-pb-sm">
        <q-input
          v-model="filterSearch"
          dense
          outlined
          clearable
          placeholder="이슈 제목으로 검색..."
          class="filter-search-input"
        >
          <template #prepend>
            <q-icon name="search" color="grey-5" />
          </template>
          <template #append>
            <q-btn flat dense round icon="refresh" color="grey-5" size="sm" @click="loadIssues">
              <q-tooltip>새로고침</q-tooltip>
            </q-btn>
          </template>
        </q-input>
      </div>

      <q-separator />

      <div class="row items-center q-px-md q-py-xs q-gutter-x-xs flex-wrap">
        <span class="text-caption text-grey-5 q-mr-xs" style="line-height: 32px">필터</span>

        <!-- 상태 -->
        <q-chip
          :color="filterStatus ? 'primary' : undefined"
          :text-color="filterStatus ? 'white' : 'grey-8'"
          :outline="!filterStatus"
          clickable
          :removable="!!filterStatus"
          @remove="filterStatus = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterStatus" name="radio_button_checked" size="10px" class="q-mr-xs" />
          <span>{{ filterStatus ? STATUS_LABEL[filterStatus] : '상태' }}</span>
          <q-icon v-if="!filterStatus" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">상태 선택</q-item-label>
              <q-item v-for="opt in statusOptions" :key="opt.value" clickable v-close-popup @click="filterStatus = opt.value">
                <q-item-section side style="padding-right: 8px; min-width: 24px">
                  <q-badge :color="STATUS_COLOR[opt.value]" rounded style="width: 8px; height: 8px; min-width: 8px" />
                </q-item-section>
                <q-item-section>{{ opt.label }}</q-item-section>
                <q-item-section side v-if="filterStatus === opt.value">
                  <q-icon name="check" color="primary" size="xs" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!-- 우선순위 -->
        <q-chip
          :color="filterPriority ? 'orange-7' : undefined"
          :text-color="filterPriority ? 'white' : 'grey-8'"
          :outline="!filterPriority"
          clickable
          :removable="!!filterPriority"
          @remove="filterPriority = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterPriority" :name="PRIORITY_ICON[filterPriority]" size="10px" class="q-mr-xs" />
          <span>{{ filterPriority ? PRIORITY_LABEL[filterPriority] : '우선순위' }}</span>
          <q-icon v-if="!filterPriority" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">우선순위 선택</q-item-label>
              <q-item v-for="opt in priorityOptions" :key="opt.value" clickable v-close-popup @click="filterPriority = opt.value">
                <q-item-section side style="padding-right: 8px; min-width: 24px">
                  <q-icon :name="PRIORITY_ICON[opt.value]" :color="PRIORITY_COLOR[opt.value]" size="xs" />
                </q-item-section>
                <q-item-section>{{ opt.label }}</q-item-section>
                <q-item-section side v-if="filterPriority === opt.value">
                  <q-icon name="check" color="orange-7" size="xs" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!-- 타입 -->
        <q-chip
          :color="filterType ? TYPE_COLOR[filterType] : undefined"
          :text-color="filterType ? 'white' : 'grey-8'"
          :outline="!filterType"
          clickable
          :removable="!!filterType"
          @remove="filterType = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterType" :name="TYPE_ICON[filterType]" size="10px" class="q-mr-xs" />
          <span>{{ filterType ? TYPE_LABEL[filterType] : '유형' }}</span>
          <q-icon v-if="!filterType" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 150px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">유형 선택</q-item-label>
              <q-item v-for="opt in typeOptions" :key="opt.value" clickable v-close-popup @click="filterType = opt.value">
                <q-item-section side style="padding-right: 8px; min-width: 24px">
                  <q-icon :name="TYPE_ICON[opt.value]" :color="TYPE_COLOR[opt.value]" size="xs" />
                </q-item-section>
                <q-item-section>{{ opt.label }}</q-item-section>
                <q-item-section side v-if="filterType === opt.value">
                  <q-icon name="check" :color="TYPE_COLOR[opt.value]" size="xs" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!-- 담당자 -->
        <q-chip
          :color="filterAssigneeId ? 'teal' : undefined"
          :text-color="filterAssigneeId ? 'white' : 'grey-8'"
          :outline="!filterAssigneeId"
          clickable
          :removable="!!filterAssigneeId"
          @remove="filterAssigneeId = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon v-if="filterAssigneeId" name="person" size="10px" class="q-mr-xs" />
          <span>{{ filterAssigneeId ? (memberOptions.find(m => m.value === filterAssigneeId)?.label ?? '담당자') : '담당자' }}</span>
          <q-icon v-if="!filterAssigneeId" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu>
            <q-list dense style="min-width: 170px">
              <q-item-label header class="text-grey-5" style="font-size: 11px; padding-bottom: 4px">담당자 선택</q-item-label>
              <q-item v-if="memberOptions.length === 0" class="text-grey-5 text-caption q-px-md q-py-xs">멤버가 없습니다</q-item>
              <q-item v-for="opt in memberOptions" :key="opt.value" clickable v-close-popup @click="filterAssigneeId = opt.value">
                <q-item-section side style="padding-right: 8px; min-width: 28px">
                  <q-avatar size="22px" color="teal" text-color="white" font-size="11px">
                    {{ opt.label.charAt(0).toUpperCase() }}
                  </q-avatar>
                </q-item-section>
                <q-item-section>{{ opt.label }}</q-item-section>
                <q-item-section side v-if="filterAssigneeId === opt.value">
                  <q-icon name="check" color="teal" size="xs" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-chip>

        <!-- 마감일 기간 -->
        <q-chip
          :color="filterDateFrom || filterDateTo ? 'deep-orange-7' : undefined"
          :text-color="filterDateFrom || filterDateTo ? 'white' : 'grey-8'"
          :outline="!(filterDateFrom || filterDateTo)"
          clickable
          :removable="!!(filterDateFrom || filterDateTo)"
          @remove="filterDateFrom = null; filterDateTo = null"
          class="filter-chip"
          size="sm"
        >
          <q-icon name="event" size="10px" class="q-mr-xs" />
          <span>{{ filterDateFrom || filterDateTo
            ? `${filterDateFrom ?? '~'} ~ ${filterDateTo ?? '~'}`
            : '마감일' }}</span>
          <q-icon v-if="!(filterDateFrom || filterDateTo)" name="expand_more" size="14px" class="q-ml-xs" />
          <q-menu :offset="[0, 4]">
            <div class="q-pa-md" style="min-width: 240px">
              <div class="text-caption text-grey-6 q-mb-sm">마감일 기간</div>
              <q-input
                v-model="filterDateFrom"
                type="date"
                dense outlined clearable
                label="시작일"
                class="q-mb-sm"
              />
              <q-input
                v-model="filterDateTo"
                type="date"
                dense outlined clearable
                label="종료일"
              />
            </div>
          </q-menu>
        </q-chip>

        <!-- 필터 초기화 -->
        <q-btn
          v-if="hasFilter"
          flat dense no-caps
          icon="filter_list_off"
          label="초기화"
          color="negative"
          size="sm"
          class="q-ml-xs filter-clear-btn"
          @click="clearFilters"
        />

        <q-space />

        <span class="text-caption text-grey-5 q-mr-sm" style="white-space: nowrap">
          <span class="text-weight-medium text-grey-7">{{ filteredCount }}</span>개 이슈
        </span>

        <q-btn-group flat>
          <q-btn flat dense round icon="unfold_more" size="xs" color="grey-6" @click="expandAll">
            <q-tooltip>모두 펼치기</q-tooltip>
          </q-btn>
          <q-btn flat dense round icon="unfold_less" size="xs" color="grey-6" @click="collapseAll">
            <q-tooltip>모두 접기</q-tooltip>
          </q-btn>
        </q-btn-group>
      </div>
    </q-card>

    <q-inner-loading :showing="loading" />

    <!-- 트리 목록 -->
    <q-card flat bordered>
      <div v-if="allIssues.length === 0 && !loading" class="q-pa-lg text-grey-6 text-center">이슈가 없습니다.</div>

      <div class="backlog-tree">
        <!-- ── 에픽 (드래그 가능) ── -->
        <draggable
          v-model="orderedEpics"
          item-key="id"
          handle=".drag-handle-epic"
          :animation="150"
          ghost-class="drag-ghost"
          :disabled="hasFilter"
          @end="saveOrder"
        >
          <template #item="{ element: epic }">
            <div v-show="isEpicVisible(epic)">
              <!-- 에픽 행 -->
              <q-item clickable @click="openDetail(epic)" class="epic-row tree-item">
                <q-item-section class="tree-section-toggle">
                  <div class="row no-wrap items-center">
                    <q-icon
                      name="drag_indicator"
                      class="drag-handle-epic drag-handle-icon"
                      :class="{ 'drag-active': !hasFilter }"
                      size="16px"
                      @click.stop
                    />
                    <q-btn
                      v-if="_epicMains(epic.id).length > 0"
                      flat dense round size="xs"
                      :icon="collapsed.has(epic.id) ? 'chevron_right' : 'expand_more'"
                      @click.stop="toggleCollapse(epic.id)"
                    />
                    <div v-else style="width: 24px" />
                  </div>
                </q-item-section>
                <q-item-section class="tree-section-icon">
                  <q-icon :name="_typeIcon(epic.type)" :color="_typeColor(epic.type)" size="18px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-bold">
                    <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ epic.number }}</span>
                    {{ epic.title }}
                  </q-item-label>
                  <q-item-label caption class="q-mt-xs">
                    <q-badge :color="_statusClr(epic.status)" :label="_statusLbl(epic.status)" class="q-mr-xs" />
                    <q-icon :name="_prioIcon(epic.priority)" :color="_prioClr(epic.priority)" size="xs" />
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="assignee-chip">
                    <q-avatar v-if="epic.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                      {{ epic.assigneeName.charAt(0).toUpperCase() }}
                    </q-avatar>
                    <span class="text-caption" :class="epic.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                      {{ epic.assigneeName ?? '미배정' }}
                    </span>
                  </div>
                </q-item-section>
              </q-item>

              <!-- 에픽 하위 이슈 (드래그 가능, 펼쳐진 경우만) -->
              <template v-if="!collapsed.has(epic.id)">
                <draggable
                  :model-value="_epicMains(epic.id)"
                  @update:model-value="(v: Issue[]) => { orderedMainsByEpic[String(epic.id)] = v }"
                  item-key="id"
                  handle=".drag-handle-main"
                  :animation="150"
                  ghost-class="drag-ghost"
                  :disabled="hasFilter"
                  @end="saveOrder"
                >
                  <template #item="{ element: main }">
                    <div v-show="isMainVisible(main)">
                      <q-item clickable @click="openDetail(main)" class="tree-item" style="padding-left: 28px">
                        <q-item-section class="tree-section-toggle">
                          <div class="row no-wrap items-center">
                            <q-icon
                              name="drag_indicator"
                              class="drag-handle-main drag-handle-icon"
                              :class="{ 'drag-active': !hasFilter }"
                              size="16px"
                              @click.stop
                            />
                            <q-btn
                              v-if="_subsByMain(main.id).length > 0"
                              flat dense round size="xs"
                              :icon="collapsed.has(main.id) ? 'chevron_right' : 'expand_more'"
                              @click.stop="toggleCollapse(main.id)"
                            />
                            <div v-else style="width: 24px" />
                          </div>
                        </q-item-section>
                        <q-item-section class="tree-section-icon">
                          <q-icon :name="_typeIcon(main.type)" :color="_typeColor(main.type)" size="18px" />
                        </q-item-section>
                        <q-item-section>
                          <q-item-label>
                            <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ main.number }}</span>
                            {{ main.title }}
                          </q-item-label>
                          <q-item-label caption class="q-mt-xs">
                            <q-badge :color="_statusClr(main.status)" :label="_statusLbl(main.status)" class="q-mr-xs" />
                            <q-icon :name="_prioIcon(main.priority)" :color="_prioClr(main.priority)" size="xs" />
                            <span v-if="main.epicTitle" class="text-grey-5 q-ml-sm text-caption">{{ main.epicTitle }}</span>
                          </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <div class="assignee-chip">
                            <q-avatar v-if="main.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                              {{ main.assigneeName.charAt(0).toUpperCase() }}
                            </q-avatar>
                            <span class="text-caption" :class="main.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                              {{ main.assigneeName ?? '미배정' }}
                            </span>
                          </div>
                        </q-item-section>
                      </q-item>

                      <!-- 서브태스크 (indent 2 = 56px, 드래그 가능) -->
                      <template v-if="!collapsed.has(main.id)">
                        <draggable
                          :model-value="_subsByMain(main.id)"
                          @update:model-value="(v: Issue[]) => { orderedSubsByMain[String(main.id)] = v }"
                          item-key="id"
                          handle=".drag-handle-sub"
                          :animation="150"
                          ghost-class="drag-ghost"
                          :disabled="hasFilter"
                          @end="saveOrder"
                        >
                          <template #item="{ element: sub }">
                            <div v-show="!hasFilter || matches(sub)">
                              <q-item clickable @click="openDetail(sub)" class="tree-item" style="padding-left: 56px">
                                <q-item-section class="tree-section-toggle">
                                  <div class="row no-wrap items-center">
                                    <q-icon
                                      name="drag_indicator"
                                      class="drag-handle-sub drag-handle-icon"
                                      :class="{ 'drag-active': !hasFilter }"
                                      size="16px"
                                      @click.stop
                                    />
                                    <div style="width: 24px" />
                                  </div>
                                </q-item-section>
                                <q-item-section class="tree-section-icon">
                                  <q-icon :name="_typeIcon(sub.type)" :color="_typeColor(sub.type)" size="18px" />
                                </q-item-section>
                                <q-item-section>
                                  <q-item-label>
                                    <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ sub.number }}</span>
                                    {{ sub.title }}
                                  </q-item-label>
                                  <q-item-label caption class="q-mt-xs">
                                    <q-badge :color="_statusClr(sub.status)" :label="_statusLbl(sub.status)" class="q-mr-xs" />
                                    <q-icon :name="_prioIcon(sub.priority)" :color="_prioClr(sub.priority)" size="xs" />
                                  </q-item-label>
                                </q-item-section>
                                <q-item-section side>
                                  <div class="assignee-chip">
                                    <q-avatar v-if="sub.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                                      {{ sub.assigneeName.charAt(0).toUpperCase() }}
                                    </q-avatar>
                                    <span class="text-caption" :class="sub.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                                      {{ sub.assigneeName ?? '미배정' }}
                                    </span>
                                  </div>
                                </q-item-section>
                              </q-item>
                            </div>
                          </template>
                        </draggable>
                      </template>
                    </div>
                  </template>
                </draggable>
              </template>
            </div>
          </template>
        </draggable>

        <!-- ── 에픽 없음 섹션 ── -->
        <template v-if="hasVisibleOrphans">
          <div
            v-if="hasVisibleEpics"
            class="bg-grey-2 q-px-md"
            style="height: 30px; display: flex; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.12)"
          >
            <span class="text-caption text-grey-6 text-weight-medium">에픽 없음</span>
          </div>

          <draggable
            v-model="orderedOrphans"
            item-key="id"
            handle=".drag-handle-main"
            :animation="150"
            ghost-class="drag-ghost"
            :disabled="hasFilter"
            @end="saveOrder"
          >
            <template #item="{ element: main }">
              <div v-show="isMainVisible(main)">
                <q-item clickable @click="openDetail(main)" class="tree-item">
                  <q-item-section class="tree-section-toggle">
                    <div class="row no-wrap items-center">
                      <q-icon
                        name="drag_indicator"
                        class="drag-handle-main drag-handle-icon"
                        :class="{ 'drag-active': !hasFilter }"
                        size="16px"
                        @click.stop
                      />
                      <q-btn
                        v-if="_subsByMain(main.id).length > 0"
                        flat dense round size="xs"
                        :icon="collapsed.has(main.id) ? 'chevron_right' : 'expand_more'"
                        @click.stop="toggleCollapse(main.id)"
                      />
                      <div v-else style="width: 24px" />
                    </div>
                  </q-item-section>
                  <q-item-section class="tree-section-icon">
                    <q-icon :name="_typeIcon(main.type)" :color="_typeColor(main.type)" size="18px" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>
                      <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ main.number }}</span>
                      {{ main.title }}
                    </q-item-label>
                    <q-item-label caption class="q-mt-xs">
                      <q-badge :color="_statusClr(main.status)" :label="_statusLbl(main.status)" class="q-mr-xs" />
                      <q-icon :name="_prioIcon(main.priority)" :color="_prioClr(main.priority)" size="xs" />
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="assignee-chip">
                      <q-avatar v-if="main.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                        {{ main.assigneeName.charAt(0).toUpperCase() }}
                      </q-avatar>
                      <span class="text-caption" :class="main.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                        {{ main.assigneeName ?? '미배정' }}
                      </span>
                    </div>
                  </q-item-section>
                </q-item>

                <!-- 서브태스크 (indent 1 = 28px, 드래그 가능) -->
                <template v-if="!collapsed.has(main.id)">
                  <draggable
                    :model-value="_subsByMain(main.id)"
                    @update:model-value="(v: Issue[]) => { orderedSubsByMain[String(main.id)] = v }"
                    item-key="id"
                    handle=".drag-handle-sub"
                    :animation="150"
                    ghost-class="drag-ghost"
                    :disabled="hasFilter"
                    @end="saveOrder"
                  >
                    <template #item="{ element: sub }">
                      <div v-show="!hasFilter || matches(sub)">
                        <q-item clickable @click="openDetail(sub)" class="tree-item" style="padding-left: 28px">
                          <q-item-section class="tree-section-toggle">
                            <div class="row no-wrap items-center">
                              <q-icon
                                name="drag_indicator"
                                class="drag-handle-sub drag-handle-icon"
                                :class="{ 'drag-active': !hasFilter }"
                                size="16px"
                                @click.stop
                              />
                              <div style="width: 24px" />
                            </div>
                          </q-item-section>
                          <q-item-section class="tree-section-icon">
                            <q-icon :name="_typeIcon(sub.type)" :color="_typeColor(sub.type)" size="18px" />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label>
                              <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ sub.number }}</span>
                              {{ sub.title }}
                            </q-item-label>
                            <q-item-label caption class="q-mt-xs">
                              <q-badge :color="_statusClr(sub.status)" :label="_statusLbl(sub.status)" class="q-mr-xs" />
                              <q-icon :name="_prioIcon(sub.priority)" :color="_prioClr(sub.priority)" size="xs" />
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <div class="assignee-chip">
                              <q-avatar v-if="sub.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                                {{ sub.assigneeName.charAt(0).toUpperCase() }}
                              </q-avatar>
                              <span class="text-caption" :class="sub.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                                {{ sub.assigneeName ?? '미배정' }}
                              </span>
                            </div>
                          </q-item-section>
                        </q-item>
                      </div>
                    </template>
                  </draggable>
                </template>
              </div>
            </template>
          </draggable>

          <!-- 부모 없는 서브태스크 -->
          <div v-for="sub in orphanSubs" :key="sub.id" v-show="!hasFilter || matches(sub)">
            <q-item clickable @click="openDetail(sub)" class="tree-item">
              <q-item-section class="tree-section-toggle"><div style="width: 40px" /></q-item-section>
              <q-item-section class="tree-section-icon">
                <q-icon :name="_typeIcon(sub.type)" :color="_typeColor(sub.type)" size="18px" />
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  <span class="text-grey-5 text-caption q-mr-xs">{{ project?.key }}-{{ sub.number }}</span>
                  {{ sub.title }}
                </q-item-label>
                <q-item-label caption class="q-mt-xs">
                  <q-badge :color="_statusClr(sub.status)" :label="_statusLbl(sub.status)" class="q-mr-xs" />
                  <q-icon :name="_prioIcon(sub.priority)" :color="_prioClr(sub.priority)" size="xs" />
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="assignee-chip">
                  <q-avatar v-if="sub.assigneeName" size="22px" color="teal" text-color="white" font-size="10px" class="q-mr-xs">
                    {{ sub.assigneeName.charAt(0).toUpperCase() }}
                  </q-avatar>
                  <span class="text-caption" :class="sub.assigneeName ? 'text-grey-7' : 'text-grey-5'">
                    {{ sub.assigneeName ?? '미배정' }}
                  </span>
                </div>
              </q-item-section>
            </q-item>
          </div>
        </template>
      </div>
    </q-card>

    <IssueFormDialog
      v-model="createDialog.open"
      :project-id="projectId"
      @created="onIssueCreated"
    />

    <IssueDetailDialog
      v-model="detailDialog.open"
      :project-id="projectId"
      :project-key="project?.key ?? ''"
      :issue="detailDialog.issue"
      @updated="onIssueUpdated"
      @deleted="onIssueDeleted"
      @update:model-value="!$event && loadIssues()"
    />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify } from 'quasar'
import draggable from 'vuedraggable'
import {
  listIssues,
  ISSUE_STATUSES, STATUS_LABEL, STATUS_COLOR,
  TYPE_ICON, TYPE_COLOR, PRIORITY_ICON, PRIORITY_COLOR, PRIORITY_LABEL,
  type Issue, type IssueStatus, type IssuePriority, type IssueType,
} from 'src/services/pm/issue'
import { getProject, listProjectMembers, type Project, type ProjectMember } from 'src/services/pm/project'
import IssueFormDialog from './components/IssueFormDialog.vue'
import IssueDetailDialog from './components/IssueDetailDialog.vue'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const projectId = route.params.projectId as string

const project  = ref<Project | null>(null)
const allIssues = ref<Issue[]>([])
const members  = ref<ProjectMember[]>([])
const loading  = ref(false)

const collapsed = ref(new Set<string>())
const createDialog = ref({ open: false })
const detailDialog = ref({ open: false, issue: null as Issue | null })

// ── 필터 ──────────────────────────────────────────────────────────────
const filterSearch    = ref('')
const filterStatus    = ref<IssueStatus | null>(null)
const filterPriority  = ref<IssuePriority | null>(null)
const filterType      = ref<IssueType | null>(null)
const filterAssigneeId = ref<string | null>(null)
const filterDateFrom  = ref<string | null>(null)
const filterDateTo    = ref<string | null>(null)

const FILTER_KEY = `backlog_filter_${projectId}`

function saveFilters() {
  localStorage.setItem(FILTER_KEY, JSON.stringify({
    search: filterSearch.value, status: filterStatus.value,
    priority: filterPriority.value, type: filterType.value, assigneeId: filterAssigneeId.value,
    dateFrom: filterDateFrom.value, dateTo: filterDateTo.value,
  }))
}

function restoreFilters() {
  try {
    const raw = localStorage.getItem(FILTER_KEY)
    if (!raw) return
    const s = JSON.parse(raw) as { search: string; status: IssueStatus | null; priority: IssuePriority | null; type: IssueType | null; assigneeId: string | null; dateFrom: string | null; dateTo: string | null }
    filterSearch.value = s.search ?? ''; filterStatus.value = s.status ?? null
    filterPriority.value = s.priority ?? null; filterType.value = s.type ?? null
    filterAssigneeId.value = s.assigneeId ?? null
    filterDateFrom.value = s.dateFrom ?? null; filterDateTo.value = s.dateTo ?? null
  } catch { /* ignore */ }
}

watch([filterSearch, filterStatus, filterPriority, filterType, filterAssigneeId, filterDateFrom, filterDateTo], saveFilters)

const hasFilter = computed(() =>
  !!(filterSearch.value || filterStatus.value || filterPriority.value || filterType.value || filterAssigneeId.value || filterDateFrom.value || filterDateTo.value)
)

function clearFilters() {
  filterSearch.value = ''; filterStatus.value = null
  filterPriority.value = null; filterType.value = null; filterAssigneeId.value = null
  filterDateFrom.value = null; filterDateTo.value = null
}

// ── 드래그 순서 관리 ──────────────────────────────────────────────────
const orderedEpics      = ref<Issue[]>([])
const orderedMainsByEpic = reactive<Record<string, Issue[]>>({})
const orderedOrphans    = ref<Issue[]>([])
const orderedSubsByMain  = reactive<Record<string, Issue[]>>({})
const orphanSubs        = ref<Issue[]>([])

const ORDER_KEY = `backlog_order_${projectId}`

type SavedOrder = {
  epics: string[]
  mainsByEpic: Record<string, string[]>
  orphans: string[]
  subsByMain: Record<string, string[]>
}

function loadOrder(): SavedOrder | null {
  try { return JSON.parse(localStorage.getItem(ORDER_KEY) ?? 'null') as SavedOrder | null }
  catch { return null }
}

function saveOrder() {
  const order: SavedOrder = {
    epics: orderedEpics.value.map(e => e.id),
    mainsByEpic: Object.fromEntries(Object.entries(orderedMainsByEpic).map(([k, v]) => [k, v.map(i => i.id)])),
    orphans: orderedOrphans.value.map(i => i.id),
    subsByMain: Object.fromEntries(Object.entries(orderedSubsByMain).map(([k, v]) => [k, v.map(i => i.id)])),
  }
  localStorage.setItem(ORDER_KEY, JSON.stringify(order))
}

function sortByIds<T extends { id: string }>(items: T[], ids?: string[]): T[] {
  if (!ids?.length) return items
  const idx = new Map(ids.map((id, i) => [id, i]))
  return [...items].sort((a, b) => (idx.get(a.id) ?? 9999) - (idx.get(b.id) ?? 9999))
}

function applyOrder(issues: Issue[]) {
  const saved = loadOrder()
  const epics   = issues.filter(i => i.type === 'EPIC')
  const epicIds = new Set(epics.map(e => e.id))
  const mains   = issues.filter(i => i.type !== 'EPIC' && i.type !== 'SUB_TASK')
  const mainIds = new Set(mains.map(m => m.id))
  const subs    = issues.filter(i => i.type === 'SUB_TASK')

  orderedEpics.value = sortByIds(epics, saved?.epics)

  const mainsByEpicTmp: Record<string, Issue[]> = {}
  const orphanList: Issue[] = []
  for (const m of mains) {
    const eid = m.epicId && epicIds.has(m.epicId) ? m.epicId : null
    if (eid) (mainsByEpicTmp[eid] ??= []).push(m)
    else orphanList.push(m)
  }
  for (const k of Object.keys(orderedMainsByEpic)) delete orderedMainsByEpic[k]
  for (const epic of epics) {
    orderedMainsByEpic[epic.id] = sortByIds(mainsByEpicTmp[epic.id] ?? [], saved?.mainsByEpic?.[epic.id])
  }
  orderedOrphans.value = sortByIds(orphanList, saved?.orphans)

  const subsByMainTmp: Record<string, Issue[]> = {}
  for (const s of subs) {
    if (s.parentIssueId && mainIds.has(s.parentIssueId))
      (subsByMainTmp[s.parentIssueId] ??= []).push(s)
  }
  for (const k of Object.keys(orderedSubsByMain)) delete orderedSubsByMain[k]
  for (const [mid, items] of Object.entries(subsByMainTmp)) {
    orderedSubsByMain[mid] = sortByIds(items, saved?.subsByMain?.[mid])
  }
  orphanSubs.value = subs.filter(s => !s.parentIssueId || !mainIds.has(s.parentIssueId))
}

watch(allIssues, (issues) => applyOrder(issues))

// ── 필터 적용 ─────────────────────────────────────────────────────────
function matches(issue: Issue): boolean {
  const q = filterSearch.value.toLowerCase()
  if (q && !issue.title.toLowerCase().includes(q)) return false
  if (filterStatus.value     && issue.status     !== filterStatus.value)     return false
  if (filterPriority.value   && issue.priority   !== filterPriority.value)   return false
  if (filterType.value       && issue.type       !== filterType.value)       return false
  if (filterAssigneeId.value && issue.assigneeId !== filterAssigneeId.value) return false
  if (filterDateFrom.value   && (!issue.dueDate  || issue.dueDate < filterDateFrom.value)) return false
  if (filterDateTo.value     && (!issue.dueDate  || issue.dueDate > filterDateTo.value))   return false
  return true
}

function visibleSubsForMain(mainId: string): Issue[] {
  const subs = orderedSubsByMain[mainId] ?? []
  return hasFilter.value ? subs.filter(matches) : subs
}

function isMainVisible(main: Issue): boolean {
  if (!hasFilter.value) return true
  return matches(main) || (orderedSubsByMain[main.id] ?? []).some(matches)
}

function isEpicVisible(epic: Issue): boolean {
  if (!hasFilter.value) return true
  return matches(epic) || (orderedMainsByEpic[epic.id] ?? []).some(isMainVisible)
}

const hasVisibleEpics   = computed(() => orderedEpics.value.some(isEpicVisible))
const hasVisibleOrphans = computed(() =>
  orderedOrphans.value.some(isMainVisible) || orphanSubs.value.some(s => !hasFilter.value || matches(s))
)

const filteredCount = computed(() => {
  let n = 0
  for (const epic of orderedEpics.value) {
    if (!isEpicVisible(epic)) continue
    n++
    for (const main of orderedMainsByEpic[epic.id] ?? []) {
      if (!isMainVisible(main)) continue
      n++
      n += visibleSubsForMain(main.id).length
    }
  }
  for (const main of orderedOrphans.value) {
    if (!isMainVisible(main)) continue
    n++
    n += visibleSubsForMain(main.id).length
  }
  n += orphanSubs.value.filter(s => !hasFilter.value || matches(s)).length
  return n
})

// ── 접기/펼치기 ───────────────────────────────────────────────────────
function toggleCollapse(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function expandAll() { collapsed.value = new Set() }

function collapseAll() {
  const next = new Set<string>()
  for (const epic of orderedEpics.value) {
    if ((orderedMainsByEpic[epic.id]?.length ?? 0) > 0) next.add(epic.id)
    for (const main of orderedMainsByEpic[epic.id] ?? []) {
      if ((orderedSubsByMain[main.id]?.length ?? 0) > 0) next.add(main.id)
    }
  }
  for (const main of orderedOrphans.value) {
    if ((orderedSubsByMain[main.id]?.length ?? 0) > 0) next.add(main.id)
  }
  collapsed.value = next
}

// vuedraggable 슬롯 요소가 any로 추론되므로 타입 안전한 헬퍼 사용
const _typeIcon  = (t: unknown) => TYPE_ICON[t as IssueType]
const _typeColor = (t: unknown) => TYPE_COLOR[t as IssueType]
const _statusLbl = (s: unknown) => STATUS_LABEL[s as IssueStatus]
const _statusClr = (s: unknown) => STATUS_COLOR[s as IssueStatus]
const _prioIcon  = (p: unknown) => PRIORITY_ICON[p as IssuePriority]
const _prioClr   = (p: unknown) => PRIORITY_COLOR[p as IssuePriority]
const _epicMains = (epicId: unknown): Issue[] => orderedMainsByEpic[String(epicId)] ?? []
const _subsByMain = (mainId: unknown): Issue[] => orderedSubsByMain[String(mainId)] ?? []

// ── 옵션 목록 ─────────────────────────────────────────────────────────
const TYPE_LABEL: Record<IssueType, string> = {
  EPIC: 'Epic', STORY: 'Story', TASK: 'Task', BUG: 'Bug', SUB_TASK: 'Sub-task',
}

const statusOptions   = ISSUE_STATUSES.map(s => ({ label: STATUS_LABEL[s], value: s }))
const priorityOptions = [
  { label: '최고', value: 'HIGHEST' as IssuePriority }, { label: '높음', value: 'HIGH' as IssuePriority },
  { label: '보통', value: 'MEDIUM' as IssuePriority  }, { label: '낮음', value: 'LOW' as IssuePriority  },
  { label: '최저', value: 'LOWEST' as IssuePriority  },
]
const typeOptions = [
  { label: 'Epic',     value: 'EPIC'     as IssueType }, { label: 'Story', value: 'STORY'    as IssueType },
  { label: 'Task',     value: 'TASK'     as IssueType }, { label: 'Bug',   value: 'BUG'      as IssueType },
  { label: 'Sub-task', value: 'SUB_TASK' as IssueType },
]

const memberOptions = computed(() =>
  members.value.map(m => ({ label: m.userName || m.userEmail, value: m.userId }))
)

// ── 데이터 로드 ───────────────────────────────────────────────────────
async function loadIssues() {
  loading.value = true
  try {
    allIssues.value = await listIssues(projectId)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '이슈 로드 실패') })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  restoreFilters()
  loading.value = true
  try {
    const [proj, issues, mems] = await Promise.all([
      getProject(projectId),
      listIssues(projectId),
      listProjectMembers(projectId),
    ])
    project.value  = proj
    allIssues.value = issues
    members.value  = mems
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function openDetail(issue: Issue) { detailDialog.value = { open: true, issue } }

function onIssueCreated(issue: Issue) {
  allIssues.value = [...allIssues.value, issue]
}

function onIssueUpdated() { void loadIssues() }

function onIssueDeleted(issueId: string) {
  allIssues.value = allIssues.value.filter(i => i.id !== issueId)
}
</script>

<style scoped>
/* ── 필터 카드 ── */
.filter-card { border-radius: 8px; }
.filter-search-input :deep(.q-field__control) { border-radius: 6px; }
.filter-chip { cursor: pointer; font-size: 12px; transition: opacity 0.15s; }
.filter-chip:hover { opacity: 0.82; }
.filter-clear-btn { font-size: 12px; border-radius: 14px; }

/* ── 트리 행 ── */
.backlog-tree { overflow: hidden; }
.tree-item {
  min-height: 48px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
.epic-row { background: #f3f0ff; }
.epic-row:hover { background: #e9e3ff; }
.tree-section-toggle {
  min-width: 40px;
  max-width: 40px;
  padding: 0;
  flex: 0 0 40px;
}
.tree-section-icon {
  min-width: 28px;
  max-width: 28px;
  padding: 0;
  flex: 0 0 28px;
}
.assignee-chip { display: flex; align-items: center; white-space: nowrap; }

/* ── 드래그 핸들 ── */
.drag-handle-icon {
  opacity: 0;
  transition: opacity 0.15s;
}
.tree-item:hover .drag-handle-icon.drag-active {
  opacity: 1;
  cursor: grab;
}
.drag-ghost {
  opacity: 0.5;
  background: #e8e8fb;
}
</style>
