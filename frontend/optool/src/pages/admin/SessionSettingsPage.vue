<template>
  <q-page padding>
    <div class="text-subtitle1 text-weight-bold q-mb-md">세션 설정</div>

    <q-card flat bordered style="max-width: 480px">
      <q-card-section class="q-gutter-md">
        <q-input
          v-model.number="internalMinutes"
          type="number"
          min="1"
          label="내부망 세션 만료 시간 (분)"
          hint="사내망 접속 시 활동이 있을 때마다 자동 연장(슬라이딩 세션)됩니다"
          outlined
          dense
        />
        <q-input
          v-if="!isPort9000"
          v-model.number="externalMinutes"
          type="number"
          min="1"
          label="외부망 세션 만료 시간 (분)"
          hint="외부 접속(포트 9001)은 자동 연장 없이 고정 시간 후 만료됩니다"
          outlined
          dense
        />
      </q-card-section>

      <q-card-section class="text-caption text-grey">
        <q-icon name="fa-solid fa-info-circle" size="xs" class="q-mr-xs" />
        저장하면 재시작 없이 즉시 반영됩니다. 이미 발급된 세션의 만료 시각은 바뀌지 않고,
        다음 로그인 또는 세션 연장(자동/수동)부터 새 값이 적용됩니다.
      </q-card-section>

      <q-card-actions align="right">
        <q-btn color="primary" label="저장" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { settingsService } from 'src/services/settings'

const $q = useQuasar()

// 포트 9000은 내부 전용 접속점이므로 외부망 설정 UI 자체를 노출하지 않는다.
const isPort9000 = window.location.port === '9000'

const internalMinutes = ref<number | null>(null)
const externalMinutes = ref<number | null>(null)
const saving = ref(false)

async function load() {
  if (isPort9000) {
    const internal = await settingsService.get('access_token_expire_minutes')
    internalMinutes.value = internal.value ? Number(internal.value) : null
    return
  }
  const [internal, external] = await Promise.all([
    settingsService.get('access_token_expire_minutes'),
    settingsService.get('access_token_expire_minutes_external'),
  ])
  internalMinutes.value = internal.value ? Number(internal.value) : null
  externalMinutes.value = external.value ? Number(external.value) : null
}

async function save() {
  if (!internalMinutes.value || (!isPort9000 && !externalMinutes.value)) {
    $q.notify({ type: 'warning', message: '만료 시간을 입력해주세요' })
    return
  }
  saving.value = true
  try {
    const puts = [settingsService.put('access_token_expire_minutes', String(internalMinutes.value))]
    if (!isPort9000 && externalMinutes.value) {
      puts.push(settingsService.put('access_token_expire_minutes_external', String(externalMinutes.value)))
    }
    await Promise.all(puts)
    $q.notify({ type: 'positive', message: '저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
