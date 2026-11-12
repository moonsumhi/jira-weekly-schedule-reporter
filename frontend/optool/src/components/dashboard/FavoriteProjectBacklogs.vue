<template>
  <section class="favorite-backlogs" aria-labelledby="favorite-backlogs-title" :aria-busy="loading">
    <div class="favorite-heading">
      <slot name="drag-handle" />
      <div class="favorite-heading-title">
        <h2 id="favorite-backlogs-title">즐겨찾는 프로젝트</h2>
        <span v-if="!loading && !loadFailed && favorites.length" class="favorite-count">{{ favorites.length }}</span>
      </div>
      <q-btn flat dense round size="sm" color="primary" icon="open_in_new" aria-label="전체 프로젝트 열기" to="/pm/projects">
        <q-tooltip>전체 프로젝트</q-tooltip>
      </q-btn>
      <slot name="actions" />
    </div>

    <div class="favorite-body">
      <div v-if="loading" class="favorite-grid" role="status" aria-label="즐겨찾는 프로젝트 불러오는 중">
        <div v-for="index in 3" :key="index" class="favorite-placeholder" aria-hidden="true">
          <q-skeleton type="text" width="65%" :animation="'none'" />
          <q-skeleton type="text" width="30%" :animation="'none'" />
        </div>
      </div>

      <div v-else-if="loadFailed" class="favorite-message" role="status">
        <p>즐겨찾는 프로젝트를 불러오지 못했습니다.</p>
        <q-btn flat no-caps color="primary" icon="refresh" label="다시 불러오기" @click="loadFavorites" />
      </div>

      <template v-else-if="favorites.length">
        <ul id="favorite-backlog-list" class="favorite-grid">
          <li v-for="project in visibleFavorites" :key="project.id">
            <router-link
              :to="`/pm/projects/${project.id}/backlog`"
              class="favorite-project-link"
              :aria-label="`${project.name} (${project.key}) 백로그 열기`"
            >
              <div class="favorite-project-info">
                <span class="favorite-project-name" :title="project.name">{{ project.name }}</span>
                <span class="favorite-project-key" :title="project.key">{{ project.key }}</span>
              </div>
              <span class="favorite-project-action" aria-hidden="true">
                백로그 <q-icon name="arrow_forward" size="18px" />
              </span>
            </router-link>
          </li>
        </ul>
        <div v-if="favorites.length > PREVIEW_LIMIT" class="favorite-more">
          <q-btn flat no-caps color="primary"
            :label="expanded ? '접기' : `${favorites.length - PREVIEW_LIMIT}개 더 보기`"
            :icon-right="expanded ? 'expand_less' : 'expand_more'"
            :aria-expanded="expanded" aria-controls="favorite-backlog-list"
            @click="expanded = !expanded" />
        </div>
      </template>

      <div v-else class="favorite-message favorite-empty">
        <div>
          <p class="favorite-empty-title">자주 쓰는 프로젝트를 여기에 모아보세요.</p>
          <p>프로젝트에서 별표를 누르면 백로그로 바로 이동할 수 있어요.</p>
        </div>
        <q-btn outline no-caps color="primary" icon="star_border" label="프로젝트 고르기" to="/pm/projects" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listProjects, type Project } from 'src/services/pm/project'

const PREVIEW_LIMIT = 6
const favorites = ref<Project[]>([])
const loading = ref(true)
const loadFailed = ref(false)
const expanded = ref(false)
const visibleFavorites = computed(() => expanded.value ? favorites.value : favorites.value.slice(0, PREVIEW_LIMIT))

async function loadFavorites() {
  loading.value = true
  loadFailed.value = false
  try {
    const projects = await listProjects()
    favorites.value = projects.filter(project => project.isFavorite)
      .sort((a, b) => (a.favoriteOrder ?? 0) - (b.favoriteOrder ?? 0))
  } catch {
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => { void loadFavorites() })
</script>

<style scoped>
.favorite-backlogs { display: flex; flex-direction: column; min-width: 0; margin: 0; padding: 20px; background: var(--bo-surface); border: 1px solid var(--bo-border); border-radius: var(--bo-radius); }
.favorite-heading { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-shrink: 0; }
.favorite-body { flex: 1; min-height: 0; overflow-y: auto; }
.favorite-heading-title { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.favorite-heading h2 { margin: 0; color: var(--bo-text); font-size: 15px; line-height: 1.45; font-weight: 700; }
.favorite-count { color: var(--bo-muted); font-size: 13px; font-variant-numeric: tabular-nums; }
.favorite-grid { display: grid; grid-template-columns: minmax(0, 1fr); margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--bo-border); }
.favorite-grid > li { min-width: 0; border-bottom: 1px solid var(--bo-border); }
.favorite-project-link, .favorite-placeholder {
  min-height: 80px;
  height: 100%;
  padding: 14px 8px;
  border-radius: var(--bo-control-radius);
}
.favorite-project-link { display: flex; align-items: center; gap: 16px; text-decoration: none; transition: background-color 160ms ease-out; }
.favorite-project-link:hover { background: var(--bo-accent-soft); }
.favorite-project-link:focus-visible { outline: 2px solid var(--bo-accent-ink); outline-offset: 3px; background: var(--bo-accent-soft); }
.favorite-project-info { flex: 1; min-width: 0; }
.favorite-project-name { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; overflow-wrap: anywhere; color: var(--bo-text); font-size: 15px; line-height: 1.5; font-weight: 600; }
.favorite-project-key { display: block; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bo-muted); font-size: 12px; }
.favorite-project-action { display: flex; align-items: center; gap: 6px; flex-shrink: 0; color: var(--bo-accent-ink); font-size: 12px; font-weight: 600; }
.favorite-message { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px 20px; padding: 16px 0 0; border-top: 1px solid var(--bo-border); color: var(--bo-muted); font-size: 13px; }
.favorite-message p { margin: 0; }
.favorite-empty .favorite-empty-title { margin-bottom: 4px; color: var(--bo-secondary); font-size: 14px; font-weight: 600; }
.favorite-more { display: flex; justify-content: center; margin-top: 8px; }
@media (max-width: 600px) {
  .favorite-backlogs { padding: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .favorite-project-link { transition: none; }
}
</style>
