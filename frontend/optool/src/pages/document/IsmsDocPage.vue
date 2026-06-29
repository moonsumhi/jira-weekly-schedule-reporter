<template>
  <DocumentManagePage :scope-folder="folderName" />
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import DocumentManagePage from './DocumentManagePage.vue'

const route = useRoute()
const folderName = route.params['folderName'] as string
</script>
