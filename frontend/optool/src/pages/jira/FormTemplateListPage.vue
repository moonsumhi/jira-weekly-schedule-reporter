<template>
  <q-page padding>
    <div class="text-h5 q-mb-md">폼 템플릿</div>

    <q-inner-loading :showing="loading" />

    <q-list bordered separator v-if="!loading">
      <q-item
        v-for="(tmpl, idx) in templates"
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
              :disable="idx === templates.length - 1 || reordering"
              @click="moveDown(idx)"
            />
          </div>
        </q-item-section>
      </q-item>

      <q-item v-if="templates.length === 0">
        <q-item-section>
          <q-item-label class="text-grey">템플릿이 없습니다.</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { formTemplateService, type FormTemplate } from 'src/services/formTemplates'

const $q = useQuasar()
const templates = ref<FormTemplate[]>([])
const loading = ref(true)
const reordering = ref(false)

onMounted(async () => {
  try {
    templates.value = await formTemplateService.list()
  } finally {
    loading.value = false
  }
})

async function moveUp(idx: number) {
  if (idx === 0) return
  await swapOrder(idx, idx - 1)
}

async function moveDown(idx: number) {
  if (idx === templates.length - 1) return
  await swapOrder(idx, idx + 1)
}

async function swapOrder(a: number, b: number) {
  reordering.value = true
  try {
    const aOrder = a + 1
    const bOrder = b + 1
    await Promise.all([
      formTemplateService.patchSortOrder(templates.value[a].id, bOrder),
      formTemplateService.patchSortOrder(templates.value[b].id, aOrder),
    ])
    // swap in local list
    const tmp = templates.value[a]
    templates.value[a] = { ...templates.value[b], sort_order: aOrder }
    templates.value[b] = { ...tmp, sort_order: bOrder }
  } catch {
    $q.notify({ type: 'negative', message: '순서 변경 실패' })
  } finally {
    reordering.value = false
  }
}
</script>
