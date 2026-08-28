<template>
  <div class="rk-elev">
    <!-- 상단 바 -->
    <div class="rk-topbar">
      <div class="rk-title-wrap">
        <q-icon name="dns" size="18px" class="q-mr-xs text-grey-6" />
        <span class="rk-title">{{ layout.rack.name }}</span>
        <q-chip v-if="layout.rack.serverRoom" dense square size="sm" color="grey-3" text-color="grey-8" class="q-ml-sm">
          {{ layout.rack.serverRoom }}
        </q-chip>
      </div>
      <q-space />
      <q-btn-toggle
        :model-value="side"
        dense no-caps unelevated size="sm"
        toggle-color="primary" color="grey-3" text-color="grey-8"
        :options="[
          { label: '전체', value: 'ALL' },
          { label: '전면', value: 'FRONT' },
          { label: '후면', value: 'REAR' },
        ]"
        @update:model-value="$emit('update:side', $event)"
      />
    </div>

    <!-- 사용률 -->
    <div class="rk-stats">
      <div class="rk-stat">
        <div class="rk-stat-num">{{ layout.rack.usedU }}<span class="rk-stat-den">/{{ layout.rack.totalU }}U</span></div>
        <div class="rk-stat-label">사용 중</div>
      </div>
      <div class="rk-usagebar">
        <q-linear-progress
          :value="(layout.rack.usageRate || 0) / 100"
          size="8px" rounded
          :color="usageColor" track-color="grey-3"
        />
        <div class="rk-usage-cap">
          <span>{{ layout.rack.usageRate }}%</span>
          <span>최대 연속 빈 {{ layout.rack.maxContiguousFreeU }}U</span>
        </div>
      </div>
    </div>

    <!-- 랙 케이지 -->
    <div class="rk-cage">
      <!-- 레인 헤더 -->
      <div class="rk-lane-head" :style="{ gridTemplateColumns: colsTemplate }">
        <div></div>
        <div class="rk-lane-title">{{ isAll ? '전면' : side === 'REAR' ? '후면' : '전면' }}</div>
        <div v-if="isAll" class="rk-lane-title">후면</div>
        <div></div>
      </div>

      <div class="rk-grid" :style="gridStyle">
        <template v-for="u in totalU" :key="`row-${u}`">
          <div class="rk-unum rk-unum--l" :style="{ gridColumn: 1, gridRow: rowFor(u) }">{{ u }}</div>
          <div class="rk-unum rk-unum--r" :style="{ gridColumn: rightNumCol, gridRow: rowFor(u) }">{{ u }}</div>
        </template>

        <!-- 빈 슬롯: 좌측 레인 (전면 또는 단일) -->
        <div
          v-for="u in col2Empties"
          :key="`e2-${u}`"
          class="rk-slot"
          :class="{ 'is-drop': dragOver === `2-${u}` }"
          :style="{ gridColumn: 2, gridRow: rowFor(u) }"
          @click="emitEmpty(u, col2Side)"
          @dragover.prevent="dragOver = `2-${u}`"
          @dragleave="dragOver === `2-${u}` && (dragOver = null)"
          @drop.prevent="onDrop(u, col2Side)"
        >
          <q-icon name="add" size="14px" class="rk-slot-add" />
        </div>

        <!-- 빈 슬롯: 후면 레인 (전체 뷰만) -->
        <div
          v-for="u in col3Empties"
          :key="`e3-${u}`"
          class="rk-slot"
          :class="{ 'is-drop': dragOver === `3-${u}` }"
          :style="{ gridColumn: 3, gridRow: rowFor(u) }"
          @click="emitEmpty(u, 'REAR')"
          @dragover.prevent="dragOver = `3-${u}`"
          @dragleave="dragOver === `3-${u}` && (dragOver = null)"
          @drop.prevent="onDrop(u, 'REAR')"
        >
          <q-icon name="add" size="14px" class="rk-slot-add" />
        </div>

        <!-- 장비 블록 -->
        <div
          v-for="p in visiblePlacements"
          :key="`p-${p.assetId}`"
          class="rk-dev"
          :class="{ 'is-sel': p.assetId === highlightAssetId, 'is-dragging': draggingId === p.assetId }"
          draggable="true"
          :style="{
            gridColumn: deviceCol(p),
            gridRow: `${blockStart(p.endU)} / span ${p.heightU}`,
            '--accent': colorFor(p.assetCategory),
          }"
          @click="$emit('select', p)"
          @dragstart="onDragStart(p)"
          @dragend="draggingId = null; dragOver = null"
        >
          <q-icon :name="iconFor(p.assetCategory)" size="15px" class="rk-dev-ico" />
          <div class="rk-dev-text">
            <div class="rk-dev-name">
              {{ p.name }}
              <span v-if="isAll && p.mountSide !== 'FULL'" class="rk-dev-side">{{ p.mountSide === 'FRONT' ? '전' : '후' }}</span>
            </div>
            <div class="rk-dev-sub">{{ p.assetCode || '—' }} · {{ p.assetCategory }} · U{{ p.startU }}<template v-if="p.heightU > 1">~U{{ p.endU }}</template></div>
          </div>
          <q-icon name="drag_indicator" size="16px" class="rk-dev-grip" />
        </div>
      </div>
    </div>

    <!-- 범례 -->
    <div class="rk-legend">
      <span v-for="c in legend" :key="c.cat" class="rk-legend-item">
        <span class="rk-legend-dot" :style="{ background: c.color }" />{{ c.cat }}
      </span>
      <q-space />
      <span class="rk-legend-hint"><q-icon name="drag_indicator" size="13px" /> 끌어서 이동 · 빈 칸 클릭 배치</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { RackLayout, RackPlacementAsset } from 'src/types/racks'

