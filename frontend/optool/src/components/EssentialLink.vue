<template>
  <!-- If has children -> render as expansion -->
  <q-expansion-item
    v-if="children && children.length"
    :icon="icon"
    :label="title"
    expand-separator
  >
    <EssentialLink
      v-for="child in children"
      :key="child.title"
      v-bind="child"
      @select="$emit('select', $event)"
    />
  </q-expansion-item>

  <!-- If no children -> render as clickable item -->
  <q-item v-else clickable :to="link" @click="$emit('select', link)">
    <q-item-section v-if="icon" avatar>
      <q-icon :name="icon" />
    </q-item-section>

    <q-item-section>
      <q-item-label>{{ title }}</q-item-label>
      <q-item-label caption>{{ caption }}</q-item-label>
    </q-item-section>
  </q-item>
</template>

<script setup lang="ts">
export interface EssentialLinkProps {
  title: string;
  caption?: string;
  link?: string;
  icon?: string;
  children?: EssentialLinkProps[];
}

withDefaults(defineProps<EssentialLinkProps>(), {
  caption: '',
  link: '#',
  icon: '',
  children: () => [],
});
</script>
