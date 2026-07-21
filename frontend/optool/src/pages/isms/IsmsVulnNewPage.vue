<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <q-btn flat dense icon="arrow_back" @click="router.push('/isms-p/vulnerabilities')" />
      <div class="text-h6 q-ml-sm">새 취약점 추가</div>
    </div>

    <q-form @submit="submit">
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-subtitle1 text-weight-bold q-mb-sm">기본 정보</div>
              <div class="row q-col-gutter-sm">
                <div class="col-6">
                  <q-input v-model="form.check_date" dense outlined type="date" label="점검일시 *"
                    :rules="[(v: string) => !!v || '필수 입력']" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.asset_category" dense outlined label="자산구분" />
                </div>
                <div class="col-6">
                  <q-select v-model="form.asset_type" dense outlined label="자산종류"
                    :options="ASSET_TYPE_SUGGESTIONS" use-input new-value-mode="add-unique" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.zone" dense outlined label="Zone" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.asset_name" dense outlined label="자산명" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.hostname" dense outlined label="호스트명" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.ip_address" dense outlined label="IP" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.classification" dense outlined label="분류" />
                </div>
                <div class="col-6">
                  <q-input v-model="form.check_code" dense outlined label="점검코드" />
                </div>
                <div class="col-6">
                  <q-select v-model="form.risk_level" dense outlined label="위험도" :options="RISK_LEVEL_OPTIONS" />
                </div>
                <div class="col-12">
                  <q-input v-model="form.check_item" dense outlined type="textarea" autogrow label="점검항목" />
                </div>
                <div class="col-12">
                  <q-input v-model="form.check_result" dense outlined type="textarea" autogrow label="점검결과" />
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-6">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-subtitle1 text-weight-bold q-mb-sm">조치 정보</div>
              <div class="row q-col-gutter-sm">
                <div class="col-6">
                  <q-input v-model="form.assignee" dense outlined label="담당자" />
                </div>
                <div class="col-6">
                  <q-select v-model="form.control_status" dense outlined label="통제여부" :options="CONTROL_STATUS_OPTIONS" clearable />
                </div>
                <div class="col-6">
                  <q-input v-model="form.planned_date" dense outlined type="date" label="조치예정일" />
                </div>
                <div class="col-12">
                  <q-input v-model="form.action_plan" dense outlined type="textarea" autogrow label="조치계획" />
                </div>
                <div class="col-12">
                  <q-input v-model="form.notes" dense outlined type="textarea" autogrow label="비고" />
                </div>
              </div>
            </q-card-section>
          </q-card>

          <div class="row justify-end q-mt-md">
            <q-btn flat label="취소" class="q-mr-sm" @click="router.push('/isms-p/vulnerabilities')" />
            <q-btn type="submit" color="primary" label="생성" :loading="saving" />
          </div>
        </div>
      </div>
    </q-form>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import {
  createVulnerability,
  RISK_LEVEL_OPTIONS, CONTROL_STATUS_OPTIONS, ASSET_TYPE_SUGGESTIONS,
  type VulnerabilityCreatePayload,
} from 'src/services/isms/vulnerability'

const router = useRouter()
const $q = useQuasar()
const saving = ref(false)

const form = ref<VulnerabilityCreatePayload>({
  check_date: '', asset_category: '', asset_type: '', zone: '', asset_name: '',
  hostname: '', ip_address: '', classification: '', check_code: '', check_item: '',
  risk_level: null, check_result: '', assignee: '', control_status: null,
  action_plan: '', planned_date: '', notes: '',
})

async function submit() {
  saving.value = true
  try {
    const payload: VulnerabilityCreatePayload = {}
    for (const [k, v] of Object.entries(form.value)) {
      (payload as Record<string, unknown>)[k] = v === '' ? null : v
    }
    const created = await createVulnerability(payload)
    $q.notify({ type: 'positive', message: '취약점이 생성되었습니다.' })
    void router.push(`/isms-p/vulnerabilities/${created.id}`)
  } catch {
    $q.notify({ type: 'negative', message: '생성에 실패했습니다.' })
  } finally {
    saving.value = false
  }
}
</script>
