<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    :maximized="$q.screen.lt.sm"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="inspection-plan-dialog">
      <header>
        <div>
          <h2>작업계획서 연결</h2>
          <p>{{ target?.issue.key }} · {{ target?.issue.title }}</p>
        </div>
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="작업계획서 연결창 닫기"
          :disable="saving"
          @click="emit('update:modelValue', false)"
        />
      </header>
      <main>
        <p class="plan-task-context">
          {{ target ? formatInspectionMonth(target.month) : '' }} ·
          {{
            target?.common
              ? '공통 작업'
              : target?.assets.map((a) => (a.current || a).name).join(' · ')
          }}
        </p>
        <q-banner v-if="error" class="plan-save-error" role="alert"
          >{{ error
          }}<template #action
            ><q-btn
              flat
              dense
              label="최신 연결 불러오기"
              :disable="saving || loading"
              @click="reload" /></template
        ></q-banner>
        <InspectionWorkPlanPicker
          v-if="modelValue && target"
          v-model="selected"
          :disable="saving || loading"
          :asset-ids="target.assets.map((a) => a.id)"
        />
      </main>
      <footer>
        <span>{{ selected.length }}개 연결</span><q-space /><q-btn
          flat
          label="취소"
          :disable="saving"
          @click="emit('update:modelValue', false)"
        /><q-btn
          unelevated
          color="primary"
          label="연결 저장"
          :loading="saving"
          :disable="!canSave"
          @click="save"
        />
      </footer>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import {
  formatInspectionMonth,
  getInspectionTasks,
  inspectionError,
  thisMonth,
  type InspectionTask,
} from 'src/services/inspection';
import { saveInspectionWorkPlans, type InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
import InspectionWorkPlanPicker from './InspectionWorkPlanPicker.vue';
const props = defineProps<{ modelValue: boolean; task: InspectionTask | null }>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>();
const $q = useQuasar();
const target = ref<InspectionTask | null>(null),
  selected = ref<InspectionWorkPlan[]>([]);
const saving = ref(false),
  loading = ref(false),
  error = ref('');
let request = 0;
const canSave = computed(
  () =>
    !saving.value &&
    !loading.value &&
    target.value?.state === 'ACTIVE' &&
    !target.value.issueDeleted &&
    !(target.value.month < thisMonth() && target.value.issue.status === 'DONE'),
);
function setTarget(task: InspectionTask) {
  target.value = task;
  selected.value = (task.workPlans || []).map((plan) => ({ ...plan }));
}
watch(
  () => [props.modelValue, props.task],
  () => {
    ++request;
    error.value = '';
    saving.value = false;
    loading.value = false;
    if (props.modelValue && props.task) setTarget(props.task);
  },
  { immediate: true },
);
async function reload() {
  if (!target.value) return;
  const token = ++request,
    task = target.value;
  loading.value = true;
  try {
    const result = await getInspectionTasks(task.month, {
      issue_id: task.issueId,
      include_overdue: false,
    });
    if (token !== request) return;
    const current = result.items.find((item) => item.month === task.month);
    if (!current) {
      error.value = '점검 작업을 찾을 수 없습니다.';
      target.value = null;
      return;
    }
    setTarget(current);
    error.value = '';
  } catch (e) {
    if (token === request) error.value = inspectionError(e);
  } finally {
    if (token === request) loading.value = false;
  }
}
async function save() {
  if (!canSave.value || !target.value) return;
  const token = request;
  saving.value = true;
  error.value = '';
  try {
    await saveInspectionWorkPlans(
      target.value,
      selected.value.map((plan) => plan.id),
    );
    if (token !== request) return;
    $q.notify({ type: 'positive', message: '작업계획서 연결을 저장했습니다.' });
    emit('saved');
    emit('update:modelValue', false);
  } catch (e) {
    if (token === request) error.value = inspectionError(e);
  } finally {
    if (token === request) saving.value = false;
  }
}
onBeforeUnmount(() => {
  ++request;
});
</script>
<style scoped>
.inspection-plan-dialog {
  width: 620px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  color: #344c65;
}
header {
  padding: 22px 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  border-bottom: 1px solid #e7edf3;
}
h2 {
  font-size: 19px;
  margin: 0;
  font-weight: 650;
  line-height: 1.5;
}
header p {
  margin: 8px 0 0;
  font-size: 12px;
  color: #718398;
  overflow-wrap: anywhere;
}
main {
  overflow-y: auto;
  padding: 18px 24px 24px;
}
.plan-task-context {
  font-size: 12px;
  margin-bottom: 18px;
  color: #657b92;
}
.plan-save-error {
  margin-bottom: 15px;
  background: #fff4f1;
  color: #9d5046;
}
footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid #e7edf3;
  flex-shrink: 0;
}
footer > span {
  font-size: 12px;
  color: #74869b;
}
@media (max-width: 599px) {
  .inspection-plan-dialog {
    width: 100vw;
    max-width: 100vw;
    max-height: 100dvh;
  }
  main {
    flex: 1;
    padding: 16px;
  }
  header,
  footer {
    padding: 18px 16px;
  }
}
</style>
