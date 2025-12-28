<template>
  <q-page class="flex flex-center bg-grey-2">
    <q-card class="q-pa-lg" style="width: 420px; max-width: 95vw;">
      <q-card-section>
        <div class="text-h6 text-center">Welcome</div>
        <div class="text-subtitle2 text-center text-grey-7">
          Login or create a new account
        </div>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-tabs v-model="mode" class="text-primary" align="justify">
          <q-tab name="login" label="Login" />
          <q-tab name="register" label="Register" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="mode" animated>
          <!-- LOGIN TAB -->
          <q-tab-panel name="login">
            <q-form @submit.prevent="onSubmitLogin" class="q-gutter-md">
              <q-input
                v-model="email"
                label="Email"
                type="email"
                outlined
                dense
                autocomplete="username"
                :rules="[val => !!val || 'Email is required']"
              />

              <q-input
                v-model="password"
                label="Password"
                type="password"
                outlined
                dense
                autocomplete="current-password"
                :rules="[val => !!val || 'Password is required']"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="auth.loading"
                  type="submit"
                  color="primary"
                  label="Login"
                />
              </div>
            </q-form>
          </q-tab-panel>

          <!-- REGISTER TAB -->
          <q-tab-panel name="register">
            <q-form @submit.prevent="onSubmitRegister" class="q-gutter-md">
              <q-input
                v-model="email"
                label="Email"
                type="email"
                outlined
                dense
                autocomplete="username"
                :rules="[val => !!val || 'Email is required']"
              />

              <q-input
                v-model="fullName"
                label="Full name"
                outlined
                dense
                autocomplete="name"
              />

              <q-input
                v-model="password"
                label="Password"
                type="password"
                outlined
                dense
                autocomplete="new-password"
                :rules="[val => (val && val.length >= 6) || 'Min 6 characters']"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="auth.loading"
                  type="submit"
                  color="primary"
                  label="Register"
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
            label="Check /auth/me"
            @click="onCheckMe"
          />
          <q-btn
            flat
            dense
            color="negative"
            icon="logout"
            label="Logout"
            @click="onLogout"
          />
        </div>

        <div v-if="auth.me" class="q-mt-md">
          <div class="text-caption text-grey-7">Current user</div>
          <q-card flat bordered class="q-pa-sm q-mt-xs">
            <div class="text-body2"><b>ID:</b> {{ auth.me.id }}</div>
            <div class="text-body2"><b>Email:</b> {{ auth.me.email }}</div>
            <div class="text-body2">
              <b>Name:</b> {{ auth.me.full_name || '-' }}
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
    $q.notify({ type: 'negative', message: auth.lastError || 'Login failed' })
    return
  }

  $q.notify({ type: 'positive', message: 'Login success' })
  goAfterAuth()
}

async function onSubmitRegister() {
  const registered = await auth.register(email.value, password.value, fullName.value)
  if (!registered) {
    $q.notify({ type: 'negative', message: auth.lastError || 'Register failed' })
    return
  }

  $q.notify({ type: 'positive', message: 'Registered. Logging in...' })

  const ok = await auth.login(email.value, password.value)
  if (!ok) {
    $q.notify({ type: 'negative', message: auth.lastError || 'Login failed' })
    return
  }

  mode.value = 'login'
  goAfterAuth()
}

async function onCheckMe() {
  try {
    const me = await auth.fetchMe()
    if (!me) {
      $q.notify({ type: 'warning', message: 'No token / not logged in' })
    } else {
      $q.notify({ type: 'positive', message: `Hello, ${me.email}` })
    }
  } catch {
    $q.notify({
      type: 'negative',
      message: auth.lastError || 'Failed to fetch /auth/me',
    })
  }
}

function onLogout() {
  auth.logout()
  $q.notify({ type: 'info', message: 'Logged out' })
  // router.replace returns a Promise -> mark as intentionally ignored
  void router.replace({ name: 'auth' })
}
</script>

