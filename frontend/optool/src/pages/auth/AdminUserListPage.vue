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
                <q-tooltip>권한 설정</q-tooltip>
              </q-btn>
              <q-btn dense flat icon="key" color="grey-7" @click="openPwChange(props.row)">
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
          <div class="text-h6">권한 설정</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ selected?.email }}</div>
        </q-card-section>

        <q-separator />

        <q-card-section class="q-gutter-md">
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
    <q-dialog v-model="pwDialog">
      <q-card style="width: 360px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">비밀번호 변경</div>
          <div class="text-body2 text-grey-7 q-mt-xs">{{ pwTarget?.email }}</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="newPassword"
            outlined dense
            label="새 비밀번호"
            :type="showPw ? 'text' : 'password'"
            :rules="[v => v.length >= 6 || '6자 이상 입력하세요']"
          >
            <template #append>
              <q-icon :name="showPw ? 'visibility_off' : 'visibility'" class="cursor-pointer" @click="showPw = !showPw" />
            </template>
          </q-input>
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="변경" :loading="pwSaving" @click="doChangePw" />
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
import type { QTableProps } from 'quasar'

type User = {
  id: string
  email: string
  fullName?: string | null
  isAdmin: boolean
  isBlocked: boolean
  permissions: string[]
  createdAt?: string
  lastLoginAt?: string | null
}

const PERMISSION_OPTIONS = [
  { value: 'jira_search',           label: 'Jira 검색' },
  { value: 'weekly_report',         label: '주간 보고서' },
  { value: 'asset_list',            label: '서버 자산' },
  { value: 'watch_timetable',       label: '당직 일정' },
  { value: 'inspection_checklist',  label: '서버실 점검' },
  { value: 'pilot_tasks',           label: 'Pilot AI' },
]

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
const editIsAdmin = ref(false)
const editPermissions = ref<string[]>([])
const saving = ref(false)

const isAllSelected = computed(() =>
  PERMISSION_OPTIONS.every(p => editPermissions.value.includes(p.value))
)

function toggleAll() {
  if (isAllSelected.value) {
    editPermissions.value = []
  } else {
    editPermissions.value = PERMISSION_OPTIONS.map(p => p.value)
  }
}

function openEdit(user: User) {
  selected.value = user
  editIsAdmin.value = user.isAdmin
  editPermissions.value = [...(user.permissions ?? [])]
  editDialog.value = true
}

async function doSave() {
  if (!selected.value) return
  saving.value = true
  try {
    const res = await api.patch<User>(`/admin/users/${selected.value.id}`, {
      is_admin: editIsAdmin.value,
      permissions: editIsAdmin.value ? [] : editPermissions.value,
    })
    rows.value = rows.value.map(r => r.id === selected.value!.id ? res.data : r)
    $q.notify({ type: 'positive', message: '권한이 저장되었습니다.' })
    editDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '저장 실패') })
  } finally {
    saving.value = false
  }
}

const pwDialog = ref(false)
const pwTarget = ref<User | null>(null)
const newPassword = ref('')
const showPw = ref(false)
const pwSaving = ref(false)

function openPwChange(user: User) {
  pwTarget.value = user
  newPassword.value = ''
  showPw.value = false
  pwDialog.value = true
}

async function doChangePw() {
  if (!pwTarget.value || newPassword.value.length < 6) return
  pwSaving.value = true
  try {
    await api.post(`/admin/users/${pwTarget.value.id}/change-password`, { new_password: newPassword.value })
    $q.notify({ type: 'positive', message: '비밀번호가 변경되었습니다.' })
    pwDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: getErrorMessage(e, '비밀번호 변경 실패') })
  } finally {
    pwSaving.value = false
  }
}

onMounted(() => void load())
</script>
