<template>
  <div
    ref="root"
    class="floor-plan"
    :class="{ 'plan-expanded': expanded, 'plan-active': active }"
    tabindex="0"
    @focusin="active = true"
    @focusout="focusOut"
    @keydown="keyboard"
  >
    <div class="plan-toolbar">
      <div class="plan-toolbar__group">
        <template v-if="editable">
          <q-btn
            flat
            dense
            round
            icon="undo"
            aria-label="실행 취소"
            :disable="!past.length"
            @click="undo"
            ><q-tooltip>실행 취소 · Ctrl/⌘ Z</q-tooltip></q-btn
          >
          <q-btn
            flat
            dense
            round
            icon="redo"
            aria-label="다시 실행"
            :disable="!future.length"
            @click="redo"
            ><q-tooltip>다시 실행 · Ctrl/⌘ Shift Z</q-tooltip></q-btn
          >
          <q-separator vertical inset class="q-mx-sm" /><q-toggle
            v-model="grid"
            dense
            label="격자"
          /><q-toggle v-model="snap" dense label="격자 맞춤" />
        </template>
        <span v-else class="plan-toolbar__label"
          ><q-icon name="touch_app" size="18px" />좌석을 선택해 인원 배정·상세 확인</span
        >
      </div>
      <div class="plan-toolbar__group">
        <div class="plan-zoom">
          <q-btn flat dense round icon="remove" aria-label="축소" @click="zoom(1.25)" /><span
            >{{ Math.round((modelValue.width / view.width) * 100) }}%</span
          ><q-btn flat dense round icon="add" aria-label="확대" @click="zoom(0.8)" />
        </div>
        <q-btn flat dense round icon="fit_screen" aria-label="전체 보기" @click="fit"
          ><q-tooltip>전체 캔버스 보기</q-tooltip></q-btn
        >
        <q-btn
          flat
          dense
          round
          icon="center_focus_strong"
          aria-label="배치에 맞춤"
          :disable="!modelValue.objects.length"
          @click="fitDrawing"
          ><q-tooltip>배치한 객체에 화면 맞춤</q-tooltip></q-btn
        >
        <q-btn
          flat
          dense
          round
          :icon="expanded ? 'fullscreen_exit' : 'fullscreen'"
          :aria-label="expanded ? '넓게 보기 종료' : '넓게 보기'"
          @click="expanded = !expanded"
          ><q-tooltip>{{ expanded ? '넓게 보기 종료' : '넓게 보기' }}</q-tooltip></q-btn
        >
      </div>
    </div>
    <div :class="['plan-body', { editing: editable }]">
      <aside v-if="editable" class="tools">
        <div class="plan-panel-title">편집 도구</div>
        <div class="plan-mode-tools">
          <q-btn
            v-for="item in tools.slice(0, 2)"
            :key="item.value"
            flat
            no-caps
            :class="{ 'tool-active': tool === item.value }"
            :icon="item.icon"
            :label="item.label"
            :aria-pressed="tool === item.value"
            @click="tool = item.value"
          />
        </div>
        <div class="plan-section-label">객체 추가</div>
        <div class="plan-object-tools">
          <q-btn
            v-for="item in tools.slice(2)"
            :key="item.value"
            flat
            stack
            no-caps
            :class="{ 'tool-active': tool === item.value }"
            :icon="item.icon"
            :label="item.label"
            :aria-pressed="tool === item.value"
            @click="tool = item.value"
          />
        </div>
        <div class="tool-guidance">
          <q-icon name="info_outline" size="16px" /><span>{{
            tool === 'wall'
              ? '시작점에서 끝점까지 드래그하세요.'
              : tool === 'select'
                ? '객체를 선택해 이동하거나 속성을 변경하세요.'
                : tool === 'pan'
                  ? '캔버스를 드래그해 화면을 이동하세요.'
                  : '캔버스의 원하는 위치를 클릭하세요.'
          }}</span>
        </div>
        <q-separator class="q-my-md" />
        <div class="plan-selection-actions">
          <q-btn
            flat
            dense
            icon="content_copy"
            label="복제"
            :disable="!selected.length"
            @click="duplicate"
          /><q-btn
            flat
            dense
            color="negative"
            icon="delete_outline"
            label="삭제"
            :disable="!selected.length"
            @click="remove"
          />
        </div>
        <q-expansion-item dense label="캔버스 설정" class="plan-settings q-mt-md"
          ><div class="q-pt-md q-gutter-sm">
            <q-input
              :model-value="modelValue.width"
              type="number"
              dense
              outlined
              label="캔버스 너비"
              @change="(v: string) => canvasSize('width', v)"
            /><q-input
              :model-value="modelValue.height"
              type="number"
              dense
              outlined
              label="캔버스 높이"
              @change="(v: string) => canvasSize('height', v)"
            /></div
        ></q-expansion-item>
      </aside>
      <div class="canvas-wrap">
        <svg
          ref="svg"
          class="plan-svg"
          tabindex="0"
          role="group"
          aria-label="사무실 배치도"
          :viewBox="`${view.x} ${view.y} ${view.width} ${view.height}`"
          @pointerdown="startBackground"
          @pointermove="move"
          @pointerup="end"
          @pointercancel="cancelGesture"
          @wheel="wheel"
          @contextmenu.prevent
        >
          <defs>
            <pattern :id="gridId" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#dbe3eb" stroke-width="1" />
            </pattern>
          </defs>
          <rect
            :x="view.x - 20000"
            :y="view.y - 20000"
            width="60000"
            height="60000"
            fill="#edf1f5"
          />
          <rect
            x="0"
            y="0"
            :width="modelValue.width"
            :height="modelValue.height"
            fill="white"
            stroke="#b0bec5"
          />
          <rect
            v-if="grid && editable"
            x="0"
            y="0"
            :width="modelValue.width"
            :height="modelValue.height"
            :fill="`url(#${gridId})`"
          />
          <g
            v-for="obj in orderedObjects"
            :key="obj.id"
            :data-object="obj.id"
            :data-kind="obj.kind"
            :data-seat="obj.seatId || undefined"
            :role="!editable && obj.seatId && matches(obj) ? 'button' : undefined"
            :tabindex="!editable && obj.seatId && matches(obj) ? 0 : undefined"
            :aria-label="
              obj.seatId
                ? `${seatFor(obj)?.number} · ${personName(obj.seatId) || '미배정'} · 좌석 정보 열기`
                : undefined
            "
            :transform="`translate(${obj.x} ${obj.y}) rotate(${obj.rotation})`"
            :opacity="matches(obj) ? 1 : 0.18"
            :class="{
              movable: editable && tool === 'select',
              seat: !editable && obj.kind === 'desk',
            }"
            @pointerdown.stop="(e) => startObject(e, obj)"
            @keydown.enter.stop.prevent="activateSeat(obj)"
            @keydown.space.stop.prevent="activateSeat(obj)"
          >
            <title v-if="obj.kind === 'desk'">
              {{ seatFor(obj)?.number }} · {{ personName(obj.seatId) || '미배정' }}
            </title>
            <rect
              v-if="obj.kind === 'wall'"
              :width="obj.width"
              :height="obj.height"
              fill="#455a64"
            />
            <g v-else-if="obj.kind === 'door'" fill="none" stroke="#607d8b" stroke-width="3">
              <path :d="`M 0 ${obj.height} L 0 0 L ${obj.width} 0`" />
              <path
                :d="`M 0 ${obj.height} A ${obj.width} ${obj.height} 0 0 0 ${obj.width} 0`"
                stroke-dasharray="5 4"
              />
              <rect :width="obj.width" :height="obj.height" fill="transparent" stroke="none" />
            </g>
            <g v-else-if="obj.kind === 'desk'">
              <rect
                :width="obj.width"
                :height="obj.height"
                rx="5"
                :fill="teamColor(seatFor(obj)?.teamId)"
                fill-opacity="0.13"
                :stroke="teamColor(seatFor(obj)?.teamId)"
                stroke-width="2"
              />
              <rect
                :x="obj.width * 0.3"
                :y="obj.height - 6"
                :width="obj.width * 0.4"
                height="13"
                rx="5"
                :fill="teamColor(seatFor(obj)?.teamId)"
              />
              <text
                :x="obj.width / 2"
                :y="obj.height / 2 - seatFontSize * 0.35"
                text-anchor="middle"
                fill="#263238"
                :font-size="seatFontSize"
                font-weight="600"
              >
                {{ shortLabel(seatFor(obj)?.number || '좌석', obj.width) }}
              </text>
              <text
                :x="obj.width / 2"
                :y="obj.height / 2 + seatFontSize * 0.9"
                text-anchor="middle"
                fill="#455a64"
                :font-size="seatFontSize"
              >
                {{ shortLabel(personName(obj.seatId) || '미배정', obj.width) }}
              </text>
            </g>
            <g v-else-if="obj.kind === 'cabinet'">
              <rect
                :width="obj.width"
                :height="obj.height"
                rx="2"
                fill="#e4e8ed"
                stroke="#78909c"
                stroke-width="2"
              />
              <path :d="`M ${obj.width / 2} 0 V ${obj.height}`" stroke="#78909c" />
              <text
                :x="obj.width / 2"
                :y="obj.height / 2 + 4"
                text-anchor="middle"
                font-size="12"
                fill="#455a64"
              >
                {{ obj.name || '캐비닛' }}
              </text>
            </g>
            <g v-else-if="obj.kind === 'zone'">
              <rect
                :width="obj.width"
                :height="obj.height"
                rx="8"
                :fill="teamColor(obj.teamId)"
                fill-opacity="0.07"
                :stroke="teamColor(obj.teamId)"
                stroke-dasharray="8 6"
                stroke-width="2"
              />
              <text x="10" y="22" font-size="14" :fill="teamColor(obj.teamId)">
                {{ obj.name || teams.find((t) => t.id === obj.teamId)?.name || '팀 구역' }}
              </text>
            </g>
            <g v-else>
              <rect :width="obj.width" :height="obj.height" fill="transparent" />
              <text x="4" :y="Math.min(obj.height - 2, 22)" font-size="18" fill="#263238">
                {{ obj.name || '텍스트' }}
              </text>
            </g>
            <rect
              v-if="selected.includes(obj.id) || (selectedSeatId && obj.seatId === selectedSeatId)"
              x="-4"
              y="-4"
              :width="obj.width + 8"
              :height="obj.height + 8"
              fill="none"
              stroke="#1565c0"
              stroke-width="2"
              stroke-dasharray="6 3"
              pointer-events="none"
            />
            <g v-if="editable && selected.length === 1 && selected[0] === obj.id">
              <rect
                :x="obj.width - 6"
                :y="obj.height - 6"
                width="12"
                height="12"
                fill="#1976d2"
                stroke="white"
                class="resize-handle"
                @pointerdown.stop="(e) => startTransform(e, obj, 'resize')"
              />
              <path :d="`M ${obj.width / 2} 0 V -25`" stroke="#1976d2" />
              <circle
                :cx="obj.width / 2"
                cy="-25"
                r="7"
                fill="#1976d2"
                stroke="white"
                class="rotate-handle"
                @pointerdown.stop="(e) => startTransform(e, obj, 'rotate')"
              />
            </g>
          </g>
          <rect
            v-if="marquee"
            :x="marquee.x"
            :y="marquee.y"
            :width="marquee.width"
            :height="marquee.height"
            fill="#1976d2"
            fill-opacity="0.08"
            stroke="#1976d2"
            stroke-dasharray="5 3"
            pointer-events="none"
          />
        </svg>
        <div v-if="!modelValue.objects.length" class="canvas-empty">
          <q-icon :name="editable ? 'draw' : 'map'" size="36px" /><strong>{{
            editable ? '나만의 사무실 배치도를 만들어 보세요' : '게시된 배치도가 없습니다'
          }}</strong
          ><span>{{
            editable
              ? '왼쪽에서 벽이나 책상을 선택한 뒤 이곳에 배치하세요.'
              : '배치도를 만들고 게시하면 좌석을 확인할 수 있습니다.'
          }}</span>
        </div>
      </div>
      <aside v-if="editable" class="properties">
        <div class="plan-panel-title q-mb-md">
          {{ selected.length > 1 ? `${selected.length}개 객체 선택` : '객체 속성' }}
        </div>
        <template v-if="current">
          <q-badge
            color="blue-1"
            text-color="primary"
            :label="tools.find((t) => t.value === current?.kind)?.label"
            class="q-mb-md"
          />
          <q-input
            :model-value="current.name"
            outlined
            dense
            label="이름 / 텍스트"
            maxlength="100"
            class="q-mb-sm"
            @change="(v: string) => property('name', String(v))"
          />
          <div class="plan-section-label q-mt-lg">위치와 크기</div>
          <div class="row q-col-gutter-sm">
            <div v-for="field in numberFields" :key="field.key" class="col-6">
              <q-input
                :model-value="current[field.key]"
                type="number"
                outlined
                dense
                :label="field.label"
                class="q-mb-sm"
                @change="(v: string) => property(field.key, Number(v))"
              />
            </div>
          </div>
          <template v-if="current.kind === 'wall'"
            ><div class="text-caption q-mb-sm">
              시작점은 X·Y, 길이는 너비, 방향은 회전으로 조정합니다.
            </div>
            <div class="row q-col-gutter-sm">
              <div class="col-6">
                <q-input
                  :model-value="Math.round(wallEnd.x)"
                  type="number"
                  outlined
                  dense
                  label="끝점 X"
                  @change="(v: string) => wallEndpoint(Number(v), wallEnd.y)"
                />
              </div>
              <div class="col-6">
                <q-input
                  :model-value="Math.round(wallEnd.y)"
                  type="number"
                  outlined
                  dense
                  label="끝점 Y"
                  @change="(v: string) => wallEndpoint(wallEnd.x, Number(v))"
                />
              </div></div
          ></template>
          <template v-if="current.kind === 'desk'">
            <q-separator class="q-my-md" />
            <div class="plan-section-label">좌석 정보</div>
            <q-input
              :model-value="seatFor(current)?.number"
              outlined
              dense
              label="좌석번호 *"
              maxlength="100"
              class="q-mb-sm"
              @change="(v: string) => seatProperty('number', String(v))"
            />
            <q-select
              :model-value="seatFor(current)?.teamId"
              :options="teams.map((t) => ({ label: t.name, value: t.id }))"
              emit-value
              map-options
              clearable
              outlined
              dense
              label="좌석 담당 팀"
              :hint="
                teams.length
                  ? '이 좌석을 사용할 팀입니다. 게시하면 적용됩니다.'
                  : '사무실에 등록된 사용 팀이 없습니다.'
              "
              @update:model-value="(v) => seatProperty('teamId', v as string | null)"
            />
            <div class="q-mt-md text-body2">
              배정 인원: {{ personName(current.seatId) || '미배정' }}
            </div>
            <q-badge
              class="q-mt-xs"
              :color="personName(current.seatId) ? 'positive' : 'grey'"
              :label="personName(current.seatId) ? '배정' : '미배정'"
            />
            <p class="text-caption text-grey-7 q-mt-sm">
              인원 배정·해제는 조회 화면에서 좌석을 클릭해 처리합니다.
            </p>
          </template>
          <q-select
            v-if="current.kind === 'zone'"
            :model-value="current.teamId"
            :options="teams.map((t) => ({ label: t.name, value: t.id }))"
            emit-value
            map-options
            clearable
            outlined
            dense
            label="구역 표시 팀"
            hint="색상으로 영역만 표시합니다. 좌석 담당 팀은 각 책상에서 지정하세요."
            @update:model-value="(v) => property('teamId', v as string | null)"
          />
        </template>
        <div v-else class="property-empty">
          <q-icon :name="selected.length ? 'select_all' : 'ads_click'" size="32px" /><strong>{{
            selected.length ? `${selected.length}개 객체 선택됨` : '선택된 객체가 없습니다'
          }}</strong>
          <p>
            {{
              selected.length
                ? '선택한 객체를 함께 이동·복제·삭제할 수 있습니다.'
                : '객체를 클릭하면 위치, 크기와 좌석 정보를 설정할 수 있습니다.'
            }}
          </p>
        </div>
      </aside>
    </div>
    <div class="plan-statusbar">
      <span>{{
        editable
          ? `${modelValue.objects.length}개 객체${selected.length ? ` · ${selected.length}개 선택` : ''}`
          : `${modelValue.seats.length}개 좌석`
      }}</span
      ><span v-if="!active"
        >배치도를 클릭하면 확대·축소{{ editable ? '·편집' : '' }}할 수 있습니다.</span
      ><span v-else
        >휠로 확대·축소 · {{ editable ? 'Shift+클릭으로 여러 객체 선택' : '드래그로 화면 이동' }} ·
        Esc로 조작 해제</span
      ><q-btn v-if="editable" flat dense size="sm" icon="help_outline" aria-label="편집 단축키"
        ><q-tooltip class="text-body2"
          >가운데 버튼: 화면 이동<br />방향키: 객체 이동<br />Ctrl/⌘ Z: 실행 취소<br />Ctrl/⌘ D:
          복제<br />Delete: 삭제</q-tooltip
        ></q-btn
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { drawingBounds, newSpaceId } from 'src/utils/spacePlan';
import { useQuasar } from 'quasar';
import type {
  Assignment,
  ObjectKind,
  Person,
  Plan,
  PlanObject,
  Seat,
  Team,
} from 'src/services/spaces';
const props = withDefaults(
  defineProps<{
    modelValue: Plan;
    editable?: boolean;
    teams: Team[];
    assignments: Assignment[];
    people: Person[];
    teamFilter?: string | null;
    selectedSeatId?: string | null;
    visibleSeatIds?: string[];
  }>(),
  { editable: false, teamFilter: null, selectedSeatId: null },
);
const emit = defineEmits<{ 'update:modelValue': [value: Plan]; selectSeat: [id: string] }>();
const $q = useQuasar();
const root = ref<HTMLElement>();
const active = ref(false);
const expanded = ref(false);
const canvasPixels = ref({ width: 900, height: 500 });
let resizeObserver: ResizeObserver | undefined;
const svg = ref<SVGSVGElement>(),
  gridId = `space-grid-${newSpaceId()}`;
