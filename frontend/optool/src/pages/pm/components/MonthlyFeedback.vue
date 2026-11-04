<template>
  <q-card id="monthly-feedback" flat class="feedback-workspace" :class="`feedback-workspace--${view}`">
    <header class="feedback-header">
      <div>
        <div class="feedback-eyebrow">{{ currentMonth }} 보고서 · 데이터운영팀</div>
        <h2>피드백 메모</h2>
        <p>{{ period === 'current' ? `${currentMonth} 메모 등록 → 담당자 작성 → ${nextMonth} 주요 안건 반영` : `${previousMonth}에 받은 코멘트의 후속 내용을 작성해 ${currentMonth} 보고에 반영하세요.` }}</p>
      </div>
      <div class="feedback-header-actions">
        <q-btn unelevated color="primary" icon="add" :label="`${report.reportMonth}월 피드백 남기기`" no-caps :disable="busy || loading" @click="openCreate" />
        <q-btn flat round icon="close" aria-label="피드백 메모 닫기" :disable="busy" @click="requestClose" />
      </div>
    </header>

    <nav class="feedback-periods" aria-label="피드백을 받은 월 선택">
      <button type="button" :class="{ active: period === 'current' }" :aria-pressed="period === 'current'" :disabled="busy || loading" @click="changePeriod('current')">
        <span class="feedback-period-title"><q-icon name="edit_note" /><strong>{{ currentMonth }} 피드백 메모</strong><span>{{ currentItems.length }}</span></span>
        <small>이번 달에 받은 코멘트 → {{ nextMonth }} 주요 안건</small>
      </button>
      <button type="button" :class="{ active: period === 'previous' }" :aria-pressed="period === 'previous'" :disabled="busy || loading" @click="changePeriod('previous')">
        <span class="feedback-period-title"><q-icon name="assignment" /><strong>{{ previousMonth }} 피드백 후속 작성</strong><span>{{ previousItems.length }}</span></span>
        <small>지난달에 받은 코멘트 → {{ currentMonth }} 주요 안건</small>
      </button>
    </nav>

    <div v-if="loading" class="feedback-loading" role="status"><q-spinner color="primary" size="28px" /><span>메모를 불러오는 중입니다.</span></div>
    <div v-else-if="loadError" class="feedback-empty" role="alert">
      <q-icon name="error_outline" size="36px" /><h3>메모를 불러오지 못했습니다.</h3><p>{{ loadError }}</p>
      <q-btn outline color="primary" label="다시 불러오기" no-caps @click="load" />
    </div>
    <div v-else class="feedback-body">
      <aside class="feedback-sidebar" aria-label="피드백 메모 목록">
        <div class="feedback-list-heading"><strong>{{ period === 'current' ? '이번 달 피드백 메모' : '지난달에서 넘어온 작성 요청' }}</strong><span>{{ periodItems.length }}건</span></div>
        <div class="feedback-filters" aria-label="메모 필터">
          <button v-for="option in filters" :key="option.value" type="button" :aria-pressed="filter === option.value"
            :class="{ active: filter === option.value }" :disabled="busy" @click="changeFilter(option.value)">
            {{ option.label }} <span>{{ option.count }}</span>
          </button>
        </div>
        <div v-if="!visibleItems.length" class="feedback-list-empty">
          <q-icon name="sticky_note_2" size="28px" />
          <p>{{ filter === 'mine' ? '내가 작성할 메모가 없습니다.' : filter === 'requested' ? '내가 요청한 메모가 없습니다.' : period === 'current' ? `${currentMonth}에 등록한 메모가 없습니다.` : `${previousMonth}에서 넘어온 작성 요청이 없습니다.` }}</p>
          <q-btn v-if="filter !== 'all'" flat color="primary" label="전체 메모 보기" no-caps @click="changeFilter('all')" />
        </div>
        <div v-else class="feedback-list">
          <button v-for="item in visibleItems" :key="item.id" type="button" class="feedback-list-item"
            :class="{ selected: selectedId === item.id && view !== 'create' }" :aria-pressed="selectedId === item.id && view !== 'create'"
            :disabled="busy" @click="selectItem(item)">
            <div class="feedback-item-top"><span :class="['feedback-status', `feedback-status--${item.status.toLowerCase()}`]">{{ statusLabel[item.status] }}</span><span v-if="needsMyAction(item)" class="feedback-mine">내 할 일</span></div>
            <strong>{{ item.title }}</strong>
            <div class="feedback-item-meta">{{ item.assigneeName }} 작성 <span v-if="item.dueDate">· {{ item.dueDate }}까지</span></div>
            <div class="feedback-item-target"><q-icon name="subdirectory_arrow_right" /> {{ targetMonth(item) }} 주요 안건</div>
          </button>
        </div>
      </aside>

      <main ref="detailPanel" class="feedback-detail" aria-label="메모 내용">
        <q-btn v-if="view !== 'list'" class="feedback-mobile-back" flat dense icon="arrow_back" label="메모 목록" no-caps :disable="busy" @click="backToList" />
        <template v-if="view === 'create'">
          <div class="feedback-detail-heading"><div class="feedback-eyebrow">{{ currentMonth }}에 받은 피드백</div><h3>코멘트를 남기고 담당자를 지정하세요.</h3><p>담당자에게 작성 요청을 보내고, 작성 완료한 내용을 {{ nextMonth }} 주요 안건에 반영합니다.</p></div>
          <q-form class="feedback-create-form" @submit="submitCreate">
            <div class="feedback-detail-scroll" :class="{ 'feedback-saving': saving }">
              <section class="feedback-form-section">
                <q-input v-model="form.title" outlined label="안건 제목 *" placeholder="예: 백업 체계 개선 현황" maxlength="300" :disable="saving"
                  hint="담당자의 답변이 반영될 때 주요 안건 제목으로 사용됩니다." :rules="[v => !!v?.trim() || '안건 제목을 입력해 주세요.']" lazy-rules />
                <div v-if="assigneeError" class="feedback-field-error" role="alert">{{ assigneeError }} <q-btn flat dense label="다시 불러오기" @click="loadAssignees" /></div>
                <div class="feedback-assignment">
                  <q-select v-model="form.assignee_id" :options="users" option-label="label" option-value="value" emit-value map-options outlined label="작성 담당자 *"
                    :loading="loadingAssignees" :disable="saving || loadingAssignees" :rules="[v => !!v || '담당자를 선택해 주세요.']" lazy-rules>
                    <template #no-option><q-item><q-item-section>작성 권한이 있는 담당자가 없습니다.</q-item-section></q-item></template>
                  </q-select>
                  <q-input v-model="form.due_date" type="date" label="작성 기한 (선택)" outlined stack-label :disable="saving" />
                </div>
              </section>
              <section class="feedback-form-section">
                <MarkdownEditor v-model="form.comment" label="팀장님 코멘트" required :rows="4"
                  placeholder="예: 백업 실패 원인과 개선 진행 상황을 다음 달 보고에 정리해 주세요."
                  @uploading="uploading = $event" />
                <p v-if="commentError" class="feedback-field-error" role="alert">{{ commentError }}</p>
                <div class="feedback-private-note"><q-icon name="sticky_note_2" /> 이 코멘트는 메모에만 남고, 보고서에는 담당자가 작성한 내용이 들어갑니다.</div>
              </section>
              <div class="feedback-destination"><q-icon name="event_note" size="22px" /><div><small>작성 완료 시 반영 위치</small><strong>{{ nextMonth }} 월간보고 · 주요 안건</strong></div></div>
            </div>
            <footer class="feedback-footer">
              <q-btn flat label="돌아가기" no-caps :disable="busy" @click="leaveCreate" />
              <q-btn unelevated color="primary" icon="send" label="메모 등록하고 요청 보내기" no-caps type="submit" :loading="saving" :disable="uploading || loadingAssignees || !!assigneeError" />
            </footer>
          </q-form>
        </template>

        <template v-else-if="selected">
          <div class="feedback-detail-heading">
            <div class="feedback-eyebrow feedback-origin">{{ sourceMonth(selected) }} 피드백 <q-icon name="arrow_forward" /> {{ targetMonth(selected) }} 보고</div>
            <div class="feedback-detail-title"><span :class="['feedback-status', `feedback-status--${selected.status.toLowerCase()}`]">{{ statusLabel[selected.status] }}</span>
              <q-btn v-if="canCancel(selected)" flat round dense icon="more_horiz" aria-label="메모 관리" :disable="busy"><q-menu><q-list><q-item clickable v-close-popup @click="cancel(selected)"><q-item-section class="text-negative">작성 요청 취소</q-item-section></q-item></q-list></q-menu></q-btn>
            </div>
            <h3>{{ selected.title }}</h3>
            <p>{{ selected.requesterName }} 요청 <q-icon name="arrow_forward" /> {{ selected.assigneeName }} 작성<template v-if="selected.dueDate"> · {{ selected.dueDate }}까지</template></p>
          </div>
          <div class="feedback-detail-scroll" :class="{ 'feedback-saving': saving }">
            <div class="feedback-destination" :class="{ 'feedback-destination--done': selected.status === 'APPLIED' }">
              <q-icon :name="selected.status === 'APPLIED' ? 'check_circle' : 'event_note'" size="24px" />
              <div><small>{{ selected.status === 'APPLIED' ? '주요 안건에 반영 완료' : '작성 완료 시 반영 위치' }}</small><strong>{{ targetMonth(selected) }} 월간보고 · 주요 안건</strong></div>
              <q-btn v-if="selected.status === 'APPLIED'" flat dense icon="arrow_outward" label="보고서 보기" no-caps @click="openReport(selected)" />
            </div>
            <section class="feedback-memo">
              <div class="feedback-section-label"><q-icon name="sticky_note_2" /><h4>팀장님 코멘트</h4><span>메모 전용</span></div>
              <WorkResultContent :content="selected.comment" />
            </section>
            <div v-if="selected.reviewNote" class="feedback-notice">보완 요청: {{ selected.reviewNote }}</div>
            <section class="feedback-response">
              <div class="feedback-section-label"><q-icon name="description" /><h4>보고서에 들어갈 내용</h4></div>
              <template v-if="canWrite(selected)">
                <p v-if="writingAsAdmin" class="feedback-notice">담당자를 대신해 작성 중입니다. 작성 완료하면 {{ targetMonth(selected) }} 주요 안건에 바로 반영됩니다.</p>
                <p class="feedback-help">코멘트에 대한 진행 상황이나 결과를 작성하세요. 아래 내용이 주요 안건의 본문으로 들어갑니다.</p>
                <MarkdownEditor :key="selected.id" v-model="content" :rows="6" placeholder="진행한 내용, 결과와 후속 계획을 작성해 주세요." @uploading="uploading = $event" />
                <div v-if="targetLocked" class="feedback-notice">이 보고서는 이미 확정되었습니다. 임시 저장한 뒤 보고서의 확정을 해제해야 반영할 수 있습니다.</div>
              </template>
              <template v-else-if="selected.content"><WorkResultContent :content="selected.content" /><p v-if="selected.status !== 'APPLIED'" class="feedback-help">{{ selected.status === 'APPLYING' ? '내용은 저장되었습니다. 반영을 다시 시도하면 중복 없이 처리됩니다.' : selected.status === 'CANCELLED' ? '요청이 취소되어 보고서에 반영되지 않습니다.' : '임시 저장된 내용입니다. 작성 완료 후 보고서에 반영됩니다.' }}</p></template>
              <div v-else class="feedback-awaiting"><q-icon name="edit_note" size="28px" /><strong>{{ selected.status === 'CANCELLED' ? '취소된 작성 요청입니다.' : `${selected.assigneeName} 님의 작성을 기다리고 있습니다.` }}</strong><p v-if="selected.status !== 'CANCELLED'">담당자가 ‘작성 완료’를 누르면 {{ targetMonth(selected) }} 주요 안건에 자동으로 추가됩니다.</p></div>
            </section>
          </div>
          <footer class="feedback-footer" aria-live="polite">
            <template v-if="canWrite(selected)">
              <span class="feedback-save-hint">{{ dirty ? '저장하지 않은 변경사항' : selected.status === 'WRITING' ? '임시 저장된 내용' : '작성 완료하면 보고서에 반영됩니다.' }}</span>
              <div class="feedback-footer-actions"><q-btn outline color="primary" label="임시 저장" no-caps :disable="busy" @click="act(selected, 'save')" /><q-btn unelevated color="primary" icon="check" label="작성 완료 · 주요 안건에 추가" no-caps :loading="saving" :disable="uploading || !content.trim() || targetLocked" @click="act(selected, 'submit')" /></div>
            </template>
            <template v-else-if="canRetry(selected)"><span class="feedback-save-hint">작성한 내용이 보관되어 있습니다.</span><q-btn unelevated color="primary" icon="refresh" label="주요 안건 반영 다시 시도" no-caps :loading="saving" @click="act(selected, 'submit')" /></template>
            <template v-else><span class="feedback-save-hint">{{ selected.status === 'APPLIED' ? '팀장님 코멘트 원문은 보고서에 포함되지 않습니다.' : selected.status === 'CANCELLED' ? '이 메모는 보고서에 반영되지 않습니다.' : '담당자에게 작성 요청을 보냈습니다.' }}</span><q-btn v-if="canWriteForAssignee(selected)" outline color="primary" icon="edit_note" label="담당자 대신 작성" no-caps @click="writingAsAdmin = true" /><q-btn v-else flat color="primary" icon="arrow_outward" :label="`${targetMonth(selected)} 보고서 보기`" no-caps @click="openReport(selected)" /></template>
          </footer>
        </template>

        <div v-else class="feedback-empty">
          <div class="feedback-empty-icon"><q-icon name="edit_note" size="42px" /></div>
          <h3>{{ periodItems.length ? '확인할 메모를 선택하세요.' : period === 'current' ? `${currentMonth} 피드백을 남겨주세요.` : `${previousMonth}에서 넘어온 작성 요청이 없습니다.` }}</h3>
          <p v-if="period === 'current'">이번 달에 받은 팀장님 코멘트를 남기고 담당자를 지정하세요.<br />담당자의 답변은 {{ nextMonth }} 주요 안건에 반영됩니다.</p>
          <p v-else>지난달 피드백에 대한 답변을 작성하는 곳입니다.<br />이번 달에 새로 받은 코멘트는 ‘{{ currentMonth }} 피드백 메모’에 남겨주세요.</p>
          <q-btn v-if="!periodItems.length && period === 'current'" unelevated color="primary" icon="add" :label="`${report.reportMonth}월 피드백 남기기`" no-caps @click="openCreate" />
          <q-btn v-else-if="!periodItems.length" outline color="primary" :label="`${report.reportMonth}월 피드백 메모로 이동`" no-caps @click="changePeriod('current')" />
        </div>
      </main>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Dialog, Notify } from 'quasar'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'
