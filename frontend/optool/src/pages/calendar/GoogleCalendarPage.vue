<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6">팀 캘린더</div>
      <q-space />
      <q-btn
        v-if="isAdmin"
        flat dense round icon="settings"
        color="grey-7"
        @click="openSettings"
      >
        <q-tooltip>캘린더 URL 설정</q-tooltip>
      </q-btn>
    </div>

    <!-- URL 미설정 -->
    <div v-if="!calendarUrl && !loading" class="text-center text-grey-5 q-pa-xl">
      <q-icon name="calendar_month" size="48px" class="q-mb-sm" /><br />
      Google 캘린더가 설정되지 않았습니다.<br />
      <span v-if="isAdmin" class="text-primary cursor-pointer" @click="openSettings">
        설정에서 캘린더 URL을 입력해주세요.
      </span>
      <span v-else>관리자에게 캘린더 URL 설정을 요청하세요.</span>
    </div>

    <!-- 캘린더 iframe -->
    <div v-else-if="calendarUrl" class="calendar-wrap">
      <iframe
        :src="calendarUrl"
        style="border:0"
        width="100%"
        height="100%"
        frameborder="0"
        scrolling="no"
        allowfullscreen
      />
    </div>
  </q-page>

  <!-- 설정 다이얼로그 (관리자 전용) -->
  <q-dialog v-model="settingsDialog" persistent>
    <q-card style="min-width:480px">
      <q-card-section class="text-h6">Google 캘린더 설정</q-card-section>
      <q-card-section class="q-gutter-sm">
        <div class="text-caption text-grey-7 q-mb-sm">
          Google Calendar → 설정 → 캘린더 통합 → 삽입 코드에서<br />
          <code>src="..."</code> 안의 URL을 복사하여 붙여넣으세요.
        </div>
        <q-input
          v-model="urlInput"
          outlined dense
          label="캘린더 임베드 URL"
          placeholder="https://calendar.google.com/calendar/embed?src=..."
          autofocus
        />
        <div class="text-caption text-grey-6 q-mt-xs">
          한국 시간대 적용을 위해 URL에 <code>&amp;ctz=Asia/Seoul</code>이 포함되어 있는지 확인하세요.
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="취소" v-close-popup />
        <q-btn
          color="primary" label="저장"
          :loading="saving"
          @click="saveUrl"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useAuthStore } from 'stores/auth'

const $q = useQuasar()
const auth = useAuthStore()

const isAdmin = computed(() => !!auth.me?.isAdmin)

const loading = ref(false)
const saving = ref(false)
const calendarUrl = ref('')
const settingsDialog = ref(false)
const urlInput = ref('')

async function load() {
  loading.value = true
  try {
    const res = await api.get<{ key: string; value: string | null }>('/settings/google_calendar_url')
    calendarUrl.value = res.data.value ?? ''
  } catch {
    calendarUrl.value = ''
  } finally {
    loading.value = false
  }
}

function openSettings() {
  urlInput.value = calendarUrl.value
  settingsDialog.value = true
}

async function saveUrl() {
  if (!urlInput.value.trim()) return
  saving.value = true
  try {
    await api.put('/settings/google_calendar_url', { value: urlInput.value.trim() })
    calendarUrl.value = urlInput.value.trim()
    settingsDialog.value = false
    $q.notify({ type: 'positive', message: '캘린더 URL이 저장되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.calendar-wrap {
  width: 100%;
  height: calc(100vh - 120px);
  min-height: 500px;
}
.calendar-wrap iframe {
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.1);
}
</style>
