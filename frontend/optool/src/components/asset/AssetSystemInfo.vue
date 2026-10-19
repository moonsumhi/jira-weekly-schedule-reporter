<template>
  <div class="system-info" aria-label="시스템 정보">
    <q-card-section v-for="section in systemInfoSections" :key="section.key" class="q-py-sm" :data-system-section="section.key">
      <div class="section-title-row">
        <span class="section-title">{{ section.title }}</span>
        <q-space />
        <q-btn v-if="editing && section.multiple" flat dense color="primary" icon="add" :label="`${section.itemLabel} 추가`"
          :disable="disabled || model[section.key].length >= section.limit" @click="addEntry(section)" />
      </div>
      <div class="section-divider" />
      <template v-if="section.multiple">
        <div v-for="(entry, index) in model[section.key]" :key="`${section.key}-${index}`" class="system-entry q-py-md"
          :data-system-entry="`${section.key}.${index}`">
          <div class="row items-center q-mb-sm">
            <span class="entry-title">{{ section.itemLabel }} {{ index + 1 }}<template v-if="entry.name || entry.slot"> · {{ entry.name || entry.slot }}</template></span>
            <q-space />
            <q-btn v-if="editing" flat dense color="negative" icon="remove_circle_outline" label="삭제"
              :aria-label="`${section.itemLabel} ${index + 1} 삭제`" :disable="disabled" @click="removeEntry(section.key, index)" />
          </div>
          <AssetSystemInfoFields :fields="section.fields" :values="entry" :prefix="`${section.key}.${index}`"
            :editing="editing" :disabled="disabled" @change="value => updateEntry(section.key, index, value)" />
        </div>
        <div v-if="!model[section.key].length" class="text-grey-6 text-caption q-py-md">
          등록된 {{ section.itemLabel }} 정보가 없습니다.<template v-if="editing"> ‘{{ section.itemLabel }} 추가’로 입력하세요.</template>
        </div>
      </template>
      <AssetSystemInfoFields v-else class="q-mt-md q-mb-sm" :fields="section.fields" :values="model[section.key]"
        :prefix="section.key" :editing="editing" :disabled="disabled" @change="value => updateSection(section.key, value)" />
    </q-card-section>
    <q-card-section class="q-py-sm">
      <div class="section-title-row"><span class="section-title">기타 정보</span></div>
      <div class="section-divider" />
      <div class="form-field q-mt-md q-mb-md" data-system-field="notes">
        <div class="field-label">비고</div>
        <q-input v-if="editing" :model-value="model.notes" type="textarea" autogrow borderless dense class="field-input"
          aria-label="시스템 정보 비고" :maxlength="4000" :disable="disabled" @update:model-value="value => model = { ...model, notes: String(value || '') }" />
        <div v-else class="detail-value">{{ model.notes || '-' }}</div>
      </div>
    </q-card-section>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'
import AssetSystemInfoFields from './AssetSystemInfoFields.vue'
import { emptySystemInfoEntry, systemInfoSections, type SystemInformation, type SystemInfoSection, type SystemInfoValues } from 'src/types/assetSystemInfo'
const model = defineModel<SystemInformation>({ required: true })
defineProps<{ editing: boolean; disabled: boolean }>()
function updateSection(key: 'cpu' | 'memory' | 'hardware', value: SystemInfoValues) {
  model.value = { ...model.value, [key]: value }
}
function updateEntry(key: 'memoryModules' | 'disks' | 'networkInterfaces', index: number, value: SystemInfoValues) {
  model.value = { ...model.value, [key]: model.value[key].map((row, i) => i === index ? value : row) }
}
function removeEntry(key: 'memoryModules' | 'disks' | 'networkInterfaces', index: number) {
  model.value = { ...model.value, [key]: model.value[key].filter((_, i) => i !== index) }
}
async function addEntry(section: SystemInfoSection) {
  if (!section.multiple || model.value[section.key].length >= section.limit) return
  const index = model.value[section.key].length
  model.value = { ...model.value, [section.key]: [...model.value[section.key], emptySystemInfoEntry(section.fields)] }
  await nextTick()
  document.querySelector<HTMLInputElement>(`[data-system-entry="${section.key}.${index}"] input`)?.focus()
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.system-entry + .system-entry { border-top: 1px solid rgba(0, 0, 0, .08); }
.entry-title { color: #555; font-size: 12px; font-weight: 500; overflow-wrap: anywhere; }
.detail-value { white-space: pre-line; }
</style>
