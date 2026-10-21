<template>
  <q-dialog :model-value="modelValue" :persistent="busy" @update:model-value="close">
    <q-card class="space-dialog seat-assignment" aria-labelledby="seat-assignment-title">
      <q-card-section class="seat-assignment__header">
        <q-avatar rounded color="blue-1" text-color="primary" icon="event_seat" />
        <div>
          <h2 id="seat-assignment-title">
            {{ seat?.number || '좌석' }} {{ occupant ? '좌석 정보' : '인원 배정' }}
          </h2>
          <div class="text-caption space-muted">
            {{ location }} · {{ team?.name || '팀 미지정' }}
          </div>
        </div>
        <q-space />
        <q-btn
          flat
          round
          dense
          icon="close"
          aria-label="좌석 배정 창 닫기"
          :disable="busy"
          @click="close(false)"
        />
      </q-card-section>
      <q-separator />
      <q-card-section>
        <q-banner v-if="error" rounded class="bg-red-1 text-negative q-mb-md" role="alert">
          {{ error }}
          <template #action
            ><q-btn flat label="최신 정보 불러오기" :disable="busy" @click="refreshSeat"
          /></template>
        </q-banner>
        <div v-if="!seat" class="space-hint">
          좌석을 찾을 수 없습니다. 배치도에서 다른 좌석을 선택해 주세요.
        </div>
        <template v-else>
          <template v-if="canConfigureTeam && !occupant">
            <q-select
              v-if="roomTeams.length > 1"
              v-model="selectedTeamId"
              :options="roomTeams.map((t) => ({ label: t.name, value: t.id }))"
              emit-value
              map-options
              outlined
              dense
              label="좌석 담당 팀"
              :disable="busy"
              class="q-mb-md"
            />
            <div v-if="assignmentTeamId" class="space-hint q-mb-md">
              <q-icon name="groups" size="20px" />
              <span
                >담당 팀이 비어 있는 좌석입니다. 인원을 배정하면 좌석 담당 팀도 {{ team?.name }}으로
                저장됩니다.</span
              >
            </div>
          </template>
          <div v-if="occupant" class="seat-assignment__occupant">
            <q-avatar color="blue-1" text-color="primary">{{ occupant.name.slice(0, 1) }}</q-avatar>
            <div>
              <div class="text-caption space-muted">현재 배정 인원</div>
              <strong>{{ occupant.name }}</strong>
              <div class="text-caption space-muted">{{ occupant.title || team?.name }}</div>
            </div>
            <q-space /><q-badge color="green-1" text-color="green-9" label="배정됨" />
          </div>
          <template v-if="canAssign && !occupant">
            <p class="q-mt-none q-mb-md">
              배정할 인원을 한 명 선택한 뒤 <strong>배정</strong>을 누르세요.
            </p>
            <q-input
              v-model="search"
              outlined
              dense
              autofocus
              clearable
              label="이름 또는 직책 검색"
              :disable="busy"
            >
              <template #prepend><q-icon name="search" /></template>
            </q-input>
            <div class="text-caption space-muted q-mt-sm q-mb-sm">
              {{ team?.name }} 소속 인원 {{ candidates.length }}명
            </div>
            <q-list
              v-if="candidates.length"
              bordered
              separator
              class="seat-assignment__people"
              role="group"
              aria-label="배정할 인원"
            >
              <q-item
                v-for="person in candidates"
                :key="person.id"
                tag="label"
                :active="personId === person.id"
                :disable="busy"
              >
                <q-item-section avatar
                  ><q-checkbox
                    :model-value="personId === person.id"
                    @update:model-value="
                      (checked: boolean) => (personId = checked ? person.id : null)
                    "
                    :aria-label="`${person.name} 선택`"
                    :disable="busy"
                /></q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium"
                    >{{ person.name
                    }}<span v-if="person.title" class="text-caption text-grey-7 q-ml-sm">{{
                      person.title
                    }}</span></q-item-label
                  >
                  <q-item-label caption>{{
                    currentSeat(person.id)
                      ? `현재 ${seatLabel(currentSeat(person.id))} · 선택 시 이 좌석으로 이동`
                      : '배정된 좌석 없음'
                  }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
            <div v-else class="seat-assignment__empty">
              <q-icon name="person_search" size="30px" />
              <div>
                {{ search ? '검색 결과가 없습니다.' : '이 팀에 등록된 활성 인원이 없습니다.' }}
              </div>
              <span class="text-caption space-muted">{{
                search
                  ? '다른 이름이나 직책으로 검색해 주세요.'
                  : '인원 현황에서 인원을 먼저 등록해 주세요.'
              }}</span>
              <q-btn
                v-if="!search"
                flat
                color="primary"
                label="인원 현황으로 이동"
                to="/spaces/people"
                @click="close(false)"
              />
            </div>
            <div v-if="previousSeat" class="space-hint q-mt-md">
              <q-icon name="swap_horiz" size="20px" />
              <span
                >{{ chosenPerson?.name }}님의 기존 {{ seatLabel(previousSeat) }} 배정이 해제되고 이
                좌석으로 이동합니다.</span
              >
            </div>
          </template>
          <p v-else-if="canAssign" class="text-caption space-muted q-mt-md q-mb-none">
            다른 인원을 배정하려면 현재 배정을 먼저 해제하세요. 이 인원의 자리를 옮기려면 이동할 빈
            좌석을 클릭하세요.
          </p>
          <div v-else class="space-hint q-mt-md">
            <q-icon name="lock_outline" size="20px" /><span>{{
              assignmentTeamId
                ? '인적자원 관리 메뉴 권한을 확인해 주세요.'
                : canConfigureTeam && roomTeams.length
                  ? '좌석을 사용할 팀을 선택하면 배정할 인원이 표시됩니다.'
                  : roomTeams.length
                    ? '좌석 담당 팀이 비어 있습니다. 담당 팀을 선택해 주세요.'
                    : '사무실에 등록된 사용 팀이 없습니다. 공간 관리에서 사용 팀을 먼저 등록해 주세요.'
            }}</span>
          </div>
        </template>
      </q-card-section>
      <q-separator />
      <q-card-actions align="right" class="space-dialog__actions">
        <q-btn
          flat
          :label="canAssign && !occupant ? '취소' : '닫기'"
          :disable="busy"
          @click="close(false)"
        />
        <q-btn
          v-if="canAssign && occupant"
          outline
          color="negative"
          icon="person_remove"
          label="배정 해제"
          :disable="needsRefresh"
          :loading="busy"
          @click="unassign"
        />
        <q-btn
          v-else-if="canAssign"
          unelevated
          color="primary"
          icon="person_add"
          :label="previousSeat ? '이 좌석으로 이동' : '배정'"
          :disable="!chosenPerson || needsRefresh"
          :loading="busy"
          @click="assign"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import { spaceApi, type Seat, type SpaceData } from 'src/services/spaces';
import { getErrorMessage } from 'src/utils/http/error';
const props = defineProps<{
  modelValue: boolean;
  seatId: string | null;
  data: SpaceData;
  refresh: () => Promise<void>;
}>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();
const $q = useQuasar();
const needsRefresh = ref(false);
const busy = ref(false),
  error = ref(''),
  search = ref<string | null>(''),
  personId = ref<string | null>(null);
let revision = 0;
const seat = computed(() => props.data.seats.find((s) => s.id === props.seatId));
const room = computed(() => props.data.rooms.find((r) => r.id === seat.value?.roomId));
const roomTeams = computed(() =>
  props.data.teams.filter((t) => room.value?.teamIds.includes(t.id)),
);
const selectedTeamId = ref<string | null>(null);
const canConfigureTeam = computed(
  () => !seat.value?.teamId && !!room.value && props.data.editableRoomIds.includes(room.value.id),
);
const assignmentTeamId = computed(
  () => seat.value?.teamId || (canConfigureTeam.value ? selectedTeamId.value : null),
);
const team = computed(() => props.data.teams.find((t) => t.id === assignmentTeamId.value));
const canAssign = computed(() => !!assignmentTeamId.value && props.data.canManage);
const occupant = computed(() =>
  props.data.people.find(
    (p) => p.id === props.data.assignments.find((a) => a.seatId === props.seatId)?.personId,
  ),
);
function seatLabel(value: Seat | undefined) {
  const room = props.data.rooms.find((r) => r.id === value?.roomId);
  const floor = props.data.floors.find((f) => f.id === room?.floorId);
  const building = props.data.buildings.find((b) => b.id === floor?.buildingId);
  return [building?.name, floor?.name, room?.name, value?.number].filter(Boolean).join(' / ');
}
const location = computed(() => seatLabel(seat.value));
function currentSeat(id: string) {
  return props.data.seats.find(
    (s) => s.id === props.data.assignments.find((a) => a.personId === id)?.seatId,
  );
}
const eligible = computed(() =>
  props.data.people.filter((p) => p.active && p.teamId === assignmentTeamId.value),
);
const candidates = computed(() =>
  eligible.value.filter((p) =>
    `${p.name} ${p.title}`.toLowerCase().includes((search.value || '').trim().toLowerCase()),
  ),
);
const chosenPerson = computed(() => eligible.value.find((p) => p.id === personId.value));
const previousSeat = computed(() => (personId.value ? currentSeat(personId.value) : undefined));
watch(
  () => [props.modelValue, props.seatId],
  () => {
    error.value = '';
    needsRefresh.value = false;
    search.value = '';
    personId.value = null;
    selectedTeamId.value = roomTeams.value.length === 1 ? roomTeams.value[0]!.id : null;
    revision = props.data.revision;
  },
  { immediate: true },
);
watch(selectedTeamId, () => {
  personId.value = null;
  search.value = '';
});
function close(value: boolean) {
  if (!busy.value) emit('update:modelValue', value);
}
function confirm(message: string, label: string): Promise<boolean> {
  return new Promise((resolve) => {
    $q.dialog({
      title: label,
      message,
      persistent: true,
      cancel: { label: '취소', flat: true },
      ok: { label, color: 'primary' },
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false));
  });
}
async function mutate(
  action: () => Promise<void>,
  success: string,
  confirmation?: string,
  confirmationLabel = '좌석 이동',
) {
  if (busy.value || needsRefresh.value) return;
  busy.value = true;
  error.value = '';
  let committed = false;
  try {
    if (confirmation && !(await confirm(confirmation, confirmationLabel))) return;
    await action();
    committed = true;
    await props.refresh();
    emit('update:modelValue', false);
    $q.notify({ type: 'positive', message: success });
  } catch (e) {
    needsRefresh.value = true;
    error.value = committed
      ? '처리는 완료됐지만 최신 좌석 정보를 불러오지 못했습니다. 최신 정보 불러오기를 눌러 확인해 주세요.'
      : getErrorMessage(e, '처리하지 못했습니다. 최신 정보를 불러온 뒤 다시 시도해 주세요.');
  } finally {
    busy.value = false;
  }
}
async function assign() {
  const target = seat.value,
    person = chosenPerson.value,
    expectedRevision = revision,
    teamId = target?.teamId ? undefined : assignmentTeamId.value || undefined;
  if (!target || !person || !canAssign.value || occupant.value) return;
  const previous = previousSeat.value;
  await mutate(
    () => spaceApi.assign(target.id, person.id, expectedRevision, teamId),
    `${person.name}님을 ${target.number} 좌석에 배정했습니다.`,
    previous
      ? `${person.name}님의 기존 ${seatLabel(previous)} 배정을 해제하고 ${target.number} 좌석으로 이동할까요?`
      : undefined,
  );
}
async function unassign() {
  const target = seat.value,
    expectedRevision = revision;
  if (!target || !occupant.value || !canAssign.value) return;
  await mutate(
    () => spaceApi.unassign(target.id, expectedRevision),
    `${target.number} 좌석 배정을 해제했습니다.`,
    `${target.number} 좌석의 ${occupant.value.name}님 배정을 해제할까요?`,
    '배정 해제',
  );
}
async function refreshSeat() {
  if (busy.value) return;
  busy.value = true;
  try {
    await props.refresh();
    await nextTick();
    needsRefresh.value = false;
    revision = props.data.revision;
    personId.value = null;
    if (!roomTeams.value.some((t) => t.id === selectedTeamId.value))
      selectedTeamId.value = roomTeams.value.length === 1 ? roomTeams.value[0]!.id : null;
    error.value = '';
  } catch (e) {
    error.value = getErrorMessage(e, '최신 정보를 불러오지 못했습니다.');
  } finally {
    busy.value = false;
  }
}
</script>
<style scoped>
.seat-assignment {
  width: 560px;
  max-width: 94vw;
}
.seat-assignment__header,
.seat-assignment__occupant {
  display: flex;
  align-items: center;
  gap: 12px;
}
.seat-assignment__header h2 {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
  margin: 0 0 4px;
}
.seat-assignment__occupant {
  padding: 16px;
  border-radius: 8px;
  background: var(--space-bg);
}
.seat-assignment__people {
  max-height: min(320px, 40vh);
  overflow-y: auto;
  border-radius: 8px;
}
.seat-assignment__people .q-item--active {
  background: var(--space-soft);
  color: var(--space-text);
}
.seat-assignment__empty {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 24px 8px;
  text-align: center;
}
</style>
