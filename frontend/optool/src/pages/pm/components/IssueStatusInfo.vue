<template>
  <q-icon name="info_outline" size="15px" color="grey-6" class="q-ml-xs cursor-help" aria-label="상태 설명">
    <q-tooltip anchor="bottom middle" self="top middle" class="bg-grey-9 text-white">
      <div v-for="status in ISSUE_STATUSES" :key="status" class="q-py-xs">
        <strong>{{ STATUS_LABEL[status] }}</strong> — {{ STATUS_DESCRIPTION[status] }}
      </div>
    </q-tooltip>
  </q-icon>
</template>

<script setup lang="ts">
import { ISSUE_STATUSES, STATUS_LABEL } from 'src/services/pm/issue'

const STATUS_DESCRIPTION = {
  BACKLOG: '아직 작업 일정이 정해지지 않은 항목',
  TODO: '작업할 준비가 된 항목',
  IN_PROGRESS: '현재 작업 중인 항목',
  IMPLEMENTED: '개발 / 운영 서버에 완료된 항목',
  DONE: '개발 / 운영 서버에 완료된 항목',
} as const
</script>
