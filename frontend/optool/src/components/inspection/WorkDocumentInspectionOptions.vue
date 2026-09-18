<template>
  <section
    class="document-inspection-options"
    :class="{ 'is-enabled': enabled }"
    aria-label="서버 점검 등록"
  >
    <q-checkbox
      v-model="enabled"
      label="서버 점검에 추가"
      :disable="disable"
      aria-controls="document-inspection-fields"
      :aria-expanded="enabled"
    />
    <p v-if="!enabled" class="inspection-description">
      점검일에 진행할 작업이면 함께 등록해 주세요.
    </p>
    <div v-else id="document-inspection-fields" class="inspection-fields">
      <div class="inspection-dates">
        <InspectionMonthPicker v-model="month" :disable="disable" />
        <q-input
          v-if="!existing.length"
          v-model="plannedOn"
          type="date"
          outlined
          dense
          stack-label
          label="작업 예정일"
          :disable="disable || loading"
          :min="`${month}-01`"
          :max="monthEnd"
        />
      </div>
      <div v-if="loading" class="inspection-feedback" role="status">
        <q-spinner size="16px" />점검 일정 확인 중…
      </div>
      <div v-else-if="error" class="inspection-feedback text-negative" role="alert">
        <span>{{ error }}</span
        ><q-btn flat dense no-caps label="다시 불러오기" :disable="disable" @click="load" />
      </div>
      <p v-else-if="existing.length" class="inspection-feedback inspection-existing">
        <q-icon name="check_circle" size="18px" />이미 {{ formatInspectionMonth(month) }} 점검에
        등록돼 있습니다.
      </p>
      <template v-else>
        <q-select
          v-model="assignee"
          :options="assignees"
          option-label="name"
          use-input
          fill-input
          hide-selected
          clearable
          outlined
          dense
          label="점검 담당자 (선택)"
          input-debounce="250"
          :disable="disable"
          @filter="filterAssignees"
        >
          <template #option="scope"
            ><q-item v-bind="scope.itemProps"
              ><q-item-section>
                <q-item-label>{{ scope.opt.name }}</q-item-label>
                <q-item-label caption>{{ scope.opt.team || scope.opt.email }}</q-item-label>
              </q-item-section></q-item
            ></template
          >
          <template #no-option
            ><q-item
              ><q-item-section>{{
                assigneeError || '일치하는 사용자가 없습니다.'
              }}</q-item-section></q-item
            ></template
          >
        </q-select>
        <p v-if="assets.length" class="inspection-targets">
          <q-icon name="dns" size="17px" /><span
            >연결 자산: {{ assets.map((asset) => asset.name).join(', ') }}</span
          >
        </p>
        <p v-else class="inspection-targets">위에서 자산을 선택해 주세요.</p>
      </template>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import type { WorkDocumentAsset } from 'src/services/formEntries';
import {
  getInspectionDate,
  thisMonth,
  formatInspectionMonth,
  type InspectionTask,
} from 'src/services/inspection';
import {
  getReportParticipantOptions,
  type ReportParticipantUser,
} from 'src/services/inspectionReports';
import {
  documentInspectionTasks,
  workDocumentDate,
  type WorkDocumentInspection,
} from 'src/services/workDocumentInspection';
import InspectionMonthPicker from './InspectionMonthPicker.vue';

const props = defineProps<{
  entryId?: string | undefined;
  assets: WorkDocumentAsset[];
  data: Record<string, unknown>;
  disable: boolean;
}>();
const model = defineModel<WorkDocumentInspection | null>({ required: true });
const enabled = ref(false);
const sourceDate = computed(() => workDocumentDate(props.data));
const month = ref(sourceDate.value.slice(0, 7) || thisMonth()),
  plannedOn = ref('');
const monthEnd = computed(() => {
  const [year, m] = month.value.split('-').map(Number);
  return `${month.value}-${new Date(year!, m!, 0).getDate()}`;
});
const assignee = ref<ReportParticipantUser | null>(null),
  assignees = ref<ReportParticipantUser[]>([]),
  assigneeError = ref('');
const existing = ref<InspectionTask[]>([]),
  loading = ref(false),
  error = ref('');
let request = 0,
  userRequest = 0,
  loadedMonth = '';
watch(
  [enabled, month, plannedOn, assignee],
  () => {
    model.value = enabled.value
      ? {
          month: month.value,
          plannedOn: plannedOn.value,
          assigneeId: assignee.value?.id ?? null,
        }
      : null;
  },
  { immediate: true },
);

async function load() {
  const token = ++request;
  error.value = '';
  existing.value = [];
  if (!enabled.value) {
    loading.value = false;
    return;
  }
  loading.value = true;
  const previousDate = loadedMonth === month.value ? plannedOn.value : '';
  loadedMonth = month.value;
  plannedOn.value = '';
  try {
    const [date, tasks] = await Promise.all([
      getInspectionDate(month.value),
      props.entryId ? documentInspectionTasks(props.entryId, month.value) : Promise.resolve([]),
    ]);
    if (token !== request) return;
    existing.value = tasks;
    plannedOn.value =
      previousDate || (sourceDate.value.startsWith(month.value) ? sourceDate.value : date);
  } catch {
    if (token === request) error.value = '점검 일정을 불러오지 못했습니다.';
  } finally {
    if (token === request) loading.value = false;
  }
}
watch([enabled, month, () => props.entryId], load);
async function filterAssignees(search: string, update: (callback: () => void) => void) {
  const token = ++userRequest;
  assigneeError.value = '';
  try {
    const result = await getReportParticipantOptions(search);
    if (token === userRequest)
      update(() => {
        assignees.value = result.users;
      });
  } catch {
    if (token === userRequest) {
      assigneeError.value = '사용자를 불러오지 못했습니다. 다시 검색해 주세요.';
      update(() => {
        assignees.value = [];
      });
    }
  }
}
onBeforeUnmount(() => {
  ++request;
  ++userRequest;
});
</script>
<style scoped>
.document-inspection-options {
  margin: 0 0 28px;
  padding: 10px 16px;
  border: 1px solid #e1e7ef;
  border-radius: 9px;
  background: #f8fafc;
}
.is-enabled {
  border-color: #a8c6e5;
}
.document-inspection-options > .q-checkbox {
  font-size: 13px;
  font-weight: 600;
  color: #365778;
}
.inspection-description {
  margin: 0 0 6px 40px;
  color: #718399;
  font-size: 12px;
}
.inspection-fields {
  display: grid;
  gap: 16px;
  padding: 16px 8px 8px;
  margin-top: 8px;
  border-top: 1px solid #e1e7ef;
}
.inspection-dates {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.inspection-feedback,
.inspection-targets {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: #526a84;
  font-size: 12px;
  line-height: 1.7;
}
.inspection-targets {
  align-items: flex-start;
  overflow-wrap: anywhere;
}
.inspection-targets .q-icon {
  flex-shrink: 0;
  margin-top: 2px;
}
.inspection-existing {
  color: #397458;
}
@media (max-width: 599px) {
  .document-inspection-options {
    padding: 8px;
  }
  .inspection-description {
    margin-left: 8px;
  }
  .inspection-dates {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
