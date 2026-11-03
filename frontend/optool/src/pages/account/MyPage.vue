<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div>
        <div class="text-h5 text-weight-bold">마이페이지</div>
        <div class="text-body2 text-grey-7 q-mt-xs">내 계정 정보와 방화벽 정책 현황을 확인합니다.</div>
      </div>
      <q-space />
      <q-btn flat icon="settings" label="계정 설정" @click="router.push('/account/settings')" />
    </div>

    <q-card flat bordered>
      <q-tabs v-model="tab" align="left" active-color="primary" indicator-color="primary">
        <q-tab name="profile" icon="badge" label="내 정보" />
        <q-tab name="firewall" icon="security" label="방화벽 정책 현황" />
      </q-tabs>
      <q-separator />

      <q-tab-panels v-model="tab" animated>
        <q-tab-panel name="profile" class="q-pa-lg">
          <div class="row items-center q-mb-md">
            <div class="text-h6">내 정보</div>
            <q-space />
            <q-btn outline color="primary" icon="edit" label="내 정보 수정" @click="openProfileDialog" />
          </div>
          <div class="row q-col-gutter-md">
            <div v-for="item in profileItems" :key="item.label" class="col-12 col-sm-6 col-lg-4">
              <q-card flat bordered class="profile-field">
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ item.label }}</div>
                  <div class="text-body1 text-weight-medium q-mt-xs">{{ item.value || '-' }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
          <div class="text-caption text-grey-6 q-mt-md">
            내 정보는 직접 수정할 수 있으며, 이메일과 소속 팀은 관리자 정보로 관리됩니다.
          </div>
        </q-tab-panel>

        <q-tab-panel name="firewall" class="q-pa-lg">
          <div class="text-h6 q-mb-md">방화벽 정책 현황</div>
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-12 col-md-6">
              <q-card flat bordered class="identity-card">
                <q-card-section class="row items-center no-wrap">
                  <q-avatar color="primary" text-color="white" icon="person" class="q-mr-md" />
                  <div class="col">
                    <div class="text-caption text-grey-7">사용자 이름</div>
                    <div class="text-body1 text-weight-bold">{{ auth.me?.fullName || '-' }}</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-md-6">
              <q-card flat bordered class="identity-card">
                <q-card-section class="row items-center no-wrap">
                  <q-avatar color="blue-grey-7" text-color="white" icon="computer" class="q-mr-md" />
                  <div class="col">
                    <div class="text-caption text-grey-7">등록된 호스트 PC IP</div>
                    <div class="text-body1 text-weight-bold">{{ auth.me?.hostPcIp || '-' }}</div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div class="row items-center q-gutter-sm q-mb-md">
            <div class="text-subtitle1 text-weight-medium">
              조회 대상 IP: <span class="text-primary">{{ auth.me?.hostPcIp || '미등록' }}</span>
            </div>
            <q-space />
            <q-btn color="primary" icon="search" label="정책 조회" disable>
              <q-tooltip>방화벽 정책 API 연결 후 사용할 수 있습니다.</q-tooltip>
            </q-btn>
          </div>

          <div class="row items-center q-gutter-sm q-mb-sm" aria-label="정책 상태 범례">
            <q-badge color="green-2" text-color="green-10" label="정상 · 91일 이상" />
            <q-badge color="orange-2" text-color="orange-10" label="만료예정 · 31~90일" />
            <q-badge color="red-2" text-color="red-10" label="만료임박 · 0~30일" />
            <q-badge color="grey-4" text-color="grey-9" label="종료 · 종료일 경과" />
          </div>

          <div class="row items-center q-mt-lg q-mb-sm">
            <div class="text-h6">내 방화벽 정책</div>
            <q-space />
            <q-badge color="blue-grey-1" text-color="blue-grey-9" :label="`총 ${policyRows.length}건`" />
          </div>

          <q-table
            flat
            bordered
            :rows="policyRows"
            :columns="policyColumns"
            row-key="policyName"
            :pagination="{ rowsPerPage: 10 }"
            no-data-label="방화벽 정책 API 연결 후 정책이 표시됩니다."
          >
            <template #body="props">
              <q-tr :props="props" :class="policyRowClass(props.row)">
                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                  <q-badge v-if="col.name === 'status'" :color="statusColor(props.row)" :text-color="statusTextColor(props.row)">
                    {{ policyStatus(props.row).label }}
                  </q-badge>
                  <span v-else-if="col.name === 'policyName'" class="column">
                    <span class="text-weight-medium">{{ props.row.policyName || '-' }}</span>
                    <span v-if="props.row.description" class="text-caption text-grey-7">{{ props.row.description }}</span>
                  </span>
                  <span v-else-if="col.name === 'remainingDays'">{{ remainingDaysLabel(props.row) }}</span>
                  <span v-else>{{ col.value ?? '-' }}</span>
                </q-td>
              </q-tr>
            </template>
          </q-table>
          <div class="text-caption text-grey-6 q-mt-sm">
            등록된 호스트 PC IP를 기준으로 관련 정책을 조회합니다.
          </div>
        </q-tab-panel>
      </q-tab-panels>
    </q-card>

    <q-dialog v-model="profileDialog">
      <q-card style="width: 520px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">내 정보 수정</div>
          <div class="text-caption text-grey-7 q-mt-xs">로그인 이메일과 소속 팀은 관리자 정보로 관리됩니다.</div>
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="editProfile.fullName" outlined dense label="이름" />
          <q-input v-model="editProfile.employeeNumber" outlined dense label="사번" />
          <q-input v-model="editProfile.hostPcIp" outlined dense label="호스트 PC IP" />
          <q-input v-model="editProfile.extension" outlined dense label="내선번호" />
          <q-input v-model="editProfile.position" outlined dense label="직책" />
        </q-card-section>
        <q-separator />
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="saving" @click="saveProfile" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'stores/auth'
import { api } from 'boot/axios'
import { getErrorMessage } from 'src/utils/http/error'
import type { QTableProps } from 'quasar'

const router = useRouter()
const $q = useQuasar()
const auth = useAuthStore()
const tab = ref<'profile' | 'firewall'>('profile')
const profileDialog = ref(false)
const saving = ref(false)
const editProfile = reactive({
  fullName: '',
  employeeNumber: '',
  hostPcIp: '',
  extension: '',
  position: '',
})

type PolicyRow = {
  sourceIp: string
  destinationIp: string
  protocol: string
  port: string
  startDate: string
  endDate: string
  policyName: string
  description: string
}

const policyRows = ref<PolicyRow[]>([])
const policyColumns: NonNullable<QTableProps['columns']> = [
  { name: 'status', label: '정책 상태', field: (row: PolicyRow) => policyStatus(row).label, align: 'center' },
  { name: 'policyName', label: '정책 이름 · 설명', field: 'policyName', align: 'left' },
  { name: 'sourceIp', label: '출발지 IP', field: 'sourceIp', align: 'left' },
  { name: 'destinationIp', label: '도착지 IP', field: 'destinationIp', align: 'left' },
  { name: 'protocolPort', label: '프로토콜 · 포트', field: (row: PolicyRow) => [row.protocol, row.port].filter(Boolean).join(' · '), align: 'left' },
  { name: 'period', label: '적용 기간', field: (row: PolicyRow) => `${row.startDate} ~ ${row.endDate}`, align: 'left' },
  { name: 'remainingDays', label: '잔여일', field: (row: PolicyRow) => remainingDays(row.endDate), align: 'center' },
]

const profileItems = computed(() => [
  { label: '이름', value: auth.me?.fullName },
  { label: '사번', value: auth.me?.employeeNumber },
  { label: '이메일', value: auth.me?.email },
  { label: '호스트 PC IP', value: auth.me?.hostPcIp },
  { label: '내선번호', value: auth.me?.extension },
  { label: '직책', value: auth.me?.position },
  { label: '소속 팀', value: auth.me?.team },
])

function openProfileDialog() {
  editProfile.fullName = auth.me?.fullName ?? ''
  editProfile.employeeNumber = auth.me?.employeeNumber ?? ''
  editProfile.hostPcIp = auth.me?.hostPcIp ?? ''
  editProfile.extension = auth.me?.extension ?? ''
  editProfile.position = auth.me?.position ?? ''
  profileDialog.value = true
}

async function saveProfile() {
  saving.value = true
  try {
    await api.patch('/auth/profile', {
      full_name: editProfile.fullName || null,
      employee_number: editProfile.employeeNumber || null,
      host_pc_ip: editProfile.hostPcIp || null,
      extension: editProfile.extension || null,
      position: editProfile.position || null,
    })
    await auth.fetchMe(true)
    profileDialog.value = false
    $q.notify({ type: 'positive', message: '내 정보가 저장되었습니다.' })
  } catch (error) {
    $q.notify({ type: 'negative', message: getErrorMessage(error, '내 정보 저장에 실패했습니다.') })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await auth.fetchMe(true)
})

function todayKstOrdinal(): number {
  const dateParts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const part = (type: Intl.DateTimeFormatPartTypes) => dateParts.find(item => item.type === type)?.value ?? '0'
  return Date.UTC(Number(part('year')), Number(part('month')) - 1, Number(part('day'))) / 86_400_000
}

function remainingDays(endDate: string): number {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(endDate)
  if (!match) return 0
  const endOrdinal = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / 86_400_000
  return endOrdinal - todayKstOrdinal()
}

function remainingDaysLabel(row: PolicyRow): string {
  const days = remainingDays(row.endDate)
  return days < 0 ? `${Math.abs(days)}일 경과` : `${days}일`
}

function policyStatus(row: PolicyRow): { label: string; color: string; textColor: string; rowClass: string } {
  const days = remainingDays(row.endDate)
  if (days < 0) return { label: '종료', color: 'grey-4', textColor: 'grey-9', rowClass: 'policy-row-expired' }
  if (days <= 30) return { label: '만료임박', color: 'red-2', textColor: 'red-10', rowClass: 'policy-row-expiring' }
  if (days <= 90) return { label: '만료예정', color: 'orange-2', textColor: 'orange-10', rowClass: 'policy-row-upcoming' }
  return { label: '정상', color: 'green-2', textColor: 'green-10', rowClass: 'policy-row-normal' }
}

function policyRowClass(row: PolicyRow): string {
  return policyStatus(row).rowClass
}

function statusColor(row: PolicyRow): string {
  return policyStatus(row).color
}

function statusTextColor(row: PolicyRow): string {
  return policyStatus(row).textColor
}
</script>

<style scoped>
.profile-field {
  min-height: 82px;
}

.identity-card {
  min-height: 88px;
}

:deep(.policy-row-normal > td) {
  background: #f1f8e9;
}

:deep(.policy-row-upcoming > td) {
  background: #fff3e0;
}

:deep(.policy-row-expiring > td) {
  background: #ffebee;
}

:deep(.policy-row-expired > td) {
  background: #eeeeee;
  color: #616161;
}
</style>
