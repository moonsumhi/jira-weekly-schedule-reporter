<template>
  <router-view />
  <SessionExpiryDialog />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from 'stores/auth'
import SessionExpiryDialog from 'components/SessionExpiryDialog.vue'

const auth = useAuthStore()
onMounted(() => auth.bootstrap())
</script>
