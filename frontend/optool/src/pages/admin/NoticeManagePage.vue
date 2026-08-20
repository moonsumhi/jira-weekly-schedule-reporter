<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6 col">공지사항 관리</div>
      <q-btn icon="add" label="공지 등록" color="primary" @click="openCreate" />
    </div>

    <q-table
      :rows="notices"
      :columns="columns"
      row-key="id"
      flat
      bordered
      :loading="loading"
      no-data-label="등록된 공지사항이 없습니다"
    >
      <template #body-cell-isActive="{ row }">
        <q-td class="text-center">
          <q-badge :color="isCurrentlyShown(row) ? 'positive' : (row.isActive ? 'blue-6' : 'grey-6')">
            {{ isCurrentlyShown(row) ? '노출 중' : (row.isActive ? '대기' : '비활성') }}
          </q-badge>
        </q-td>
      </template>
      <template #body-cell-actions="{ row }">
        <q-td class="text-right">
          <q-btn flat dense icon="edit" size="sm" @click="openEdit(row)" />
          <q-btn flat dense icon="delete" color="negative" size="sm" @click="confirmDelete(row)" />
        </q-td>
      </template>
    </q-table>

    <!-- 등록 / 수정 다이얼로그 -->
    <q-dialog v-model="dialog" persistent @show="onDialogShow">
      <q-card style="min-width: 560px; max-width: 90vw">
        <q-card-section class="text-h6">{{ editTarget ? '공지사항 수정' : '공지 등록' }}</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input ref="titleInputRef" v-model="form.title" label="제목 *" outlined dense />
          <MarkdownEditor v-model="form.content" label="내용" required :rows="8" />
          <div class="row q-col-gutter-md">
            <div class="col-6">
              <q-input v-model="form.startDate" label="시작일 *" outlined dense type="date" />
            </div>
            <div class="col-6">
              <q-input v-model="form.endDate" label="종료일 *" outlined dense type="date" />
            </div>
          </div>
          <q-toggle v-model="form.isActive" label="활성화 (팝업으로 노출)" color="positive" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" :label="editTarget ? '수정' : '등록'" :loading="saving" @click="submit" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import type { QInput } from 'quasar'
import { noticeService, type NoticeOut } from 'src/services/notices'
import MarkdownEditor from 'src/components/MarkdownEditor.vue'

const $q = useQuasar()

const notices = ref<NoticeOut[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editTarget = ref<NoticeOut | null>(null)
const form = ref({ title: '', content: '', startDate: '', endDate: '', isActive: true })
const titleInputRef = ref<QInput | null>(null)

// autofocus 대신 다이얼로그 진입 트랜지션이 끝난 뒤 한 번만 포커스한다
// (동시에 걸리면 한글 IME 조합이 깨지는 문제 방지).
function onDialogShow() {
  void nextTick(() => titleInputRef.value?.focus())
}

const columns = [
  { name: 'title', label: '제목', field: 'title', align: 'left' as const },
  { name: 'period', label: '게시 기간', field: (row: NoticeOut) => `${row.startDate} ~ ${row.endDate}`, align: 'center' as const },
  { name: 'isActive', label: '상태', field: 'isActive', align: 'center' as const },
  { name: 'createdBy', label: '등록자', field: 'createdBy', align: 'left' as const },
  { name: 'actions', label: '', field: 'id', align: 'right' as const },
]

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function isCurrentlyShown(row: NoticeOut) {
  const today = todayStr()
  return row.isActive && row.startDate <= today && row.endDate >= today
}

async function load() {
  loading.value = true
  try {
    notices.value = await noticeService.list()
  } catch {
    $q.notify({ type: 'negative', message: '공지사항을 불러오는데 실패했습니다' })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editTarget.value = null
  const today = todayStr()
  form.value = { title: '', content: '', startDate: today, endDate: today, isActive: true }
  dialog.value = true
}

function openEdit(row: NoticeOut) {
  editTarget.value = row
  form.value = { title: row.title, content: row.content, startDate: row.startDate, endDate: row.endDate, isActive: row.isActive }
  dialog.value = true
}

async function submit() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    $q.notify({ type: 'warning', message: '제목과 내용을 입력해주세요.', position: 'top' })
    return
  }
  if (!form.value.startDate || !form.value.endDate) {
    $q.notify({ type: 'warning', message: '게시 기간을 입력해주세요.', position: 'top' })
    return
  }
  if (form.value.startDate > form.value.endDate) {
    $q.notify({ type: 'warning', message: '시작일이 종료일보다 늦을 수 없습니다.', position: 'top' })
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.value.title.trim(),
      content: form.value.content,
      start_date: form.value.startDate,
      end_date: form.value.endDate,
      is_active: form.value.isActive,
    }
    if (editTarget.value) {
      await noticeService.patch(editTarget.value.id, payload)
    } else {
      await noticeService.create(payload)
    }
    dialog.value = false
    await load()
  } catch {
    $q.notify({ type: 'negative', message: editTarget.value ? '수정에 실패했습니다' : '등록에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: NoticeOut) {
  $q.dialog({
    title: '공지사항 삭제',
    message: `'${row.title}' 공지사항을 삭제하시겠습니까?`,
    cancel: true,
  }).onOk(() => { void (async () => { await noticeService.remove(row.id); await load() })() })
}

onMounted(() => { void load() })
</script>
