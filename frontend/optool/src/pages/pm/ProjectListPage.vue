<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h5">프로젝트</div>
      <q-space />
      <q-btn color="primary" icon="add" label="새 프로젝트" @click="openCreateDialog" />
    </div>

    <q-inner-loading :showing="loading" />

    <div v-if="!loading && projects.length === 0" class="column items-center q-mt-xl text-grey-6">
      <q-icon name="fa-solid fa-diagram-project" size="4rem" class="q-mb-md" />
      <div class="text-h6">프로젝트가 없습니다</div>
      <div class="text-caption">새 프로젝트를 만들어보세요.</div>
    </div>

    <div class="row q-col-gutter-md">
      <div v-for="project in projects" :key="project.id" class="col-12 col-sm-6 col-md-4">
        <q-card flat bordered class="cursor-pointer project-card" @click="goToProject(project)">
          <q-card-section>
            <div class="row items-center q-gutter-sm q-mb-xs">
              <q-badge color="primary" :label="project.key" />
            </div>
            <div class="text-h6">{{ project.name }}</div>
            <div class="text-caption text-grey-6">{{ project.description || '설명 없음' }}</div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat dense icon="fa-solid fa-table-columns" label="보드" @click.stop="goToBoard(project)" />
            <q-btn flat dense icon="fa-solid fa-list" label="백로그" @click.stop="goToBacklog(project)" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <!-- 프로젝트 생성 다이얼로그 -->
    <q-dialog v-model="dialog.open" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">새 프로젝트</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="dialog.orgId"
            :options="orgOptions"
            label="조직 *"
            emit-value map-options
            option-value="id" option-label="name"
            dense outlined
          />
          <q-input v-model="dialog.name" label="프로젝트 이름 *" dense outlined />
          <q-input
            v-model="dialog.key"
            label="키 * (예: TF, PROJ)"
            dense outlined
            hint="대문자 영문+숫자, 최대 10자"
            @update:model-value="v => dialog.key = String(v).toUpperCase()"
          />
          <q-input v-model="dialog.description" label="설명" dense outlined type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" @click="dialog.open = false" />
          <q-btn color="primary" label="생성" :loading="dialog.loading" @click="submitCreate" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { listProjects, createProject, type Project } from 'src/services/pm/project'
import { listOrganizations, type Organization } from 'src/services/pm/organization'
import { usePmStore } from 'src/stores/pm'
import { getErrorMessage } from 'src/utils/http/error'

const router = useRouter()
const pmStore = usePmStore()

const projects = ref<Project[]>([])
const orgs = ref<Organization[]>([])
const loading = ref(false)

const orgOptions = computed(() => orgs.value.map(o => ({ id: o.id, name: `${o.name} (${o.slug})` })))

const dialog = ref({
  open: false,
  loading: false,
  orgId: '',
  name: '',
  key: '',
  description: '',
})

onMounted(async () => {
  loading.value = true
  try {
    const [p, o] = await Promise.all([listProjects(), listOrganizations()])
    projects.value = p
    orgs.value = o
    if (o.length) dialog.value.orgId = o[0]!.id
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function openCreateDialog() {
  dialog.value = { open: true, loading: false, orgId: orgs.value[0]?.id ?? '', name: '', key: '', description: '' }
}

async function submitCreate() {
  if (!dialog.value.orgId || !dialog.value.name || !dialog.value.key) {
    Notify.create({ type: 'warning', message: '조직, 이름, 키는 필수입니다.' })
    return
  }
  dialog.value.loading = true
  try {
    const created = await createProject({
      org_id: dialog.value.orgId,
      name: dialog.value.name,
      key: dialog.value.key,
      ...(dialog.value.description ? { description: dialog.value.description } : {}),
    })
    projects.value.unshift(created)
    dialog.value.open = false
    Notify.create({ type: 'positive', message: '프로젝트가 생성되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '생성 실패') })
  } finally {
    dialog.value.loading = false
  }
}

function goToProject(project: Project) {
  pmStore.setProject(project)
  void router.push(`/pm/projects/${project.id}`)
}

function goToBoard(project: Project) {
  pmStore.setProject(project)
  void router.push(`/pm/projects/${project.id}/board`)
}

function goToBacklog(project: Project) {
  pmStore.setProject(project)
  void router.push(`/pm/projects/${project.id}/backlog`)
}
</script>

<style scoped>
.project-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
}
</style>
