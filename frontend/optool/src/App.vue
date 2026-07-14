<template>
  <router-view />
  <SessionExpiryDialog />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from 'stores/auth'
import { useThemeStore } from 'stores/theme'
import SessionExpiryDialog from 'components/SessionExpiryDialog.vue'

const auth = useAuthStore()
const theme = useThemeStore()
onMounted(() => {
  void auth.bootstrap()
  void theme.load()
})
</script>
