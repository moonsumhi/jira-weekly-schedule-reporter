<template>
  <q-page class="spaces-page">
    <SpaceHeader
      title="공간 관리"
      description="사무실의 사용 팀을 지정하고, 배치도를 만들어 좌석을 구성하세요."
      :error="error"
      :loading="loading"
      @reload="reload"
    >
      <template v-if="data.canManage">
        <q-btn outline color="primary" icon="groups" label="팀 관리" @click="teamDialog = true" />
        <q-btn
          v-if="data.floors.length"
          unelevated
          color="primary"
          icon="add"
          label="사무실 등록"
          @click="edit('rooms')"
        />
        <q-btn
          v-else-if="data.buildings.length"
          unelevated
          color="primary"
          icon="add"
          label="층 등록"
          @click="edit('floors')"
        />
        <q-btn
          v-else
          unelevated
          color="primary"
          icon="add"
          label="건물 등록"
          @click="edit('buildings')"
        />
      </template>
    </SpaceHeader>
    <SpaceSummary
      :items="[
        {
          label: '등록 사무실',
          value: data.rooms.length,
          unit: '개',
          icon: 'meeting_room',
          hint: `${data.buildings.length}개 건물 · ${data.floors.length}개 층`,
        },
        {
          label: '배정된 좌석',
          value: data.assignments.length,
          unit: '석',
          icon: 'event_seat',
          tone: 'green',
        },
        {
          label: '미배정 좌석',
          value: data.seats.length - data.assignments.length,
          unit: '석',
          icon: 'chair_alt',
          tone: 'slate',
        },
      ]"
    />
    <div class="rooms-layout">
      <aside class="space-panel rooms-tree">
        <div class="space-panel__heading">
          <h2>건물·층</h2>
          <q-space /><q-btn
            v-if="data.canManage"
            flat
            dense
            round
            color="primary"
            icon="add"
            aria-label="건물 등록"
            @click="edit('buildings')"
            ><q-tooltip>건물 등록</q-tooltip></q-btn
          >
        </div>
        <q-list class="q-pa-sm">
          <q-item
            clickable
            :active="!floorFilter && !buildingFilter"
            active-class="rooms-tree__active"
            @click="
              floorFilter = null;
              buildingFilter = null;
            "
          >
            <q-item-section avatar><q-icon name="domain" size="20px" /></q-item-section
            ><q-item-section>전체 사무실</q-item-section
            ><q-item-section side>{{ data.rooms.length }}</q-item-section>
          </q-item>
          <q-expansion-item v-for="building in data.buildings" :key="building.id" default-opened>
            <template #header>
              <q-item-section avatar><q-icon name="apartment" size="20px" /></q-item-section>
              <q-item-section class="text-weight-medium">{{ building.name }}</q-item-section>
              <q-item-section v-if="data.canManage" side>
                <q-btn
                  flat
                  dense
                  round
                  size="sm"
                  icon="more_horiz"
                  :aria-label="`${building.name} 관리`"
                  @click.stop
                >
                  <q-menu
                    ><q-list style="min-width: 150px">
                      <q-item
                        clickable
                        v-close-popup
                        @click="
                          buildingFilter = building.id;
                          floorFilter = null;
                        "
                        ><q-item-section>이 건물 사무실 보기</q-item-section></q-item
                      >
                      <q-item
                        clickable
                        v-close-popup
                        @click="edit('floors', undefined, building.id)"
                        ><q-item-section>층 추가</q-item-section></q-item
                      >
                      <q-item clickable v-close-popup @click="edit('buildings', building)"
                        ><q-item-section>건물 수정</q-item-section></q-item
                      >
                      <q-separator /><q-item
                        clickable
                        v-close-popup
                        class="text-negative"
                        @click="remove('buildings', building.id)"
                        ><q-item-section>건물 삭제</q-item-section></q-item
                      >
                    </q-list></q-menu
                  >
                </q-btn>
              </q-item-section>
            </template>
            <q-item
              v-for="floor in data.floors.filter((f) => f.buildingId === building.id)"
              :key="floor.id"
              clickable
              class="rooms-tree__floor"
              :active="floorFilter === floor.id"
              active-class="rooms-tree__active"
              @click="
                floorFilter = floor.id;
                buildingFilter = building.id;
              "
            >
              <q-item-section>{{ floor.name }}</q-item-section
              ><q-item-section side class="space-muted">{{
                data.rooms.filter((r) => r.floorId === floor.id).length
              }}</q-item-section>
              <q-item-section v-if="data.canManage" side>
                <q-btn
                  flat
                  dense
                  round
                  size="sm"
                  icon="more_horiz"
                  :aria-label="`${floor.name} 관리`"
                  @click.stop
                >
                  <q-menu
                    ><q-list style="min-width: 130px"
                      ><q-item clickable v-close-popup @click="edit('floors', floor)"
                        ><q-item-section>층 수정</q-item-section></q-item
                      ><q-item
                        clickable
                        v-close-popup
                        class="text-negative"
                        @click="remove('floors', floor.id)"
                        ><q-item-section>층 삭제</q-item-section></q-item
                      ></q-list
                    ></q-menu
                  >
                </q-btn>
              </q-item-section>
            </q-item>
            <div
              v-if="!data.floors.some((f) => f.buildingId === building.id)"
              class="q-pa-md text-caption space-muted"
            >
              등록된 층이 없습니다.<q-btn
                v-if="data.canManage"
                flat
                dense
                color="primary"
                label="층 추가"
                @click="edit('floors', undefined, building.id)"
              />
            </div>
          </q-expansion-item>
        </q-list>
        <div v-if="!data.buildings.length" class="q-pa-lg text-caption space-muted">
          건물을 등록하면 층별로 사무실을 찾아볼 수 있습니다.
        </div>
      </aside>
      <section class="space-panel">
        <div class="space-panel__heading">
          <h2>{{ filterLabel }}</h2>
          <q-badge color="blue-1" text-color="primary">{{ rooms.length }}개</q-badge>
        </div>
        <div class="space-filters">
          <q-input
            v-model="search"
            outlined
            dense
            clearable
            label="사무실 검색"
            class="space-search"
            ><template #prepend><q-icon name="search" size="20px" /></template
          ></q-input>
          <q-select
            v-model="teamFilter"
            :options="teamOptions"
            emit-value
            map-options
            clearable
            outlined
            dense
            label="사용 팀"
          />
          <q-btn
            flat
            color="grey-7"
            icon="restart_alt"
            label="초기화"
            :disable="!search && !teamFilter && !floorFilter && !buildingFilter"
            @click="resetFilters"
          />
        </div>
        <q-table
          flat
          class="space-table"
          :rows="rooms"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="{ rowsPerPage: 20 }"
          :rows-per-page-options="[20, 50]"
          rows-per-page-label="페이지당 사무실"
        >
          <template #body-cell-name="p"
            ><q-td :props="p"
              ><div class="space-person">
                <q-avatar rounded size="38px" icon="meeting_room" />
                <div>
                  <strong>{{ p.row.name }}</strong>
                  <div class="text-caption space-muted">{{ roomPath(p.row) }}</div>
                </div>
              </div></q-td
            ></template
          >
          <template #body-cell-teams="p"
            ><q-td :props="p"
              ><div class="rooms-team-list">
                <span v-for="id in p.row.teamIds" :key="id" class="space-team-label"
                  ><span
                    class="space-team-dot"
                    :style="{ background: data.teams.find((t) => t.id === id)?.color }"
                  />{{ teamName(id) }}</span
                ><span v-if="!p.row.teamIds.length" class="space-muted">미지정</span>
              </div></q-td
            ></template
          >
          <template #body-cell-seats="p"
            ><q-td :props="p"
              ><div>
                <strong>{{ counts(p.row.id).assigned }}</strong
                ><span class="space-muted"> / {{ counts(p.row.id).total }}석 배정</span>
              </div>
              <q-linear-progress
                rounded
                size="4px"
                :value="
                  counts(p.row.id).total ? counts(p.row.id).assigned / counts(p.row.id).total : 0
                "
                color="primary"
                track-color="blue-grey-1"
                class="q-mt-sm"
                style="max-width: 120px"
              />
              <div class="text-caption space-muted q-mt-xs">
                미배정 {{ counts(p.row.id).total - counts(p.row.id).assigned }}석
              </div></q-td
            ></template
          >
          <template #body-cell-plan="p"
            ><q-td :props="p"
              ><q-badge
                :color="
                  data.plans.find((x) => x.roomId === p.row.id)?.published ? 'green-1' : 'grey-2'
                "
                :text-color="
                  data.plans.find((x) => x.roomId === p.row.id)?.published ? 'green-9' : 'grey-8'
                "
                :label="
                  data.plans.find((x) => x.roomId === p.row.id)?.published
                    ? '게시됨'
                    : data.plans.find((x) => x.roomId === p.row.id)?.hasDraft
                      ? '임시저장'
                      : '미생성'
                " /></q-td
          ></template>
          <template #body-cell-actions="p"
            ><q-td :props="p"
              ><q-btn
                flat
                dense
                color="primary"
                :label="
                  !data.plans.some((x) => x.roomId === p.row.id) &&
                  data.editableRoomIds.includes(p.row.id)
                    ? '배치도 만들기'
                    : '배치도 열기'
                "
                icon-right="chevron_right"
                :to="{
                  name: 'space-room-plan',
                  params: { roomId: p.row.id },
                  query:
                    !data.plans.some((x) => x.roomId === p.row.id) &&
                    data.editableRoomIds.includes(p.row.id)
                      ? { edit: '1' }
                      : {},
                }"
              /><q-btn
                v-if="data.canManage || canDeletePlan(p.row.id)"
                flat
                dense
                round
                icon="more_horiz"
                :aria-label="`${p.row.name} 관리`"
                ><q-menu
                  ><q-list style="min-width: 140px"
                    ><q-item
                      v-if="data.canManage"
                      clickable
                      v-close-popup
                      @click="edit('rooms', p.row)"
                      ><q-item-section avatar><q-icon name="edit" size="18px" /></q-item-section
                      ><q-item-section>수정</q-item-section></q-item
                    ><q-item
                      v-if="canDeletePlan(p.row.id)"
                      clickable
                      v-close-popup
                      class="text-negative"
                      @click="removePlan(p.row.id)"
                      ><q-item-section avatar
                        ><q-icon name="layers_clear" size="18px" /></q-item-section
                      ><q-item-section>배치도 삭제</q-item-section></q-item
                    ><q-separator v-if="data.canManage && canDeletePlan(p.row.id)" />
                    <q-item
                      v-if="data.canManage"
                      clickable
                      v-close-popup
                      class="text-negative"
                      @click="remove('rooms', p.row.id)"
                      ><q-item-section avatar
                        ><q-icon name="delete_outline" size="18px" /></q-item-section
                      ><q-item-section>삭제</q-item-section></q-item
                    ></q-list
                  ></q-menu
                ></q-btn
              ></q-td
            ></template
          >
          <template #no-data
            ><SpaceEmpty
              icon="meeting_room"
              :title="
                data.rooms.length ? '조건에 맞는 사무실이 없습니다' : '공간 구성을 시작해 보세요'
              "
              :description="
                data.rooms.length
                  ? '검색어나 선택한 건물·층을 변경해 주세요.'
                  : '건물 → 층 → 사무실 순서로 등록하면 배치도를 만들 수 있습니다.'
              "
              ><q-btn
                v-if="data.rooms.length"
                flat
                color="primary"
                label="필터 초기화"
                @click="resetFilters" /><q-btn
                v-else-if="data.canManage"
                unelevated
                color="primary"
                icon="add"
                :label="
                  !data.buildings.length
                    ? '건물 등록'
                    : !data.floors.length
                      ? '층 등록'
                      : '사무실 등록'
                "
                @click="
                  edit(
                    !data.buildings.length ? 'buildings' : !data.floors.length ? 'floors' : 'rooms',
                  )
                " /></SpaceEmpty
          ></template>
        </q-table>
      </section>
    </div>
    <q-dialog v-model="teamDialog"
      ><q-card class="space-dialog">
        <q-card-section class="space-dialog__header"
          ><div class="row items-center">
            <h2>팀 관리</h2>
            <q-space /><q-btn flat round dense icon="close" aria-label="닫기" v-close-popup />
          </div>
          <p>
            팀과 표시 색상을 관리합니다. 인적자원 관리 메뉴에 접근할 수 있으면 모든 팀과 공간을
            관리할 수 있습니다.
          </p></q-card-section
        >
        <q-list separator class="q-px-sm"
          ><q-item v-for="team in data.teams" :key="team.id" class="q-py-md"
            ><q-item-section avatar
              ><q-avatar size="36px" color="grey-2"
                ><q-icon name="groups" :style="{ color: team.color }" /></q-avatar></q-item-section
            ><q-item-section
              ><q-item-label class="text-weight-medium">{{
                team.name
              }}</q-item-label></q-item-section
            ><q-item-section side
              ><q-btn
                flat
                color="primary"
                label="수정"
                @click="edit('teams', team)" /></q-item-section></q-item
        ></q-list>
        <q-card-actions align="right" class="space-dialog__actions"
          ><q-btn unelevated color="primary" icon="add" label="팀 추가" @click="edit('teams')"
        /></q-card-actions> </q-card
    ></q-dialog>
    <q-dialog v-model="dialog" :persistent="busy" no-backdrop-dismiss
      ><q-card class="space-dialog"
        ><q-form @submit="save">
          <q-card-section class="space-dialog__header"
            ><div class="row items-center">
              <h2>{{ labels[kind] }} {{ editingId ? '수정' : '등록' }}</h2>
              <q-space /><q-btn
                flat
                round
                dense
                icon="close"
                aria-label="닫기"
                :disable="busy"
                v-close-popup
              />
            </div>
            <p>
              {{
                kind === 'rooms'
                  ? '공간 정보와 사용 팀을 설정하세요.'
                  : '기본 정보를 입력하세요. * 표시는 필수 항목입니다.'
              }}
            </p></q-card-section
          >
          <q-card-section class="space-dialog__body">
            <section class="space-form-section">
              <h3>기본 정보</h3>
              <div class="space-form-grid">
                <q-input
                  v-model="form.name"
                  outlined
                  dense
                  :label="`${labels[kind]}명 *`"
                  maxlength="100"
                  :disable="kind === 'teams' && !!editingId"
                  :rules="[required]"
                  hide-bottom-space
                  :class="{ 'space-form-wide': kind === 'buildings' || kind === 'teams' }"
                />
                <q-select
                  v-if="kind === 'floors'"
                  v-model="form.buildingId"
                  :options="data.buildings.map((b) => ({ label: b.name, value: b.id }))"
                  emit-value
                  map-options
                  outlined
                  dense
                  label="건물 *"
                  :rules="[required]"
                  hide-bottom-space
                />
                <q-select
                  v-if="kind === 'rooms'"
                  v-model="form.floorId"
                  :options="
                    data.floors.map((f) => ({
                      label: `${data.buildings.find((b) => b.id === f.buildingId)?.name} / ${f.name}`,
                      value: f.id,
                    }))
                  "
                  emit-value
                  map-options
                  outlined
                  dense
                  label="층 *"
                  :rules="[required]"
                  hide-bottom-space
                />
                <template v-if="kind === 'buildings' || kind === 'rooms'"
                  ><q-input
                    v-model="form.location"
                    outlined
                    dense
                    label="위치"
                    maxlength="300"
                    class="space-form-wide" /><q-input
                    v-model="form.description"
                    outlined
                    dense
                    type="textarea"
                    rows="2"
                    label="설명"
                    maxlength="1000"
                    class="space-form-wide"
                /></template>
              </div>
            </section>
            <template v-if="kind === 'rooms'">
              <section class="space-form-section">
                <h3>사용 팀</h3>
                <div class="space-form-grid">
                  <q-select
                    v-model="form.teamIds"
                    :options="teamOptions"
                    emit-value
                    map-options
                    multiple
                    use-chips
                    outlined
                    dense
                    label="사용 팀"
                    hint="여러 팀이 함께 사용하는 사무실도 등록할 수 있습니다."
                    class="space-form-wide"
                  />
                </div>
              </section>
            </template>
            <section v-if="kind === 'teams'" class="space-form-section">
              <h3>팀 구분</h3>
              <div class="space-form-grid">
                <q-input
                  v-model="form.color"
                  outlined
                  dense
                  label="팀 표시 색상"
                  :rules="[
                    (v) => /^#[0-9a-fA-F]{6}$/.test(String(v)) || '올바른 색상을 선택해 주세요.',
                  ]"
                  hide-bottom-space
                  class="space-form-wide"
                  ><template #prepend
                    ><q-icon name="circle" :style="{ color: form.color }" /></template
                  ><template #append
                    ><q-icon
                      name="palette"
                      class="cursor-pointer"
                      aria-label="색상 선택"
                      role="button"
                      tabindex="0"
                      ><q-popup-proxy cover
                        ><q-color
                          v-model="form.color"
                          no-header
                          no-footer
                          default-view="palette" /></q-popup-proxy></q-icon></template
                ></q-input>
              </div>
            </section>
          </q-card-section>
          <q-card-actions align="right" class="space-dialog__actions"
            ><q-btn flat label="취소" v-close-popup :disable="busy" /><q-btn
              unelevated
              color="primary"
              type="submit"
              :label="editingId ? '변경사항 저장' : '등록'"
              :loading="busy"
          /></q-card-actions> </q-form></q-card
    ></q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue';
