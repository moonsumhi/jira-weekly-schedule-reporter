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
                  · 하위 {{ subsOf(menu.id).length + systemSubsOf(menu).length }}개
                  <span class="text-orange">
                    · {{ effectiveVisibleTeams(menu.visibleTeams).join(', ') }}만 표시
                  </span>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row no-wrap items-center">
                  <q-badge v-if="menu.isSystem" color="blue-grey" label="시스템" class="q-mr-xs" />
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
          </template>
          <div v-else class="text-caption text-grey">
            {{ editMenuTarget?.title }} <span class="text-grey-5">(시스템 메뉴 — 이름 변경 불가)</span>
          </div>
          <div>
            <div class="text-caption text-grey q-mb-xs">아이콘</div>
            <IconPicker v-model="menuForm.icon" />
          </div>
          <q-toggle v-if="!editMenuTarget?.isSystem" v-model="menuForm.is_visible" label="사이드바에 표시" />
          <q-input v-model="menuForm.link" label="링크 (직접 이동할 URL, 비우면 하위 메뉴 방식)" outlined dense clearable />
          <div>
            <q-select
              v-model="menuForm.visible_teams"
              :options="TEAM_OPTIONS"
              :label="`노출 팀 (비우면 ${DEFAULT_VISIBLE_TEAM}에게만 표시)`"
              outlined dense multiple use-chips clearable
            />
            <div class="text-caption text-grey q-mt-xs">
              선택한 팀 외에는 사이드바에서 숨겨지고 URL 직접 접근도 차단됩니다.
              비워두면 {{ DEFAULT_VISIBLE_TEAM }}에게만 표시됩니다.
            </div>
          </div>
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
import { DEFAULT_VISIBLE_TEAM, effectiveVisibleTeams } from 'src/constants/menuPermissions'

const menuStore = useMenuStore()

const $q = useQuasar()

// 백엔드 app/models/user.py의 TEAM_OPTIONS와 동일하게 유지해야 함
const TEAM_OPTIONS = ['데이터운영팀', '데이터구축팀', '데이터활용팀', '데이터결합팀']

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
const menuForm = ref({ title: '', icon: 'fa-solid fa-folder', is_visible: true, link: '', visible_teams: [] as string[] })

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

// 시스템 고정 하위메뉴 — job(작업 양식)만 프론트에서 동적 로드하고,
// 나머지는 메뉴 자체가 갖고 있는 menu.submenus(백엔드 시드 데이터, 사이드바가 실제로 쓰는 값)를 그대로 사용한다.
// (예전엔 여기 프론트에 SYSTEM_SUBS를 별도로 하드코딩해뒀었는데, 백엔드에 새 하위메뉴가 추가돼도
//  이 목록엔 반영이 안 돼서 스케줄 관리/SR/Audit Log 같은 항목의 아이콘을 여기서 수정할 수 없는 문제가 있었다.)
function systemSubsOf(menu: MenuOut): { title: string; icon: string; link: string }[] {
  if (menu.slug === 'job') {
    return jobTemplates.value.map((t) => ({
      title: t.title,
      icon: 'fa-solid fa-file-alt',
      link: `/job/forms/${t.jiraIssueKey || t.id}`,
    }))
  }
  return menu.submenus ?? []
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
    let items = systemSubsOf(menu)
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
  return systemSubsOf(menu).filter((s) => !visibleLinks.has(s.link))
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
    const allSubs = systemSubsOf(menu)
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

// ── 메뉴 ──
function openCreateMenu() {
  editMenuTarget.value = null
  menuForm.value = { title: '', icon: 'fa-solid fa-folder', is_visible: true, link: '', visible_teams: [] }
  menuDialog.value = true
}

function openEditMenu(menu: MenuOut) {
  editMenuTarget.value = menu
  menuForm.value = { title: menu.title, icon: menu.icon, is_visible: menu.isVisible, link: menu.link ?? '', visible_teams: menu.visibleTeams ?? [] }
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
      visible_teams: menuForm.value.visible_teams,
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
