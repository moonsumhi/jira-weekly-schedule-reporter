<template>
  <q-page padding>
    <div class="text-h6 q-mb-md">ISMS-P 취약점 대시보드</div>

    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-6 col-md-3">
        <StatTile label="전체 취약점" :value="stats.total" icon="fa-solid fa-bug" color="primary" />
      </div>
      <div class="col-6 col-md-3">
        <StatTile label="취약 건수" :value="stats.statusCounts['취약'] ?? 0" icon="fa-solid fa-triangle-exclamation" color="negative" />
      </div>
      <div class="col-6 col-md-3">
        <StatTile label="양호 건수" :value="stats.statusCounts['양호'] ?? 0" icon="fa-solid fa-circle-check" color="positive" />
      </div>
      <div class="col-6 col-md-3">
        <StatTile label="리뷰 건수" :value="stats.statusCounts['리뷰'] ?? 0" icon="fa-solid fa-magnifying-glass" color="orange" />
      </div>
    </div>

    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">통제여부 현황</div>
            <canvas ref="controlChartEl" height="147"></canvas>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">자산종류별 취약점 수</div>
            <canvas ref="assetChartEl" height="147"></canvas>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">위험도별 현황</div>
            <canvas ref="riskChartEl" height="147"></canvas>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">월별 목표 조치건수 vs 실제 조치건수</div>
            <canvas ref="progressChartEl" height="80"></canvas>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">담당자별 조치 현황</div>
            <canvas ref="assigneeChartEl" height="147"></canvas>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">담당자별 상세</div>
            <q-table
              :rows="assigneeStats"
              :columns="assigneeColumns"
              row-key="assignee"
              flat dense
              hide-bottom
              :rows-per-page-options="[0]"
            >
              <template #body-cell-completionRate="props">
                <q-td :props="props">
                  <q-linear-progress
                    :value="props.row.completionRate / 100"
                    :color="props.row.completionRate >= 50 ? 'positive' : 'grey'"
                    size="16px"
                    rounded
                  >
                    <div class="absolute-full flex flex-center">
                      <span class="text-caption text-white">{{ props.row.completionRate }}%</span>
                    </div>
                  </q-linear-progress>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, defineComponent, h } from 'vue'
import {
  Chart, ArcElement, BarElement, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend,
  DoughnutController, BarController, LineController,
} from 'chart.js'
import {
  getStats, getAssigneeStats, getActionProgress,
  type StatsOut, type AssigneeStat,
} from 'src/services/isms/vulnerability'

Chart.register(
  ArcElement, BarElement, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend,
  DoughnutController, BarController, LineController,
)

const StatTile = defineComponent({
  props: { label: String, value: Number, icon: String, color: String },
  setup(props) {
    return () => h('div', { class: `stat-tile bg-${props.color}-1` }, [
      h('div', { class: 'text-caption text-grey-8' }, props.label),
      h('div', { class: 'text-h5 text-weight-bold' }, String(props.value ?? 0)),
      h('q-icon', { name: props.icon, class: 'stat-tile-icon', color: props.color }),
    ])
  },
})

const stats = ref<StatsOut>({ total: 0, statusCounts: {}, assetCounts: {}, riskCounts: {} })
const assigneeStats = ref<AssigneeStat[]>([])

const assigneeColumns = [
  { name: 'assignee', label: '담당자', field: 'assignee', align: 'left' as const },
  { name: 'total', label: '전체', field: 'total', align: 'center' as const },
  { name: 'completed', label: '완료', field: 'completed', align: 'center' as const },
  { name: 'todo', label: '미조치', field: 'todo', align: 'center' as const },
  { name: 'completionRate', label: '완료율', field: 'completionRate', align: 'center' as const },
]

const controlChartEl = ref<HTMLCanvasElement | null>(null)
const assetChartEl = ref<HTMLCanvasElement | null>(null)
const riskChartEl = ref<HTMLCanvasElement | null>(null)
const progressChartEl = ref<HTMLCanvasElement | null>(null)
const assigneeChartEl = ref<HTMLCanvasElement | null>(null)

let charts: Chart[] = []

function destroyCharts() {
  charts.forEach((c) => c.destroy())
  charts = []
}

async function loadAndRender() {
  destroyCharts()

  const [statsData, assigneeData, progressData] = await Promise.all([
    getStats(), getAssigneeStats(), getActionProgress(),
  ])
  stats.value = statsData
  assigneeStats.value = assigneeData

  if (controlChartEl.value) {
    const sc = statsData.statusCounts
    charts.push(new Chart(controlChartEl.value, {
      type: 'doughnut',
      data: {
        labels: ['양호', '취약', '리뷰', '해당없음'],
        datasets: [{
          data: [sc['양호'] ?? 0, sc['취약'] ?? 0, sc['리뷰'] ?? 0, sc['해당없음'] ?? 0],
          backgroundColor: ['#22c55e', '#ef4444', '#f97316', '#9e9e9e'],
        }],
      },
      options: { responsive: true },
    }))
  }

  if (assetChartEl.value) {
    const ac = statsData.assetCounts
    charts.push(new Chart(assetChartEl.value, {
      type: 'bar',
      data: {
        labels: Object.keys(ac),
        datasets: [{ label: '취약점 수', data: Object.values(ac), backgroundColor: '#3b82f6' }],
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } },
    }))
  }

  if (riskChartEl.value) {
    const rc = statsData.riskCounts
    charts.push(new Chart(riskChartEl.value, {
      type: 'doughnut',
      data: {
        labels: ['상', '중', '하'],
        datasets: [{ data: [rc['상'] ?? 0, rc['중'] ?? 0, rc['하'] ?? 0], backgroundColor: ['#ef4444', '#f97316', '#facc15'] }],
      },
      options: { responsive: true },
    }))
  }

  if (progressChartEl.value) {
    charts.push(new Chart(progressChartEl.value, {
      type: 'line',
      data: {
        labels: progressData.labels,
        datasets: [
          { label: '목표', data: progressData.target, borderColor: '#3b82f6', backgroundColor: '#3b82f6' },
          { label: '실제', data: progressData.actual, borderColor: '#22c55e', backgroundColor: '#22c55e' },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}건` } },
        },
      },
    }))
  }

  if (assigneeChartEl.value) {
    charts.push(new Chart(assigneeChartEl.value, {
      type: 'bar',
      data: {
        labels: assigneeData.map((a) => a.assignee),
        datasets: [
          { label: '완료', data: assigneeData.map((a) => a.completed), backgroundColor: '#22c55e' },
          { label: '미조치', data: assigneeData.map((a) => a.todo), backgroundColor: '#d1d5db' },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        scales: { x: { stacked: true }, y: { stacked: true } },
      },
    }))
  }
}

onMounted(() => { void loadAndRender() })
onBeforeUnmount(destroyCharts)
</script>

<style scoped>
.stat-tile {
  position: relative;
  border-radius: 8px;
  padding: 12px 16px;
  overflow: hidden;
}
.stat-tile-icon {
  position: absolute;
  right: 8px;
  bottom: 4px;
  font-size: 2.4rem;
  opacity: 0.25;
}
</style>
