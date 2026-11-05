<template>
  <router-view />
  <SessionExpiryDialog />
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useAuthStore } from 'stores/auth'
import { useThemeStore } from 'stores/theme'
import SessionExpiryDialog from 'components/SessionExpiryDialog.vue'

const auth = useAuthStore()
const theme = useThemeStore()
watch(
  () => auth.me?.id,
  (userId) => theme.loadAppearanceMode(userId),
  { immediate: true },
)
onMounted(() => {
  void auth.bootstrap()
  void theme.load()
})
</script>
