// 메뉴 slug ↔ 권한(permission) 문자열 매핑.
// 대부분 동일하지만 isms-p처럼 slug와 permission 표기가 다른 경우가 있어 별도로 관리한다.
export const SLUG_PERM: Record<string, string> = {
  jira: 'jira', job: 'job', asset: 'asset', watch: 'watch',
  inspection: 'inspection', server_check: 'server_check',
  pm: 'pm', sr: 'sr', calendar: 'calendar',
  documents: 'documents', 'isms-p': 'isms_p',
}

export const PERM_SLUG: Record<string, string> = Object.fromEntries(
  Object.entries(SLUG_PERM).map(([slug, perm]) => [perm, slug]),
)

// 메뉴에 노출 팀이 지정되지 않았을 때 적용되는 기본값.
// (비워두면 전체 팀에 표시가 아니라, 데이터운영팀에게만 표시된다)
export const DEFAULT_VISIBLE_TEAM = '데이터운영팀'

export function effectiveVisibleTeams(visibleTeams?: string[] | null): string[] {
  return visibleTeams && visibleTeams.length > 0 ? visibleTeams : [DEFAULT_VISIBLE_TEAM]
}
