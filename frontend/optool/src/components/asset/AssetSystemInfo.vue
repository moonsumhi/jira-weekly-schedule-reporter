<template>
  <div ref="root" class="system-info hardware-info" aria-label="하드웨어 정보">
    <nav ref="toc" class="hardware-toc" aria-label="하드웨어 정보 목차">
      <button v-for="item in navigation" :key="item.key" type="button" class="hardware-toc-link"
        :class="{ 'hardware-toc-link--active': activeSection === item.key }"
        :aria-current="activeSection === item.key ? 'location' : undefined"
        @click="jumpToSection(item.key)">{{ item.label }}</button>
    </nav>
    <q-card-section class="q-pb-sm" data-hardware-section="summary" tabindex="-1" aria-label="하드웨어 요약">
      <div class="text-subtitle2 q-mb-sm">하드웨어 요약</div>
      <div class="hardware-summary">
        <div v-for="item in summary" :key="item.label" class="hardware-summary-item">
          <span class="text-caption text-grey-6">{{ item.label }}</span><strong>{{ item.value }}</strong>
        </div>
      </div>
    </q-card-section>
    <q-card-section v-for="(section, sectionIndex) in systemInfoSections" :key="section.title" class="q-py-sm"
      :data-system-section="section.key" :data-hardware-section="String(sectionIndex)" tabindex="-1" :aria-label="section.title">
      <template v-if="section.multiple">
        <div class="section-title-row">
          <span class="section-title">{{ section.title }}</span>
          <q-badge outline color="primary" class="q-ml-sm">{{ model[section.key].length }}개</q-badge>
          <q-space />
          <q-btn v-if="editing" flat dense color="primary" icon="add" :label="`${section.itemLabel} 추가`"
            :disable="disabled || model[section.key].length >= section.limit" @click="addEntry(section)" />
        </div>
        <div class="section-divider" />
        <template v-if="editing && model[section.key].length">
          <div v-for="(entry, index) in model[section.key]" :key="`${section.key}-${index}`"
            class="system-entry hardware-edit-entry q-py-md" :data-system-entry="`${section.key}.${index}`">
            <div class="row items-center q-mb-md">
              <strong>{{ section.itemLabel }} {{ index + 1 }}</strong><q-space />
              <q-btn v-if="editing" flat dense color="negative" icon="remove_circle_outline" label="삭제"
                :aria-label="`${section.itemLabel} ${index + 1} 삭제`" :disable="disabled" @click="removeEntry(section.key, index)" />
            </div>
            <AssetSystemInfoFields :fields="section.fields" :rows="section.rows" :values="entry" :prefix="`${section.key}.${index}`"
              :editing="editing" :disabled="disabled" @change="value => updateEntry(section.key, index, value)" />
          </div>
        </template>
        <q-markup-table v-else-if="model[section.key].length" flat bordered wrap-cells class="hardware-table q-my-sm">
          <thead><tr>
            <th v-for="column in section.columns" :key="column" class="text-left">{{ columnLabel(section, column) }}</th>
            <th class="text-center">상세</th>
          </tr></thead>
          <tbody>
            <template v-for="(entry, index) in model[section.key]" :key="`${section.key}-${index}`">
              <tr class="hardware-list-row" @click="toggleEntry(section.key, index)">
                <td v-for="column in section.columns" :key="column" :title="String(entry[column] ?? '')">{{ columnValue(section, entry, column) }}</td>
                <td class="text-center"><q-btn flat round dense size="sm" :icon="isExpanded(section.key, index) ? 'expand_less' : 'expand_more'"
                  :aria-expanded="isExpanded(section.key, index)" :aria-label="`${section.itemLabel} ${index + 1} 상세 ${isExpanded(section.key, index) ? '접기' : '펼치기'}`"
                  @click.stop="toggleEntry(section.key, index)" /></td>
              </tr>
              <tr v-if="isExpanded(section.key, index)">
                <td :colspan="section.columns.length + 1" class="hardware-detail-cell">
                  <div class="system-entry q-pa-sm" :data-system-entry="`${section.key}.${index}`">
                    <div class="row items-center q-mb-md">
                      <strong>{{ section.itemLabel }} 상세 · {{ entry.slot || entry.name || entry.mountPoint || index + 1 }}</strong>
                      <q-space />
                      <q-btn v-if="editing" flat dense color="negative" icon="remove_circle_outline" label="삭제"
                        :aria-label="`${section.itemLabel} ${index + 1} 삭제`" :disable="disabled" @click="removeEntry(section.key, index)" />
                    </div>
                    <AssetSystemInfoFields :fields="section.fields" :rows="section.rows" :values="entry" :prefix="`${section.key}.${index}`"
                      :editing="editing" :disabled="disabled" @change="value => updateEntry(section.key, index, value)" />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </q-markup-table>
        <div v-else class="text-grey-6 text-caption q-py-md">
          등록된 {{ section.itemLabel }} 정보가 없습니다.<template v-if="editing"> '{{ section.itemLabel }} 추가'로 입력하세요.</template>
        </div>
      </template>
      <q-expansion-item v-else default-opened dense header-class="q-px-none" class="hardware-section">
        <template #header><span class="section-title q-py-sm">{{ section.title }}</span></template>
        <div class="section-divider" />
        <AssetSystemInfoFields class="q-mt-md q-mb-sm" :fields="section.fields" :rows="section.rows" :values="model[section.key]"
          :prefix="section.key" :editing="editing" :disabled="disabled" @change="value => updateSection(section.key, value)" />
      </q-expansion-item>
    </q-card-section>
    <q-card-section class="q-py-sm" data-hardware-section="notes" tabindex="-1" aria-label="기타 정보">
      <div class="section-title-row"><span class="section-title">기타 정보</span></div>
      <div class="section-divider" />
      <div class="form-field q-mt-md q-mb-md" data-system-field="notes">
        <div class="field-label">비고</div>
        <q-input v-if="editing" :model-value="model.notes" type="textarea" autogrow borderless dense class="field-input"
          aria-label="하드웨어 정보 비고" :maxlength="4000" :disable="disabled" @update:model-value="value => model = { ...model, notes: String(value || '') }" />
        <div v-else class="detail-value">{{ model.notes || '-' }}</div>
      </div>
    </q-card-section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AssetSystemInfoFields from './AssetSystemInfoFields.vue'
