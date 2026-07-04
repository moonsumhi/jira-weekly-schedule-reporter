<template>
  <q-page class="q-pa-md">
    <div class="text-h6 q-mb-md">계정 설정</div>

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
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'
import { api } from 'boot/axios'

const $q = useQuasar()
const auth = useAuthStore()
const router = useRouter()

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