import WorkResultContent from 'src/components/WorkResultContent.vue'
import { useAuthStore } from 'src/stores/auth'
import { createFeedback, feedbackAction, listFeedback, listFeedbackAssignees, type MonthlyFeedback } from 'src/services/pm/monthlyFeedback'
import type { MonthlyReport } from 'src/services/pm/reports'
import { getErrorMessage } from 'src/utils/http/error'

const props = defineProps<{ report: MonthlyReport }>()
const emit = defineEmits<{ changed: []; close: []; report: [id: string] }>()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
type Filter = 'all' | 'mine' | 'requested'
type Period = 'current' | 'previous'
const items = ref<MonthlyFeedback[]>([])
const period = ref<Period>('current')
const currentItems = computed(() => items.value.filter(item => item.sourceReportId === props.report.id))
const previousItems = computed(() => items.value.filter(item => item.targetReportId === props.report.id && item.sourceReportId !== props.report.id))
const periodItems = computed(() => period.value === 'current' ? currentItems.value : previousItems.value)
const selectedId = ref('')
const selected = computed(() => periodItems.value.find(item => item.id === selectedId.value))
const view = ref<'list' | 'detail' | 'create'>('list')
const filter = ref<Filter>('all')
const loading = ref(false), saving = ref(false), uploading = ref(false), loadingAssignees = ref(false)
const loadError = ref(''), assigneeError = ref(''), commentError = ref('')
const busy = computed(() => saving.value || uploading.value)
const users = ref<{ label: string; value: string }[]>([])
const blankForm = () => ({ title: '', comment: '', assignee_id: '', due_date: '' })
const form = ref(blankForm())
const content = ref('')
const writingAsAdmin = ref(false)
const detailPanel = ref<HTMLElement>()
const currentId = computed(() => String(auth.me?.id || ''))
const statusLabel: Record<MonthlyFeedback['status'], string> = { REQUESTED: '작성 대기', WRITING: '작성 중', SUBMITTED: '작성 완료 필요', APPLYING: '반영 확인 필요', APPLIED: '반영 완료', CANCELLED: '요청 취소' }
const currentMonth = computed(() => monthLabel(0))
const previousMonth = computed(() => monthLabel(-1))
const nextMonth = computed(() => monthLabel(1))
const targetLocked = computed(() => selected.value?.targetReportId === props.report.id && props.report.status === 'CONFIRMED')
const dirty = computed(() => view.value === 'create' ? Object.values(form.value).some(value => !!value) : !!selected.value && canWrite(selected.value) && content.value !== selected.value.content)
const filters = computed(() => [
  { value: 'all' as const, label: '전체', count: periodItems.value.length },
  { value: 'mine' as const, label: '내 할 일', count: periodItems.value.filter(needsMyAction).length },
  { value: 'requested' as const, label: '내가 요청', count: periodItems.value.filter(item => item.requesterId === currentId.value).length },
])
const visibleItems = computed(() => periodItems.value.filter(item => filter.value === 'mine' ? needsMyAction(item) : filter.value === 'requested' ? item.requesterId === currentId.value : true)
  .sort((a, b) => Number(isFinished(a)) - Number(isFinished(b))))
