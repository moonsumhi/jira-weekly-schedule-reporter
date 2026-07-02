<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-gutter-sm q-mb-md">
      <div class="text-h6">회원 목록</div>
      <q-space />
      <q-btn outline icon="refresh" label="새로고침" :loading="loading" @click="load" />
    </div>

    <q-card bordered>
      <q-card-section>
        <q-input
          v-model="filter"
          dense
          outlined
          clearable
          debounce="200"
          placeholder="이메일/이름 검색"
          style="max-width: 300px"
        />
      </q-card-section>

      <q-separator />

      <q-card-section class="q-pa-none">
        <q-table
          :rows="filteredRows"
          :columns="columns"
          row-key="id"
          :pagination="{ rowsPerPage: 10 }"
          :loading="loading"
          flat
          bordered
        >
          <template #body-cell-team="props">
            <q-td :props="props">
              <span v-if="props.row.team" class="text-caption">{{ props.row.team }}</span>
              <span v-else class="text-grey-4 text-caption">-</span>
            </q-td>
          </template>

          <template #body-cell-isAdmin="props">
            <q-td :props="props">
              <q-badge :color="props.row.isBlocked ? 'grey-7' : props.row.isAdmin ? 'negative' : 'grey-5'" outline>
                {{ props.row.isBlocked ? '차단됨' : props.row.isAdmin ? '관리자' : '일반' }}
              </q-badge>
            </q-td>
          </template>

          <template #body-cell-permissions="props">
            <q-td :props="props">
              <span v-if="props.row.isAdmin" class="text-grey-5 text-caption">전체 허용</span>
              <div v-else class="row q-gutter-xs">
                <q-badge
                  v-for="p in PERMISSION_OPTIONS"
                  :key="p.value"
                  :color="props.row.permissions?.includes(p.value) ? 'primary' : 'grey-3'"
                  :text-color="props.row.permissions?.includes(p.value) ? 'white' : 'grey-6'"
                  outline
                >
                  {{ p.label }}
                </q-badge>
              </div>
            </q-td>
          </template>

          <template #body-cell-lastLoginAt="props">
            <q-td :props="props">
              <span v-if="props.row.lastLoginAt" class="text-caption">
                {{ formatKst(props.row.lastLoginAt) }}
              </span>
              <span v-else class="text-grey-5 text-caption">-</span>
            </q-td>
          </template>

          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn dense flat icon="edit" color="primary" @click="openEdit(props.row)">
                <q-tooltip>정보 편집</q-tooltip>
              </q-btn>
              <q-btn dense flat icon="key" color="orange-7" @click="openPwDialog(props.row)">
                <q-tooltip>비밀번호 변경</q-tooltip>
              </q-btn>
              <q-btn
                v-if="!props.row.isAdmin"
                dense flat
                :icon="props.row.isBlocked ? 'lock_open' : 'block'"
                :color="props.row.isBlocked ? 'positive' : 'negative'"
                :loading="blockingId === props.row.id"
                @click="toggleBlock(props.row)"
              >
                <q-tooltip>{{ props.row.isBlocked ? '차단 해제' : '차단' }}</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Edit Dialog -->
    <q-dialog v-model="editDialog">
      <q-card style="width: 520px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">회원 정보 편집</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ selected?.email }}</div>
        </q-card-section>

        <q-separator />

        <q-card-section class="q-gutter-md">
          <div>
            <div class="text-subtitle2 q-mb-sm">기본 정보</div>
            <div class="column q-gutter-sm">
              <q-input
                v-model="editFullName"
                label="이름"
                outlined
                dense
              />
              <q-select
                v-model="editTeam"
                :options="TEAM_OPTIONS"
                label="소속 팀"
                outlined
                dense
                clearable
              />
            </div>
          </div>

          <div>
            <div class="text-subtitle2 q-mb-sm">계정 유형</div>
            <q-toggle v-model="editIsAdmin" label="관리자 권한" color="negative" />
          </div>

          <div v-if="!editIsAdmin">
            <div class="row items-center q-mb-sm">
              <div class="text-subtitle2">메뉴 접근 권한</div>
              <q-space />
              <q-btn flat dense size="sm" :label="isAllSelected ? '전체 해제' : '전체 선택'" @click="toggleAll" />
            </div>
            <div class="column q-gutter-sm">
              <q-checkbox
                v-for="p in PERMISSION_OPTIONS"
                :key="p.value"
                v-model="editPermissions"
                :val="p.value"
                :label="p.label"
                color="primary"
              />
            </div>
          </div>

          <div v-if="!editIsAdmin && editPermissions.includes('sr')">
            <q-separator class="q-my-sm" />
            <div class="text-subtitle2 q-mb-sm">SR 역할 <span class="text-caption text-grey-5">(SR 메뉴 활성 시)</span></div>
            <div class="column q-gutter-sm">
              <q-checkbox v-model="editPermissions" val="sr_requester" label="접수자 (sr_requester) — SR 접수·본인 SR 조회" color="blue-grey" />
              <q-checkbox v-model="editPermissions" val="sr_operator" label="처리자 (sr_operator) — 상태 변경 가능" color="teal" />
              <q-checkbox v-model="editPermissions" val="sr_manager" label="관리자 (sr_manager) — 검토·승인·담당자 배정 가능" color="deep-orange" />
            </div>
          </div>
          <div v-else class="text-caption text-grey-6">
            관리자는 모든 메뉴에 접근 가능합니다.
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="saving" @click="doSave" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 비밀번호 변경 Dialog -->
    <q-dialog v-model="pwDialog" persistent>
      <q-card style="width: 360px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">비밀번호 변경</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ pwTarget?.email }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="pwNew" label="새 비밀번호 *" outlined dense
            :type="pwShow ? 'text' : 'password'"
            :append-icon="pwShow ? 'visibility_off' : 'visibility'"
            hint="6자 이상">
            <template #append>
              <q-icon :name="pwShow ? 'visibility_off' : 'visibility'"
                class="cursor-pointer" @click="pwShow = !pwShow" />
            </template>
          </q-input>
          <q-input v-model="pwConfirm" label="비밀번호 확인 *" outlined dense
            :type="pwShow ? 'text' : 'password'"
            :error="!!pwNew && !!pwConfirm && pwNew !== pwConfirm"
            error-message="비밀번호가 일치하지 않습니다." />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="orange-7" label="변경" :loading="pwSaving"
            :disable="!pwNew || pwNew.length < 6 || pwNew !== pwConfirm"
            @click="doChangePw" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { getErrorMessage } from 'src/utils/http/error'
