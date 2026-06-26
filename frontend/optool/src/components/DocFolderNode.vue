<template>
  <div class="folder-node">
    <div
      class="folder-item"
      :class="{ 'folder-item--active': selectedId === node.id }"
      @click="$emit('select', node.id)"
    >
      <q-icon
        v-if="node.children.length"
        :name="expanded ? 'expand_more' : 'chevron_right'"
        size="14px"
        class="q-mr-xs cursor-pointer"
        @click.stop="expanded = !expanded"
      />
      <span v-else style="width:14px; display:inline-block; margin-right:4px" />
      <q-icon name="folder" size="16px" color="amber-7" class="q-mr-xs" />
      <span class="folder-item-label">{{ node.name }}</span>
      <q-btn
        v-if="isAdmin"
        flat dense round icon="delete" color="negative" size="xs"
        class="folder-del-btn"
        @click.stop="$emit('delete', node)"
      />
    </div>
    <div v-if="expanded && node.children.length" class="folder-children">
      <DocFolderNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :selected-id="selectedId"
        :is-admin="isAdmin"
        @select="$emit('select', $event)"
        @delete="$emit('delete', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { DocFolder } from 'src/services/documents'

interface TreeNode extends DocFolder {
  children: TreeNode[]
}

defineProps<{
  node: TreeNode
  selectedId: string | null
  isAdmin: boolean
}>()

defineEmits<{
  select: [id: string]
  delete: [folder: TreeNode]
}>()

const expanded = ref(false)
</script>

<style scoped>
.folder-node { /* wrapper */ }

.folder-item {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #37474f;
  transition: background 0.15s;
  position: relative;
}

.folder-item:hover { background: #f0f4ff; }
.folder-item--active { background: #e8eeff; color: #1a237e; font-weight: 600; }

.folder-item-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-del-btn {
  opacity: 0;
  transition: opacity 0.15s;
}
.folder-item:hover .folder-del-btn { opacity: 1; }

.folder-children { padding-left: 16px; }
</style>
