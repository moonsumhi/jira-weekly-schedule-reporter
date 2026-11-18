<template>
  <q-card class="server-form-card typed-asset-dialog" :class="software ? 'software-dialog' : 'storage-dialog'" :aria-label="`${category} ${editing ? '편집' : '등록'}`">
    <q-form @submit="submit">
      <div ref="body">
        <q-card-section class="q-pb-sm" :class="editing && !software ? 'row items-center' : undefined">
          <div :class="{ col: editing && !software }">
            <div class="top-field-row">
              <span class="top-field-label">{{ software ? '관리명' : '호스트명' }}:</span>
              <q-input :model-value="values['__name__']" @update:model-value="v => values = { ...values, __name__: String(v ?? '') }" borderless dense class="top-field-input" :aria-label="software ? '관리명' : '호스트명'"
                :disable="saving" :placeholder="software ? '미입력 시 제품명으로 자동 설정' : editing ? undefined : 'hostname'"
                :error="!!errors['__name__']" :error-message="errors['__name__']" hide-bottom-space />
            </div>
            <div v-if="!software" class="top-field-row q-mt-sm">
              <span class="top-field-label">IP:</span>
              <div class="col">
                <q-input :model-value="values['__ip__']" @update:model-value="v => values = { ...values, __ip__: String(v ?? '') }" borderless dense class="top-field-input" aria-label="IP" :disable="saving" :placeholder="editing ? undefined : '192.168.0.1'" />
              </div>
            </div>
          </div>
          <q-btn v-if="editing && !software" flat dense round icon="close" aria-label="편집 닫기" class="q-ml-md self-start" :disable="saving" @click="emit('cancel')" />
        </q-card-section>
        <SoftwareAssetFields v-if="software" v-model="values" :own-id="ownId || ''" :disabled="saving" :validated="validated" />
        <StorageAssetFields v-else v-model="values" :own-id="ownId || ''" :disabled="saving" :validated="validated" />
        <q-card-section class="q-py-sm form-field">
          <div class="field-label">태그 (선택)</div>
          <q-select v-model="tags" borderless dense class="field-input" aria-label="태그 (선택)" multiple use-input use-chips new-value-mode="add-unique" hide-dropdown-icon :disable="saving" placeholder="태그 입력 후 Enter" />
        </q-card-section>
      </div>
      <q-separator />
      <q-card-actions align="right" class="q-pa-md">
        <q-btn flat label="취소" class="q-mr-sm" :disable="saving" @click="emit('cancel')" />
        <q-btn class="create-btn" :label="editing ? '저장' : '생성'" type="submit" :loading="saving" />
      </q-card-actions>
    </q-form>
  </q-card>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import SoftwareAssetFields from './SoftwareAssetFields.vue'
import StorageAssetFields from './StorageAssetFields.vue'
import { softwareErrors } from 'src/utils/softwareAssetForm'
import { storageErrors } from 'src/utils/storageAssetForm'
const props = defineProps<{ category: '스토리지' | '소프트웨어'; modelValue: Record<string, string>; modelTags: string[]; editing?: boolean; saving?: boolean; ownId?: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, string>]; 'update:modelTags': [value: string[]]; submit: []; cancel: []
}>()
const values = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
const tags = computed({ get: () => props.modelTags, set: value => emit('update:modelTags', value) })
const software = computed(() => props.category === '소프트웨어')
const validated = ref(false)
const errors = computed(() => validated.value ? (software.value ? softwareErrors(values.value) : storageErrors(values.value)) : {})
const body = ref<HTMLElement>()
async function submit() {
  if (props.saving) return
  validated.value = true
  if (Object.keys(errors.value).length) {
    await nextTick()
    body.value?.querySelector<HTMLInputElement>('.q-field--error input, .q-field--error textarea')?.focus()
    return
  }
  emit('submit')
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped src="../../css/asset-form-layout.css"></style>
