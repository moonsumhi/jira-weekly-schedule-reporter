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

            <!-- Pilot -->
            <EssentialLink
              title="Pilot"
              icon="fa-solid fa-robot"
              :children="[{ title: '일감 현황', icon: 'fa-solid fa-tasks', link: '/pilot/tasks' }]"
            />

            <!-- Job -->
            <EssentialLink
              title="Job"
              icon="fa-solid fa-briefcase"
              :children="dynamicMenuItems('Job')"
            />

            <!-- 자산 -->
            <EssentialLink
              title="자산"
              icon="fa-solid fa-computer"
              :children="[{ title: '목록', icon: 'fa-solid fa-list', link: '/asset/list' }]"
            />

            <!-- Timetable -->
            <EssentialLink
              title="Timetable"
              icon="fa-solid fa-clock"
              :children="[
                { title: '당직 시간표', icon: 'fa-regular fa-thumbs-up', link: '/watch/timetable' },
                ...dynamicMenuItems('Timetable'),
              ]"
            />

            <!-- Admin -->
            <EssentialLink
              title="Admin"
              icon="fa-solid fa-hammer"
              :children="[{ title: '회원가입 승인', icon: 'fa-regular fa-thumbs-up', link: '/admin/approvals' }]"
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
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth'
import EssentialLink, { type EssentialLinkProps } from 'components/EssentialLink.vue'
import { formTemplateService } from 'src/services/formTemplates'

const auth = useAuthStore()
const router = useRouter()

type TemplateMenuItem = { title: string; icon: string; link: string; menu: string }

const templateItems = ref<TemplateMenuItem[]>([])

async function loadFormTemplates() {
  try {
    const templates = await formTemplateService.list()
    if (!Array.isArray(templates)) return
    templateItems.value = templates
      .filter((t) => !!t.menu)
      .map((t) => ({
        title: t.title,
        icon: 'fa-solid fa-file-alt',
        link: `/job/forms/${t.id}`,
        menu: t.menu as string,
      }))
  } catch (e) {
    console.error('[menu] loadFormTemplates failed:', e)
  }
}

function dynamicMenuItems(menuName: string): EssentialLinkProps[] {
  return templateItems.value.filter(
    (item) => item.menu.toLowerCase() === menuName.toLowerCase()
  )
}

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
  (loggedIn) => {
    if (!loggedIn) leftDrawerOpen.value = false
    else void loadFormTemplates()
  }
)

onMounted(() => {
  if (auth.isLoggedIn) void loadFormTemplates()
})
</script>
