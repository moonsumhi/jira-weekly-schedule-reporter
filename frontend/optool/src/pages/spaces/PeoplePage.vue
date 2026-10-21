<template>
  <q-page class="spaces-page">
    <SpaceHeader
      title="인원 현황"
      description="팀별 인원과 근무 공간, 배정된 좌석을 한곳에서 확인하세요."
      :error="error"
      :loading="loading"
      @reload="reload"
    >
      <q-btn
        v-if="data.canManage && data.teams.length"
        unelevated
        color="primary"
        icon="person_add"
        label="인원 등록"
        @click="edit()"
      />
    </SpaceHeader>
    <SpaceSummary
      :items="[
        { label: '활성 인원', value: activePeople.length, unit: '명', icon: 'groups' },
        { label: '좌석 배정', value: assignedCount, unit: '명', icon: 'how_to_reg', tone: 'green' },
        {
          label: '좌석 미배정',
          value: activePeople.length - assignedCount,
          unit: '명',
          icon: 'person_search',
          tone: 'slate',
        },
      ]"
    />
    <section class="space-panel">
      <div class="space-panel__heading">
        <h2>인원 목록</h2>
        <q-badge color="blue-1" text-color="primary" role="status" aria-live="polite"
          >{{ hasFilters ? '검색 결과' : '전체' }} {{ rows.length }}명</q-badge
        ><q-space /><q-toggle v-model="showInactive" dense label="비활성 포함" />
      </div>
      <div class="people-filters" role="group" aria-label="인원 검색 및 필터">
        <div class="people-filter-toolbar">
          <q-input
            v-model="search"
            outlined
            dense
            clearable
            placeholder="이름 검색"
            aria-label="이름 검색"
            bg-color="white"
            class="people-search"
            ><template #prepend><q-icon name="search" size="18px" color="grey-5" /></template
          ></q-input>
          <div class="row items-center no-wrap q-gutter-xs">
            <q-btn
              flat
              dense
              size="sm"
              icon="tune"
              label="상세 필터"
              :class="detailFiltersExpanded ? 'text-indigo-7' : 'text-grey-6'"
              no-caps
              class="q-px-xs"
              :aria-expanded="detailFiltersExpanded"
              aria-controls="people-detail-filters"
              @click="detailFiltersExpanded = !detailFiltersExpanded"
            >
              <q-badge
                v-if="detailFilterCount"
                color="indigo-7"
                :label="detailFilterCount"
                class="q-ml-xs"
              />
            </q-btn>
            <q-btn
              flat
              dense
              size="sm"
              color="grey-6"
              icon="refresh"
              label="초기화"
              no-caps
              @click="resetFilters"
            />
          </div>
        </div>
        <q-slide-transition>
          <div v-if="hasFilters" class="people-active-filters" aria-label="적용된 필터">
            <q-chip
              v-for="filter in activeFilters"
              :key="filter.key"
              dense
              removable
              size="sm"
              color="indigo-1"
              text-color="indigo-9"
              :aria-label="`${filter.label}${filter.value ? `: ${filter.value}` : ''} 필터 해제`"
              @remove="clearFilter(filter.key)"
            >
              <span class="text-weight-medium text-caption">{{ filter.label }}</span>
              <span v-if="filter.value" class="people-filter-value ellipsis q-ml-xs">{{
                filter.value
              }}</span>
              <q-tooltip>{{ filter.label }} {{ filter.value }}</q-tooltip>
            </q-chip>
          </div>
        </q-slide-transition>
        <q-slide-transition>
          <div
            id="people-detail-filters"
            v-show="detailFiltersExpanded"
            class="people-detail-filters"
          >
            <q-separator class="q-mb-md" />
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-sm-6 col-md-4">
                <q-select
                  v-model="teamFilter"
                  :options="teamOptions"
                  emit-value
                  map-options
                  clearable
                  outlined
                  dense
                  options-dense
                  bg-color="white"
                  label="소속 팀"
                >
                  <template #prepend><q-icon name="groups" size="16px" color="grey-5" /></template>
                </q-select>
              </div>
              <div class="col-12 col-sm-6 col-md-4">
                <q-select
                  v-model="titleFilter"
                  :options="titleOptions"
                  emit-value
                  map-options
                  clearable
                  outlined
                  dense
                  options-dense
                  bg-color="white"
                  label="직책"
                >
                  <template #prepend><q-icon name="badge" size="16px" color="grey-5" /></template>
                  <template #no-option>
                    <q-item>
                      <q-item-section class="space-muted">등록된 직책이 없습니다.</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-sm-6 col-md-4">
                <q-select
                  v-model="roomFilter"
                  :options="roomOptions"
                  emit-value
                  map-options
                  clearable
                  outlined
                  dense
                  options-dense
                  bg-color="white"
                  label="근무 사무실"
                >
                  <template #prepend
                    ><q-icon name="meeting_room" size="16px" color="grey-5"
                  /></template>
                </q-select>
              </div>
            </div>
          </div>
        </q-slide-transition>
      </div>
      <q-table
        flat
        class="space-table"
        :rows="rows"
        :columns="columns"
        row-key="id"
        :loading="loading"
        v-model:pagination="pagination"
        :rows-per-page-options="[20, 50, 100]"
        rows-per-page-label="페이지당 인원"
      >
        <template #body-cell-name="p"
          ><q-td :props="p"
            ><div class="space-person">
              <q-avatar size="34px">{{ p.row.name.slice(0, 1) }}</q-avatar
              ><strong>{{ p.row.name }}</strong>
            </div></q-td
          ></template
        >
        <template #body-cell-team="p"
          ><q-td :props="p"
            ><span class="space-team-label"
              ><span
                class="space-team-dot"
                :style="{ background: data.teams.find((t) => t.id === p.row.teamId)?.color }"
              />{{ teamName(p.row.teamId) }}</span
            ></q-td
          ></template
        >
        <template #body-cell-title="p"
          ><q-td :props="p"
            ><span :class="{ 'space-muted': !p.row.title?.trim() }">{{
              p.row.title?.trim() || '미지정'
            }}</span></q-td
          ></template
        >
        <template #body-cell-room="p"
          ><q-td :props="p">{{
            roomName(personSeat(p.row.id)?.roomId || p.row.roomId)
          }}</q-td></template
        >
        <template #body-cell-seat="p"
          ><q-td :props="p"
            ><q-btn
              v-if="personSeat(p.row.id)"
              flat
              dense
              color="primary"
              icon="event_seat"
              :label="personSeat(p.row.id)?.number"
              :to="{
                path: '/spaces/seats',
                query: { room: personSeat(p.row.id)?.roomId, person: p.row.id },
              }"
              ><q-tooltip>배치도에서 좌석 확인</q-tooltip></q-btn
            ><span v-else class="space-muted">미배정</span></q-td
          ></template
        >
        <template #body-cell-active="p"
          ><q-td :props="p"
            ><q-badge
              :color="p.row.active ? 'green-1' : 'grey-3'"
              :text-color="p.row.active ? 'green-9' : 'grey-8'"
              :label="p.row.active ? '활성' : '비활성'" /></q-td
        ></template>
        <template #body-cell-actions="p"
          ><q-td :props="p"
            ><div v-if="data.canManage" class="people-row-actions">
              <q-btn
                flat
                dense
                color="grey-7"
                icon="edit"
                label="수정"
                :disable="busy"
                @click="edit(p.row)"
              />
              <q-btn
                flat
                dense
                color="negative"
                icon="delete_outline"
                label="삭제"
                :aria-label="`${p.row.name} 삭제`"
                :disable="busy"
                :loading="deletingId === p.row.id"
                @click="remove(p.row)"
              /></div></q-td
        ></template>
        <template #no-data
          ><SpaceEmpty
            :icon="data.people.length ? 'search_off' : 'people_outline'"
            :title="data.people.length ? '검색 결과가 없습니다' : '등록된 인원이 없습니다'"
            :description="
              data.people.length
                ? '검색어나 필터를 변경해 다시 찾아보세요.'
                : '인원을 등록하고 소속 팀과 근무 공간을 지정해 보세요.'
            "
            ><q-btn
              v-if="data.people.length"
              flat
              color="primary"
              label="필터 초기화"
              @click="resetFilters" /><q-btn
              v-else-if="data.canManage && data.teams.length"
              unelevated
              color="primary"
              icon="add"
              label="첫 인원 등록"
              @click="edit()" /></SpaceEmpty
        ></template>
      </q-table>
    </section>
    <q-dialog v-model="dialog" persistent>
      <q-card class="space-dialog"
        ><q-form @submit="save">
          <q-card-section class="space-dialog__header"
            ><div class="row items-center">
              <h2>{{ editingId ? '인원 수정' : '인원 등록' }}</h2>
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
            <p>기본 정보를 입력하세요. * 표시는 필수 항목입니다.</p></q-card-section
          >
          <q-card-section class="space-dialog__body">
            <section class="space-form-section">
              <h3>기본 정보</h3>
              <div class="space-form-grid">
                <q-input
                  v-model="form.name"
                  outlined
                  dense
                  label="이름 *"
                  maxlength="100"
                  :rules="[required]"
                  hide-bottom-space
                />
                <q-select
                  v-model="form.teamId"
                  :options="teamOptions"
                  emit-value
                  map-options
                  outlined
                  dense
                  label="소속 팀 *"
                  :rules="[required]"
                  hide-bottom-space
                  @update:model-value="form.roomId = null"
                />
                <q-input v-model="form.title" outlined dense label="직책" maxlength="100" />
                <q-select
                  v-model="form.roomId"
                  :options="
                    roomOptions.filter((r) =>
                      data.rooms.find((x) => x.id === r.value)?.teamIds.includes(form.teamId),
                    )
                  "
                  emit-value
                  map-options
                  clearable
                  outlined
                  dense
                  label="근무 공간"
                />
              </div>
            </section>
            <section class="space-form-section">
              <h3>계정 연결 <span class="space-muted text-weight-regular">· 선택</span></h3>
              <q-select
                v-model="form.userId"
                :options="accountOptions"
                emit-value
                map-options
                clearable
                outlined
                dense
                label="로그인 계정"
                hint="계정 연결 없이도 인원을 등록할 수 있습니다."
                @update:model-value="linkAccount"
              />
            </section>
            <section class="space-form-section">
              <div class="row items-center justify-between">
                <div>
                  <h3 class="q-mb-xs">활성 상태</h3>
                  <div class="space-muted text-caption">현재 근무 중인 인원으로 관리합니다.</div>
                </div>
                <q-toggle v-model="form.active" label="활성 인원" />
              </div>
              <q-banner v-if="!form.active" rounded dense class="bg-orange-1 text-orange-10 q-mt-md"
                ><template #avatar><q-icon name="info_outline" /></template>비활성화하면 현재 좌석
                배정도 해제됩니다.</q-banner
              >
            </section>
          </q-card-section>
          <q-card-actions align="right" class="space-dialog__actions"
            ><q-btn flat label="취소" :disable="busy" v-close-popup /><q-btn
              unelevated
              color="primary"
              type="submit"
              :label="editingId ? '변경사항 저장' : '등록'"
              :loading="busy"
          /></q-card-actions> </q-form
      ></q-card>
    </q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { QTableColumn } from 'quasar';
