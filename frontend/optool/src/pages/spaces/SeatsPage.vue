<template>
  <q-page class="spaces-page">
    <SpaceHeader
      title="좌석 배정"
      description="사무실별 좌석 현황과 인원 배정을 관리합니다."
      :error="error || planError"
      :loading="loading || planLoading"
      @reload="refresh"
    >
      <SpacePlanPdfButton
        v-if="roomId && plan.published"
        :room-id="roomId"
        :disabled="loading || planLoading || !!error || !!planError"
      />
      <q-btn
        v-if="data.editableRoomIds.includes(roomId)"
        outline
        color="primary"
        icon="edit"
        label="사무실 배치도"
        :to="{ name: 'space-room-plan', params: { roomId } }"
      />
    </SpaceHeader>
    <RoomPicker :model-value="roomId" :data="data" @update:model-value="changeRoom" />
    <section v-if="!roomId && !loading" class="space-panel">
      <SpaceEmpty
        icon="meeting_room"
        title="사무실을 선택하세요"
        description="공간을 선택하면 게시된 배치도와 좌석 현황을 확인할 수 있습니다."
      />
    </section>
    <template v-if="roomId">
      <SpaceSummary
        :items="[
          { label: '전체 좌석', value: roomSeats.length, unit: '석', icon: 'event_seat' },
          { label: '배정된 좌석', value: occupied, unit: '석', icon: 'how_to_reg', tone: 'green' },
          {
            label: '미배정 좌석',
            value: roomSeats.length - occupied,
            unit: '석',
            icon: 'chair_alt',
            tone: 'slate',
          },
        ]"
      />
      <div class="seats-layout">
        <section class="space-panel seats-workspace">
          <div class="space-panel__heading">
            <h2>{{ data.rooms.find((r) => r.id === roomId)?.name }} 좌석</h2>
            <q-space /><q-tabs
              v-model="viewMode"
              dense
              no-caps
              active-color="primary"
              indicator-color="primary"
              class="seat-view-tabs"
              ><q-tab name="map" icon="map" label="배치도" /><q-tab
                name="list"
                icon="format_list_bulleted"
                label="목록"
            /></q-tabs>
          </div>
          <div class="space-filters">
            <q-input
              v-model="search"
              outlined
              dense
              clearable
              label="인원 이름 / 좌석번호 검색"
              class="space-search"
              ><template #prepend><q-icon name="search" size="20px" /></template></q-input
            ><q-select
              v-model="teamFilter"
              :options="
                roomTeams.map((t) => ({ label: `${t.name} (${teamCount(t.id)})`, value: t.id }))
              "
              emit-value
              map-options
              clearable
              outlined
              dense
              label="사용 팀"
            />
          </div>
          <div class="seat-filter-info">
            <q-toggle v-model="vacantOnly" dense label="미배정 좌석만" /><q-space /><span
              class="space-muted"
              >{{ rows.length }}개 좌석 표시</span
            ><q-btn
              v-if="search || teamFilter || vacantOnly"
              flat
              dense
              color="primary"
              label="초기화"
              @click="resetFilters"
            />
          </div>
          <q-skeleton v-if="planLoading" height="480px" square animation="fade" />
          <template v-else-if="!planError">
            <SpaceEmpty
              v-if="!plan.published"
              icon="map"
              title="게시된 배치도가 없습니다"
              description="배치도를 만들고 게시하면 좌석에 인원을 배정할 수 있습니다."
              ><q-btn
                v-if="data.editableRoomIds.includes(roomId)"
                unelevated
                color="primary"
                label="배치도 만들기"
                :to="{ name: 'space-room-plan', params: { roomId }, query: { edit: '1' } }"
            /></SpaceEmpty>
            <template v-else-if="viewMode === 'map'">
              <div v-if="!rows.length && roomSeats.length" class="seat-search-empty">
                조건에 맞는 좌석이 없습니다. 검색어나 필터를 변경해 주세요.
              </div>
              <FloorPlanCanvas
                :key="roomId + canvasKey"
                :model-value="plan"
                :teams="roomTeams"
                :assignments="data.assignments"
                :people="data.people"
                :team-filter="teamFilter"
                :visible-seat-ids="rows.map((s) => s.id)"
                :selected-seat-id="selectedId"
                @select-seat="openSeat"
              />
              <div class="space-legend">
                <span v-for="team in roomTeams" :key="team.id" class="space-team-label"
                  ><span class="space-team-dot" :style="{ background: team.color }" />{{
                    team.name
                  }}</span
                ><span v-if="roomSeats.some((s) => !s.teamId)" class="space-team-label"
                  ><span class="space-team-dot" style="background: #78909c" />팀 미지정</span
                >
              </div>
            </template>
            <q-table
              v-else
              flat
              class="space-table seat-table"
              :rows="rows"
              :columns="columns"
              row-key="id"
              :pagination="{ rowsPerPage: 10 }"
              :rows-per-page-options="[10, 20, 50]"
              rows-per-page-label="페이지당 좌석"
              :table-row-class-fn="(seat) => (seat.id === selectedId ? 'seat-row-selected' : '')"
              @row-click="(_e, seat) => openSeat(seat.id)"
            >
              <template #body-cell-number="p"
                ><q-td :props="p"
                  ><q-btn
                    flat
                    dense
                    color="primary"
                    icon="event_seat"
                    :label="p.row.number"
                    @click.stop="openSeat(p.row.id)" /></q-td
              ></template>
              <template #body-cell-team="p"
                ><q-td :props="p"
                  ><span class="space-team-label"
                    ><span
                      class="space-team-dot"
                      :style="{
                        background:
                          data.teams.find((t) => t.id === p.row.teamId)?.color || '#78909c',
                      }"
                    />{{ teamName(p.row.teamId) }}</span
                  ></q-td
                ></template
              >
              <template #body-cell-person="p"
                ><q-td :props="p"
                  ><strong v-if="occupant(p.row.id)">{{ occupant(p.row.id)?.name }}</strong
                  ><q-badge v-else color="grey-2" text-color="grey-7" label="미배정" /></q-td
              ></template>
              <template #no-data
                ><SpaceEmpty
                  title="조건에 맞는 좌석이 없습니다"
                  description="검색어나 사용 팀을 변경해 다시 찾아보세요."
                  ><q-btn
                    flat
                    color="primary"
                    label="필터 초기화"
                    @click="resetFilters" /></SpaceEmpty
              ></template>
            </q-table>
          </template>
        </section>
      </div>
    </template>
    <SeatAssignmentDialog
      v-model="assignmentOpen"
      :seat-id="selectedId"
      :data="data"
      :refresh="refreshAssignments"
    />
  </q-page>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { QTableColumn } from 'quasar';
