<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated :text-color="theme.currentTextColor()">
      <q-toolbar>
        <!-- menu button only when logged in -->
        <q-btn
          v-if="auth.isLoggedIn"
          flat
          dense
          round
          icon="menu"
          aria-label="Menu"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title>{{ theme.appName }}</q-toolbar-title>

        <div>{{ theme.appName }} v1.0</div>

        <!-- 알림 벨 -->
        <NotificationBell v-if="auth.isLoggedIn" class="q-ml-xs" />

        <!-- 링크 사이드바 토글 (내부망만) -->
        <q-btn
          v-if="auth.isLoggedIn && !isExternal"
          flat dense round
          icon="fa-solid fa-link"
          aria-label="Links"
          class="q-ml-sm"
          @click="toggleRightDrawer"
        />
      </q-toolbar>
    </q-header>

    <!-- drawer only when logged in -->
    <q-drawer
      v-if="auth.isLoggedIn"
      v-model="leftDrawerOpen"
      show-if-above
      bordered
    >
      <!-- column layout to pin logout button at bottom -->
      <div class="column fit">

        <!-- MENU AREA -->
        <q-scroll-area class="col">
          <q-list>
            <q-item-label header class="cursor-pointer" @click="$router.push('/app')">{{ auth.me?.team || theme.appName }}</q-item-label>

            <!-- 모든 메뉴를 sortOrder 순서대로 렌더링 -->
            <template v-for="menu in sortedVisibleMenus" :key="menu.id">
              <!-- Job: form template 기반 동적 하위 메뉴 -->
              <EssentialLink
                v-if="menu.slug === 'job'"
                :title="menu.title"
                :icon="menu.icon"
                :children="jobMenuItems"
              />

              <!-- Admin: 승인 대기 badge 포함 -->
              <EssentialLink
                v-else-if="menu.slug === 'admin'"
                :title="menu.title"
                :icon="menu.icon"
                :badge="pendingCount"
                :children="menuChildren(menu, '/admin/approvals')"
              />

              <!-- leaf 링크 메뉴 -->
              <EssentialLink
                v-else-if="menu.link"
                :title="menu.title"
                :icon="menu.icon"
                :link="menu.link"
              />

              <!-- DB submenus 기반 메뉴 -->
              <EssentialLink
                v-else-if="menu.submenus?.length"
                :title="menu.title"
                :icon="menu.icon"
                :children="menuChildren(menu)"
              />

              <!-- 동적 게시판 메뉴 (관리자가 추가한 메뉴) -->
              <EssentialLink
                v-else
                :title="menu.title"
                :icon="menu.icon"
                :children="boardChildrenOf(menu.id)"
              />
            </template>
          </q-list>
        </q-scroll-area>

        <!-- USER / LOGOUT AREA (BOTTOM) -->
        <q-separator />

        <q-item
          clickable v-ripple
          class="q-py-sm"
          @click="$router.push('/account/settings')"
        >
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="36px" class="text-caption">
              {{ auth.me?.fullName?.[0] ?? auth.me?.email?.[0]?.toUpperCase() ?? '?' }}
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-medium">{{ auth.me?.fullName ?? '-' }}</q-item-label>
            <q-item-label caption class="text-grey-6">{{ auth.me?.email }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn
              flat round dense
              icon="logout"
              color="grey-6"
              size="sm"
              @click.stop="onLogout"
            />
          </q-item-section>
        </q-item>
      </div>
    </q-drawer>
    <!-- 오른쪽 링크 사이드바 (내부망만) -->
    <q-drawer
      v-if="auth.isLoggedIn && !isExternal"
      v-model="rightDrawerOpen"
      side="right"
      bordered
      :width="280"
    >
      <div class="column fit">
        <div class="row items-center q-px-md q-py-sm">
          <div class="text-subtitle1 text-weight-bold col">서비스 바로가기</div>
          <q-btn v-if="auth.me?.isAdmin" flat dense round icon="add" size="sm" @click="openLinkCreate" />
          <q-btn v-if="auth.me?.isAdmin" flat dense round icon="playlist_add" size="sm" color="grey" title="일괄 등록" @click="openBulkImport" />
          <q-btn v-if="auth.me?.isAdmin" flat dense round :icon="linkEditMode ? 'close' : 'edit'" size="sm" color="grey" @click="linkEditMode = !linkEditMode" />
        </div>
        <q-separator />

        <q-scroll-area class="col">
          <!-- 로딩 중 -->
          <div v-if="linksLoading" class="q-pa-md text-center text-grey">불러오는 중...</div>

          <!-- 링크 없음 -->
          <div v-else-if="visibleLinks.length === 0" class="q-pa-md text-center text-grey text-caption">
            등록된 링크가 없습니다.
          </div>

          <!-- 카드 목록 -->
          <div v-else class="q-pa-sm">
            <div
              v-for="link in visibleLinks"
              :key="link.id"
              class="link-card q-mb-sm"
            >
              <!-- 색상 상단 바 + 서비스 종류 -->
              <div class="link-card-top" :style="{ backgroundColor: linkColorMap[link.color] ?? '#9e9e9e' }">
                {{ link.type || '기타' }}
              </div>

              <!-- 본문 -->
              <a :href="link.url" target="_blank" rel="noopener noreferrer" class="link-card-body">
                <div class="link-card-title">{{ link.title }}</div>
                <div v-if="link.note" class="link-card-desc">{{ link.note }}</div>
                <div v-if="link.tags.length" class="link-card-tags">
                  <span v-for="tag in link.tags" :key="tag" class="link-tag">#{{ tag }}</span>
                </div>
              </a>

              <!-- 관리자 편집 버튼 -->
              <div v-if="linkEditMode && auth.me?.isAdmin" class="link-card-actions">
                <q-btn flat dense round icon="edit" size="xs" color="grey" @click.stop="openLinkEdit(link)" />
                <q-btn flat dense round icon="delete" size="xs" color="negative" @click.stop="confirmDeleteLink(link)" />
              </div>
            </div>
          </div>
        </q-scroll-area>
      </div>
    </q-drawer>

    <!-- 링크 추가/수정 다이얼로그 -->
    <q-dialog v-model="linkDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">{{ linkForm.id ? '링크 수정' : '링크 추가' }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input v-model="linkForm.title" outlined dense label="사이트 이름 *" />
          <q-input v-model="linkForm.url" outlined dense label="URL *" placeholder="https://" />
          <q-input v-model="linkForm.type" outlined dense label="서비스 종류" placeholder="예: 모니터링, 관리" />
          <q-select
            v-model="linkForm.color"
            outlined dense label="색상"
            :options="linkColorOptions"
            emit-value map-options
          >
            <template #selected-item="{ opt }">
              <span class="q-mr-sm" :style="{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '2px', backgroundColor: linkColorMap[opt.value] ?? '#9e9e9e' }"></span>
              {{ opt.label }}
            </template>
          </q-select>
          <q-input v-model="linkForm.note" outlined dense label="설명" type="textarea" rows="2" />
          <q-input
            v-model="linkForm.tagsInput"
            outlined dense label="태그 (쉼표로 구분)"
            placeholder="예: 서버, 모니터링"
          />
          <q-input v-model.number="linkForm.rank" outlined dense label="정렬 순서" type="number" />
          <q-toggle v-model="linkForm.is_visible" label="표시" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="저장" :loading="linkSaving" @click="saveLink" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- 링크 엑셀 일괄 등록 다이얼로그 -->
    <q-dialog v-model="bulkImportDialog" persistent>
      <q-card style="min-width: 440px; max-width: 560px">
        <q-card-section>
          <div class="text-h6">링크 일괄 등록 (엑셀)</div>
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-btn outline color="primary" icon="download" label="템플릿 다운로드" @click="downloadLinkTemplate" />
          <q-file
            v-model="bulkImportFile"
            outlined dense
            label="엑셀 파일 선택"
            accept=".xlsx,.xls"
            clearable
          >
            <template #prepend><q-icon name="attach_file" /></template>
          </q-file>
          <div v-if="bulkImportError" class="text-negative text-caption">{{ bulkImportError }}</div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="취소" v-close-popup />
          <q-btn color="primary" label="등록" :loading="bulkImporting" :disable="!bulkImportFile" @click="saveBulkLinks" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from 'stores/auth'
import { useMenuStore } from 'stores/menus'
import { useThemeStore } from 'stores/theme'
import { useNotificationStore } from 'stores/notification'
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'
import NotificationBell from 'components/NotificationBell.vue'
import type { MenuOut } from 'src/services/menus'
import { useQuasar } from 'quasar'
import { fetchLinks, createLink, patchLink, deleteLink, type Link } from 'src/services/links'
import { SLUG_PERM, effectiveVisibleTeams } from 'src/constants/menuPermissions'

const auth = useAuthStore()
const menuStore = useMenuStore()
const theme = useThemeStore()
const notifStore = useNotificationStore()
const $q = useQuasar()
const { sidebarMenus, sidebarBoards, templateItems } = storeToRefs(menuStore)
const router = useRouter()
const route = useRoute()

function hasPerm(perm: string): boolean {
  if (auth.me?.isAdmin) return true
  return (auth.me?.permissions ?? []).includes(perm)
}

// localhost, 127.0.0.1, 사설 IP 대역(10.x / 172.16~31.x / 192.168.x)이면 내부망으로 인식
function detectInternal(hostname: string): boolean {
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') return true
  // IPv4 사설 대역
  if (/^10\./.test(hostname)) return true
  if (/^192\.168\./.test(hostname)) return true
  const m = hostname.match(/^172\.(\d+)\./)
  if (m && Number(m[1]) >= 16 && Number(m[1]) <= 31) return true
  return false
}
const isExternal = !detectInternal(window.location.hostname)
const isPort9001 = window.location.port === '9001'

function hasTeamAccess(menu: MenuOut): boolean {
  if (auth.me?.isAdmin) return true
  return effectiveVisibleTeams(menu.visibleTeams).includes(auth.me?.team ?? '')
}

const sortedVisibleMenus = computed(() =>
  sidebarMenus.value
    .filter((m) => m.isVisible)
    .filter((m) => m.slug !== 'admin' || !!auth.me?.isAdmin)
    .filter((m) => {
      const perm = SLUG_PERM[m.slug ?? '']
      return perm ? hasPerm(perm) : true  // 권한 필요한 슬러그는 hasPerm 체크
    })
    .filter(hasTeamAccess)
    .filter((m) => {
      if (isPort9001) return m.slug === 'jira' || m.slug === 'calendar' || m.title === '팀캘린더'
      return m.slug !== 'jira' && m.slug !== 'calendar' && m.title !== '팀캘린더'
    })
    .sort((a, b) => (a.sortOrder ?? Infinity) - (b.sortOrder ?? Infinity))
)

function applySubOrder<T extends { link: string }>(items: T[], menu: { subOrder?: string[] | null }): T[] {
  if (!menu.subOrder || menu.subOrder.length === 0) return items
  const orderMap = new Map(menu.subOrder.map((link, i) => [link, i]))
  const ordered = items.filter((item) => orderMap.has(item.link))
    .sort((a, b) => (orderMap.get(a.link) ?? Infinity) - (orderMap.get(b.link) ?? Infinity))
  const unordered = items.filter((item) => !orderMap.has(item.link))
  return [...ordered, ...unordered]
}

function menuChildren(menu: MenuOut, badgeLink?: string): EssentialLinkProps[] {
  const items = (menu.submenus ?? [])
    .filter((s) => !s.requireAdmin || !!auth.me?.isAdmin)
    .map((s) => ({
      title: s.title,
      icon: menu.subIcons?.[s.link] ?? s.icon,
      link: s.link,
      badge: badgeLink === s.link ? pendingCount.value : 0,
    }))
  return applySubOrder(items, menu)
}

function boardChildrenOf(menuId: string) {
  const menu = sortedVisibleMenus.value.find((m) => m.id === menuId)
  let boards = sidebarBoards.value.filter((b) => b.menuId === menuId)
  if (menu?.subOrder && menu.subOrder.length > 0) {
    const orderMap = new Map(menu.subOrder.map((key, i) => [key, i]))
    boards = boards
      .filter((b) => orderMap.has(b.link ?? `/board/${b.id}`))
      .sort((a, b) => (orderMap.get(a.link ?? `/board/${a.id}`) ?? Infinity) - (orderMap.get(b.link ?? `/board/${b.id}`) ?? Infinity))
  }
  return boards.map((b) => ({ title: b.title, icon: b.icon ?? 'fa-solid fa-clipboard-list', link: b.link ?? `/board/${b.id}` }))
}

const jobMenuItems = computed<EssentialLinkProps[]>(() => {
  const menu = sortedVisibleMenus.value.find((m) => m.slug === 'job')
  let items = templateItems.value
    .filter((item) => item.menu.toLowerCase() === 'job')
    .map((item) => ({
      ...item,
      icon: menu?.subIcons?.[item.link] ?? item.icon,
    }))
  if (menu?.subOrder && menu.subOrder.length > 0) {
    const orderMap = new Map(menu.subOrder.map((link, i) => [link, i]))
    items = items.filter((item) => orderMap.has(item.link))
    items.sort((a, b) => (orderMap.get(a.link) ?? Infinity) - (orderMap.get(b.link) ?? Infinity))
  }
  return items
})

const pendingCount = computed(() => auth.pendingCount)
let pendingTimer: ReturnType<typeof setInterval> | null = null

const leftDrawerOpen = ref(false)
const rightDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

function toggleRightDrawer() {
  rightDrawerOpen.value = !rightDrawerOpen.value
  if (rightDrawerOpen.value && links.value.length === 0) void loadLinks()
}

// ── 링크 사이드바 ──────────────────────────────────────────────────────────────
const links = ref<Link[]>([])
const linksLoading = ref(false)
const linkEditMode = ref(false)
const linkDialog = ref(false)
const linkSaving = ref(false)
const linkForm = ref({
  id: '',
  title: '',
  url: '',
  type: '',
  color: 'grey',
  note: '',
  tagsInput: '',
  rank: null as number | null,
  is_visible: true,
})

const linkColorMap: Record<string, string> = {
  red: '#f44336',
  pink: '#e91e63',
  purple: '#9c27b0',
  blue: '#2196f3',
  teal: '#009688',
  green: '#4caf50',
  orange: '#ff9800',
  brown: '#795548',
  grey: '#9e9e9e',
}

const bulkImportDialog = ref(false)
const bulkImportFile = ref<File | null>(null)
const bulkImportError = ref('')
const bulkImporting = ref(false)

const LINK_TEMPLATE_HEADERS = ['사이트 이름', 'URL', '서비스 종류', '색상', '설명', '태그(쉼표구분)', '정렬순서', '표시여부(true/false)']
const LINK_COLOR_VALUES = Object.keys(linkColorMap).join(', ')

function openBulkImport() {
  bulkImportFile.value = null
  bulkImportError.value = ''
  bulkImportDialog.value = true
}

function downloadLinkTemplate() {
  import('xlsx').then((XLSX) => {
    const ws = XLSX.utils.aoa_to_sheet([
      LINK_TEMPLATE_HEADERS,
      ['예시 사이트', 'https://example.com', '웹', 'blue', '설명 입력', '태그1,태그2', '1', 'true'],
    ])
    ws['!cols'] = [{ wch: 20 }, { wch: 36 }, { wch: 14 }, { wch: 10 }, { wch: 24 }, { wch: 20 }, { wch: 10 }, { wch: 18 }]
    const note = `색상 가능 값: ${LINK_COLOR_VALUES}`
    XLSX.utils.sheet_add_aoa(ws, [[note]], { origin: 'A4' })
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '링크목록')
    XLSX.writeFile(wb, '링크_일괄등록_템플릿.xlsx')
  }).catch(() => { $q.notify({ type: 'negative', message: '템플릿 생성 실패' }) })
}

async function saveBulkLinks() {
  if (!bulkImportFile.value) return
  bulkImportError.value = ''
  bulkImporting.value = true
  try {
    const XLSX = await import('xlsx')
    const buf = await bulkImportFile.value.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const ws = wb.Sheets[wb.SheetNames[0]!]
    if (!ws) throw new Error('시트를 찾을 수 없습니다.')
    const rows = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1, defval: '' })
    // 헤더 행(0) 제외, 빈 행 제외
    const dataRows = rows.slice(1).filter((r) => r[0] || r[1])
    if (dataRows.length === 0) { bulkImportError.value = '데이터가 없습니다.'; bulkImporting.value = false; return }

    let successCount = 0
    const errors: string[] = []
    for (const r of dataRows) {
      const title = `${r[0] ?? ''}`
      const url = `${r[1] ?? ''}`
      if (!title || !url) { errors.push(`사이트 이름/URL 누락 (행: ${JSON.stringify(r)})`); continue }
      try {
        await createLink({
          title,
          url,
          type: `${r[2] ?? ''}`,
          color: r[3] ? `${r[3]}` : 'grey',
          note: r[4] ? `${r[4]}` : null,
          tags: r[5] ? `${r[5]}`.split(',').map((t) => t.trim()).filter(Boolean) : [],
          rank: r[6] ? Number(r[6]) || null : null,
          is_visible: `${r[7]}`.toLowerCase() !== 'false',
        })
        successCount++
      } catch {
        errors.push(`등록 실패: ${title}`)
      }
    }
    await loadLinks()
    bulkImportDialog.value = false
    $q.notify({
      type: errors.length === 0 ? 'positive' : 'warning',
      message: `${successCount}개 등록 완료${errors.length ? `, ${errors.length}개 실패` : ''}`,
      timeout: 4000,
    })
    if (errors.length) console.warn('[일괄등록 오류]', errors)
  } catch (e) {
    bulkImportError.value = `오류: ${(e as Error).message}`
  } finally {
    bulkImporting.value = false
  }
}

