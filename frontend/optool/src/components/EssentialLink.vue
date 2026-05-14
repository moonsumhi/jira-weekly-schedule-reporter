<template>
  <!-- If has children -> render as expansion -->
  <q-expansion-item
    v-if="children && children.length"
    :icon="icon"
    :label="title"
    expand-separator
  >
    <template #header>
      <q-item-section avatar>
        <q-icon :name="icon" />
      </q-item-section>
      <q-item-section>{{ title }}</q-item-section>
      <q-item-section side v-if="badge && badge > 0">
        <q-badge color="negative" :label="badge" rounded />
      </q-item-section>
    </template>
    <EssentialLink
      v-for="child in children"
      :key="(child.link ?? child.title) + (child.icon ?? '')"
      v-bind="child"
      :isChild="true"
      @select="$emit('select', $event)"
    />
  </q-expansion-item>

  <!-- If no children -> render as clickable item -->
  <q-item
    v-else
    clickable
    :active="isActive"
    active-color="primary"
    @click="navigate"
    :class="{ 'child-item': isChild }"
  >
    <q-item-section avatar>
      <q-icon :name="icon || 'fiber_manual_record'" :size="icon ? 'sm' : 'xs'" />
    </q-item-section>

    <q-item-section>
      <q-item-label>{{ title }}</q-item-label>
      <q-item-label caption>{{ caption }}</q-item-label>
    </q-item-section>

    <q-item-section side v-if="badge && badge > 0">
      <q-badge color="negative" :label="badge" rounded />
    </q-item-section>
  </q-item>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export interface EssentialLinkProps {
  title: string;
  caption?: string;
  link?: string;
  icon?: string;
  children?: EssentialLinkProps[];
  isChild?: boolean;
  badge?: number;
}

const props = withDefaults(defineProps<EssentialLinkProps>(), {
  caption: '',
  link: '#',
  icon: '',
  children: () => [],
  isChild: false,
  badge: 0,
})

defineEmits(['select'])

const route = useRoute()
const router = useRouter()

const isActive = computed(() => {
  if (!props.link || props.link === '#') return false
  const [linkPath, linkQueryStr] = props.link.split('?')
  if (route.path !== linkPath) return false
  if (!linkQueryStr) return Object.keys(route.query).length === 0
  const linkParams = new URLSearchParams(linkQueryStr)
  for (const [k, v] of linkParams.entries()) {
    if (route.query[k] !== v) return false
  }
  return true
})

function navigate() {
  if (props.link && props.link !== '#') void router.push(props.link)
}
</script>

<style scoped>
.child-item {
  padding-left: 40px;
  font-size: 12px;
}

.child-item :deep(.q-item__label) {
  font-size: 12px;
}
</style>
