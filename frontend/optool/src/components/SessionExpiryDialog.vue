<template>
  <q-dialog v-model="visible" persistent>
    <q-card style="min-width: 320px">
      <q-card-section class="row items-center q-gutter-sm">
        <q-icon name="fa-solid fa-clock" color="warning" size="24px" />
        <div class="text-subtitle1">세션 만료 안내</div>
      </q-card-section>

      <q-card-section class="text-body2">
        <strong>{{ remainingLabel }}</strong> 후 자동으로 로그아웃됩니다.<br />
        로그아웃을 원치 않으면 연장 버튼을 눌러주세요.
      </q-card-section>

      <q-card-actions align="right">
        <q-btn unelevated label="세션 연장" color="primary" :loading="extending" @click="onExtend" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Notify } from 'quasar'
import { useAuthStore } from 'stores/auth'

// 경고 시작 시점 = min(5분, 세션 전체 길이의 20%), 최소 30초 — 5분처럼 짧게 설정된
// 테스트용 세션에서 로그인/새로고침 직후부터 계속 경고가 뜨는 것을 방지
const MAX_WARNING_MS = 5 * 60 * 1000
const MIN_WARNING_MS = 30 * 1000
const WARNING_RATIO = 0.2
// 다이얼로그가 떠 있는 동안 초 단위 카운트다운을 보여줘야 해서 1초 간격으로 체크
const CHECK_INTERVAL_MS = 1_000

function warningWindowMs(): number {
  const { tokenIssuedAt, tokenExpiresAt } = auth
  if (!tokenIssuedAt || !tokenExpiresAt) return MAX_WARNING_MS
  const duration = tokenExpiresAt - tokenIssuedAt
  if (duration <= 0) return MAX_WARNING_MS
  return Math.min(MAX_WARNING_MS, Math.max(MIN_WARNING_MS, duration * WARNING_RATIO))
}

const auth = useAuthStore()
const router = useRouter()

const visible = ref(false)
const extending = ref(false)
const remainingMs = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const remainingLabel = computed(() => {
  const totalSec = Math.max(0, Math.floor(remainingMs.value / 1000))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return m > 0 ? `${m}분 ${s}초` : `${s}초`
})

function forceLogout() {
  visible.value = false
  auth.logout()
  Notify.create({
    type: 'warning',
    message: '세션이 만료되었습니다. 다시 로그인해 주세요.',
    timeout: 4000,
  })
  void router.replace({ name: 'auth' })
}

function check() {
  if (!auth.token || !auth.tokenExpiresAt) {
    visible.value = false
    return
  }
  const remaining = auth.tokenExpiresAt - Date.now()
  remainingMs.value = remaining

  if (remaining <= 0) {
    forceLogout()
    return
  }
  // 내부망 슬라이딩 세션 등으로 백그라운드에서 조용히 연장된 경우 다이얼로그를 다시 닫는다.
  visible.value = remaining <= warningWindowMs()
}

async function onExtend() {
  extending.value = true
  const ok = await auth.extendSession()
  extending.value = false
  if (ok) {
    visible.value = false
    Notify.create({ type: 'positive', message: '세션이 연장되었습니다.', timeout: 2000 })
  } else {
    Notify.create({ type: 'negative', message: '세션 연장에 실패했습니다. 다시 로그인해 주세요.', timeout: 3000 })
    forceLogout()
  }
}

onMounted(() => {
  check()
  timer = setInterval(check, CHECK_INTERVAL_MS)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