import { emptySystemInfoEntry, formatHardwareBytes, systemInfoSections, type SystemInformation, type SystemInfoSection, type SystemInfoValues, type SystemInfoListKey, type SystemInfoSingleKey } from 'src/types/assetSystemInfo'
const model = defineModel<SystemInformation>({ required: true })
defineProps<{ editing: boolean; disabled: boolean }>()
const expanded = ref(new Set<string>())
const root = ref<HTMLElement | null>(null)
const toc = ref<HTMLElement | null>(null)
const activeSection = ref('summary')
const navigation = [
  { key: 'summary', label: '요약' },
  ...systemInfoSections.map((section, index) => ({ key: String(index), label: section.title.replace(/ (상세|목록|정보)$/, '') })),
  { key: 'notes', label: '기타' },
]
let scrollContainer: HTMLElement | null = null
let resizeObserver: ResizeObserver | null = null
let scrollFrame = 0
let selectedDestination: string | null = null
function updateActiveSection() {
  if (!root.value || !toc.value || !scrollContainer) return
  if (selectedDestination !== null) {
    activeSection.value = selectedDestination
    return
  }
  const threshold = toc.value.getBoundingClientRect().bottom + 16
  let current = 'summary'
  for (const element of root.value.querySelectorAll<HTMLElement>('[data-hardware-section]')) {
    if (element.getBoundingClientRect().top <= threshold) current = element.dataset.hardwareSection || current
  }
  activeSection.value = current
}
function resumeScrollTracking() {
  selectedDestination = null
  scheduleScrollUpdate()
}
function onScrollKey(event: KeyboardEvent) {
  if ((event.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable="true"]')) return
  if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) resumeScrollTracking()
}
function onScrollbarPointer(event: PointerEvent) {
  if (event.target === scrollContainer) resumeScrollTracking()
}
function scheduleScrollUpdate() {
  if (scrollFrame) return
  scrollFrame = requestAnimationFrame(() => { scrollFrame = 0; updateActiveSection() })
}
function jumpToSection(key: string) {
  const element = root.value?.querySelector<HTMLElement>(`[data-hardware-section="${key}"]`)
  if (!element || !scrollContainer || !toc.value) return
  selectedDestination = key
  activeSection.value = key
  const top = element.getBoundingClientRect().top - scrollContainer.getBoundingClientRect().top
    + scrollContainer.scrollTop - toc.value.offsetHeight - 12
  scrollContainer.scrollTo({ top: Math.max(0, top), behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  element.focus({ preventScroll: true })
}
onMounted(() => {
  // Quasar inserts a scrollable .q-panel wrapper inside .q-tab-panels.
  // Scroll the nearest scroll surface, rather than the outer tab container.
  scrollContainer = root.value?.closest<HTMLElement>('.scroll, .scroll-y, .overflow-auto') || null
  scrollContainer?.addEventListener('scroll', scheduleScrollUpdate, { passive: true })
  scrollContainer?.addEventListener('wheel', resumeScrollTracking, { passive: true })
  scrollContainer?.addEventListener('touchmove', resumeScrollTracking, { passive: true })
  scrollContainer?.addEventListener('keydown', onScrollKey)
  scrollContainer?.addEventListener('pointerdown', onScrollbarPointer)
  resizeObserver = new ResizeObserver(scheduleScrollUpdate)
  if (root.value) resizeObserver.observe(root.value)
  if (toc.value) resizeObserver.observe(toc.value)
  if (scrollContainer) resizeObserver.observe(scrollContainer)
  scheduleScrollUpdate()
})
onBeforeUnmount(() => {
  scrollContainer?.removeEventListener('scroll', scheduleScrollUpdate)
  scrollContainer?.removeEventListener('wheel', resumeScrollTracking)
  scrollContainer?.removeEventListener('touchmove', resumeScrollTracking)
  scrollContainer?.removeEventListener('keydown', onScrollKey)
  scrollContainer?.removeEventListener('pointerdown', onScrollbarPointer)
  resizeObserver?.disconnect()
  if (scrollFrame) cancelAnimationFrame(scrollFrame)
})
const summary = computed(() => {
  const cpu = model.value.cpu
  const cores = cpu.coreCount ?? (cpu.sockets != null && cpu.coresPerSocket != null ? Number(cpu.sockets) * Number(cpu.coresPerSocket) : null)
  return [
    { label: 'CPU 모델', value: cpu.model || '-' },
    { label: '전체 코어 수', value: cores == null ? '-' : `${cores}개` },
    { label: '메모리 총 용량', value: model.value.memory.totalGb == null ? '-' : `${model.value.memory.totalGb} GB` },
    { label: '디스크 수', value: `${model.value.disks.length}개` },
  ]
})
function updateSection(key: SystemInfoSingleKey, value: SystemInfoValues) {
  model.value = { ...model.value, [key]: value }
}
function updateEntry(key: SystemInfoListKey, index: number, value: SystemInfoValues) {
  model.value = { ...model.value, [key]: model.value[key].map((row, i) => i === index ? value : row) }
}
function removeEntry(key: SystemInfoListKey, index: number) {
  model.value = { ...model.value, [key]: model.value[key].filter((_, i) => i !== index) }
  expanded.value.clear()
}
function isExpanded(key: SystemInfoListKey, index: number) { return expanded.value.has(`${key}.${index}`) }
function toggleEntry(key: SystemInfoListKey, index: number) {
  const id = `${key}.${index}`
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}
function columnLabel(section: SystemInfoSection, key: string) {
  const field = section.fields.find(field => field.key === key)
  if (section.key === 'disks' && key === 'sizeBytes') return 'SIZE'
  return (field?.label || key).replace(/\n/g, ' ')
}
function columnValue(section: SystemInfoSection, entry: SystemInfoValues, key: string) {
  const value = entry[key]
  if (value === null || value === undefined || value === '') return key === 'sizeBytes' && section.key === 'disks' ? entry.capacity || '-' : '-'
  return section.key === 'disks' && key === 'sizeBytes' ? formatHardwareBytes(value) : value
}
async function addEntry(section: SystemInfoSection) {
  if (!section.multiple || model.value[section.key].length >= section.limit) return
  const index = model.value[section.key].length
  model.value = { ...model.value, [section.key]: [...model.value[section.key], emptySystemInfoEntry(section.fields)] }
  expanded.value.add(`${section.key}.${index}`)
  await nextTick()
  document.querySelector<HTMLInputElement>(`[data-system-entry="${section.key}.${index}"] input`)?.focus()
}
</script>

<style scoped src="../../css/asset-detail-fields.css"></style>
<style scoped>
.hardware-toc { position: sticky; top: 0; z-index: 2; display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 16px; background: #fff; border-bottom: 1px solid #cbd5e1; box-shadow: 0 2px 5px #0000000a; }
.hardware-toc-link { border: 1px solid transparent; border-radius: 6px; background: transparent; color: #52627a; font: inherit; font-size: 12px; min-height: 32px; padding: 5px 8px; cursor: pointer; }
.hardware-toc-link:hover { background: #edf3fa; }
.hardware-toc-link--active { background: #e5efff; color: #1856a2; border-color: #a6c8f0; font-weight: 600; }
.hardware-toc-link:focus-visible { outline: 2px solid var(--q-primary); outline-offset: 1px; }
:global(body.body--dark .hardware-toc) { background: #182334; border-color: #475569; }
:global(body.body--dark .hardware-toc-link) { color: #cbd5e1; }
:global(body.body--dark .hardware-toc-link:hover) { background: #26364c; }
:global(body.body--dark .hardware-toc-link--active) { background: #234c76; color: #e5f2ff; border-color: #6b9dd1; }
.hardware-table { max-width: 100%; }
.hardware-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.hardware-summary-item { display: flex; align-items: baseline; gap: 10px; padding: 10px 12px; border: 1px solid #9aa9bc55; border-radius: 8px; overflow-wrap: anywhere; }
.hardware-summary-item > span { flex: 0 0 auto; }
.hardware-summary-item strong { flex: 1 1 0; min-width: 0; font-size: 13px; }
.hardware-edit-entry + .hardware-edit-entry { border-top: 1px solid #9aa9bc55; }
.hardware-table th { min-width: 100px; font-size: 11px; white-space: normal; }
.hardware-table td { max-width: 240px; overflow-wrap: anywhere; white-space: normal; }
.hardware-list-row { cursor: pointer; }
.hardware-detail-cell { padding: 12px !important; }
.detail-value { white-space: pre-line; }
</style>
