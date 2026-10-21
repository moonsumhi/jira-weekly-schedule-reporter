<template>
  <q-page class="spaces-page">
    <SpaceHeader
      :title="room ? `${room.name} 배치도` : '사무실 배치도'"
      eyebrow="인적자원 관리 · 공간 관리"
      :description="room ? roomName(roomId) : ''"
      :error="error || planError"
      :loading="loading || planLoading || busy"
      @reload="refresh"
    >
      <template #leading>
        <q-btn
          flat
          round
          icon="arrow_back"
          aria-label="뒤로가기"
          :disable="busy || planLoading"
          @click="goBack"
        >
          <q-tooltip>뒤로가기</q-tooltip>
        </q-btn>
      </template>
      <SpacePlanPdfButton
        v-if="room && plan.published && !editing"
        :room-id="roomId"
        :disabled="loading || planLoading || busy || !!error || !!planError"
      />
      <q-btn
        v-if="room"
        outline
        color="primary"
        icon="event_seat"
        label="좌석 목록"
        :to="{ path: '/spaces/seats', query: { room: roomId } }"
      />
    </SpaceHeader>
    <section v-if="!room && !loading && !error" class="space-panel">
      <SpaceEmpty
        icon="meeting_room"
        title="사무실을 찾을 수 없습니다"
        description="삭제되었거나 조회 권한이 없는 사무실입니다. 공간 관리에서 접근 가능한 사무실을 선택해 주세요."
        ><q-btn unelevated color="primary" label="공간 관리로 이동" to="/spaces/rooms"
      /></SpaceEmpty>
    </section>
    <template v-if="room">
      <div class="space-workspace-heading">
        <div class="space-room-stats">
          <span
            >전체<strong>{{ plan.seats.length }}</strong
            >석</span
          ><span
            >배정<strong>{{ occupied }}</strong
            >석</span
          ><span
            >미배정<strong>{{ plan.seats.length - occupied }}</strong
            >석</span
          >
        </div>
        <q-space />
        <q-select
          v-model="teamFilter"
          :options="roomTeams.map((t) => ({ label: t.name, value: t.id }))"
          emit-value
          map-options
          clearable
          outlined
          dense
          label="팀별 보기"
        />
      </div>
      <section class="space-panel plan-workspace">
        <div class="plan-room-teams">
          <div class="plan-room-teams__row">
            <strong>사무실 사용 팀</strong>
            <span v-for="team in roomTeams" :key="team.id" class="space-team-label">
              <span class="space-team-dot" :style="{ background: team.color }" />{{ team.name }}
            </span>
            <span v-if="!roomTeams.length" class="space-muted">등록된 팀이 없습니다</span>
            <q-space />
            <q-btn
              v-if="data.canManage"
              flat
              dense
              color="primary"
              icon="groups"
              label="사용 팀 설정"
              :disable="busy || planLoading"
              @click="openTeamSettings"
            />
          </div>
          <p v-if="editing">
            책상을 선택하고 오른쪽 <strong>좌석 담당 팀</strong>을 지정하세요. 팀 구역은 영역을
            색상으로 표시하는 용도입니다.
          </p>
        </div>
        <div class="plan-actions">
          <div class="plan-actions__status">
            <q-icon
              :name="editing ? 'edit_note' : 'visibility'"
              color="primary"
              size="22px"
            /><strong>{{ editing ? '배치도 편집' : '게시 배치도' }}</strong>
            <q-badge v-if="dirty" color="orange-1" text-color="orange-10" label="미저장 변경사항" />
            <q-badge
              v-else
              :color="editing && plan.hasDraft ? 'orange-1' : plan.published ? 'green-1' : 'grey-2'"
              :text-color="
                editing && plan.hasDraft ? 'orange-10' : plan.published ? 'green-9' : 'grey-8'
              "
              :label="editing && plan.hasDraft ? '임시저장' : plan.published ? '게시됨' : '미생성'"
            />
          </div>
          <div v-if="!planLoading && !planError" class="plan-actions__buttons">
            <q-btn
              v-if="data.editableRoomIds.length && plan.createdAt"
              flat
              color="grey-7"
              icon="content_copy"
              label="다른 사무실로 복제"
              :disable="dirty || busy"
              @click="cloneDialog = true"
            />
            <q-btn
              v-if="canEdit && data.plans.some((p) => p.roomId === roomId)"
              flat
              color="negative"
              icon="delete_outline"
              label="배치도 삭제"
              :disable="busy"
              @click="removePlan"
            />
            <q-btn
              v-if="canEdit && !editing"
              unelevated
              color="primary"
              icon="edit"
              :label="plan.published ? '배치도 편집' : '배치도 생성'"
              :disable="busy"
              @click="startEditing"
            />
            <q-btn
              v-if="editing"
              outline
              color="primary"
              icon="save"
              label="임시저장"
              :loading="busy"
              @click="save"
            />
            <q-btn
              v-if="editing"
              unelevated
              color="primary"
              icon="publish"
              label="게시"
              :disable="busy"
              :loading="busy"
              @click="publish"
            />
          </div>
        </div>
        <div v-if="editing" class="plan-edit-notice">
          <q-icon name="info_outline" size="18px" /><span
            >팀 지정과 좌석 배치를 마치고 게시하면, 좌석을 클릭해 인원을 배정할 수 있습니다. 나중에
            이어서 편집하려면 임시저장하세요.</span
          >
        </div>
        <q-skeleton v-if="planLoading" height="520px" square animation="fade" />
        <FloorPlanCanvas
          v-else-if="!planError && (editing || plan.published)"
          :key="`${roomId}-${editing}-${canvasKey}`"
          v-model="plan"
          :inert="busy"
          :editable="editing"
          :teams="roomTeams"
          :assignments="data.assignments"
          :people="data.people"
          :team-filter="teamFilter"
          :selected-seat-id="selectedSeatId"
          @select-seat="openSeat"
        />
        <SpaceEmpty
          v-else-if="!planError"
          icon="draw"
          title="아직 게시된 배치도가 없습니다"
          :description="
            canEdit
              ? '배치도 생성 버튼을 눌러 벽과 책상을 배치해 보세요. 저장한 편집본이 있으면 이어서 편집할 수 있습니다.'
              : '배치도를 만들고 게시하면 이곳에서 좌석을 확인할 수 있습니다.'
          "
        />
      </section>
      <div v-if="plan.createdAt" class="space-hint q-mt-sm">
        <q-icon name="schedule" size="16px" /><span
          >마지막 저장 {{ new Date(plan.createdAt).toLocaleString('ko-KR') }} ·
          {{ plan.createdBy }}</span
        >
      </div>
    </template>
    <q-dialog v-model="teamDialog" :persistent="busy">
      <q-card v-if="teamForm" class="space-dialog" style="width: 500px">
        <q-card-section class="space-dialog__header">
          <h2>{{ room?.name }} 사용 팀 설정</h2>
          <p>이 사무실을 함께 사용하는 팀을 선택하세요. 여러 팀을 등록할 수 있습니다.</p>
        </q-card-section>
        <q-card-section class="space-dialog__body">
          <q-list separator>
            <q-item v-for="team in data.teams" :key="team.id" tag="label">
              <q-item-section avatar>
                <q-checkbox
                  v-model="teamForm.teamIds"
                  :val="team.id"
                  :disable="
                    busy || (protectedTeamIds.has(team.id) && teamForm.teamIds.includes(team.id))
                  "
                  :aria-label="team.name"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label class="space-team-label"
                  ><span class="space-team-dot" :style="{ background: team.color }" />{{
                    team.name
                  }}</q-item-label
                >
                <q-item-label v-if="protectedTeamIds.has(team.id)" caption
                  >좌석·구역 또는 근무 인원이 연결되어 있습니다</q-item-label
                >
              </q-item-section>
            </q-item>
          </q-list>
          <p class="space-hint q-mt-md">
            새 팀 등록과 색상 변경은 공간 관리의 ‘팀 관리’에서 할 수 있습니다.
          </p>
        </q-card-section>
        <q-card-actions align="right" class="space-dialog__actions">
          <q-btn flat label="취소" v-close-popup :disable="busy" />
          <q-btn
            unelevated
            color="primary"
            label="사용 팀 저장"
            :loading="busy"
            @click="saveTeamSettings"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <q-dialog v-model="cloneDialog"
      ><q-card class="space-dialog" style="width: 500px">
        <q-card-section class="space-dialog__header"
          ><h2>다른 사무실로 복제</h2>
          <p>
            {{ data.rooms.find((r) => r.id === roomId)?.name }}의
            {{ editing ? '저장된 편집본' : '게시본' }}을 가져옵니다.
          </p></q-card-section
        >
        <q-card-section class="space-dialog__body"
          ><q-select
            v-model="targetRoom"
            :options="cloneTargets"
            emit-value
            map-options
            outlined
            label="대상 사무실"
          />
          <div class="space-hint q-mt-md">
            <q-icon name="info_outline" size="18px" />책상과 좌석번호는 복제되며, 인원 배정은
            제외됩니다.
          </div>
          <div v-if="!cloneTargets.length" class="space-muted q-mt-md">
            배치도가 없고 편집 권한이 있는 다른 사무실을 먼저 등록해 주세요.
          </div></q-card-section
        >
        <q-card-actions align="right" class="space-dialog__actions"
          ><q-btn flat label="취소" v-close-popup /><q-btn
            unelevated
            color="primary"
            label="복제"
            :disable="!targetRoom"
            :loading="busy"
            @click="clone"
        /></q-card-actions> </q-card
    ></q-dialog>
    <SeatAssignmentDialog
      v-model="assignmentOpen"
      :seat-id="selectedSeatId"
      :data="data"
      :refresh="refreshAssignments"
    />
  </q-page>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, toRaw, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router';
