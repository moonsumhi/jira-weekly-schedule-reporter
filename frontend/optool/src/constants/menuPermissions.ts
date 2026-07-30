// 메뉴 slug ↔ 권한(permission) 문자열 매핑.
// 관리자 화면(AdminUserListPage)에서 권한은 menu.slug 값 그대로 부여되므로
// 이 맵의 값도 항상 slug와 동일해야 한다 (예전에 'isms-p' → 'isms_p'로 잘못 매핑되어
// 있었는데, 실제 저장되는 권한 문자열은 'isms-p'라서 절대 매치되지 않는 버그였음).
export const SLUG_PERM: Record<string, string> = {
  jira: 'jira', job: 'job', asset: 'asset', watch: 'watch',
  inspection: 'inspection', server_check: 'server_check',
  pm: 'pm', sr: 'sr', calendar: 'calendar',
  documents: 'documents', 'isms-p': 'isms-p',
}

export const PERM_SLUG: Record<string, string> = Object.fromEntries(
  Object.entries(SLUG_PERM).map(([slug, perm]) => [perm, slug]),
)
