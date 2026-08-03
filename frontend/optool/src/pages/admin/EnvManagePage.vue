<template>
  <q-page padding>
    <div class="row items-center q-mb-md">
      <div class="text-h6 col">환경설정 관리</div>
    </div>

    <div class="row q-col-gutter-md">
      <!-- 좌측: 카테고리 목록 -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section class="row items-center q-py-sm">
            <div class="text-subtitle2 col">카테고리</div>
            <q-btn flat dense round icon="add" size="sm" @click="openCreateCategory" />
          </q-card-section>
          <q-separator />
          <q-list separator>
            <q-item
              v-for="c in categories" :key="c.id"
              clickable
              :active="selected?.id === c.id"
              active-class="bg-blue-1"
              @click="selected = c"
            >
              <q-item-section>
                <q-item-label>{{ c.label }}</q-item-label>
                <q-item-label caption>{{ c.key }} · {{ c.items.length }}개</q-item-label>
              </q-item-section>
              <q-item-section v-if="c.isSystem" side>
                <q-icon name="lock" size="16px" color="grey-5">
                  <q-tooltip>시스템 기본 카테고리 (삭제 불가)</q-tooltip>
                </q-icon>
              </q-item-section>
            </q-item>
            <q-item v-if="!loading && categories.length === 0">
              <q-item-section class="text-grey">등록된 카테고리가 없습니다.</q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <!-- 우측: 선택된 카테고리의 항목 관리 -->
      <div class="col-12 col-md-8">
        <q-card v-if="selected" flat bordered>
          <q-card-section class="row items-center q-py-sm">
            <div class="text-subtitle2 col">{{ selected.label }} 항목</div>
            <q-btn
              v-if="!selected.isSystem"
              flat dense round icon="edit" size="sm" class="q-mr-xs"
              @click="openEditCategory(selected)"
            />
            <q-btn
              v-if="!selected.isSystem"
              flat dense round icon="delete" color="negative" size="sm" class="q-mr-sm"
              @click="confirmDeleteCategory(selected)"
            />
            <q-btn flat dense label="항목 추가" icon="add" color="primary" @click="openCreateItem" />
          </q-card-section>
          <q-separator />
          <q-list separator>
            <q-item v-for="(item, idx) in selected.items" :key="item.id">
              <q-item-section>
                <q-item-label :class="{ 'text-grey-5': !item.isActive }">{{ item.label }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <q-btn flat dense round icon="arrow_upward" size="sm" :disable="idx === 0" @click="moveItem(idx, -1)" />
                  <q-btn flat dense round icon="arrow_downward" size="sm" :disable="idx === selected.items.length - 1" @click="moveItem(idx, 1)" />
                  <q-toggle :model-value="item.isActive" dense color="positive" @update:model-value="(v) => toggleItem(item, v)" />
                  <q-btn flat dense round icon="edit" size="sm" @click="openEditItem(item)" />
                  <q-btn flat dense round icon="delete" color="negative" size="sm" @click="confirmDeleteItem(item)" />
                </div>
              </q-item-section>
            </q-item>
            <q-item v-if="selected.items.length === 0">
              <q-item-section class="text-grey">등록된 항목이 없습니다.</q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-card v-else flat bordered class="q-pa-xl text-center text-grey">
          왼쪽에서 카테고리를 선택하세요.
        </q-card>
      </div>
    </div>

    <!-- 카테고리 등록/수정 다이얼로그 -->
    <q-dialog v-model="categoryDialog" persistent>
      <q-card style="min-width: 420px; max-width: 90vw">
        <q-card-section class="text-h6">{{ categoryEditTarget ? '카테고리 수정' : '카테고리 등록' }}</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input
            v-if="!categoryEditTarget"
            v-model="categoryForm.key" label="키 (영문, 코드에서 참조) *" outlined dense autofocus
            hint="예: target_system"
          />
          <q-input v-model="categoryForm.label" label="표시 이름 *" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="categorySaving" @click="submitCategory" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 항목 등록/수정 다이얼로그 -->
    <q-dialog v-model="itemDialog" persistent>
      <q-card style="min-width: 420px; max-width: 90vw">
        <q-card-section class="text-h6">{{ itemEditTarget ? '항목 수정' : '항목 등록' }}</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="itemForm.label" label="이름 *" outlined dense autofocus />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="itemSaving" @click="submitItem" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { envCategoryService, type EnvCategoryOut, type EnvItem } from 'src/services/envCategory'

const $q = useQuasar()

const categories = ref<EnvCategoryOut[]>([])
const selected = ref<EnvCategoryOut | null>(null)
const loading = ref(false)

async function load(keepSelection = true) {
  loading.value = true
  try {
    categories.value = await envCategoryService.list()
    if (keepSelection && selected.value) {
      selected.value = categories.value.find((c) => c.id === selected.value?.id) ?? categories.value[0] ?? null
    } else {
      selected.value = categories.value[0] ?? null
    }
  } catch {
    $q.notify({ type: 'negative', message: '카테고리를 불러오는데 실패했습니다' })
  } finally {
    loading.value = false
  }
}

// ── 카테고리 CRUD ──
const categoryDialog = ref(false)
const categorySaving = ref(false)
const categoryEditTarget = ref<EnvCategoryOut | null>(null)
const categoryForm = ref({ key: '', label: '' })

function openCreateCategory() {
  categoryEditTarget.value = null
  categoryForm.value = { key: '', label: '' }
  categoryDialog.value = true
}

function openEditCategory(c: EnvCategoryOut) {
  categoryEditTarget.value = c
  categoryForm.value = { key: c.key, label: c.label }
  categoryDialog.value = true
}

async function submitCategory() {
  if (!categoryForm.value.label.trim() || (!categoryEditTarget.value && !categoryForm.value.key.trim())) {
    $q.notify({ type: 'warning', message: '필수 항목을 입력해주세요.', position: 'top' })
    return
  }
  categorySaving.value = true
  try {
    if (categoryEditTarget.value) {
      await envCategoryService.patchCategory(categoryEditTarget.value.id, { label: categoryForm.value.label.trim() })
    } else {
      await envCategoryService.createCategory({ key: categoryForm.value.key.trim(), label: categoryForm.value.label.trim() })
    }
    categoryDialog.value = false
    await load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '저장에 실패했습니다' })
  } finally {
    categorySaving.value = false
  }
}

