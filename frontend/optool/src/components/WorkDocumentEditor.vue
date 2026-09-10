<template>
  <q-dialog :model-value="modelValue" maximized :persistent="saving" transition-show="slide-up" transition-hide="slide-down"
    @update:model-value="emit('update:modelValue', $event)" @hide="emit('hide')">
    <q-card class="work-document">
      <header class="document-topbar">
        <q-btn flat round dense icon="arrow_back" aria-label="작성 화면 닫기" :disable="saving" @click="close" />
        <div class="document-breadcrumb"><span>작업 관리</span><q-icon name="chevron_right" size="16px" /><strong>{{ title }}</strong></div>
        <q-space /><span class="reading-badge"><span />{{ isEdit ? '문서 수정' : '새 문서 작성' }}</span>
        <q-btn flat round dense icon="close" aria-label="작성 화면 닫기" :disable="saving" @click="close" />
      </header>
      <div class="document-layout">
        <aside class="document-sidebar">
          <div class="sidebar-label">문서 목차 <span>{{ sections.length }}</span></div>
          <nav class="document-nav" aria-label="작성 문서 목차">
            <button v-for="(section, index) in sections" :key="index" type="button"
              :class="['document-nav-item', { active: activeSection === index }]"
              :aria-current="activeSection === index ? 'location' : undefined" @click="goToSection(index)">
              <span class="nav-number">{{ String(index + 1).padStart(2, '0') }}</span><span>{{ section.title }}</span>
            </button>
          </nav>
          <div class="sidebar-metadata"><q-icon name="edit_note" size="24px" /><div class="sidebar-meta-title">{{ isEdit ? '문서를 수정하고 있습니다' : '새 문서를 작성하고 있습니다' }}</div>
            <p>필수 항목을 입력한 뒤 하단의 저장 버튼을 눌러 주세요.</p>
            <span>{{ dirty ? '저장하지 않은 변경사항이 있습니다.' : '변경사항이 없습니다.' }}</span>
          </div>
        </aside>
        <main ref="scrollArea" class="document-scroll" @scroll="updateActiveSection">
          <article class="document-paper">
            <header class="document-hero"><div class="document-kind"><q-icon name="edit_note" size="16px" />{{ isEdit ? '문서 수정' : '새 문서' }}</div>
              <h1>{{ title }}</h1><div class="document-byline">별표(*)가 표시된 항목은 필수 입력입니다.</div>
              <p v-if="syncMarkdown" class="text-grey-7">원본 양식을 수정하고 있습니다. 저장하면 Markdown 보기와 .md 파일에도 반영됩니다.</p>
            </header>
            <fieldset :disabled="saving" class="editor-fieldset">
              <section v-for="(section, index) in sections" :key="index" :data-section-index="index" class="document-section">
                <div class="section-heading"><span class="section-number">{{ String(index + 1).padStart(2, '0') }}</span><h2>{{ section.title }}</h2></div>
                <slot name="section" :section="section" />
              </section>
            </fieldset>
            <div class="document-end"><span />입력 내용 확인 후 저장해 주세요<span /></div>
          </article>
        </main>
      </div>
      <div v-if="$slots.images" class="editor-image-panel"><slot name="images" /></div>
      <footer class="document-footer"><span class="footer-note"><q-icon name="edit_note" />{{ dirty ? '저장하지 않은 변경사항' : title }}</span><q-space />
        <q-btn flat label="취소" :disable="saving" @click="close" />
        <q-btn unelevated color="primary" icon="save" :label="isEdit ? '수정 저장' : '저장'" :loading="saving" @click="emit('save')" />
      </footer>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { FormSection } from 'src/services/formTemplates'
const props = defineProps<{ modelValue: boolean; title: string; sections: FormSection[]; isEdit: boolean; saving: boolean; dirty: boolean; syncMarkdown?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; hide: []; save: [] }>()
defineSlots<{ section(props: { section: FormSection }): unknown; images(): unknown }>()
const scrollArea = ref<HTMLElement | null>(null)
const activeSection = ref(0)
function close() { if (!props.saving) emit('update:modelValue', false) }
function goToSection(index: number) {
  scrollArea.value?.querySelector<HTMLElement>(`[data-section-index="${index}"]`)?.scrollIntoView({
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start',
  })
  activeSection.value = index
}
function updateActiveSection() {
  if (!scrollArea.value) return
  const top = scrollArea.value.getBoundingClientRect().top + 90
  let current = 0
  scrollArea.value.querySelectorAll<HTMLElement>('[data-section-index]').forEach((element, index) => {
    if (element.getBoundingClientRect().top <= top) current = index
  })
  activeSection.value = current
}
watch(() => props.modelValue, async (open) => {
  if (!open) return
  activeSection.value = 0
  await nextTick()
  if (scrollArea.value) scrollArea.value.scrollTop = 0
})
</script>

<style scoped src="./workDocument.css"></style>
<style scoped>
.editor-fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.editor-image-panel { flex-shrink: 0; max-height: 24vh; overflow: auto; }
.sidebar-metadata p { line-height: 1.8; }
</style>
