<template>
  <q-page class="q-pa-md">
    <q-inner-loading :showing="loading" />

    <template v-if="org">
      <!-- 헤더 -->
      <div class="row items-center q-mb-lg q-gutter-sm">
        <q-btn flat dense round icon="arrow_back" @click="$router.push('/pm/organizations')" />
        <q-avatar color="primary" text-color="white" size="40px">
          {{ org.name[0]?.toUpperCase() ?? '' }}
        </q-avatar>
        <div>
          <div class="text-h5">{{ org.name }}</div>
          <div class="text-caption text-grey-6">{{ org.slug }}</div>
        </div>
        <q-space />
        <q-btn
          v-if="authStore.me?.isAdmin"
          flat dense icon="edit" label="이름 수정"
          @click="openEdit"
        />
      </div>

      <!-- 프로젝트 목록 -->
      <div class="row items-center q-mb-md">
        <div class="text-subtitle1 text-weight-medium">프로젝트 ({{ projects.length }})</div>
        <q-space />
        <q-btn color="primary" icon="add" label="새 프로젝트" @click="openCreateProject" />
      </div>

      <div v-if="!loading && projects.length === 0" class="column items-center q-mt-lg text-grey-6">
        <q-icon name="fa-solid fa-diagram-project" size="40px" class="q-mb-sm" />
        <div class="text-body2">아직 프로젝트가 없습니다.</div>
      </div>

      <div class="row q-col-gutter-md">
        <div v-for="p in projects" :key="p.id" class="col-12 col-sm-6 col-md-4">
          <q-card flat bordered class="project-card cursor-pointer" @click="goProject(p.id)">
            <q-card-section>
              <div class="row items-center q-gutter-sm q-mb-xs">
                <q-badge color="primary" :label="p.key" class="text-caption" />
                <div class="text-subtitle2 text-weight-medium">{{ p.name }}</div>
              </div>
              <div v-if="p.description" class="text-caption text-grey-7 ellipsis-2-lines">
                {{ p.description }}
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section class="q-py-xs">
              <div class="text-caption text-grey-6">생성일: {{ fmtDate(p.createdAt) }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- 멤버 목록 -->
      <q-separator class="q-my-lg" />
      <div class="row items-center q-mb-md">
        <div class="text-subtitle1 text-weight-medium">멤버 ({{ members.length }})</div>
        <q-space />
        <q-btn
          v-if="authStore.me?.isAdmin"
          color="primary" icon="person_add" label="멤버 추가"
          @click="openAddMember"
        />
      </div>

      <q-list bordered separator>
        <q-item v-for="m in members" :key="m.id">
          <q-item-section avatar>
            <q-avatar color="secondary" text-color="white" size="36px">
              {{ (m.userName || m.userEmail)[0]?.toUpperCase() }}
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ m.userName || m.userEmail }}</q-item-label>
            <q-item-label caption>{{ m.userEmail }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-badge :color="m.role === 'ADMIN' ? 'deep-orange' : 'grey-6'" :label="m.role" />
          </q-item-section>
          <q-item-section side v-if="authStore.me?.isAdmin">
            <div class="row q-gutter-xs">
              <q-btn
                flat dense round icon="swap_horiz" size="sm"
                :title="m.role === 'ADMIN' ? 'MEMBER로 변경' : 'ADMIN으로 변경'"
                @click="toggleRole(m)"
              />
              <q-btn
                flat dense round icon="person_remove" size="sm" color="negative"
                title="멤버 제거"
                @click="confirmRemove(m)"
              />
            </div>
          </q-item-section>
        </q-item>
        <q-item v-if="members.length === 0">
          <q-item-section class="text-grey-6 text-center">멤버가 없습니다.</q-item-section>
        </q-item>
      </q-list>

    </template>

    <!-- 멤버 추가 다이얼로그 -->
    <q-dialog v-model="addMemberDialog.open" persistent>
      <q-card style="min-width: 400px">
        <q-card-section><div class="text-h6">멤버 추가</div></q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="addMemberDialog.selectedUser"
            :options="pmUsersFiltered"
            option-value="id"
            :option-label="(opt) => opt.name || opt.email"
            label="사용자 선택 *"
            dense outlined
            use-input
            input-debounce="0"
            @filter="filterUsers"
          >
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.name || scope.opt.email }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.email }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
            <template #no-option><q-item><q-item-section class="text-grey">검색 결과 없음</q-item-section></q-item></template>
          </q-select>
          <q-select
            v-model="addMemberDialog.role"
            :options="['MEMBER', 'ADMIN']"
            label="역할"
            dense outlined
          />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" @click="addMemberDialog.open = false" />
          <q-btn
            color="primary" label="추가"
            :loading="addMemberDialog.loading"
            :disable="!addMemberDialog.selectedUser"
            @click="submitAddMember"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 조직 이름 수정 다이얼로그 -->
    <q-dialog v-model="editDialog.open" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">조직 이름 수정</div>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-input v-model="editDialog.name" label="조직 이름 *" dense outlined autofocus />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" @click="editDialog.open = false" />
          <q-btn
            color="primary" label="저장"
            :loading="editDialog.loading"
            :disable="!editDialog.name"
            @click="submitEdit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 새 프로젝트 생성 다이얼로그 -->
    <q-dialog v-model="createDialog.open" persistent>
      <q-card style="min-width: 420px">
        <q-card-section>
          <div class="text-h6">새 프로젝트</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="createDialog.name"
            label="프로젝트 이름 *"
            dense outlined autofocus
            @update:model-value="autoKey"
          />
          <q-input
            v-model="createDialog.key"
            label="키 *"
            dense outlined
            hint="대문자 영문, 2–10자 (예: PROJ)"
            :rules="[v => /^[A-Z][A-Z0-9]{1,9}$/.test(v) || '대문자 영문/숫자 2~10자']"
          />
          <q-input v-model="createDialog.description" label="설명" dense outlined type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="취소" @click="createDialog.open = false" />
          <q-btn
            color="primary" label="생성"
            :loading="createDialog.loading"
            :disable="!createDialog.name || !createDialog.key"
            @click="submitCreate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Dialog, Notify } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import {
  getOrganization, patchOrganization, listOrgProjects,
  listOrgMembers, addOrgMember, patchOrgMemberRole, removeOrgMember,
  listPmUsers,
  type Organization, type OrgMember, type PmUser,
} from 'src/services/pm/organization'
import { createProject, type Project } from 'src/services/pm/project'
import { getErrorMessage } from 'src/utils/http/error'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const orgId = route.params.orgId as string

