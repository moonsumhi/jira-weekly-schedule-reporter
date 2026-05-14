<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">폼 템플릿</div>
      <q-toggle
        v-model="showDeleted"
        label="삭제된 항목 보기"
        dense
        color="negative"
        @update:model-value="load"
      />
    </div>

    <q-inner-loading :showing="loading" />

    <q-list bordered separator v-if="!loading">
      <q-item
        v-for="(tmpl, idx) in activeTemplates"
        :key="tmpl.id"
        clickable
        :to="`/jira/forms/${tmpl.id}`"
      >
        <q-item-section avatar>
          <q-icon name="fa-solid fa-file-alt" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ tmpl.title }}</q-item-label>
          <q-item-label caption>{{ tmpl.jira_issue_key }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-item-label caption>{{ tmpl.menu }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <div class="row items-center q-gutter-xs" @click.prevent.stop>
            <q-btn
              dense flat icon="arrow_upward" size="sm"
              :disable="idx === 0 || reordering"
              @click="moveUp(idx)"
            />
            <q-btn
              dense flat icon="arrow_downward" size="sm"
              :disable="idx === activeTemplates.length - 1 || reordering"
              @click="moveDown(idx)"
            />
            <q-btn
              dense flat icon="delete" size="sm" color="negative"
              @click="confirmDelete(tmpl)"
            />
          </div>
        </q-item-section>
      </q-item>

      <!-- 삭제된 항목 -->
      <template v-if="showDeleted">
        <q-separator v-if="deletedTemplates.length > 0 && activeTemplates.length > 0" spaced />
        <q-item
          v-for="tmpl in deletedTemplates"
          :key="tmpl.id"
          class="deleted-item"
          v-ripple="false"
        >
          <q-item-section avatar>
            <q-icon name="fa-solid fa-file-alt" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-grey-5 text-strike">{{ tmpl.title }}</q-item-label>
            <q-item-label caption class="text-grey-5">{{ tmpl.jira_issue_key }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-badge color="grey-4" text-color="grey-7" label="삭제됨" />
          </q-item-section>
          <q-item-section side>
            <div class="row items-center q-gutter-xs" @click.prevent.stop>
              <q-btn
                dense flat icon="restore" size="sm" color="positive"
                label="복원"
                @click="restoreTemplate(tmpl)"
              />
            </div>
          </q-item-section>
        </q-item>
      </template>

      <q-item v-if="activeTemplates.length === 0 && (!showDeleted || deletedTemplates.length === 0)">
        <q-item-section>
          <q-item-label class="text-grey">템플릿이 없습니다.</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { formTemplateService, type FormTemplate } from 'src/services/formTemplates'

const $q = useQuasar()
const templates = ref<FormTemplate[]>([])
const loading = ref(true)
const reordering = ref(false)
const showDeleted = ref(false)

const activeTemplates = computed(() => templates.value.filter((t) => !t.is_deleted))
const deletedTemplates = computed(() => templates.value.filter((t) => t.is_deleted))

async function load() {
  loading.value = true
  try {
    templates.value = await formTemplateService.list(undefined, showDeleted.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function moveUp(idx: number) {
  if (idx === 0) return
  await swapOrder(idx, idx - 1)
}

async function moveDown(idx: number) {
  if (idx === activeTemplates.value.length - 1) return
  await swapOrder(idx, idx + 1)
}

async function swapOrder(a: number, b: number) {
  reordering.value = true
  try {
    const aOrder = a + 1
    const bOrder = b + 1
    const tmplA = activeTemplates.value[a]
    const tmplB = activeTemplates.value[b]
    if (!tmplA || !tmplB) return
    await Promise.all([
      formTemplateService.patchSortOrder(tmplA.id, bOrder),
      formTemplateService.patchSortOrder(tmplB.id, aOrder),
    ])
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '순서 변경 실패' })
  } finally {
    reordering.value = false
  }
}

function confirmDelete(tmpl: FormTemplate) {
  $q.dialog({
    title: '템플릿 삭제',
    message: `"${tmpl.title}" 템플릿을 삭제하시겠습니까?`,
    cancel: { label: '취소', flat: true },
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      try {
        await formTemplateService.delete(tmpl.id)
        $q.notify({ type: 'positive', message: '삭제되었습니다' })
        await load()
      } catch {
        $q.notify({ type: 'negative', message: '삭제 실패' })
      }
    })()
  })
}

async function restoreTemplate(tmpl: FormTemplate) {
  try {
    await formTemplateService.restore(tmpl.id)
    $q.notify({ type: 'positive', message: '복원되었습니다' })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '복원 실패' })
  }
}
</script>

<style scoped>
.deleted-item {
  background-color: #fafafa;
  opacity: 0.75;
}
.text-strike {
  text-decoration: line-through;
}
</style>
