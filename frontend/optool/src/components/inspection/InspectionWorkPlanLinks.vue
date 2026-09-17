<template>
  <div v-if="plans?.length" class="inspection-work-plan-links">
    <span class="plan-link-label"><q-icon name="description" size="14px" />작업계획서</span>
    <template v-for="plan in plans" :key="plan.id">
      <button
        v-if="canOpen && !plan.unavailable && !plan.isDeleted"
        type="button"
        class="plan-link"
        @click="
          selected = plan;
          open = true;
        "
      >
        {{ displayWorkPlan(plan).title }}
      </button>
      <span v-else class="plan-link-unavailable"
        >{{ displayWorkPlan(plan).title
        }}<small>{{ plan.unavailable || plan.isDeleted ? ' · 문서 확인 불가' : '' }}</small></span
      >
    </template>
  </div>
  <WorkDocumentEntryDialog
    v-if="selected && open"
    v-model="open"
    :entry-id="selected.id"
    :title="selected.templateTitle"
    :back-label="props.backLabel"
    @saved="changed = true"
  />
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useAuthStore } from 'stores/auth';
import WorkDocumentEntryDialog from 'src/components/WorkDocumentEntryDialog.vue';
import { displayWorkPlan, type InspectionWorkPlan } from 'src/services/inspectionWorkPlans';
const props = withDefaults(
  defineProps<{ plans?: InspectionWorkPlan[] | undefined; backLabel?: string }>(),
  {
    backLabel: '점검 목록으로 돌아가기',
  },
);
const auth = useAuthStore();
const emit = defineEmits<{ updated: [] }>();
const canOpen = computed(() => !!(auth.me?.isAdmin || auth.me?.permissions?.includes('job')));
const selected = ref<InspectionWorkPlan | null>(null),
  open = ref(false);
const changed = ref(false);
watch(open, (visible) => {
  if (!visible && changed.value) {
    changed.value = false;
    emit('updated');
  }
});
</script>
<style scoped>
.inspection-work-plan-links {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 5px 10px;
  margin-top: 8px;
  min-width: 0;
  font-size: 11px;
  line-height: 1.7;
}
.plan-link-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #7c8b9d;
  flex-shrink: 0;
}
.plan-link {
  padding: 0;
  border: 0;
  background: none;
  color: #456b91;
  font: inherit;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.plan-link:hover {
  text-decoration: underline;
}
.plan-link-unavailable {
  color: #7c8b9d;
  overflow-wrap: anywhere;
}
@media print {
  .plan-link {
    color: #52657a;
    text-decoration: none;
  }
}
</style>
