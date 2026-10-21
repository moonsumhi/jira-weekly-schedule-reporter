import { computed, onMounted, ref } from 'vue';
import { useQuasar } from 'quasar';
import { blankData, spaceApi } from 'src/services/spaces';
import { getErrorMessage } from 'src/utils/http/error';

export function useSpaces() {
  const $q = useQuasar();
  const data = ref(blankData());
  const loading = ref(false);
  const busy = ref(false);
  const error = ref('');
  async function reload() {
    loading.value = true;
    error.value = '';
    try {
      data.value = await spaceApi.snapshot();
    } catch (e) {
      error.value = getErrorMessage(e, '공간 정보를 불러오지 못했습니다.');
    } finally {
      loading.value = false;
    }
  }
  async function run(action: () => Promise<unknown>, message = '저장했습니다.') {
    if (busy.value) return false;
    busy.value = true;
    try {
      await action();
      await reload();
      $q.notify({ type: 'positive', message });
      return true;
    } catch (e) {
      $q.notify({ type: 'negative', message: getErrorMessage(e, '처리하지 못했습니다.') });
      return false;
    } finally {
      busy.value = false;
    }
  }
  function confirm(
    message: string,
    options: { title?: string; label?: string; color?: string } = {},
  ): Promise<boolean> {
    return new Promise((resolve) => {
      $q.dialog({
        title: options.title || '확인',
        message,
        cancel: { label: '취소', flat: true },
        ok: { label: options.label || '확인', color: options.color || 'primary' },
        persistent: true,
      })
        .onOk(() => resolve(true))
        .onCancel(() => resolve(false))
        .onDismiss(() => resolve(false));
    });
  }
  async function deletePlan(roomId: string, version: number, unsaved = false) {
    if (busy.value) return false;
    const room = data.value.rooms.find((r) => r.id === roomId);
    if (!room || !data.value.editableRoomIds.includes(roomId)) return false;
    const revision = data.value.revision;
    const seatIds = new Set(data.value.seats.filter((s) => s.roomId === roomId).map((s) => s.id));
    const assigned = data.value.assignments.filter((a) => seatIds.has(a.seatId)).length;
    const message = assigned
      ? `'${room.name}'에 배정된 ${assigned}명의 좌석 배정을 모두 해제하고 배치도를 삭제할까요?`
      : `'${room.name}'의 배치도를 삭제할까요?`;
    if (
      !(await confirm(
        `${message} 게시본·임시저장본과 모든 좌석이 함께 삭제됩니다.${unsaved ? ' 저장하지 않은 편집 내용도 사라집니다.' : ''} 사무실과 인원 정보는 유지됩니다.`,
        {
          title: '배치도 삭제',
          label: assigned ? '배정 해제 후 삭제' : '배치도 삭제',
          color: 'negative',
        },
      ))
    )
      return false;
    return run(
      () => spaceApi.removePlan(roomId, version, assigned > 0, revision),
      assigned
        ? `${assigned}명의 좌석 배정을 해제하고 배치도를 삭제했습니다.`
        : '배치도를 삭제했습니다.',
    );
  }
  const teamOptions = computed(() => data.value.teams.map((t) => ({ label: t.name, value: t.id })));
  const accountOptions = computed(() =>
    data.value.accounts.map((a) => ({ label: `${a.name} (${a.email})`, value: a.id })),
  );
  function teamName(id: string | null) {
    return data.value.teams.find((t) => t.id === id)?.name ?? '미지정';
  }
  function roomName(id: string | null | undefined) {
    const room = data.value.rooms.find((r) => r.id === id);
    const floor = data.value.floors.find((f) => f.id === room?.floorId);
    const building = data.value.buildings.find((b) => b.id === floor?.buildingId);
    return room ? `${building?.name ?? ''} / ${floor?.name ?? ''} / ${room.name}` : '미지정';
  }
  const roomOptions = computed(() =>
    data.value.rooms.map((r) => ({ label: roomName(r.id), value: r.id })),
  );
  onMounted(() => {
    void reload();
  });
  return {
    data,
    loading,
    busy,
    error,
    reload,
    run,
    confirm,
    deletePlan,
    teamOptions,
    accountOptions,
    roomOptions,
    teamName,
    roomName,
  };
}
