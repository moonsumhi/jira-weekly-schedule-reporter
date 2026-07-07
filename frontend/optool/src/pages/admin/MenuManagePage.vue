<template>
  <q-page padding>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-9">
        <div class="row items-center q-mb-sm">
          <div class="text-subtitle1 text-weight-bold col">메뉴</div>
          <q-btn icon="add" label="추가" color="primary" size="sm" @click="openCreateMenu" />
        </div>

        <q-list bordered>
          <draggable
            v-model="menus"
            item-key="id"
            handle=".drag-handle"
            ghost-class="drag-ghost"
            @end="onDragEnd"
          >
            <template #item="{ element: menu }">
          <q-expansion-item
            :key="menu.id"
            expand-separator
            :header-class="expandedId === menu.id ? 'bg-blue-1' : ''"
            @update:model-value="(v) => expandedId = v ? menu.id : null"
          >
            <template #header>
              <q-item-section avatar style="min-width:32px; padding-right:4px">
                <q-icon name="drag_indicator" class="drag-handle cursor-grab" color="grey-5" size="sm" />
              </q-item-section>
              <q-item-section avatar style="min-width:36px">
                <q-icon :name="menu.icon" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ menu.title }}</q-item-label>
                <q-item-label caption>
                  <span :class="menu.isVisible ? 'text-positive' : 'text-grey'">
                    {{ menu.isVisible ? '표시' : '숨김' }}
                  </span>
                  · 내부: <span :class="menu.isInternalVisible ? 'text-positive' : 'text-grey'">{{ menu.isInternalVisible ? '공개' : '숨김' }}</span>
                  · 외부: <span :class="menu.isExternalVisible ? 'text-positive' : 'text-grey'">{{ menu.isExternalVisible ? '공개' : '숨김' }}</span>
                  · 하위 {{ subsOf(menu.id).length + systemSubsOf(menu.slug).length }}개
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row no-wrap items-center">
                  <q-badge v-if="menu.isSystem" color="blue-grey" label="시스템" class="q-mr-xs" />
                  <q-btn
                    flat dense round size="sm"
                    :icon="menu.isInternalVisible ? 'corporate_fare' : 'corporate_fare'"
                    :color="menu.isInternalVisible ? 'primary' : 'grey-4'"
                    :title="'내부: ' + (menu.isInternalVisible ? '공개' : '숨김')"
                    @click.stop="toggleInternalVisible(menu)"
                  >
                    <q-tooltip>내부망 {{ menu.isInternalVisible ? '공개 (클릭시 숨김)' : '숨김 (클릭시 공개)' }}</q-tooltip>
                  </q-btn>
                  <q-btn
                    flat dense round size="sm"
                    :icon="menu.isExternalVisible ? 'public' : 'public_off'"
                    :color="menu.isExternalVisible ? 'positive' : 'grey-4'"
                    :title="'외부: ' + (menu.isExternalVisible ? '공개' : '숨김')"
                    @click.stop="toggleExternalVisible(menu)"
                  >
                    <q-tooltip>외부망 {{ menu.isExternalVisible ? '공개 (클릭시 숨김)' : '숨김 (클릭시 공개)' }}</q-tooltip>
                  </q-btn>
                  <q-btn flat dense round icon="edit" size="sm" @click.stop="openEditMenu(menu)" />
                  <q-btn v-if="!menu.isSystem" flat dense round icon="delete" size="sm" color="negative" @click.stop="confirmDeleteMenu(menu)" />
                </div>
              </q-item-section>
            </template>

            <!-- 하위 메뉴 목록 -->
            <div class="q-pl-md q-pb-sm">
              <div class="row items-center q-py-xs q-px-sm">
                <span class="text-caption text-grey col">하위 메뉴</span>
                <q-btn v-if="!menu.isSystem && menu.slug !== 'asset'" icon="add" label="추가" size="xs" flat color="primary" @click.stop="openCreateSub(menu)" />
              </div>

              <q-list dense separator>
                <!-- 시스템 고정 하위메뉴 (드래그로 순서 변경 가능) -->
                <draggable
                  :model-value="sysSubsMap[menu.id] ?? []"
                  @update:model-value="(v) => updateSysSubsEntry(menu.id, v)"
                  item-key="link"
                  handle=".sys-drag-handle"
                  ghost-class="drag-ghost"
                  @end="onSysSubDragEnd(menu)"
                >
                  <template #item="{ element: sys }">
                    <q-item :key="sys.link" class="bg-grey-1">
                      <q-item-section avatar style="min-width:28px; padding-right:2px">
                        <q-icon name="drag_indicator" class="sys-drag-handle cursor-grab" color="grey-4" size="xs" />
                      </q-item-section>
                      <q-item-section avatar style="min-width:28px">
                        <q-icon :name="menu.subIcons?.[sys.link] ?? sys.icon" size="xs" color="grey-6" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label>{{ sys.title }}</q-item-label>
                        <q-item-label caption>{{ sys.link }}</q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <div class="row no-wrap items-center">
                          <q-badge color="grey-5" label="시스템" class="q-mr-xs" />
                          <q-btn flat dense round icon="edit" size="xs" @click.stop="openSysIconEdit(menu, sys)" />
                          <q-btn v-if="sys.link !== '/admin/menus'" flat dense round icon="visibility_off" size="xs" color="grey-5" @click.stop="hideSysSub(menu, sys)" />
                        </div>
                      </q-item-section>
                    </q-item>
                  </template>
                </draggable>

                <!-- 동적 게시판 하위메뉴 -->
                <draggable
                  :model-value="subsMap[menu.id] ?? []"
                  @update:model-value="(v: BoardOut[]) => { subsMap[menu.id] = v }"
                  item-key="id"
                  handle=".sub-drag-handle"
                  ghost-class="drag-ghost"
                  @end="onSubDragEnd(menu.id)"
                >
                  <template #item="{ element: sub }">
                    <q-item :key="sub.id" class="bg-grey-1">
                      <q-item-section avatar style="min-width:28px; padding-right:2px">
                        <q-icon name="drag_indicator" class="sub-drag-handle cursor-grab" color="grey-4" size="xs" />
                      </q-item-section>
                      <q-item-section avatar style="min-width:28px">
                        <q-icon :name="sub.icon ?? 'fa-solid fa-clipboard-list'" size="xs" color="grey-7" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label>{{ sub.title }}</q-item-label>
                        <q-item-label caption>
                          {{ sub.link ? sub.link : `/board/${sub.id}` }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <div class="row no-wrap">
                          <q-btn flat dense round icon="open_in_new" size="xs" color="primary" :to="sub.link ?? `/board/${sub.id}`" />
                          <q-btn flat dense round icon="edit" size="xs" @click.stop="openEditSub(sub)" />
                          <q-btn flat dense round icon="visibility_off" size="xs" color="grey-5" @click.stop="hideBoardSub(menu, sub)" />
                          <q-btn flat dense round icon="delete" size="xs" color="negative" @click.stop="confirmDeleteSub(sub)" />
                        </div>
                      </q-item-section>
                    </q-item>
                  </template>
                </draggable>

                <q-item v-if="(sysSubsMap[menu.id] ?? []).length === 0 && subsOf(menu.id).length === 0 && hiddenSysSubsOf(menu).length === 0 && hiddenBoardSubsOf(menu).length === 0" class="bg-grey-1">
                  <q-item-section class="text-grey text-caption q-py-xs">
                    하위 메뉴가 없습니다
                  </q-item-section>
                </q-item>

                <!-- 숨겨진 동적 하위메뉴(게시판) -->
                <template v-if="hiddenBoardSubsOf(menu).length > 0">
                  <q-item class="bg-grey-1">
                    <q-item-section class="text-caption text-grey">숨겨진 항목</q-item-section>
                  </q-item>
                  <q-item v-for="sub in hiddenBoardSubsOf(menu)" :key="sub.id" class="bg-grey-2">
                    <q-item-section avatar style="min-width:28px; padding-right:2px">
                      <q-icon name="visibility_off" size="xs" color="grey-4" />
                    </q-item-section>
                    <q-item-section avatar style="min-width:28px">
                      <q-icon :name="sub.icon ?? 'fa-solid fa-clipboard-list'" size="xs" color="grey-5" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-grey">{{ sub.title }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-btn flat dense round icon="visibility" size="xs" color="primary" @click.stop="restoreBoardSub(menu, sub)" />
                    </q-item-section>
                  </q-item>
                </template>

                <!-- 숨겨진 시스템 하위메뉴 -->
                <template v-if="hiddenSysSubsOf(menu).length > 0">
                  <q-item class="bg-grey-1">
                    <q-item-section class="text-caption text-grey">숨겨진 항목</q-item-section>
                  </q-item>
                  <q-item v-for="sub in hiddenSysSubsOf(menu)" :key="sub.link" class="bg-grey-2">
                    <q-item-section avatar style="min-width:28px; padding-right:2px">
                      <q-icon name="visibility_off" size="xs" color="grey-4" />
                    </q-item-section>
                    <q-item-section avatar style="min-width:28px">
                      <q-icon :name="sub.icon" size="xs" color="grey-5" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-grey">{{ sub.title }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-btn flat dense round icon="visibility" size="xs" color="primary" @click.stop="restoreSysSub(menu, sub)" />
                    </q-item-section>
                  </q-item>
                </template>
              </q-list>
            </div>
          </q-expansion-item>
            </template>
          </draggable>

          <q-item v-if="menus.length === 0">
            <q-item-section class="text-grey text-caption text-center q-pa-sm">
              메뉴가 없습니다
            </q-item-section>
          </q-item>

        </q-list>
      </div>

      <div class="col-12 col-md-3 flex items-start">
        <div class="text-grey text-caption q-pt-xs">
          <q-icon name="fa-solid fa-info-circle" size="xs" class="q-mr-xs" />
          메뉴를 펼치면 하위 메뉴를 관리할 수 있습니다
        </div>
      </div>
    </div>

    <!-- 메뉴 다이얼로그 -->
    <q-dialog v-model="menuDialog" persistent>
      <q-card style="min-width: 380px">
        <q-card-section class="text-h6">{{ editMenuTarget ? '메뉴 수정' : '메뉴 추가' }}</q-card-section>
        <q-card-section class="q-gutter-sm">
          <template v-if="!editMenuTarget?.isSystem">
            <q-input v-model="menuForm.title" label="메뉴 이름" outlined dense />
            <div>
              <div class="text-caption text-grey q-mb-xs">아이콘</div>
              <IconPicker v-model="menuForm.icon" />
            </div>
            <q-toggle v-model="menuForm.is_visible" label="사이드바에 표시" />
          </template>
          <q-input v-model="menuForm.link" label="링크 (직접 이동할 URL, 비우면 하위 메뉴 방식)" outlined dense clearable />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" :label="editMenuTarget ? '수정' : '추가'" @click="submitMenu" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 시스템 하위메뉴 아이콘 편집 다이얼로그 -->
    <q-dialog v-model="sysIconDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section class="text-h6">아이콘 수정 — {{ sysIconTarget?.title }}</q-card-section>
        <q-card-section>
          <IconPicker v-model="sysIconValue" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="saving" @click="submitSysIcon" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 하위 메뉴 다이얼로그 -->
    <q-dialog v-model="subDialog" persistent>
      <q-card style="min-width: 380px">
        <q-card-section class="text-h6">{{ editSubTarget ? '하위 메뉴 수정' : '하위 메뉴 추가' }}</q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="subForm.title" label="이름" outlined dense autofocus />
          <q-input v-model="subForm.description" label="설명 (선택)" outlined dense />
          <div>
            <div class="text-caption text-grey q-mb-xs">아이콘</div>
            <IconPicker v-model="subForm.icon" />
          </div>
          <q-input v-model="subForm.link" label="링크 (비우면 게시판으로 이동)" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" :label="editSubTarget ? '수정' : '추가'" @click="submitSub" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import draggable from 'vuedraggable'
import IconPicker from 'src/components/IconPicker.vue'
import { menuService, type MenuOut } from 'src/services/menus'
import { boardService, type BoardOut } from 'src/services/boards'
import { formTemplateService, type FormTemplate } from 'src/services/formTemplates'
import { useMenuStore } from 'stores/menus'

const menuStore = useMenuStore()

const $q = useQuasar()

const menus = ref<MenuOut[]>([])
const subsMap = ref<Record<string, BoardOut[]>>({})
const allBoardsMap = ref<Record<string, BoardOut[]>>({})
const sysSubsMap = ref<Record<string, { title: string; icon: string; link: string }[]>>({})
const jobTemplates = ref<FormTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const expandedId = ref<string | null>(null)

// 메뉴 다이얼로그
const menuDialog = ref(false)
const editMenuTarget = ref<MenuOut | null>(null)
const menuForm = ref({ title: '', icon: 'fa-solid fa-folder', is_visible: true, link: '' })

// 시스템 하위메뉴 아이콘 편집
const sysIconDialog = ref(false)
const sysIconTarget = ref<{ title: string; link: string; icon: string } | null>(null)
const sysIconMenu = ref<MenuOut | null>(null)
const sysIconValue = ref('')

function openSysIconEdit(menu: MenuOut, sys: { title: string; link: string; icon: string }) {
  sysIconMenu.value = menu
  sysIconTarget.value = sys
  sysIconValue.value = menu.subIcons?.[sys.link] ?? sys.icon
  sysIconDialog.value = true
}

async function submitSysIcon() {
  if (!sysIconMenu.value || !sysIconTarget.value) return
  saving.value = true
  try {
    const updated = { ...(sysIconMenu.value.subIcons ?? {}), [sysIconTarget.value.link]: sysIconValue.value }
    await menuService.patch(sysIconMenu.value.id, { sub_icons: updated })
    sysIconDialog.value = false
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

// 시스템 고정 하위메뉴 (slug별 하드코딩)
const SYSTEM_SUBS: Record<string, { title: string; icon: string; link: string }[]> = {
  jira: [
    { title: '검색', icon: 'fa-solid fa-list', link: '/jira/search' },
    { title: '주간보고', icon: 'fa-solid fa-calendar-week', link: '/report/weekly' },
  ],
  asset: [
    { title: '전체',          icon: 'fa-solid fa-layer-group',   link: '/asset/list' },
    { title: '서버',          icon: 'fa-solid fa-server',        link: '/asset/list?category=서버' },
    { title: '네트워크',      icon: 'fa-solid fa-network-wired', link: '/asset/list?category=네트워크' },
    { title: '정보보호시스템', icon: 'fa-solid fa-shield-halved', link: '/asset/list?category=정보보호시스템' },
    { title: 'DBMS',         icon: 'fa-solid fa-database',       link: '/asset/list?category=DBMS' },
    { title: 'VMware',       icon: 'fa-brands fa-vuejs',         link: '/asset/list?category=VMware' },
  ],
  watch: [],
  account: [
    { title: '내 계정', icon: 'fa-solid fa-user', link: '/account/settings' },
  ],
  inspection: [],
  admin: [
    { title: '회원가입 승인', icon: 'fa-regular fa-thumbs-up', link: '/admin/approvals' },
    { title: '회원 목록', icon: 'fa-solid fa-users', link: '/admin/users' },
    { title: '메뉴 관리', icon: 'fa-solid fa-list', link: '/admin/menus' },
  ],
}


function systemSubsOf(slug: string | null): { title: string; icon: string; link: string }[] {
  if (slug === 'job') {
    return jobTemplates.value.map((t) => ({
      title: t.title,
      icon: 'fa-solid fa-file-alt',
      link: `/job/forms/${t.jiraIssueKey || t.id}`,
    }))
  }
  return SYSTEM_SUBS[slug ?? ''] ?? []
}

// 하위 메뉴 다이얼로그
const subDialog = ref(false)
const editSubTarget = ref<BoardOut | null>(null)
const subMenuTarget = ref<MenuOut | null>(null)
const subForm = ref({ title: '', description: '', icon: 'fa-solid fa-clipboard-list', link: '' })

function subsOf(menuId: string): BoardOut[] {
  return subsMap.value[menuId] ?? []
}

type SysSub = { title: string; icon: string; link: string }

function updateSysSubsEntry(menuId: string, v: unknown) {
  sysSubsMap.value[menuId] = v as SysSub[]
}

function buildSysSubsMap() {
  const map: Record<string, { title: string; icon: string; link: string }[]> = {}
  for (const menu of menus.value) {
    let items: { title: string; icon: string; link: string }[]
    if (menu.slug === 'job') {
      items = jobTemplates.value.map((t) => ({
        title: t.title,
        icon: 'fa-solid fa-file-alt',
        link: `/job/forms/${t.jiraIssueKey || t.id}`,
      }))
    } else {
      items = [...(SYSTEM_SUBS[menu.slug ?? ''] ?? [])]
    }
    if (menu.subOrder && menu.subOrder.length > 0) {
      const orderMap = new Map(menu.subOrder.map((link, i) => [link, i]))
      items = items.filter((item) => orderMap.has(item.link))
      items.sort((a, b) => (orderMap.get(a.link) ?? Infinity) - (orderMap.get(b.link) ?? Infinity))
    }
    map[menu.id] = items
  }
  sysSubsMap.value = map
}

function hiddenSysSubsOf(menu: MenuOut): { title: string; icon: string; link: string }[] {
  const visibleLinks = new Set((sysSubsMap.value[menu.id] ?? []).map((s) => s.link))
  if (menu.slug === 'job') {
    return jobTemplates.value
      .map((t) => ({ title: t.title, icon: 'fa-solid fa-file-alt', link: `/job/forms/${t.jiraIssueKey || t.id}` }))
      .filter((s) => !visibleLinks.has(s.link))
  }
  const allSubs = SYSTEM_SUBS[menu.slug ?? ''] ?? []
  return allSubs.filter((s) => !visibleLinks.has(s.link))
}

async function hideSysSub(menu: MenuOut, sys: { link: string }) {
  const current = sysSubsMap.value[menu.id] ?? []
  const newOrder = current.filter((i) => i.link !== sys.link).map((i) => i.link)
  saving.value = true
  try {
    await menuService.patch(menu.id, { sub_order: newOrder })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

async function restoreSysSub(menu: MenuOut, sub: { link: string }) {
  const current = sysSubsMap.value[menu.id] ?? []
  let newOrder: string[]
  if (menu.slug === 'job') {
    newOrder = [...current.map((i) => i.link), sub.link]
  } else {
    const allSubs = SYSTEM_SUBS[menu.slug ?? ''] ?? []
    const defaultIdx = allSubs.findIndex((s) => s.link === sub.link)
    newOrder = [...current.map((i) => i.link)]
    newOrder.splice(Math.min(defaultIdx, newOrder.length), 0, sub.link)
  }
  saving.value = true
  try {
    await menuService.patch(menu.id, { sub_order: newOrder })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

function buildSubsMap(fetchedMenus: MenuOut[], boards: BoardOut[]) {
  const all: Record<string, BoardOut[]> = {}
  const map: Record<string, BoardOut[]> = {}
  for (const m of fetchedMenus) { all[m.id] = []; map[m.id] = [] }
  for (const b of boards) {
    if (!all[b.menuId]) all[b.menuId] = []
    all[b.menuId]!.push(b)
  }
  allBoardsMap.value = all
  for (const menu of fetchedMenus) {
    const arr = [...(all[menu.id] ?? [])]
    if (menu.subOrder && menu.subOrder.length > 0) {
      const orderMap = new Map(menu.subOrder.map((key, i) => [key, i]))
      map[menu.id] = arr
        .filter((b) => orderMap.has(b.link ?? `/board/${b.id}`))
        .sort((a, b) => (orderMap.get(a.link ?? `/board/${a.id}`) ?? Infinity) - (orderMap.get(b.link ?? `/board/${b.id}`) ?? Infinity))
    } else {
      map[menu.id] = arr.sort((a, b) => (a.sortOrder ?? Infinity) - (b.sortOrder ?? Infinity))
    }
  }
  subsMap.value = map
}

function hiddenBoardSubsOf(menu: MenuOut): BoardOut[] {
  const visibleLinks = new Set((subsMap.value[menu.id] ?? []).map((b) => b.link ?? `/board/${b.id}`))
  return (allBoardsMap.value[menu.id] ?? []).filter((b) => !visibleLinks.has(b.link ?? `/board/${b.id}`))
}

async function hideBoardSub(menu: MenuOut, sub: BoardOut) {
  const current = subsMap.value[menu.id] ?? []
  const newOrder = current.filter((b) => (b.link ?? `/board/${b.id}`) !== (sub.link ?? `/board/${sub.id}`)).map((b) => b.link ?? `/board/${b.id}`)
  saving.value = true
  try {
    await menuService.patch(menu.id, { sub_order: newOrder })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

async function restoreBoardSub(menu: MenuOut, sub: BoardOut) {
  const current = subsMap.value[menu.id] ?? []
  const newOrder = [...current.map((b) => b.link ?? `/board/${b.id}`), sub.link ?? `/board/${sub.id}`]
  saving.value = true
  try {
    await menuService.patch(menu.id, { sub_order: newOrder })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const [fetchedMenus, fetchedBoards, fetchedTemplates] = await Promise.all([
      menuService.list(false),
      boardService.listBoards(),
      formTemplateService.list('Job'),
    ])
    jobTemplates.value = fetchedTemplates
    const filtered = fetchedMenus.filter((m) => m.slug !== 'pilot')
    menus.value = filtered
    buildSubsMap(filtered, fetchedBoards)
    buildSysSubsMap()
    void menuStore.refresh()
  } finally {
    loading.value = false
  }
}

async function onDragEnd() {
  try {
    await Promise.all(menus.value.map((menu, idx) => menuService.patch(menu.id, { sort_order: idx + 1 })))
    await menuStore.refresh()
    $q.notify({ type: 'positive', message: '메뉴 순서가 저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '순서 저장 실패' })
    await load()
  }
}

async function onSubDragEnd(menuId: string) {
  const items = subsMap.value[menuId] ?? []
  try {
    await Promise.all(
      items.map((sub, idx) => boardService.patchBoard(sub.id, { sort_order: idx + 1 }))
    )
    await menuStore.refresh()
    $q.notify({ type: 'positive', message: '하위 메뉴 순서가 저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '순서 저장 실패' })
    await load()
  }
}

async function onSysSubDragEnd(menu: MenuOut) {
  if (menu.id.startsWith('__')) return
  const items = sysSubsMap.value[menu.id] ?? []
  try {
    if (menu.slug === 'job') {
      await Promise.all(
        items.map((item, idx) =>
          formTemplateService.patchSortOrder(item.link.replace('/job/forms/', ''), idx + 1)
        )
      )
    } else {
      await menuService.patch(menu.id, { sub_order: items.map((i) => i.link) })
    }
    await menuStore.refresh()
    $q.notify({ type: 'positive', message: '하위 메뉴 순서가 저장되었습니다' })
  } catch {
    $q.notify({ type: 'negative', message: '순서 저장 실패' })
    await load()
  }
}

async function toggleInternalVisible(menu: MenuOut) {
  try {
    await menuService.patch(menu.id, { is_internal_visible: !menu.isInternalVisible })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  }
}

async function toggleExternalVisible(menu: MenuOut) {
  try {
    await menuService.patch(menu.id, { is_external_visible: !menu.isExternalVisible })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  }
}

// ── 메뉴 ──
function openCreateMenu() {
  editMenuTarget.value = null
  menuForm.value = { title: '', icon: 'fa-solid fa-folder', is_visible: true, link: '' }
  menuDialog.value = true
}

function openEditMenu(menu: MenuOut) {
  editMenuTarget.value = menu
  menuForm.value = { title: menu.title, icon: menu.icon, is_visible: menu.isVisible, link: menu.link ?? '' }
  menuDialog.value = true
}

async function submitMenu() {
  if (!menuForm.value.title) return
  saving.value = true
  try {
    const payload = {
      title: menuForm.value.title,
      icon: menuForm.value.icon,
      is_visible: menuForm.value.is_visible,
      link: menuForm.value.link || null,
    }
    if (editMenuTarget.value) {
      await menuService.patch(editMenuTarget.value.id, payload)
    } else {
      await menuService.create(payload)
    }
    menuDialog.value = false
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

function confirmDeleteMenu(menu: MenuOut) {
  if (menu.isSystem) {
    $q.dialog({
      title: '시스템 메뉴',
      message: `"${menu.title}" 메뉴는 하드코딩된 시스템 메뉴입니다.<br>삭제하려면 소스 코드에서 직접 제거해야 합니다.`,
      html: true,
      ok: { label: '확인', flat: true },
    })
    return
  }
  $q.dialog({
    title: '메뉴 삭제',
    message: `"${menu.title}" 메뉴를 정말 삭제하시겠습니까?`,
    html: true,
    cancel: { label: '취소', flat: true },
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    $q.dialog({
      title: '최종 확인',
      message: `"${menu.title}" 메뉴를 정말로 삭제하시겠습니까?<br>이 작업은 되돌릴 수 없습니다.`,
      html: true,
      cancel: { label: '취소', flat: true },
      ok: { label: '삭제', color: 'negative' },
    }).onOk(() => {
      void (async () => {
        await menuService.remove(menu.id)
        await load()
      })()
    })
  })
}

// ── 하위 메뉴 ──
function openCreateSub(menu: MenuOut) {
  subMenuTarget.value = menu
  editSubTarget.value = null
  subForm.value = { title: '', description: '', icon: 'fa-solid fa-clipboard-list', link: '' }
  subDialog.value = true
}

function openEditSub(sub: BoardOut) {
  editSubTarget.value = sub
  subForm.value = { title: sub.title, description: sub.description, icon: sub.icon ?? 'fa-solid fa-clipboard-list', link: sub.link ?? '' }
  subDialog.value = true
}

async function submitSub() {
  if (!subForm.value.title) return
  saving.value = true
  const payload = {
    title: subForm.value.title,
    description: subForm.value.description,
    icon: subForm.value.icon || null,
    link: subForm.value.link || null,
  }
  try {
    if (editSubTarget.value) {
      await boardService.patchBoard(editSubTarget.value.id, payload)
    } else if (subMenuTarget.value) {
      await boardService.createBoard({ ...payload, menu_id: subMenuTarget.value.id })
    }
    subDialog.value = false
    await load()
  } catch {
    $q.notify({ type: 'negative', message: '저장에 실패했습니다' })
  } finally {
    saving.value = false
  }
}

function confirmDeleteSub(sub: BoardOut) {
  $q.dialog({
    title: '하위 메뉴 삭제',
    message: `"${sub.title}" 항목을 삭제하시겠습니까?`,
    html: true,
    cancel: { label: '취소', flat: true },
    ok: { label: '삭제', color: 'negative' },
  }).onOk(() => {
    $q.dialog({
      title: '최종 확인',
      message: `"${sub.title}" 항목을 정말로 삭제하시겠습니까?<br>이 작업은 되돌릴 수 없습니다.`,
      html: true,
      cancel: { label: '취소', flat: true },
      ok: { label: '삭제', color: 'negative' },
    }).onOk(() => {
      void (async () => { await boardService.deleteBoard(sub.id); await load() })()
    })
  })
}

onMounted(load)
</script>

<style scoped>
.drag-handle {
  cursor: grab;
}
.drag-ghost {
  opacity: 0.4;
  background: #c8ebfb;
}
</style>