type Side = 'ALL' | 'FRONT' | 'REAR'

const props = defineProps<{
  layout: RackLayout
  highlightAssetId?: string | null
  side?: Side
}>()

const emit = defineEmits<{
  (e: 'select', placement: RackPlacementAsset): void
  (e: 'clickEmpty', u: number, side: 'FULL' | 'FRONT' | 'REAR'): void
  (e: 'moveDrop', payload: { placement: RackPlacementAsset; startU: number; targetSide: 'FRONT' | 'REAR' }): void
  (e: 'update:side', side: Side): void
}>()

const ROW_H = 28
const side = computed<Side>(() => props.side ?? 'ALL')
const isAll = computed(() => side.value === 'ALL')
const totalU = computed(() => props.layout.rack.totalU || 0)

const colsTemplate = computed(() =>
  isAll.value ? '26px 1fr 1fr 26px' : '26px 1fr 26px',
)
const gridStyle = computed(() => ({
  gridTemplateColumns: colsTemplate.value,
  gridTemplateRows: `repeat(${totalU.value}, ${ROW_H}px)`,
}))
const rightNumCol = computed(() => (isAll.value ? 4 : 3))

function rowFor(u: number): number { return totalU.value - u + 1 }
function blockStart(endU: number): number { return totalU.value - endU + 1 }

const usageColor = computed(() => {
  const r = props.layout.rack.usageRate || 0
  return r >= 90 ? 'negative' : r >= 70 ? 'orange' : 'primary'
})

// 전체 뷰는 모든 장비, 전면/후면 뷰는 FULL + 해당 면
const visiblePlacements = computed<RackPlacementAsset[]>(() => {
  if (isAll.value) return props.layout.placements
  return props.layout.placements.filter((p) => p.mountSide === 'FULL' || p.mountSide === side.value)
})

// 전체 뷰: FULL → 두 레인, FRONT → 좌, REAR → 우 / 그 외 뷰 → 단일 레인
function deviceCol(p: RackPlacementAsset): string {
  if (!isAll.value) return '2'
  if (p.mountSide === 'FULL') return '2 / span 2'
  return p.mountSide === 'REAR' ? '3' : '2'
}

function coveredUnits(pred: (p: RackPlacementAsset) => boolean): Set<number> {
  const s = new Set<number>()
  for (const p of props.layout.placements) {
    if (!pred(p)) continue
    for (let u = p.startU; u <= p.endU; u++) s.add(u)
  }
  return s
}
const frontOccupied = computed(() => coveredUnits((p) => p.mountSide === 'FULL' || p.mountSide === 'FRONT'))
const rearOccupied = computed(() => coveredUnits((p) => p.mountSide === 'FULL' || p.mountSide === 'REAR'))

const allU = computed(() => Array.from({ length: totalU.value }, (_, i) => i + 1))

// 좌측 레인 빈칸: 전체·전면 뷰는 전면 기준, 후면 뷰는 후면 기준
const col2Empties = computed(() => {
  const occ = side.value === 'REAR' ? rearOccupied.value : frontOccupied.value
  return allU.value.filter((u) => !occ.has(u))
})
const col2Side = computed<'FRONT' | 'REAR'>(() => (side.value === 'REAR' ? 'REAR' : 'FRONT'))

// 빈 칸 클릭 시 장착면 제안: 전체 뷰에서 앞뒤 모두 비었으면 FULL, 한쪽만 비었으면 그 면
function emitEmpty(u: number, lane: 'FRONT' | 'REAR') {
  // 클릭한 레인/뷰의 면을 기본값으로 (전체(FULL)는 다이얼로그에서 수동 선택)
  const s: 'FRONT' | 'REAR' = isAll.value ? lane : side.value === 'REAR' ? 'REAR' : 'FRONT'
  emit('clickEmpty', u, s)
}
// 우측(후면) 레인 빈칸: 전체 뷰에서만
const col3Empties = computed(() =>
  isAll.value ? allU.value.filter((u) => !rearOccupied.value.has(u)) : [],
)

const draggingId = ref<string | null>(null)
const dragOver = ref<string | null>(null)