import SpaceEmpty from 'src/components/spaces/SpaceEmpty.vue';
import SpaceHeader from 'src/components/spaces/SpaceHeader.vue';
import SpacePlanPdfButton from 'src/components/spaces/SpacePlanPdfButton.vue';
import FloorPlanCanvas from 'src/components/spaces/FloorPlanCanvas.vue';
import SeatAssignmentDialog from 'src/components/spaces/SeatAssignmentDialog.vue';
import { blankPlan, spaceApi, type Room } from 'src/services/spaces';
import { getErrorMessage } from 'src/utils/http/error';
import { useSpaces } from './useSpaces';
const { data, loading, busy, error, reload, run, confirm, deletePlan, roomName } = useSpaces();
const route = useRoute(),
  router = useRouter();
const roomId = computed(() => (typeof route.params.roomId === 'string' ? route.params.roomId : ''));
const room = computed(() => data.value.rooms.find((r) => r.id === roomId.value));
const selectedSeatId = ref<string | null>(null),
  assignmentOpen = ref(false);
const editing = ref(false),
  plan = ref(blankPlan()),
  baseline = ref(''),
  planLoading = ref(false),
  planError = ref(''),
  canvasKey = ref(0);
const teamFilter = ref<string | null>(null),
  cloneDialog = ref(false),
  targetRoom = ref<string | null>(null);