const linkColorOptions = Object.entries(linkColorMap).map(([value, hex]) => ({
  value,
  label: { red: '빨강', pink: '분홍', purple: '보라', blue: '파랑', teal: '청록', green: '초록', orange: '주황', brown: '갈색', grey: '회색' }[value] ?? value,
  hex,
}))

const visibleLinks = computed(() => links.value.filter((l) => l.isVisible))

async function loadLinks() {
  linksLoading.value = true
  try {
    links.value = await fetchLinks(true)
  } finally {
    linksLoading.value = false
  }
}

function openLinkCreate() {
  linkForm.value = { id: '', title: '', url: '', type: '', color: 'grey', note: '', tagsInput: '', rank: null, is_visible: true }
  linkDialog.value = true
}

function openLinkEdit(link: Link) {
  linkForm.value = {
    id: link.id,
    title: link.title,
    url: link.url,
    type: link.type,
    color: link.color,
    note: link.note ?? '',
    tagsInput: link.tags.join(', '),
    rank: link.rank ?? null,
    is_visible: link.isVisible,
  }
  linkDialog.value = true
}

async function saveLink() {
  if (!linkForm.value.title || !linkForm.value.url) {
    $q.notify({ type: 'warning', message: '이름과 URL은 필수입니다.' })
    return
  }
  linkSaving.value = true
  try {
    const tags = linkForm.value.tagsInput.split(',').map((t) => t.trim()).filter(Boolean)
    const payload = {
      title: linkForm.value.title,
      url: linkForm.value.url,
      type: linkForm.value.type,
      color: linkForm.value.color,
      note: linkForm.value.note || null,
      tags,
      rank: linkForm.value.rank,
      is_visible: linkForm.value.is_visible,
    }
    if (linkForm.value.id) {
      await patchLink(linkForm.value.id, payload)
    } else {
      await createLink(payload)
    }
    linkDialog.value = false
    await loadLinks()
    $q.notify({ type: 'positive', message: '저장되었습니다.' })
  } catch {
    $q.notify({ type: 'negative', message: '저장 실패' })
  } finally {
    linkSaving.value = false
  }
}