import SpaceSummary from 'src/components/spaces/SpaceSummary.vue';
import SpaceEmpty from 'src/components/spaces/SpaceEmpty.vue';
import SpaceHeader from 'src/components/spaces/SpaceHeader.vue';
import { spaceApi, type Person } from 'src/services/spaces';
import { useSpaces } from './useSpaces';
const {
  data,
  loading,
  busy,
  error,
  reload,
  run,
  confirm,
  teamOptions,
  accountOptions,
  roomOptions,
  teamName,
  roomName,
} = useSpaces();
const search = ref(''),
  teamFilter = ref<string | null>(null),
  titleFilter = ref<string | null>(null),
  roomFilter = ref<string | null>(null),
  showInactive = ref(false);
const pagination = ref({ page: 1, rowsPerPage: 20 });
const detailFiltersExpanded = ref(false);
const detailFilterCount = computed(
  () =>
    Number(!!teamFilter.value) + Number(titleFilter.value !== null) + Number(!!roomFilter.value),
);
const titleOptions = computed(() => {
  const titles = new Set(data.value.people.map((p) => (p.title || '').trim()));
  const options = [...titles]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, 'ko'))
    .map((title) => ({ label: title, value: title }));
  if (titles.has('')) options.push({ label: '미지정', value: '' });
  return options;
});
type FilterKey = 'search' | 'team' | 'title' | 'room' | 'inactive';
const activeFilters = computed(() => {
  const filters: { key: FilterKey; label: string; value?: string }[] = [];
  if (search.value?.trim())
    filters.push({ key: 'search', label: '이름', value: search.value.trim() });
  if (teamFilter.value)
    filters.push({ key: 'team', label: '팀', value: teamName(teamFilter.value) });
  if (titleFilter.value !== null)
    filters.push({ key: 'title', label: '직책', value: titleFilter.value || '미지정' });
  if (roomFilter.value)
    filters.push({ key: 'room', label: '사무실', value: roomName(roomFilter.value) });
  if (showInactive.value) filters.push({ key: 'inactive', label: '비활성 포함' });
  return filters;
});
const hasFilters = computed(() => activeFilters.value.length > 0);
function clearFilter(key: FilterKey) {
  if (key === 'search') search.value = '';
  else if (key === 'team') teamFilter.value = null;
  else if (key === 'title') titleFilter.value = null;
  else if (key === 'room') roomFilter.value = null;
  else showInactive.value = false;
}
watch([search, teamFilter, titleFilter, roomFilter, showInactive], () => {
  pagination.value.page = 1;
});
const dialog = ref(false),
  editingId = ref<string | null>(null),
  deletingId = ref<string | null>(null);