import type { QTableColumn } from 'quasar';
import SpaceSummary from 'src/components/spaces/SpaceSummary.vue';
import SpaceEmpty from 'src/components/spaces/SpaceEmpty.vue';
import SpaceHeader from 'src/components/spaces/SpaceHeader.vue';
import { spaceApi, type Room, type Building, type Floor, type Team } from 'src/services/spaces';
import { useSpaces } from './useSpaces';
const { data, loading, busy, error, reload, run, confirm, deletePlan, teamOptions, teamName } =
  useSpaces();
type Kind = 'buildings' | 'floors' | 'rooms' | 'teams';
const labels = { buildings: '건물', floors: '층', rooms: '사무실', teams: '팀' };
const kind = ref<Kind>('rooms'),
  dialog = ref(false),
  teamDialog = ref(false),
  editingId = ref<string | null>(null);
const floorFilter = ref<string | null>(null),
  buildingFilter = ref<string | null>(null),
  teamFilter = ref<string | null>(null),
  search = ref('');
const empty = () => ({
  name: '',
  location: '',
  description: '',
  buildingId: '',
  floorId: '',
  teamIds: [] as string[],
  managerIds: [] as string[],
  viewerIds: [] as string[],
  visibility: 'all' as 'all' | 'members',
  color: '#1976d2',
});
const form = ref(empty());
const required = (v: unknown) => !!v || '필수 항목입니다.';
const rooms = computed(() =>
  data.value.rooms.filter(
    (r) =>
      (!floorFilter.value || r.floorId === floorFilter.value) &&
      (!buildingFilter.value ||
        data.value.floors.find((f) => f.id === r.floorId)?.buildingId === buildingFilter.value) &&
      (!teamFilter.value || r.teamIds.includes(teamFilter.value)) &&
      r.name.toLowerCase().includes((search.value || '').toLowerCase()),
  ),
);
const filterLabel = computed(() =>
  floorFilter.value
    ? `${data.value.buildings.find((b) => b.id === buildingFilter.value)?.name ?? ''} · ${data.value.floors.find((f) => f.id === floorFilter.value)?.name ?? ''}`
    : buildingFilter.value
      ? data.value.buildings.find((b) => b.id === buildingFilter.value)?.name
      : '전체 사무실',
);
function roomPath(room: Room) {
  const floor = data.value.floors.find((f) => f.id === room.floorId);
  return `${data.value.buildings.find((b) => b.id === floor?.buildingId)?.name ?? ''} · ${floor?.name ?? ''}`;
}
function resetFilters() {
  search.value = '';
  teamFilter.value = null;
  floorFilter.value = null;
  buildingFilter.value = null;
}
function counts(roomId: string) {
  const seats = data.value.seats.filter((s) => s.roomId === roomId);
  return {
    total: seats.length,
    assigned: seats.filter((s) => data.value.assignments.some((a) => a.seatId === s.id)).length,
  };
}
function canDeletePlan(id: string) {
  return data.value.editableRoomIds.includes(id) && data.value.plans.some((p) => p.roomId === id);
}
async function removePlan(id: string) {
  const plan = data.value.plans.find((p) => p.roomId === id);
  if (plan) await deletePlan(id, plan.version);
}
const columns: QTableColumn<Room>[] = [
  { name: 'name', label: '사무실', field: 'name', align: 'left', sortable: true },
  { name: 'teams', label: '사용 팀', field: 'teamIds', align: 'left' },
  { name: 'seats', label: '좌석 현황', field: 'id', align: 'left' },
  { name: 'plan', label: '배치도', field: 'id', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];
function edit(k: Kind, entity?: Room | Building | Floor | Team, parent?: string) {
  kind.value = k;
  editingId.value = entity?.id ?? null;
  form.value = {
    ...empty(),
    floorId: floorFilter.value ?? data.value.floors[0]?.id ?? '',
    buildingId: parent ?? data.value.buildings[0]?.id ?? '',
    ...(JSON.parse(JSON.stringify(entity ?? {})) as object),
  };
  dialog.value = true;
}
async function save() {
  const f = form.value;
  const body =
    kind.value === 'teams'
      ? { name: f.name, color: f.color, managerIds: f.managerIds }
      : kind.value === 'floors'
        ? { name: f.name, buildingId: f.buildingId }
        : kind.value === 'buildings'
          ? { name: f.name, location: f.location, description: f.description }
          : {
              name: f.name,
              location: f.location,
              description: f.description,
              floorId: f.floorId,
              teamIds: f.teamIds,
              managerIds: f.managerIds,
              viewerIds: f.viewerIds,
              visibility: f.visibility,
            };
  if (await run(() => spaceApi.save(kind.value, editingId.value, body, data.value.revision)))
    dialog.value = false;
}
async function remove(k: Kind, id: string) {
  if (
    await confirm(
      `${labels[k]}을 삭제할까요? 사용 중인 하위 공간·인원·배치도가 있으면 삭제할 수 없습니다.`,
    )
  ) {
    if (await run(() => spaceApi.remove(k, id, data.value.revision), '삭제했습니다.')) {
      floorFilter.value = null;
      buildingFilter.value = null;
    }
  }
}
</script>

<style scoped>
.rooms-layout {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  align-items: start;
  gap: 20px;
}
.rooms-tree :deep(.q-item) {
  border-radius: 7px;
  min-height: 44px;
  padding: 8px 12px;
}
.rooms-tree :deep(.q-item__section--avatar) {
  min-width: 30px;
}
.rooms-tree :deep(.rooms-tree__floor) {
  margin-left: 28px;
}
.rooms-tree__active {
  background: var(--space-soft);
  color: var(--q-primary);
}
.rooms-team-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
@media (max-width: 1100px) {
  .rooms-layout {
    grid-template-columns: 210px minmax(0, 1fr);
    gap: 16px;
  }
}
@media (max-width: 850px) {
  .rooms-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
