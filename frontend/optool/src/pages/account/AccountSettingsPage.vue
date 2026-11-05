<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-gutter-sm q-mb-md">
      <q-btn flat dense icon="arrow_back" label="마이페이지" @click="router.push('/account/my-page')" />
      <div class="text-h6">계정 설정</div>
    </div>

    <!-- 화면 테마 -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-subtitle2 q-mb-xs">화면 모드</div>
        <div class="text-body2 text-grey-7 q-mb-md">라이트 모드와 다크 모드 중 원하는 화면을 선택하세요.</div>
        <q-btn-toggle
          v-model="appearanceMode"
          :options="appearanceOptions"
          color="grey-3"
          text-color="dark"
          toggle-color="primary"
          toggle-text-color="white"
          unelevated
        />
        <div class="text-caption text-grey-6 q-mt-sm">선택한 모드는 이 브라우저에서 계정별로 저장됩니다.</div>
      </q-card-section>
    </q-card>

    <!-- 내 정보 -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-subtitle2 q-mb-sm">내 정보</div>
        <q-list separator>
          <q-item>
            <q-item-section>
              <q-item-label caption>이메일</q-item-label>
              <q-item-label>{{ auth.me?.email }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label caption>이름</q-item-label>
              <q-item-label>{{ auth.me?.fullName || '-' }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label caption>계정 유형</q-item-label>
              <q-item-label>
                <q-badge :color="auth.me?.isAdmin ? 'negative' : 'primary'" outline>
                  {{ auth.me?.isAdmin ? '관리자' : '일반' }}
                </q-badge>
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- 비밀번호 변경 -->
    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle2 q-mb-md">비밀번호 변경</div>
        <q-form @submit.prevent="onChangePw" class="q-gutter-md" style="max-width: 400px">
          <q-input
            v-model="currentPw"
            label="현재 비밀번호"
            type="password"
            outlined
            dense
            autocomplete="current-password"
            :rules="[val => !!val || '현재 비밀번호를 입력해 주세요.']"
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
          <div>
            <q-btn type="submit" color="primary" label="변경" :loading="loading" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'
import { useThemeStore, type AppearanceMode } from 'stores/theme'
import { api } from 'boot/axios'

const $q = useQuasar()
const auth = useAuthStore()
const theme = useThemeStore()
const router = useRouter()

const appearanceOptions = [
  { label: '라이트 모드', value: 'light', icon: 'light_mode' },
  { label: '다크 모드', value: 'dark', icon: 'dark_mode' },
]
const appearanceMode = computed({
  get: () => theme.appearanceMode,
  set: (mode: AppearanceMode) => theme.setAppearanceMode(mode, auth.me?.id),
})

const currentPw = ref('')
const newPw = ref('')
const newPwConfirm = ref('')
const loading = ref(false)

async function onChangePw() {
  if (newPw.value !== newPwConfirm.value) {
    $q.notify({ type: 'negative', message: '새 비밀번호가 일치하지 않습니다.' })
    return
  }
  loading.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: currentPw.value,
      new_password: newPw.value,
    })
    $q.notify({ type: 'positive', message: '비밀번호가 변경되었습니다.' })
    currentPw.value = ''
    newPw.value = ''
    newPwConfirm.value = ''
    void router.push('/app')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '비밀번호 변경에 실패했습니다.'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    loading.value = false
  }
}
</script>
