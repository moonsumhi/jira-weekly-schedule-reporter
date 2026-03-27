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
            <q-item-label header>데이터운영팀</q-item-label>

            <!-- Jira 섹션 -->
            <q-expansion-item icon="fa-brands fa-jira" label="Jira" expand-separator>
              <EssentialLink title="검색" icon="fa-solid fa-list" link="/jira/search" />
              <EssentialLink title="주간보고" icon="fa-solid fa-calendar-week" link="/report/weekly" />
            </q-expansion-item>

            <!-- 나머지 메뉴 -->
            <EssentialLink
              v-for="link in staticLinks"
              :key="link.title"
              v-bind="link"
            />
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
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'

const auth = useAuthStore()
const router = useRouter()

const staticLinks: EssentialLinkProps[] = [
  {
    title: 'Pilot',
    icon: 'fa-solid fa-robot',
    children: [
      { title: '일감 현황', icon: 'fa-solid fa-tasks', link: '/pilot/tasks' },
    ],
  },
  {
    title: '자산',
    icon: 'fa-solid fa-computer',
    children: [
      { title: '목록', icon: 'fa-solid fa-list', link: '/asset/list' },
    ],
  },
  {
    title: 'Timetable',
    icon: 'fa-solid fa-clock',
    children: [
      { title: '당직 시간표', icon: 'fa-regular fa-thumbs-up', link: '/watch/timetable' },
    ],
  },
  {
    title: 'Job',
    icon: 'fa-solid fa-file-alt',
    children: [
      { title: '작업계획서 (서비스)', icon: 'fa-solid fa-clipboard-list', link: '/job/service-work-plan' },
      { title: '작업계획서 (서비스 외)', icon: 'fa-solid fa-clipboard', link: '/job/non-service-work-plan' },
      { title: '작업결과서', icon: 'fa-solid fa-file-circle-check', link: '/job/service-work-result' },
    ],
  },
  {
    title: 'test',
    icon: 'fa-solid fa-flask',
    children: [
      { title: 'test1', icon: 'fa-solid fa-vial', link: '/test/test1' },
      { title: 'test2', icon: 'fa-solid fa-vial-circle-check', link: '/test/test2' },
      { title: 'test3', icon: 'fa-solid fa-file-pdf', link: '/test/test3' },
      { title: 'test4', icon: 'fa-solid fa-file-lines', link: '/test/test4' },
      { title: 'test5', icon: 'fa-solid fa-wand-magic-sparkles', link: '/test/test5' },
      { title: 'test6', icon: 'fa-solid fa-file-pen', link: '/test/test6' },
      { title: 'test7', icon: 'fa-solid fa-database', link: '/test/test7' },
    ],
  },
  {
    title: 'Admin',
    icon: 'fa-solid fa-hammer',
    children: [
      { title: '회원가입 승인', icon: 'fa-regular fa-thumbs-up', link: '/admin/approvals' },
    ],
  },
]

const leftDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

function onLogout() {
  auth.logout()
  leftDrawerOpen.value = false
  void router.replace({ name: 'auth' }) // 로그인 페이지로
}

/** close drawer instantly when user logs out (or token becomes null) */
watch(
  () => auth.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn) leftDrawerOpen.value = false
  }
)

</script>
