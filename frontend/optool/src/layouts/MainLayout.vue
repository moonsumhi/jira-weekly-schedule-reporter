<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
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

        <q-toolbar-title>OPTOOL</q-toolbar-title>

        <div>OPTOOL v1.0</div>
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
            <q-item-label header class="cursor-pointer" @click="$router.push('/app')">데이터운영팀</q-item-label>

            <!-- 모든 메뉴를 sortOrder 순서대로 렌더링 -->
            <template v-for="menu in sortedVisibleMenus" :key="menu.id">
              <!-- Jira -->
              <EssentialLink
                v-if="menu.slug === 'jira' && (hasPerm('jira_search') || hasPerm('weekly_report'))"
                :title="menu.title"
                :icon="menu.icon"
                :children="applySubOrder([
                  ...(hasPerm('jira_search') ? [{ title: '검색', icon: menu.subIcons?.['/jira/search'] ?? 'fa-solid fa-list', link: '/jira/search' }] : []),
                  ...(hasPerm('weekly_report') ? [{ title: '주간보고', icon: menu.subIcons?.['/report/weekly'] ?? 'fa-solid fa-calendar-week', link: '/report/weekly' }] : []),
                ], menu)"
              />


              <!-- Job -->
              <EssentialLink
                v-else-if="menu.slug === 'job'"
                :title="menu.title"
                :icon="menu.icon"
                :children="jobMenuItems"
              />

              <!-- 자산 -->
              <EssentialLink
                v-else-if="menu.slug === 'asset' && hasPerm('asset_list')"
                :title="menu.title"
                :icon="menu.icon"
                :children="applySubOrder([
                  { title: '전체',          icon: menu.subIcons?.['/asset/list']                      ?? 'fa-solid fa-layer-group',   link: '/asset/list' },
                  { title: '서버',          icon: menu.subIcons?.['/asset/list?category=서버']         ?? 'fa-solid fa-server',        link: '/asset/list?category=서버' },
                  { title: '네트워크',      icon: menu.subIcons?.['/asset/list?category=네트워크']     ?? 'fa-solid fa-network-wired', link: '/asset/list?category=네트워크' },
                  { title: '정보보호시스템', icon: menu.subIcons?.['/asset/list?category=정보보호시스템'] ?? 'fa-solid fa-shield-halved', link: '/asset/list?category=정보보호시스템' },
                  { title: 'DBMS',         icon: menu.subIcons?.['/asset/list?category=DBMS']         ?? 'fa-solid fa-database',       link: '/asset/list?category=DBMS' },
                  { title: 'VMware',       icon: menu.subIcons?.['/asset/list?category=VMware']       ?? 'fa-brands fa-vuejs',         link: '/asset/list?category=VMware' },
                ], menu)"
              />

              <!-- Timetable -->
              <EssentialLink
                v-else-if="menu.slug === 'watch' && hasPerm('watch_timetable')"
                :title="menu.title"
                :icon="menu.icon"
                link="/watch/timetable"
              />

              <!-- Google 캘린더 -->
              <EssentialLink
                v-else-if="menu.slug === 'calendar'"
                :title="menu.title"
                :icon="menu.icon"
                link="/calendar"
              />

              <!-- 계정 설정 -->
              <EssentialLink
                v-else-if="menu.slug === 'account'"
                :title="menu.title"
                :icon="menu.icon"
                :children="[{ title: '내 계정', icon: menu.subIcons?.['/account/settings'] ?? 'fa-solid fa-user', link: '/account/settings' }]"
              />

              <!-- 서버실 점검 -->
              <EssentialLink
                v-else-if="menu.slug === 'inspection' && hasPerm('inspection_checklist')"
                :title="menu.title"
                :icon="menu.icon"
                link="/inspection/checklist"
              />

              <!-- 서버점검 (월1회) -->
              <EssentialLink
                v-else-if="menu.slug === 'server_check' && hasPerm('health_report')"
                :title="menu.title"
                :icon="menu.icon"
                :children="applySubOrder([
                  { title: '요약', icon: menu.subIcons?.['/inspection/health-summary'] ?? 'fa-solid fa-table-list', link: '/inspection/health-summary' },
                  { title: '서버리스트', icon: menu.subIcons?.['/inspection/health-servers'] ?? 'fa-solid fa-server', link: '/inspection/health-servers' },
                  { title: '월별 비교', icon: menu.subIcons?.['/inspection/health-compare'] ?? 'fa-solid fa-code-compare', link: '/inspection/health-compare' },
                ], menu)"
              />

              <!-- Admin -->
              <EssentialLink
                v-else-if="menu.slug === 'admin' && auth.me?.isAdmin"
                :title="menu.title"
                :icon="menu.icon"
                :badge="pendingCount"
                :children="applySubOrder([
                  { title: '회원가입 승인', icon: menu.subIcons?.['/admin/approvals'] ?? 'fa-regular fa-thumbs-up', link: '/admin/approvals', badge: pendingCount },
                  { title: '회원 목록', icon: menu.subIcons?.['/admin/users'] ?? 'fa-solid fa-users', link: '/admin/users' },
                  { title: 'Audit Log', icon: menu.subIcons?.['/admin/audit-log'] ?? 'fa-solid fa-clock-rotate-left', link: '/admin/audit-log' },
                  { title: '자산 로그', icon: menu.subIcons?.['/admin/asset-log'] ?? 'fa-solid fa-server', link: '/admin/asset-log' },
                ], menu)"
              />

              <!-- 동적 메뉴 (관리자가 추가한 메뉴 > 게시판) -->
              <EssentialLink
                v-else-if="!menu.slug"
                :title="menu.title"
                :icon="menu.icon"
                :children="boardChildrenOf(menu.id)"
              />
            </template>
          </q-list>
        </q-scroll-area>

        <!-- LOGOUT AREA (BOTTOM) -->
        <q-separator />

        <q-list>
          <q-item clickable v-ripple @click="onLogout">
            <q-item-section avatar>
              <q-icon name="logout" color="negative" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-negative">
                로그아웃
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </q-drawer>
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
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'

