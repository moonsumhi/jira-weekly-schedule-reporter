<template>
  <div class="space-panel space-room-picker">
    <div class="space-room-picker__label">
      <q-icon name="location_on" color="primary" size="20px" />공간 선택
    </div>
    <div class="space-room-picker__fields">
      <q-select
        :model-value="buildingId"
        :options="data.buildings.map((b) => ({ label: b.name, value: b.id }))"
        emit-value
        map-options
        outlined
        dense
        label="건물"
        :disable="!data.buildings.length"
        @update:model-value="setBuilding"
      />
      <q-icon name="chevron_right" class="space-muted" size="20px" />
      <q-select
        :model-value="floorId"
        :options="floors.map((f) => ({ label: f.name, value: f.id }))"
        emit-value
        map-options
        outlined
        dense
        label="층"
        :disable="!floors.length"
        @update:model-value="setFloor"
      />
      <q-icon name="chevron_right" class="space-muted" size="20px" />
      <q-select
        :model-value="modelValue"
        :options="rooms.map((r) => ({ label: r.name, value: r.id }))"
        emit-value
        map-options
        outlined
        dense
        label="사무실"
        :disable="!rooms.length"
        @update:model-value="(v) => $emit('update:modelValue', String(v))"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue';
import type { SpaceData } from 'src/services/spaces';
const props = defineProps<{ modelValue: string; data: SpaceData }>();
const emit = defineEmits<{ 'update:modelValue': [id: string] }>();
const emptyBuilding = ref(''),
  emptyFloor = ref('');
const selectedRoom = computed(() => props.data.rooms.find((r) => r.id === props.modelValue));
const floorId = computed(() => selectedRoom.value?.floorId ?? emptyFloor.value);
const buildingId = computed(
  () =>
    props.data.floors.find((f) => f.id === floorId.value)?.buildingId ?? emptyBuilding.value ?? '',
);
const floors = computed(() => props.data.floors.filter((f) => f.buildingId === buildingId.value));
const rooms = computed(() => props.data.rooms.filter((r) => r.floorId === floorId.value));
function setBuilding(id: string) {
  emptyBuilding.value = id;
  setFloor(props.data.floors.find((f) => f.buildingId === id)?.id ?? '');
}
function setFloor(id: string) {
  emptyFloor.value = id;
  emit('update:modelValue', props.data.rooms.find((r) => r.floorId === id)?.id ?? '');
}
</script>