function monthLabel(offset: number) {
  const date = new Date(props.report.reportYear, props.report.reportMonth - 1 + offset, 1)
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월`
}
function targetMonth(item: MonthlyFeedback) { return item.targetReportId === props.report.id ? monthLabel(0) : nextMonth.value }
function sourceMonth(item: MonthlyFeedback) { return item.sourceReportId === props.report.id ? currentMonth.value : previousMonth.value }
function periodFor(item: MonthlyFeedback): Period { return item.sourceReportId === props.report.id ? 'current' : 'previous' }
function isFinished(item: MonthlyFeedback) { return ['APPLIED', 'CANCELLED'].includes(item.status) }
function needsMyAction(item: MonthlyFeedback) { return item.assigneeId === currentId.value && !isFinished(item) }
function canWrite(item: MonthlyFeedback) { return (item.assigneeId === currentId.value || (auth.me?.isAdmin && writingAsAdmin.value)) && ['REQUESTED', 'WRITING', 'SUBMITTED'].includes(item.status) }
function canWriteForAssignee(item: MonthlyFeedback) { return auth.me?.isAdmin && item.assigneeId !== currentId.value && ['REQUESTED', 'WRITING', 'SUBMITTED'].includes(item.status) }
function canRetry(item: MonthlyFeedback) { return (item.assigneeId === currentId.value || auth.me?.isAdmin) && item.status === 'APPLYING' }
function canCancel(item: MonthlyFeedback) { return (item.requesterId === currentId.value || auth.me?.isAdmin) && ['REQUESTED', 'WRITING', 'SUBMITTED'].includes(item.status) }
function confirmDiscard(): Promise<boolean> {
  if (busy.value) return Promise.resolve(false)
  if (!dirty.value) return Promise.resolve(true)
  return new Promise(resolve => {
    Dialog.create({ title: '저장하지 않은 내용이 있습니다', message: '화면을 이동하면 작성 중인 내용이 사라집니다.', ok: { label: '저장하지 않고 이동', color: 'negative' }, cancel: { label: '계속 작성', flat: true }, persistent: true })
      .onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false))
  })
}
function setSelected(item?: MonthlyFeedback, showDetail = true) {
  writingAsAdmin.value = false
  selectedId.value = item?.id || ''
  content.value = item?.content || ''
  view.value = item && showDetail ? 'detail' : 'list'
  void nextTick(() => { detailPanel.value?.querySelector('.feedback-detail-scroll')?.scrollTo({ top: 0 }) })
}
async function selectItem(item: MonthlyFeedback, resetFilter = false) {
  if (selectedId.value === item.id && view.value !== 'create') { if (resetFilter) filter.value = 'all'; view.value = 'detail'; return }
  if (await confirmDiscard()) {
    if (resetFilter || period.value !== periodFor(item)) filter.value = 'all'
    period.value = periodFor(item)
    setSelected(item)
  }
}
async function changePeriod(value: Period) {
  if (value === period.value || !await confirmDiscard()) return
  period.value = value
  filter.value = 'all'
  setSelected(periodItems.value.find(needsMyAction) || periodItems.value[0], false)
}
async function changeFilter(value: Filter) {
  if (value === filter.value || !await confirmDiscard()) return
  filter.value = value
  setSelected(visibleItems.value[0], false)
}
async function requestClose() { if (await confirmDiscard()) emit('close') }
async function backToList() { if (await confirmDiscard()) { content.value = selected.value?.content || ''; view.value = 'list' } }
async function leaveCreate() { if (await confirmDiscard()) setSelected(selected.value || visibleItems.value[0]) }
let loadVersion = 0
async function load() {
  const version = ++loadVersion
  loading.value = true
  loadError.value = ''
  try {
    const result = await listFeedback(props.report.id)
    if (version !== loadVersion) return
    items.value = result
    const linked = result.find(item => item.id === route.query.feedback)
    period.value = linked ? periodFor(linked) : 'current'
    setSelected(linked || periodItems.value.find(needsMyAction) || periodItems.value[0], !!linked)
  } catch (e) { if (version === loadVersion) loadError.value = getErrorMessage(e, '잠시 후 다시 시도해 주세요.') }
  finally { if (version === loadVersion) loading.value = false }
}
watch(() => props.report.id, () => { filter.value = 'all'; void load() }, { immediate: true })
watch(() => route.query.feedback, id => {
  const item = items.value.find(item => item.id === id)
  if (item) void selectItem(item, true)
})
async function loadAssignees() {
  loadingAssignees.value = true
  assigneeError.value = ''
  try { users.value = (await listFeedbackAssignees()).map(user => ({ label: user.name, value: user.id })) }
  catch (e) { assigneeError.value = getErrorMessage(e, '담당자를 불러오지 못했습니다.') }
  finally { loadingAssignees.value = false }
}
async function openCreate() {
  if (view.value === 'create' || !await confirmDiscard()) return
  form.value = blankForm()
  commentError.value = ''
  period.value = 'current'
  filter.value = 'all'
  view.value = 'create'
  await loadAssignees()
}
async function submitCreate() {
  if (busy.value) return
  commentError.value = !form.value.comment.trim() ? '팀장님 코멘트를 입력해 주세요.' : form.value.comment.trim().length > 5000 ? '코멘트는 5,000자 이내로 입력해 주세요.' : ''
  if (commentError.value || !form.value.title.trim() || !form.value.assignee_id) return
  saving.value = true
  try {
    const item = await createFeedback({ ...form.value, source_report_id: props.report.id })
    items.value.unshift(item)
    filter.value = 'all'
    form.value = blankForm()
    setSelected(item)
    emit('changed')
    Notify.create({ type: 'positive', message: `${item.assigneeName} 님에게 작성 요청을 보냈습니다.` })
  } catch (e) { Notify.create({ type: 'negative', message: getErrorMessage(e, '요청을 보내지 못했습니다. 입력한 내용은 유지됩니다.') }) }
  finally { saving.value = false }
}
async function act(item: MonthlyFeedback, action: 'save' | 'submit' | 'cancel') {
  if (busy.value) return
  saving.value = true
  try {
    const updated = await feedbackAction(item.id, action, item.status === 'APPLYING' ? item.content : content.value)
    items.value = items.value.map(existing => existing.id === updated.id ? updated : existing)
    content.value = updated.content
    // Keep the completed item visible so the result and report link remain clear.
    if (filter.value === 'mine' && isFinished(updated)) filter.value = 'all'
    emit('changed')
    Notify.create({ type: 'positive', message: action === 'submit' ? `${targetMonth(updated)} 주요 안건에 추가했습니다.` : action === 'save' ? '임시 저장했습니다. 아직 보고서에는 반영되지 않습니다.' : '작성 요청을 취소했습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '처리하지 못했습니다. 다시 시도해 주세요.') })
    // Reconcile interrupted submissions without discarding the user's draft.
    try {
      items.value = await listFeedback(props.report.id)
      if (selected.value && !canWrite(selected.value)) content.value = selected.value.content
    } catch { /* Keep the current list and draft when the network is unavailable. */ }
  } finally { saving.value = false }
}
function cancel(item: MonthlyFeedback) {
  Dialog.create({ title: '작성 요청 취소', message: `“${item.title}” 요청을 취소하시겠습니까? 작성 중인 내용은 보고서에 반영되지 않습니다.`, ok: { label: '요청 취소', color: 'negative' }, cancel: { label: '돌아가기', flat: true } })
    .onOk(() => { void act(item, 'cancel') })
}
async function openReport(item: MonthlyFeedback) {
  if (!await confirmDiscard()) return
  if (item.targetReportId === props.report.id) emit('report', item.targetReportId)
  else { emit('close'); await router.push(`/pm/monthly-report/${item.targetReportId}`) }
}
</script>

<style scoped>
.feedback-workspace { width: 1160px; max-width: 96vw; height: 88vh; height: 88dvh; max-height: 960px; display: flex; flex-direction: column; overflow: hidden; color: #233746; border-radius: 16px; background: #fff; }
.feedback-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 24px 28px 20px; }
.feedback-eyebrow { color: #687e8c; font-size: 12px; font-weight: 600; }
.feedback-header h2 { margin: 5px 0 6px; font-size: 24px; line-height: 1.4; font-weight: 750; letter-spacing: -.6px; }
.feedback-header p, .feedback-detail-heading p { margin: 0; color: #637786; font-size: 13px; line-height: 1.65; }
.feedback-header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.feedback-header-actions > .q-btn:first-child { border-radius: 8px; }
.feedback-periods { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px 28px; background: #f3f7f9; border-block: 1px solid #e3ebef; }
.feedback-periods button { min-width: 0; border: 1px solid #dce5eb; border-radius: 8px; background: #fff; padding: 12px 16px; font: inherit; color: #627784; cursor: pointer; text-align: left; }
.feedback-periods button.active { border-color: #4a8cac; color: #205c7c; background: #edf6fb; box-shadow: inset 0 0 0 1px #4a8cac; }
.feedback-periods button:focus-visible { outline: 2px solid #1976d2; outline-offset: 2px; }
.feedback-periods button:disabled { cursor: default; opacity: .65; }
.feedback-period-title { display: flex; align-items: center; gap: 7px; }
.feedback-period-title .q-icon { font-size: 20px; flex-shrink: 0; }
.feedback-period-title strong { font-size: 14px; line-height: 1.5; }
.feedback-period-title > span { margin-left: auto; background: #e5edf2; border-radius: 5px; padding: 2px 7px; font-size: 11px; }
.feedback-periods small { display: block; margin-top: 5px; font-size: 12px; line-height: 1.6; }
.feedback-origin { margin-bottom: 10px; color: #436b81; }
.feedback-body { display: flex; flex: 1; min-height: 0; }
.feedback-sidebar { width: 310px; flex-shrink: 0; border-right: 1px solid #e3ebef; background: #fbfcfd; display: flex; flex-direction: column; min-height: 0; }
.feedback-list-heading { padding: 22px 20px 12px; display: flex; gap: 8px; align-items: center; font-size: 13px; }
.feedback-list-heading > span { color: #7c8c97; font-size: 12px; }
.feedback-filters { display: flex; gap: 4px; padding: 0 14px 16px; border-bottom: 1px solid #e8eef1; }
.feedback-filters button { border: none; border-radius: 6px; padding: 7px 8px; background: transparent; color: #647887; font: inherit; font-size: 12px; cursor: pointer; white-space: nowrap; }
.feedback-filters button span { margin-left: 3px; font-size: 11px; }
.feedback-filters button.active { background: #e6f0f6; color: #205c7c; font-weight: 700; }
.feedback-list { overflow-y: auto; padding: 10px; }
.feedback-list-item { width: 100%; display: block; text-align: left; padding: 16px 14px; margin-bottom: 6px; border: 1px solid transparent; border-radius: 10px; background: transparent; color: inherit; font: inherit; cursor: pointer; }
.feedback-list-item:hover { background: #f0f5f8; }
.feedback-list-item.selected { background: #fff; border-color: #85b0c5; box-shadow: 0 2px 6px #213f5010; }
.feedback-list-item:focus-visible, .feedback-filters button:focus-visible { outline: 2px solid #1976d2; outline-offset: 2px; }
.feedback-item-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 9px; }
.feedback-list-item > strong { display: block; font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }
.feedback-mine { color: #236f94; font-size: 11px; font-weight: 700; }
.feedback-status { display: inline-flex; border-radius: 5px; padding: 4px 7px; background: #edf1f4; color: #536b7a; font-size: 11px; font-weight: 700; line-height: 1.2; }
.feedback-status--writing, .feedback-status--submitted { background: #e8f1fc; color: #3267a5; }
.feedback-status--applying { background: #fff0d9; color: #966219; }
.feedback-status--applied { background: #e4f4ee; color: #237b5b; }
.feedback-status--cancelled { background: #f0f0f0; color: #777; }
.feedback-item-meta { margin-top: 9px; font-size: 12px; color: #6b7f8c; line-height: 1.6; }
.feedback-item-target { margin-top: 6px; color: #527889; font-size: 11px; }
.feedback-detail { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.feedback-detail-heading { padding: 24px 28px 18px; }
.feedback-detail-heading h3 { font-size: 20px; line-height: 1.5; margin: 10px 0 7px; font-weight: 700; overflow-wrap: anywhere; }
.feedback-detail-title { display: flex; align-items: center; justify-content: space-between; min-height: 28px; }
.feedback-detail-scroll { overflow-y: auto; flex: 1; min-height: 0; padding: 0 28px 28px; }
.feedback-destination { display: flex; align-items: center; gap: 12px; padding: 15px 16px; background: #eef5fa; color: #315d77; border-radius: 9px; margin-bottom: 24px; }
.feedback-destination small, .feedback-destination strong { display: block; }
.feedback-destination small { font-size: 11px; margin-bottom: 3px; }
.feedback-destination strong { font-size: 13px; line-height: 1.6; }
.feedback-destination .q-btn { margin-left: auto; flex-shrink: 0; }
.feedback-destination--done { background: #edf8f1; color: #277954; }
.feedback-memo { border: 1px solid #eee5ce; border-radius: 9px; background: #fffdf7; padding: 18px; margin-bottom: 26px; overflow-wrap: anywhere; }
.feedback-section-label { display: flex; align-items: center; gap: 7px; margin-bottom: 12px; }
.feedback-section-label > .q-icon { color: #7b8f9b; font-size: 18px; }
.feedback-section-label h4 { font-size: 14px; line-height: 1.5; font-weight: 700; margin: 0; }
.feedback-memo :deep(p:last-child) { margin-bottom: 0; }
.feedback-section-label > span { margin-left: auto; color: #8b7b57; font-size: 11px; }
.feedback-help { color: #647887; font-size: 12px; line-height: 1.8; margin: 0 0 14px; }
.feedback-response { overflow-wrap: anywhere; }
.feedback-awaiting { display: flex; align-items: center; flex-direction: column; background: #f7f9fa; border-radius: 9px; padding: 28px 18px; text-align: center; gap: 8px; color: #657d8b; }
.feedback-awaiting strong { font-size: 13px; font-weight: 500; }
.feedback-awaiting p { margin: 0; font-size: 12px; line-height: 1.8; }
.feedback-footer { padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; border-top: 1px solid #e3ebef; background: #fff; }
.feedback-footer-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-left: auto; }
.feedback-save-hint { color: #6e8190; font-size: 11px; }
.feedback-footer .q-btn { border-radius: 7px; }
.feedback-create-form { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.feedback-form-section { margin-bottom: 20px; }
.feedback-form-section > .q-field { margin-bottom: 16px; }
.feedback-assignment { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.feedback-private-note { display: flex; gap: 6px; align-items: baseline; color: #7b725f; font-size: 11px; line-height: 1.8; margin-top: 10px; }
.feedback-field-error { color: #b43535; font-size: 12px; margin: 8px 0; }
.feedback-notice { background: #fff5e2; color: #8a631f; padding: 12px 14px; border-radius: 7px; font-size: 12px; line-height: 1.8; margin: 12px 0; }
.feedback-saving { pointer-events: none; opacity: .7; }
.feedback-empty, .feedback-loading { flex: 1; display: flex; align-items: center; justify-content: center; flex-direction: column; padding: 32px; text-align: center; gap: 12px; color: #667e8d; }
.feedback-empty-icon { background: #edf3f7; border-radius: 18px; padding: 16px; color: #6890a5; }
.feedback-empty h3 { font-size: 18px; line-height: 1.5; color: #334e5e; margin: 8px 0 0; }
.feedback-empty p { font-size: 13px; line-height: 1.9; margin: 0 0 10px; }
.feedback-list-empty { color: #7e929f; text-align: center; padding: 30px 16px; font-size: 12px; }
.feedback-mobile-back { display: none; }
@media (max-width: 800px) {
  .feedback-workspace { width: 100vw; max-width: 100vw; height: 100dvh; max-height: 100dvh; border-radius: 0; }
  .feedback-header { padding: 18px 16px 14px; gap: 10px; flex-wrap: wrap; position: relative; }
  .feedback-header h2 { font-size: 21px; }
  .feedback-header > div:first-child { padding-right: 30px; }
  .feedback-header p { font-size: 12px; }
  .feedback-header-actions > .q-btn:last-child { position: absolute; right: 8px; top: 12px; }
  .feedback-header-actions > .q-btn:first-child { font-size: 12px; min-height: 34px; }
  .feedback-periods { padding: 10px 12px; gap: 8px; }
  .feedback-periods button { padding: 10px; }
  .feedback-period-title { gap: 5px; }
  .feedback-period-title .q-icon { display: none; }
  .feedback-period-title strong { font-size: 12px; }
  .feedback-period-title > span { padding: 2px 5px; }
  .feedback-periods small { font-size: 10px; }
  .feedback-workspace--detail .feedback-header p, .feedback-workspace--create .feedback-header p,
  .feedback-workspace--detail .feedback-header-actions > .q-btn:first-child, .feedback-workspace--create .feedback-header-actions > .q-btn:first-child,
  .feedback-workspace--detail .feedback-periods, .feedback-workspace--create .feedback-periods { display: none; }
  .feedback-sidebar { width: 100%; border: 0; }
  .feedback-workspace--list .feedback-detail { display: none; }
  .feedback-workspace--detail .feedback-sidebar, .feedback-workspace--create .feedback-sidebar { display: none; }
  .feedback-mobile-back { display: flex; align-self: flex-start; margin: 12px 16px 0; color: #647e8c; }
  .feedback-detail-heading { padding: 12px 20px 18px; }
  .feedback-detail-heading h3 { font-size: 18px; }
  .feedback-detail-scroll { padding: 0 20px 24px; }
  .feedback-footer { padding: 12px 16px max(12px, env(safe-area-inset-bottom)); }
  .feedback-footer-actions { width: 100%; margin: 0; }
  .feedback-footer-actions > .q-btn { flex: 1 0 auto; font-size: 12px; }
  .feedback-assignment { grid-template-columns: 1fr; gap: 4px; }
  .feedback-destination { flex-wrap: wrap; padding: 12px; }
  .feedback-destination .q-btn { margin-left: 32px; }
}
</style>
