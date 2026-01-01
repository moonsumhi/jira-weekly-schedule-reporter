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

        <div>Quasar v{{ $q.version }}</div>
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

            <EssentialLink
              v-for="link in linksList"
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

const linksList: EssentialLinkProps[] = [
  {
    title: 'Jira',
    icon: 'fa-brands fa-jira',
    children: [
      { title: '검색', icon: 'fa-solid fa-list', link: '/jira/search' },
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
