<template>
  <!-- If has children -> render as expansion -->
  <q-expansion-item
    v-if="children && children.length"
    :model-value="!compact && isExpanded"
    :dark="theme.appearanceMode === 'dark'"
    class="sidebar-expansion-item"
    @update:model-value="onExpansionToggle"
    header-class="sidebar-group-header"
    :expand-icon="sidebarIcons.expand"
    :class="{ 'sidebar-group--active': isGroupActive }"
  >
    <template #header>
      <q-item-section avatar>
        <q-icon :name="displayIcon" :size="isChild ? '18px' : '20px'" :style="menuIconColorStyle" />
      </q-item-section>
      <q-item-section :style="menuColorStyle">{{ title }}</q-item-section>
      <q-item-section side v-if="badge && badge > 0">
        <q-badge color="negative" :label="badge" rounded />
      </q-item-section>
      <q-tooltip v-if="compact" anchor="center right" self="center left">{{ title }}</q-tooltip>
    </template>
    <div class="sidebar-children">
    <EssentialLink
      v-for="child in children"
      :key="(child.link ?? child.title) + (child.icon ?? '')"
      v-bind="child"
      :isChild="true"
      :compact="props.compact ?? false"
      @select="$emit('select', $event)"
      @expand-sidebar="emit('expand-sidebar')"
    />
    </div>
  </q-expansion-item>

  <!-- If no children -> render as clickable item -->
  <q-item
    v-else
    :dark="theme.appearanceMode === 'dark'"
    class="sidebar-link-item"
    clickable
    :active="isActive"
    :aria-current="isActive ? 'page' : undefined"
    active-color="primary"
    @click="navigate"
    :class="{ 'child-item': isChild }"
  >
    <q-item-section avatar>
      <q-icon :name="displayIcon || 'fiber_manual_record'" :size="icon ? (isChild ? '18px' : '20px') : '6px'" :style="menuIconColorStyle" />
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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resolveSidebarIcon, sidebarIcons } from 'src/utils/sidebarIcons'
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
const displayIcon = computed(() => resolveSidebarIcon(props.icon))

const isActive = computed(() => {
  if (!props.link || props.link === '#') return false
  const [linkPath, linkQueryStr] = props.link.split('?')
  if (route.meta.activeMenuLink === linkPath && !linkQueryStr) return true
  if (route.path !== linkPath && !route.path.startsWith(`${linkPath}/`)) return false
  if (!linkQueryStr) return true
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

const isGroupActive = computed(() => props.children.some((child) => {
  if (!child.link || child.link === '#') return false
  const [path = ''] = child.link.split('?')
  const activePath = route.meta.activeMenuLink ?? route.path
  return typeof activePath === 'string' && (activePath === path || activePath.startsWith(`${path}/`))
}))
watch(isGroupActive, (active) => { if (active) isExpanded.value = true }, { immediate: true })

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
.sidebar-link-caption {
  margin-top: 4px;
  color: var(--bo-muted);
  font-size: 12px;
  line-height: 1.5;
}

:global(body.body--dark) .sidebar-link-caption {
  color: rgba(255, 255, 255, 0.68);
}

.sidebar-expansion-item :deep(.sidebar-group-header),
.sidebar-link-item {
  width: 100%;
  box-sizing: border-box;
  min-height: 44px;
  align-items: center;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.45;
  letter-spacing: -0.01em;
}
.sidebar-expansion-item { margin-bottom: 4px; }
.sidebar-link-item { margin-bottom: 4px; }
.sidebar-expansion-item :deep(.sidebar-group-header) { padding-right: 10px; }
.sidebar-expansion-item :deep(.q-item__section--avatar),
.sidebar-link-item :deep(.q-item__section--avatar) { min-width: 32px; padding-right: 12px; }
.sidebar-expansion-item :deep(.q-expansion-item__toggle-icon) { font-size: 18px; color: var(--bo-muted); }
.sidebar-children { margin: 4px 0 8px 21px; padding-left: 10px; border-left: 1px solid var(--bo-border); }
.sidebar-link-item.child-item { min-height: 40px; padding: 9px 10px; margin-bottom: 2px; font-size: 13px; font-weight: 450; }
.sidebar-link-item.child-item :deep(.q-item__section--avatar) { min-width: 28px; padding-right: 10px; }
.sidebar-expansion-item :deep(.q-item__section--main),
.sidebar-link-item :deep(.q-item__section--main) { min-width: 0; overflow-wrap: anywhere; }
.sidebar-link-item.q-item--active {
  background: var(--bo-accent-soft);
  font-weight: 600;
}
.sidebar-link-item.q-item--active :deep(.q-item__section),
.sidebar-link-item.q-item--active :deep(.q-icon) {
  color: var(--bo-accent-ink) !important;
}
.sidebar-group--active :deep(.sidebar-group-header) {
  font-weight: 600;
}
.sidebar-expansion-item :deep(.sidebar-group-header:focus-visible),
.sidebar-link-item:focus-visible { outline-offset: -2px; }

.sidebar-expansion-item :deep(.q-item__section--main),
.sidebar-link-item :deep(.q-item__section--main) {
  justify-content: center;
}

.sidebar-expansion-item :deep(.q-item__label),
.sidebar-link-title {
  line-height: 1.45;
}
</style>