function confirmDeleteLink(link: Link) {
  $q.dialog({
    title: '링크 삭제',
    message: `"${link.title}"을(를) 삭제하시겠습니까?`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void (async () => {
      try {
        await deleteLink(link.id)
        links.value = links.value.filter((l) => l.id !== link.id)
        $q.notify({ type: 'positive', message: '삭제되었습니다.' })
      } catch {
        $q.notify({ type: 'negative', message: '삭제 실패' })
      }
    })()
  })
}

function onLogout() {
  auth.logout()
  leftDrawerOpen.value = false
  void router.replace({ name: 'auth' })
}

watch(
  () => auth.isLoggedIn,
  async (loggedIn) => {
    if (!loggedIn) {
      leftDrawerOpen.value = false
      auth.pendingCount = 0
      if (pendingTimer) { clearInterval(pendingTimer); pendingTimer = null }
      notifStore.stopPolling()
    } else {
      await auth.fetchMe()
      void menuStore.refresh()
      if (auth.me?.isAdmin) {
        void auth.fetchPendingCount()
        pendingTimer = setInterval(() => void auth.fetchPendingCount(true), 30000)
      }
      notifStore.startPolling()
    }
  }
)

onMounted(async () => {
  if (auth.isLoggedIn) {
    await auth.fetchMe()
    void menuStore.refresh()
    if (auth.me?.isAdmin) {
      void auth.fetchPendingCount()
      pendingTimer = setInterval(() => void auth.fetchPendingCount(true), 30000)
    }
    notifStore.startPolling()
  }
})

// 메뉴 관리 페이지에서 벗어날 때 사이드바 메뉴 갱신
watch(
  () => route.path,
  (newPath, oldPath) => {
    if (auth.isLoggedIn && oldPath === '/admin/menus' && newPath !== '/admin/menus') {
      void menuStore.refresh()
    }
  }
)

onBeforeUnmount(() => {
  if (pendingTimer) clearInterval(pendingTimer)
  notifStore.stopPolling()
})
</script>

<style scoped>
.link-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}
.link-card-top {
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.3px;
}
.link-card-body {
  display: block;
  padding: 8px 10px 8px;
  text-decoration: none;
  color: inherit;
}
.link-card-body:hover {
  background: #f5f5f5;
}
.link-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #212121;
  margin-bottom: 3px;
}
.link-card-desc {
  font-size: 11px;
  color: #757575;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.link-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}
.link-tag {
  font-size: 10px;
  color: #1976d2;
  background: #e3f2fd;
  border-radius: 3px;
  padding: 1px 5px;
}
.link-card-actions {
  position: absolute;
  top: 2px;
  right: 4px;
  display: flex;
  gap: 2px;
}
</style>