import SpaceSummary from 'src/components/spaces/SpaceSummary.vue';
import SpaceEmpty from 'src/components/spaces/SpaceEmpty.vue';
import SpaceHeader from 'src/components/spaces/SpaceHeader.vue';
import SpacePlanPdfButton from 'src/components/spaces/SpacePlanPdfButton.vue';
import RoomPicker from 'src/components/spaces/RoomPicker.vue';
import FloorPlanCanvas from 'src/components/spaces/FloorPlanCanvas.vue';
import SeatAssignmentDialog from 'src/components/spaces/SeatAssignmentDialog.vue';
import { blankPlan, spaceApi, type Seat } from 'src/services/spaces';
import { getErrorMessage } from 'src/utils/http/error';
import { useSpaces } from './useSpaces';
const { data, loading, error, reload, teamName } = useSpaces();
const router = useRouter();
const route = useRoute(),
  roomId = ref(''),
  plan = ref(blankPlan()),
  planLoading = ref(false),
  planError = ref(''),
  canvasKey = ref(0);
const viewMode = ref('map');
const selectedId = ref<string | null>(null),
  assignmentOpen = ref(false),
  search = ref(''),
  teamFilter = ref<string | null>(null),
  vacantOnly = ref(false);
const roomTeams = computed(() =>
  data.value.teams.filter((t) =>
    data.value.rooms.find((r) => r.id === roomId.value)?.teamIds.includes(t.id),
  ),
);
const roomSeats = computed(() => data.value.seats.filter((s) => s.roomId === roomId.value));
const occupied = computed(() => roomSeats.value.filter((s) => occupant(s.id)).length);
function openSeat(id: string) {
  selectedId.value = id;
  assignmentOpen.value = true;
}
function occupant(seatId: string) {
  const a = data.value.assignments.find((a) => a.seatId === seatId);
  return data.value.people.find((p) => p.id === a?.personId);
}
function resetFilters() {
  search.value = '';
  teamFilter.value = null;
  vacantOnly.value = false;
}
function teamCount(id: string) {
  const seats = roomSeats.value.filter((s) => s.teamId === id);
  return `배정 ${seats.filter((s) => occupant(s.id)).length}/${seats.length}석`;
}
const rows = computed(() =>
  roomSeats.value.filter(
    (s) =>
      (!teamFilter.value || s.teamId === teamFilter.value) &&
      (!vacantOnly.value || !occupant(s.id)) &&
      `${s.number} ${occupant(s.id)?.name ?? ''}`
        .toLowerCase()
        .includes((search.value || '').toLowerCase()),
  ),
);
const columns: QTableColumn<Seat>[] = [
  { name: 'number', label: '좌석', field: 'number', align: 'left', sortable: true },
  { name: 'team', label: '팀', field: 'teamId', align: 'left' },
  { name: 'person', label: '인원', field: 'id', align: 'left' },
];
let requestId = 0;
async function loadPlan() {
  const request = ++requestId;
  planLoading.value = true;
  planError.value = '';
  try {
    const result = await spaceApi.plan(roomId.value);
    if (request === requestId) {
      plan.value = result;
      canvasKey.value++;
    }
  } catch (e) {
    if (request === requestId)
      planError.value = getErrorMessage(e, '배치도를 불러오지 못했습니다.');
  } finally {
    if (request === requestId) planLoading.value = false;
  }
}
watch(
  () => data.value.rooms,
  (rooms) => {
    if (!roomId.value && rooms.length) {
      roomId.value =
        typeof route.query.room === 'string' && rooms.some((r) => r.id === route.query.room)
          ? route.query.room
          : (rooms[0]?.id ?? '');
      selectedId.value =
        typeof route.query.seat === 'string'
          ? route.query.seat
          : (data.value.assignments.find((a) => a.personId === route.query.person)?.seatId ?? null);
      void loadPlan();
    }
  },
);
watch(selectedId, (id) => {
  assignmentOpen.value = !!id;
});
async function changeRoom(id: string) {
  roomId.value = id;
  selectedId.value = null;
  assignmentOpen.value = false;
  teamFilter.value = null;
  search.value = '';
  if (id) await loadPlan();
  await router.replace({ query: { room: id || undefined } });
}
watch(
  () => route.query,
  (query) => {
    const id = typeof query.room === 'string' ? query.room : '';
    if (id && id !== roomId.value && data.value.rooms.some((r) => r.id === id)) {
      roomId.value = id;
      teamFilter.value = null;
      void loadPlan();
    }
    selectedId.value =
      typeof query.seat === 'string'
        ? query.seat
        : (data.value.assignments.find((a) => a.personId === query.person)?.seatId ?? null);
  },
);
async function refreshAssignments() {
  const target = roomId.value;
  await reload();
  if (error.value) throw new Error(error.value);
  const result = await spaceApi.plan(target);
  if (target === roomId.value) plan.value = result;
}
async function refresh() {
  await reload();
  if (roomId.value) await loadPlan();
}
onBeforeUnmount(() => {
  requestId++;
});
</script>

<style scoped>
.seats-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
.seats-workspace :deep(.floor-plan) {
  border: 0;
  border-radius: 0;
}
.seats-workspace :deep(.canvas-wrap),
.seats-workspace :deep(.plan-svg) {
  min-height: 450px;
}
.seat-view-tabs :deep(.q-tab) {
  min-height: 36px;
  padding: 0 12px;
}
.seat-view-tabs :deep(.q-tab__content) {
  flex-direction: row;
  gap: 6px;
  min-width: 0;
}
.seat-view-tabs :deep(.q-tab__icon) {
  font-size: 18px;
  height: 20px;
  width: 20px;
}
.seat-filter-info {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 0 20px 16px;
  font-size: 12px;
}
.seat-search-empty {
  padding: 12px 20px;
  color: var(--space-muted);
  background: var(--space-bg);
  font-size: 13px;
}
.seat-table :deep(tr) {
  cursor: pointer;
}
.seat-table :deep(.seat-row-selected) {
  background: var(--space-soft);
}
</style>