const grid = ref(true),
  snap = ref(true),
  selected = ref<string[]>([]);
type Tool = ObjectKind | 'select' | 'pan';
const tool = ref<Tool>('select');
const tools: { value: Tool; label: string; icon: string }[] = [
  { value: 'select', label: '선택', icon: 'near_me' },
  { value: 'pan', label: '화면 이동', icon: 'pan_tool' },
  { value: 'wall', label: '벽 그리기', icon: 'horizontal_rule' },
  { value: 'door', label: '출입문', icon: 'meeting_room' },
  { value: 'desk', label: '책상 / 좌석', icon: 'desk' },
  { value: 'cabinet', label: '캐비닛', icon: 'inventory_2' },
  { value: 'text', label: '텍스트', icon: 'title' },
  { value: 'zone', label: '팀 구역', icon: 'crop_free' },
];
const numberFields = [
  { key: 'x', label: 'X' },
  { key: 'y', label: 'Y' },
  { key: 'width', label: '너비 / 길이' },
  { key: 'height', label: '높이 / 두께' },
  { key: 'rotation', label: '회전 (°)' },
] as const;
const copy = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const past = ref<Plan[]>([]),
  future = ref<Plan[]>([]);
const view = ref({
  x: -40,
  y: -40,
  width: props.modelValue.width + 80,
  height: props.modelValue.height + 80,
});
const seatFontSize = computed(() => {
  const scale = Math.min(
    canvasPixels.value.width / view.value.width,
    canvasPixels.value.height / view.value.height,
  );
  return Math.max(13, Math.min(24, 11 / Math.max(scale, 0.01)));
});
function shortLabel(text: string, width: number) {
  const limit = Math.max(2, (width - 12) / seatFontSize.value);
  let used = 0,
    result = '';
  for (const char of text) {
    used += char.charCodeAt(0) < 128 ? 0.6 : 1;
    if (used > limit) return result.slice(0, -1) + '…';
    result += char;
  }
  return result;
}
const current = computed(() =>
  selected.value.length === 1
    ? props.modelValue.objects.find((o) => o.id === selected.value[0])
    : undefined,
);
const orderedObjects = computed(() =>
  [...props.modelValue.objects].sort(
    (a, b) => Number(b.kind === 'zone') - Number(a.kind === 'zone'),
  ),
);
const wallEnd = computed(() => ({
  x:
    (current.value?.x ?? 0) +
    (current.value?.width ?? 0) * Math.cos(((current.value?.rotation ?? 0) * Math.PI) / 180),
  y:
    (current.value?.y ?? 0) +
    (current.value?.width ?? 0) * Math.sin(((current.value?.rotation ?? 0) * Math.PI) / 180),
}));
function checkpoint() {
  past.value.push(copy(props.modelValue));
  if (past.value.length > 80) past.value.shift();
  future.value = [];
}
function content(plan: Plan) {
  emit('update:modelValue', {
    ...props.modelValue,
    width: plan.width,
    height: plan.height,
    objects: copy(plan.objects),
    seats: copy(plan.seats),
  });
}
function mutate(fn: (plan: Plan) => void) {
  checkpoint();
  const p = copy(props.modelValue);
  fn(p);
  content(p);
}
function undo() {
  const p = past.value.pop();
  if (!p) return;
  future.value.push(copy(props.modelValue));
  content(p);
  selected.value = [];
}
function redo() {
  const p = future.value.pop();
  if (!p) return;
  past.value.push(copy(props.modelValue));
  content(p);
  selected.value = [];
}
function fit() {
  view.value = {
    x: -40,
    y: -40,
    width: props.modelValue.width + 80,
    height: props.modelValue.height + 80,
  };
}
function fitDrawing() {
  const bounds = drawingBounds(props.modelValue.objects);
  if (bounds) view.value = bounds;
  else fit();
}
onMounted(() => {
  document.addEventListener('pointerdown', pointerFocus, true);
  window.addEventListener('blur', deactivate);
  if (!props.editable) fitDrawing();
  resizeObserver = new ResizeObserver(([entry]) => {
    if (entry)
      canvasPixels.value = { width: entry.contentRect.width, height: entry.contentRect.height };
  });
  if (svg.value) resizeObserver.observe(svg.value);
});
onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  document.removeEventListener('pointerdown', pointerFocus, true);
  window.removeEventListener('blur', deactivate);
});
function deactivate() {
  active.value = false;
}
function pointerFocus(e: PointerEvent) {
  if (!root.value?.contains(e.target as Node)) {
    deactivate();
    return;
  }
  if (e.button !== 0 && e.button !== 1) return;
  active.value = true;
  if (e.target instanceof SVGElement) svg.value?.focus({ preventScroll: true });
}
function focusOut(e: FocusEvent) {
  if (!root.value?.contains(e.relatedTarget as Node | null)) deactivate();
}
function zoom(factor: number) {
  const w = view.value.width * factor;
  if (w < 150 || w > 50000) return;
  view.value = {
    x: view.value.x + (view.value.width - w) / 2,
    y: view.value.y + (view.value.height * (1 - factor)) / 2,
    width: w,
    height: view.value.height * factor,
  };
}
function wheel(e: WheelEvent) {
  if (!active.value) return;
  e.preventDefault();
  zoom(e.deltaY > 0 ? 1.1 : 1 / 1.1);
}
function round(v: number) {
  return snap.value ? Math.round(v / 20) * 20 : Math.round(v);
}
function teamColor(id?: string | null) {
  return props.teams.find((t) => t.id === id)?.color ?? '#78909c';
}
function seatFor(obj: PlanObject) {
  return props.modelValue.seats.find((s) => s.id === obj.seatId);
}
function personName(seatId: string | null) {
  const a = props.assignments.find((a) => a.seatId === seatId);
  return props.people.find((p) => p.id === a?.personId)?.name ?? '';
}
function matches(obj: PlanObject) {
  if (
    obj.kind === 'desk' &&
    props.visibleSeatIds &&
    !props.visibleSeatIds.includes(obj.seatId ?? '')
  )
    return false;
  return (
    !props.teamFilter ||
    (obj.kind !== 'desk' && obj.kind !== 'zone') ||
    (obj.kind === 'desk' ? seatFor(obj)?.teamId : obj.teamId) === props.teamFilter
  );
}
function nextNumber(seats: Seat[]) {
  let i = 1;
  while (seats.some((s) => s.number.toUpperCase() === `A-${String(i).padStart(2, '0')}`)) i++;
  return `A-${String(i).padStart(2, '0')}`;
}
function add(kind: ObjectKind, x: number, y: number) {
  const id = newSpaceId();
  mutate((p) => {
    const seatId = kind === 'desk' ? newSpaceId() : null;
    if (seatId)
      p.seats.push({ id: seatId, number: nextNumber(p.seats), teamId: props.teams[0]?.id ?? null });
    p.objects.push({
      id,
      kind,
      name: kind === 'text' ? '텍스트' : '',
      x: round(x),
      y: round(y),
      width: kind === 'zone' ? 400 : kind === 'wall' ? 1 : 120,
      height: kind === 'zone' ? 240 : kind === 'wall' ? 8 : kind === 'text' ? 40 : 80,
      rotation: 0,
      seatId,
      teamId: kind === 'zone' ? (props.teams[0]?.id ?? null) : null,
    });
  });
  selected.value = [id];
  return id;
}
function duplicate() {
  const ids: string[] = [];
  mutate((p) => {
    for (const source of props.modelValue.objects.filter((o) => selected.value.includes(o.id))) {
      const o = { ...copy(source), id: newSpaceId(), x: source.x + 40, y: source.y + 40 };
      if (o.seatId) {
        const s = p.seats.find((s) => s.id === o.seatId);
        o.seatId = newSpaceId();
        p.seats.push({ id: o.seatId, number: nextNumber(p.seats), teamId: s?.teamId ?? null });
      }
      p.objects.push(o);
      ids.push(o.id);
    }
  });
  selected.value = ids;
}
function remove() {
  if (
    props.modelValue.objects.some(
      (o) =>
        selected.value.includes(o.id) &&
        o.seatId &&
        props.assignments.some((a) => a.seatId === o.seatId),
    )
  ) {
    $q.notify({
      type: 'warning',
      message: '배정된 좌석은 조회 화면에서 해당 좌석을 클릭해 먼저 해제해 주세요.',
    });
    return;
  }
  mutate((p) => {
    p.objects = p.objects.filter((o) => !selected.value.includes(o.id));
    p.seats = p.seats.filter((s) => p.objects.some((o) => o.seatId === s.id));
  });
  selected.value = [];
}
function property(key: keyof PlanObject, value: string | number | null) {
  if (!current.value) return;
  if (
    typeof value === 'number' &&
    (!Number.isFinite(value) || (['width', 'height'].includes(key) && value <= 0))
  )
    return;
  mutate((p) => {
    const o = p.objects.find((o) => o.id === current.value?.id);
    if (o) Object.assign(o, { [key]: value });
  });
}
function seatProperty(key: 'number' | 'teamId', value: string | null) {
  if (!current.value) return;
  mutate((p) => {
    const s = p.seats.find((s) => s.id === current.value?.seatId);
    if (s) Object.assign(s, { [key]: value });
  });
}
function wallEndpoint(x: number, y: number) {
  if (!current.value) return;
  mutate((p) => {
    const o = p.objects.find((o) => o.id === current.value?.id);
    if (o) {
      o.width = Math.max(1, Math.hypot(x - o.x, y - o.y));
      o.rotation = (Math.atan2(y - o.y, x - o.x) * 180) / Math.PI;
    }
  });
}
function canvasSize(key: 'width' | 'height', value: string | number | null) {
  const n = Number(value);
  if (n >= 200 && n <= 20000)
    mutate((p) => {
      p[key] = n;
    });
}
type Point = { x: number; y: number };
type Gesture = {
  type: 'move' | 'pan' | 'box' | 'wall' | 'resize' | 'rotate';
  start: Point;
  matrix: DOMMatrix;
  before: Plan;
  view: typeof view.value;
  id?: string | undefined;
  additive?: boolean;
  seatId?: string | undefined;
  pointerStart: Point;
  moved?: boolean;
};
let gesture: Gesture | null = null;
const marquee = ref<{ x: number; y: number; width: number; height: number } | null>(null);
function begin(e: PointerEvent, type: Gesture['type'], id?: string) {
  if (!active.value) return;
  const matrix = svg.value?.getScreenCTM()?.inverse();
  if (!matrix) return;
  svg.value?.setPointerCapture(e.pointerId);
  gesture = {
    type,
    start: new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix),
    matrix,
    before: copy(props.modelValue),
    view: copy(view.value),
    id,
    additive: e.shiftKey,
    pointerStart: { x: e.clientX, y: e.clientY },
  };
  if (['move', 'resize', 'rotate'].includes(type)) checkpoint();
}
function startBackground(e: PointerEvent) {
  if (e.button !== 0 && e.button !== 1) return;
  if (!props.editable || tool.value === 'pan' || e.button === 1) {
    begin(e, 'pan');
    return;
  }
  if (tool.value === 'select') {
    if (!e.shiftKey) selected.value = [];
    begin(e, 'box');
    return;
  }
  const matrix = svg.value?.getScreenCTM()?.inverse();
  if (!matrix) return;
  const pos = new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix);
  const kind = tool.value;
  const id = add(kind, pos.x, pos.y);
  if (kind === 'wall') begin(e, 'wall', id);
  else tool.value = 'select';
}
function startObject(e: PointerEvent, o: PlanObject) {
  if (e.button !== 0 && e.button !== 1) return;
  if (!props.editable) {
    begin(e, 'pan');
    if (gesture && e.button === 0 && o.seatId && matches(o)) gesture.seatId = o.seatId;
    return;
  }
  if (tool.value !== 'select' || e.button === 1) {
    startBackground(e);
    return;
  }
  if (e.shiftKey) {
    if (selected.value.includes(o.id)) {
      selected.value = selected.value.filter((id) => id !== o.id);
      return;
    }
    selected.value.push(o.id);
  } else if (!selected.value.includes(o.id)) selected.value = [o.id];
  begin(e, 'move');
}
function activateSeat(o: PlanObject) {
  if (!props.editable && o.seatId && matches(o)) emit('selectSeat', o.seatId);
}
function startTransform(e: PointerEvent, o: PlanObject, type: 'resize' | 'rotate') {
  begin(e, type, o.id);
}
function move(e: PointerEvent) {
  const g = gesture;
  if (!g || !active.value) return;
  if (Math.hypot(e.clientX - g.pointerStart.x, e.clientY - g.pointerStart.y) > 5) g.moved = true;
  const pos = new DOMPoint(e.clientX, e.clientY).matrixTransform(g.matrix);
  const dx = pos.x - g.start.x,
    dy = pos.y - g.start.y;
  if (g.type === 'pan') {
    view.value = { ...g.view, x: g.view.x - dx, y: g.view.y - dy };
    return;
  }
  if (g.type === 'box') {
    marquee.value = {
      x: Math.min(g.start.x, pos.x),
      y: Math.min(g.start.y, pos.y),
      width: Math.abs(dx),
      height: Math.abs(dy),
    };
    return;
  }
  if (g.type === 'wall') {
    const p = copy(props.modelValue),
      o = p.objects.find((o) => o.id === g.id);
    if (o) {
      const x = round(pos.x),
        y = round(pos.y);
      o.width = Math.max(1, Math.hypot(x - o.x, y - o.y));
      o.rotation = (Math.atan2(y - o.y, x - o.x) * 180) / Math.PI;
      content(p);
    }
    return;
  }
  const p = copy(g.before);
  if (g.type === 'move') {
    for (const o of p.objects)
      if (selected.value.includes(o.id)) {
        o.x += round(dx);
        o.y += round(dy);
      }
  } else {
    const o = p.objects.find((o) => o.id === g.id);
    if (!o) return;
    if (g.type === 'rotate') {
      const angle =
        Math.atan2(pos.y - o.y, pos.x - o.x) - Math.atan2(g.start.y - o.y, g.start.x - o.x);
      o.rotation = ((o.rotation + (angle * 180) / Math.PI + 540) % 360) - 180;
      if (snap.value) o.rotation = Math.round(o.rotation / 15) * 15;
    } else {
      const a = (-o.rotation * Math.PI) / 180,
        x = pos.x - o.x,
        y = pos.y - o.y;
      o.width = Math.max(10, round(x * Math.cos(a) - y * Math.sin(a)));
      o.height = Math.max(4, round(x * Math.sin(a) + y * Math.cos(a)));
    }
  }
  content(p);
}
function end(e: PointerEvent) {
  const clickedSeat =
    active.value &&
    gesture?.seatId &&
    !gesture.moved &&
    Math.hypot(e.clientX - gesture.pointerStart.x, e.clientY - gesture.pointerStart.y) <= 5
      ? gesture.seatId
      : null;
  if (gesture?.type === 'box' && marquee.value) {
    const b = marquee.value;
    const ids = props.modelValue.objects
      .filter((o) => {
        const a = (o.rotation * Math.PI) / 180;
        return [
          [0, 0],
          [o.width, 0],
          [0, o.height],
          [o.width, o.height],
        ].every(([x = 0, y = 0]) => {
          const px = o.x + x * Math.cos(a) - y * Math.sin(a),
            py = o.y + x * Math.sin(a) + y * Math.cos(a);
          return px >= b.x && px <= b.x + b.width && py >= b.y && py <= b.y + b.height;
        });
      })
      .map((o) => o.id);
    selected.value = [...new Set([...(gesture.additive ? selected.value : []), ...ids])];
  }
  if (gesture?.type === 'wall') tool.value = 'select';
  if (svg.value?.hasPointerCapture(e.pointerId)) svg.value.releasePointerCapture(e.pointerId);
  gesture = null;
  marquee.value = null;
  if (clickedSeat) emit('selectSeat', clickedSeat);
}
function cancelGesture(e: PointerEvent) {
  if (gesture) gesture.seatId = undefined;
  if (gesture && !['box', 'pan', 'wall'].includes(gesture.type)) content(gesture.before);
  end(e);
}
function keyboard(e: KeyboardEvent) {
  if (!active.value || (e.target as HTMLElement).closest('input,textarea,[contenteditable=true]'))
    return;
  if (e.key === 'Escape') {
    selected.value = [];
    expanded.value = false;
    deactivate();
    return;
  }
  if (!props.editable) return;
  const command = e.ctrlKey || e.metaKey;
  if (command && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    if (e.shiftKey) redo();
    else undo();
  } else if (command && e.key.toLowerCase() === 'y') {
    e.preventDefault();
    redo();
  } else if (command && e.key.toLowerCase() === 'd') {
    e.preventDefault();
    if (selected.value.length) duplicate();
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault();
    if (selected.value.length) remove();
  } else if (e.key.startsWith('Arrow') && selected.value.length) {
    e.preventDefault();
    const step = e.shiftKey ? 20 : 1;
    mutate((p) => {
      for (const o of p.objects)
        if (selected.value.includes(o.id)) {
          o.x += e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
          o.y += e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
        }
    });
  }
}
</script>

