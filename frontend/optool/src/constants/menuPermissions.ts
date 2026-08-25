// 메뉴 slug ↔ 권한(permission) 문자열 매핑.
// 관리자 화면(AdminUserListPage)에서 권한은 menu.slug 값 그대로 부여되므로
// 이 맵의 값도 항상 slug와 동일해야 한다.
export const SLUG_PERM: Record<string, string> = {
  job: 'job', asset: 'asset', watch: 'watch',
  server_check: 'server_check',
  pm: 'pm', sr: 'sr', calendar: 'calendar',
}

export const PERM_SLUG: Record<string, string> = Object.fromEntries(
  Object.entries(SLUG_PERM).map(([slug, perm]) => [perm, slug]),
)
