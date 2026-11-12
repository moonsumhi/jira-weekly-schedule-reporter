<template>
  <q-page class="auth-page">
    <q-card flat bordered class="auth-card">
      <q-card-section class="auth-intro">
        <h1>{{ theme.appName }}</h1>
        <p>
          로그인하거나 새 계정을 만들어 주세요.
        </p>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-tabs v-model="mode" class="text-primary" align="justify">
          <q-tab name="login" label="로그인" />
          <q-tab name="register" label="회원가입" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="mode" animated>
          <!-- LOGIN TAB -->
          <q-tab-panel name="login">
            <q-form @submit.prevent="onSubmitLogin" class="q-gutter-md">
              <q-input
                v-model="email"
                label="이메일"
                type="email"
                outlined
                dense
                autocomplete="username"
                :rules="[val => !!val || '이메일을 입력해 주세요.']"
              />

              <q-input
                v-model="password"
                label="비밀번호"
                type="password"
                outlined
                dense
                autocomplete="current-password"
                :rules="[val => !!val || '비밀번호를 입력해 주세요.']"
              />

              <q-checkbox
                v-model="rememberEmail"
                label="아이디 저장"
                dense
                @update:model-value="onRememberEmailChange"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="auth.loading"
                  type="submit"
                  color="primary"
                  label="로그인"
                  class="full-width"
                />
              </div>
            </q-form>
          </q-tab-panel>

          <!-- REGISTER TAB -->
          <q-tab-panel name="register">
            <q-form @submit.prevent="onSubmitRegister" class="q-gutter-md">
              <q-input
                v-model="email"
                label="이메일"
                type="email"
                outlined
                dense
                autocomplete="username"
                :rules="[val => !!val || '이메일을 입력해 주세요.']"
              />

              <q-input
                v-model="fullName"
                label="이름"
                outlined
                dense
                autocomplete="name"
              />

              <q-select
                v-model="team"
                :options="TEAM_OPTIONS"
                label="소속 팀"
                outlined
                dense
                clearable
                :rules="[val => !!val || '소속 팀을 선택해 주세요.']"
              />

              <q-input
                v-model="password"
                label="비밀번호"
                type="password"
                outlined
                dense
                autocomplete="new-password"
                :rules="[val => (val && val.length >= 6) || '비밀번호는 6자 이상 입력해 주세요.']"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="auth.loading"
                  type="submit"
                  color="primary"
                  label="회원가입"
                  class="full-width"
                />
              </div>
            </q-form>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>

      <q-separator />

      <!-- 계정 설정: show only when logged in -->
      <q-card-section v-if="auth.isLoggedIn">
        <div class="text-subtitle2 text-grey-7 q-mb-sm">계정 설정</div>
        <q-card flat bordered class="q-pa-sm q-mb-md">
          <div class="text-body2"><b>이메일:</b> {{ auth.me?.email }}</div>
          <div class="text-body2"><b>이름:</b> {{ auth.me?.fullName || '-' }}</div>
        </q-card>
        <div class="row q-gutter-sm">
          <q-btn flat dense icon="lock" label="비밀번호 변경" @click="pwDialog = true" />
          <q-btn flat dense color="negative" icon="logout" label="로그아웃" @click="onLogout" />
        </div>
      </q-card-section>

      <!-- 비밀번호 변경 다이얼로그 -->
      <q-dialog v-model="pwDialog">
        <q-card style="width: 400px; max-width: 95vw">
          <q-card-section>
            <div class="text-h6">비밀번호 변경</div>
          </q-card-section>
          <q-separator />
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="currentPw"
              label="현재 비밀번호"
              type="password"
              outlined
              dense
              autocomplete="current-password"
            />
            <q-input
              v-model="newPw"
              label="새 비밀번호"
              type="password"
              outlined
              dense
              autocomplete="new-password"
              :rules="[val => (val && val.length >= 6) || '6자 이상 입력해 주세요.']"
            />
            <q-input
              v-model="newPwConfirm"
              label="새 비밀번호 확인"
              type="password"
              outlined
              dense
              autocomplete="new-password"
              :rules="[val => val === newPw || '비밀번호가 일치하지 않습니다.']"
            />
          </q-card-section>
          <q-separator />
          <q-card-actions align="right">
            <q-btn flat label="취소" v-close-popup />
            <q-btn color="primary" label="변경" :loading="pwLoading" @click="onChangePw" />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'
