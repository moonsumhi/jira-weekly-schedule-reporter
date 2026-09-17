<template>
  <div
    :class="
      metric.value !== null && metric.value >= 90
        ? 'text-negative'
        : metric.value !== null && metric.value >= 80
          ? 'text-deep-orange-8'
          : 'text-grey-9'
    "
    class="text-weight-medium"
  >
    {{ metric.value === null ? '—' : `${metric.value}%`
    }}<q-tooltip
      >{{ measurementBasis(metric) }}{{ metric.path ? ` · ${metric.path}` : '' }}</q-tooltip
    >
  </div>
  <div class="text-caption text-grey-7">
    {{
      metric.delta === null ? '비교할 값 없음' : `${metric.delta > 0 ? '+' : ''}${metric.delta}%p`
    }}
  </div>
</template>
<script setup lang="ts">
import type { ResourceMetric } from 'src/services/inspectionReports';
import { measurementBasis } from 'src/utils/inspectionMeasurements';
defineProps<{ metric: ResourceMetric }>();
</script>
