<template>
  <div class="trend-chart">
    <div v-if="!points.length" class="text-center text-grey-5 q-pa-lg">
      <q-icon name="show_chart" size="32px" class="q-mb-xs" /><br />
      추이를 표시할 데이터가 없습니다.
    </div>
    <template v-else>
      <div class="trend-toolbar">
        <div class="trend-legend">
          <span class="legend-item"><span class="legend-swatch" style="background:#eda100" />CPU</span>
          <span class="legend-item"><span class="legend-swatch" style="background:#2a78d6" />RAM</span>
          <span class="legend-item"><span class="legend-swatch" style="background:#1baf7a" />Disk</span>
        </div>
        <q-btn flat dense no-caps size="sm" :label="showTable ? '차트로 보기' : '표로 보기'" @click="showTable = !showTable" />
      </div>

      <div v-if="!showTable" class="trend-svg-wrap">
        <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="trend-svg" :class="{ 'trend-svg--large': large }" @pointerleave="hoverIndex = null">
          <!-- 80% 이상 경고 구간 배경 -->
          <rect :x="padL" :y="yFor(100)" :width="plotW" :height="yFor(80) - yFor(100)" fill="#fab219" opacity="0.08" />

          <!-- 그리드라인 -->
          <g v-for="g in gridTicks" :key="g">
            <line :x1="padL" :x2="W - padR" :y1="yFor(g)" :y2="yFor(g)" class="grid-line" />
            <text :x="padL - 5" :y="yFor(g)" class="grid-label" text-anchor="end" dominant-baseline="middle">{{ g }}%</text>
          </g>

          <!-- 시리즈 라인 -->
          <path :d="lineFor('cpu')" class="series-line" stroke="#eda100" fill="none" />
          <path :d="lineFor('ram')" class="series-line" stroke="#2a78d6" fill="none" />
          <path :d="lineFor('disk')" class="series-line" stroke="#1baf7a" fill="none" />

          <!-- 시작점 마커 (데이터가 왼쪽 끝에서 잘려 보이지 않도록) -->
          <g v-if="first">
            <circle :cx="xFor(0)" :cy="yFor(first.cpu)" r="3" fill="#eda100" stroke="#fcfcfb" stroke-width="2" />
            <circle :cx="xFor(0)" :cy="yFor(first.ram)" r="3" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2" />
            <circle :cx="xFor(0)" :cy="yFor(first.disk)" r="3" fill="#1baf7a" stroke="#fcfcfb" stroke-width="2" />
          </g>

          <!-- 끝점 마커 + 직접 라벨 (라벨은 점 위/아래에 배치) -->
          <g v-if="last">
            <circle :cx="xFor(points.length - 1)" :cy="yFor(last.cpu)" r="4" fill="#eda100" stroke="#fcfcfb" stroke-width="2" />
            <text :x="xFor(points.length - 1)" :y="yFor(last.cpu) + labelDy(last.cpu)" class="end-label" text-anchor="middle">{{ last.cpu.toFixed(1) }}%</text>
            <circle :cx="xFor(points.length - 1)" :cy="yFor(last.ram)" r="4" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2" />
            <text :x="xFor(points.length - 1)" :y="yFor(last.ram) + labelDy(last.ram)" class="end-label" text-anchor="middle">{{ last.ram.toFixed(1) }}%</text>
            <circle :cx="xFor(points.length - 1)" :cy="yFor(last.disk)" r="4" fill="#1baf7a" stroke="#fcfcfb" stroke-width="2" />
            <text :x="xFor(points.length - 1)" :y="yFor(last.disk) + labelDy(last.disk)" class="end-label" text-anchor="middle">{{ last.disk.toFixed(1) }}%</text>
          </g>

          <!-- x축 라벨 (양 끝은 잘리지 않도록 안쪽으로 정렬) -->
          <text v-for="(p, i) in points" :key="p.label" :x="xFor(i)" :y="H - 6" class="x-label" :text-anchor="xLabelAnchor(i)">{{ p.label }}</text>

          <!-- 호버 크로스헤어 -->
          <line v-if="hoverIndex !== null" :x1="xFor(hoverIndex)" :x2="xFor(hoverIndex)" :y1="padT" :y2="H - padB" class="crosshair" />

          <!-- 히트 영역 (마크보다 넉넉하게) -->
          <rect
            v-for="(p, i) in points" :key="'hit-' + p.label"
            :x="xFor(i) - hitW / 2" :y="padT" :width="hitW" :height="H - padT - padB"
            fill="transparent"
            tabindex="0"
            @pointerenter="hoverIndex = i"
            @pointermove="hoverIndex = i"
            @focus="hoverIndex = i"
          />
        </svg>

        <div v-if="hoverIndex !== null" class="trend-tooltip" :style="{ left: tooltipLeftPct + '%' }">
          <div class="tooltip-date">{{ points[hoverIndex]!.label }}</div>
          <div class="tooltip-row"><span class="tooltip-key" style="background:#eda100" />CPU <b>{{ points[hoverIndex]!.cpu.toFixed(1) }}%</b></div>
          <div class="tooltip-row"><span class="tooltip-key" style="background:#2a78d6" />RAM <b>{{ points[hoverIndex]!.ram.toFixed(1) }}%</b></div>
          <div class="tooltip-row"><span class="tooltip-key" style="background:#1baf7a" />Disk <b>{{ points[hoverIndex]!.disk.toFixed(1) }}%</b></div>
        </div>
      </div>

      <q-markup-table v-else flat dense bordered class="trend-table">
        <thead>
          <tr class="bg-grey-2"><th>월</th><th>CPU</th><th>RAM</th><th>Disk</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in points" :key="p.label">
            <td>{{ p.label }}</td>
            <td>{{ p.cpu.toFixed(1) }}%</td>
            <td>{{ p.ram.toFixed(1) }}%</td>
            <td>{{ p.disk.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </q-markup-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface TrendPoint {
  label: string
  cpu: number
  ram: number
  disk: number
}

const props = withDefaults(defineProps<{ points: TrendPoint[]; large?: boolean }>(), {
  large: false,
})

const W = 640
const H = 260
// 맨 처음 데이터가 y축 숫자와 너무 붙지 않도록 왼쪽 여백을 넉넉히
const padL = 60
// 끝점 값 라벨은 점 위/아래에 붙으므로, 오른쪽은 마커가 잘리지 않을 정도의 여백만 필요
const padR = 20
const padT = 16
const padB = 28
const plotW = W - padL - padR
const gridTicks = [0, 25, 50, 75, 100]

const first = computed(() => props.points[0] ?? null)
const last = computed(() => props.points[props.points.length - 1] ?? null)

function yFor(pct: number): number {
  const plotH = H - padT - padB
  return padT + plotH * (1 - pct / 100)
}

function xFor(i: number): number {
  if (props.points.length <= 1) return padL + plotW / 2
  return padL + (plotW * i) / (props.points.length - 1)
}

function lineFor(key: 'cpu' | 'ram' | 'disk'): string {
  return props.points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(p[key])}`)
    .join(' ')
}

// 끝점 값 라벨의 상/하 오프셋 — 값이 100%에 가까워 위쪽 여백이 부족하면 점 아래로 배치
function labelDy(pct: number): number {
  return pct > 88 ? 16 : -10
}

// 맨 앞/맨 뒤 날짜 라벨은 가운데 정렬 시 차트 영역 밖으로 잘릴 수 있어 안쪽으로 정렬
function xLabelAnchor(i: number): 'start' | 'middle' | 'end' {
  if (i === 0 && props.points.length > 1) return 'start'
  if (i === props.points.length - 1 && props.points.length > 1) return 'end'
  return 'middle'
}

const hitW = computed(() => Math.max(24, plotW / Math.max(1, props.points.length - 1)))

const hoverIndex = ref<number | null>(null)
const showTable = ref(false)

const tooltipLeftPct = computed(() => {
  if (hoverIndex.value === null) return 0
  // 툴팁이 차트 좌우 바깥으로 삐져나가 가로 스크롤바가 생기지 않도록 범위를 살짝 안쪽으로 제한
  const pct = (xFor(hoverIndex.value) / W) * 100
  return Math.min(92, Math.max(8, pct))
})
</script>

<style scoped>
.trend-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.trend-legend {
  display: flex;
  gap: 14px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #52514e;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.trend-svg-wrap {
  position: relative;
  overflow: hidden;
}

.trend-svg {
  width: 100%;
  height: 260px;
  display: block;
}

.trend-svg--large {
  height: 60vh;
}

.grid-line {
  stroke: #e1e0d9;
  stroke-width: 1;
}

.grid-label,
.x-label {
  font-size: 10px;
  fill: #898781;
}

.series-line {
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.end-label {
  font-size: 11px;
  fill: #0b0b0b;
  font-weight: 600;
}

.crosshair {
  stroke: #c3c2b7;
  stroke-width: 1;
}

.trend-tooltip {
  position: absolute;
  top: 8px;
  transform: translateX(-50%);
  background: #fcfcfb;
  border: 1px solid rgba(11, 11, 11, 0.1);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  pointer-events: none;
  white-space: nowrap;
}

.tooltip-date {
  color: #52514e;
  margin-bottom: 2px;
}

.tooltip-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tooltip-key {
  width: 10px;
  height: 2px;
  display: inline-block;
}

.trend-table {
  font-size: 12px;
}
</style>