const org = ref<Organization | null>(null)
const projects = ref<Project[]>([])
const members = ref<OrgMember[]>([])
const pmUsers = ref<PmUser[]>([])
const pmUsersFiltered = ref<PmUser[]>([])
const loading = ref(false)

const editDialog = ref({ open: false, name: '', loading: false })
const createDialog = ref({ open: false, name: '', key: '', description: '', loading: false })
const addMemberDialog = ref<{
  open: boolean
  selectedUser: PmUser | null
  role: 'ADMIN' | 'MEMBER'
  loading: boolean
}>({ open: false, selectedUser: null, role: 'MEMBER', loading: false })

onMounted(async () => {
  loading.value = true
  try {
    const [o, p, m] = await Promise.all([
      getOrganization(orgId),
      listOrgProjects(orgId),
      listOrgMembers(orgId),
    ])
    org.value = o
    projects.value = p
    members.value = m
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '로드 실패') })
  } finally {
    loading.value = false
  }
})

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })
}

function goProject(projectId: string) {
  void router.push(`/pm/projects/${projectId}`)
}

function openEdit() {
  editDialog.value = { open: true, name: org.value?.name ?? '', loading: false }
}

async function submitEdit() {
  editDialog.value.loading = true
  try {
    org.value = await patchOrganization(orgId, { name: editDialog.value.name })
    editDialog.value.open = false
    Notify.create({ type: 'positive', message: '수정되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '수정 실패') })
  } finally {
    editDialog.value.loading = false
  }
}

function openCreateProject() {
  createDialog.value = { open: true, name: '', key: '', description: '', loading: false }
}

function autoKey(name: string | number | null) {
  if (!name || typeof name !== 'string') return
  createDialog.value.key = name
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 10)
}

async function submitCreate() {
  createDialog.value.loading = true
  try {
    const p = await createProject({
      org_id: orgId,
      name: createDialog.value.name,
      key: createDialog.value.key,
      ...(createDialog.value.description ? { description: createDialog.value.description } : {}),
    })
    projects.value.unshift(p)
    createDialog.value.open = false
    Notify.create({ type: 'positive', message: '프로젝트가 생성되었습니다.' })
    void router.push(`/pm/projects/${p.id}`)
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '생성 실패') })
  } finally {
    createDialog.value.loading = false
  }
}

async function openAddMember() {
  if (pmUsers.value.length === 0) {
    pmUsers.value = await listPmUsers()
  }
  pmUsersFiltered.value = pmUsers.value
  addMemberDialog.value = { open: true, selectedUser: null, role: 'MEMBER', loading: false }
}

function filterUsers(val: string, update: (fn: () => void) => void) {
  update(() => {
    const q = val.toLowerCase()
    pmUsersFiltered.value = pmUsers.value.filter(
      u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
    )
  })
}

async function submitAddMember() {
  if (!addMemberDialog.value.selectedUser) return
  addMemberDialog.value.loading = true
  try {
    const m = await addOrgMember(orgId, addMemberDialog.value.selectedUser.id, addMemberDialog.value.role)
    members.value.push(m)
    addMemberDialog.value.open = false
    Notify.create({ type: 'positive', message: '멤버가 추가되었습니다.' })
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '추가 실패') })
  } finally {
    addMemberDialog.value.loading = false
  }
}

async function toggleRole(m: OrgMember) {
  const newRole = m.role === 'ADMIN' ? 'MEMBER' : 'ADMIN'
  try {
    const updated = await patchOrgMemberRole(orgId, m.userId, newRole)
    const idx = members.value.findIndex(x => x.id === m.id)
    if (idx !== -1) members.value[idx] = updated
  } catch (e) {
    Notify.create({ type: 'negative', message: getErrorMessage(e, '역할 변경 실패') })
  }
}

function confirmRemove(m: OrgMember) {
  Dialog.create({
    title: '멤버 제거',
    message: `${m.userName || m.userEmail}을(를) 조직에서 제거하시겠습니까?`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await removeOrgMember(orgId, m.userId)
        members.value = members.value.filter(x => x.id !== m.id)
        Notify.create({ type: 'positive', message: '멤버가 제거되었습니다.' })
      } catch (e) {
        Notify.create({ type: 'negative', message: getErrorMessage(e, '제거 실패') })
      }
    })()
  })
}
</script>

<style scoped>
.project-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.ellipsis-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
