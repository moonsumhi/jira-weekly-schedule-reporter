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
      <q-list>
        <q-item-label header>데이터운영팀</q-item-label>

        <EssentialLink
          v-for="link in linksList"
          :key="link.title"
          v-bind="link"
        />
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuthStore } from 'stores/auth'
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'

const auth = useAuthStore()

const linksList: EssentialLinkProps[] = [
  {
    title: 'Jira',
    icon: 'fa-brands fa-jira',
    children: [
      { title: '검색', icon: 'fa-solid fa-list', link: '/jira/search' },
    ],
  },
]

const leftDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

/** close drawer instantly when user logs out (or token becomes null) */
watch(
  () => auth.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn) leftDrawerOpen.value = false
  }
)
</script>
