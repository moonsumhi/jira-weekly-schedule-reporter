import type { LocationQuery, RouterScrollBehavior } from 'vue-router'

const dialogQueryKeys = new Set(['entryId', 'issueId', 'commentId'])
function pageQuery(query: LocationQuery) {
  return JSON.stringify(Object.entries(query)
    .filter(([key]) => !dialogQueryKeys.has(key))
    .sort(([left], [right]) => left.localeCompare(right)))
}

/** Dialog history and query cleanup keep the current page in place. */
export const routeScrollBehavior: RouterScrollBehavior = (to, from, savedPosition) => {
  if (from.matched.length && to.fullPath === from.fullPath) return false
  if (savedPosition) return savedPosition
  if (from.matched.length && to.path === from.path && to.hash === from.hash
    && pageQuery(to.query) === pageQuery(from.query)) return false
  return { left: 0, top: 0 }
}