import { useThemeStore } from 'stores/theme'
import { api } from 'boot/axios'

const $q = useQuasar()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const theme = useThemeStore()

const TEAM_OPTIONS = ['데이터운영팀', '데이터구축팀', '데이터활용팀', '데이터결합팀']
const SAVED_LOGIN_EMAIL_KEY = 'savedLoginEmail'
const savedLoginEmail = localStorage.getItem(SAVED_LOGIN_EMAIL_KEY) ?? ''

const mode = ref<'login' | 'register'>('login')
const email = ref(savedLoginEmail)
const rememberEmail = ref(Boolean(savedLoginEmail))
const password = ref('')
const fullName = ref('')
const team = ref<string | null>(null)

const pwDialog = ref(false)
const currentPw = ref('')
const newPw = ref('')
const newPwConfirm = ref('')
const pwLoading = ref(false)

/**
 * Only allow internal redirects ("/something").
 * This prevents open-redirect attacks like redirect=https://evil.com
 */
const safeRedirect = computed<string | null>(() => {
  const r = route.query.redirect
  if (typeof r !== 'string') return null
  if (!r.startsWith('/')) return null
  return r
})

function goAfterAuth() {
  // router.replace returns a Promise -> mark as intentionally ignored
  void router.replace(safeRedirect.value || { name: 'app-home' })
}

onMounted(() => {
  if (auth.isLoggedIn) {
    goAfterAuth()
  }
})

async function onSubmitLogin() {
  const ok = await auth.login(email.value, password.value)
  if (!ok) {
    $q.notify({ type: 'negative', message: auth.lastError || '로그인에 실패했어요.' })
    return
  }

  if (rememberEmail.value) {
    localStorage.setItem(SAVED_LOGIN_EMAIL_KEY, email.value.trim())
  } else {
    localStorage.removeItem(SAVED_LOGIN_EMAIL_KEY)
  }

  $q.notify({ type: 'positive', message: '로그인되었습니다.' })
  goAfterAuth()
}

function onRememberEmailChange(remember: boolean) {
  if (!remember) localStorage.removeItem(SAVED_LOGIN_EMAIL_KEY)
}

async function onSubmitRegister() {
  const registered = await auth.register(email.value, password.value, fullName.value, team.value ?? undefined)
  if (!registered) {
    $q.notify({ type: 'negative', message: auth.lastError || '회원가입에 실패했어요.' })
    return
  }

  const ok = await auth.login(email.value, password.value)
  if (!ok) {
    $q.notify({ type: 'negative', message: auth.lastError || '로그인에 실패했어요.' })
    return
  }

  mode.value = 'login'
  goAfterAuth()
}

async function onChangePw() {
  if (newPw.value !== newPwConfirm.value) {
    $q.notify({ type: 'negative', message: '새 비밀번호가 일치하지 않습니다.' })
    return
  }
  pwLoading.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: currentPw.value,
      new_password: newPw.value,
    })
    $q.notify({ type: 'positive', message: '비밀번호가 변경되었습니다.' })
    pwDialog.value = false
    currentPw.value = ''
    newPw.value = ''
    newPwConfirm.value = ''
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '비밀번호 변경에 실패했습니다.'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    pwLoading.value = false
  }
}


function onLogout() {
  auth.logout()
  $q.notify({ type: 'info', message: '로그아웃되었습니다.' })
  // router.replace returns a Promise -> mark as intentionally ignored
  void router.replace({ name: 'auth' })
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  background: var(--bo-canvas);
}
.auth-card { width: 460px; max-width: 100%; padding: 24px; }
.auth-intro { padding: 12px 16px 28px; text-align: center; }
.auth-intro h1 { margin: 0; font-size: 24px; line-height: 1.4; font-weight: 700; letter-spacing: -0.6px; overflow-wrap: anywhere; }
.auth-intro p { margin: 10px 0 0; color: var(--bo-muted); font-size: 14px; }
.auth-card :deep(.q-tab-panels) { background: transparent; }
.auth-card :deep(.q-tab-panel) { padding: 28px 0 8px; }
.auth-card :deep(.q-field--dense .q-field__control) { min-height: 44px; }
@media (max-width: 599px) {
  .auth-page { padding: 24px 16px; align-items: flex-start; }
  .auth-card { padding: 16px; }
  .auth-intro { padding: 12px 8px 24px; }
  .auth-intro h1 { font-size: 22px; }
}
</style>
