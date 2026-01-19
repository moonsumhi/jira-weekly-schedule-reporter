<template>
  <q-page class="flex flex-center bg-grey-2">
    <q-card class="q-pa-lg" style="width: 420px; max-width: 95vw;">
      <q-card-section>
        <div class="text-h6 text-center">데이터운영팀 OPTOOL</div>
        <div class="text-subtitle2 text-center text-grey-7">
          로그인하거나 새 계정을 만들어 주세요.
        </div>
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

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="auth.loading"
                  type="submit"
                  color="primary"
                  label="로그인"
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
                />
              </div>
            </q-form>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>

      <q-separator />

      <!-- Optional debug area: show only when logged in -->
      <q-card-section v-if="auth.isLoggedIn">
        <div class="row items-center q-gutter-sm">
          <q-btn
            flat
            dense
            icon="person"
            label="/auth/me 확인"
            @click="onCheckMe"
          />
          <q-btn
            flat
            dense
            color="negative"
            icon="logout"
            label="로그아웃"
            @click="onLogout"
          />
        </div>

        <div v-if="auth.me" class="q-mt-md">
          <div class="text-caption text-grey-7">현재 사용자</div>
          <q-card flat bordered class="q-pa-sm q-mt-xs">
            <div class="text-body2"><b>ID:</b> {{ auth.me.id }}</div>
            <div class="text-body2"><b>이메일:</b> {{ auth.me.email }}</div>
            <div class="text-body2">
              <b>이름:</b> {{ auth.me?.fullName || '-' }}
            </div>
          </q-card>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const fullName = ref('')

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

  $q.notify({ type: 'positive', message: '로그인되었습니다.' })
  goAfterAuth()
}

async function onSubmitRegister() {
  const registered = await auth.register(email.value, password.value, fullName.value)
  if (!registered) {
    $q.notify({ type: 'negative', message: auth.lastError || '회원가입에 실패했어요.' })
    return
  }

  $q.notify({ type: 'positive', message: '회원가입이 완료되어 자동으로 로그인합니다.' })

  const ok = await auth.login(email.value, password.value)
  if (!ok) {
    $q.notify({ type: 'negative', message: auth.lastError || '로그인에 실패했어요.' })
    return
  }

  mode.value = 'login'
  goAfterAuth()
}

async function onCheckMe() {
  try {
    const me = await auth.fetchMe()
    if (!me) {
      $q.notify({ type: 'warning', message: '로그인이 필요합니다.' })
    } else {
      $q.notify({ type: 'positive', message: `${me.email} 님, 안녕하세요.` })
    }
  } catch {
    $q.notify({
      type: 'negative',
      message: auth.lastError || '/auth/me 조회에 실패했어요.',
    })
  }
}

function onLogout() {
  auth.logout()
  $q.notify({ type: 'info', message: '로그아웃되었습니다.' })
  // router.replace returns a Promise -> mark as intentionally ignored
  void router.replace({ name: 'auth' })
}
</script>