const auth = useAuthStore()
const menuStore = useMenuStore()
const { sidebarMenus, sidebarBoards, templateItems } = storeToRefs(menuStore)
const router = useRouter()
const route = useRoute()

function hasPerm(perm: string): boolean {
  if (auth.me?.isAdmin) return true
  return (auth.me?.permissions ?? []).includes(perm)
}

const sortedVisibleMenus = computed(() => {
  const isInternal = auth.me?.isInternal !== false
  return sidebarMenus.value
    .filter((m) => m.isVisible && (isInternal ? m.isInternalVisible !== false : m.isExternalVisible))
    .sort((a, b) => (a.sortOrder ?? Infinity) - (b.sortOrder ?? Infinity))
})

function applySubOrder<T extends { link: string }>(items: T[], menu: { subOrder?: string[] | null }): T[] {
  if (!menu.subOrder || menu.subOrder.length === 0) return items
  const orderMap = new Map(menu.subOrder.map((link, i) => [link, i]))
  const ordered = items.filter((item) => orderMap.has(item.link))
    .sort((a, b) => (orderMap.get(a.link) ?? Infinity) - (orderMap.get(b.link) ?? Infinity))
  const unordered = items.filter((item) => !orderMap.has(item.link))
  return [...ordered, ...unordered]
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

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
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
    } else {
      await auth.fetchMe()
      void menuStore.refresh()
      if (auth.me?.isAdmin) {
        void auth.fetchPendingCount()
        pendingTimer = setInterval(() => void auth.fetchPendingCount(), 30000)
      }
    }
  }
)

onMounted(async () => {
  if (auth.isLoggedIn) {
    await auth.fetchMe()
    void menuStore.refresh()
    if (auth.me?.isAdmin) {
      void auth.fetchPendingCount()
      pendingTimer = setInterval(() => void auth.fetchPendingCount(), 30000)
    }
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
})
</script>
