<template>
  <q-page padding>
    <div class="text-h6 q-mb-md">앱 설정</div>

    <!-- 현재 감지 IP -->
    <q-card class="q-mb-md" style="max-width: 640px">
      <q-card-section>
        <div class="text-subtitle2 q-mb-xs">현재 접속 정보</div>
        <div v-if="myIpLoading" class="text-caption text-grey">확인 중...</div>
        <template v-else-if="myIp">
          <div class="row items-center q-gutter-sm">
            <q-chip :color="myIp.isInternal ? 'positive' : 'negative'" text-color="white" dense>
              {{ myIp.isInternal ? '내부 접속' : '외부 접속' }}
            </q-chip>
            <span class="text-body2 text-mono">{{ myIp.clientIp }}</span>
            <q-btn flat dense icon="refresh" size="sm" @click="loadMyIp" />
          </div>
          <div class="text-caption text-grey q-mt-xs">
            내부 IP 목록에 위 IP가 포함되어 있지 않으면 내부 접속으로 인식되지 않습니다.
          </div>
        </template>
      </q-card-section>
    </q-card>

    <q-card class="q-mb-md" style="max-width: 640px">
      <q-card-section>
        <div class="text-subtitle2 q-mb-xs">내부 IP 목록</div>
        <div class="text-caption text-grey q-mb-sm">
          여기에 등록된 IP에서 접속하면 내부 접속으로 간주합니다.<br>
          IP, IP 프리픽스(예: 192.168.), CIDR(예: 10.0.0.0/8) 형식 지원.<br>
          줄바꿈 또는 콤마로 구분. 비워두면 모두 내부 접속으로 처리됩니다.
        </div>
        <q-input
          v-model="internalIps"
          type="textarea"
          outlined
          dense
          autogrow
          placeholder="192.168.1.0/24&#10;10.0.0.&#10;172.16.0.1"
          :loading="loading"
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="초기화" @click="load" :disable="saving" />
        <q-btn color="primary" label="저장" @click="save" :loading="saving" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'

const $q = useQuasar()
const internalIps = ref('')
const loading = ref(false)
const saving = ref(false)
const myIp = ref<{ clientIp: string; isInternal: boolean } | null>(null)
const myIpLoading = ref(false)

async function loadMyIp() {
  myIpLoading.value = true
  try {
    const { data } = await api.get<{ clientIp: string; isInternal: boolean }>('/settings/my-ip')
    myIp.value = data
  } catch {
    myIp.value = null
  } finally {
    myIpLoading.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<{ key: string; value: string | null }>('/settings/internal_ips')
    internalIps.value = data.value ?? ''
  } catch {
    $q.notify({ type: 'negative', message: '설정을 불러오지 못했습니다' })
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await api.put('/settings/internal_ips', { value: internalIps.value })
    $q.notify({ type: 'positive', message: '저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
  void loadMyIp()
})
</script>
