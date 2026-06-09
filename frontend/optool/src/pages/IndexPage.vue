<template>
  <q-page class="home-page">

    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-overlay" />
      <div class="hero-content">
        <img src="~assets/logo.png" alt="국가암데이터센터" class="hero-logo" />
        <h1 class="hero-title">데이터운영팀 백오피스</h1>
      </div>
    </div>

    <!-- Service Cards -->
    <div class="services-section">
      <div class="section-header">
        <span class="section-bar" />
        <span class="section-title">주요 서비스</span>
      </div>
      <div class="cards-grid">
        <div
          class="service-card"
          v-for="menu in menus"
          :key="menu.path"
          @click="$router.push(menu.path)"
        >
          <div class="card-icon-wrap" :style="{ background: menu.bg }">
            <q-icon :name="menu.icon" size="32px" color="white" />
          </div>
          <div class="card-body">
            <div class="card-title">{{ menu.title }}</div>
            <div class="card-desc">{{ menu.desc }}</div>
          </div>
          <q-icon name="chevron_right" size="20px" color="grey-4" class="card-arrow" />
        </div>
      </div>
    </div>

  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useMenuStore } from 'stores/menus'

const menuStore = useMenuStore()

onMounted(async () => {
  if (!menuStore.templateItems.length) {
    await menuStore.loadTemplates()
  }
})

const workPlanLink = computed(() => {
  const item = menuStore.templateItems.find((t) =>
    t.title.includes('계획서') && t.title.includes('서비스') && !t.title.includes('서비스 외') && !t.title.includes('서비스외')
  )
  return item?.link ?? '/job/forms'
})

const menus = computed(() => [
  {
    path: '/jira/search',
    icon: 'search',
    bg: 'linear-gradient(135deg, #1565c0, #1e88e5)',
    title: 'Jira 티켓 검색',
    desc: '담당자별 작업 현황 조회'
  },
  {
    path: '/report/weekly',
    icon: 'summarize',
    bg: 'linear-gradient(135deg, #4527a0, #7e57c2)',
    title: '주간 보고서',
    desc: '주간 업무 보고서 생성'
  },
  {
    path: '/asset/list',
    icon: 'dns',
    bg: 'linear-gradient(135deg, #00695c, #26a69a)',
    title: '서버 자산 관리',
    desc: '서버 자산 현황 및 이력'
  },
  {
    path: '/watch/timetable',
    icon: 'schedule',
    bg: 'linear-gradient(135deg, #e65100, #ff8f00)',
    title: '당직 일정',
    desc: '당직 근무 일정 관리'
  },
  {
    path: '/inspection/checklist',
    icon: 'checklist',
    bg: 'linear-gradient(135deg, #ad1457, #e91e8c)',
    title: '서버실 점검',
    desc: '서버실 점검 체크리스트'
  },
  {
    path: workPlanLink.value,
    icon: 'assignment',
    bg: 'linear-gradient(135deg, #1b5e20, #43a047)',
    title: '작업 계획서(서비스)',
    desc: '서비스 작업 계획서 작성'
  }
])
</script>

<style scoped>
.home-page {
  background: #f4f6f9;
  min-height: 100vh;
}

/* Hero */
.hero-section {
  position: relative;
  height: 280px;
  background: linear-gradient(135deg, #2458b6 0%, #a68fca 50%, #d8abc8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.15);
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0px;
}

.hero-logo {
  height: 230px;
  object-fit: contain;
}

.hero-title {
  color: #ffffff;
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  margin-top: -60px;
  letter-spacing: 2px;
}

.hero-desc {
  color: rgba(255, 255, 255, 0.65);
  font-size: 14px;
  margin: 0;
  letter-spacing: 1px;
}

/* Services */
.services-section {
  max-width: 1000px;
  margin: 0 auto;
  padding: 48px 24px 64px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.section-bar {
  display: inline-block;
  width: 4px;
  height: 22px;
  background: #1565c0;
  border-radius: 2px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a237e;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 600px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
}

.service-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  border: 1px solid #e8edf5;
  transition: transform 0.15s, box-shadow 0.15s;
}

.service-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(21, 101, 192, 0.12);
}

.card-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a237e;
}

.card-desc {
  font-size: 12px;
  color: #90a4ae;
  margin-top: 3px;
}

.card-arrow {
  flex-shrink: 0;
}
</style>