import { useMenuStore } from 'src/stores/menus'
import { storeToRefs } from 'pinia'
import type { QTableProps } from 'quasar'

const TEAM_OPTIONS = ['데이터운영팀', '데이터구축팀', '데이터활용팀', '데이터결합팀']

type User = {
  id: string
  email: string
  fullName?: string | null
  team?: string | null
  isAdmin: boolean
  isBlocked: boolean
  permissions: string[]
  createdAt?: string
  lastLoginAt?: string | null
}

const menuStore = useMenuStore()
const { sidebarMenus } = storeToRefs(menuStore)

const PERMISSION_OPTIONS = computed(() =>
  sidebarMenus.value
    .filter((m) => m.slug && m.slug !== 'admin')
    .map((m) => ({ value: m.slug as string, label: m.title }))
)

function formatKst(iso: string): string {
  const s = iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z'
  const d = new Date(s)
  return d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const $q = useQuasar()
const loading = ref(false)
const rows = ref<User[]>([])
const filter = ref('')

const columns: NonNullable<QTableProps['columns']> = [
  { name: 'email',        label: 'Email',      field: 'email',       align: 'left', sortable: true },
  { name: 'fullName',     label: '이름',       field: 'fullName',    align: 'left', sortable: true },
  { name: 'team',         label: '소속 팀',    field: 'team',        align: 'left', sortable: true },
  { name: 'isAdmin',      label: '유형',       field: 'isAdmin',     align: 'left', sortable: true },
  { name: 'permissions',  label: '메뉴 권한',   field: 'permissions', align: 'left' },
  { name: 'lastLoginAt',  label: '마지막 접속일', field: 'lastLoginAt', align: 'left', sortable: true },
  { name: 'actions',      label: '',           field: 'actions',     align: 'right' },
]

const filteredRows = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(
    r => r.email.toLowerCase().includes(q) || (r.fullName || '').toLowerCase().includes(q)
  )
})

