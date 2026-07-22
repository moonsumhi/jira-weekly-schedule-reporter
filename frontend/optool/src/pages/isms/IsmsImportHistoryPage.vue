<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6 col">가져오기 이력</div>
    </div>

    <q-card flat bordered>
      <q-table
        :rows="rows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        flat
        :rows-per-page-options="[10, 20, 50]"
      >
        <template #body-cell-actions="props">
          <q-td :props="props" class="text-center">
            <q-btn
              flat dense size="sm" color="negative" label="롤백"
              :disable="!props.row.canRollback"
              @click="confirmRollback(props.row)"
            >
              <q-tooltip v-if="!props.row.canRollback">이미 롤백되었습니다</q-tooltip>
            </q-btn>
          </q-td>
        </template>
      </q-table>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { listImportHistory, rollbackImport, type ImportLog } from 'src/services/isms/vulnerability'

const $q = useQuasar()
const rows = ref<ImportLog[]>([])
const loading = ref(false)

const columns = [
  { name: 'createdAt', label: 'Import 일시', field: 'createdAt', align: 'left' as const },
  { name: 'recordsBefore', label: 'Import 전 건수', field: 'recordsBefore', align: 'center' as const },
  { name: 'inserted', label: '신규', field: 'inserted', align: 'center' as const },
  { name: 'updated', label: '업데이트', field: 'updated', align: 'center' as const },
  { name: 'recordsAfter', label: 'Import 후 건수', field: 'recordsAfter', align: 'center' as const },
  { name: 'uploaderEmail', label: '업로더', field: 'uploaderEmail', align: 'left' as const },
  { name: 'actions', label: '', field: 'actions', align: 'center' as const },
]

async function load() {
  loading.value = true
  try {
    rows.value = await listImportHistory()
  } catch {
    $q.notify({ type: 'negative', message: '이력을 불러오는데 실패했습니다.' })
  } finally {
    loading.value = false
  }
}

function confirmRollback(row: ImportLog) {
  $q.dialog({
    title: '롤백 확인',
    message: `${row.createdAt ?? ''} 임포트를 롤백하시겠습니까?<br>신규 등록된 ${row.inserted}건은 삭제되고, 수정된 ${row.updated}건은 임포트 전 상태로 복원됩니다.`,
    html: true,
    cancel: { label: '취소', flat: true },
    ok: { label: '롤백 실행', color: 'negative' },
  }).onOk(() => {
    void (async () => {
      try {
        const result = await rollbackImport(row.id)
        $q.notify({ type: 'positive', message: `롤백 완료: 복원 ${result.restored}건, 삭제 ${result.deleted}건` })
        await load()
      } catch {
        $q.notify({ type: 'negative', message: '롤백에 실패했습니다.' })
      }
    })()
  })
}

onMounted(load)
</script>
