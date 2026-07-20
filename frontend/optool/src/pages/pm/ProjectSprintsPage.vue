<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h6">{{ project?.name }} — 스프린트</div>
      <q-badge v-if="project" color="primary" :label="project.key" class="q-ml-sm" />
      <q-space />
      <q-btn color="primary" icon="add" label="스프린트 생성" @click="openCreateDialog" />
    </div>

    <q-inner-loading :showing="loading" />

    <div v-if="!loading && sprints.length === 0" class="text-center text-grey-6 q-mt-xl">
      스프린트가 없습니다.
    </div>

    <div class="column q-gutter-md">
      <q-card v-for="sprint in sprints" :key="sprint.id" flat bordered>
        <q-card-section>
          <div class="row items-center q-gutter-sm">
            <q-badge :color="statusColor(sprint.status)" :label="statusLabel(sprint.status)" />
            <span class="text-h6">{{ sprint.name }}</span>
            <q-space />
            <q-btn
              v-if="sprint.status === 'PLANNED'"
              flat dense color="positive" icon="play_arrow" label="시작"
              @click="startSprint(sprint)"
            />
            <q-btn
              v-if="sprint.status === 'ACTIVE'"
              flat dense color="warning" icon="stop" label="종료"
              @click="completeSprint(sprint)"
            />
            <q-btn flat dense icon="edit" @click="openEditDialog(sprint)" />
            <q-btn flat dense color="negative" icon="delete" @click="confirmDelete(sprint)" />
          </div>
          <div v-if="sprint.goal" class="text-caption text-grey-7 q-mt-xs">목표: {{ sprint.goal }}</div>
          <div class="text-caption text-grey-6 q-mt-xs">
            이슈 {{ sprint.issueCount }}개
            <template v-if="sprint.startDate"> · {{ fmtDate(sprint.startDate) }} ~ {{ fmtDate(sprint.endDate) }}</template>
          </div>
        </q-card-section>
      </q-card>
    </div>

    <!-- 생성/수정 다이얼로그 -->
    <q-dialog v-model="dialog.open" persistent>
      <q-card style="min-width: 380px">
        <q-card-section>
          <div class="text-h6">{{ dialog.isEdit ? '스프린트 수정' : '스프린트 생성' }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="dialog.name" label="이름 *" dense outlined />
          <q-input v-model="dialog.goal" label="목표" dense outlined type="textarea" rows="2" />
          <q-input v-model="dialog.startDate" label="시작일" dense outlined type="date" />
          <q-input v-model="dialog.endDate" label="종료일" dense outlined type="date" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="dialog.open = false" />
          <q-btn color="primary" :label="dialog.isEdit ? '수정' : '생성'" :loading="dialog.loading" @click="submitDialog" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Notify, Dialog } from 'quasar'
import {
  listSprints, createSprint, updateSprint, deleteSprint,
  type Sprint, type SprintStatus,
} from 'src/services/pm/sprint'
import { getProject, type Project } from 'src/services/pm/project'
import { getErrorMessage } from 'src/utils/http/error'
import { fmtDateKst } from 'src/utils/time/kst'

const route = useRoute()
const projectId = route.params.projectId as string

const project = ref<Project | null>(null)
const sprints = ref<Sprint[]>([])
const loading = ref(false)

const dialog = ref({
  open: false, isEdit: false, loading: false,
  id: '', name: '', goal: '', startDate: '', endDate: '',
})

onMounted(async () => {
  loading.value = true
  try {
    const [proj, sp] = await Promise.all([getProject(projectId), listSprints(projectId)])
    project.value = proj
    sprints.value = sp
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function statusLabel(s: SprintStatus) {
  return { PLANNED: '예정', ACTIVE: '진행 중', COMPLETED: '완료' }[s]
}
function statusColor(s: SprintStatus) {
  return { PLANNED: 'grey', ACTIVE: 'positive', COMPLETED: 'blue' }[s]
}
function fmtDate(d: string | null) { return fmtDateKst(d) }

function openCreateDialog() {
  dialog.value = { open: true, isEdit: false, loading: false, id: '', name: '', goal: '', startDate: '', endDate: '' }
}

function openEditDialog(sprint: Sprint) {
  dialog.value = {
    open: true, isEdit: true, loading: false,
    id: sprint.id, name: sprint.name, goal: sprint.goal ?? '',
    startDate: sprint.startDate?.slice(0, 10) ?? '',
    endDate: sprint.endDate?.slice(0, 10) ?? '',
  }
}

async function submitDialog() {
  if (!dialog.value.name) {
    Notify.create({ type: 'warning', message: '이름은 필수입니다.' })
    return
  }
  dialog.value.loading = true
  try {
    const payload = {
      name: dialog.value.name,
      ...(dialog.value.goal ? { goal: dialog.value.goal } : {}),
      ...(dialog.value.startDate ? { start_date: new Date(dialog.value.startDate).toISOString() } : {}),
      ...(dialog.value.endDate ? { end_date: new Date(dialog.value.endDate).toISOString() } : {}),
    }
    if (dialog.value.isEdit) {
      const updated = await updateSprint(projectId, dialog.value.id, payload)
      const idx = sprints.value.findIndex(s => s.id === dialog.value.id)
      if (idx !== -1) sprints.value[idx] = updated
    } else {
      const created = await createSprint(projectId, payload)
      sprints.value.unshift(created)
    }
    dialog.value.open = false
    Notify.create({ type: 'positive', message: dialog.value.isEdit ? '수정되었습니다.' : '생성되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    dialog.value.loading = false
  }
}

async function startSprint(sprint: Sprint) {
  try {
    const updated = await updateSprint(projectId, sprint.id, {
      status: 'ACTIVE',
      start_date: new Date().toISOString(),
    })
    const idx = sprints.value.findIndex(s => s.id === sprint.id)
    if (idx !== -1) sprints.value[idx] = updated
    Notify.create({ type: 'positive', message: '스프린트를 시작했습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '시작 실패') })
  }
}

async function completeSprint(sprint: Sprint) {
  try {
    const updated = await updateSprint(projectId, sprint.id, {
      status: 'COMPLETED',
      end_date: new Date().toISOString(),
    })
    const idx = sprints.value.findIndex(s => s.id === sprint.id)
    if (idx !== -1) sprints.value[idx] = updated
    Notify.create({ type: 'positive', message: '스프린트를 종료했습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '종료 실패') })
  }
}

function confirmDelete(sprint: Sprint) {
  Dialog.create({
    title: '스프린트 삭제',
    message: `"${sprint.name}"을 삭제하시겠습니까? 소속 이슈는 백로그로 이동됩니다.`,
    cancel: true, persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteSprint(projectId, sprint.id)
        sprints.value = sprints.value.filter(s => s.id !== sprint.id)
        Notify.create({ type: 'positive', message: '삭제되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '삭제 실패') })
      }
    })()
  })
}
</script>
