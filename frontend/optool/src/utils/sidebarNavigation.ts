type SidebarRoute = {
  path: string
  query: Record<string, string | null | (string | null)[] | undefined>
  activeMenuLink?: unknown
}

function matchLink(link: string | undefined, route: SidebarRoute) {
  if (!link?.startsWith('/') || link.startsWith('//')) return null
  const [path = '', query = ''] = link.split('#')[0]!.split('?')
  const activePath = typeof route.activeMenuLink === 'string' ? route.activeMenuLink : route.path
  if (activePath !== path && !activePath.startsWith(`${path}/`)) return null
  const params = new URLSearchParams(query)
  for (const [key, value] of params) {
    if (route.query[key] !== value) return null
  }
  return { pathLength: path.length, queryCount: Array.from(params).length }
}

/** Prefer a matching category/detail menu over its unfiltered parent link. */
export function isSidebarLinkActive(
  link: string | undefined,
  route: SidebarRoute,
  siblingLinks: readonly string[] = [],
): boolean {
  const match = matchLink(link, route)
  if (!match) return false
  return !siblingLinks.some(sibling => {
    const other = matchLink(sibling, route)
    return other !== null && (
      other.pathLength > match.pathLength
      || (other.pathLength === match.pathLength && other.queryCount > match.queryCount)
    )
  })
}