async function load() {
  loading.value = true
  try {
    const res = await api.get<User[]>('/admin/users')
    rows.value = res.data
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '회원 목록 조회 실패') })
  } finally {
    loading.value = false
  }
}

// ── 비밀번호 변경 ────────────────────────────────────────────────────
const pwDialog  = ref(false)
const pwTarget  = ref<User | null>(null)
const pwNew     = ref('')
const pwConfirm = ref('')
const pwShow    = ref(false)
const pwSaving  = ref(false)

function openPwDialog(user: User) {
  pwTarget.value  = user
  pwNew.value     = ''
  pwConfirm.value = ''
  pwShow.value    = false
  pwDialog.value  = true
}

async function doChangePw() {
  if (!pwTarget.value || pwNew.value !== pwConfirm.value) return
  pwSaving.value = true
  try {
    await api.post(`/admin/users/${pwTarget.value.id}/change-password`, { new_password: pwNew.value })
    $q.notify({ type: 'positive', message: '비밀번호가 변경되었습니다.' })
    pwDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '비밀번호 변경 실패') })
  } finally {
    pwSaving.value = false
  }
}

const blockingId = ref<string | null>(null)

async function toggleBlock(user: User) {
  blockingId.value = user.id
  try {
    const action = user.isBlocked ? 'unblock' : 'block'
    const res = await api.post<User>(`/admin/users/${user.id}/${action}`)
    rows.value = rows.value.map(r => r.id === user.id ? res.data : r)
    $q.notify({ type: user.isBlocked ? 'positive' : 'warning', message: user.isBlocked ? '차단이 해제되었습니다.' : '계정이 차단되었습니다.' })
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '처리 실패') })
  } finally {
    blockingId.value = null
  }
}

const editDialog = ref(false)
const selected = ref<User | null>(null)
const editFullName = ref('')
const editTeam = ref<string | null>(null)
const editIsAdmin = ref(false)
const editPermissions = ref<string[]>([])
const saving = ref(false)

const isAllSelected = computed(() =>
  PERMISSION_OPTIONS.value.every(p => editPermissions.value.includes(p.value))
)

function toggleAll() {
  const srRoles = editPermissions.value.filter(p => p === 'sr_requester' || p === 'sr_operator' || p === 'sr_manager')
  if (isAllSelected.value) {
    editPermissions.value = srRoles
  } else {
    editPermissions.value = [...new Set([...PERMISSION_OPTIONS.value.map(p => p.value), ...srRoles])]
  }
}

function openEdit(user: User) {
  selected.value = user
  editFullName.value = user.fullName ?? ''
  editTeam.value = user.team ?? null
  editIsAdmin.value = user.isAdmin
  editPermissions.value = [...(user.permissions ?? [])]
  editDialog.value = true
}

async function doSave() {
  if (!selected.value) return
  saving.value = true
  try {
    const res = await api.patch<User>(`/admin/users/${selected.value.id}`, {
      full_name: editFullName.value || null,
      team: editTeam.value || null,
      is_admin: editIsAdmin.value,
      permissions: editIsAdmin.value ? [] : editPermissions.value,
    })
    rows.value = rows.value.map(r => r.id === selected.value!.id ? res.data : r)
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
    editDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await menuStore.refresh()
  void load()
})
</script>