const empty = () => ({
  name: '',
  teamId: '',
  title: '',
  roomId: null as string | null,
  userId: null as string | null,
  active: true,
});
const form = ref(empty());
const required = (value: unknown) => !!value || '필수 항목입니다.';
const activePeople = computed(() => data.value.people.filter((p) => p.active));
const assignedCount = computed(() => activePeople.value.filter((p) => personSeat(p.id)).length);
function personSeat(id: string) {
  const a = data.value.assignments.find((a) => a.personId === id);
  return data.value.seats.find((s) => s.id === a?.seatId);
}
const matchingPeople = computed(() =>
  data.value.people.filter(
    (p) =>
      (showInactive.value || p.active) &&
      p.name.toLowerCase().includes((search.value || '').trim().toLowerCase()) &&
      (titleFilter.value === null || (p.title || '').trim() === titleFilter.value) &&
      (!roomFilter.value ||
        p.roomId === roomFilter.value ||
        personSeat(p.id)?.roomId === roomFilter.value),
  ),
);
const rows = computed(() =>
  matchingPeople.value.filter((p) => !teamFilter.value || p.teamId === teamFilter.value),
);
const columns: QTableColumn<Person>[] = [
  { name: 'name', label: '이름', field: 'name', align: 'left', sortable: true },
  { name: 'team', label: '소속 팀', field: 'teamId', align: 'left' },
  { name: 'title', label: '직책', field: 'title', align: 'left' },
  { name: 'room', label: '근무 공간', field: 'roomId', align: 'left' },
  { name: 'seat', label: '배정 좌석', field: 'id', align: 'left' },
  { name: 'active', label: '상태', field: 'active', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];
function resetFilters() {
  search.value = '';
  teamFilter.value = null;
  titleFilter.value = null;
  roomFilter.value = null;
  showInactive.value = false;
}
async function remove(person: Person) {
  if (busy.value || !data.value.canManage) return;
  const revision = data.value.revision;
  const seat = personSeat(person.id);
  const message = `'${person.name}' (${teamName(person.teamId)}) 인원 정보를 삭제할까요?${
    seat
      ? ` 현재 배정된 ${roomName(seat.roomId)} / ${seat.number} 좌석 배정도 함께 해제됩니다.`
      : ''
  }${person.userId ? ' 연결된 로그인 계정은 유지됩니다.' : ''}`;
  if (!(await confirm(message, { title: '인원 삭제', label: '삭제', color: 'negative' }))) return;
  deletingId.value = person.id;
  try {
    if (
      await run(
        () => spaceApi.remove('people', person.id, revision),
        `${person.name}님의 인원 정보를 삭제했습니다.`,
      )
    ) {
      const lastPage = Math.max(1, Math.ceil(rows.value.length / pagination.value.rowsPerPage));
      pagination.value.page = Math.min(pagination.value.page, lastPage);
    }
  } finally {
    deletingId.value = null;
  }
}
function edit(person?: Person) {
  editingId.value = person?.id ?? null;
  form.value = person
    ? {
        name: person.name,
        teamId: person.teamId,
        title: person.title,
        roomId: person.roomId,
        userId: person.userId,
        active: person.active,
      }
    : { ...empty(), teamId: data.value.teams[0]?.id ?? '' };
  dialog.value = true;
}
function linkAccount(id: string | null) {
  const a = data.value.accounts.find((a) => a.id === id);
  if (!a) return;
  form.value.name = a.name;
  const team = data.value.teams.find((t) => t.name === a.team);
  if (team) form.value.teamId = team.id;
}
async function save() {
  if (
    !form.value.active &&
    editingId.value &&
    personSeat(editingId.value) &&
    !(await confirm('인원을 비활성화하고 현재 좌석 배정을 해제할까요?'))
  )
    return;
  if (await run(() => spaceApi.save('people', editingId.value, form.value, data.value.revision)))
    dialog.value = false;
}
</script>

<style scoped>
.people-row-actions {
  display: inline-flex;
  gap: 4px;
  white-space: nowrap;
}
.people-filters {
  padding: 16px 20px;
}
.people-filter-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.people-search {
  flex: 1;
  min-width: 220px;
}
.people-active-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
}
.people-active-filters .q-chip {
  max-width: min(320px, 100%);
  margin: 0;
}
.people-filter-value {
  opacity: 0.65;
}
.people-detail-filters {
  padding-top: 16px;
}
@media (max-width: 600px) {
  .people-search {
    flex-basis: 100%;
    min-width: 0;
  }
}
</style>
