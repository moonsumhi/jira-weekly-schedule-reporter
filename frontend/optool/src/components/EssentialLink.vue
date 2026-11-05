<template>
  <!-- If has children -> render as expansion -->
  <q-expansion-item
    v-if="children && children.length"
    :model-value="isExpanded"
    :dark="theme.appearanceMode === 'dark'"
    class="sidebar-expansion-item"
    expand-separator
    @update:model-value="onExpansionToggle"
  >
    <template #header>
      <q-item-section avatar>
        <q-icon :name="icon" :style="menuIconColorStyle" />
      </q-item-section>
      <q-item-section :style="menuColorStyle">{{ title }}</q-item-section>
      <q-item-section side v-if="badge && badge > 0">
        <q-badge color="negative" :label="badge" rounded />
      </q-item-section>
      <q-tooltip v-if="compact" anchor="center right" self="center left">{{ title }}</q-tooltip>
    </template>
    <EssentialLink
      v-for="child in children"
      :key="(child.link ?? child.title) + (child.icon ?? '')"
      v-bind="child"
      :isChild="true"
      :compact="props.compact ?? false"
      @select="$emit('select', $event)"
      @expand-sidebar="emit('expand-sidebar')"
    />
  </q-expansion-item>

  <!-- If no children -> render as clickable item -->
  <q-item
    v-else
    :dark="theme.appearanceMode === 'dark'"
    class="sidebar-link-item"
    clickable
    :active="isActive"
    active-color="primary"
    @click="navigate"
    :class="{ 'child-item': isChild }"
  >
    <q-item-section avatar>
      <q-icon :name="icon || 'fiber_manual_record'" :size="icon ? 'sm' : 'xs'" :style="menuIconColorStyle" />
    </q-item-section>

    <q-item-section :style="menuColorStyle">
      <span class="sidebar-link-title">{{ title }}</span>
      <span v-if="caption" class="sidebar-link-caption">{{ caption }}</span>
    </q-item-section>

    <q-item-section side v-if="badge && badge > 0">
      <q-badge color="negative" :label="badge" rounded />
    </q-item-section>
    <q-tooltip v-if="compact" anchor="center right" self="center left">{{ title }}</q-tooltip>
  </q-item>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from 'stores/theme'

export interface EssentialLinkProps {
  title: string;
  caption?: string;
  link?: string;
  icon?: string;
  color?: string | null;
  iconColor?: string | null;
  children?: EssentialLinkProps[];
  isChild?: boolean;
  compact?: boolean;
  badge?: number;
}

const props = withDefaults(defineProps<EssentialLinkProps>(), {
  caption: '',
  link: '#',
  icon: '',
  color: null,
  iconColor: null,
  children: () => [],
  isChild: false,
  compact: false,
  badge: 0,
})

const emit = defineEmits<{
  (event: 'select', link: string): void
  (event: 'expand-sidebar'): void
}>()

const route = useRoute()
const router = useRouter()
const theme = useThemeStore()
const isExpanded = ref(false)

function menuColorForMode(value: string | null | undefined): string {
  const hex = value && /^#[0-9a-fA-F]{6}$/.test(value) ? value : '#000000'
  if (theme.appearanceMode !== 'dark') return hex

  const channels = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16))
  const brightness = (channels[0]! * 299 + channels[1]! * 587 + channels[2]! * 114) / 1000
  const targetBrightness = 190
  if (brightness >= targetBrightness) return hex

  const lightenRatio = (targetBrightness - brightness) / (255 - brightness)
  return `#${channels.map((channel) => Math.round(channel + (255 - channel) * lightenRatio).toString(16).padStart(2, '0')).join('')}`
}

const menuColorStyle = computed(() => ({ color: menuColorForMode(props.color) }))
const menuIconColorStyle = computed(() => ({ color: menuColorForMode(props.iconColor ?? props.color) }))

const isActive = computed(() => {
  if (!props.link || props.link === '#') return false
  const [linkPath, linkQueryStr] = props.link.split('?')
  if (route.meta.activeMenuLink === linkPath && !linkQueryStr) return true
  if (route.path !== linkPath) return false
  if (!linkQueryStr) return Object.keys(route.query).length === 0
  const linkParams = new URLSearchParams(linkQueryStr)
  for (const [k, v] of linkParams.entries()) {
    if (route.query[k] !== v) return false
  }
  return true
})

function onExpansionToggle(expanded: boolean) {
  if (props.compact) {
    isExpanded.value = true
    emit('expand-sidebar')
    return
  }
  isExpanded.value = expanded
}

function navigate() {
  if (!props.link || props.link === '#') return
  if (props.link.startsWith('http://') || props.link.startsWith('https://')) {
    window.open(props.link, '_blank', 'noopener,noreferrer')
  } else {
    void router.push(props.link)
  }
}
</script>

<style scoped>
.child-item {
  padding-left: 40px;
  font-size: 12px;
}

.child-item .sidebar-link-title {
  font-size: 12px;
}

.sidebar-link-caption {
  margin-top: 4px;
  color: rgba(0, 0, 0, 0.54);
  font-size: 12px;
  line-height: 1.2;
}

:global(body.body--dark) .sidebar-link-caption {
  color: rgba(255, 255, 255, 0.68);
}

.sidebar-expansion-item,
.sidebar-expansion-item :deep(.q-expansion-item__header),
.sidebar-link-item {
  width: 100%;
  box-sizing: border-box;
  min-height: 48px;
  align-items: center;
}

.sidebar-expansion-item :deep(.q-item__section--main),
.sidebar-link-item :deep(.q-item__section--main) {
  justify-content: center;
}

.sidebar-expansion-item :deep(.q-item__label),
.sidebar-link-title {
  line-height: 1.25;
}
</style>
