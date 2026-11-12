<template>
  <q-layout view="lHh Lpr lFf" class="backoffice-layout">
    <a class="skip-to-content" href="#workspace-content" @click.prevent="focusWorkspace">본문으로 이동</a>
    <q-header class="workspace-header">
      <q-toolbar class="workspace-toolbar">
        <!-- menu button only when logged in -->
        <q-btn
          v-if="authIsLoggedIn"
          flat
          dense
          round
          icon="menu"
          :aria-label="miniDrawer ? '사이드바 펼치기' : (isNarrowLayout ? '메뉴 열기' : '사이드바 접기')"
          :title="miniDrawer ? '사이드바 펼치기' : (isNarrowLayout ? '메뉴 열기' : '사이드바 접기')"
          :aria-expanded="leftDrawerOpen && !miniDrawer"
          aria-controls="workspace-navigation"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title class="workspace-location">
          <span v-if="auth.isLoggedIn" class="workspace-location-team">데이터운영팀 <span aria-hidden="true">/</span></span>
          <span>{{ auth.isLoggedIn ? currentPageTitle : theme.appName }}</span>
        </q-toolbar-title>

        <span class="workspace-version">v1.2.0</span>

        <!-- 알림 벨 -->
        <NotificationBell v-if="authIsLoggedIn" class="q-ml-xs" />

        <!-- AI 채팅 -->
        <q-btn
          v-if="authIsLoggedIn && (authMe?.isAdmin || authMe?.permissions?.includes('ai_access'))"
          flat dense round
          icon="smart_toy"
          aria-label="AI 채팅"
          class="q-ml-xs"
          :color="aiChatOpen ? 'primary' : undefined"
          :aria-pressed="aiChatOpen"
          @click="aiChatOpen = !aiChatOpen"
        >
          <q-tooltip>AI 어시스턴트</q-tooltip>
        </q-btn>

        <!-- 링크 사이드바 토글 (내부망만) -->
        <q-btn
          v-if="authIsLoggedIn && !isExternal"
          flat dense round
          icon="fa-solid fa-link"
          aria-label="서비스 바로가기"
          :aria-expanded="rightDrawerOpen"
          class="q-ml-sm"
          @click="toggleRightDrawer"
        />
      </q-toolbar>
    </q-header>

    <!-- drawer only when logged in -->
    <q-drawer
      v-if="authIsLoggedIn"
      class="app-sidebar workspace-drawer"
      v-model="leftDrawerOpen"
      show-if-above
      bordered
      :dark="theme.appearanceMode === 'dark'"
      :style="theme.appearanceMode === 'dark' ? { backgroundColor: '#17212f' } : undefined"
      :mini="miniDrawer"
      :mini-width="80"
      :width="248"
      :breakpoint="1024"
      :behavior="isNarrowLayout ? 'mobile' : 'desktop'"
    >
      <!-- column layout to pin logout button at bottom -->
      <div id="workspace-navigation" class="column no-wrap fit"
        :class="{ 'sidebar-dark': theme.appearanceMode === 'dark' }"
        :style="{ backgroundColor: theme.appearanceMode === 'dark' ? '#17212f' : theme.sidebarBackgroundColor }">
        <div class="workspace-brand-row">
          <button class="workspace-brand" type="button" :aria-label="`${theme.appName} 홈으로 이동`" @click="goHome">
            <q-icon :name="sidebarIcons.brand" size="28px" color="primary" aria-hidden="true" />
            <span v-if="!miniDrawer" class="workspace-brand-copy">
              <span class="workspace-brand-name">{{ theme.appName }}</span>
              <span class="workspace-brand-team">데이터운영팀 백오피스</span>
            </span>
          </button>
          <q-btn flat round dense :icon="sidebarIcons.close" class="workspace-nav-close" aria-label="메뉴 닫기" @click="leftDrawerOpen = false" />
        </div>

        <!-- MENU AREA -->
        <q-scroll-area class="col workspace-nav-scroll" :content-style="{ width: '100%', boxSizing: 'border-box' }">
          <nav ref="navigationElement" aria-label="주 메뉴" class="workspace-navigation">
          <q-list class="sidebar-menu-list" :dark="theme.appearanceMode === 'dark'">
            <q-item clickable v-ripple :active="route.name === 'app-home'" active-class="workspace-home--active" class="workspace-home" to="/app" :aria-current="route.name === 'app-home' ? 'page' : undefined">
              <q-item-section avatar><q-icon :name="sidebarIcons.dashboard" size="20px" /></q-item-section>
              <q-item-section>대시보드</q-item-section>
            </q-item>
            <q-separator class="workspace-nav-separator" />

            <!-- 모든 메뉴를 sortOrder 순서대로 렌더링 -->
            <template v-for="menu in sortedVisibleMenus" :key="menu.id">
              <!-- Job: form template 기반 동적 하위 메뉴 -->
              <EssentialLink
                v-if="menu.slug === 'job'"
                :title="menu.title"
                :icon="menu.icon"
                :color="menu.color ?? '#000000'"
                :icon-color="menu.iconColor ?? menu.color ?? '#000000'"
                :compact="miniDrawer"
                :children="jobMenuItems"
                @expand-sidebar="expandSidebar"
              />

              <!-- Admin: 승인 대기 badge 포함 -->
              <EssentialLink
                v-else-if="menu.slug === 'admin'"
                :title="menu.title"
                :icon="menu.icon"
                :color="menu.color ?? '#000000'"
                :icon-color="menu.iconColor ?? menu.color ?? '#000000'"
                :compact="miniDrawer"
                :badge="pendingCount"
                :children="menuChildren(menu, '/admin/approvals')"
                @expand-sidebar="expandSidebar"
              />

              <!-- leaf 링크 메뉴 -->
              <EssentialLink
                v-else-if="menu.link"
                :title="menu.title"
                :icon="menu.icon"
                :color="menu.color ?? '#000000'"
                :icon-color="menu.iconColor ?? menu.color ?? '#000000'"
                :compact="miniDrawer"
                :link="menu.link"
                @expand-sidebar="expandSidebar"
              />

              <!-- DB submenus 기반 메뉴 -->
              <EssentialLink
                v-else-if="menu.submenus?.length"
                :title="menu.title"
                :icon="menu.icon"
                :color="menu.color ?? '#000000'"
                :icon-color="menu.iconColor ?? menu.color ?? '#000000'"
                :compact="miniDrawer"
                :children="menuChildren(menu)"
                @expand-sidebar="expandSidebar"
              />

              <!-- 동적 게시판 메뉴 (관리자가 추가한 메뉴) -->
              <EssentialLink
                v-else
                :title="menu.title"
                :icon="menu.icon"
                :color="menu.color ?? '#000000'"
                :icon-color="menu.iconColor ?? menu.color ?? '#000000'"
                :compact="miniDrawer"
                :children="boardChildrenOf(menu.id)"
                @expand-sidebar="expandSidebar"
              />
            </template>

          </q-list>
          </nav>
        </q-scroll-area>

        <!-- USER / LOGOUT AREA (BOTTOM) -->
        <div class="workspace-account">
          <q-item clickable v-ripple to="/account/my-page" class="workspace-account-link"
            active-class="workspace-account-link--active" aria-label="마이페이지">
            <q-item-section avatar>
              <q-avatar size="36px" class="workspace-account-avatar">
                {{ auth.me?.fullName?.[0] ?? auth.me?.email?.[0]?.toUpperCase() ?? '?' }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="workspace-account-name" :title="auth.me?.fullName ?? undefined">{{ auth.me?.fullName ?? '-' }}</q-item-label>
              <q-item-label caption :title="auth.me?.email">{{ auth.me?.email }}</q-item-label>
            </q-item-section>
            <q-tooltip>마이페이지</q-tooltip>
          </q-item>
          <q-btn v-if="!miniDrawer" flat round dense :icon="sidebarIcons.logout" aria-label="로그아웃" class="workspace-logout" @click="onLogout">
            <q-tooltip>로그아웃</q-tooltip>
          </q-btn>
        </div>
      </div>
    </q-drawer>
    <!-- 오른쪽 링크 사이드바 (내부망만) -->
    <q-drawer
      v-if="authIsLoggedIn && !isExternal"
      v-model="rightDrawerOpen"
      side="right"
      bordered
      :width="280"
    >
      <div class="column fit">
        <div class="row items-center q-px-md q-py-sm">
          <div class="text-subtitle1 text-weight-bold col">서비스 바로가기</div>
          <q-btn v-if="authMe?.isAdmin" flat dense round icon="add" size="sm" @click="openLinkCreate" />
          <q-btn v-if="authMe?.isAdmin" flat dense round icon="playlist_add" size="sm" color="grey" title="일괄 등록" @click="openBulkImport" />
          <q-btn v-if="authMe?.isAdmin" flat dense round :icon="linkEditMode ? 'close' : 'edit'" size="sm" color="grey" @click="linkEditMode = !linkEditMode" />
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
              <div v-if="linkEditMode && authMe?.isAdmin" class="link-card-actions">
                <q-btn flat dense round icon="edit" size="xs" color="grey" @click.stop="openLinkEdit(link)" />
                <q-btn flat dense round icon="delete" size="xs" color="negative" @click.stop="confirmDeleteLink(link)" />
              </div>
            </div>
          </div>
        </q-scroll-area>
      </div>
    </q-drawer>

    <!-- 링크 추가/수정 다이얼로그 -->
    <q-dialog v-model="linkDialog" no-backdrop-dismiss no-route-dismiss>
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
              <span class="q-mr-sm" :style="{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '2px', backgroundColor: linkColorFor(opt.value) }"></span>
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
    <q-dialog v-model="bulkImportDialog" no-backdrop-dismiss no-route-dismiss>
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

    <q-page-container id="workspace-content" tabindex="-1" :class="{ 'pm-theme-container': isScheduleManagementRoute }">
      <router-view />
    </q-page-container>

    <NoticePopup v-if="authIsLoggedIn" />

    <AiChatPanel :open="aiChatOpen" @close="aiChatOpen = false" />

    <IssueDetailDialog
      v-if="activeIssue"
      v-model="issueDialogOpen"
      :project-id="activeIssue.projectId"
      :project-key="activeIssue.projectKey ?? ''"
      :issue="activeIssue"
      :initial-comment-id="initialCommentId"
    />
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from 'stores/auth'
import { useMenuStore } from 'stores/menus'
import { useThemeStore } from 'stores/theme'
import { useNotificationStore } from 'stores/notification'
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'
import { sidebarIcons } from 'src/utils/sidebarIcons'
import NotificationBell from 'components/NotificationBell.vue'
import NoticePopup from 'components/NoticePopup.vue'
import AiChatPanel from 'components/AiChatPanel.vue'
import IssueDetailDialog from 'src/pages/pm/components/IssueDetailDialog.vue'
import { useIssueDialogStore } from 'stores/issueDialog'
import type { MenuOut } from 'src/services/menus'
import { useQuasar } from 'quasar'
import { fetchLinks, createLink, patchLink, deleteLink, type Link } from 'src/services/links'
import { SLUG_PERM } from 'src/constants/menuPermissions'
import { api } from 'boot/axios'

const auth = useAuthStore()
const menuStore = useMenuStore()
const theme = useThemeStore()
const notifStore = useNotificationStore()
const issueDialog = useIssueDialogStore()
const { isLoggedIn: authIsLoggedIn, me: authMe } = storeToRefs(auth)
const {
  issue: activeIssue,
  open: issueDialogOpen,
  initialCommentId,
} = storeToRefs(issueDialog)
const $q = useQuasar()
const { sidebarMenus, sidebarBoards, templateItems } = storeToRefs(menuStore)
const router = useRouter()
const route = useRoute()
const isScheduleManagementRoute = computed(() => route.path.startsWith('/pm'))

function recordHomeVisit() {
  void api.get('/auth/home-ping')
}

function focusWorkspace() {
  document.getElementById('workspace-content')?.focus()
}

function goHome() {
  if (route.name === 'app-home') {
    recordHomeVisit()
    return
  }
  void router.push({ name: 'app-home' })
}

watch(() => route.name, (name) => {
  if (name === 'app-home') recordHomeVisit()
}, { immediate: true })

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

const sortedVisibleMenus = computed(() =>
  sidebarMenus.value
    .filter((m) => m.isVisible)
    .filter((m) => m.slug !== 'my-page')
    .filter((m) => m.slug !== 'admin' || !!auth.me?.isAdmin)
    .filter((m) => {
      const perm = SLUG_PERM[m.slug ?? '']
      return perm ? hasPerm(perm) : true  // 권한 필요한 슬러그는 hasPerm 체크
    })
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
      color: menu.subColors?.[s.link] ?? menu.color ?? '#000000',
      iconColor: menu.subIconColors?.[s.link] ?? menu.iconColor ?? menu.subColors?.[s.link] ?? menu.color ?? '#000000',
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
  return boards.map((b) => {
    const link = b.link ?? `/board/${b.id}`
    return {
      title: b.title,
      icon: b.icon ?? 'fa-solid fa-clipboard-list',
      link,
      color: menu?.subColors?.[link] ?? menu?.color ?? '#000000',
      iconColor: menu?.subIconColors?.[link] ?? menu?.iconColor ?? menu?.subColors?.[link] ?? menu?.color ?? '#000000',
    }
  })

}

const jobMenuItems = computed<EssentialLinkProps[]>(() => {
  const menu = sortedVisibleMenus.value.find((m) => m.slug === 'job')
  let items = templateItems.value
    .filter((item) => item.menu.toLowerCase() === 'job')
    .map((item) => ({
      ...item,
      icon: menu?.subIcons?.[item.link] ?? item.icon,
      color: menu?.subColors?.[item.link] ?? menu?.color ?? '#000000',
      iconColor: menu?.subIconColors?.[item.link] ?? menu?.iconColor ?? menu?.subColors?.[item.link] ?? menu?.color ?? '#000000',
    }))
  if (menu?.subOrder && menu.subOrder.length > 0) {
    const orderMap = new Map(menu.subOrder.map((link, i) => [link, i]))
    items = items.filter((item) => orderMap.has(item.link))
    items.sort((a, b) => (orderMap.get(a.link) ?? Infinity) - (orderMap.get(b.link) ?? Infinity))
  }
  return items
})

const currentPageTitle = computed(() => {
  if (route.name === 'app-home') return '대시보드'
  const activePath = typeof route.meta.activeMenuLink === 'string' ? route.meta.activeMenuLink : route.path
  const destinations = sortedVisibleMenus.value.flatMap((menu) => [
    { title: menu.title, link: menu.link },
    ...(menu.slug === 'job' ? jobMenuItems.value : menu.submenus?.length ? menuChildren(menu) : boardChildrenOf(menu.id)),
  ])
  const match = destinations
    .filter((item) => {
      if (!item.link || item.link === '#' || /^https?:/.test(item.link)) return false
      const [path = '', query] = item.link.split('?')
      if (activePath !== path && !activePath.startsWith(`${path}/`)) return false
      return !query || Array.from(new URLSearchParams(query)).every(([key, value]) => route.query[key] === value)
    })
    .sort((a, b) => (b.link?.length ?? 0) - (a.link?.length ?? 0))[0]
  if (match) return match.title
  if (route.path.startsWith('/account')) return '계정 설정'
  if (route.path.startsWith('/notifications')) return '알림'
  return theme.appName
})

const pendingCount = computed(() => auth.pendingCount)
let pendingTimer: ReturnType<typeof setInterval> | null = null

const leftDrawerOpen = ref(false)
const rightDrawerOpen = ref(false)
const aiChatOpen = ref(false)
const sidebarMini = ref(localStorage.getItem('sidebar-mini-mode-v2') !== 'false')
const isNarrowLayout = computed(() => $q.screen.width <= 1024)
const miniDrawer = computed(() => !isNarrowLayout.value && sidebarMini.value)

watch(sidebarMini, (mini) => {
  localStorage.setItem('sidebar-mini-mode-v2', String(mini))
})

const navigationElement = ref<HTMLElement | null>(null)
let navigationRevealTimer: ReturnType<typeof setTimeout> | undefined

function scheduleActiveMenuReveal() {
  if (navigationRevealTimer) clearTimeout(navigationRevealTimer)
  // QExpansionItem opens over 300ms. Scroll its container after the final layout.
  navigationRevealTimer = setTimeout(() => {
    const active = navigationElement.value?.querySelector<HTMLElement>('[aria-current="page"]')
    const viewport = navigationElement.value?.closest<HTMLElement>('.q-scrollarea__container')
    if (!active || !viewport) return
    const item = active.getBoundingClientRect()
    const bounds = viewport.getBoundingClientRect()
    if (item.top < bounds.top + 8) viewport.scrollTop += item.top - bounds.top - 8
    else if (item.bottom > bounds.bottom - 8) viewport.scrollTop += item.bottom - bounds.bottom + 8
  }, 350)
}

watch([() => route.fullPath, sortedVisibleMenus, jobMenuItems, leftDrawerOpen], async () => {
  await nextTick()
  scheduleActiveMenuReveal()
}, { flush: 'post', immediate: true })

function toggleLeftDrawer() {
  if (isNarrowLayout.value) {
    leftDrawerOpen.value = !leftDrawerOpen.value
    return
  }
  sidebarMini.value = !sidebarMini.value
}

function expandSidebar() {
  if (!isNarrowLayout.value) sidebarMini.value = false
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

function linkColorFor(value: unknown): string {
  return typeof value === 'string' ? linkColorMap[value] ?? '#9e9e9e' : '#9e9e9e'
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
    noBackdropDismiss: true, noRouteDismiss: true,
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
      void theme.loadSidebarTheme()
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
    void theme.loadSidebarTheme()
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
    if ($q.screen.width < 1024) leftDrawerOpen.value = false
    if (auth.isLoggedIn && oldPath === '/admin/menus' && newPath !== '/admin/menus') {
      void menuStore.refresh()
    }
  }
)

onBeforeUnmount(() => {
  if (navigationRevealTimer) clearTimeout(navigationRevealTimer)
  if (pendingTimer) clearInterval(pendingTimer)
  notifStore.stopPolling()
})
</script>

<style scoped>
:deep(.q-drawer--left) {
  transition:
    width 180ms cubic-bezier(0.2, 0, 0, 1),
    transform 180ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(.q-page-container) {
  transition: padding-left 180ms cubic-bezier(0.2, 0, 0, 1);
}

:deep(.q-drawer--mini .sidebar-menu-list .q-item) {
  padding-left: 16px;
  padding-right: 0;
}

:deep(.q-drawer--mini .sidebar-menu-list .q-item__section--avatar) {
  width: 56px;
  min-width: 56px;
  margin-left: 0;
  margin-right: 0;
}


#workspace-navigation { font-family: 'Pretendard Variable', var(--bo-font); }
.workspace-header {
  background: var(--bo-surface);
  color: var(--bo-text);
  border-bottom: 1px solid var(--bo-border);
}
.workspace-toolbar {
  min-height: 64px;
  padding: 0 24px;
  gap: 8px;
}
.workspace-location {
  display: flex;
  gap: 14px;
  font-size: 14px;
  font-weight: 600;
}
.workspace-location-team {
  color: var(--bo-muted);
  font-weight: 400;
}
.workspace-location-team > span {
  padding-left: 14px;
  color: var(--bo-border-strong);
}
.workspace-version {
  color: var(--bo-muted);
  font-size: 12px;
  margin-right: 12px;
}
.workspace-brand-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 20px 20px 18px;
  flex-shrink: 0;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}
.workspace-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--bo-text);
  text-align: left;
  cursor: pointer;
  font: inherit;
}
.workspace-brand-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.workspace-brand-name { font-size: 20px; line-height: 1.3; font-weight: 700; letter-spacing: -0.02em; overflow-wrap: anywhere; }
.workspace-brand-team { color: var(--bo-muted); font-size: 12px; line-height: 1.5; }
.workspace-nav-close { display: none; color: var(--bo-muted); flex-shrink: 0; }
.workspace-nav-scroll { min-height: 0; min-width: 0; width: 100%; }
.workspace-navigation { width: 100%; box-sizing: border-box; padding: 4px 12px 20px; }
.workspace-home {
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--bo-secondary);
  font-weight: 500;
  font-size: 14px;
  line-height: 1.45;
  letter-spacing: -0.01em;
}
.workspace-home .q-item__section--avatar { min-width: 32px; padding-right: 12px; }
.workspace-home--active { color: var(--bo-accent-ink); background: var(--bo-accent-soft); font-weight: 600; }
.workspace-nav-separator { margin: 14px 12px; }
.workspace-account { display: flex; align-items: center; gap: 2px; width: 100%; min-width: 0; box-sizing: border-box; padding: 12px; border-top: 1px solid var(--bo-border); flex-shrink: 0; }
.workspace-account-link { flex: 1; min-width: 0; min-height: 56px; padding: 8px; border-radius: 8px; color: var(--bo-text); }
.workspace-account-link--active { background: var(--bo-accent-soft); }
.workspace-account-link :deep(.q-item__section--avatar) { min-width: 46px; padding-right: 10px; }
.workspace-account-link :deep(.q-item__section--main) { min-width: 0; }
.workspace-account-name { font-size: 13px; font-weight: 600; }
.workspace-account-link :deep(.q-item__label) { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.workspace-account-link :deep(.q-item__label--caption) { margin-top: 4px; font-size: 12px; color: var(--bo-muted); }
.workspace-account-avatar { background: var(--bo-accent-soft); color: var(--bo-accent-ink); font-size: 14px; font-weight: 600; }
.workspace-logout { color: var(--bo-muted); width: 36px; height: 36px; flex-shrink: 0; }
.workspace-brand:focus-visible, .workspace-home:focus-visible, .workspace-account-link:focus-visible { outline-offset: -2px; }
@media (max-width: 1024px) {
  .workspace-brand-row { padding-right: 12px; }
  .workspace-nav-close { display: inline-flex; width: 36px; height: 36px; }
}
.skip-to-content {
  position: fixed;
  top: 8px;
  left: 12px;
  z-index: 10000;
  transform: translateY(-180%);
  background: var(--bo-surface);
  color: var(--bo-accent-ink);
  padding: 10px 16px;
  border-radius: 8px;
}
.skip-to-content:focus { transform: translateY(0); }
@media (max-width: 599px) {
  .workspace-toolbar { min-height: 56px; padding: 0 12px; gap: 2px; }
  .workspace-location { padding: 0 6px; }
  .workspace-location-team, .workspace-version { display: none; }
}
@media print {
  .skip-to-content { display: none; }
}
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

:deep(.q-drawer--mini .workspace-brand-row) { padding: 20px 16px 18px; }
:deep(.q-drawer--mini .workspace-brand) { justify-content: center; }
:deep(.q-drawer--mini .workspace-navigation) { padding: 4px 8px 20px; }
:deep(.q-drawer--mini .sidebar-menu-list .q-item) { padding: 10px 12px; }
:deep(.q-drawer--mini .sidebar-menu-list .q-item__section--avatar) { min-width: 0; width: 100%; padding: 0; align-items: center; }
:deep(.q-drawer--mini .workspace-account) { padding: 8px; }
:deep(.q-drawer--mini .workspace-account-link .q-item__section--avatar) { min-width: 36px; padding: 0; }
</style>