const canEdit = computed(() => data.value.editableRoomIds.includes(roomId.value));
const roomTeams = computed(() =>
  data.value.teams.filter((t) => room.value?.teamIds.includes(t.id)),
);
const teamDialog = ref(false);
const teamForm = ref<Room | null>(null);
let teamRevision = 0;
const protectedTeamIds = computed(
  () =>
    new Set(
      [
        ...plan.value.seats.map((s) => s.teamId),
        ...plan.value.objects.map((o) => o.teamId),
        ...data.value.seats.filter((s) => s.roomId === roomId.value).map((s) => s.teamId),
        ...data.value.people
          .filter((p) => p.roomId === roomId.value && p.active)
          .map((p) => p.teamId),
      ].filter((id): id is string => !!id),
    ),
);
function openTeamSettings() {
  if (!data.value.canManage || !room.value || busy.value) return;
  teamForm.value = structuredClone(toRaw(room.value));
  teamRevision = data.value.revision;
  teamDialog.value = true;
}
async function saveTeamSettings() {
  if (!teamForm.value || !data.value.canManage) return;
  const f = teamForm.value;
  const body = {
    name: f.name,
    floorId: f.floorId,
    location: f.location,
    description: f.description,
    teamIds: f.teamIds,
    managerIds: f.managerIds,
    viewerIds: f.viewerIds,
    visibility: f.visibility,
  };
  if (
    await run(
      () => spaceApi.save('rooms', f.id, body, teamRevision),
      '사무실의 사용 팀을 변경했습니다.',
    )
  ) {
    teamDialog.value = false;
    if (teamFilter.value && !body.teamIds.includes(teamFilter.value)) teamFilter.value = null;
  }
}
const signature = computed(() =>
  JSON.stringify({
    width: plan.value.width,
    height: plan.value.height,
    objects: plan.value.objects,
    seats: plan.value.seats,
  }),
);
const dirty = computed(
  () => editing.value && !!baseline.value && signature.value !== baseline.value,
);
const occupied = computed(
  () =>
    plan.value.seats.filter((s) => data.value.assignments.some((a) => a.seatId === s.id)).length,
);
const cloneTargets = computed(() =>
  data.value.rooms
    .filter(
      (r) =>
        r.id !== roomId.value &&
        data.value.editableRoomIds.includes(r.id) &&
        !data.value.plans.some((p) => p.roomId === r.id),
    )
    .map((r) => ({ label: roomName(r.id), value: r.id })),
);
let requestId = 0;
async function loadPlan() {
  const request = ++requestId;
  planLoading.value = true;
  planError.value = '';
  try {
    const result = await spaceApi.plan(roomId.value, editing.value);
    if (request !== requestId) return;
    plan.value = result;
    baseline.value = signature.value;
    canvasKey.value++;
  } catch (e) {
    if (request === requestId)
      planError.value = getErrorMessage(e, '배치도를 불러오지 못했습니다.');
  } finally {
    if (request === requestId) planLoading.value = false;
  }
}
watch(
  [roomId, () => !!room.value],
  () => {
    editing.value = route.query.edit === '1' && canEdit.value;
    teamFilter.value = null;
    teamDialog.value = false;
    assignmentOpen.value = false;
    selectedSeatId.value = null;
    targetRoom.value = null;
    plan.value = blankPlan();
    baseline.value = '';
    if (room.value) void loadPlan();
    else {
      requestId++;
      planError.value = '';
      planLoading.value = false;
    }
  },
  { immediate: true },
);
async function mayDiscard() {
  if (busy.value) return false;
  return (
    !dirty.value ||
    (await confirm('저장하지 않은 변경사항이 있습니다. 변경사항을 버리고 이동할까요?'))
  );
}
async function startEditing() {
  if (busy.value || !canEdit.value) return;
  assignmentOpen.value = false;
  selectedSeatId.value = null;
  editing.value = true;
  await loadPlan();
}
async function goBack() {
  if (busy.value || planLoading.value) return;
  if (editing.value) {
    if (!(await mayDiscard())) return;
    await finishEditing();
    return;
  }
  await router.push('/spaces/rooms');
}
async function finishEditing() {
  planLoading.value = true;
  editing.value = false;
  assignmentOpen.value = false;
  selectedSeatId.value = null;
  teamFilter.value = null;
  // Do not reopen the editor on refresh after publishing a newly created plan.
  const query = { ...route.query };
  delete query.edit;
  await router.replace({ query });
  await loadPlan();
}
async function refreshAssignments() {
  const target = roomId.value;
  await reload();
  if (error.value) throw new Error(error.value);
  const result = await spaceApi.plan(target);
  if (target === roomId.value && !editing.value) plan.value = result;
}
async function refresh() {
  if (!(await mayDiscard())) return;
  await reload();
  if (room.value) await loadPlan();
}
async function removePlan() {
  if (busy.value || planLoading.value || !canEdit.value) return;
  if (await deletePlan(roomId.value, plan.value.version, dirty.value)) await finishEditing();
}
async function save() {
  if (
    await run(
      () => spaceApi.savePlan(roomId.value, plan.value),
      '임시저장했습니다. 게시 전까지 일반 사용자에게 공개되지 않습니다.',
    )
  )
    await loadPlan();
}
async function publish() {
  if (busy.value || planLoading.value || !editing.value) return;
  if (
    !(await confirm('현재 편집 내용을 저장하고 게시할까요? 기존 게시본이 새 배치도로 교체됩니다.'))
  )
    return;
  const target = roomId.value;
  let saved = false;
  const published = await run(async () => {
    const result = await spaceApi.savePlan(target, plan.value);
    // Keep the saved revision if publishing fails so the draft can be retried.
    plan.value.version = result.version;
    plan.value.hasDraft = true;
    baseline.value = signature.value;
    saved = true;
    try {
      await spaceApi.publish(target, result.version);
    } catch (e) {
      throw new Error(
        `임시저장은 완료됐지만 게시하지 못했습니다. ${getErrorMessage(e, '다시 시도해 주세요.')}`,
      );
    }
  }, '현재 편집 내용을 저장하고 게시했습니다.');
  if (published) await finishEditing();
  else if (saved) await reload();
}
async function clone() {
  const target = targetRoom.value;
  if (!target) return;
  if (
    await run(
      () =>
        spaceApi.clone(
          roomId.value,
          target,
          plan.value.version,
          editing.value ? 'draft' : 'published',
        ),
      '대상 사무실에 임시 배치도를 만들었습니다.',
    )
  ) {
    cloneDialog.value = false;
    await router.push({
      name: 'space-room-plan',
      params: { roomId: target },
      query: { edit: '1' },
    });
  }
}
function openSeat(id: string) {
  if (editing.value || busy.value || !plan.value.published) return;
  selectedSeatId.value = id;
  assignmentOpen.value = true;
}
function unload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = '';
  }
}
window.addEventListener('beforeunload', unload);
onBeforeUnmount(() => {
  requestId++;
  window.removeEventListener('beforeunload', unload);
});
onBeforeRouteLeave(mayDiscard);
onBeforeRouteUpdate(async (to) => {
  if (to.params.roomId !== roomId.value) return mayDiscard();
});
</script>

<style scoped>
.plan-room-teams {
  padding: 12px 18px;
  border-bottom: 1px solid var(--space-line);
}
.plan-room-teams__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.plan-room-teams p {
  margin: 8px 0 0;
  color: var(--space-muted);
  font-size: 12px;
  line-height: 1.7;
}
.plan-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  gap: 12px;
  border-bottom: 1px solid var(--space-line);
}
.plan-actions__status,
.plan-actions__buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.plan-edit-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--space-soft);
  color: var(--q-primary);
  font-size: 12px;
  line-height: 1.7;
}
.plan-workspace :deep(.floor-plan) {
  border: 0;
  border-radius: 0;
}
@media (max-width: 700px) {
  .space-room-stats {
    width: 100%;
    order: 3;
  }
  .plan-actions__buttons {
    gap: 6px;
  }
}
</style>
