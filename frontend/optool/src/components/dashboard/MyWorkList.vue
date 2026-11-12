<template>
  <div class="my-work-list" :aria-busy="loading">
    <div v-if="errors.length" class="my-work-notice" role="status">
      <span>{{ errors.join(' · ') }} 목록을 불러오지 못했습니다.</span>
      <q-btn flat dense no-caps color="primary" label="다시 불러오기" :loading="loading" @click="$emit('retry')" />
    </div>
    <div v-if="loading" class="my-work-empty" role="status">내 일감을 불러오는 중입니다.</div>
    <div v-if="items.length" class="my-work-summary" aria-label="내 일감 현황">
      <span>{{ loading || errors.length ? '불러온' : '전체' }} <strong>{{ items.length }}</strong>건</span>
      <span v-if="overdueCount" class="my-work-overdue-count">지연 <strong>{{ overdueCount }}</strong>건</span>
      <span v-if="todayCount" class="my-work-today-count">오늘 마감 <strong>{{ todayCount }}</strong>건</span>
      <span class="my-work-sort">지연 · 마감일순</span>
    </div>
    <p v-if="!loading && !errors.length && !items.length" class="my-work-empty">담당 중인 미완료 일감이 없습니다.</p>
    <ul v-if="items.length" class="my-work-rows">
      <li v-for="item in items" :key="item.id">
        <button type="button" class="my-work-row" :class="`my-work-row--${item.urgency}`" @click="$emit('open', item)">
          <span class="my-work-copy">
            <span class="my-work-reference"><span class="my-work-key">{{ item.key }}</span><span class="my-work-context">{{ item.context }}</span></span>
            <span class="my-work-title">{{ item.title }}</span>
          </span>
          <span class="my-work-deadline">
            <span class="my-work-deadline-label">
              <q-icon v-if="item.urgency === 'overdue'" name="error_outline" size="16px" aria-hidden="true" />
              <q-icon v-else-if="item.urgency === 'today'" name="schedule" size="16px" aria-hidden="true" />
              {{ item.deadlineLabel }}
            </span>
            <time v-if="item.dueDate" :datetime="item.dueDate" class="my-work-due-date">마감 {{ item.dueDate.replaceAll('-', '.') }}</time>
          </span>
          <span class="my-work-status">{{ item.kind === 'issue' ? STATUS_LABEL[item.issue.status] : SR_STATUS_LABEL[item.sr.status] }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STATUS_LABEL } from 'src/services/pm/issue'
import { SR_STATUS_LABEL } from 'src/services/sr'
import type { MyWorkItem } from 'src/utils/myWork'

const props = defineProps<{ items: MyWorkItem[]; loading: boolean; errors: string[] }>()
defineEmits<{ open: [item: MyWorkItem]; retry: [] }>()
const overdueCount = computed(() => props.items.filter(item => item.urgency === 'overdue').length)
const todayCount = computed(() => props.items.filter(item => item.urgency === 'today').length)
</script>

<style scoped>
.my-work-list { container-type: inline-size; }
.my-work-summary { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 16px; position: sticky; top: 0; z-index: 1; padding: 4px 0 10px; background: var(--bo-surface); color: var(--bo-muted); font-size: 12px; line-height: 1.5; }
.my-work-summary strong { font-weight: 600; }
.my-work-overdue-count { color: #b42318; }
.my-work-today-count { color: #93370d; }
.my-work-sort { margin-left: auto; }
.my-work-rows { margin: 0; padding: 0; list-style: none; }
.my-work-row { display: grid; grid-template-columns: minmax(0, 1fr) 130px 76px; align-items: center; gap: 16px; width: 100%; padding: 12px; border: 0; border-bottom: 1px solid var(--bo-border); background: transparent; color: var(--bo-text); font: inherit; text-align: left; cursor: pointer; }
.my-work-row--overdue { background: #fff4f2; }
.my-work-row:hover { background: var(--bo-accent-soft); }
.my-work-row:focus-visible { outline: 2px solid var(--bo-accent-ink); outline-offset: -2px; }
.my-work-copy { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.my-work-reference { display: flex; flex-wrap: wrap; gap: 4px 10px; font-size: 12px; line-height: 1.5; }
.my-work-key { color: var(--bo-accent-ink); font-weight: 600; }
.my-work-context { color: var(--bo-muted); overflow-wrap: anywhere; }
.my-work-title { font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.my-work-deadline { display: flex; flex-direction: column; gap: 4px; color: var(--bo-muted); font-size: 12px; line-height: 1.5; font-variant-numeric: tabular-nums; }
.my-work-deadline-label { display: flex; align-items: center; gap: 4px; }
.my-work-row--overdue .my-work-deadline-label { color: #b42318; font-weight: 600; }
.my-work-row--today .my-work-deadline-label { color: #93370d; font-weight: 600; }
.my-work-status { color: var(--bo-secondary); font-size: 12px; line-height: 1.5; text-align: right; }
.my-work-empty { margin: 0; padding: 20px 12px; color: var(--bo-muted); font-size: 13px; text-align: center; }
.my-work-notice { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; color: var(--bo-muted); font-size: 12px; line-height: 1.5; }
@container (max-width: 480px) {
  .my-work-row { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; padding: 12px 8px; }
  .my-work-copy { grid-column: 1 / -1; }
  .my-work-deadline { flex-direction: row; flex-wrap: wrap; gap: 4px 10px; }
  .my-work-sort { width: 100%; margin-left: 0; }
}
</style>