<style scoped>
.floor-plan {
  border: 1px solid var(--space-line, #e2e7ee);
  border-radius: 10px;
  overflow: hidden;
  background: var(--space-surface, white);
  outline: none;
}
.floor-plan:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 2px;
}
.plan-toolbar {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--space-line, #e2e7ee);
  background: var(--space-surface, white);
}
.plan-toolbar__group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.plan-toolbar__label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--space-muted, #64748b);
}
.plan-zoom {
  display: flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--space-line, #e2e7ee);
  border-radius: 6px;
}
.plan-zoom span {
  font-size: 12px;
  min-width: 40px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.plan-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  height: clamp(460px, calc(100vh - 560px), 700px);
}
.plan-body.editing {
  grid-template-columns: 176px minmax(300px, 1fr) 248px;
}
.tools,
.properties {
  padding: 16px;
  overflow-y: auto;
  background: var(--space-surface, white);
}
.tools {
  border-right: 1px solid var(--space-line, #e2e7ee);
  padding: 16px 12px;
}
.properties {
  border-left: 1px solid var(--space-line, #e2e7ee);
}
.plan-panel-title {
  font-size: 14px;
  font-weight: 700;
}
.plan-section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--space-muted, #64748b);
  margin-bottom: 10px;
}
.plan-mode-tools {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 12px 0 20px;
}
.plan-mode-tools .q-btn {
  justify-content: flex-start;
  font-size: 13px;
}
.plan-mode-tools :deep(.q-btn__content) {
  justify-content: flex-start;
}
.plan-mode-tools :deep(.q-icon) {
  font-size: 20px;
}
.plan-object-tools {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.plan-object-tools .q-btn {
  min-height: 64px;
  border: 1px solid var(--space-line, #e2e7ee);
  padding: 8px 2px;
  font-size: 11px;
}
.plan-object-tools :deep(.q-icon) {
  font-size: 22px;
  margin-bottom: 6px;
}
.tool-active {
  background: var(--space-soft, #eef5fc) !important;
  color: var(--q-primary);
  border-color: var(--q-primary) !important;
}
.tool-guidance {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-top: 14px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--space-muted, #64748b);
}
.tool-guidance .q-icon {
  margin-top: 2px;
}
.plan-selection-actions {
  display: flex;
  justify-content: space-between;
}
.plan-selection-actions .q-btn {
  font-size: 12px;
}
.plan-selection-actions :deep(.q-icon) {
  font-size: 17px;
}
.plan-settings :deep(.q-item) {
  padding: 0;
  font-size: 12px;
  color: var(--space-muted, #64748b);
}
.canvas-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.plan-active .canvas-wrap {
  outline: 2px solid var(--q-primary);
  outline-offset: -2px;
}
.plan-svg {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  touch-action: none;
  user-select: none;
}
.canvas-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
  color: #64748b;
  pointer-events: none;
}
.canvas-empty strong {
  font-size: 16px;
  font-weight: 600;
}
.canvas-empty span {
  font-size: 13px;
  line-height: 1.8;
  max-width: 260px;
}
.property-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 14px;
  padding: 44px 4px;
  color: var(--space-muted, #64748b);
  font-size: 13px;
}
.property-empty strong {
  font-weight: 500;
}
.property-empty p {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
}
.plan-statusbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 16px;
  border-top: 1px solid var(--space-line, #e2e7ee);
  color: var(--space-muted, #64748b);
  font-size: 11px;
  min-height: 35px;
}
.plan-expanded {
  position: fixed;
  inset: 12px;
  z-index: 5900;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--space-line, #e2e7ee) !important;
  border-radius: 12px !important;
  box-shadow: 0 0 0 100vmax #15203466;
}
.plan-expanded .plan-body {
  height: auto;
  flex: 1;
  min-height: 0;
}
.movable {
  cursor: move;
}
.seat {
  cursor: pointer;
}
.resize-handle {
  cursor: nwse-resize;
}
.rotate-handle {
  cursor: crosshair;
}
@media (max-width: 1000px) {
  .plan-body.editing {
    grid-template-columns: 155px minmax(300px, 1fr) 220px;
    overflow-x: auto;
  }
}
@media (max-width: 600px) {
  .plan-body {
    height: 400px;
  }
  .plan-toolbar {
    padding: 8px;
  }
  .plan-toolbar__group {
    gap: 2px;
  }
  .plan-statusbar {
    font-size: 10px;
  }
  .plan-expanded {
    inset: 4px;
  }
}
</style>