function confirmDeleteCategory(c: EnvCategoryOut) {
  $q.dialog({
    title: '카테고리 삭제',
    message: `'${c.label}' 카테고리를 삭제하시겠습니까? 하위 항목도 모두 삭제됩니다.`,
    cancel: true,
  }).onOk(() => {
    void (async () => {
      try {
        await envCategoryService.removeCategory(c.id)
        selected.value = null
        await load(false)
      } catch {
        $q.notify({ type: 'negative', message: '삭제에 실패했습니다' })
      }
    })()
  })
}

// ── 항목 CRUD ──
const itemDialog = ref(false)
const itemSaving = ref(false)
const itemEditTarget = ref<EnvItem | null>(null)
const itemForm = ref({ label: '' })

function openCreateItem() {
  itemEditTarget.value = null
  itemForm.value = { label: '' }
  itemDialog.value = true
}

function openEditItem(item: EnvItem) {
  itemEditTarget.value = item
  itemForm.value = { label: item.label }
  itemDialog.value = true
}

async function submitItem() {
  if (!selected.value) return
  if (!itemForm.value.label.trim()) {
    $q.notify({ type: 'warning', message: '이름을 입력해주세요.', position: 'top' })
    return
  }
  itemSaving.value = true
  try {
    if (itemEditTarget.value) {
      await envCategoryService.patchItem(selected.value.id, itemEditTarget.value.id, { label: itemForm.value.label.trim() })
    } else {
      await envCategoryService.addItem(selected.value.id, { label: itemForm.value.label.trim() })
    }
    itemDialog.value = false
    await load()
  } catch (e) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    $q.notify({ type: 'negative', message: msg || '저장에 실패했습니다' })
  } finally {
    itemSaving.value = false
  }
}

async function toggleItem(item: EnvItem, active: boolean) {
  if (!selected.value) return
  try {
    await envCategoryService.patchItem(selected.value.id, item.id, { isActive: active })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '변경에 실패했습니다' })
  }
}

async function moveItem(idx: number, dir: -1 | 1) {
  if (!selected.value) return
  const items = selected.value.items
  const other = items[idx + dir]
  const current = items[idx]
  if (!other || !current) return
  try {
    await Promise.all([
      envCategoryService.patchItem(selected.value.id, current.id, { sortOrder: other.sortOrder }),
      envCategoryService.patchItem(selected.value.id, other.id, { sortOrder: current.sortOrder }),
    ])
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '순서 변경에 실패했습니다' })
  }
}

function confirmDeleteItem(item: EnvItem) {
  if (!selected.value) return
  const categoryId = selected.value.id
  $q.dialog({
    title: '항목 삭제',
    message: `'${item.label}' 항목을 삭제하시겠습니까?`,
    cancel: true,
  }).onOk(() => {
    void (async () => {
      try {
        await envCategoryService.removeItem(categoryId, item.id)
        await load()
      } catch {
        $q.notify({ type: 'negative', message: '삭제에 실패했습니다' })
      }
    })()
  })
}

onMounted(() => { void load() })
</script>
