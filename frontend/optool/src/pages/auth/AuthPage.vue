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
                :rules="[val => !!val || 'Email is required']"
              />

              <q-input
                v-model="password"
                label="Password"
                type="password"
                outlined
                dense
                :rules="[val => !!val || 'Password is required']"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="loading"
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
                :rules="[val => !!val || 'Email is required']"
              />

              <q-input
                v-model="fullName"
                label="Full name"
                outlined
                dense
              />

              <q-input
                v-model="password"
                label="Password"
                type="password"
                outlined
                dense
                :rules="[val => (val && val.length >= 6) || 'Min 6 characters']"
              />

              <div class="row items-center q-mt-md">
                <q-space />
                <q-btn
                  :loading="loading"
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

      <q-card-section>
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

        <div v-if="me" class="q-mt-md">
          <div class="text-caption text-grey-7">Current user</div>
          <q-card flat bordered class="q-pa-sm q-mt-xs">
            <div class="text-body2"><b>ID:</b> {{ me.id }}</div>
            <div class="text-body2"><b>Email:</b> {{ me.email }}</div>
            <div class="text-body2">
              <b>Name:</b> {{ me.full_name || '-' }}
            </div>
          </q-card>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import axios, { type AxiosError } from 'axios'
import { useRoute, useRouter } from 'vue-router'

type UserMe = {
  id: string | number
  email: string
  full_name?: string | null
}

type ApiErrorBody = {
  detail?: string
  message?: string
}

const $q = useQuasar()
const router = useRouter()
const route = useRoute()

const mode = ref<'login' | 'register'>('login')
const email = ref<string>('')
const password = ref<string>('')
const fullName = ref<string>('')
const loading = ref<boolean>(false)
const me = ref<UserMe | null>(null)

function saveToken(token: string) {
  localStorage.setItem('access_token', token)
}

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

function clearToken() {
  localStorage.removeItem('access_token')
}

function getErrorMessage(err: unknown, fallback: string) {
  const e = err as AxiosError<ApiErrorBody>
  return e.response?.data?.detail || e.response?.data?.message || e.message || fallback
}

async function fetchMe() {
  const token = getToken()
  if (!token) {
    me.value = null
    return
  }

  const res = await axios.get<UserMe>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  me.value = res.data
}

async function onSubmitLogin() {
  loading.value = true
  try {
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const res = await axios.post<{ access_token: string }>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    saveToken(res.data.access_token)
    $q.notify({ type: 'positive', message: 'Login success' })

    await fetchMe()

    // ✅ support redirect query (?redirect=/jira/search)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect || { name: 'app-home' })
  } catch (err) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, 'Login failed') })
  } finally {
    loading.value = false
  }
}

async function onSubmitRegister() {
  loading.value = true
  try {
    await axios.post('/auth/register', {
      email: email.value,
      password: password.value,
      full_name: fullName.value || null,
    })

    $q.notify({ type: 'positive', message: 'Registered. Logging in...' })

    // auto-login
    await onSubmitLogin()
  } catch (err) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, 'Register failed') })
  } finally {
    loading.value = false
  }
}

async function onCheckMe() {
  try {
    await fetchMe()
    if (!me.value) {
      $q.notify({ type: 'warning', message: 'No token / not logged in' })
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: getErrorMessage(err, 'Failed to fetch /auth/me') })
  }
}

async function onLogout() {
  clearToken()
  me.value = null
  $q.notify({ type: 'info', message: 'Logged out' })
  await router.replace({ name: 'auth' })
}
</script>

<style scoped>
</style>