function onDragStart(p: RackPlacementAsset) { draggingId.value = p.assetId }
function onDrop(u: number, laneSide: 'FRONT' | 'REAR') {
  dragOver.value = null
  const p = props.layout.placements.find((x) => x.assetId === draggingId.value)
  draggingId.value = null
  if (!p) return
  // 같은 위치·같은 면이면 무시
  if (p.startU === u && (p.mountSide === 'FULL' || p.mountSide === laneSide)) return
  emit('moveDrop', { placement: p, startU: u, targetSide: laneSide })
}

const CATEGORY_COLOR: Record<string, string> = {
  서버: '#1976d2',
  네트워크: '#009688',
  정보보호시스템: '#9c27b0',
  DBMS: '#f57c00',
  VMware: '#43a047',
}
const CATEGORY_ICON: Record<string, string> = {
  서버: 'dns',
  네트워크: 'lan',
  정보보호시스템: 'shield',
  DBMS: 'storage',
  VMware: 'cloud',
}
function colorFor(cat: string): string { return CATEGORY_COLOR[cat] || '#607d8b' }
function iconFor(cat: string): string { return CATEGORY_ICON[cat] || 'memory' }

const legend = computed(() => {
  const seen = new Set(props.layout.placements.map((p) => p.assetCategory))
  return [...seen].map((cat) => ({ cat, color: colorFor(cat) }))
})
</script>

<style scoped>
.rk-elev {
  display: flex;
  flex-direction: column;
}

/* 상단 바 */
.rk-topbar {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
.rk-title-wrap {
  display: flex;
  align-items: center;
  min-width: 0;
}
.rk-title {
  font-size: 15px;
  font-weight: 600;
  color: #212121;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 사용률 */
.rk-stats {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}
.rk-stat {
  text-align: center;
  min-width: 66px;
}
.rk-stat-num {
  font-size: 19px;
  font-weight: 600;
  color: #1976d2;
  line-height: 1;
}
.rk-stat-den {
  font-size: 12px;
  color: #9e9e9e;
  font-weight: 500;
}
.rk-stat-label {
  font-size: 10px;
  color: #bdbdbd;
  margin-top: 3px;
}
.rk-usagebar {
  flex: 1;
}
.rk-usage-cap {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #9e9e9e;
  margin-top: 3px;
}

/* 케이지 — 밝은 Material 톤 */
.rk-cage {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px;
}
.rk-lane-head {
  display: grid;
  column-gap: 0;
  padding-bottom: 6px;
}
.rk-lane-title {
  text-align: center;
  color: #9e9e9e;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
}
.rk-grid {
  display: grid;
  column-gap: 0;
  row-gap: 2px;
}
.rk-unum {
  color: #9e9e9e;
  font-size: 9px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  user-select: none;
}
.rk-unum--l { border-radius: 3px 0 0 3px; }
.rk-unum--r { border-radius: 0 3px 3px 0; }

/* 빈 슬롯 */
.rk-slot {
  margin: 0 6px;
  border: 1px dashed #d8d8d8;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.1s, border-color 0.1s;
}
.rk-slot-add { color: #d0d0d0; }
.rk-slot:hover,
.rk-slot.is-drop {
  background: #e3f2fd;
  border-color: #90caf9;
  border-style: solid;
}
.rk-slot:hover .rk-slot-add,
.rk-slot.is-drop .rk-slot-add { color: #1976d2; }

/* 장비 블록 — 흰 카드 + 카테고리 좌측 액센트 (플랫) */
.rk-dev {
  margin: 1px 6px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-left: 3px solid var(--accent, #607d8b);
  border-radius: 4px;
  cursor: grab;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 8px;
  gap: 7px;
  transition: background-color 0.1s, border-color 0.1s;
}
.rk-dev:hover { background: #f5f7fa; }
.rk-dev:active { cursor: grabbing; }
.rk-dev.is-sel {
  border-color: #1976d2;
  border-left-color: var(--accent, #607d8b);
  background: #e8f2fe;
}
.rk-dev.is-dragging { opacity: 0.4; }
.rk-dev-ico { color: var(--accent, #607d8b); flex: 0 0 auto; }
.rk-dev-text {
  min-width: 0;
  flex: 1;
  line-height: 1.2;
}
.rk-dev-name {
  font-size: 12px;
  font-weight: 600;
  color: #212121;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 5px;
}
.rk-dev-side {
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  background: #9e9e9e;
  border-radius: 3px;
  padding: 0 4px;
  line-height: 14px;
}
.rk-dev-sub {
  font-size: 10px;
  color: #9e9e9e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rk-dev-grip {
  color: #e0e0e0;
  flex: 0 0 auto;
}
.rk-dev:hover .rk-dev-grip { color: #bdbdbd; }

/* 범례 */
.rk-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  padding: 0 2px;
}
.rk-legend-item {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  color: #757575;
}
.rk-legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 5px;
}
.rk-legend-hint {
  font-size: 11px;
  color: #bdbdbd;
}
</style>
